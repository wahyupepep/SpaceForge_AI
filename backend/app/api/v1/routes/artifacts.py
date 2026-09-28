from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_artifact_service
from app.schemas.artifact import ArtifactCreate, ArtifactResponse, ArtifactVersionCreate
from app.schemas.error import ErrorResponse
from app.services.artifacts import ArtifactService

router = APIRouter(prefix="/projects/{project_id}/artifacts", tags=["artifacts"])
ArtifactServiceDependency = Annotated[ArtifactService, Depends(get_artifact_service)]


@router.post(
    "",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def create_artifact(
    project_id: UUID, payload: ArtifactCreate, service: ArtifactServiceDependency
) -> ArtifactResponse:
    return await service.create(project_id, payload)


@router.get("", response_model=list[ArtifactResponse])
async def list_artifacts(
    project_id: UUID, service: ArtifactServiceDependency
) -> list[ArtifactResponse]:
    return await service.list(project_id)


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    project_id: UUID, artifact_id: UUID, service: ArtifactServiceDependency
) -> ArtifactResponse:
    return await service.get(project_id, artifact_id)


@router.post(
    "/{artifact_id}/versions",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def create_artifact_version(
    project_id: UUID,
    artifact_id: UUID,
    payload: ArtifactVersionCreate,
    service: ArtifactServiceDependency,
) -> ArtifactResponse:
    return await service.create_version(project_id, artifact_id, payload)
