from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.agents.development_planner import (
    DevelopmentPlannerAgent,
    DevelopmentPlannerInput,
    DevelopmentPlannerOutput,
)
from app.artifacts.schemas import (
    DevelopmentTaskContent,
    UIPrototypeContent,
    validate_artifact_content,
)
from app.core.errors import (
    AgentExecutionError,
    ArtifactDependencyMissingError,
    NotFoundError,
    QualityGateBlockedError,
    ServiceUnavailableError,
)
from app.core.security import sanitized_error
from app.domain.analysis import AgentExecutionStatus
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.handoff import HandoffExportFormat, HandoffWorkflowStatus
from app.domain.projects import ProjectStatus
from app.domain.quality import QualityWorkflowStatus
from app.domain.solution import SolutionWorkflowStatus
from app.models.analysis import AgentExecution
from app.models.artifact import Artifact, ArtifactVersion
from app.models.handoff import HandoffPackageVersion, HandoffWorkflow
from app.repositories.handoff import HandoffRepository
from app.schemas.artifact import ArtifactResponse
from app.schemas.handoff import (
    ArtifactSourceReference,
    DevelopmentPlanResponse,
    HandoffPackageContent,
    HandoffPackageResponse,
    HandoffSection,
    HandoffWorkflowResponse,
    TraceabilityEntry,
    TrelloCard,
    TrelloList,
    TrelloReadyContent,
)
from app.services.file_storage import FileStorageService
from app.services.llm import LLMRequest, LLMResult

QUALITY_SOURCE_TYPES = (
    ArtifactType.REQUIREMENT_BASELINE,
    ArtifactType.SOLUTION,
    ArtifactType.PROCESS_FLOW,
    ArtifactType.UI_PROTOTYPE,
    ArtifactType.DATABASE_DESIGN,
    ArtifactType.API_SPECIFICATION,
    ArtifactType.TEST_SCENARIO,
    ArtifactType.ACCEPTANCE_CRITERIA,
)


@dataclass(frozen=True)
class ExportedFile:
    content: bytes
    content_type: str
    filename: str


class DevelopmentHandoffService:
    def __init__(
        self,
        repository: HandoffRepository,
        planner: Optional[DevelopmentPlannerAgent],
        storage: FileStorageService,
    ) -> None:
        self._repository = repository
        self._planner = planner
        self._storage = storage

    async def plan(
        self, project_id: UUID, requirement_id: UUID
    ) -> DevelopmentPlanResponse:
        if self._planner is None:
            raise ServiceUnavailableError(
                "OPENAI_API_KEY is required to run Development Planner."
            )
        project, artifacts, quality_versions = await self._load_passed_sources(
            project_id, requirement_id
        )
        research = await self._required_artifact(
            project_id, requirement_id, ArtifactType.RESEARCH
        )
        existing = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.EXISTING_SYSTEM_ANALYSIS
        )
        planner_input = DevelopmentPlannerInput(
            project_context=self._project_context(project),
            requirement_baseline=self._content(artifacts[ArtifactType.REQUIREMENT_BASELINE]),
            research=self._content(research),
            existing_system_analysis=self._content(existing) if existing else None,
            solution=self._content(artifacts[ArtifactType.SOLUTION]),
            process_flow=self._content(artifacts[ArtifactType.PROCESS_FLOW]),
            ui_prototype=self._content(artifacts[ArtifactType.UI_PROTOTYPE]),
            database_design=self._content(artifacts[ArtifactType.DATABASE_DESIGN]),
            api_specification=self._content(artifacts[ArtifactType.API_SPECIFICATION]),
            test_scenarios=self._content(artifacts[ArtifactType.TEST_SCENARIO]),
            acceptance_criteria=self._content(artifacts[ArtifactType.ACCEPTANCE_CRITERIA]),
            source_versions=quality_versions,
        )
        request = self._planner.build_request(planner_input)
        execution = await self._start_execution(
            project_id, requirement_id, self._planner.name, request
        )
        try:
            result = await self._planner.analyze(request)
            self._validate_planner_authority(result.output, planner_input, existing is not None)
            artifact, version = await self._save_task_artifact(
                execution, result, project_id, requirement_id
            )
            workflow = await self._repository.get_handoff_workflow(
                project_id, requirement_id, for_update=True
            )
            if workflow is None:
                workflow = HandoffWorkflow(
                    project_id=project_id,
                    requirement_id=requirement_id,
                    development_task_artifact_id=artifact.id,
                    current_task_version_id=version.id,
                    status=HandoffWorkflowStatus.TASKS_READY,
                    current_package_version=0,
                )
                self._repository.add(workflow)
            else:
                workflow.current_task_version_id = version.id
                workflow.status = HandoffWorkflowStatus.TASKS_READY
            await self._repository.commit()
            await self._repository.refresh_artifact(artifact)
            await self._repository.refresh_handoff_workflow(workflow)
            return DevelopmentPlanResponse(
                execution_id=execution.id,
                workflow=self._workflow_response(workflow, artifact),
            )
        except AgentExecutionError:
            raise
        except Exception as error:
            await self._repository.rollback()
            await self._record_failure(execution, error)
            raise AgentExecutionError(str(execution.id)) from error

    async def generate_package(
        self,
        project_id: UUID,
        requirement_id: UUID,
        expected_task_version: int,
    ) -> HandoffWorkflowResponse:
        project, artifacts, quality_versions = await self._load_passed_sources(
            project_id, requirement_id
        )
        research = await self._required_artifact(
            project_id, requirement_id, ArtifactType.RESEARCH
        )
        existing = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.EXISTING_SYSTEM_ANALYSIS
        )
        task_artifact = await self._required_artifact(
            project_id, requirement_id, ArtifactType.DEVELOPMENT_TASK
        )
        workflow = await self._repository.get_handoff_workflow(
            project_id, requirement_id, for_update=True
        )
        if workflow is None:
            raise QualityGateBlockedError("Preview Development Tasks before generating a package.")
        task_version = self._version(task_artifact)
        if (
            expected_task_version != task_artifact.current_version
            or workflow.current_task_version_id != task_version.id
        ):
            raise QualityGateBlockedError(
                "Development Tasks changed; preview the current version before export."
            )

        package = await self._build_package(
            project,
            requirement_id,
            artifacts,
            research,
            existing,
            task_artifact,
            quality_versions,
        )
        next_version = workflow.current_package_version + 1
        generation_id = uuid4()
        prefix = (
            f"projects/{project_id}/requirements/{requirement_id}/"
            f"handoffs/{generation_id}"
        )
        json_body = json.dumps(package.model_dump(mode="json"), ensure_ascii=False, indent=2)
        markdown_body = self._render_markdown(package)
        trello_body = json.dumps(
            package.trello_ready.model_dump(mode="json"), ensure_ascii=False, indent=2
        )
        stored_keys: list[str] = []
        try:
            json_file = await self._storage.put(
                f"{prefix}/development-handoff.json",
                json_body.encode("utf-8"),
                "application/json; charset=utf-8",
            )
            stored_keys.append(json_file.key)
            markdown_file = await self._storage.put(
                f"{prefix}/development-handoff.md",
                markdown_body.encode("utf-8"),
                "text/markdown; charset=utf-8",
            )
            stored_keys.append(markdown_file.key)
            trello_file = await self._storage.put(
                f"{prefix}/trello-ready.json",
                trello_body.encode("utf-8"),
                "application/json; charset=utf-8",
            )
            stored_keys.append(trello_file.key)
            package_version = HandoffPackageVersion(
                workflow_id=workflow.id,
                development_task_version_id=task_version.id,
                version=next_version,
                source_versions={
                    **quality_versions,
                    ArtifactType.RESEARCH.value: research.current_version,
                    **(
                        {ArtifactType.EXISTING_SYSTEM_ANALYSIS.value: existing.current_version}
                        if existing
                        else {}
                    ),
                    ArtifactType.DEVELOPMENT_TASK.value: task_artifact.current_version,
                },
                content_json=package.model_dump(mode="json"),
                json_storage_key=json_file.key,
                markdown_storage_key=markdown_file.key,
                trello_storage_key=trello_file.key,
            )
            workflow.packages.append(package_version)
            workflow.current_package_version = next_version
            workflow.status = HandoffWorkflowStatus.PACKAGE_READY
            await self._repository.commit()
            await self._repository.refresh_handoff_workflow(workflow)
            return self._workflow_response(workflow, task_artifact)
        except Exception:
            await self._repository.rollback()
            for key in stored_keys:
                try:
                    await self._storage.delete(key)
                except Exception:
                    pass
            raise

    async def get(
        self, project_id: UUID, requirement_id: UUID
    ) -> HandoffWorkflowResponse:
        workflow = await self._repository.get_handoff_workflow(project_id, requirement_id)
        if workflow is None:
            raise NotFoundError("Development Handoff workflow")
        task_artifact = await self._required_artifact(
            project_id, requirement_id, ArtifactType.DEVELOPMENT_TASK
        )
        return self._workflow_response(workflow, task_artifact)

    async def download(
        self,
        project_id: UUID,
        requirement_id: UUID,
        version: int,
        export_format: HandoffExportFormat,
    ) -> ExportedFile:
        package = await self._repository.get_package(project_id, requirement_id, version)
        if package is None:
            raise NotFoundError("Development Handoff package")
        config = {
            HandoffExportFormat.JSON: (
                package.json_storage_key,
                "application/json; charset=utf-8",
                f"development-handoff-v{version}.json",
            ),
            HandoffExportFormat.MARKDOWN: (
                package.markdown_storage_key,
                "text/markdown; charset=utf-8",
                f"development-handoff-v{version}.md",
            ),
            HandoffExportFormat.TRELLO: (
                package.trello_storage_key,
                "application/json; charset=utf-8",
                f"development-handoff-trello-v{version}.json",
            ),
        }[export_format]
        try:
            content = await self._storage.read(config[0])
        except FileNotFoundError as error:
            raise NotFoundError("Development Handoff export") from error
        return ExportedFile(content=content, content_type=config[1], filename=config[2])

    async def _load_passed_sources(self, project_id: UUID, requirement_id: UUID):  # type: ignore[no-untyped-def]
        project = await self._repository.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        if project.status != ProjectStatus.READY_FOR_ANALYSIS:
            raise QualityGateBlockedError("Project context is no longer ready.")
        requirement = await self._repository.get_requirement(project_id, requirement_id)
        if requirement is None:
            raise NotFoundError("Requirement")
        quality = await self._repository.get_quality_workflow(project_id, requirement_id)
        if quality is None or quality.status != QualityWorkflowStatus.PASSED:
            raise QualityGateBlockedError()
        artifacts = {}
        for artifact_type in QUALITY_SOURCE_TYPES:
            artifact = await self._required_artifact(project_id, requirement_id, artifact_type)
            if artifact.status != ArtifactStatus.VALIDATED:
                raise QualityGateBlockedError(f"{artifact_type.value} is not validated.")
            artifacts[artifact_type] = artifact
        current_versions = {
            artifact_type.value: artifact.current_version
            for artifact_type, artifact in artifacts.items()
        }
        if quality.reviewed_versions != current_versions:
            raise QualityGateBlockedError("Artifacts changed after the passing SA Review.")
        solution_workflow = await self._repository.get_workflow(project_id, requirement_id)
        solution = artifacts[ArtifactType.SOLUTION]
        if (
            solution_workflow is None
            or solution_workflow.status != SolutionWorkflowStatus.APPROVED
            or solution_workflow.current_artifact_version_id != self._version(solution).id
        ):
            raise QualityGateBlockedError("The current Solution is not approved.")
        return project, artifacts, current_versions

    async def _required_artifact(
        self, project_id: UUID, requirement_id: UUID, artifact_type: ArtifactType
    ) -> Artifact:
        artifact = await self._repository.get_artifact(
            project_id, requirement_id, artifact_type
        )
        if artifact is None:
            raise ArtifactDependencyMissingError(artifact_type.value)
        return artifact

    async def _build_package(
        self,
        project,
        requirement_id: UUID,
        artifacts: dict[ArtifactType, Artifact],
        research: Artifact,
        existing: Optional[Artifact],
        tasks: Artifact,
        quality_versions: dict[str, int],
    ) -> HandoffPackageContent:  # type: ignore[no-untyped-def]
        solution = self._content(artifacts[ArtifactType.SOLUTION])
        ui_content = self._content(artifacts[ArtifactType.UI_PROTOTYPE])
        manifest = UIPrototypeContent.model_validate(ui_content)
        prototype_sources = []
        for screen in manifest.screens:
            try:
                source = (await self._storage.read(screen.storage_key)).decode("utf-8")
            except (FileNotFoundError, UnicodeDecodeError) as error:
                raise ArtifactDependencyMissingError(ArtifactType.UI_PROTOTYPE.value) from error
            prototype_sources.append(
                {
                    "filename": screen.filename,
                    "title": screen.title,
                    "purpose": screen.purpose,
                    "requirement_refs": screen.requirement_refs,
                    "source_html": source,
                }
            )
        prototype = {**ui_content, "source_files": prototype_sources}
        db_content = self._content(artifacts[ArtifactType.DATABASE_DESIGN])
        api_content = self._content(artifacts[ArtifactType.API_SPECIFICATION])
        task_content = DevelopmentTaskContent.model_validate(self._content(tasks))
        technical_specification = {
            "boundary": (
                "Specification package only; target application implementation is external."
            ),
            "database_changes": [
                {
                    "entity": item.get("entity"),
                    "table": item.get("table"),
                    "classification": item.get("classification"),
                }
                for item in db_content.get("entities", [])
            ],
            "api_changes": [
                {
                    "method": item.get("method"),
                    "endpoint": item.get("endpoint"),
                    "classification": item.get("classification"),
                }
                for item in api_content.get("endpoints", [])
            ],
            "integration_requirements": solution.get("integration_requirements", []),
            "data_requirements": solution.get("data_requirements", []),
            "assumptions": list(
                dict.fromkeys(
                    solution.get("assumptions", [])
                    + db_content.get("assumptions", [])
                    + api_content.get("assumptions", [])
                )
            ),
            "risks": solution.get("risks", []),
        }
        refs = {
            kind: self._source_ref(artifact)
            for kind, artifact in artifacts.items()
        }
        research_ref = self._source_ref(research)
        task_ref = self._source_ref(tasks)
        existing_ref = self._source_ref(existing) if existing else None
        existing_content = (
            self._content(existing)
            if existing
            else {"available": False, "solution_as_is": solution.get("as_is", [])}
        )
        sections = [
            HandoffSection(
                number="01", slug="project-context", title="Project Context",
                source_artifacts=[], content=self._project_context(project),
            ),
            HandoffSection(
                number="02", slug="requirement-baseline", title="Requirement Baseline",
                source_artifacts=[refs[ArtifactType.REQUIREMENT_BASELINE]],
                content=self._content(artifacts[ArtifactType.REQUIREMENT_BASELINE]),
            ),
            HandoffSection(
                number="03", slug="research-summary", title="Research Summary",
                source_artifacts=[research_ref], content=self._content(research),
            ),
            HandoffSection(
                number="04", slug="existing-system", title="AS-IS / Existing System Analysis",
                source_artifacts=[existing_ref] if existing_ref else [refs[ArtifactType.SOLUTION]],
                content=existing_content,
            ),
            HandoffSection(
                number="05", slug="functional-specification", title="Functional Specification",
                source_artifacts=[refs[ArtifactType.SOLUTION]], content=solution,
            ),
            HandoffSection(
                number="06", slug="to-be-process-flow", title="TO-BE Process Flow",
                source_artifacts=[refs[ArtifactType.PROCESS_FLOW]],
                content=self._content(artifacts[ArtifactType.PROCESS_FLOW]),
            ),
            HandoffSection(
                number="07", slug="html-prototype", title="HTML Prototype",
                source_artifacts=[refs[ArtifactType.UI_PROTOTYPE]], content=prototype,
            ),
            HandoffSection(
                number="08", slug="database-design", title="Database Design",
                source_artifacts=[refs[ArtifactType.DATABASE_DESIGN]], content=db_content,
            ),
            HandoffSection(
                number="09", slug="api-specification", title="API Specification",
                source_artifacts=[refs[ArtifactType.API_SPECIFICATION]], content=api_content,
            ),
            HandoffSection(
                number="10", slug="technical-specification", title="Technical Specification",
                source_artifacts=[
                    refs[ArtifactType.SOLUTION], refs[ArtifactType.DATABASE_DESIGN],
                    refs[ArtifactType.API_SPECIFICATION], research_ref,
                ], content=technical_specification,
            ),
            HandoffSection(
                number="11", slug="test-scenarios", title="Test Scenarios",
                source_artifacts=[refs[ArtifactType.TEST_SCENARIO]],
                content=self._content(artifacts[ArtifactType.TEST_SCENARIO]),
            ),
            HandoffSection(
                number="12", slug="acceptance-criteria", title="Acceptance Criteria",
                source_artifacts=[refs[ArtifactType.ACCEPTANCE_CRITERIA]],
                content=self._content(artifacts[ArtifactType.ACCEPTANCE_CRITERIA]),
            ),
            HandoffSection(
                number="13", slug="development-tasks", title="Development Tasks",
                source_artifacts=[task_ref], content=task_content.model_dump(mode="json"),
            ),
        ]
        trello = self._trello(project.name, task_content)
        traceability = [
            TraceabilityEntry(
                task_id=task.id,
                requirement=task.requirement,
                acceptance_criteria=task.acceptance_criteria,
                reference_artifacts=[item.value for item in task.reference_artifact],
            )
            for task in task_content.tasks
        ]
        source_versions = {
            **quality_versions,
            ArtifactType.RESEARCH.value: research.current_version,
            **(
                {ArtifactType.EXISTING_SYSTEM_ANALYSIS.value: existing.current_version}
                if existing
                else {}
            ),
            ArtifactType.DEVELOPMENT_TASK.value: tasks.current_version,
        }
        return HandoffPackageContent(
            package_name=f"{project.name} — Development Handoff",
            project_id=project.id,
            requirement_id=requirement_id,
            source_versions=source_versions,
            sections=sections,
            traceability=traceability,
            trello_ready=trello,
        )

    async def _save_task_artifact(
        self,
        execution: AgentExecution,
        result: LLMResult,
        project_id: UUID,
        requirement_id: UUID,
    ) -> tuple[Artifact, ArtifactVersion]:
        if not isinstance(result.output, BaseModel):
            raise TypeError("Development Planner output was not a validated model.")
        content = validate_artifact_content(
            ArtifactType.DEVELOPMENT_TASK, result.output.model_dump(mode="json")
        )
        artifact = await self._repository.get_artifact(
            project_id, requirement_id, ArtifactType.DEVELOPMENT_TASK, for_update=True
        )
        if artifact is None:
            version = ArtifactVersion(
                version=1, content_json=content, created_by=execution.agent_name
            )
            artifact = Artifact(
                project_id=project_id,
                requirement_id=requirement_id,
                artifact_type=ArtifactType.DEVELOPMENT_TASK,
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
        await self._repository.flush()
        execution.status = AgentExecutionStatus.SUCCEEDED
        execution.response_json = result.output.model_dump(mode="json")
        execution.provider_response_id = result.response_id
        execution.input_tokens = result.usage.input_tokens
        execution.output_tokens = result.usage.output_tokens
        execution.total_tokens = result.usage.total_tokens
        execution.duration_ms = round(result.duration_ms)
        execution.artifact_version_id = version.id
        return artifact, version

    async def _start_execution(
        self, project_id: UUID, requirement_id: UUID, name: str, request: LLMRequest
    ) -> AgentExecution:
        execution = AgentExecution(
            project_id=project_id,
            requirement_id=requirement_id,
            agent_name=name,
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

    async def _record_failure(self, execution: AgentExecution, error: Exception) -> None:
        execution.status = AgentExecutionStatus.FAILED
        execution.error_message = sanitized_error(error)
        await self._repository.commit()

    @staticmethod
    def _validate_planner_authority(
        output: DevelopmentPlannerOutput,
        planner_input: DevelopmentPlannerInput,
        has_existing: bool,
    ) -> None:
        baseline = planner_input.requirement_baseline
        solution = planner_input.solution
        allowed_requirements = set(
            baseline.get("known_requirements", [])
            + baseline.get("business_rules", [])
            + solution.get("functional_requirements", [])
            + solution.get("business_rules", [])
        )
        allowed_acceptance = {
            item.get("id")
            for item in planner_input.acceptance_criteria.get("criteria", [])
            if item.get("id")
        }
        available_artifacts = {
            ArtifactType.REQUIREMENT_BASELINE,
            ArtifactType.RESEARCH,
            ArtifactType.SOLUTION,
            ArtifactType.PROCESS_FLOW,
            ArtifactType.UI_PROTOTYPE,
            ArtifactType.DATABASE_DESIGN,
            ArtifactType.API_SPECIFICATION,
            ArtifactType.TEST_SCENARIO,
            ArtifactType.ACCEPTANCE_CRITERIA,
        }
        if has_existing:
            available_artifacts.add(ArtifactType.EXISTING_SYSTEM_ANALYSIS)
        for task in output.tasks:
            if task.requirement not in allowed_requirements:
                raise ValueError(f"task {task.id} introduces an unknown requirement")
            if not set(task.acceptance_criteria).issubset(allowed_acceptance):
                raise ValueError(f"task {task.id} references unknown acceptance criteria")
            if not set(task.reference_artifact).issubset(available_artifacts):
                raise ValueError(f"task {task.id} references an unavailable artifact")

    @staticmethod
    def _project_context(project) -> dict:  # type: ignore[no-untyped-def]
        return {
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
        }

    @staticmethod
    def _trello(project_name: str, content: DevelopmentTaskContent) -> TrelloReadyContent:
        cards = []
        for task in content.tasks:
            description = "\n".join(
                (
                    f"## Objective\n{task.objective}",
                    "## Requirement\n" + task.requirement,
                    "## Scope\n" + "\n".join(f"- {item}" for item in task.scope),
                    "## Technical notes\n"
                    + "\n".join(f"- {item}" for item in task.technical_notes),
                    "## Dependencies\n"
                    + ("\n".join(f"- {item}" for item in task.dependency) or "- None"),
                )
            )
            cards.append(
                TrelloCard(
                    id=task.id,
                    name=task.title,
                    description=description,
                    target_list="Backlog",
                    labels=[task.workstream.value],
                    dependencies=task.dependency,
                    checklist=task.acceptance_criteria,
                    reference_artifacts=[item.value for item in task.reference_artifact],
                )
            )
        return TrelloReadyContent(
            board_name=f"{project_name} — Development Handoff",
            lists=[
                TrelloList(name="Backlog", position=1),
                TrelloList(name="Ready", position=2),
                TrelloList(name="In Progress", position=3),
                TrelloList(name="Review", position=4),
                TrelloList(name="Done", position=5),
            ],
            cards=cards,
        )

    @staticmethod
    def _render_markdown(package: HandoffPackageContent) -> str:
        lines = [
            f"# {package.package_name}",
            "",
            f"Project ID: `{package.project_id}`  ",
            f"Requirement ID: `{package.requirement_id}`",
            "",
        ]
        for section in package.sections:
            lines.extend(
                [
                    f"## {section.number} {section.title}",
                    "",
                    "```json",
                    json.dumps(section.content, ensure_ascii=False, indent=2),
                    "```",
                    "",
                ]
            )
        lines.extend(
            [
                "## Trello-ready structure",
                "",
                "```json",
                json.dumps(
                    package.trello_ready.model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def _workflow_response(
        cls, workflow: HandoffWorkflow, task_artifact: Artifact
    ) -> HandoffWorkflowResponse:
        packages = [cls._package_response(item) for item in workflow.packages]
        current = next(
            (item for item in packages if item.version == workflow.current_package_version), None
        )
        return HandoffWorkflowResponse(
            id=workflow.id,
            project_id=workflow.project_id,
            requirement_id=workflow.requirement_id,
            status=workflow.status,
            current_task_version=task_artifact.current_version,
            current_package_version=workflow.current_package_version,
            task_artifact=cls._artifact_response(task_artifact),
            current_package=current,
            packages=packages,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    @staticmethod
    def _package_response(package: HandoffPackageVersion) -> HandoffPackageResponse:
        return HandoffPackageResponse(
            id=package.id,
            version=package.version,
            development_task_version_id=package.development_task_version_id,
            source_versions=package.source_versions,
            content_json=HandoffPackageContent.model_validate(package.content_json),
            created_at=package.created_at,
        )

    @classmethod
    def _source_ref(cls, artifact: Artifact) -> ArtifactSourceReference:
        return ArtifactSourceReference(
            artifact_type=artifact.artifact_type.value,
            artifact_id=artifact.id,
            version=artifact.current_version,
        )

    @staticmethod
    def _version(artifact: Artifact) -> ArtifactVersion:
        return next(item for item in artifact.versions if item.version == artifact.current_version)

    @classmethod
    def _content(cls, artifact: Artifact) -> dict:
        return cls._version(artifact).content_json

    @classmethod
    def _artifact_response(cls, artifact: Artifact) -> ArtifactResponse:
        current = cls._version(artifact)
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
