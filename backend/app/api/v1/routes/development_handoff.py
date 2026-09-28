from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_development_handoff_service
from app.domain.handoff import HandoffExportFormat
from app.schemas.error import ErrorResponse
from app.schemas.handoff import (
    DevelopmentPlanResponse,
    GenerateHandoffRequest,
    HandoffWorkflowResponse,
    PlanDevelopmentRequest,
)
from app.services.development_handoff import DevelopmentHandoffService

router = APIRouter(prefix="/projects/{project_id}", tags=["development-handoff"])
HandoffServiceDependency = Annotated[
    DevelopmentHandoffService, Depends(get_development_handoff_service)
]
ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


@router.post(
    "/handoff/plan", response_model=DevelopmentPlanResponse, responses=ERROR_RESPONSES
)
async def plan_development(
    project_id: UUID,
    payload: PlanDevelopmentRequest,
    service: HandoffServiceDependency,
) -> DevelopmentPlanResponse:
    return await service.plan(project_id, payload.requirement_id)


@router.post(
    "/requirements/{requirement_id}/handoff/generate",
    response_model=HandoffWorkflowResponse,
    responses=ERROR_RESPONSES,
)
async def generate_handoff(
    project_id: UUID,
    requirement_id: UUID,
    payload: GenerateHandoffRequest,
    service: HandoffServiceDependency,
) -> HandoffWorkflowResponse:
    return await service.generate_package(
        project_id, requirement_id, payload.expected_task_version
    )


@router.get(
    "/requirements/{requirement_id}/handoff",
    response_model=HandoffWorkflowResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_handoff(
    project_id: UUID,
    requirement_id: UUID,
    service: HandoffServiceDependency,
) -> HandoffWorkflowResponse:
    return await service.get(project_id, requirement_id)


@router.get(
    "/requirements/{requirement_id}/handoff/packages/{version}/download/{export_format}",
    response_class=Response,
    responses={404: {"model": ErrorResponse}},
)
async def download_handoff(
    project_id: UUID,
    requirement_id: UUID,
    version: int,
    export_format: HandoffExportFormat,
    service: HandoffServiceDependency,
) -> Response:
    exported = await service.download(
        project_id, requirement_id, version, export_format
    )
    return Response(
        content=exported.content,
        media_type=exported.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{exported.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
