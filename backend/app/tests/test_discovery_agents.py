from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agents.discovery import (
    ExistingComponentOutput,
    ExistingSystemAnalysisOutput,
    ExistingSystemAnalyst,
    GapAnalysisOutput,
    InvalidDiscoveryOutputError,
    ResearchAgent,
    ResearchAgentOutput,
    ResearchSourceOutput,
    SpecialistAgentConfig,
)
from app.core.errors import RequirementNotReadyError
from app.domain.analysis import RequirementReadiness
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.discovery import (
    ChangeClassification,
    ExistingComponentType,
    ExistingEvidenceType,
)
from app.domain.projects import ProjectStatus, ProjectType
from app.models.analysis import AgentExecution
from app.models.artifact import Artifact, ArtifactVersion
from app.schemas.discovery import AnalyzeExistingSystemRequest, ExistingEvidenceInput
from app.services.discovery_analysis import DiscoveryAnalysisService
from app.services.llm import LLMResult, LLMUsage


class QueueLLM:
    def __init__(self, outputs: list[object]) -> None:
        self.outputs = outputs
        self.requests = []

    async def generate_structured(self, request, _output_schema):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        return LLMResult(
            output=self.outputs.pop(0),
            response_id=f"response-{len(self.requests)}",
            model=request.model,
            usage=LLMUsage(input_tokens=20, output_tokens=30, total_tokens=50),
        )


def research_output() -> ResearchAgentOutput:
    return ResearchAgentOutput(
        objective="Identify approval workflow practices",
        common_practices=["Separate approval authority by materiality."],
        comparable_workflows=["Expense approval workflow"],
        common_metadata=["amount", "requester", "decision timestamp"],
        ux_patterns=["Show current approval status and pending actor."],
        technical_considerations=["Preserve an auditable decision history."],
        risks=["Ambiguous thresholds can route requests incorrectly."],
        sources=[
            ResearchSourceOutput(
                title="Approval controls",
                url="https://example.com/approval-controls",
                supports="Approval authority should be explicit.",
            )
        ],
        open_questions=[],
    )


def existing_output() -> ExistingSystemAnalysisOutput:
    return ExistingSystemAnalysisOutput(
        as_is_summary="Requests are currently approved by one manager.",
        components=[
            ExistingComponentOutput(
                name="Approval module",
                component_type=ExistingComponentType.MODULE,
                classification=ChangeClassification.MODIFY,
                evidence="User description states that one manager approves all requests.",
                rationale="The existing module already owns approval decisions.",
                impact="Approval routing behavior may change.",
            )
        ],
        affected_components=["Approval module"],
        gap_analysis=[
            GapAnalysisOutput(
                area="Approval authority",
                current_state="One manager approves every request.",
                required_state="Requirement calls for amount-based approval tiers.",
                gap="Current routing does not distinguish amount tiers.",
            )
        ],
        regression_risks=["Existing low-value approval behavior may regress."],
        unknown_information=["Current module ownership is not documented."],
    )


class FakeDiscoveryRepository:
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
                current_rules="Manager approves every request",
                current_problem="High values need additional control",
                requested_change="Add amount-based approval tiers",
                constraints=None,
                notes=None,
            ),
        )
        self.requirement = SimpleNamespace(
            id=uuid4(),
            project_id=self.project.id,
            analysis_readiness=RequirementReadiness.READY,
        )
        baseline_version = ArtifactVersion(
            id=uuid4(),
            version=1,
            content_json={
                "feature": "Tiered approval",
                "business_objective": "Reduce risk",
                "problem_statement": "High-value approvals need more control",
                "actors": ["Requester", "Manager"],
                "known_requirements": ["Tiers depend on amount"],
                "business_rules": [],
                "constraints": [],
                "dependencies": [],
                "assumptions": [],
                "unknown_information": [],
                "readiness": "READY",
                "clarification_questions": [],
                "blocked_reason": "",
            },
            created_by="REQUIREMENT_ANALYST",
            created_at=now,
        )
        self.artifacts = {
            ArtifactType.REQUIREMENT_BASELINE: Artifact(
                id=uuid4(),
                project_id=self.project.id,
                requirement_id=self.requirement.id,
                artifact_type=ArtifactType.REQUIREMENT_BASELINE,
                current_version=1,
                status=ArtifactStatus.VALIDATED,
                created_at=now,
                updated_at=now,
                versions=[baseline_version],
            )
        }
        self.executions: list[AgentExecution] = []

    async def get_project(self, project_id):  # type: ignore[no-untyped-def]
        return self.project if project_id == self.project.id else None

    async def get_requirement(self, project_id, requirement_id):  # type: ignore[no-untyped-def]
        if project_id == self.project.id and requirement_id == self.requirement.id:
            return self.requirement
        return None

    async def get_typed_artifact(
        self,
        _project_id,
        _requirement_id,
        artifact_type,
        **_kwargs,  # type: ignore[no-untyped-def]
    ):
        return self.artifacts.get(artifact_type)

    def add(self, value):  # type: ignore[no-untyped-def]
        if isinstance(value, AgentExecution):
            self.executions.append(value)
        elif isinstance(value, Artifact):
            self.artifacts[value.artifact_type] = value

    def _hydrate(self) -> None:
        now = datetime.now(timezone.utc)
        for execution in self.executions:
            execution.id = execution.id or uuid4()
            execution.created_at = execution.created_at or now
            execution.updated_at = now
        for artifact in self.artifacts.values():
            artifact.id = artifact.id or uuid4()
            artifact.created_at = artifact.created_at or now
            artifact.updated_at = now
            for version in artifact.versions:
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


def make_service(repository: FakeDiscoveryRepository):
    research_llm = QueueLLM([research_output(), research_output()])
    existing_llm = QueueLLM([existing_output()])
    config = SpecialistAgentConfig(model="configured-model", max_output_tokens=1200)
    service = DiscoveryAnalysisService(
        repository,
        ResearchAgent(research_llm, config, web_search_enabled=True),
        ExistingSystemAnalyst(existing_llm, config),
    )
    return service, research_llm, existing_llm


@pytest.mark.asyncio
async def test_research_and_existing_analysis_create_versioned_audited_artifacts() -> None:
    repository = FakeDiscoveryRepository()
    service, research_llm, existing_llm = make_service(repository)

    research = await service.run_research(repository.project.id, repository.requirement.id)
    research_v2 = await service.run_research(repository.project.id, repository.requirement.id)
    existing = await service.analyze_existing_system(
        repository.project.id,
        AnalyzeExistingSystemRequest(
            requirement_id=repository.requirement.id,
            evidence=[
                ExistingEvidenceInput(
                    source_type=ExistingEvidenceType.USER_DESCRIPTION,
                    title="Current approval flow",
                    content="One manager approves all requests.",
                )
            ],
        ),
    )

    assert research.artifact.artifact_type == ArtifactType.RESEARCH
    assert research_v2.artifact.version == 2
    assert research_llm.requests[0].tools == ({"type": "web_search"},)
    assert existing.artifact.artifact_type == ArtifactType.EXISTING_SYSTEM_ANALYSIS
    assert existing.artifact.content_json["components"][0]["classification"] == "MODIFY"
    assert "RESEARCH" in existing_llm.requests[0].user_prompt
    assert len(repository.executions) == 3
    assert all(item.artifact_version_id for item in repository.executions)


@pytest.mark.asyncio
async def test_specialists_are_blocked_until_requirement_is_ready() -> None:
    repository = FakeDiscoveryRepository()
    repository.requirement.analysis_readiness = RequirementReadiness.NEEDS_CLARIFICATION
    service, _research_llm, _existing_llm = make_service(repository)

    with pytest.raises(RequirementNotReadyError):
        await service.run_research(repository.project.id, repository.requirement.id)

    assert repository.executions == []


@pytest.mark.asyncio
async def test_enhancement_existing_analysis_requires_as_is_gap_and_affected_components() -> None:
    invalid = existing_output().model_copy(
        update={"as_is_summary": "", "affected_components": [], "gap_analysis": []}
    )
    llm = QueueLLM([invalid])
    analyst = ExistingSystemAnalyst(
        llm,
        SpecialistAgentConfig(model="configured-model", max_output_tokens=1200),
    )
    request = analyst.build_request(
        SimpleNamespace(model_dump=lambda **_kwargs: {})  # type: ignore[arg-type]
    )

    with pytest.raises(InvalidDiscoveryOutputError):
        await analyst.analyze(request, ProjectType.ENHANCEMENT)


def test_research_source_rejects_non_http_url() -> None:
    with pytest.raises(ValidationError):
        ResearchSourceOutput(
            title="Unsafe source",
            url="javascript:alert(1)",
            supports="Nothing",
        )
