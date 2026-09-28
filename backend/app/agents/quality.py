from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.artifacts.schemas import AcceptanceCriteriaContent, TestScenarioContent
from app.domain.artifacts import ArtifactType
from app.domain.quality import (
    REVIEWABLE_ARTIFACT_TYPES,
    ReviewDecision,
    ReviewSeverity,
)
from app.services.llm import LLMRequest, LLMResult, LLMService


@dataclass(frozen=True)
class QualityAgentConfig:
    model: str
    max_output_tokens: int
    temperature: Optional[float] = None


class QualityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: dict
    solution: dict
    flow: dict
    ui: dict
    database: dict
    api: dict
    test_scenario: Optional[dict] = None
    acceptance_criteria: Optional[dict] = None
    revision_feedback: list[dict] = Field(default_factory=list)


class QAAnalystOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_scenario: TestScenarioContent
    acceptance_criteria: AcceptanceCriteriaContent

    @model_validator(mode="after")
    def require_coverage(self) -> QAAnalystOutput:
        categories = {case.category.value for case in self.test_scenario.test_cases}
        required = {
            "POSITIVE",
            "NEGATIVE",
            "VALIDATION",
            "BOUNDARY",
            "PERMISSION",
            "WORKFLOW",
            "INTEGRATION",
            "REGRESSION",
        }
        missing = sorted(required - categories)
        if missing:
            raise ValueError(f"test coverage is missing categories: {', '.join(missing)}")
        if any(not case.steps for case in self.test_scenario.test_cases):
            raise ValueError("every test case must contain at least one step")
        if not self.acceptance_criteria.criteria:
            raise ValueError("at least one acceptance criterion is required")
        return self


class ReviewIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact: ArtifactType
    issue: str = Field(min_length=1)
    severity: ReviewSeverity
    reason: str = Field(min_length=1)
    recommended_revision: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_revision_target(self) -> ReviewIssue:
        if self.artifact.value not in REVIEWABLE_ARTIFACT_TYPES:
            raise ValueError("review issues must target a Phase 6 or QA artifact")
        return self


class SAReviewerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    summary: str = Field(min_length=1)
    issues: list[ReviewIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_decision(self) -> SAReviewerOutput:
        if self.decision == ReviewDecision.PASS and self.issues:
            raise ValueError("PASS cannot contain issues")
        if self.decision == ReviewDecision.REVISION_REQUIRED and not self.issues:
            raise ValueError("REVISION_REQUIRED must contain at least one issue")
        return self


QA_SYSTEM_PROMPT = "\n".join(
    (
        "You are the QA Analyst Agent for SpecForge AI.",
        "Use the Requirement, approved Solution, Process Flow, UI prototype source, Database "
        "Design, and API Specification as the complete authority.",
        "Generate concrete test cases across POSITIVE, NEGATIVE, VALIDATION, BOUNDARY, "
        "PERMISSION, WORKFLOW, INTEGRATION, and REGRESSION. Every test case needs a stable id, "
        "scenario, precondition, ordered steps, expected result, and related requirement.",
        "Generate acceptance criteria in explicit Given/When/Then fields and trace every item to "
        "a requirement. Do not invent product behavior or implementation.",
        "When revision_feedback is present, correct the cited issues while preserving valid "
        "coverage.",
        "Return only the structured output requested by the schema.",
    )
)


REVIEW_SYSTEM_PROMPT = "\n".join(
    (
        "You are the SA Reviewer Agent and final consistency gate for SpecForge AI.",
        "Check Requirement vs Flow, Requirement vs UI, UI vs Database, UI vs API, Business Rule "
        "vs Test, Permission vs API, AS-IS vs TO-BE, and Acceptance Criteria vs Requirement.",
        "Return PASS only when all supplied artifacts are mutually consistent, sufficiently "
        "traceable, and contain no material gap. Otherwise return REVISION_REQUIRED.",
        "Requirement and approved Solution are authoritative baselines. Route each issue to the "
        "downstream artifact that must be revised: PROCESS_FLOW, UI_PROTOTYPE, DATABASE_DESIGN, "
        "API_SPECIFICATION, TEST_SCENARIO, or ACCEPTANCE_CRITERIA.",
        "For every issue provide artifact, issue, severity, reason, and a specific recommended "
        "revision. Do not redesign artifacts yourself.",
        "Return only the structured output requested by the schema.",
    )
)


class _QualityAgent:
    name: str
    system_prompt: str

    def __init__(self, llm: LLMService, config: QualityAgentConfig) -> None:
        self._llm = llm
        self._config = config

    def build_request(self, payload: QualityInput) -> LLMRequest:
        return LLMRequest(
            agent_name=self.name,
            system_prompt=self.system_prompt,
            user_prompt=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
            model=self._config.model,
            max_output_tokens=self._config.max_output_tokens,
            temperature=self._config.temperature,
        )


class QAAnalystAgent(_QualityAgent):
    name = "QA_ANALYST"
    system_prompt = QA_SYSTEM_PROMPT

    async def analyze(self, request: LLMRequest) -> LLMResult[QAAnalystOutput]:
        return await self._llm.generate_structured(request, QAAnalystOutput)


class SAReviewerAgent(_QualityAgent):
    name = "SA_REVIEWER"
    system_prompt = REVIEW_SYSTEM_PROMPT

    async def analyze(self, request: LLMRequest) -> LLMResult[SAReviewerOutput]:
        return await self._llm.generate_structured(request, SAReviewerOutput)
