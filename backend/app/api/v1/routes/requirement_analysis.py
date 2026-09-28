from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_requirement_analysis_service
from app.schemas.analysis import (
    AgentExecutionResponse,
    AnalyzeRequirementRequest,
    AnswerClarificationsRequest,
    ClarificationResponse,
    RequirementAnalysisResponse,
)
from app.schemas.error import ErrorResponse
from app.services.requirement_analysis import RequirementAnalysisService

router = APIRouter(prefix="/projects/{project_id}", tags=["requirement-analysis"])
AnalysisServiceDependency = Annotated[
    RequirementAnalysisService, Depends(get_requirement_analysis_service)
]


@router.post(
    "/analyze-requirement",
    response_model=RequirementAnalysisResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def analyze_requirement(
    project_id: UUID,
    payload: AnalyzeRequirementRequest,
    service: AnalysisServiceDependency,
) -> RequirementAnalysisResponse:
    return await service.analyze(project_id, payload.requirement_id)


@router.get(
    "/requirements/{requirement_id}/clarifications",
    response_model=list[ClarificationResponse],
)
async def list_clarifications(
    project_id: UUID,
    requirement_id: UUID,
    service: AnalysisServiceDependency,
) -> list[ClarificationResponse]:
    return await service.list_clarifications(project_id, requirement_id)


@router.post(
    "/requirements/{requirement_id}/clarifications/answer",
    response_model=RequirementAnalysisResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def answer_clarifications(
    project_id: UUID,
    requirement_id: UUID,
    payload: AnswerClarificationsRequest,
    service: AnalysisServiceDependency,
) -> RequirementAnalysisResponse:
    return await service.answer_clarifications(project_id, requirement_id, payload)


@router.get(
    "/requirements/{requirement_id}/analysis-history",
    response_model=list[AgentExecutionResponse],
)
async def list_analysis_history(
    project_id: UUID,
    requirement_id: UUID,
    service: AnalysisServiceDependency,
) -> list[AgentExecutionResponse]:
    return await service.list_history(project_id, requirement_id)
