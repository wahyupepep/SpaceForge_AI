from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.analysis import ClarificationStatus
from app.domain.artifacts import ArtifactType
from app.models.analysis import AgentExecution, RequirementClarification
from app.models.artifact import Artifact
from app.models.project import Project
from app.models.requirement import Requirement


class RequirementAnalysisRepository:
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
                Requirement.id == requirement_id,
                Requirement.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_baseline_artifact(
        self, project_id: UUID, requirement_id: UUID, *, for_update: bool = False
    ) -> Artifact | None:
        statement = (
            select(Artifact)
            .options(selectinload(Artifact.versions))
            .where(
                Artifact.project_id == project_id,
                Artifact.requirement_id == requirement_id,
                Artifact.artifact_type == ArtifactType.REQUIREMENT_BASELINE,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        return result.scalars().unique().one_or_none()

    async def get_typed_artifact(
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

    async def list_clarifications(
        self, project_id: UUID, requirement_id: UUID
    ) -> list[RequirementClarification]:
        result = await self._session.execute(
            select(RequirementClarification)
            .where(
                RequirementClarification.project_id == project_id,
                RequirementClarification.requirement_id == requirement_id,
            )
            .order_by(RequirementClarification.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_pending_clarifications(
        self, project_id: UUID, requirement_id: UUID
    ) -> list[RequirementClarification]:
        result = await self._session.execute(
            select(RequirementClarification).where(
                RequirementClarification.project_id == project_id,
                RequirementClarification.requirement_id == requirement_id,
                RequirementClarification.status == ClarificationStatus.PENDING,
            )
        )
        return list(result.scalars().all())

    async def list_executions(self, project_id: UUID, requirement_id: UUID) -> list[AgentExecution]:
        result = await self._session.execute(
            select(AgentExecution)
            .where(
                AgentExecution.project_id == project_id,
                AgentExecution.requirement_id == requirement_id,
            )
            .order_by(AgentExecution.created_at.desc())
        )
        return list(result.scalars().all())

    def add(self, value: object) -> None:
        self._session.add(value)

    def add_all(self, values: list[object]) -> None:
        self._session.add_all(values)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def refresh_artifact(self, artifact: Artifact) -> None:
        await self._session.refresh(artifact)
        await self._session.refresh(artifact, attribute_names=["versions"])
