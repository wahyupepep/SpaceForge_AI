from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.agents.development_planner import (
    DevelopmentPlannerAgent,
    DevelopmentPlannerConfig,
    DevelopmentPlannerOutput,
)
from app.artifacts.schemas import DevelopmentTaskItemContent
from app.domain.artifacts import ArtifactType
from app.domain.handoff import DevelopmentWorkstream, HandoffExportFormat, HandoffWorkflowStatus
from app.services.development_handoff import DevelopmentHandoffService
from app.tests.test_quality_gate import make_quality_service
from app.tests.test_solution_analyst import QueueLLM


def planner_output() -> DevelopmentPlannerOutput:
    tasks = [
        DevelopmentTaskItemContent(
            id="DEV-001",
            title="Create approval persistence",
            workstream=DevelopmentWorkstream.DATABASE,
            objective="Prepare persistence required by tiered approval.",
            scope=["Create the approved request and decision structures."],
            requirement="Route based on amount",
            technical_notes=["Follow DATABASE_DESIGN classifications and field contracts."],
            dependency=[],
            acceptance_criteria=["AC-001"],
            reference_artifact=[ArtifactType.DATABASE_DESIGN],
        ),
        DevelopmentTaskItemContent(
            id="DEV-002",
            title="Implement approval API",
            workstream=DevelopmentWorkstream.BACKEND,
            objective="Expose the approved workflow contract.",
            scope=["Implement the specified endpoints and authorization rules."],
            requirement="Route based on amount",
            technical_notes=["Follow API_SPECIFICATION validations and errors."],
            dependency=["DEV-001"],
            acceptance_criteria=["AC-001"],
            reference_artifact=[ArtifactType.API_SPECIFICATION],
        ),
        DevelopmentTaskItemContent(
            id="DEV-003",
            title="Build approval interface",
            workstream=DevelopmentWorkstream.FRONTEND,
            objective="Implement the reviewed approval screens.",
            scope=["Build screens and interactions represented by the prototype."],
            requirement="Route based on amount",
            technical_notes=["Use UI_PROTOTYPE as behavior reference."],
            dependency=["DEV-002"],
            acceptance_criteria=["AC-001"],
            reference_artifact=[ArtifactType.UI_PROTOTYPE],
        ),
        DevelopmentTaskItemContent(
            id="DEV-004",
            title="Integrate approval workflow",
            workstream=DevelopmentWorkstream.INTEGRATION,
            objective="Connect UI, API, and approval state transitions.",
            scope=["Integrate the reviewed end-to-end process."],
            requirement="Route based on amount",
            technical_notes=["Preserve PROCESS_FLOW alternative and exception paths."],
            dependency=["DEV-003"],
            acceptance_criteria=["AC-001"],
            reference_artifact=[ArtifactType.PROCESS_FLOW, ArtifactType.API_SPECIFICATION],
        ),
        DevelopmentTaskItemContent(
            id="DEV-005",
            title="Execute QA scenarios",
            workstream=DevelopmentWorkstream.QA,
            objective="Verify the implementation against reviewed scenarios.",
            scope=["Execute all test categories and record results."],
            requirement="Route based on amount",
            technical_notes=["Use TEST_SCENARIO without changing expected results."],
            dependency=["DEV-004"],
            acceptance_criteria=["AC-001"],
            reference_artifact=[
                ArtifactType.TEST_SCENARIO,
                ArtifactType.ACCEPTANCE_CRITERIA,
            ],
        ),
    ]
    return DevelopmentPlannerOutput(
        summary="Dependency-aware implementation plan",
        tasks=tasks,
        execution_order=[task.id for task in tasks],
        traceability=["Route based on amount -> DEV-001..DEV-005 -> AC-001"],
    )


@pytest.mark.asyncio
async def test_handoff_requires_preview_then_exports_all_formats() -> None:
    repository, quality_service = await make_quality_service()
    await quality_service.run_qa(repository.project.id, repository.requirement.id)
    await quality_service.run_review(repository.project.id, repository.requirement.id)
    await quality_service.revise(
        repository.project.id, repository.requirement.id, ArtifactType.PROCESS_FLOW
    )
    await quality_service.run_review(repository.project.id, repository.requirement.id)

    planner_llm = QueueLLM([planner_output()])
    planner = DevelopmentPlannerAgent(
        planner_llm,
        DevelopmentPlannerConfig(model="planner-model", max_output_tokens=8000),
    )
    service = DevelopmentHandoffService(
        repository,
        planner,
        quality_service._storage,  # noqa: SLF001
    )
    planned = await service.plan(repository.project.id, repository.requirement.id)

    assert planned.workflow.status == HandoffWorkflowStatus.TASKS_READY
    assert len(planned.workflow.task_artifact.content_json["tasks"]) == 5
    assert "requirement_authority" in planner_llm.requests[0].user_prompt

    generated = await service.generate_package(
        repository.project.id,
        repository.requirement.id,
        planned.workflow.current_task_version,
    )
    assert generated.status == HandoffWorkflowStatus.PACKAGE_READY
    assert generated.current_package is not None
    assert [section.number for section in generated.current_package.content_json.sections] == [
        f"{index:02d}" for index in range(1, 14)
    ]
    assert len(generated.current_package.content_json.trello_ready.cards) == 5

    exported_json = await service.download(
        repository.project.id,
        repository.requirement.id,
        1,
        HandoffExportFormat.JSON,
    )
    exported_markdown = await service.download(
        repository.project.id,
        repository.requirement.id,
        1,
        HandoffExportFormat.MARKDOWN,
    )
    exported_trello = await service.download(
        repository.project.id,
        repository.requirement.id,
        1,
        HandoffExportFormat.TRELLO,
    )
    assert len(json.loads(exported_json.content)["sections"]) == 13
    assert b"## 13 Development Tasks" in exported_markdown.content
    assert len(json.loads(exported_trello.content)["cards"]) == 5


def test_planner_rejects_dependency_cycle() -> None:
    task = planner_output().tasks[0]
    task.dependency = [task.id]
    with pytest.raises(ValidationError):
        DevelopmentPlannerOutput(
            summary="Invalid",
            tasks=[task],
            execution_order=[task.id],
            traceability=[],
        )
