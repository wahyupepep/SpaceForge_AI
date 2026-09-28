from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_orchestrator_service
from app.schemas.error import ErrorResponse
from app.schemas.orchestrator import (
    OrchestratorExecutionResponse,
    OrchestratorWorkflowResponse,
    StartOrchestratorRequest,
)
from app.services.orchestrator import SAOrchestratorService

router = APIRouter(prefix="/projects/{project_id}", tags=["sa-orchestrator"])
ServiceDependency = Annotated[SAOrchestratorService, Depends(get_orchestrator_service)]
ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


@router.post(
    "/orchestrator/start",
    response_model=OrchestratorWorkflowResponse,
    responses=ERROR_RESPONSES,
)
async def start_orchestrator(
    project_id: UUID,
    payload: StartOrchestratorRequest,
    service: ServiceDependency,
) -> OrchestratorWorkflowResponse:
    return await service.start(
        project_id, payload.requirement_id, payload.existing_system_evidence
    )


@router.post(
    "/requirements/{requirement_id}/orchestrator/resume",
    response_model=OrchestratorWorkflowResponse,
    responses=ERROR_RESPONSES,
)
async def resume_orchestrator(
    project_id: UUID,
    requirement_id: UUID,
    service: ServiceDependency,
) -> OrchestratorWorkflowResponse:
    return await service.resume(project_id, requirement_id)


@router.get(
    "/requirements/{requirement_id}/orchestrator",
    response_model=OrchestratorWorkflowResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_orchestrator(
    project_id: UUID,
    requirement_id: UUID,
    service: ServiceDependency,
) -> OrchestratorWorkflowResponse:
    return await service.get(project_id, requirement_id)


@router.get(
    "/requirements/{requirement_id}/orchestrator/history",
    response_model=list[OrchestratorExecutionResponse],
    responses={404: {"model": ErrorResponse}},
)
async def get_orchestrator_history(
    project_id: UUID,
    requirement_id: UUID,
    service: ServiceDependency,
) -> list[OrchestratorExecutionResponse]:
    return (await service.get(project_id, requirement_id)).executions


@router.get(
    "/orchestrator-workflows",
    response_model=list[OrchestratorWorkflowResponse],
)
async def list_orchestrator_workflows(
    project_id: UUID, service: ServiceDependency
) -> list[OrchestratorWorkflowResponse]:
    return await service.list(project_id)
