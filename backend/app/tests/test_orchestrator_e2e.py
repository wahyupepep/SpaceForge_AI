from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.errors import OrchestratorConflictError
from app.domain.analysis import RequirementReadiness
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.handoff import HandoffWorkflowStatus
from app.domain.orchestrator import OrchestratorStage, OrchestratorStatus
from app.domain.projects import ProjectStatus, ProjectType
from app.domain.quality import QualityWorkflowStatus
from app.domain.solution import SolutionWorkflowStatus
from app.models.orchestrator import OrchestratorExecution, OrchestratorWorkflow
from app.services.orchestrator import SAOrchestratorService


class OrchestratorMemoryRepository:
    def __init__(self) -> None:
        self.project = SimpleNamespace(
            id=uuid4(),
            project_type=ProjectType.ENHANCEMENT,
            status=ProjectStatus.READY_FOR_ANALYSIS,
            context=SimpleNamespace(
                current_flow="Requester submits, manager approves manually.",
                current_actors="Requester, Manager",
                current_rules="All amounts use one approver.",
                current_problem="High-value requests need stronger control.",
                requested_change="Route approval by nominal amount.",
            ),
        )
        self.requirement = SimpleNamespace(
            id=uuid4(), project_id=self.project.id, analysis_readiness=None
        )
        self.workflow: OrchestratorWorkflow | None = None
        self.artifacts: dict[ArtifactType, SimpleNamespace] = {}
        self.solution = None
        self.quality = None
        self.handoff = None

    async def get_project(self, project_id):  # type: ignore[no-untyped-def]
        return self.project if project_id == self.project.id else None

    async def get_requirement(self, project_id, requirement_id):  # type: ignore[no-untyped-def]
        if project_id == self.project.id and requirement_id == self.requirement.id:
            return self.requirement
        return None

    async def get_workflow(self, _project_id, _requirement_id, **_kwargs):  # type: ignore[no-untyped-def]
        return self.workflow

    async def list_project_workflows(self, _project_id):  # type: ignore[no-untyped-def]
        return [self.workflow] if self.workflow else []

    async def get_execution(self, execution_id):  # type: ignore[no-untyped-def]
        if self.workflow is None:
            return None
        return next(
            (item for item in self.workflow.executions if item.id == execution_id), None
        )

    async def try_acquire_lease(self, _workflow_id, run_id, lease_expires_at):  # type: ignore[no-untyped-def]
        assert self.workflow is not None
        self.workflow.active_run_id = run_id
        self.workflow.lease_expires_at = lease_expires_at
        return True

    async def release_lease(self, _workflow_id, run_id):  # type: ignore[no-untyped-def]
        assert self.workflow is not None
        if self.workflow.active_run_id == run_id:
            self.workflow.active_run_id = None
            self.workflow.lease_expires_at = None

    async def list_artifacts(self, _project_id, _requirement_id):  # type: ignore[no-untyped-def]
        return list(self.artifacts.values())

    async def get_solution_workflow(self, _project_id, _requirement_id):  # type: ignore[no-untyped-def]
        return self.solution

    async def get_quality_workflow(self, _project_id, _requirement_id):  # type: ignore[no-untyped-def]
        return self.quality

    async def get_handoff_workflow(self, _project_id, _requirement_id):  # type: ignore[no-untyped-def]
        return self.handoff

    def add(self, value):  # type: ignore[no-untyped-def]
        if isinstance(value, OrchestratorWorkflow):
            self.workflow = value
        elif isinstance(value, OrchestratorExecution):
            assert self.workflow is not None
            self.workflow.executions.append(value)

    async def commit(self) -> None:
        now = datetime.now(timezone.utc)
        assert self.workflow is not None
        self.workflow.id = self.workflow.id or uuid4()
        self.workflow.created_at = self.workflow.created_at or now
        self.workflow.updated_at = now
        for execution in self.workflow.executions:
            execution.id = execution.id or uuid4()
            execution.started_at = execution.started_at or now

    async def rollback(self) -> None:
        return None

    async def refresh_workflow(self, _workflow) -> None:  # type: ignore[no-untyped-def]
        return None

    def add_artifact(self, artifact_type: ArtifactType) -> None:
        current = self.artifacts.get(artifact_type)
        self.artifacts[artifact_type] = SimpleNamespace(
            artifact_type=artifact_type,
            current_version=(current.current_version + 1 if current else 1),
            status=ArtifactStatus.VALIDATED,
        )


@pytest.mark.asyncio
async def test_enhancement_nominal_approval_resumes_through_all_gates() -> None:
    repository = OrchestratorMemoryRepository()
    requirement_service = AsyncMock()
    discovery_service = AsyncMock()
    solution_service = AsyncMock()
    design_service = AsyncMock()
    quality_service = AsyncMock()
    handoff_service = AsyncMock()

    async def analyze(*_args):  # type: ignore[no-untyped-def]
        repository.requirement.analysis_readiness = RequirementReadiness.READY
        repository.add_artifact(ArtifactType.REQUIREMENT_BASELINE)
        return SimpleNamespace(readiness=RequirementReadiness.READY)

    async def research(*_args):  # type: ignore[no-untyped-def]
        repository.add_artifact(ArtifactType.RESEARCH)

    async def existing(*_args):  # type: ignore[no-untyped-def]
        repository.add_artifact(ArtifactType.EXISTING_SYSTEM_ANALYSIS)

    async def solution(*_args):  # type: ignore[no-untyped-def]
        repository.add_artifact(ArtifactType.SOLUTION)
        repository.solution = SimpleNamespace(
            status=SolutionWorkflowStatus.WAITING_USER_APPROVAL
        )

    async def flow(*_args):  # type: ignore[no-untyped-def]
        repository.add_artifact(ArtifactType.PROCESS_FLOW)

    async def technical(*_args):  # type: ignore[no-untyped-def]
        repository.add_artifact(ArtifactType.DATABASE_DESIGN)
        repository.add_artifact(ArtifactType.API_SPECIFICATION)

    async def prototype(*_args):  # type: ignore[no-untyped-def]
        repository.add_artifact(ArtifactType.UI_PROTOTYPE)

    async def qa(*_args):  # type: ignore[no-untyped-def]
        repository.add_artifact(ArtifactType.TEST_SCENARIO)
        repository.add_artifact(ArtifactType.ACCEPTANCE_CRITERIA)
        repository.quality = SimpleNamespace(
            status=QualityWorkflowStatus.READY_FOR_REVIEW,
            issues_json=[],
            revision_count=0,
        )

    review_count = 0

    async def review(*_args):  # type: ignore[no-untyped-def]
        nonlocal review_count
        review_count += 1
        if review_count == 1:
            repository.quality.status = QualityWorkflowStatus.REVISION_REQUIRED
            repository.quality.issues_json = [{"artifact": "PROCESS_FLOW"}]
        else:
            repository.quality.status = QualityWorkflowStatus.PASSED
            repository.quality.issues_json = []

    async def revise(*_args):  # type: ignore[no-untyped-def]
        repository.add_artifact(ArtifactType.PROCESS_FLOW)
        repository.quality.status = QualityWorkflowStatus.READY_FOR_REVIEW
        repository.quality.revision_count += 1

    async def plan(*_args):  # type: ignore[no-untyped-def]
        repository.add_artifact(ArtifactType.DEVELOPMENT_TASK)
        repository.handoff = SimpleNamespace(status=HandoffWorkflowStatus.TASKS_READY)

    requirement_service.analyze.side_effect = analyze
    discovery_service.run_research.side_effect = research
    discovery_service.analyze_existing_system.side_effect = existing
    solution_service.generate.side_effect = solution
    design_service.run_flow.side_effect = flow
    design_service.run_technical_architecture.side_effect = technical
    design_service.run_ui_prototype.side_effect = prototype
    quality_service.run_qa.side_effect = qa
    quality_service.run_review.side_effect = review
    quality_service.revise.side_effect = revise
    handoff_service.plan.side_effect = plan

    service = SAOrchestratorService(
        repository,
        requirement_service,
        discovery_service,
        solution_service,
        design_service,
        quality_service,
        handoff_service,
        900,
    )
    waiting_approval = await service.start(
        repository.project.id, repository.requirement.id, []
    )
    assert waiting_approval.current_stage == OrchestratorStage.USER_APPROVAL
    assert waiting_approval.pending_user_action == "APPROVE_SOLUTION"
    assert ArtifactType.EXISTING_SYSTEM_ANALYSIS.value in waiting_approval.artifact_status

    repository.solution.status = SolutionWorkflowStatus.APPROVED
    waiting_handoff = await service.resume(repository.project.id, repository.requirement.id)
    assert waiting_handoff.current_stage == OrchestratorStage.HANDOFF_READY
    assert waiting_handoff.pending_user_action == "PREVIEW_AND_EXPORT_HANDOFF"
    assert waiting_handoff.revision_history[0]["artifact"] == "PROCESS_FLOW"

    repository.handoff.status = HandoffWorkflowStatus.PACKAGE_READY
    completed = await service.resume(repository.project.id, repository.requirement.id)
    assert completed.status == OrchestratorStatus.COMPLETED
    assert completed.current_stage == OrchestratorStage.COMPLETED
    assert completed.pending_user_action is None
    assert len(completed.executions) >= 14


@pytest.mark.asyncio
async def test_orchestrator_rejects_duplicate_active_execution() -> None:
    repository = OrchestratorMemoryRepository()
    workflow = OrchestratorWorkflow(
        project_id=repository.project.id,
        requirement_id=repository.requirement.id,
        current_stage=OrchestratorStage.USER_APPROVAL,
        status=OrchestratorStatus.WAITING_USER_ACTION,
        completed_stages=[],
        artifact_status={},
        revision_history=[],
        state_json={},
    )
    repository.add(workflow)
    await repository.commit()
    repository.try_acquire_lease = AsyncMock(return_value=False)  # type: ignore[method-assign]
    service = SAOrchestratorService(
        repository,
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        900,
    )

    with pytest.raises(OrchestratorConflictError):
        await service.resume(repository.project.id, repository.requirement.id)
