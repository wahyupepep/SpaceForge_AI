from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_quality_gate_service
from app.schemas.error import ErrorResponse
from app.schemas.quality import (
    QualityAgentResponse,
    QualityWorkflowResponse,
    RevisionRequest,
    RunQualityRequest,
)
from app.services.quality_gate import QualityGateService

router = APIRouter(prefix="/projects/{project_id}", tags=["quality-gate"])
QualityServiceDependency = Annotated[QualityGateService, Depends(get_quality_gate_service)]
ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


@router.post("/quality/qa", response_model=QualityAgentResponse, responses=ERROR_RESPONSES)
async def run_qa(
    project_id: UUID, payload: RunQualityRequest, service: QualityServiceDependency
) -> QualityAgentResponse:
    return await service.run_qa(project_id, payload.requirement_id)


@router.post("/quality/review", response_model=QualityAgentResponse, responses=ERROR_RESPONSES)
async def run_review(
    project_id: UUID, payload: RunQualityRequest, service: QualityServiceDependency
) -> QualityAgentResponse:
    return await service.run_review(project_id, payload.requirement_id)


@router.post(
    "/requirements/{requirement_id}/quality/revise",
    response_model=QualityAgentResponse,
    responses=ERROR_RESPONSES,
)
async def revise_artifact(
    project_id: UUID,
    requirement_id: UUID,
    payload: RevisionRequest,
    service: QualityServiceDependency,
) -> QualityAgentResponse:
    return await service.revise(project_id, requirement_id, payload.artifact_type)


@router.get("/quality-workflows", response_model=list[QualityWorkflowResponse])
async def list_quality_workflows(
    project_id: UUID, service: QualityServiceDependency
) -> list[QualityWorkflowResponse]:
    return await service.list(project_id)


@router.get(
    "/requirements/{requirement_id}/quality-workflow",
    response_model=QualityWorkflowResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_quality_workflow(
    project_id: UUID, requirement_id: UUID, service: QualityServiceDependency
) -> QualityWorkflowResponse:
    return await service.get(project_id, requirement_id)
