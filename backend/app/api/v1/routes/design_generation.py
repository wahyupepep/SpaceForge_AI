from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_design_generation_service
from app.schemas.design import DesignAgentResponse, RunDesignAgentRequest
from app.schemas.error import ErrorResponse
from app.services.design_generation import DesignGenerationService

router = APIRouter(prefix="/projects/{project_id}", tags=["design-generation"])
DesignServiceDependency = Annotated[DesignGenerationService, Depends(get_design_generation_service)]
ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


@router.post(
    "/design/flow",
    response_model=DesignAgentResponse,
    responses=ERROR_RESPONSES,
)
async def run_flow_designer(
    project_id: UUID,
    payload: RunDesignAgentRequest,
    service: DesignServiceDependency,
) -> DesignAgentResponse:
    return await service.run_flow(project_id, payload.requirement_id)


@router.post(
    "/design/ui-prototype",
    response_model=DesignAgentResponse,
    responses=ERROR_RESPONSES,
)
async def run_ui_prototype(
    project_id: UUID,
    payload: RunDesignAgentRequest,
    service: DesignServiceDependency,
) -> DesignAgentResponse:
    return await service.run_ui_prototype(project_id, payload.requirement_id)


@router.post(
    "/design/technical-architecture",
    response_model=DesignAgentResponse,
    responses=ERROR_RESPONSES,
)
async def run_technical_architecture(
    project_id: UUID,
    payload: RunDesignAgentRequest,
    service: DesignServiceDependency,
) -> DesignAgentResponse:
    return await service.run_technical_architecture(project_id, payload.requirement_id)


@router.get(
    "/requirements/{requirement_id}/ui-prototypes/{artifact_id}/"
    "versions/{version_number}/files/{filename}",
    response_class=Response,
    responses={404: {"model": ErrorResponse}},
)
async def open_prototype_file(
    project_id: UUID,
    requirement_id: UUID,
    artifact_id: UUID,
    version_number: int,
    filename: str,
    service: DesignServiceDependency,
) -> Response:
    prototype = await service.read_prototype_file(
        project_id, requirement_id, artifact_id, version_number, filename
    )
    return Response(
        content=prototype.content,
        media_type=prototype.content_type,
        headers={
            "Content-Security-Policy": (
                "sandbox allow-scripts; default-src 'none'; style-src 'unsafe-inline'; "
                "script-src 'unsafe-inline'; img-src 'none'; connect-src 'none'; "
                "object-src 'none'; base-uri 'none'"
            ),
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )
