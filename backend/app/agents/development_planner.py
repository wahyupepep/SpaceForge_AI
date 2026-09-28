from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.artifacts.schemas import DevelopmentTaskContent
from app.domain.artifacts import ArtifactType
from app.services.llm import LLMRequest, LLMResult, LLMService


@dataclass(frozen=True)
class DevelopmentPlannerConfig:
    model: str
    max_output_tokens: int
    temperature: Optional[float] = None


class DevelopmentPlannerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_context: dict
    requirement_baseline: dict
    research: dict
    existing_system_analysis: Optional[dict] = None
    solution: dict
    process_flow: dict
    ui_prototype: dict
    database_design: dict
    api_specification: dict
    test_scenarios: dict
    acceptance_criteria: dict
    source_versions: dict[str, int]


class DevelopmentPlannerOutput(DevelopmentTaskContent):
    @model_validator(mode="after")
    def validate_dependency_graph(self) -> DevelopmentPlannerOutput:
        if not self.tasks:
            raise ValueError("at least one development task is required")
        ids = [task.id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("development task ids must be unique")
        known = set(ids)
        for task in self.tasks:
            if task.id in task.dependency:
                raise ValueError(f"task {task.id} cannot depend on itself")
            unknown = set(task.dependency) - known
            if unknown:
                raise ValueError(f"task {task.id} has unknown dependencies: {sorted(unknown)}")
            if not task.scope or not task.technical_notes:
                raise ValueError(f"task {task.id} requires scope and technical notes")
            if not task.acceptance_criteria or not task.reference_artifact:
                raise ValueError(
                    f"task {task.id} requires acceptance criteria and artifact references"
                )
        if set(self.execution_order) != known or len(self.execution_order) != len(ids):
            raise ValueError("execution_order must contain every task id exactly once")
        positions = {task_id: index for index, task_id in enumerate(self.execution_order)}
        for task in self.tasks:
            if any(positions[item] >= positions[task.id] for item in task.dependency):
                raise ValueError("execution_order must place every dependency before its task")
        allowed = {
            ArtifactType.REQUIREMENT_BASELINE,
            ArtifactType.RESEARCH,
            ArtifactType.EXISTING_SYSTEM_ANALYSIS,
            ArtifactType.SOLUTION,
            ArtifactType.PROCESS_FLOW,
            ArtifactType.UI_PROTOTYPE,
            ArtifactType.DATABASE_DESIGN,
            ArtifactType.API_SPECIFICATION,
            ArtifactType.TEST_SCENARIO,
            ArtifactType.ACCEPTANCE_CRITERIA,
        }
        for task in self.tasks:
            if any(reference not in allowed for reference in task.reference_artifact):
                raise ValueError(f"task {task.id} references an unsupported artifact")
        return self


SYSTEM_PROMPT = "\n".join(
    (
        "You are the Development Planner for SpecForge AI.",
        "Transform only the supplied approved and quality-passed specifications into an ordered "
        "developer task plan. Never add, reinterpret, or expand product requirements.",
        "Each task must have a stable id, title, workstream, objective, concrete scope, one exact "
        "requirement copied from the supplied requirement_authority, technical notes, dependency "
        "task ids, existing acceptance-criteria ids, and source artifact types.",
        "Build an acyclic dependency graph and a topological execution_order. Prefer the natural "
        "sequence Database Migration -> Backend API -> Frontend -> Integration -> QA when those "
        "workstreams are actually required by the specification.",
        "Tasks describe implementation work but must not contain source code, migrations, or new "
        "solution decisions. Do not create new acceptance criteria.",
        "Return only the structured output requested by the schema.",
    )
)


class DevelopmentPlannerAgent:
    name = "DEVELOPMENT_PLANNER"

    def __init__(self, llm: LLMService, config: DevelopmentPlannerConfig) -> None:
        self._llm = llm
        self._config = config

    def build_request(self, input_data: DevelopmentPlannerInput) -> LLMRequest:
        payload = input_data.model_dump(mode="json")
        baseline = input_data.requirement_baseline
        solution = input_data.solution
        payload["requirement_authority"] = list(
            dict.fromkeys(
                baseline.get("known_requirements", [])
                + baseline.get("business_rules", [])
                + solution.get("functional_requirements", [])
                + solution.get("business_rules", [])
            )
        )
        payload["acceptance_criteria_ids"] = [
            item.get("id") for item in input_data.acceptance_criteria.get("criteria", [])
        ]
        return LLMRequest(
            agent_name=self.name,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
            model=self._config.model,
            max_output_tokens=self._config.max_output_tokens,
            temperature=self._config.temperature,
        )

    async def analyze(self, request: LLMRequest) -> LLMResult[DevelopmentPlannerOutput]:
        return await self._llm.generate_structured(request, DevelopmentPlannerOutput)
