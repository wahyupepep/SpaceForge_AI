from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.agents.solution_analyst import SolutionAgentInput, SolutionAnalyst
from app.artifacts.schemas import validate_artifact_content
from app.core.errors import (
    AgentExecutionError,
    ArtifactDependencyMissingError,
    NotFoundError,
    ProjectNotReadyError,
    RequirementNotReadyError,
    ServiceUnavailableError,
    SolutionWorkflowConflictError,
    TechnicalDesignBlockedError,
)
from app.core.security import sanitized_error
from app.domain.analysis import AgentExecutionStatus, RequirementReadiness
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.projects import ProjectStatus
from app.domain.solution import SolutionApprovalAction, SolutionWorkflowStatus
from app.models.analysis import AgentExecution
from app.models.artifact import Artifact, ArtifactVersion
from app.models.solution import SolutionApproval, SolutionWorkflow
from app.repositories.solution import SolutionRepository
from app.schemas.artifact import ArtifactResponse
from app.schemas.solution import (
    SolutionAnalysisResponse,
    SolutionApprovalRequest,
    SolutionWorkflowResponse,
)
from app.services.llm import LLMRequest, LLMResult


class SolutionAnalysisService:
    def __init__(self, repository: SolutionRepository, agent: Optional[SolutionAnalyst]) -> None:
        self._repository = repository
        self._agent = agent

    async def generate(self, project_id: UUID, requirement_id: UUID) -> SolutionAnalysisResponse:
        project, _requirement, baseline, research, existing = await self._load_inputs(
            project_id, requirement_id
        )
        if await self._repository.get_workflow(project_id, requirement_id) is not None:
            raise SolutionWorkflowConflictError(
                "A Solution workflow already exists; use REQUEST_REVISION to create a new version."
            )
        return await self._execute(
            project,
            requirement_id,
            baseline,
            research,
            existing,
            previous_solution=None,
            revision_note=None,
        )

    async def act(
        self, project_id: UUID, requirement_id: UUID, payload: SolutionApprovalRequest
    ) -> SolutionWorkflowResponse:
        workflow = await self._repository.get_workflow(project_id, requirement_id, for_update=True)
        if workflow is None:
            raise NotFoundError("Solution workflow")
        artifact = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.SOLUTION, for_update=True
        )
        if artifact is None:
            raise ArtifactDependencyMissingError(ArtifactType.SOLUTION.value)
        if workflow.status != SolutionWorkflowStatus.WAITING_USER_APPROVAL:
            raise SolutionWorkflowConflictError(
                "Only a Solution waiting for user approval can receive an approval action."
            )
        if payload.expected_version != artifact.current_version:
            raise SolutionWorkflowConflictError(
                f"Solution version changed; expected v{payload.expected_version}, "
                f"current version is v{artifact.current_version}."
            )
        current = self._current_version(artifact)
        if workflow.current_artifact_version_id != current.id:
            raise SolutionWorkflowConflictError(
                "The active Solution version is not the version awaiting approval."
            )
        approval = SolutionApproval(
            workflow_id=workflow.id,
            project_id=project_id,
            requirement_id=requirement_id,
            artifact_version_id=current.id,
            action=payload.action,
            note=payload.note,
            acted_by=payload.acted_by,
        )
        self._repository.add(approval)

        if payload.action == SolutionApprovalAction.APPROVE:
            workflow.status = SolutionWorkflowStatus.APPROVED
            artifact.status = ArtifactStatus.VALIDATED
            await self._repository.commit()
            await self._repository.refresh_artifact(artifact)
            await self._repository.refresh_workflow(workflow)
            return self._workflow_response(workflow, artifact)
        if payload.action == SolutionApprovalAction.REJECT:
            workflow.status = SolutionWorkflowStatus.REJECTED
            artifact.status = ArtifactStatus.DRAFT
            await self._repository.commit()
            await self._repository.refresh_artifact(artifact)
            await self._repository.refresh_workflow(workflow)
            return self._workflow_response(workflow, artifact)

        workflow.status = SolutionWorkflowStatus.REVISION_REQUESTED
        artifact.status = ArtifactStatus.DRAFT
        await self._repository.commit()

        project, _requirement, baseline, research, existing = await self._load_inputs(
            project_id, requirement_id
        )
        result = await self._execute(
            project,
            requirement_id,
            baseline,
            research,
            existing,
            previous_solution=current.content_json,
            revision_note=payload.note,
        )
        return result.workflow

    async def get(self, project_id: UUID, requirement_id: UUID) -> SolutionWorkflowResponse:
        workflow = await self._repository.get_workflow(project_id, requirement_id)
        if workflow is None:
            raise NotFoundError("Solution workflow")
        artifact = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.SOLUTION
        )
        if artifact is None:
            raise ArtifactDependencyMissingError(ArtifactType.SOLUTION.value)
        return self._workflow_response(workflow, artifact)

    async def retry_revision(
        self, project_id: UUID, requirement_id: UUID
    ) -> SolutionAnalysisResponse:
        workflow = await self._repository.get_workflow(project_id, requirement_id)
        if workflow is None or workflow.status != SolutionWorkflowStatus.REVISION_REQUESTED:
            raise SolutionWorkflowConflictError(
                "Only a failed pending Solution revision can be retried."
            )
        artifact = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.SOLUTION
        )
        if artifact is None:
            raise ArtifactDependencyMissingError(ArtifactType.SOLUTION.value)
        current = self._current_version(artifact)
        revision = next(
            (
                item
                for item in reversed(workflow.approvals)
                if item.action == SolutionApprovalAction.REQUEST_REVISION
                and item.artifact_version_id == current.id
            ),
            None,
        )
        if revision is None or not revision.note:
            raise SolutionWorkflowConflictError(
                "The pending revision has no auditable revision note."
            )
        project, _requirement, baseline, research, existing = await self._load_inputs(
            project_id, requirement_id
        )
        return await self._execute(
            project,
            requirement_id,
            baseline,
            research,
            existing,
            previous_solution=current.content_json,
            revision_note=revision.note,
        )

    async def list(self, project_id: UUID) -> list[SolutionWorkflowResponse]:
        result = []
        for workflow in await self._repository.list_workflows(project_id):
            artifact = await self._repository.get_artifact(
                project_id, workflow.requirement_id, ArtifactType.SOLUTION
            )
            if artifact is not None:
                result.append(self._workflow_response(workflow, artifact))
        return result

    async def ensure_technical_design_allowed(self, project_id: UUID, requirement_id: UUID) -> None:
        workflow = await self._repository.get_workflow(project_id, requirement_id)
        artifact = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.SOLUTION
        )
        if (
            workflow is None
            or artifact is None
            or workflow.status != SolutionWorkflowStatus.APPROVED
            or workflow.current_artifact_version_id != self._current_version(artifact).id
        ):
            raise TechnicalDesignBlockedError()

    async def _execute(
        self,
        project,
        requirement_id: UUID,
        baseline: Artifact,
        research: Artifact,
        existing: Optional[Artifact],
        *,
        previous_solution: Optional[dict],
        revision_note: Optional[str],
    ) -> SolutionAnalysisResponse:  # type: ignore[no-untyped-def]
        if self._agent is None:
            raise ServiceUnavailableError("OPENAI_API_KEY is required to run Solution Analyst.")
        request = self._agent.build_request(
            SolutionAgentInput(
                project_type=project.project_type,
                project_context={
                    "name": project.name,
                    "description": project.description,
                    "business_objective": project.business_objective,
                    "current_flow": project.context.current_flow,
                    "current_actors": project.context.current_actors,
                    "current_rules": project.context.current_rules,
                    "current_problem": project.context.current_problem,
                    "requested_change": project.context.requested_change,
                    "constraints": project.context.constraints,
                    "notes": project.context.notes,
                },
                requirement_baseline=self._current_content(baseline),
                research_artifact=self._current_content(research),
                existing_system_analysis=(
                    self._current_content(existing) if existing is not None else None
                ),
                previous_solution=previous_solution,
                revision_note=revision_note,
            )
        )
        execution = await self._start_execution(project.id, requirement_id, request)
        try:
            result = await self._agent.analyze(request, project.project_type)
            return await self._save_result(execution, result, project.id, requirement_id)
        except AgentExecutionError:
            raise
        except Exception as error:
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def _load_inputs(self, project_id: UUID, requirement_id: UUID):  # type: ignore[no-untyped-def]
        project = await self._repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        if project.status != ProjectStatus.READY_FOR_ANALYSIS:
            raise ProjectNotReadyError()
        requirement = await self._repository.get_requirement(project_id, requirement_id)
        if requirement is None:
            raise NotFoundError("Requirement")
        if requirement.analysis_readiness != RequirementReadiness.READY:
            raise RequirementNotReadyError()
        baseline = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.REQUIREMENT_BASELINE
        )
        if baseline is None:
            raise ArtifactDependencyMissingError(ArtifactType.REQUIREMENT_BASELINE.value)
        research = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.RESEARCH
        )
        if research is None:
            raise ArtifactDependencyMissingError(ArtifactType.RESEARCH.value)
        existing = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.EXISTING_SYSTEM_ANALYSIS
        )
        return project, requirement, baseline, research, existing

    async def _start_execution(
        self, project_id: UUID, requirement_id: UUID, request: LLMRequest
    ) -> AgentExecution:
        execution = AgentExecution(
            project_id=project_id,
            requirement_id=requirement_id,
            agent_name=self._agent.name if self._agent else "SOLUTION_ANALYST",
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

    async def _save_result(
        self,
        execution: AgentExecution,
        result: LLMResult,
        project_id: UUID,
        requirement_id: UUID,
    ) -> SolutionAnalysisResponse:
        try:
            output = result.output
            if not isinstance(output, BaseModel):
                raise TypeError("Solution Analyst output was not a validated model.")
            content = validate_artifact_content(
                ArtifactType.SOLUTION, output.model_dump(mode="json")
            )
            artifact = await self._repository.get_artifact(
                project_id, requirement_id, ArtifactType.SOLUTION, for_update=True
            )
            if artifact is None:
                version = ArtifactVersion(
                    version=1, content_json=content, created_by="SOLUTION_ANALYST"
                )
                artifact = Artifact(
                    project_id=project_id,
                    requirement_id=requirement_id,
                    artifact_type=ArtifactType.SOLUTION,
                    current_version=1,
                    status=ArtifactStatus.DRAFT,
                    versions=[version],
                )
                self._repository.add(artifact)
                await self._repository.flush()
                workflow = SolutionWorkflow(
                    project_id=project_id,
                    requirement_id=requirement_id,
                    solution_artifact_id=artifact.id,
                    current_artifact_version_id=version.id,
                    status=SolutionWorkflowStatus.WAITING_USER_APPROVAL,
                )
                self._repository.add(workflow)
            else:
                workflow = await self._repository.get_workflow(
                    project_id, requirement_id, for_update=True
                )
                if workflow is None or workflow.status != SolutionWorkflowStatus.REVISION_REQUESTED:
                    raise SolutionWorkflowConflictError("Solution revision was not requested.")
                version = ArtifactVersion(
                    version=artifact.current_version + 1,
                    content_json=content,
                    created_by="SOLUTION_ANALYST",
                )
                artifact.versions.append(version)
                artifact.current_version = version.version
                artifact.status = ArtifactStatus.DRAFT
                await self._repository.flush()
                workflow.current_artifact_version_id = version.id
                workflow.status = SolutionWorkflowStatus.WAITING_USER_APPROVAL
            await self._repository.flush()
            execution.status = AgentExecutionStatus.SUCCEEDED
            execution.response_json = output.model_dump(mode="json")
            execution.provider_response_id = result.response_id
            execution.input_tokens = result.usage.input_tokens
            execution.output_tokens = result.usage.output_tokens
            execution.total_tokens = result.usage.total_tokens
            execution.duration_ms = round(result.duration_ms)
            execution.artifact_version_id = version.id
            await self._repository.commit()
            await self._repository.refresh_artifact(artifact)
            await self._repository.refresh_workflow(workflow)
            return SolutionAnalysisResponse(
                execution_id=execution.id,
                workflow=self._workflow_response(workflow, artifact),
            )
        except Exception as error:
            await self._repository.rollback()
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def _record_failure(self, execution: AgentExecution, error: Exception) -> None:
        execution.status = AgentExecutionStatus.FAILED
        execution.error_message = sanitized_error(error)
        await self._repository.commit()

    @staticmethod
    def _current_version(artifact: Artifact) -> ArtifactVersion:
        return next(item for item in artifact.versions if item.version == artifact.current_version)

    @classmethod
    def _current_content(cls, artifact: Artifact) -> dict:
        return cls._current_version(artifact).content_json

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

    @classmethod
    def _workflow_response(
        cls, workflow: SolutionWorkflow, artifact: Artifact
    ) -> SolutionWorkflowResponse:
        current = cls._current_version(artifact)
        return SolutionWorkflowResponse(
            id=workflow.id,
            project_id=workflow.project_id,
            requirement_id=workflow.requirement_id,
            status=workflow.status,
            current_version=artifact.current_version,
            technical_design_allowed=(
                workflow.status == SolutionWorkflowStatus.APPROVED
                and workflow.current_artifact_version_id == current.id
            ),
            artifact=cls._artifact_response(artifact),
            approvals=workflow.approvals,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )
