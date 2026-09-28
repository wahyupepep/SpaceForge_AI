from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agents.design import (
    DesignAgentConfig,
    FlowDesignerAgent,
    FlowDesignerOutput,
    PrototypeScreenOutput,
    TechnicalArchitectAgent,
    TechnicalArchitectOutput,
    UIPrototypeAgent,
    UIPrototypeOutput,
)
from app.artifacts.schemas import (
    APIEndpointContent,
    APIErrorContent,
    APIFieldContent,
    APISpecificationContent,
    DatabaseDesignContent,
    DatabaseEntityContent,
    DatabaseFieldContent,
    FlowStepContent,
    FlowVariantContent,
    StateTransitionContent,
)
from app.core.errors import ArtifactDependencyMissingError, TechnicalDesignBlockedError
from app.domain.artifacts import ArtifactType
from app.domain.solution import SolutionApprovalAction
from app.domain.technical import APIChangeType, DatabaseChangeType, HTTPMethod
from app.schemas.solution import SolutionApprovalRequest
from app.services.design_generation import DesignGenerationService
from app.services.file_storage import StoredFile
from app.tests.test_solution_analyst import (
    FakeSolutionRepository,
    QueueLLM,
    make_service,
)


class MemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, content: bytes, content_type: str) -> StoredFile:
        self.files[key] = (content, content_type)
        return StoredFile(key=key, size_bytes=len(content), content_type=content_type)

    async def read(self, key: str) -> bytes:
        return self.files[key][0]

    async def delete(self, key: str) -> None:
        self.files.pop(key, None)


def flow_output() -> FlowDesignerOutput:
    main = FlowStepContent(
        step_id="FR-1",
        actor="Requester",
        action="Submit request",
        outcome="Request enters approval routing",
        requirement_refs=["Tiered approval"],
    )
    return FlowDesignerOutput(
        name="Tiered approval flow",
        mermaid="flowchart TD\n  A[Submit] --> B[Route by amount] --> C[Decision]",
        main_flow=[main],
        alternative_flows=[
            FlowVariantContent(name="Withdraw", trigger="Before decision", steps=[main])
        ],
        exception_flows=[
            FlowVariantContent(name="Escalate", trigger="Approver unavailable", steps=[main])
        ],
        state_transitions=[
            StateTransitionContent(
                from_state="DRAFT", event="submit", to_state="PENDING", condition=None
            )
        ],
        requirement_traceability=["Tiered approval"],
    )


def ui_output() -> UIPrototypeOutput:
    return UIPrototypeOutput(
        summary="Approval workspace prototype",
        screens=[
            PrototypeScreenOutput(
                filename="approval.html",
                title="Approval",
                purpose="Review and decide a pending request",
                source_html=(
                    "<!doctype html><html><head><style>button{padding:8px}</style></head>"
                    "<body><main><h1>Approval</h1><button id='approve'>Approve</button>"
                    "<p id='status'>Pending</p></main><script>document.querySelector('#approve')"
                    ".onclick=()=>document.querySelector('#status').textContent='Approved';"
                    "</script></body></html>"
                ),
                requirement_refs=["Tiered approval"],
            )
        ],
        interactions=["Approve updates the visible in-memory status."],
        requirement_traceability=["Tiered approval -> approval.html"],
    )


def technical_output() -> TechnicalArchitectOutput:
    identifier = DatabaseFieldContent(
        name="id",
        datatype="uuid",
        primary_key=True,
        foreign_key=None,
        nullable=False,
        default="generated UUID",
        indexed=True,
        unique=True,
        description="Request identity",
    )
    database = DatabaseDesignContent(
        summary="Approval persistence specification",
        entities=[
            DatabaseEntityContent(
                entity="ApprovalRequest",
                table="approval_requests",
                classification=DatabaseChangeType.NEW,
                description="Stores approval requests.",
                fields=[identifier],
                audit_fields=["created_at", "updated_at"],
                requirement_refs=["Tiered approval"],
            )
        ],
        relationships=[],
        constraints=["Amount must be non-negative."],
        assumptions=[],
        requirement_traceability=["Tiered approval -> ApprovalRequest"],
    )
    field = APIFieldContent(
        name="request_id", datatype="uuid", required=True, description="Request identity"
    )
    api = APISpecificationContent(
        base_path="/api/v1",
        authentication="Authenticated business user",
        endpoints=[
            APIEndpointContent(
                method=HTTPMethod.POST,
                endpoint="/approval-requests/{request_id}/approve",
                classification=APIChangeType.NEW,
                purpose="Approve a pending request.",
                actor="Approver",
                authorization="Actor must own the active approval step.",
                request_fields=[field],
                response_fields=[field],
                validations=["Request must be pending."],
                business_rules=["Apply the configured amount tier."],
                error_responses=[
                    APIErrorContent(
                        status_code=409,
                        code="INVALID_STATE",
                        condition="Request is not pending.",
                        response_fields=[],
                    )
                ],
                requirement_refs=["Tiered approval"],
            )
        ],
        assumptions=[],
        requirement_traceability=["Tiered approval -> approve endpoint"],
    )
    return TechnicalArchitectOutput(database_design=database, api_specification=api)


def make_design_service(repository: FakeSolutionRepository):
    config = DesignAgentConfig(model="configured-design-model", max_output_tokens=12000)
    storage = MemoryStorage()
    flow_llm = QueueLLM([flow_output(), flow_output()])
    ui_llm = QueueLLM([ui_output()])
    technical_llm = QueueLLM([technical_output()])
    service = DesignGenerationService(
        repository,
        FlowDesignerAgent(flow_llm, config),
        UIPrototypeAgent(ui_llm, config),
        TechnicalArchitectAgent(technical_llm, config),
        storage,
    )
    return service, storage, flow_llm, ui_llm, technical_llm


async def approve_solution(repository: FakeSolutionRepository) -> None:
    solution_service, _llm = make_service(repository)
    await solution_service.generate(repository.project.id, repository.requirement.id)
    await solution_service.act(
        repository.project.id,
        repository.requirement.id,
        SolutionApprovalRequest(action=SolutionApprovalAction.APPROVE, expected_version=1),
    )


@pytest.mark.asyncio
async def test_design_agents_require_approved_solution() -> None:
    repository = FakeSolutionRepository()
    service, _storage, _flow, _ui, _technical = make_design_service(repository)

    try:
        await service.run_flow(repository.project.id, repository.requirement.id)
        raise AssertionError("Expected technical design gate")
    except TechnicalDesignBlockedError:
        pass


@pytest.mark.asyncio
async def test_ui_prototype_requires_process_flow() -> None:
    repository = FakeSolutionRepository()
    await approve_solution(repository)
    service, _storage, _flow, _ui, _technical = make_design_service(repository)

    with pytest.raises(ArtifactDependencyMissingError):
        await service.run_ui_prototype(repository.project.id, repository.requirement.id)


def test_prototype_rejects_remote_assets_and_network_calls() -> None:
    with pytest.raises(ValidationError):
        PrototypeScreenOutput(
            filename="unsafe.html",
            title="Unsafe",
            purpose="Invalid prototype",
            source_html=(
                "<html><style></style><body></body>"
                "<script>fetch('https://example.com')</script></html>"
            ),
            requirement_refs=["REQ-1"],
        )


@pytest.mark.asyncio
async def test_flow_ui_and_technical_outputs_are_versioned_and_browser_readable() -> None:
    repository = FakeSolutionRepository()
    await approve_solution(repository)
    service, storage, flow_llm, ui_llm, technical_llm = make_design_service(repository)

    flow = await service.run_flow(repository.project.id, repository.requirement.id)
    flow_v2 = await service.run_flow(repository.project.id, repository.requirement.id)
    technical = await service.run_technical_architecture(
        repository.project.id, repository.requirement.id
    )
    prototype = await service.run_ui_prototype(repository.project.id, repository.requirement.id)

    assert flow.artifacts[0].artifact_type == ArtifactType.PROCESS_FLOW
    assert flow_v2.artifacts[0].version == 2
    assert {item.artifact_type for item in technical.artifacts} == {
        ArtifactType.DATABASE_DESIGN,
        ArtifactType.API_SPECIFICATION,
    }
    prototype_artifact = prototype.artifacts[0]
    screen = prototype_artifact.content_json["screens"][0]
    opened = await service.read_prototype_file(
        repository.project.id,
        repository.requirement.id,
        prototype_artifact.id,
        prototype_artifact.version,
        screen["filename"],
    )
    assert b"<html" in opened.content
    assert screen["storage_key"] in storage.files
    assert "approved_solution" in flow_llm.requests[0].user_prompt
    assert "process_flow" in ui_llm.requests[0].user_prompt
    assert "never implement" in technical_llm.requests[0].system_prompt
    assert len(repository.executions) == 5
