from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.agents.design import (
    ApprovedDesignInput,
    FlowDesignerAgent,
    TechnicalArchitectAgent,
    UIPrototypeAgent,
    UIPrototypeInput,
    UIPrototypeOutput,
)
from app.artifacts.schemas import UIPrototypeContent, validate_artifact_content
from app.core.errors import (
    AgentExecutionError,
    ArtifactDependencyMissingError,
    NotFoundError,
    ServiceUnavailableError,
    TechnicalDesignBlockedError,
)
from app.core.security import sanitized_error
from app.domain.analysis import AgentExecutionStatus
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.projects import ProjectStatus
from app.domain.solution import SolutionWorkflowStatus
from app.models.analysis import AgentExecution
from app.models.artifact import Artifact, ArtifactVersion
from app.repositories.solution import SolutionRepository
from app.schemas.artifact import ArtifactResponse
from app.schemas.design import DesignAgentResponse
from app.services.file_storage import FileStorageService
from app.services.llm import LLMRequest, LLMResult


@dataclass(frozen=True)
class PrototypeFile:
    content: bytes
    content_type: str
    filename: str


class DesignGenerationService:
    def __init__(
        self,
        repository: SolutionRepository,
        flow_agent: Optional[FlowDesignerAgent],
        ui_agent: Optional[UIPrototypeAgent],
        technical_agent: Optional[TechnicalArchitectAgent],
        storage: FileStorageService,
    ) -> None:
        self._repository = repository
        self._flow_agent = flow_agent
        self._ui_agent = ui_agent
        self._technical_agent = technical_agent
        self._storage = storage

    async def run_flow(
        self, project_id: UUID, requirement_id: UUID, revision_feedback: Optional[list[dict]] = None
    ) -> DesignAgentResponse:
        project, baseline, solution, existing = await self._load_approved(
            project_id, requirement_id
        )
        if self._flow_agent is None:
            raise ServiceUnavailableError("OPENAI_API_KEY is required to run Flow Designer.")
        request = self._flow_agent.build_request(
            self._approved_input(project, baseline, solution, existing, revision_feedback)
        )
        execution = await self._start_execution(
            project_id, requirement_id, self._flow_agent.name, request
        )
        try:
            result = await self._flow_agent.analyze(request)
            return await self._save_outputs(
                execution,
                result,
                project_id,
                requirement_id,
                [(ArtifactType.PROCESS_FLOW, result.output.model_dump(mode="json"))],
            )
        except AgentExecutionError:
            raise
        except Exception as error:
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def run_ui_prototype(
        self, project_id: UUID, requirement_id: UUID, revision_feedback: Optional[list[dict]] = None
    ) -> DesignAgentResponse:
        _project, baseline, solution, _existing = await self._load_approved(
            project_id, requirement_id
        )
        flow = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.PROCESS_FLOW
        )
        if flow is None or flow.status != ArtifactStatus.VALIDATED:
            raise ArtifactDependencyMissingError(ArtifactType.PROCESS_FLOW.value)
        if self._ui_agent is None:
            raise ServiceUnavailableError("OPENAI_API_KEY is required to run UI Prototype Agent.")
        request = self._ui_agent.build_request(
            UIPrototypeInput(
                requirement_baseline=self._current_content(baseline),
                approved_solution=self._current_content(solution),
                process_flow=self._current_content(flow),
                revision_feedback=revision_feedback or [],
            )
        )
        execution = await self._start_execution(
            project_id, requirement_id, self._ui_agent.name, request
        )
        stored_keys: list[str] = []
        try:
            result = await self._ui_agent.analyze(request)
            content, stored_keys = await self._store_prototype_files(
                project_id, requirement_id, result.output
            )
            return await self._save_outputs(
                execution,
                result,
                project_id,
                requirement_id,
                [(ArtifactType.UI_PROTOTYPE, content)],
            )
        except AgentExecutionError:
            await self._delete_files(stored_keys)
            raise
        except Exception as error:
            await self._delete_files(stored_keys)
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def run_technical_architecture(
        self,
        project_id: UUID,
        requirement_id: UUID,
        revision_feedback: Optional[list[dict]] = None,
    ) -> DesignAgentResponse:
        project, baseline, solution, existing = await self._load_approved(
            project_id, requirement_id
        )
        if self._technical_agent is None:
            raise ServiceUnavailableError("OPENAI_API_KEY is required to run Technical Architect.")
        request = self._technical_agent.build_request(
            self._approved_input(project, baseline, solution, existing, revision_feedback)
        )
        execution = await self._start_execution(
            project_id, requirement_id, self._technical_agent.name, request
        )
        try:
            result = await self._technical_agent.analyze(request)
            return await self._save_outputs(
                execution,
                result,
                project_id,
                requirement_id,
                [
                    (
                        ArtifactType.DATABASE_DESIGN,
                        result.output.database_design.model_dump(mode="json"),
                    ),
                    (
                        ArtifactType.API_SPECIFICATION,
                        result.output.api_specification.model_dump(mode="json"),
                    ),
                ],
            )
        except AgentExecutionError:
            raise
        except Exception as error:
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def read_prototype_file(
        self,
        project_id: UUID,
        requirement_id: UUID,
        artifact_id: UUID,
        version_number: int,
        filename: str,
    ) -> PrototypeFile:
        artifact = await self._repository.get_artifact_by_id(
            project_id, requirement_id, artifact_id
        )
        if artifact is None or artifact.artifact_type != ArtifactType.UI_PROTOTYPE:
            raise NotFoundError("UI Prototype artifact")
        version = next((item for item in artifact.versions if item.version == version_number), None)
        if version is None:
            raise NotFoundError("UI Prototype version")
        content = UIPrototypeContent.model_validate(version.content_json)
        screen = next((item for item in content.screens if item.filename == filename), None)
        if screen is None:
            raise NotFoundError("Prototype file")
        try:
            body = await self._storage.read(screen.storage_key)
        except FileNotFoundError as error:
            raise NotFoundError("Prototype file") from error
        return PrototypeFile(
            content=body, content_type=screen.content_type, filename=screen.filename
        )

    async def _load_approved(self, project_id: UUID, requirement_id: UUID):  # type: ignore[no-untyped-def]
        project = await self._repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        if project.status != ProjectStatus.READY_FOR_ANALYSIS:
            raise TechnicalDesignBlockedError()
        requirement = await self._repository.get_requirement(project_id, requirement_id)
        if requirement is None:
            raise NotFoundError("Requirement")
        workflow = await self._repository.get_workflow(project_id, requirement_id)
        solution = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.SOLUTION
        )
        if workflow is None or solution is None:
            raise TechnicalDesignBlockedError()
        if (
            workflow.status != SolutionWorkflowStatus.APPROVED
            or workflow.current_artifact_version_id != self._current_version(solution).id
        ):
            raise TechnicalDesignBlockedError()
        baseline = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.REQUIREMENT_BASELINE
        )
        if baseline is None:
            raise ArtifactDependencyMissingError(ArtifactType.REQUIREMENT_BASELINE.value)
        existing = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.EXISTING_SYSTEM_ANALYSIS
        )
        return project, baseline, solution, existing

    @classmethod
    def _approved_input(
        cls,
        project,
        baseline: Artifact,
        solution: Artifact,
        existing: Optional[Artifact],
        revision_feedback: Optional[list[dict]] = None,
    ) -> ApprovedDesignInput:  # type: ignore[no-untyped-def]
        return ApprovedDesignInput(
            project_context={
                "name": project.name,
                "description": project.description,
                "project_type": project.project_type.value,
                "business_objective": project.business_objective,
                "current_flow": project.context.current_flow,
                "current_actors": project.context.current_actors,
                "current_rules": project.context.current_rules,
                "constraints": project.context.constraints,
            },
            requirement_baseline=cls._current_content(baseline),
            approved_solution=cls._current_content(solution),
            existing_system_analysis=(
                cls._current_content(existing) if existing is not None else None
            ),
            revision_feedback=revision_feedback or [],
        )

    async def _store_prototype_files(
        self, project_id: UUID, requirement_id: UUID, output: UIPrototypeOutput
    ) -> tuple[dict, list[str]]:
        generation_id = uuid4()
        screens = []
        stored_keys = []
        try:
            for screen in output.screens:
                key = (
                    f"projects/{project_id}/requirements/{requirement_id}/"
                    f"prototypes/{generation_id}/{screen.filename}"
                )
                stored = await self._storage.put(
                    key, screen.source_html.encode("utf-8"), "text/html; charset=utf-8"
                )
                stored_keys.append(stored.key)
                screens.append(
                    {
                        "filename": screen.filename,
                        "title": screen.title,
                        "purpose": screen.purpose,
                        "storage_key": stored.key,
                        "content_type": stored.content_type,
                        "size_bytes": stored.size_bytes,
                        "requirement_refs": screen.requirement_refs,
                    }
                )
        except Exception:
            await self._delete_files(stored_keys)
            raise
        content = {
            "summary": output.summary,
            "screens": screens,
            "interactions": output.interactions,
            "requirement_traceability": output.requirement_traceability,
        }
        return validate_artifact_content(ArtifactType.UI_PROTOTYPE, content), stored_keys

    async def _delete_files(self, keys: list[str]) -> None:
        for key in keys:
            try:
                await self._storage.delete(key)
            except Exception:
                pass

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

    async def _save_outputs(
        self,
        execution: AgentExecution,
        result: LLMResult,
        project_id: UUID,
        requirement_id: UUID,
        outputs: list[tuple[ArtifactType, dict]],
    ) -> DesignAgentResponse:
        try:
            if not isinstance(result.output, BaseModel):
                raise TypeError("Design agent output was not a validated model.")
            artifacts: list[Artifact] = []
            versions: list[ArtifactVersion] = []
            for artifact_type, raw_content in outputs:
                content = validate_artifact_content(artifact_type, raw_content)
                artifact = await self._repository.get_artifact(
                    project_id, requirement_id, artifact_type, for_update=True
                )
                if artifact is None:
                    version = ArtifactVersion(
                        version=1,
                        content_json=content,
                        created_by=execution.agent_name,
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
            execution.provider_response_id = result.response_id
            execution.input_tokens = result.usage.input_tokens
            execution.output_tokens = result.usage.output_tokens
            execution.total_tokens = result.usage.total_tokens
            execution.duration_ms = round(result.duration_ms)
            execution.artifact_version_id = versions[0].id
            await self._repository.commit()
            for artifact in artifacts:
                await self._repository.refresh_artifact(artifact)
            return DesignAgentResponse(
                execution_id=execution.id,
                artifacts=[self._artifact_response(item) for item in artifacts],
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
