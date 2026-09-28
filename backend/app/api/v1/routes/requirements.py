from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_requirement_service
from app.schemas.error import ErrorResponse
from app.schemas.requirement import RequirementCreate, RequirementResponse, RequirementUpdate
from app.services.requirements import RequirementService

router = APIRouter(prefix="/projects/{project_id}/requirements", tags=["requirements"])
RequirementServiceDependency = Annotated[RequirementService, Depends(get_requirement_service)]


@router.post(
    "",
    response_model=RequirementResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def create_requirement(
    project_id: UUID,
    payload: RequirementCreate,
    service: RequirementServiceDependency,
) -> RequirementResponse:
    return await service.create(project_id, payload)


@router.get("", response_model=list[RequirementResponse])
async def list_requirements(
    project_id: UUID, service: RequirementServiceDependency
) -> list[RequirementResponse]:
    return await service.list(project_id)


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    project_id: UUID, requirement_id: UUID, service: RequirementServiceDependency
) -> RequirementResponse:
    return await service.get(project_id, requirement_id)


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    project_id: UUID,
    requirement_id: UUID,
    payload: RequirementUpdate,
    service: RequirementServiceDependency,
) -> RequirementResponse:
    return await service.update(project_id, requirement_id, payload)


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    project_id: UUID, requirement_id: UUID, service: RequirementServiceDependency
) -> Response:
    await service.delete(project_id, requirement_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
