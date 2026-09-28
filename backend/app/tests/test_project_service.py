from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from app.core.errors import ContextIncompleteError, NotFoundError
from app.domain.projects import ProjectStatus, ProjectType
from app.models.project import Project
from app.schemas.project import ProjectContextInput, ProjectCreate, ProjectUpdate
from app.services.projects import ProjectService


class FakeProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[UUID, Project] = {}
        self.commit_count = 0

    @staticmethod
    def _hydrate(project: Project) -> None:
        now = datetime.now(timezone.utc)
        if project.id is None:
            project.id = uuid4()
        if project.created_at is None:
            project.created_at = now
        if project.updated_at is None:
            project.updated_at = now
        if project.context.id is None:
            project.context.id = uuid4()
        if project.context.created_at is None:
            project.context.created_at = now
        if project.context.updated_at is None:
            project.context.updated_at = now

    async def add(self, project: Project) -> Project:
        self._hydrate(project)
        self.projects[project.id] = project
        return project

    async def get(self, project_id: UUID) -> Optional[Project]:
        return self.projects.get(project_id)

    async def list(self, offset: int, limit: int) -> list[Project]:
        return list(self.projects.values())[offset : offset + limit]

    async def delete(self, project: Project) -> None:
        del self.projects[project.id]

    async def commit(self) -> None:
        self.commit_count += 1

    async def refresh(self, project: Project) -> Project:
        self._hydrate(project)
        project.updated_at = datetime.now(timezone.utc)
        project.context.updated_at = project.updated_at
        return project


def enhancement_payload() -> ProjectCreate:
    return ProjectCreate(
        name="Tiered approval",
        description="Improve the current approval process.",
        project_type=ProjectType.ENHANCEMENT,
        business_objective="Reduce approval risk.",
    )


@pytest.mark.asyncio
async def test_enhancement_stays_draft_and_exposes_missing_as_is_fields() -> None:
    service = ProjectService(FakeProjectRepository())

    project = await service.create(enhancement_payload())

    assert project.status == ProjectStatus.DRAFT
    assert project.missing_context_fields == [
        "current_flow",
        "current_actors",
        "current_rules",
        "current_problem",
        "requested_change",
    ]


@pytest.mark.asyncio
async def test_incomplete_enhancement_cannot_be_submitted() -> None:
    repository = FakeProjectRepository()
    service = ProjectService(repository)
    project = await service.create(enhancement_payload())

    with pytest.raises(ContextIncompleteError) as error:
        await service.submit_for_analysis(project.id)

    assert error.value.code == "CONTEXT_INCOMPLETE"
    assert repository.projects[project.id].status == ProjectStatus.CONTEXT_INCOMPLETE


@pytest.mark.asyncio
async def test_complete_enhancement_can_become_ready_for_analysis() -> None:
    repository = FakeProjectRepository()
    service = ProjectService(repository)
    project = await service.create(enhancement_payload())
    await service.update(
        project.id,
        ProjectUpdate(
            context=ProjectContextInput(
                current_flow="Requester submits and manager approves.",
                current_actors="Requester, manager",
                current_rules="Manager approves every request.",
                current_problem="High-value requests need additional control.",
                requested_change="Add nominal-based approval tiers.",
            )
        ),
    )

    ready = await service.submit_for_analysis(project.id)

    assert ready.status == ProjectStatus.READY_FOR_ANALYSIS
    assert ready.missing_context_fields == []


@pytest.mark.asyncio
async def test_service_lists_updates_and_deletes_projects() -> None:
    repository = FakeProjectRepository()
    service = ProjectService(repository)
    created = await service.create(
        ProjectCreate(
            name="New portal",
            description="Create a customer portal.",
            project_type=ProjectType.NEW_SYSTEM,
            business_objective="Improve self service.",
        )
    )

    updated = await service.update(created.id, ProjectUpdate(name="Customer portal"))
    listed = await service.list(offset=0, limit=10)
    await service.delete(created.id)

    assert updated.name == "Customer portal"
    assert listed[0].id == created.id
    assert repository.projects == {}

    with pytest.raises(NotFoundError):
        await service.get(created.id)
