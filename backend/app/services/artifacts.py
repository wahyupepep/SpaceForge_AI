from typing import Optional
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.artifacts.schemas import validate_artifact_content
from app.core.errors import (
    ArtifactConflictError,
    ArtifactContentInvalidError,
    NotFoundError,
    ProjectNotReadyError,
    QualityGateBlockedError,
    TechnicalDesignBlockedError,
)
from app.domain.artifacts import APPROVAL_GATED_ARTIFACT_TYPES, ArtifactType
from app.domain.projects import ProjectStatus
from app.domain.quality import QualityWorkflowStatus
from app.domain.requirements import RequirementStatus
from app.domain.solution import SolutionWorkflowStatus
from app.models.artifact import Artifact, ArtifactVersion
from app.repositories.artifacts import ArtifactRepository
from app.schemas.artifact import ArtifactCreate, ArtifactResponse, ArtifactVersionCreate


class ArtifactService:
    def __init__(self, repository: ArtifactRepository) -> None:
        self._repository = repository

    @staticmethod
    def _validated(artifact_type: ArtifactType, content: dict) -> dict:
        try:
            return validate_artifact_content(artifact_type, content)
        except ValidationError as error:
            raise ArtifactContentInvalidError(error.errors(include_url=False)) from error

    @staticmethod
    def _response(artifact: Artifact) -> ArtifactResponse:
        current = next(
            version for version in artifact.versions if version.version == artifact.current_version
        )
        return ArtifactResponse(
            id=artifact.id,
            project_id=artifact.project_id,
            requirement_id=artifact.requirement_id,
            artifact_type=artifact.artifact_type,
            version=current.version,
            content_json=current.content_json,
            status=artifact.status,
            created_by=current.created_by,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
            versions=artifact.versions,
        )

    async def _ensure_solution_approved(
        self,
        project_id: UUID,
        requirement_id: Optional[UUID],
        artifact_type: ArtifactType,
    ) -> None:
        if artifact_type not in APPROVAL_GATED_ARTIFACT_TYPES:
            return
        if requirement_id is None:
            raise TechnicalDesignBlockedError()
        workflow = await self._repository.get_solution_workflow(project_id, requirement_id)
        solution = await self._repository.get_solution_artifact(project_id, requirement_id)
        if workflow is None or solution is None:
            raise TechnicalDesignBlockedError()
        current = next(
            item for item in solution.versions if item.version == solution.current_version
        )
        if (
            workflow.status != SolutionWorkflowStatus.APPROVED
            or workflow.current_artifact_version_id != current.id
        ):
            raise TechnicalDesignBlockedError()

    async def _ensure_quality_passed(
        self,
        project_id: UUID,
        requirement_id: Optional[UUID],
        artifact_type: ArtifactType,
    ) -> None:
        if artifact_type != ArtifactType.DEVELOPMENT_TASK:
            return
        if requirement_id is None:
            raise QualityGateBlockedError()
        workflow = await self._repository.get_quality_workflow(project_id, requirement_id)
        if workflow is None or workflow.status != QualityWorkflowStatus.PASSED:
            raise QualityGateBlockedError()
        artifacts = await self._repository.get_requirement_artifacts(project_id, requirement_id)
        current_versions = {
            artifact.artifact_type.value: artifact.current_version
            for artifact in artifacts
            if artifact.artifact_type
            in {
                ArtifactType.REQUIREMENT_BASELINE,
                ArtifactType.SOLUTION,
                ArtifactType.PROCESS_FLOW,
                ArtifactType.UI_PROTOTYPE,
                ArtifactType.DATABASE_DESIGN,
                ArtifactType.API_SPECIFICATION,
                ArtifactType.TEST_SCENARIO,
                ArtifactType.ACCEPTANCE_CRITERIA,
            }
        }
        if workflow.reviewed_versions != current_versions:
            raise QualityGateBlockedError("Artifacts changed after the last passing review.")

    async def create(self, project_id: UUID, payload: ArtifactCreate) -> ArtifactResponse:
        project = await self._repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        if project.status != ProjectStatus.READY_FOR_ANALYSIS:
            raise ProjectNotReadyError()
        requirement = None
        if payload.requirement_id is not None:
            requirement = await self._repository.get_requirement(payload.requirement_id)
            if requirement is None or requirement.project_id != project_id:
                raise NotFoundError("Requirement")
        await self._ensure_solution_approved(
            project_id, payload.requirement_id, payload.artifact_type
        )
        await self._ensure_quality_passed(
            project_id, payload.requirement_id, payload.artifact_type
        )

        content = self._validated(payload.artifact_type, payload.content_json)
        artifact = Artifact(
            project_id=project_id,
            requirement_id=payload.requirement_id,
            artifact_type=payload.artifact_type,
            current_version=1,
            status=payload.status,
            versions=[
                ArtifactVersion(version=1, content_json=content, created_by=payload.created_by)
            ],
        )
        await self._repository.add(artifact)
        if requirement is not None and payload.artifact_type == ArtifactType.REQUIREMENT_BASELINE:
            requirement.status = RequirementStatus.BASELINED
        try:
            await self._repository.commit()
        except IntegrityError as error:
            await self._repository.rollback()
            raise ArtifactConflictError() from error
        await self._repository.refresh(artifact)
        return self._response(artifact)

    async def list(self, project_id: UUID) -> list[ArtifactResponse]:
        if await self._repository.get_project(project_id) is None:
            raise NotFoundError("Project")
        return [self._response(item) for item in await self._repository.list(project_id)]

    async def get(self, project_id: UUID, artifact_id: UUID) -> ArtifactResponse:
        artifact = await self._repository.get(project_id, artifact_id)
        if artifact is None:
            raise NotFoundError("Artifact")
        return self._response(artifact)

    async def create_version(
        self, project_id: UUID, artifact_id: UUID, payload: ArtifactVersionCreate
    ) -> ArtifactResponse:
        project = await self._repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        if project.status != ProjectStatus.READY_FOR_ANALYSIS:
            raise ProjectNotReadyError()
        artifact = await self._repository.get(project_id, artifact_id, for_update=True)
        if artifact is None:
            raise NotFoundError("Artifact")
        await self._ensure_solution_approved(
            project_id, artifact.requirement_id, artifact.artifact_type
        )
        await self._ensure_quality_passed(
            project_id, artifact.requirement_id, artifact.artifact_type
        )
        content = self._validated(artifact.artifact_type, payload.content_json)
        next_version = artifact.current_version + 1
        artifact.versions.append(
            ArtifactVersion(
                version=next_version, content_json=content, created_by=payload.created_by
            )
        )
        artifact.current_version = next_version
        if payload.status is not None:
            artifact.status = payload.status
        try:
            await self._repository.commit()
        except IntegrityError as error:
            await self._repository.rollback()
            raise ArtifactConflictError() from error
        await self._repository.refresh(artifact)
        return self._response(artifact)
