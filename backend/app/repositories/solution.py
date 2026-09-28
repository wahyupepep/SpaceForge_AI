from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.artifacts import ArtifactType
from app.models.artifact import Artifact
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.solution import SolutionWorkflow


class SolutionRepository:
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

    async def get_artifact(
        self,
        project_id: UUID,
        requirement_id: UUID,
        artifact_type: ArtifactType,
        *,
        for_update: bool = False,
    ) -> Artifact | None:
        statement = (
            select(Artifact)
            .options(selectinload(Artifact.versions))
            .where(
                Artifact.project_id == project_id,
                Artifact.requirement_id == requirement_id,
                Artifact.artifact_type == artifact_type,
            )
            .order_by(Artifact.created_at.asc())
            .limit(1)
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        return result.scalars().unique().one_or_none()

    async def get_artifact_by_id(
        self, project_id: UUID, requirement_id: UUID, artifact_id: UUID
    ) -> Artifact | None:
        result = await self._session.execute(
            select(Artifact)
            .options(selectinload(Artifact.versions))
            .where(
                Artifact.id == artifact_id,
                Artifact.project_id == project_id,
                Artifact.requirement_id == requirement_id,
            )
        )
        return result.scalars().unique().one_or_none()

    async def get_workflow(
        self, project_id: UUID, requirement_id: UUID, *, for_update: bool = False
    ) -> SolutionWorkflow | None:
        statement = (
            select(SolutionWorkflow)
            .options(selectinload(SolutionWorkflow.approvals))
            .where(
                SolutionWorkflow.project_id == project_id,
                SolutionWorkflow.requirement_id == requirement_id,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        return result.scalars().unique().one_or_none()

    async def list_workflows(self, project_id: UUID) -> list[SolutionWorkflow]:
        result = await self._session.execute(
            select(SolutionWorkflow)
            .options(selectinload(SolutionWorkflow.approvals))
            .where(SolutionWorkflow.project_id == project_id)
            .order_by(SolutionWorkflow.created_at.asc())
        )
        return list(result.scalars().unique().all())

    def add(self, value: object) -> None:
        self._session.add(value)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def refresh_artifact(self, artifact: Artifact) -> None:
        await self._session.refresh(artifact)
        await self._session.refresh(artifact, attribute_names=["versions"])

    async def refresh_workflow(self, workflow: SolutionWorkflow) -> None:
        await self._session.refresh(workflow)
        await self._session.refresh(workflow, attribute_names=["approvals"])
