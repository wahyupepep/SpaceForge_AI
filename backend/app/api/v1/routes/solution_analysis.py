from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_solution_analysis_service
from app.schemas.error import ErrorResponse
from app.schemas.solution import (
    GenerateSolutionRequest,
    SolutionAnalysisResponse,
    SolutionApprovalRequest,
    SolutionWorkflowResponse,
)
from app.services.solution_analysis import SolutionAnalysisService

router = APIRouter(prefix="/projects/{project_id}", tags=["solution-analysis"])
SolutionServiceDependency = Annotated[
    SolutionAnalysisService, Depends(get_solution_analysis_service)
]


@router.post(
    "/generate-solution",
    response_model=SolutionAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def generate_solution(
    project_id: UUID,
    payload: GenerateSolutionRequest,
    service: SolutionServiceDependency,
) -> SolutionAnalysisResponse:
    return await service.generate(project_id, payload.requirement_id)


@router.get("/solution-workflows", response_model=list[SolutionWorkflowResponse])
async def list_solution_workflows(
    project_id: UUID, service: SolutionServiceDependency
) -> list[SolutionWorkflowResponse]:
    return await service.list(project_id)


@router.get(
    "/requirements/{requirement_id}/solution-workflow",
    response_model=SolutionWorkflowResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_solution_workflow(
    project_id: UUID, requirement_id: UUID, service: SolutionServiceDependency
) -> SolutionWorkflowResponse:
    return await service.get(project_id, requirement_id)


@router.post(
    "/requirements/{requirement_id}/solution-approval",
    response_model=SolutionWorkflowResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def act_on_solution(
    project_id: UUID,
    requirement_id: UUID,
    payload: SolutionApprovalRequest,
    service: SolutionServiceDependency,
) -> SolutionWorkflowResponse:
    return await service.act(project_id, requirement_id, payload)


@router.post(
    "/requirements/{requirement_id}/solution-revision/retry",
    response_model=SolutionAnalysisResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def retry_solution_revision(
    project_id: UUID,
    requirement_id: UUID,
    service: SolutionServiceDependency,
) -> SolutionAnalysisResponse:
    return await service.retry_revision(project_id, requirement_id)
