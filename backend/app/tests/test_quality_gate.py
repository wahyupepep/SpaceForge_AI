from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.design import (
    DesignAgentConfig,
    FlowDesignerAgent,
    TechnicalArchitectAgent,
    UIPrototypeAgent,
)
from app.agents.quality import (
    QAAnalystAgent,
    QAAnalystOutput,
    QualityAgentConfig,
    ReviewIssue,
    SAReviewerAgent,
    SAReviewerOutput,
)
from app.artifacts.schemas import (
    AcceptanceCriteriaContent,
    AcceptanceCriterionContent,
)
from app.artifacts.schemas import (
    TestCaseContent as ScenarioCase,
)
from app.artifacts.schemas import (
    TestScenarioContent as ScenarioArtifact,
)
from app.core.errors import MaximumRevisionReachedError, QualityGateBlockedError
from app.domain.artifacts import ArtifactType
from app.domain.quality import (
    QualityWorkflowStatus,
    ReviewDecision,
    ReviewSeverity,
)
from app.domain.quality import (
    TestCategory as ScenarioCategory,
)
from app.models.handoff import HandoffPackageVersion, HandoffWorkflow
from app.models.quality import QualityWorkflow
from app.services.artifacts import ArtifactService
from app.services.design_generation import DesignGenerationService
from app.services.quality_gate import QualityGateService
from app.tests.test_design_generation import (
    MemoryStorage,
    approve_solution,
    flow_output,
    technical_output,
    ui_output,
)
from app.tests.test_solution_analyst import FakeSolutionRepository, QueueLLM


class FakeQualityRepository(FakeSolutionRepository):
    def __init__(self) -> None:
        super().__init__()
        self.quality_workflow: QualityWorkflow | None = None
        self.handoff_workflow: HandoffWorkflow | None = None

    async def get_quality_workflow(self, _project_id, _requirement_id, **_kwargs):  # type: ignore[no-untyped-def]
        return self.quality_workflow

    async def list_quality_workflows(self, _project_id):  # type: ignore[no-untyped-def]
        return [self.quality_workflow] if self.quality_workflow else []

    async def refresh_quality_workflow(self, _workflow) -> None:  # type: ignore[no-untyped-def]
        self._hydrate()

    async def get_handoff_workflow(self, _project_id, _requirement_id, **_kwargs):  # type: ignore[no-untyped-def]
        return self.handoff_workflow

    async def get_package(self, _project_id, _requirement_id, version):  # type: ignore[no-untyped-def]
        if not self.handoff_workflow:
            return None
        return next(
            (item for item in self.handoff_workflow.packages if item.version == version), None
        )

    async def refresh_handoff_workflow(self, _workflow) -> None:  # type: ignore[no-untyped-def]
        self._hydrate()

    def add(self, value):  # type: ignore[no-untyped-def]
        if isinstance(value, QualityWorkflow):
            self.quality_workflow = value
        elif isinstance(value, HandoffWorkflow):
            self.handoff_workflow = value
        else:
            super().add(value)

    def _hydrate(self) -> None:
        super()._hydrate()
        if self.quality_workflow:
            now = datetime.now(timezone.utc)
            self.quality_workflow.id = self.quality_workflow.id or uuid4()
            self.quality_workflow.created_at = self.quality_workflow.created_at or now
            self.quality_workflow.updated_at = now
        if self.handoff_workflow:
            now = datetime.now(timezone.utc)
            self.handoff_workflow.id = self.handoff_workflow.id or uuid4()
            self.handoff_workflow.created_at = self.handoff_workflow.created_at or now
            self.handoff_workflow.updated_at = now
            for package in self.handoff_workflow.packages:
                if isinstance(package, HandoffPackageVersion):
                    package.id = package.id or uuid4()
                    package.created_at = package.created_at or now


def qa_output() -> QAAnalystOutput:
    cases = [
        ScenarioCase(
            id=f"TC-{index:03d}",
            category=category,
            scenario=f"Verify {category.value.lower()} behavior",
            precondition="An approval request exists.",
            steps=["Open the request.", "Perform the applicable action."],
            expected_result="The documented rule is enforced.",
            related_requirement="Route based on amount",
        )
        for index, category in enumerate(ScenarioCategory, start=1)
    ]
    return QAAnalystOutput(
        test_scenario=ScenarioArtifact(
            summary="Tiered approval coverage",
            test_cases=cases,
            requirement_traceability=["Route based on amount -> TC-001..TC-008"],
        ),
        acceptance_criteria=AcceptanceCriteriaContent(
            criteria=[
                AcceptanceCriterionContent(
                    id="AC-001",
                    requirement_ref="Route based on amount",
                    given="A requester enters a valid amount",
                    when="The request is submitted",
                    then="The request is routed to the matching approval tier",
                )
            ],
            requirement_traceability=["Route based on amount -> AC-001"],
        ),
    )


def revision_review() -> SAReviewerOutput:
    return SAReviewerOutput(
        decision=ReviewDecision.REVISION_REQUIRED,
        summary="The flow omits a permission denial path.",
        issues=[
            ReviewIssue(
                artifact=ArtifactType.PROCESS_FLOW,
                issue="Permission denial is missing.",
                severity=ReviewSeverity.HIGH,
                reason="The API requires an authorized active approver.",
                recommended_revision="Add an unauthorized-actor exception path.",
            )
        ],
    )


def pass_review() -> SAReviewerOutput:
    return SAReviewerOutput(
        decision=ReviewDecision.PASS,
        summary="All artifacts are consistent and traceable.",
        issues=[],
    )


async def make_quality_service(max_revisions: int = 5):
    repository = FakeQualityRepository()
    await approve_solution(repository)
    storage = MemoryStorage()
    design_config = DesignAgentConfig(model="design-model", max_output_tokens=12000)
    design_service = DesignGenerationService(
        repository,
        FlowDesignerAgent(QueueLLM([flow_output(), flow_output()]), design_config),
        UIPrototypeAgent(QueueLLM([ui_output()]), design_config),
        TechnicalArchitectAgent(QueueLLM([technical_output()]), design_config),
        storage,
    )
    await design_service.run_flow(repository.project.id, repository.requirement.id)
    await design_service.run_technical_architecture(
        repository.project.id, repository.requirement.id
    )
    await design_service.run_ui_prototype(repository.project.id, repository.requirement.id)
    config = QualityAgentConfig(model="quality-model", max_output_tokens=8000)
    service = QualityGateService(
        repository,
        QAAnalystAgent(QueueLLM([qa_output()]), config),
        SAReviewerAgent(QueueLLM([revision_review(), pass_review()]), config),
        design_service,
        storage,
        max_revisions,
    )
    return repository, service


@pytest.mark.asyncio
async def test_quality_gate_routes_revision_and_only_pass_unlocks_handoff() -> None:
    repository, service = await make_quality_service()

    qa = await service.run_qa(repository.project.id, repository.requirement.id)
    assert qa.workflow.status == QualityWorkflowStatus.READY_FOR_REVIEW
    assert {item.artifact_type for item in qa.artifacts} == {
        ArtifactType.TEST_SCENARIO,
        ArtifactType.ACCEPTANCE_CRITERIA,
    }

    review = await service.run_review(repository.project.id, repository.requirement.id)
    assert review.workflow.status == QualityWorkflowStatus.REVISION_REQUIRED
    assert review.workflow.development_handoff_allowed is False

    revised = await service.revise(
        repository.project.id,
        repository.requirement.id,
        ArtifactType.PROCESS_FLOW,
    )
    assert revised.workflow.revision_count == 1
    assert repository.artifacts[ArtifactType.PROCESS_FLOW].current_version == 2

    passed = await service.run_review(repository.project.id, repository.requirement.id)
    assert passed.workflow.status == QualityWorkflowStatus.PASSED
    assert passed.workflow.development_handoff_allowed is True

    repository.artifacts[ArtifactType.API_SPECIFICATION].current_version += 1
    stale = await service.get(repository.project.id, repository.requirement.id)
    assert stale.development_handoff_allowed is False


@pytest.mark.asyncio
async def test_quality_revision_guard_stops_infinite_loop() -> None:
    repository, service = await make_quality_service(max_revisions=0)
    await service.run_qa(repository.project.id, repository.requirement.id)
    await service.run_review(repository.project.id, repository.requirement.id)

    with pytest.raises(MaximumRevisionReachedError):
        await service.revise(
            repository.project.id,
            repository.requirement.id,
            ArtifactType.PROCESS_FLOW,
        )
    assert repository.quality_workflow is not None
    assert repository.quality_workflow.status == QualityWorkflowStatus.MAX_REVISIONS_REACHED


@pytest.mark.asyncio
async def test_development_task_requires_fresh_passing_snapshot() -> None:
    repository = AsyncMock()
    repository.get_quality_workflow.return_value = SimpleNamespace(
        status=QualityWorkflowStatus.PASSED,
        reviewed_versions={ArtifactType.REQUIREMENT_BASELINE.value: 1},
    )
    repository.get_requirement_artifacts.return_value = [
        SimpleNamespace(
            artifact_type=ArtifactType.REQUIREMENT_BASELINE,
            current_version=2,
        )
    ]
    service = ArtifactService(repository)

    with pytest.raises(QualityGateBlockedError):
        await service._ensure_quality_passed(  # noqa: SLF001
            repository.project_id,
            repository.requirement_id,
            ArtifactType.DEVELOPMENT_TASK,
        )
