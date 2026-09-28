from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.projects import ProjectType
from app.services.llm import LLMRequest, LLMResult, LLMService


class SolutionAgentInput(BaseModel):
    project_type: ProjectType
    project_context: dict
    requirement_baseline: dict
    research_artifact: dict
    existing_system_analysis: Optional[dict] = None
    previous_solution: Optional[dict] = None
    revision_note: Optional[str] = None


class SolutionAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    scope: list[str]
    out_of_scope: list[str]
    actors: list[str]
    functional_requirements: list[str]
    business_rules: list[str]
    proposed_process: list[str]
    alternative_flow: list[str]
    exception_flow: list[str]
    dependencies: list[str]
    integration_requirements: list[str]
    data_requirements: list[str]
    assumptions: list[str]
    risks: list[str]
    as_is: list[str]
    gap: list[str]
    to_be: list[str]


class InvalidSolutionOutputError(RuntimeError):
    pass


@dataclass(frozen=True)
class SolutionAnalystConfig:
    model: str
    max_output_tokens: int
    temperature: Optional[float] = None


SOLUTION_SYSTEM_PROMPT = "\n".join(
    (
        "You are the Solution Analyst for SpaceForge AI.",
        "Use only the supplied Project Context, Requirement Baseline, Research Artifact, "
        "and Existing System Analysis when present.",
        "Produce a functional solution: scope, out of scope, actors, functional requirements, "
        "business rules, proposed process, alternative and exception flows, dependencies, "
        "integration requirements, data requirements, assumptions, and risks.",
        "Do not create a database design, API specification, UI design, implementation plan, "
        "or select a technical architecture. Keep data and integration requirements functional.",
        "For ENHANCEMENT, preserve the supplied AS-IS and explicitly provide AS-IS, GAP, and "
        "TO-BE. Never replace or rewrite AS-IS as if it were TO-BE.",
        "If a previous solution and revision note are supplied, revise that solution to address "
        "the note while preserving supported facts and AS-IS. Return a complete replacement "
        "artifact, not a patch.",
        "Do not invent facts. Put uncertain items in assumptions or risks.",
        "Return only the structured output requested by the schema.",
    )
)


class SolutionAnalyst:
    name = "SOLUTION_ANALYST"

    def __init__(self, llm: LLMService, config: SolutionAnalystConfig) -> None:
        self._llm = llm
        self._config = config

    def build_request(self, input_data: SolutionAgentInput) -> LLMRequest:
        return LLMRequest(
            agent_name=self.name,
            system_prompt=SOLUTION_SYSTEM_PROMPT,
            user_prompt=json.dumps(input_data.model_dump(mode="json"), ensure_ascii=False),
            model=self._config.model,
            max_output_tokens=self._config.max_output_tokens,
            temperature=self._config.temperature,
        )

    async def analyze(
        self, request: LLMRequest, project_type: ProjectType
    ) -> LLMResult[SolutionAgentOutput]:
        result = await self._llm.generate_structured(request, SolutionAgentOutput)
        if project_type == ProjectType.ENHANCEMENT:
            output = result.output
            if not output.as_is or not output.gap or not output.to_be:
                raise InvalidSolutionOutputError(
                    "ENHANCEMENT solution requires non-empty AS-IS, GAP, and TO-BE."
                )
        return result
