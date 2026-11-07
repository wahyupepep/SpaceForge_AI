from __future__ import annotations

from typing import Optional, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectEvidence


class ProjectRepository(Protocol):
    owner_id: UUID | None

    async def add(self, project: Project) -> Project: ...

    async def get(self, project_id: UUID) -> Optional[Project]: ...

    async def list(self, offset: int, limit: int) -> list[Project]: ...

    async def delete(self, project: Project) -> None: ...

    async def commit(self) -> None: ...

    async def refresh(self, project: Project) -> Project: ...

    def add_evidence(self, evidence: ProjectEvidence) -> None: ...

    async def get_evidence(
        self, project_id: UUID, evidence_id: UUID
    ) -> Optional[ProjectEvidence]: ...

    async def delete_evidence(self, evidence: ProjectEvidence) -> None: ...


class SQLAlchemyProjectRepository:
    def __init__(self, session: AsyncSession, owner_id: UUID | None = None) -> None:
        self._session = session
        self.owner_id = owner_id

    async def add(self, project: Project) -> Project:
        self._session.add(project)
        return project

    async def get(self, project_id: UUID) -> Optional[Project]:
        statement = (
            select(Project)
            .options(selectinload(Project.context), selectinload(Project.evidence))
            .where(Project.id == project_id)
        )
        if self.owner_id is not None:
            statement = statement.where(Project.owner_id == self.owner_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list(self, offset: int, limit: int) -> list[Project]:
        statement = (
            select(Project)
            .options(selectinload(Project.context), selectinload(Project.evidence))
            .order_by(Project.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if self.owner_id is not None:
            statement = statement.where(Project.owner_id == self.owner_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def delete(self, project: Project) -> None:
        await self._session.delete(project)

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, project: Project) -> Project:
        await self._session.refresh(project)
        await self._session.refresh(project, attribute_names=["context"])
        await self._session.refresh(project, attribute_names=["evidence"])
        return project

    def add_evidence(self, evidence: ProjectEvidence) -> None:
        self._session.add(evidence)

    async def get_evidence(
        self, project_id: UUID, evidence_id: UUID
    ) -> Optional[ProjectEvidence]:
        result = await self._session.execute(
            select(ProjectEvidence).where(
                ProjectEvidence.id == evidence_id,
                ProjectEvidence.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_evidence(self, evidence: ProjectEvidence) -> None:
        await self._session.delete(evidence)
