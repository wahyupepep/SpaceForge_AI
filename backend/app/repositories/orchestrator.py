from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artifact import Artifact
from app.models.handoff import HandoffWorkflow
from app.models.orchestrator import OrchestratorExecution, OrchestratorWorkflow
from app.models.project import Project
from app.models.quality import QualityWorkflow
from app.models.requirement import Requirement
from app.models.solution import SolutionWorkflow


class OrchestratorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_project(self, project_id: UUID) -> Project | None:
        result = await self._session.execute(
            select(Project).options(selectinload(Project.context)).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_requirement(self, project_id: UUID, requirement_id: UUID) -> Requirement | None:
        result = await self._session.execute(
            select(Requirement).where(
                Requirement.project_id == project_id, Requirement.id == requirement_id
            )
        )
        return result.scalar_one_or_none()

    async def get_workflow(
        self, project_id: UUID, requirement_id: UUID, *, for_update: bool = False
    ) -> OrchestratorWorkflow | None:
        statement = (
            select(OrchestratorWorkflow)
            .options(selectinload(OrchestratorWorkflow.executions))
            .where(
                OrchestratorWorkflow.project_id == project_id,
                OrchestratorWorkflow.requirement_id == requirement_id,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        return result.scalars().unique().one_or_none()

    async def list_project_workflows(self, project_id: UUID) -> list[OrchestratorWorkflow]:
        result = await self._session.execute(
            select(OrchestratorWorkflow)
            .options(selectinload(OrchestratorWorkflow.executions))
            .where(OrchestratorWorkflow.project_id == project_id)
            .order_by(OrchestratorWorkflow.created_at.asc())
        )
        return list(result.scalars().unique().all())

    async def get_execution(self, execution_id: UUID) -> OrchestratorExecution | None:
        result = await self._session.execute(
            select(OrchestratorExecution).where(OrchestratorExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def try_acquire_lease(
        self, workflow_id: UUID, run_id: UUID, lease_expires_at: datetime
    ) -> bool:
        result = await self._session.execute(
            update(OrchestratorWorkflow)
            .where(
                OrchestratorWorkflow.id == workflow_id,
                or_(
                    OrchestratorWorkflow.active_run_id.is_(None),
                    OrchestratorWorkflow.lease_expires_at < datetime.now(lease_expires_at.tzinfo),
                    OrchestratorWorkflow.active_run_id == run_id,
                ),
            )
            .values(active_run_id=run_id, lease_expires_at=lease_expires_at)
            .returning(OrchestratorWorkflow.id)
        )
        await self._session.commit()
        return result.scalar_one_or_none() is not None

    async def release_lease(self, workflow_id: UUID, run_id: UUID) -> None:
        await self._session.execute(
            update(OrchestratorWorkflow)
            .where(
                OrchestratorWorkflow.id == workflow_id,
                OrchestratorWorkflow.active_run_id == run_id,
            )
            .values(active_run_id=None, lease_expires_at=None)
        )
        await self._session.commit()

    async def list_artifacts(self, project_id: UUID, requirement_id: UUID) -> list[Artifact]:
        result = await self._session.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.requirement_id == requirement_id,
            )
        )
        return list(result.scalars().all())

    async def get_solution_workflow(
        self, project_id: UUID, requirement_id: UUID
    ) -> SolutionWorkflow | None:
        result = await self._session.execute(
            select(SolutionWorkflow).where(
                SolutionWorkflow.project_id == project_id,
                SolutionWorkflow.requirement_id == requirement_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_quality_workflow(
        self, project_id: UUID, requirement_id: UUID
    ) -> QualityWorkflow | None:
        result = await self._session.execute(
            select(QualityWorkflow).where(
                QualityWorkflow.project_id == project_id,
                QualityWorkflow.requirement_id == requirement_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_handoff_workflow(
        self, project_id: UUID, requirement_id: UUID
    ) -> HandoffWorkflow | None:
        result = await self._session.execute(
            select(HandoffWorkflow).where(
                HandoffWorkflow.project_id == project_id,
                HandoffWorkflow.requirement_id == requirement_id,
            )
        )
        return result.scalar_one_or_none()

    def add(self, value: object) -> None:
        self._session.add(value)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def refresh_workflow(self, workflow: OrchestratorWorkflow) -> None:
        await self._session.refresh(workflow)
        await self._session.refresh(workflow, attribute_names=["executions"])

    async def refresh_execution(self, execution: OrchestratorExecution) -> None:
        await self._session.refresh(execution)
