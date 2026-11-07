from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.api.dependencies import get_project_service
from app.schemas.error import ErrorResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectEvidenceResponse,
    ProjectResponse,
    ProjectUpdate,
)
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


@router.get("/{project_id}/evidence", response_model=list[ProjectEvidenceResponse])
async def list_project_evidence(
    project_id: UUID, service: ProjectServiceDependency
) -> list[ProjectEvidenceResponse]:
    return await service.list_evidence(project_id)


@router.post(
    "/{project_id}/evidence",
    response_model=ProjectEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_project_evidence(
    project_id: UUID,
    service: ProjectServiceDependency,
    category: Annotated[str, Form()],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    file: Annotated[UploadFile, File()],
    description: Annotated[str | None, Form(max_length=2000)] = None,
) -> ProjectEvidenceResponse:
    content = await file.read()
    return await service.add_evidence(
        project_id,
        category=category,
        title=title,
        description=description,
        filename=file.filename or "evidence",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )


@router.delete(
    "/{project_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_project_evidence(
    project_id: UUID, evidence_id: UUID, service: ProjectServiceDependency
) -> Response:
    await service.delete_evidence(project_id, evidence_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/evidence/{evidence_id}/download")
async def download_project_evidence(
    project_id: UUID, evidence_id: UUID, service: ProjectServiceDependency
) -> Response:
    content, content_type, filename = await service.get_evidence_content(
        project_id, evidence_id
    )
    safe_filename = filename.replace('"', "")
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )
