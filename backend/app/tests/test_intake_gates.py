from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import (
    ArtifactConflictError,
    ProjectNotReadyError,
    TechnicalDesignBlockedError,
)
from app.domain.artifacts import ArtifactType
from app.domain.projects import ProjectStatus
from app.schemas.artifact import ArtifactCreate, ArtifactVersionCreate
from app.schemas.requirement import RequirementCreate
from app.services.artifacts import ArtifactService
from app.services.requirements import RequirementService


@pytest.mark.asyncio
async def test_requirement_create_requires_ready_project() -> None:
    repository = AsyncMock()
    repository.get_project.return_value = SimpleNamespace(status=ProjectStatus.DRAFT)
    service = RequirementService(repository)

    with pytest.raises(ProjectNotReadyError):
        await service.create(
            uuid4(),
            RequirementCreate(title="Approval", raw_requirement="Add approval tiers."),
        )


@pytest.mark.asyncio
async def test_artifact_writes_require_ready_project() -> None:
    repository = AsyncMock()
    repository.get_project.return_value = SimpleNamespace(status=ProjectStatus.DRAFT)
    service = ArtifactService(repository)
    project_id = uuid4()

    with pytest.raises(ProjectNotReadyError):
        await service.create(
            project_id,
            ArtifactCreate(
                artifact_type=ArtifactType.REQUIREMENT_BASELINE,
                content_json={},
            ),
        )

    with pytest.raises(ProjectNotReadyError):
        await service.create_version(
            project_id,
            uuid4(),
            ArtifactVersionCreate(content_json={}),
        )


@pytest.mark.asyncio
async def test_downstream_artifact_cannot_bypass_solution_approval() -> None:
    repository = AsyncMock()
    project_id = uuid4()
    requirement_id = uuid4()
    repository.get_project.return_value = SimpleNamespace(status=ProjectStatus.READY_FOR_ANALYSIS)
    repository.get_requirement.return_value = SimpleNamespace(
        id=requirement_id, project_id=project_id
    )
    repository.get_solution_workflow.return_value = None
    repository.get_solution_artifact.return_value = None
    service = ArtifactService(repository)

    with pytest.raises(TechnicalDesignBlockedError):
        await service.create(
            project_id,
            ArtifactCreate(
                artifact_type=ArtifactType.DATABASE_DESIGN,
                requirement_id=requirement_id,
                content_json={"entities": [], "relationships": [], "constraints": []},
            ),
        )

    repository.add.assert_not_called()


@pytest.mark.asyncio
async def test_duplicate_artifact_rolls_back_as_conflict() -> None:
    repository = AsyncMock()
    repository.get_project.return_value = SimpleNamespace(
        status=ProjectStatus.READY_FOR_ANALYSIS
    )
    repository.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    service = ArtifactService(repository)

    with pytest.raises(ArtifactConflictError):
        await service.create(
            uuid4(),
            ArtifactCreate(
                artifact_type=ArtifactType.PROJECT_CONTEXT,
                content_json={
                    "project_name": "Approval",
                    "project_type": "NEW_FEATURE",
                    "business_objective": "Reduce risk",
                    "context": {},
                },
            ),
        )

    repository.rollback.assert_awaited_once()
