from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.analysis import RequirementReadiness
from app.services.llm import LLMRequest, LLMResult, LLMService


class ClarificationAnswerContext(BaseModel):
    question: str
    answer: str


class RequirementAnalystInput(BaseModel):
    project_context: dict
    raw_requirement: str
    requirement_context: dict
    clarification_answers: list[ClarificationAnswerContext]


class RequirementBaselineAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature: str = Field(min_length=1)
    business_objective: str = Field(min_length=1)
    problem_statement: str = Field(min_length=1)
    actors: list[str]
    known_requirements: list[str]
    business_rules: list[str]
    constraints: list[str]
    dependencies: list[str]
    assumptions: list[str]
    unknown_information: list[str]


class RequirementAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline: RequirementBaselineAgentOutput
    readiness: RequirementReadiness
    clarification_questions: list[str]
    blocked_reason: str


class InvalidAgentOutputError(RuntimeError):
    pass


@dataclass(frozen=True)
class RequirementAnalystConfig:
    model: str
    max_output_tokens: int
    temperature: Optional[float] = None


SYSTEM_PROMPT = "\n".join(
    (
        "You are the Requirement Analyst for SpaceForge AI.",
        "Your only responsibility is to transform project context and a raw requirement "
        "into a factual Requirement Baseline, identify ambiguity, and decide readiness.",
        "",
        "Readiness rules:",
        "- READY: the requirement is sufficiently clear for later analysis.",
        "- NEEDS_CLARIFICATION: material information is missing but can be answered by "
        "the user. Ask concise, specific questions.",
        "- BLOCKED: analysis cannot continue because of an explicit conflict or "
        "unavailable prerequisite; explain it in blocked_reason.",
        "",
        "Never design a technical solution. Never propose a database, UI, API, "
        "architecture, implementation, technology, or TO-BE process. Do not invent "
        "facts. Put uncertain statements in assumptions or unknown_information.",
        "",
        "For READY, clarification_questions and blocked_reason must be empty.",
        "For NEEDS_CLARIFICATION, provide at least one specific clarification question "
        "and leave blocked_reason empty.",
        "For BLOCKED, provide blocked_reason and leave clarification_questions empty.",
        "Return only the structured output requested by the schema.",
    )
)


class RequirementAnalystAgent:
    name = "REQUIREMENT_ANALYST"

    def __init__(self, llm: LLMService, config: RequirementAnalystConfig) -> None:
        self._llm = llm
        self._config = config

    def build_request(self, input_data: RequirementAnalystInput) -> LLMRequest:
        return LLMRequest(
            agent_name=self.name,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=json.dumps(input_data.model_dump(mode="json"), ensure_ascii=False),
            model=self._config.model,
            max_output_tokens=self._config.max_output_tokens,
            temperature=self._config.temperature,
        )

    async def analyze(self, request: LLMRequest) -> LLMResult[RequirementAnalysisOutput]:
        result = await self._llm.generate_structured(request, RequirementAnalysisOutput)
        self._validate_semantics(result.output)
        return result

    @staticmethod
    def _validate_semantics(output: RequirementAnalysisOutput) -> None:
        has_questions = bool(output.clarification_questions) and all(
            question.strip() for question in output.clarification_questions
        )
        if output.readiness == RequirementReadiness.READY and (
            output.clarification_questions or output.blocked_reason.strip()
        ):
            raise InvalidAgentOutputError(
                "READY output cannot contain pending questions or a block."
            )
        if output.readiness == RequirementReadiness.NEEDS_CLARIFICATION and (
            not has_questions or output.blocked_reason.strip()
        ):
            raise InvalidAgentOutputError(
                "NEEDS_CLARIFICATION requires questions and cannot contain a block."
            )
        if output.readiness == RequirementReadiness.BLOCKED and (
            output.clarification_questions or not output.blocked_reason.strip()
        ):
            raise InvalidAgentOutputError(
                "BLOCKED requires a reason and cannot contain clarification questions."
            )
