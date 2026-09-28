from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.handoff import HandoffPackageVersion, HandoffWorkflow
from app.repositories.quality import QualityRepository


class HandoffRepository(QualityRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._session = session

    async def get_handoff_workflow(
        self, project_id: UUID, requirement_id: UUID, *, for_update: bool = False
    ) -> HandoffWorkflow | None:
        statement = (
            select(HandoffWorkflow)
            .options(selectinload(HandoffWorkflow.packages))
            .where(
                HandoffWorkflow.project_id == project_id,
                HandoffWorkflow.requirement_id == requirement_id,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        return result.scalars().unique().one_or_none()

    async def get_package(
        self,
        project_id: UUID,
        requirement_id: UUID,
        version: int,
    ) -> HandoffPackageVersion | None:
        result = await self._session.execute(
            select(HandoffPackageVersion)
            .join(HandoffWorkflow)
            .where(
                HandoffWorkflow.project_id == project_id,
                HandoffWorkflow.requirement_id == requirement_id,
                HandoffPackageVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def refresh_handoff_workflow(self, workflow: HandoffWorkflow) -> None:
        await self._session.refresh(workflow)
        await self._session.refresh(workflow, attribute_names=["packages"])
