from uuid import UUID

from app.core.errors import ContextIncompleteError, NotFoundError
from app.domain.projects import ProjectStatus, ProjectType, missing_enhancement_context
from app.models.project import Project, ProjectContext
from app.repositories.projects import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    @staticmethod
    def _response(project: Project) -> ProjectResponse:
        missing_fields = (
            missing_enhancement_context(project.context)
            if project.project_type == ProjectType.ENHANCEMENT
            else []
        )
        response = ProjectResponse.model_validate(project)
        return response.model_copy(update={"missing_context_fields": missing_fields})

    async def create(self, payload: ProjectCreate) -> ProjectResponse:
        project = Project(
            name=payload.name,
            description=payload.description,
            project_type=payload.project_type,
            business_objective=payload.business_objective,
            status=ProjectStatus.DRAFT,
            context=ProjectContext(**payload.context.model_dump()),
        )
        await self._repository.add(project)
        await self._repository.commit()
        await self._repository.refresh(project)
        return self._response(project)

    async def get(self, project_id: UUID) -> ProjectResponse:
        return self._response(await self._require_project(project_id))

    async def list(self, offset: int, limit: int) -> list[ProjectResponse]:
        projects = await self._repository.list(offset=offset, limit=limit)
        return [self._response(project) for project in projects]

    async def update(self, project_id: UUID, payload: ProjectUpdate) -> ProjectResponse:
        project = await self._require_project(project_id)
        updates = payload.model_dump(exclude_unset=True, exclude={"context"})
        for field, value in updates.items():
            setattr(project, field, value)

        if payload.context is not None:
            for field, value in payload.context.model_dump(exclude_unset=True).items():
                setattr(project.context, field, value)

        missing_fields = (
            missing_enhancement_context(project.context)
            if project.project_type == ProjectType.ENHANCEMENT
            else []
        )
        project.status = ProjectStatus.CONTEXT_INCOMPLETE if missing_fields else ProjectStatus.DRAFT
        await self._repository.commit()
        await self._repository.refresh(project)
        return self._response(project)

    async def submit_for_analysis(self, project_id: UUID) -> ProjectResponse:
        project = await self._require_project(project_id)
        missing_fields = (
            missing_enhancement_context(project.context)
            if project.project_type == ProjectType.ENHANCEMENT
            else []
        )
        if missing_fields:
            project.status = ProjectStatus.CONTEXT_INCOMPLETE
            await self._repository.commit()
            raise ContextIncompleteError(missing_fields)

        project.status = ProjectStatus.READY_FOR_ANALYSIS
        await self._repository.commit()
        await self._repository.refresh(project)
        return self._response(project)

    async def delete(self, project_id: UUID) -> None:
        project = await self._require_project(project_id)
        await self._repository.delete(project)
        await self._repository.commit()

    async def _require_project(self, project_id: UUID) -> Project:
        project = await self._repository.get(project_id)
        if project is None:
            raise NotFoundError("Project")
        return project
