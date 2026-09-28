from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.discovery import (
    ChangeClassification,
    ExistingComponentType,
    ExistingEvidenceType,
)
from app.domain.projects import ProjectType
from app.services.llm import LLMRequest, LLMResult, LLMService


class ResearchAgentInput(BaseModel):
    requirement_baseline: dict


class ResearchSourceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    supports: str

    @field_validator("url")
    @classmethod
    def require_http_url(cls, value: str) -> str:
        if urlparse(value).scheme not in {"http", "https"}:
            raise ValueError("Research source URL must use HTTP or HTTPS.")
        return value


class ResearchAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1)
    common_practices: list[str]
    comparable_workflows: list[str]
    common_metadata: list[str]
    ux_patterns: list[str]
    technical_considerations: list[str]
    risks: list[str]
    sources: list[ResearchSourceOutput]
    open_questions: list[str]


class ExistingSystemEvidence(BaseModel):
    source_type: ExistingEvidenceType
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class ExistingSystemAgentInput(BaseModel):
    project_type: ProjectType
    project_context: dict
    requirement_baseline: dict
    evidence: list[ExistingSystemEvidence]
    previous_artifacts: list[dict]


class ExistingComponentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    component_type: ExistingComponentType
    classification: ChangeClassification
    evidence: str
    rationale: str
    impact: str


class GapAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: str
    current_state: str
    required_state: str
    gap: str


class ExistingSystemAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_is_summary: str
    components: list[ExistingComponentOutput]
    affected_components: list[str]
    gap_analysis: list[GapAnalysisOutput]
    regression_risks: list[str]
    unknown_information: list[str]


class InvalidDiscoveryOutputError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpecialistAgentConfig:
    model: str
    max_output_tokens: int
    temperature: Optional[float] = None


RESEARCH_SYSTEM_PROMPT = "\n".join(
    (
        "You are the Research Agent for SpaceForge AI.",
        "Research general practices, comparable workflows, common metadata, UX patterns, "
        "technical considerations, and relevant risks for the supplied Requirement Baseline.",
        "Produce evidence-oriented insights only. Do not select, prescribe, or design a final "
        "solution. Do not create a database design, API specification, or UI design.",
        "Use web search when useful. Include only sources actually used, with a title, URL, "
        "and a concise statement of what each source supports.",
        "Separate generally observed patterns from requirement-specific facts. Do not invent "
        "sources or claim that a practice is mandatory without evidence.",
        "Return only the structured output requested by the schema.",
    )
)


EXISTING_SYSTEM_SYSTEM_PROMPT = "\n".join(
    (
        "You are the Existing System Analyst for SpaceForge AI.",
        "Analyze only the supplied project context, Requirement Baseline, evidence, and prior "
        "artifacts. Do not assume access to source systems or invent missing components.",
        "Identify existing modules, reusable entities and master data, APIs, tables, business "
        "rules, integration points, and regression risks.",
        "Classify every component as REUSE, MODIFY, NEW, or DEPRECATE and cite the supplied "
        "evidence behind the classification. NEW means the evidence indicates a capability is "
        "absent; it is not permission to design the solution.",
        "For ENHANCEMENT, provide a substantive AS-IS summary, affected components, and gap "
        "analysis. Do not design TO-BE behavior or a final technical solution.",
        "Return only the structured output requested by the schema.",
    )
)


class ResearchAgent:
    name = "RESEARCH_AGENT"

    def __init__(
        self,
        llm: LLMService,
        config: SpecialistAgentConfig,
        *,
        web_search_enabled: bool,
    ) -> None:
        self._llm = llm
        self._config = config
        self._web_search_enabled = web_search_enabled

    def build_request(self, input_data: ResearchAgentInput) -> LLMRequest:
        tools = ({"type": "web_search"},) if self._web_search_enabled else ()
        return LLMRequest(
            agent_name=self.name,
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            user_prompt=json.dumps(input_data.model_dump(mode="json"), ensure_ascii=False),
            model=self._config.model,
            max_output_tokens=self._config.max_output_tokens,
            temperature=self._config.temperature,
            tools=tools,
        )

    async def analyze(self, request: LLMRequest) -> LLMResult[ResearchAgentOutput]:
        return await self._llm.generate_structured(request, ResearchAgentOutput)


class ExistingSystemAnalyst:
    name = "EXISTING_SYSTEM_ANALYST"

    def __init__(self, llm: LLMService, config: SpecialistAgentConfig) -> None:
        self._llm = llm
        self._config = config

    def build_request(self, input_data: ExistingSystemAgentInput) -> LLMRequest:
        return LLMRequest(
            agent_name=self.name,
            system_prompt=EXISTING_SYSTEM_SYSTEM_PROMPT,
            user_prompt=json.dumps(input_data.model_dump(mode="json"), ensure_ascii=False),
            model=self._config.model,
            max_output_tokens=self._config.max_output_tokens,
            temperature=self._config.temperature,
        )

    async def analyze(
        self, request: LLMRequest, project_type: ProjectType
    ) -> LLMResult[ExistingSystemAnalysisOutput]:
        result = await self._llm.generate_structured(request, ExistingSystemAnalysisOutput)
        if project_type == ProjectType.ENHANCEMENT:
            output = result.output
            if (
                not output.as_is_summary.strip()
                or not output.affected_components
                or not output.gap_analysis
            ):
                raise InvalidDiscoveryOutputError(
                    "ENHANCEMENT analysis requires AS-IS summary, affected components, and gaps."
                )
        return result
