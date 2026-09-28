from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.requirement import Requirement


class RequirementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_project(self, project_id: UUID) -> Project | None:
        return await self._session.get(Project, project_id)

    async def add(self, requirement: Requirement) -> None:
        self._session.add(requirement)

    async def get(self, project_id: UUID, requirement_id: UUID) -> Requirement | None:
        result = await self._session.execute(
            select(Requirement).where(
                Requirement.id == requirement_id, Requirement.project_id == project_id
            )
        )
        return result.scalar_one_or_none()

    async def list(self, project_id: UUID) -> list[Requirement]:
        result = await self._session.execute(
            select(Requirement)
            .where(Requirement.project_id == project_id)
            .order_by(Requirement.updated_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, requirement: Requirement) -> None:
        await self._session.delete(requirement)

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, requirement: Requirement) -> None:
        await self._session.refresh(requirement)
