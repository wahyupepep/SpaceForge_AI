from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import QualityWorkflow
from app.repositories.solution import SolutionRepository


class QualityRepository(SolutionRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._session = session

    async def get_quality_workflow(
        self, project_id: UUID, requirement_id: UUID, *, for_update: bool = False
    ) -> QualityWorkflow | None:
        statement = select(QualityWorkflow).where(
            QualityWorkflow.project_id == project_id,
            QualityWorkflow.requirement_id == requirement_id,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_quality_workflows(self, project_id: UUID) -> list[QualityWorkflow]:
        result = await self._session.execute(
            select(QualityWorkflow)
            .where(QualityWorkflow.project_id == project_id)
            .order_by(QualityWorkflow.created_at.asc())
        )
        return list(result.scalars().all())

    async def refresh_quality_workflow(self, workflow: QualityWorkflow) -> None:
        await self._session.refresh(workflow)
