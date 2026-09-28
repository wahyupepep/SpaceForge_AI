from __future__ import annotations

from typing import Optional, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project


class ProjectRepository(Protocol):
    async def add(self, project: Project) -> Project: ...

    async def get(self, project_id: UUID) -> Optional[Project]: ...

    async def list(self, offset: int, limit: int) -> list[Project]: ...

    async def delete(self, project: Project) -> None: ...

    async def commit(self) -> None: ...

    async def refresh(self, project: Project) -> Project: ...


class SQLAlchemyProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, project: Project) -> Project:
        self._session.add(project)
        return project

    async def get(self, project_id: UUID) -> Optional[Project]:
        result = await self._session.execute(
            select(Project).options(selectinload(Project.context)).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int, limit: int) -> list[Project]:
        result = await self._session.execute(
            select(Project)
            .options(selectinload(Project.context))
            .order_by(Project.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, project: Project) -> None:
        await self._session.delete(project)

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, project: Project) -> Project:
        await self._session.refresh(project)
        await self._session.refresh(project, attribute_names=["context"])
        return project
