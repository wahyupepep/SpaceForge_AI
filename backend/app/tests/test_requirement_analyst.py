from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.requirement_analyst import (
    InvalidAgentOutputError,
    RequirementAnalysisOutput,
    RequirementAnalystAgent,
    RequirementAnalystConfig,
    RequirementAnalystInput,
    RequirementBaselineAgentOutput,
)
from app.core.errors import AgentExecutionError, ClarificationPendingError, ServiceUnavailableError
from app.domain.analysis import AgentExecutionStatus, ClarificationStatus, RequirementReadiness
from app.domain.artifacts import ArtifactStatus
from app.domain.projects import ProjectStatus, ProjectType
from app.domain.requirements import RequirementStatus
from app.models.analysis import AgentExecution, RequirementClarification
from app.models.artifact import Artifact
from app.models.requirement import Requirement
from app.schemas.analysis import AnswerClarificationsRequest, ClarificationAnswerInput
from app.services.llm import LLMRequest, LLMResult, LLMUsage
from app.services.requirement_analysis import RequirementAnalysisService


def analysis_output(
    readiness: RequirementReadiness,
    questions: list[str] | None = None,
    blocked_reason: str = "",
) -> RequirementAnalysisOutput:
    return RequirementAnalysisOutput(
        baseline=RequirementBaselineAgentOutput(
            feature="Tiered approval",
            business_objective="Reduce approval risk",
            problem_statement="High-value approvals lack sufficient control",
            actors=["Requester", "Approver"],
            known_requirements=["Approval tier depends on amount"],
            business_rules=[],
            constraints=[],
            dependencies=[],
            assumptions=[],
            unknown_information=[],
        ),
        readiness=readiness,
        clarification_questions=questions or [],
        blocked_reason=blocked_reason,
    )


class QueueLLM:
    def __init__(self, outputs: list[RequirementAnalysisOutput]) -> None:
        self.outputs = outputs
        self.requests: list[LLMRequest] = []

    async def generate_structured(self, request, output_schema):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        return LLMResult(
            output=self.outputs.pop(0),
            response_id=f"response-{len(self.requests)}",
            model=request.model,
            usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        )


class FailingLLM:
    async def generate_structured(self, _request, _output_schema):  # type: ignore[no-untyped-def]
        raise RuntimeError("provider unavailable")


class FakeAnalysisRepository:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.project = SimpleNamespace(
            id=uuid4(),
            name="Approval",
            description="Improve approvals",
            project_type=ProjectType.ENHANCEMENT,
            business_objective="Reduce risk",
            status=ProjectStatus.READY_FOR_ANALYSIS,
            context=SimpleNamespace(
                current_flow="Requester submits; manager approves",
                current_actors="Requester, manager",
                current_rules="Manager approves all requests",
                current_problem="High values need more control",
                requested_change="Add approval tiers",
                constraints=None,
                notes=None,
            ),
        )
        self.requirement = Requirement(
            id=uuid4(),
            project_id=self.project.id,
            title="Tiered approval",
            raw_requirement="Add approval tiers based on amount.",
            business_objective="Reduce risk",
            actors=[],
            known_rules=[],
            constraints=[],
            dependencies=[],
            status=RequirementStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        self.artifact = None
        self.clarifications: list[RequirementClarification] = []
        self.executions: list[AgentExecution] = []

    async def get_project(self, project_id):  # type: ignore[no-untyped-def]
        return self.project if project_id == self.project.id else None

    async def get_requirement(self, project_id, requirement_id):  # type: ignore[no-untyped-def]
        if project_id == self.project.id and requirement_id == self.requirement.id:
            return self.requirement
        return None

    async def get_baseline_artifact(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return self.artifact

    async def list_clarifications(self, *_args):  # type: ignore[no-untyped-def]
        return self.clarifications

    async def list_pending_clarifications(self, *_args):  # type: ignore[no-untyped-def]
        return [item for item in self.clarifications if item.status == ClarificationStatus.PENDING]

    async def list_executions(self, *_args):  # type: ignore[no-untyped-def]
        return self.executions

    def add(self, value):  # type: ignore[no-untyped-def]
        if isinstance(value, Artifact):
            self.artifact = value
        elif isinstance(value, AgentExecution):
            self.executions.append(value)

    def add_all(self, values):  # type: ignore[no-untyped-def]
        self.clarifications.extend(values)

    def _hydrate(self) -> None:
        now = datetime.now(timezone.utc)
        for item in [*self.executions, *self.clarifications]:
            item.id = item.id or uuid4()
            item.created_at = item.created_at or now
            item.updated_at = now
        if self.artifact is not None:
            self.artifact.id = self.artifact.id or uuid4()
            self.artifact.created_at = self.artifact.created_at or now
            self.artifact.updated_at = now
            for version in self.artifact.versions:
                version.id = version.id or uuid4()
                version.created_at = version.created_at or now

    async def flush(self) -> None:
        self._hydrate()

    async def commit(self) -> None:
        self._hydrate()

    async def rollback(self) -> None:
        pass

    async def refresh_artifact(self, _artifact) -> None:  # type: ignore[no-untyped-def]
        self._hydrate()


def make_agent(
    outputs: list[RequirementAnalysisOutput],
) -> tuple[RequirementAnalystAgent, QueueLLM]:
    llm = QueueLLM(outputs)
    return (
        RequirementAnalystAgent(
            llm,
            RequirementAnalystConfig(model="configured-analysis-model", max_output_tokens=900),
        ),
        llm,
    )


@pytest.mark.asyncio
async def test_agent_uses_configured_model_and_enforces_boundary() -> None:
    agent, llm = make_agent([analysis_output(RequirementReadiness.READY)])
    request = agent.build_request(
        RequirementAnalystInput(
            project_context={},
            raw_requirement="Add approval tiers.",
            requirement_context={},
            clarification_answers=[],
        )
    )

    await agent.analyze(request)

    assert request.model == "configured-analysis-model"
    assert "Never propose a database, UI, API" in request.system_prompt
    assert llm.requests == [request]


@pytest.mark.asyncio
async def test_agent_rejects_inconsistent_readiness_output() -> None:
    agent, _ = make_agent([analysis_output(RequirementReadiness.NEEDS_CLARIFICATION, questions=[])])
    request = agent.build_request(
        RequirementAnalystInput(
            project_context={},
            raw_requirement="Add approval tiers.",
            requirement_context={},
            clarification_answers=[],
        )
    )

    with pytest.raises(InvalidAgentOutputError):
        await agent.analyze(request)


@pytest.mark.asyncio
async def test_clarification_pauses_then_answers_trigger_new_artifact_version() -> None:
    repository = FakeAnalysisRepository()
    agent, llm = make_agent(
        [
            analysis_output(
                RequirementReadiness.NEEDS_CLARIFICATION,
                questions=["What amount thresholds should apply?"],
            ),
            analysis_output(RequirementReadiness.READY),
        ]
    )
    service = RequirementAnalysisService(repository, agent)

    first = await service.analyze(repository.project.id, repository.requirement.id)

    assert first.readiness == RequirementReadiness.NEEDS_CLARIFICATION
    assert first.artifact.version == 1
    assert first.clarifications[0].status == ClarificationStatus.PENDING
    assert repository.executions[0].request_json["model"] == "configured-analysis-model"
    assert repository.executions[0].response_json is not None
    assert repository.executions[0].artifact_version_id == first.artifact.versions[0].id

    with pytest.raises(ClarificationPendingError):
        await service.analyze(repository.project.id, repository.requirement.id)

    final = await service.answer_clarifications(
        repository.project.id,
        repository.requirement.id,
        AnswerClarificationsRequest(
            answers=[
                ClarificationAnswerInput(
                    clarification_id=first.clarifications[0].id,
                    answer="Below 10M: manager; 10M and above: director.",
                )
            ]
        ),
    )

    assert final.readiness == RequirementReadiness.READY
    assert final.artifact.version == 2
    assert len(final.artifact.versions) == 2
    assert final.artifact.status == ArtifactStatus.VALIDATED
    assert final.requirement.status == RequirementStatus.BASELINED
    assert final.requirement.analysis_readiness == RequirementReadiness.READY
    assert final.clarifications[0].status == ClarificationStatus.ANSWERED
    assert len(repository.executions) == 2
    assert "Below 10M" in llm.requests[1].user_prompt


@pytest.mark.asyncio
async def test_provider_failure_is_audited_without_creating_artifact() -> None:
    repository = FakeAnalysisRepository()
    agent = RequirementAnalystAgent(
        FailingLLM(),
        RequirementAnalystConfig(model="configured-analysis-model", max_output_tokens=900),
    )
    service = RequirementAnalysisService(repository, agent)

    with pytest.raises(AgentExecutionError) as error:
        await service.analyze(repository.project.id, repository.requirement.id)

    assert error.value.code == "AGENT_EXECUTION_FAILED"
    assert repository.artifact is None
    assert repository.executions[0].status == AgentExecutionStatus.FAILED
    assert "provider unavailable" in repository.executions[0].error_message


@pytest.mark.asyncio
async def test_missing_api_key_stops_before_execution_is_created() -> None:
    repository = FakeAnalysisRepository()
    service = RequirementAnalysisService(repository, None)

    with pytest.raises(ServiceUnavailableError):
        await service.analyze(repository.project.id, repository.requirement.id)

    assert repository.executions == []
