from __future__ import annotations

import base64
import io
import zipfile
from pathlib import PurePath
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
from app.services.file_storage import FileStorageService
from app.services.llm import LLMRequest, LLMResult

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".csv",
    ".sql",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".cs",
    ".html",
    ".css",
    ".scss",
    ".sh",
}
EVIDENCE_SOURCE_TYPES = {
    "UI_SCREENSHOT": "SCREENSHOT_DESCRIPTION",
    "SOURCE_CODE": "SOURCE_CODE_METADATA",
    "API_DOCUMENTATION": "API_DOCUMENTATION",
    "DATABASE_SCHEMA": "DATABASE_SCHEMA",
    "PROCESS_DOCUMENT": "EXISTING_DOCUMENTATION",
    "OTHER": "EXISTING_DOCUMENTATION",
}


class DiscoveryAnalysisService:
    def __init__(
        self,
        repository: RequirementAnalysisRepository,
        research_agent: Optional[ResearchAgent],
        existing_system_analyst: Optional[ExistingSystemAnalyst],
        storage: Optional[FileStorageService] = None,
    ) -> None:
        self._repository = repository
        self._research_agent = research_agent
        self._existing_system_analyst = existing_system_analyst
        self._storage = storage

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
        stored_evidence, image_urls = await self._stored_evidence(project)
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
                evidence=stored_evidence
                + [
                    ExistingSystemEvidence.model_validate(item.model_dump())
                    for item in payload.evidence
                ],
                previous_artifacts=previous_artifacts,
            ),
            image_urls=tuple(image_urls),
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
                "image_count": len(request.image_urls),
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

    async def _stored_evidence(
        self, project: object
    ) -> tuple[list[ExistingSystemEvidence], list[str]]:
        evidence_items: list[ExistingSystemEvidence] = []
        image_urls: list[str] = []
        for item in getattr(project, "evidence", []):
            content = (
                f"File: {item.original_filename}. User note: "
                f"{item.description or 'No additional note supplied.'}"
            )
            raw = b""
            if self._storage is not None:
                raw = await self._storage.read(item.storage_key)
            suffix = PurePath(item.original_filename).suffix.lower()
            if raw and item.content_type.startswith("image/"):
                encoded = base64.b64encode(raw).decode("ascii")
                image_urls.append(f"data:{item.content_type};base64,{encoded}")
                content += " The attached image is available for visual inspection."
            elif raw and suffix == ".zip":
                content += "\nSource archive inventory and text excerpts:\n" + self._zip_excerpt(
                    raw
                )
            elif raw and (item.content_type.startswith("text/") or suffix in TEXT_EXTENSIONS):
                content += "\nFile content:\n" + raw[:100_000].decode("utf-8", errors="replace")
            evidence_items.append(
                ExistingSystemEvidence(
                    source_type=EVIDENCE_SOURCE_TYPES.get(item.category, "EXISTING_DOCUMENTATION"),
                    title=item.title,
                    content=content,
                )
            )
        return evidence_items, image_urls

    @staticmethod
    def _zip_excerpt(raw: bytes) -> str:
        excerpts: list[str] = []
        total_characters = 0
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for member in archive.infolist()[:100]:
                if member.is_dir() or member.file_size > 1_000_000:
                    continue
                suffix = PurePath(member.filename).suffix.lower()
                excerpts.append(f"- {member.filename} ({member.file_size} bytes)")
                if suffix not in TEXT_EXTENSIONS or total_characters >= 100_000:
                    continue
                snippet = archive.read(member)[:20_000].decode("utf-8", errors="replace")
                excerpts.append(f"--- {member.filename} ---\n{snippet}")
                total_characters += len(snippet)
        return "\n".join(excerpts)

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
