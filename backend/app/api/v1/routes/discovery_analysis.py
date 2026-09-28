from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_discovery_analysis_service
from app.schemas.discovery import (
    AnalyzeExistingSystemRequest,
    RunResearchRequest,
    SpecialistAnalysisResponse,
)
from app.schemas.error import ErrorResponse
from app.services.discovery_analysis import DiscoveryAnalysisService

router = APIRouter(prefix="/projects/{project_id}", tags=["discovery-analysis"])
DiscoveryServiceDependency = Annotated[
    DiscoveryAnalysisService, Depends(get_discovery_analysis_service)
]


@router.post(
    "/research",
    response_model=SpecialistAnalysisResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def run_research(
    project_id: UUID,
    payload: RunResearchRequest,
    service: DiscoveryServiceDependency,
) -> SpecialistAnalysisResponse:
    return await service.run_research(project_id, payload.requirement_id)


@router.post(
    "/analyze-existing-system",
    response_model=SpecialistAnalysisResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def analyze_existing_system(
    project_id: UUID,
    payload: AnalyzeExistingSystemRequest,
    service: DiscoveryServiceDependency,
) -> SpecialistAnalysisResponse:
    return await service.analyze_existing_system(project_id, payload)
