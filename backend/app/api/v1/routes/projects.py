from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_project_service
from app.schemas.error import ErrorResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
ProjectServiceDependency = Annotated[ProjectService, Depends(get_project_service)]


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
)
async def create_project(
    payload: ProjectCreate, service: ProjectServiceDependency
) -> ProjectResponse:
    return await service.create(payload)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    service: ProjectServiceDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ProjectResponse]:
    return await service.list(offset=offset, limit=limit)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_project(project_id: UUID, service: ProjectServiceDependency) -> ProjectResponse:
    return await service.get(project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    service: ProjectServiceDependency,
) -> ProjectResponse:
    return await service.update(project_id, payload)


@router.post(
    "/{project_id}/submit-for-analysis",
    response_model=ProjectResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def submit_project_for_analysis(
    project_id: UUID, service: ProjectServiceDependency
) -> ProjectResponse:
    return await service.submit_for_analysis(project_id)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_project(project_id: UUID, service: ProjectServiceDependency) -> Response:
    await service.delete(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
