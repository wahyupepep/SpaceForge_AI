from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.agents.discovery import (
    ExistingSystemAgentInput,
    ExistingSystemAnalyst,
    ExistingSystemEvidence,
    ResearchAgent,
    ResearchAgentInput,
)
from app.artifacts.schemas import validate_artifact_content
from app.core.errors import (
    AgentExecutionError,
    ArtifactDependencyMissingError,
    NotFoundError,
    ProjectNotReadyError,
    RequirementNotReadyError,
    ServiceUnavailableError,
)
from app.core.security import sanitized_error
from app.domain.analysis import AgentExecutionStatus, RequirementReadiness
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.projects import ProjectStatus
from app.models.analysis import AgentExecution
from app.models.artifact import Artifact, ArtifactVersion
from app.repositories.analysis import RequirementAnalysisRepository
from app.schemas.artifact import ArtifactResponse
from app.schemas.discovery import AnalyzeExistingSystemRequest, SpecialistAnalysisResponse
from app.services.llm import LLMRequest, LLMResult


class DiscoveryAnalysisService:
    def __init__(
        self,
        repository: RequirementAnalysisRepository,
        research_agent: Optional[ResearchAgent],
        existing_system_analyst: Optional[ExistingSystemAnalyst],
    ) -> None:
        self._repository = repository
        self._research_agent = research_agent
        self._existing_system_analyst = existing_system_analyst

    async def run_research(
        self, project_id: UUID, requirement_id: UUID
    ) -> SpecialistAnalysisResponse:
        _project, _requirement, baseline = await self._load_ready_context(
            project_id, requirement_id
        )
        if self._research_agent is None:
            raise ServiceUnavailableError("OPENAI_API_KEY is required to run Research Agent.")
        request = self._research_agent.build_request(
            ResearchAgentInput(requirement_baseline=self._current_content(baseline))
        )
        execution = await self._start_execution(
            project_id, requirement_id, self._research_agent.name, request
        )
        try:
            result = await self._research_agent.analyze(request)
            return await self._save_result(
                execution,
                result,
                project_id,
                requirement_id,
                ArtifactType.RESEARCH,
                self._research_agent.name,
            )
        except AgentExecutionError:
            raise
        except Exception as error:
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def analyze_existing_system(
        self, project_id: UUID, payload: AnalyzeExistingSystemRequest
    ) -> SpecialistAnalysisResponse:
        project, _requirement, baseline = await self._load_ready_context(
            project_id, payload.requirement_id
        )
        if self._existing_system_analyst is None:
            raise ServiceUnavailableError(
                "OPENAI_API_KEY is required to run Existing System Analyst."
            )
        research = await self._repository.get_typed_artifact(
            project_id, payload.requirement_id, ArtifactType.RESEARCH
        )
        previous_artifacts = []
        if research is not None:
            previous_artifacts.append(
                {
                    "artifact_type": ArtifactType.RESEARCH.value,
                    "content": self._current_content(research),
                }
            )
        request = self._existing_system_analyst.build_request(
            ExistingSystemAgentInput(
                project_type=project.project_type,
                project_context={
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
                evidence=[
                    ExistingSystemEvidence.model_validate(item.model_dump())
                    for item in payload.evidence
                ],
                previous_artifacts=previous_artifacts,
            )
        )
        execution = await self._start_execution(
            project_id,
            payload.requirement_id,
            self._existing_system_analyst.name,
            request,
        )
        try:
            result = await self._existing_system_analyst.analyze(request, project.project_type)
            return await self._save_result(
                execution,
                result,
                project_id,
                payload.requirement_id,
                ArtifactType.EXISTING_SYSTEM_ANALYSIS,
                self._existing_system_analyst.name,
            )
        except AgentExecutionError:
            raise
        except Exception as error:
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def _load_ready_context(self, project_id: UUID, requirement_id: UUID):  # type: ignore[no-untyped-def]
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
        baseline = await self._repository.get_typed_artifact(
            project_id, requirement_id, ArtifactType.REQUIREMENT_BASELINE
        )
        if baseline is None:
            raise ArtifactDependencyMissingError(ArtifactType.REQUIREMENT_BASELINE.value)
        return project, requirement, baseline

    async def _start_execution(
        self,
        project_id: UUID,
        requirement_id: UUID,
        agent_name: str,
        request: LLMRequest,
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

    async def _save_result(
        self,
        execution: AgentExecution,
        result: LLMResult,
        project_id: UUID,
        requirement_id: UUID,
        artifact_type: ArtifactType,
        created_by: str,
    ) -> SpecialistAnalysisResponse:
        try:
            output = result.output
            if not isinstance(output, BaseModel):
                raise TypeError("Specialist output was not a validated model.")
            content = validate_artifact_content(artifact_type, output.model_dump(mode="json"))
            artifact = await self._repository.get_typed_artifact(
                project_id, requirement_id, artifact_type, for_update=True
            )
            if artifact is None:
                version = ArtifactVersion(version=1, content_json=content, created_by=created_by)
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
                    created_by=created_by,
                )
                artifact.versions.append(version)
                artifact.current_version = version.version
                artifact.status = ArtifactStatus.VALIDATED
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
            return SpecialistAnalysisResponse(
                execution_id=execution.id,
                artifact=self._artifact_response(artifact),
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
    def _current_content(artifact: Artifact) -> dict:
        return next(
            item.content_json
            for item in artifact.versions
            if item.version == artifact.current_version
        )

    @staticmethod
    def _artifact_response(artifact: Artifact) -> ArtifactResponse:
        current = next(
            item for item in artifact.versions if item.version == artifact.current_version
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
