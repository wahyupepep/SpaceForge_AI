from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.agents.quality import (
    QAAnalystAgent,
    QualityInput,
    SAReviewerAgent,
)
from app.artifacts.schemas import UIPrototypeContent, validate_artifact_content
from app.core.errors import (
    AgentExecutionError,
    ArtifactDependencyMissingError,
    MaximumRevisionReachedError,
    NotFoundError,
    QualityWorkflowConflictError,
    ServiceUnavailableError,
    TechnicalDesignBlockedError,
)
from app.core.security import sanitized_error
from app.domain.analysis import AgentExecutionStatus
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.quality import QualityWorkflowStatus, ReviewDecision
from app.domain.solution import SolutionWorkflowStatus
from app.models.analysis import AgentExecution
from app.models.artifact import Artifact, ArtifactVersion
from app.models.quality import QualityWorkflow
from app.repositories.quality import QualityRepository
from app.schemas.artifact import ArtifactResponse
from app.schemas.quality import QualityAgentResponse, QualityWorkflowResponse
from app.services.design_generation import DesignGenerationService
from app.services.file_storage import FileStorageService
from app.services.llm import LLMRequest, LLMResult

INPUT_TYPES = (
    ArtifactType.REQUIREMENT_BASELINE,
    ArtifactType.SOLUTION,
    ArtifactType.PROCESS_FLOW,
    ArtifactType.UI_PROTOTYPE,
    ArtifactType.DATABASE_DESIGN,
    ArtifactType.API_SPECIFICATION,
)
REVIEW_TYPES = INPUT_TYPES + (ArtifactType.TEST_SCENARIO, ArtifactType.ACCEPTANCE_CRITERIA)


class QualityGateService:
    def __init__(
        self,
        repository: QualityRepository,
        qa_agent: Optional[QAAnalystAgent],
        reviewer_agent: Optional[SAReviewerAgent],
        design_service: DesignGenerationService,
        storage: FileStorageService,
        max_revisions: int,
    ) -> None:
        self._repository = repository
        self._qa_agent = qa_agent
        self._reviewer_agent = reviewer_agent
        self._design_service = design_service
        self._storage = storage
        self._max_revisions = max_revisions

    async def run_qa(self, project_id: UUID, requirement_id: UUID) -> QualityAgentResponse:
        workflow = await self._repository.get_quality_workflow(project_id, requirement_id)
        if workflow is not None and workflow.status == QualityWorkflowStatus.REVISION_REQUIRED:
            raise QualityWorkflowConflictError(
                "Use the quality revision command while reviewer issues are pending."
            )
        return await self._generate_qa(project_id, requirement_id, [])

    async def run_review(self, project_id: UUID, requirement_id: UUID) -> QualityAgentResponse:
        if self._reviewer_agent is None:
            raise ServiceUnavailableError("OPENAI_API_KEY is required to run SA Reviewer.")
        artifacts = await self._load_artifacts(project_id, requirement_id, REVIEW_TYPES)
        workflow = await self._repository.get_quality_workflow(
            project_id, requirement_id, for_update=True
        )
        if workflow is None:
            raise QualityWorkflowConflictError("Run QA Analyst before SA Reviewer.")
        payload = await self._quality_input(artifacts)
        request = self._reviewer_agent.build_request(payload)
        execution = await self._start_execution(
            project_id, requirement_id, self._reviewer_agent.name, request
        )
        try:
            result = await self._reviewer_agent.analyze(request)
            versions = self._version_snapshot(artifacts)
            execution.status = AgentExecutionStatus.SUCCEEDED
            execution.response_json = result.output.model_dump(mode="json")
            self._apply_usage(execution, result)
            workflow.current_review_execution_id = execution.id
            workflow.reviewed_versions = versions
            workflow.issues_json = [
                issue.model_dump(mode="json") for issue in result.output.issues
            ]
            workflow.status = (
                QualityWorkflowStatus.PASSED
                if result.output.decision == ReviewDecision.PASS
                else QualityWorkflowStatus.REVISION_REQUIRED
            )
            await self._repository.commit()
            await self._repository.refresh_quality_workflow(workflow)
            return QualityAgentResponse(
                execution_id=execution.id,
                workflow=await self._workflow_response(workflow),
                artifacts=[],
            )
        except AgentExecutionError:
            raise
        except Exception as error:
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def revise(
        self, project_id: UUID, requirement_id: UUID, artifact_type: ArtifactType
    ) -> QualityAgentResponse:
        workflow = await self._repository.get_quality_workflow(
            project_id, requirement_id, for_update=True
        )
        if workflow is None or workflow.status != QualityWorkflowStatus.REVISION_REQUIRED:
            raise QualityWorkflowConflictError("No reviewer-requested revision is pending.")
        if workflow.revision_count >= workflow.max_revisions:
            workflow.status = QualityWorkflowStatus.MAX_REVISIONS_REACHED
            await self._repository.commit()
            raise MaximumRevisionReachedError(workflow.max_revisions)

        grouped_targets = self._revision_group(artifact_type)
        feedback = [
            issue for issue in workflow.issues_json if issue.get("artifact") in grouped_targets
        ]
        if not feedback:
            raise QualityWorkflowConflictError(
                f"The current review has no issue assigned to {artifact_type.value}."
            )

        if artifact_type == ArtifactType.PROCESS_FLOW:
            result = await self._design_service.run_flow(project_id, requirement_id, feedback)
        elif artifact_type == ArtifactType.UI_PROTOTYPE:
            result = await self._design_service.run_ui_prototype(
                project_id, requirement_id, feedback
            )
        elif artifact_type in {
            ArtifactType.DATABASE_DESIGN,
            ArtifactType.API_SPECIFICATION,
        }:
            result = await self._design_service.run_technical_architecture(
                project_id, requirement_id, feedback
            )
        elif artifact_type in {
            ArtifactType.TEST_SCENARIO,
            ArtifactType.ACCEPTANCE_CRITERIA,
        }:
            return await self._generate_qa(project_id, requirement_id, feedback, is_revision=True)
        else:
            raise QualityWorkflowConflictError("Artifact is not a reviewer revision target.")

        workflow.revision_count += 1
        workflow.status = QualityWorkflowStatus.READY_FOR_REVIEW
        await self._repository.commit()
        await self._repository.refresh_quality_workflow(workflow)
        return QualityAgentResponse(
            execution_id=result.execution_id,
            workflow=await self._workflow_response(workflow),
            artifacts=result.artifacts,
        )

    async def get(self, project_id: UUID, requirement_id: UUID) -> QualityWorkflowResponse:
        workflow = await self._repository.get_quality_workflow(project_id, requirement_id)
        if workflow is None:
            raise NotFoundError("Quality workflow")
        return await self._workflow_response(workflow)

    async def list(self, project_id: UUID) -> list[QualityWorkflowResponse]:
        return [
            await self._workflow_response(item)
            for item in await self._repository.list_quality_workflows(project_id)
        ]

    async def _generate_qa(
        self,
        project_id: UUID,
        requirement_id: UUID,
        feedback: list[dict],
        *,
        is_revision: bool = False,
    ) -> QualityAgentResponse:
        if self._qa_agent is None:
            raise ServiceUnavailableError("OPENAI_API_KEY is required to run QA Analyst.")
        artifacts = await self._load_artifacts(project_id, requirement_id, INPUT_TYPES)
        payload = await self._quality_input(artifacts, feedback)
        request = self._qa_agent.build_request(payload)
        execution = await self._start_execution(
            project_id, requirement_id, self._qa_agent.name, request
        )
        try:
            result = await self._qa_agent.analyze(request)
            output = result.output
            produced = await self._save_artifacts(
                execution,
                result,
                project_id,
                requirement_id,
                [
                    (ArtifactType.TEST_SCENARIO, output.test_scenario.model_dump(mode="json")),
                    (
                        ArtifactType.ACCEPTANCE_CRITERIA,
                        output.acceptance_criteria.model_dump(mode="json"),
                    ),
                ],
                commit=False,
            )
            workflow = await self._repository.get_quality_workflow(
                project_id, requirement_id, for_update=True
            )
            if workflow is None:
                workflow = QualityWorkflow(
                    project_id=project_id,
                    requirement_id=requirement_id,
                    status=QualityWorkflowStatus.READY_FOR_REVIEW,
                    revision_count=0,
                    max_revisions=self._max_revisions,
                    reviewed_versions={},
                    issues_json=[],
                )
                self._repository.add(workflow)
            else:
                workflow.status = QualityWorkflowStatus.READY_FOR_REVIEW
                workflow.current_review_execution_id = None
                if not is_revision:
                    workflow.issues_json = []
            if is_revision:
                workflow.revision_count += 1
            await self._repository.commit()
            await self._repository.refresh_quality_workflow(workflow)
            return QualityAgentResponse(
                execution_id=execution.id,
                workflow=await self._workflow_response(workflow),
                artifacts=produced,
            )
        except AgentExecutionError:
            raise
        except Exception as error:
            await self._repository.rollback()
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def _load_artifacts(
        self,
        project_id: UUID,
        requirement_id: UUID,
        artifact_types: tuple[ArtifactType, ...],
    ) -> dict[ArtifactType, Artifact]:
        project = await self._repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        requirement = await self._repository.get_requirement(project_id, requirement_id)
        if requirement is None:
            raise NotFoundError("Requirement")
        solution_workflow = await self._repository.get_workflow(project_id, requirement_id)
        solution = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.SOLUTION
        )
        if solution_workflow is None or solution is None:
            raise TechnicalDesignBlockedError()
        if (
            solution_workflow.status != SolutionWorkflowStatus.APPROVED
            or solution_workflow.current_artifact_version_id != self._current_version(solution).id
        ):
            raise TechnicalDesignBlockedError()
        artifacts = {}
        for artifact_type in artifact_types:
            artifact = await self._repository.get_artifact(
                project_id, requirement_id, artifact_type
            )
            if artifact is None or artifact.status != ArtifactStatus.VALIDATED:
                raise ArtifactDependencyMissingError(artifact_type.value)
            artifacts[artifact_type] = artifact
        return artifacts

    async def _quality_input(
        self, artifacts: dict[ArtifactType, Artifact], feedback: Optional[list[dict]] = None
    ) -> QualityInput:
        ui_content = self._current_content(artifacts[ArtifactType.UI_PROTOTYPE])
        manifest = UIPrototypeContent.model_validate(ui_content)
        sources = []
        for screen in manifest.screens:
            body = await self._storage.read(screen.storage_key)
            sources.append({"filename": screen.filename, "source_html": body.decode("utf-8")})
        ui = {**ui_content, "screen_sources": sources}
        return QualityInput(
            requirement=self._current_content(artifacts[ArtifactType.REQUIREMENT_BASELINE]),
            solution=self._current_content(artifacts[ArtifactType.SOLUTION]),
            flow=self._current_content(artifacts[ArtifactType.PROCESS_FLOW]),
            ui=ui,
            database=self._current_content(artifacts[ArtifactType.DATABASE_DESIGN]),
            api=self._current_content(artifacts[ArtifactType.API_SPECIFICATION]),
            test_scenario=(
                self._current_content(artifacts[ArtifactType.TEST_SCENARIO])
                if ArtifactType.TEST_SCENARIO in artifacts
                else None
            ),
            acceptance_criteria=(
                self._current_content(artifacts[ArtifactType.ACCEPTANCE_CRITERIA])
                if ArtifactType.ACCEPTANCE_CRITERIA in artifacts
                else None
            ),
            revision_feedback=feedback or [],
        )

    async def _start_execution(
        self, project_id: UUID, requirement_id: UUID, agent_name: str, request: LLMRequest
    ) -> AgentExecution:
        execution = AgentExecution(
            project_id=project_id,
            requirement_id=requirement_id,
            agent_name=agent_name,
            model=request.model,
            status=AgentExecutionStatus.RUNNING,
            request_json={
                "system_prompt": request.system_prompt,
                "user_prompt": request.user_prompt,
                "model": request.model,
                "max_output_tokens": request.max_output_tokens,
                "temperature": request.temperature,
                "tools": list(request.tools),
            },
        )
        self._repository.add(execution)
        await self._repository.commit()
        return execution

    async def _save_artifacts(
        self,
        execution: AgentExecution,
        result: LLMResult,
        project_id: UUID,
        requirement_id: UUID,
        outputs: list[tuple[ArtifactType, dict]],
        *,
        commit: bool,
    ) -> list[ArtifactResponse]:
        if not isinstance(result.output, BaseModel):
            raise TypeError("Quality agent output was not a validated model.")
        artifacts = []
        versions = []
        for artifact_type, raw_content in outputs:
            content = validate_artifact_content(artifact_type, raw_content)
            artifact = await self._repository.get_artifact(
                project_id, requirement_id, artifact_type, for_update=True
            )
            if artifact is None:
                version = ArtifactVersion(
                    version=1, content_json=content, created_by=execution.agent_name
                )
                artifact = Artifact(
                    project_id=project_id,
                    requirement_id=requirement_id,
                    artifact_type=artifact_type,
                    current_version=1,
                    status=ArtifactStatus.VALIDATED,
                    versions=[version],
                )
                self._repository.add(artifact)
            else:
                version = ArtifactVersion(
                    version=artifact.current_version + 1,
                    content_json=content,
                    created_by=execution.agent_name,
                )
                artifact.versions.append(version)
                artifact.current_version = version.version
                artifact.status = ArtifactStatus.VALIDATED
            artifacts.append(artifact)
            versions.append(version)
        await self._repository.flush()
        execution.status = AgentExecutionStatus.SUCCEEDED
        execution.response_json = result.output.model_dump(mode="json")
        self._apply_usage(execution, result)
        execution.artifact_version_id = versions[0].id
        if commit:
            await self._repository.commit()
        return [self._artifact_response(item) for item in artifacts]

    async def _workflow_response(self, workflow: QualityWorkflow) -> QualityWorkflowResponse:
        current_versions: dict[str, int] = {}
        complete = True
        for artifact_type in REVIEW_TYPES:
            artifact = await self._repository.get_artifact(
                workflow.project_id, workflow.requirement_id, artifact_type
            )
            if artifact is None:
                complete = False
            else:
                current_versions[artifact_type.value] = artifact.current_version
        snapshot_current = complete and workflow.reviewed_versions == current_versions
        passed = workflow.status == QualityWorkflowStatus.PASSED and snapshot_current
        effective_status = workflow.status
        if workflow.status == QualityWorkflowStatus.PASSED and not snapshot_current:
            effective_status = QualityWorkflowStatus.READY_FOR_REVIEW
        decision = None
        if effective_status == QualityWorkflowStatus.PASSED:
            decision = ReviewDecision.PASS
        elif effective_status in {
            QualityWorkflowStatus.REVISION_REQUIRED,
            QualityWorkflowStatus.MAX_REVISIONS_REACHED,
        }:
            decision = ReviewDecision.REVISION_REQUIRED
        return QualityWorkflowResponse(
            id=workflow.id,
            project_id=workflow.project_id,
            requirement_id=workflow.requirement_id,
            status=effective_status,
            decision=decision,
            revision_count=workflow.revision_count,
            max_revisions=workflow.max_revisions,
            development_handoff_allowed=passed,
            reviewed_versions=workflow.reviewed_versions,
            issues=workflow.issues_json,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    async def _record_failure(self, execution: AgentExecution, error: Exception) -> None:
        execution.status = AgentExecutionStatus.FAILED
        execution.error_message = sanitized_error(error)
        await self._repository.commit()

    @staticmethod
    def _revision_group(artifact_type: ArtifactType) -> set[str]:
        if artifact_type in {ArtifactType.DATABASE_DESIGN, ArtifactType.API_SPECIFICATION}:
            return {ArtifactType.DATABASE_DESIGN.value, ArtifactType.API_SPECIFICATION.value}
        if artifact_type in {ArtifactType.TEST_SCENARIO, ArtifactType.ACCEPTANCE_CRITERIA}:
            return {ArtifactType.TEST_SCENARIO.value, ArtifactType.ACCEPTANCE_CRITERIA.value}
        return {artifact_type.value}

    @staticmethod
    def _apply_usage(execution: AgentExecution, result: LLMResult) -> None:
        execution.provider_response_id = result.response_id
        execution.input_tokens = result.usage.input_tokens
        execution.output_tokens = result.usage.output_tokens
        execution.total_tokens = result.usage.total_tokens
        execution.duration_ms = round(result.duration_ms)

    @classmethod
    def _current_version(cls, artifact: Artifact) -> ArtifactVersion:
        return next(item for item in artifact.versions if item.version == artifact.current_version)

    @classmethod
    def _current_content(cls, artifact: Artifact) -> dict:
        return cls._current_version(artifact).content_json

    @staticmethod
    def _version_snapshot(artifacts: dict[ArtifactType, Artifact]) -> dict[str, int]:
        return {key.value: value.current_version for key, value in artifacts.items()}

    @classmethod
    def _artifact_response(cls, artifact: Artifact) -> ArtifactResponse:
        current = cls._current_version(artifact)
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
