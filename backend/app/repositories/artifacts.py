from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.artifacts import ArtifactType
from app.models.artifact import Artifact
from app.models.project import Project
from app.models.quality import QualityWorkflow
from app.models.requirement import Requirement
from app.models.solution import SolutionWorkflow


class ArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_project(self, project_id: UUID) -> Project | None:
        return await self._session.get(Project, project_id)

    async def get_requirement(self, requirement_id: UUID) -> Requirement | None:
        return await self._session.get(Requirement, requirement_id)

    async def add(self, artifact: Artifact) -> None:
        self._session.add(artifact)

    async def get(
        self, project_id: UUID, artifact_id: UUID, *, for_update: bool = False
    ) -> Artifact | None:
        statement = (
            select(Artifact)
            .options(selectinload(Artifact.versions))
            .where(Artifact.id == artifact_id, Artifact.project_id == project_id)
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list(self, project_id: UUID) -> list[Artifact]:
        result = await self._session.execute(
            select(Artifact)
            .options(selectinload(Artifact.versions))
            .where(Artifact.project_id == project_id)
            .order_by(Artifact.updated_at.desc())
        )
        return list(result.scalars().unique().all())

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

    async def get_solution_artifact(
        self, project_id: UUID, requirement_id: UUID
    ) -> Artifact | None:
        result = await self._session.execute(
            select(Artifact)
            .options(selectinload(Artifact.versions))
            .where(
                Artifact.project_id == project_id,
                Artifact.requirement_id == requirement_id,
                Artifact.artifact_type == ArtifactType.SOLUTION,
            )
            .order_by(Artifact.created_at.asc())
            .limit(1)
        )
        return result.scalars().unique().one_or_none()

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

    async def get_requirement_artifacts(
        self, project_id: UUID, requirement_id: UUID
    ) -> list[Artifact]:
        result = await self._session.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.requirement_id == requirement_id,
            )
        )
        return list(result.scalars().all())

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def refresh(self, artifact: Artifact) -> None:
        await self._session.refresh(artifact)
        await self._session.refresh(artifact, attribute_names=["versions"])
