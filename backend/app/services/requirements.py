from uuid import UUID

from app.core.errors import NotFoundError, ProjectNotReadyError
from app.domain.projects import ProjectStatus
from app.domain.requirements import RequirementStatus
from app.models.requirement import Requirement
from app.repositories.requirements import RequirementRepository
from app.schemas.requirement import RequirementCreate, RequirementResponse, RequirementUpdate


class RequirementService:
    def __init__(self, repository: RequirementRepository) -> None:
        self._repository = repository

    async def create(self, project_id: UUID, payload: RequirementCreate) -> RequirementResponse:
        project = await self._repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        if project.status != ProjectStatus.READY_FOR_ANALYSIS:
            raise ProjectNotReadyError()

        requirement = Requirement(
            project_id=project_id,
            status=RequirementStatus.DRAFT,
            **payload.model_dump(),
        )
        await self._repository.add(requirement)
        await self._repository.commit()
        await self._repository.refresh(requirement)
        return RequirementResponse.model_validate(requirement)

    async def list(self, project_id: UUID) -> list[RequirementResponse]:
        if await self._repository.get_project(project_id) is None:
            raise NotFoundError("Project")
        return [
            RequirementResponse.model_validate(item)
            for item in await self._repository.list(project_id)
        ]

    async def get(self, project_id: UUID, requirement_id: UUID) -> RequirementResponse:
        return RequirementResponse.model_validate(await self._require(project_id, requirement_id))

    async def update(
        self, project_id: UUID, requirement_id: UUID, payload: RequirementUpdate
    ) -> RequirementResponse:
        requirement = await self._require(project_id, requirement_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(requirement, field, value)
        await self._repository.commit()
        await self._repository.refresh(requirement)
        return RequirementResponse.model_validate(requirement)

    async def delete(self, project_id: UUID, requirement_id: UUID) -> None:
        requirement = await self._require(project_id, requirement_id)
        await self._repository.delete(requirement)
        await self._repository.commit()

    async def _require(self, project_id: UUID, requirement_id: UUID) -> Requirement:
        requirement = await self._repository.get(project_id, requirement_id)
        if requirement is None:
            raise NotFoundError("Requirement")
        return requirement
