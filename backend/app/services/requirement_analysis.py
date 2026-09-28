from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.agents.requirement_analyst import (
    ClarificationAnswerContext,
    RequirementAnalystAgent,
    RequirementAnalystInput,
)
from app.artifacts.schemas import validate_artifact_content
from app.core.errors import (
    AgentExecutionError,
    ClarificationAnswerInvalidError,
    ClarificationPendingError,
    NotFoundError,
    ProjectNotReadyError,
    ServiceUnavailableError,
)
from app.core.security import sanitized_error
from app.domain.analysis import AgentExecutionStatus, ClarificationStatus, RequirementReadiness
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.projects import ProjectStatus
from app.domain.requirements import RequirementStatus
from app.models.analysis import AgentExecution, RequirementClarification
from app.models.artifact import Artifact, ArtifactVersion
from app.repositories.analysis import RequirementAnalysisRepository
from app.schemas.analysis import (
    AgentExecutionResponse,
    AnswerClarificationsRequest,
    ClarificationResponse,
    RequirementAnalysisResponse,
)
from app.schemas.artifact import ArtifactResponse
from app.schemas.requirement import RequirementResponse
from app.services.llm import LLMRequest


class RequirementAnalysisService:
    def __init__(
        self,
        repository: RequirementAnalysisRepository,
        agent: Optional[RequirementAnalystAgent],
    ) -> None:
        self._repository = repository
        self._agent = agent

    async def analyze(self, project_id: UUID, requirement_id: UUID) -> RequirementAnalysisResponse:
        project = await self._repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        if project.status != ProjectStatus.READY_FOR_ANALYSIS:
            raise ProjectNotReadyError()
        requirement = await self._repository.get_requirement(project_id, requirement_id)
        if requirement is None:
            raise NotFoundError("Requirement")
        if await self._repository.list_pending_clarifications(project_id, requirement_id):
            raise ClarificationPendingError()
        if self._agent is None:
            raise ServiceUnavailableError("OPENAI_API_KEY is required to run Requirement Analyst.")

        clarifications = await self._repository.list_clarifications(project_id, requirement_id)
        input_data = RequirementAnalystInput(
            project_context={
                "name": project.name,
                "description": project.description,
                "project_type": project.project_type.value,
                "business_objective": project.business_objective,
                "current_flow": project.context.current_flow,
                "current_actors": project.context.current_actors,
                "current_rules": project.context.current_rules,
                "current_problem": project.context.current_problem,
                "requested_change": project.context.requested_change,
                "constraints": project.context.constraints,
                "notes": project.context.notes,
            },
            raw_requirement=requirement.raw_requirement,
            requirement_context={
                "title": requirement.title,
                "business_objective": requirement.business_objective,
                "actors": requirement.actors,
                "known_rules": requirement.known_rules,
                "constraints": requirement.constraints,
                "dependencies": requirement.dependencies,
            },
            clarification_answers=[
                ClarificationAnswerContext(question=item.question, answer=item.answer or "")
                for item in clarifications
                if item.status == ClarificationStatus.ANSWERED
            ],
        )
        request = self._agent.build_request(input_data)
        execution = AgentExecution(
            project_id=project_id,
            requirement_id=requirement_id,
            agent_name=self._agent.name,
            model=request.model,
            status=AgentExecutionStatus.RUNNING,
            request_json=self._request_audit(request),
        )
        self._repository.add(execution)
        await self._repository.commit()

        try:
            result = await self._agent.analyze(request)
        except Exception as error:
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

        try:
            output = result.output
            content = validate_artifact_content(
                ArtifactType.REQUIREMENT_BASELINE,
                {
                    **output.baseline.model_dump(mode="json"),
                    "readiness": output.readiness,
                    "clarification_questions": output.clarification_questions,
                    "blocked_reason": output.blocked_reason,
                },
            )
            artifact = await self._repository.get_baseline_artifact(
                project_id, requirement_id, for_update=True
            )
            artifact_status = (
                ArtifactStatus.VALIDATED
                if output.readiness == RequirementReadiness.READY
                else ArtifactStatus.DRAFT
            )
            if artifact is None:
                version = ArtifactVersion(
                    version=1,
                    content_json=content,
                    created_by=self._agent.name,
                )
                artifact = Artifact(
                    project_id=project_id,
                    requirement_id=requirement_id,
                    artifact_type=ArtifactType.REQUIREMENT_BASELINE,
                    current_version=1,
                    status=artifact_status,
                    versions=[version],
                )
                self._repository.add(artifact)
            else:
                version = ArtifactVersion(
                    version=artifact.current_version + 1,
                    content_json=content,
                    created_by=self._agent.name,
                )
                artifact.versions.append(version)
                artifact.current_version = version.version
                artifact.status = artifact_status

            requirement.analysis_readiness = output.readiness
            requirement.status = (
                RequirementStatus.BASELINED
                if output.readiness == RequirementReadiness.READY
                else RequirementStatus.DRAFT
            )
            await self._repository.flush()

            new_questions = [
                RequirementClarification(
                    project_id=project_id,
                    requirement_id=requirement_id,
                    agent_execution_id=execution.id,
                    question=question.strip(),
                    status=ClarificationStatus.PENDING,
                )
                for question in output.clarification_questions
            ]
            self._repository.add_all(new_questions)
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
        except Exception as error:
            await self._repository.rollback()
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

        all_clarifications = await self._repository.list_clarifications(project_id, requirement_id)
        return RequirementAnalysisResponse(
            execution_id=execution.id,
            readiness=output.readiness,
            requirement=RequirementResponse.model_validate(requirement),
            artifact=self._artifact_response(artifact),
            clarifications=[
                ClarificationResponse.model_validate(item) for item in all_clarifications
            ],
        )

    async def answer_clarifications(
        self,
        project_id: UUID,
        requirement_id: UUID,
        payload: AnswerClarificationsRequest,
    ) -> RequirementAnalysisResponse:
        project = await self._repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        if project.status != ProjectStatus.READY_FOR_ANALYSIS:
            raise ProjectNotReadyError()
        if await self._repository.get_requirement(project_id, requirement_id) is None:
            raise NotFoundError("Requirement")

        pending = await self._repository.list_pending_clarifications(project_id, requirement_id)
        pending_by_id = {item.id: item for item in pending}
        submitted_ids = [item.clarification_id for item in payload.answers]
        if len(set(submitted_ids)) != len(submitted_ids):
            raise ClarificationAnswerInvalidError("Clarification IDs must be unique.")
        if set(submitted_ids) != set(pending_by_id):
            raise ClarificationAnswerInvalidError(
                "Submit exactly one answer for every pending clarification."
            )

        answered_at = datetime.now(timezone.utc)
        for submitted in payload.answers:
            clarification = pending_by_id[submitted.clarification_id]
            clarification.answer = submitted.answer
            clarification.status = ClarificationStatus.ANSWERED
            clarification.answered_by = payload.answered_by
            clarification.answered_at = answered_at
        await self._repository.commit()
        return await self.analyze(project_id, requirement_id)

    async def list_clarifications(
        self, project_id: UUID, requirement_id: UUID
    ) -> list[ClarificationResponse]:
        if await self._repository.get_requirement(project_id, requirement_id) is None:
            raise NotFoundError("Requirement")
        return [
            ClarificationResponse.model_validate(item)
            for item in await self._repository.list_clarifications(project_id, requirement_id)
        ]

    async def list_history(
        self, project_id: UUID, requirement_id: UUID
    ) -> list[AgentExecutionResponse]:
        if await self._repository.get_requirement(project_id, requirement_id) is None:
            raise NotFoundError("Requirement")
        return [
            AgentExecutionResponse.model_validate(item)
            for item in await self._repository.list_executions(project_id, requirement_id)
        ]

    async def _record_failure(self, execution: AgentExecution, error: Exception) -> None:
        execution.status = AgentExecutionStatus.FAILED
        execution.error_message = sanitized_error(error)
        await self._repository.commit()

    @staticmethod
    def _request_audit(request: LLMRequest) -> dict:
        return {
            "system_prompt": request.system_prompt,
            "user_prompt": request.user_prompt,
            "model": request.model,
            "max_output_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "tools": list(request.tools),
        }

    @staticmethod
    def _artifact_response(artifact: Artifact) -> ArtifactResponse:
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
