from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agents.solution_analyst import (
    InvalidSolutionOutputError,
    SolutionAgentOutput,
    SolutionAnalyst,
    SolutionAnalystConfig,
)
from app.core.errors import (
    AgentExecutionError,
    SolutionWorkflowConflictError,
    TechnicalDesignBlockedError,
)
from app.domain.analysis import RequirementReadiness
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.projects import ProjectStatus, ProjectType
from app.domain.solution import SolutionApprovalAction, SolutionWorkflowStatus
from app.models.analysis import AgentExecution
from app.models.artifact import Artifact, ArtifactVersion
from app.models.solution import SolutionApproval, SolutionWorkflow
from app.schemas.solution import SolutionApprovalRequest
from app.services.llm import LLMResult, LLMUsage
from app.services.solution_analysis import SolutionAnalysisService


def solution_output(summary: str = "Tiered functional approval") -> SolutionAgentOutput:
    return SolutionAgentOutput(
        summary=summary,
        scope=["Route approval by amount tier."],
        out_of_scope=["Accounting settlement."],
        actors=["Requester", "Manager"],
        functional_requirements=["Determine the required approver from the amount."],
        business_rules=["High-value requests require an additional approver."],
        proposed_process=["Requester submits; system routes; approver decides."],
        alternative_flow=["Requester withdraws before a decision."],
        exception_flow=["Unavailable approver is escalated."],
        dependencies=["Approval authority matrix."],
        integration_requirements=["Read requester organization context."],
        data_requirements=["Amount, requester, approver, decision timestamp."],
        assumptions=["Authority matrix is maintained by the business."],
        risks=["Incorrect thresholds can misroute approvals."],
        as_is=["One manager approves every request."],
        gap=["No amount-based routing exists."],
        to_be=["Requests follow the applicable approval tier."],
    )


class QueueLLM:
    def __init__(self, outputs: list[object]) -> None:
        self.outputs = outputs
        self.requests = []

    async def generate_structured(self, request, _schema):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        next_output = self.outputs.pop(0)
        if isinstance(next_output, Exception):
            raise next_output
        return LLMResult(
            output=next_output,
            response_id=f"solution-{len(self.requests)}",
            model=request.model,
            usage=LLMUsage(input_tokens=40, output_tokens=80, total_tokens=120),
        )


class FakeSolutionRepository:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.project = SimpleNamespace(
            id=uuid4(),
            name="Approval enhancement",
            description="Improve approval controls",
            project_type=ProjectType.ENHANCEMENT,
            business_objective="Reduce risk",
            status=ProjectStatus.READY_FOR_ANALYSIS,
            context=SimpleNamespace(
                current_flow="Requester submits; manager approves",
                current_actors="Requester, manager",
                current_rules="One manager approves every request",
                current_problem="High values need more control",
                requested_change="Add tiered approval",
                constraints=None,
                notes=None,
            ),
        )
        self.requirement = SimpleNamespace(
            id=uuid4(),
            project_id=self.project.id,
            analysis_readiness=RequirementReadiness.READY,
        )
        self.artifacts: dict[ArtifactType, Artifact] = {}
        for kind, content in (
            (
                ArtifactType.REQUIREMENT_BASELINE,
                {
                    "feature": "Tiered approval",
                    "business_objective": "Reduce risk",
                    "problem_statement": "High values need more control",
                    "actors": ["Requester", "Manager"],
                    "known_requirements": ["Route based on amount"],
                    "business_rules": [],
                    "constraints": [],
                    "dependencies": [],
                    "assumptions": [],
                    "unknown_information": [],
                    "readiness": "READY",
                    "clarification_questions": [],
                    "blocked_reason": "",
                },
            ),
            (
                ArtifactType.RESEARCH,
                {
                    "objective": "Review approval patterns",
                    "common_practices": ["Use explicit authority tiers"],
                    "comparable_workflows": [],
                    "common_metadata": [],
                    "ux_patterns": [],
                    "technical_considerations": [],
                    "risks": [],
                    "sources": [],
                    "open_questions": [],
                },
            ),
        ):
            self.artifacts[kind] = Artifact(
                id=uuid4(),
                project_id=self.project.id,
                requirement_id=self.requirement.id,
                artifact_type=kind,
                current_version=1,
                status=ArtifactStatus.VALIDATED,
                created_at=now,
                updated_at=now,
                versions=[
                    ArtifactVersion(
                        id=uuid4(),
                        version=1,
                        content_json=content,
                        created_by="TEST",
                        created_at=now,
                    )
                ],
            )
        self.workflow: SolutionWorkflow | None = None
        self.approvals: list[SolutionApproval] = []
        self.executions: list[AgentExecution] = []

    async def get_project(self, project_id):  # type: ignore[no-untyped-def]
        return self.project if project_id == self.project.id else None

    async def get_requirement(self, project_id, requirement_id):  # type: ignore[no-untyped-def]
        return (
            self.requirement
            if (project_id, requirement_id) == (self.project.id, self.requirement.id)
            else None
        )

    async def get_artifact(self, _project_id, _requirement_id, artifact_type, **_kwargs):  # type: ignore[no-untyped-def]
        return self.artifacts.get(artifact_type)

    async def get_artifact_by_id(
        self,
        _project_id,
        _requirement_id,
        artifact_id,  # type: ignore[no-untyped-def]
    ):
        return next((item for item in self.artifacts.values() if item.id == artifact_id), None)

    async def get_workflow(self, _project_id, _requirement_id, **_kwargs):  # type: ignore[no-untyped-def]
        return self.workflow

    async def list_workflows(self, _project_id):  # type: ignore[no-untyped-def]
        return [self.workflow] if self.workflow else []

    def add(self, value):  # type: ignore[no-untyped-def]
        if isinstance(value, AgentExecution):
            self.executions.append(value)
        elif isinstance(value, Artifact):
            self.artifacts[value.artifact_type] = value
        elif isinstance(value, SolutionWorkflow):
            self.workflow = value
        elif isinstance(value, SolutionApproval):
            self.approvals.append(value)

    def _hydrate(self) -> None:
        now = datetime.now(timezone.utc)
        for execution in self.executions:
            execution.id = execution.id or uuid4()
            execution.created_at = execution.created_at or now
            execution.updated_at = execution.updated_at or now
        for artifact in self.artifacts.values():
            artifact.id = artifact.id or uuid4()
            artifact.created_at = artifact.created_at or now
            artifact.updated_at = artifact.updated_at or now
            for version in artifact.versions:
                version.id = version.id or uuid4()
                version.created_at = version.created_at or now
        if self.workflow:
            self.workflow.id = self.workflow.id or uuid4()
            self.workflow.created_at = self.workflow.created_at or now
            self.workflow.updated_at = now
            self.workflow.approvals = self.approvals
        for approval in self.approvals:
            approval.id = approval.id or uuid4()
            approval.created_at = approval.created_at or now

    async def flush(self) -> None:
        self._hydrate()

    async def commit(self) -> None:
        self._hydrate()

    async def rollback(self) -> None:
        pass

    async def refresh_artifact(self, _artifact) -> None:  # type: ignore[no-untyped-def]
        self._hydrate()

    async def refresh_workflow(self, _workflow) -> None:  # type: ignore[no-untyped-def]
        self._hydrate()


def make_service(repository: FakeSolutionRepository):
    llm = QueueLLM([solution_output(), solution_output("Revised tiered approval")])
    agent = SolutionAnalyst(
        llm, SolutionAnalystConfig(model="configured-solution-model", max_output_tokens=2000)
    )
    return SolutionAnalysisService(repository, agent), llm


@pytest.mark.asyncio
async def test_solution_waits_for_approval_revision_versions_and_approval_unlocks_design() -> None:
    repository = FakeSolutionRepository()
    service, llm = make_service(repository)

    created = await service.generate(repository.project.id, repository.requirement.id)
    assert created.workflow.status == SolutionWorkflowStatus.WAITING_USER_APPROVAL
    assert created.workflow.current_version == 1
    with pytest.raises(TechnicalDesignBlockedError):
        await service.ensure_technical_design_allowed(
            repository.project.id, repository.requirement.id
        )

    revised = await service.act(
        repository.project.id,
        repository.requirement.id,
        SolutionApprovalRequest(
            action=SolutionApprovalAction.REQUEST_REVISION,
            note="Clarify escalation behavior.",
            expected_version=1,
        ),
    )
    assert revised.status == SolutionWorkflowStatus.WAITING_USER_APPROVAL
    assert revised.current_version == 2
    assert "revision_note" in llm.requests[1].user_prompt
    assert len(repository.artifacts[ArtifactType.SOLUTION].versions) == 2

    approved = await service.act(
        repository.project.id,
        repository.requirement.id,
        SolutionApprovalRequest(action=SolutionApprovalAction.APPROVE, expected_version=2),
    )
    assert approved.status == SolutionWorkflowStatus.APPROVED
    assert approved.technical_design_allowed is True
    assert repository.artifacts[ArtifactType.SOLUTION].status == ArtifactStatus.VALIDATED
    assert [item.action for item in repository.approvals] == [
        SolutionApprovalAction.REQUEST_REVISION,
        SolutionApprovalAction.APPROVE,
    ]
    await service.ensure_technical_design_allowed(repository.project.id, repository.requirement.id)

    artifact = repository.artifacts[ArtifactType.SOLUTION]
    artifact.versions.append(
        ArtifactVersion(
            id=uuid4(),
            version=3,
            content_json=solution_output("Unapproved manual version").model_dump(mode="json"),
            created_by="USER",
            created_at=datetime.now(timezone.utc),
        )
    )
    artifact.current_version = 3
    with pytest.raises(TechnicalDesignBlockedError):
        await service.ensure_technical_design_allowed(
            repository.project.id, repository.requirement.id
        )


@pytest.mark.asyncio
async def test_reject_closes_workflow_and_stale_version_is_refused() -> None:
    repository = FakeSolutionRepository()
    service, _llm = make_service(repository)
    await service.generate(repository.project.id, repository.requirement.id)

    with pytest.raises(SolutionWorkflowConflictError):
        await service.act(
            repository.project.id,
            repository.requirement.id,
            SolutionApprovalRequest(action=SolutionApprovalAction.APPROVE, expected_version=99),
        )

    rejected = await service.act(
        repository.project.id,
        repository.requirement.id,
        SolutionApprovalRequest(
            action=SolutionApprovalAction.REJECT,
            note="The proposed scope is not acceptable.",
            expected_version=1,
        ),
    )
    assert rejected.status == SolutionWorkflowStatus.REJECTED
    assert rejected.technical_design_allowed is False


@pytest.mark.asyncio
async def test_failed_revision_preserves_note_and_can_be_retried() -> None:
    repository = FakeSolutionRepository()
    llm = QueueLLM(
        [solution_output(), RuntimeError("provider unavailable"), solution_output("Recovered")]
    )
    agent = SolutionAnalyst(
        llm, SolutionAnalystConfig(model="configured-model", max_output_tokens=1000)
    )
    service = SolutionAnalysisService(repository, agent)
    await service.generate(repository.project.id, repository.requirement.id)

    with pytest.raises(AgentExecutionError):
        await service.act(
            repository.project.id,
            repository.requirement.id,
            SolutionApprovalRequest(
                action=SolutionApprovalAction.REQUEST_REVISION,
                note="Preserve this note.",
                expected_version=1,
            ),
        )
    assert repository.workflow is not None
    assert repository.workflow.status == SolutionWorkflowStatus.REVISION_REQUESTED
    assert len(repository.approvals) == 1

    recovered = await service.retry_revision(repository.project.id, repository.requirement.id)
    assert recovered.workflow.status == SolutionWorkflowStatus.WAITING_USER_APPROVAL
    assert recovered.workflow.current_version == 2
    assert len(repository.approvals) == 1


@pytest.mark.asyncio
async def test_enhancement_solution_requires_as_is_gap_and_to_be() -> None:
    invalid = solution_output().model_copy(update={"as_is": []})
    llm = QueueLLM([invalid])
    agent = SolutionAnalyst(
        llm, SolutionAnalystConfig(model="configured-model", max_output_tokens=1000)
    )
    request = agent.build_request(SimpleNamespace(model_dump=lambda **_: {}))  # type: ignore[arg-type]
    with pytest.raises(InvalidSolutionOutputError):
        await agent.analyze(request, ProjectType.ENHANCEMENT)


def test_revision_note_is_required() -> None:
    with pytest.raises(ValidationError):
        SolutionApprovalRequest(
            action=SolutionApprovalAction.REQUEST_REVISION,
            note="  ",
            expected_version=1,
        )
