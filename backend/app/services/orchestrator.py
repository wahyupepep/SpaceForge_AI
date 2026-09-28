from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph
from sqlalchemy.exc import IntegrityError

from app.core.errors import (
    ContextIncompleteError,
    NotFoundError,
    OrchestratorConflictError,
    ProjectNotReadyError,
)
from app.core.security import sanitized_error
from app.domain.analysis import RequirementReadiness
from app.domain.artifacts import ArtifactType
from app.domain.handoff import HandoffWorkflowStatus
from app.domain.orchestrator import (
    STAGE_AGENT,
    OrchestratorExecutionStatus,
    OrchestratorStage,
    OrchestratorStatus,
)
from app.domain.projects import ProjectStatus, ProjectType, missing_enhancement_context
from app.domain.quality import QualityWorkflowStatus
from app.domain.solution import SolutionWorkflowStatus
from app.models.orchestrator import OrchestratorExecution, OrchestratorWorkflow
from app.repositories.orchestrator import OrchestratorRepository
from app.schemas.discovery import AnalyzeExistingSystemRequest, ExistingEvidenceInput
from app.schemas.orchestrator import OrchestratorWorkflowResponse
from app.services.design_generation import DesignGenerationService
from app.services.development_handoff import DevelopmentHandoffService
from app.services.discovery_analysis import DiscoveryAnalysisService
from app.services.quality_gate import QualityGateService
from app.services.requirement_analysis import RequirementAnalysisService
from app.services.solution_analysis import SolutionAnalysisService


class GraphState(TypedDict):
    workflow_id: str
    project_id: str
    requirement_id: str
    current_stage: str
    halt: bool
    run_id: str


class SAOrchestratorService:
    """LangGraph router over existing specialist application services."""

    def __init__(
        self,
        repository: OrchestratorRepository,
        requirement_service: RequirementAnalysisService,
        discovery_service: DiscoveryAnalysisService,
        solution_service: SolutionAnalysisService,
        design_service: DesignGenerationService,
        quality_service: QualityGateService,
        handoff_service: DevelopmentHandoffService,
        lease_seconds: int,
    ) -> None:
        self._repository = repository
        self._requirement_service = requirement_service
        self._discovery_service = discovery_service
        self._solution_service = solution_service
        self._design_service = design_service
        self._quality_service = quality_service
        self._handoff_service = handoff_service
        self._lease_seconds = lease_seconds
        self._graph = self._build_graph()

    async def start(
        self,
        project_id: UUID,
        requirement_id: UUID,
        evidence: list[ExistingEvidenceInput],
    ) -> OrchestratorWorkflowResponse:
        if await self._repository.get_workflow(project_id, requirement_id) is not None:
            raise OrchestratorConflictError(
                "An orchestrator workflow already exists; use resume instead."
            )
        if await self._repository.get_project(project_id) is None:
            raise NotFoundError("Project")
        if await self._repository.get_requirement(project_id, requirement_id) is None:
            raise NotFoundError("Requirement")
        run_id = uuid4()
        workflow = OrchestratorWorkflow(
            project_id=project_id,
            requirement_id=requirement_id,
            current_stage=OrchestratorStage.PROJECT_CONTEXT,
            status=OrchestratorStatus.ACTIVE,
            current_agent=None,
            pending_user_action=None,
            completed_stages=[],
            artifact_status={},
            revision_history=[],
            state_json={
                "existing_system_evidence": [item.model_dump(mode="json") for item in evidence]
            },
            active_run_id=run_id,
            lease_expires_at=self._lease_expiry(),
        )
        self._repository.add(workflow)
        try:
            await self._repository.commit()
        except IntegrityError as error:
            await self._repository.rollback()
            raise OrchestratorConflictError(
                "An orchestrator workflow already exists for this requirement."
            ) from error
        await self._repository.refresh_workflow(workflow)
        return await self._advance(workflow, run_id)

    async def resume(
        self, project_id: UUID, requirement_id: UUID
    ) -> OrchestratorWorkflowResponse:
        workflow = await self._repository.get_workflow(project_id, requirement_id)
        if workflow is None:
            raise NotFoundError("Orchestrator workflow")
        if workflow.status == OrchestratorStatus.COMPLETED:
            return self._response(workflow)
        run_id = uuid4()
        if not await self._repository.try_acquire_lease(
            workflow.id, run_id, self._lease_expiry()
        ):
            raise OrchestratorConflictError(
                "This workflow already has an active execution; retry after its lease expires."
            )
        workflow.status = OrchestratorStatus.ACTIVE
        workflow.pending_user_action = None
        workflow.last_error = None
        await self._repository.commit()
        return await self._advance(workflow, run_id)

    async def get(
        self, project_id: UUID, requirement_id: UUID
    ) -> OrchestratorWorkflowResponse:
        workflow = await self._repository.get_workflow(project_id, requirement_id)
        if workflow is None:
            raise NotFoundError("Orchestrator workflow")
        return self._response(workflow)

    async def list(self, project_id: UUID) -> list[OrchestratorWorkflowResponse]:
        return [
            self._response(item)
            for item in await self._repository.list_project_workflows(project_id)
        ]

    async def _advance(
        self, workflow: OrchestratorWorkflow, run_id: UUID
    ) -> OrchestratorWorkflowResponse:
        state: GraphState = {
            "workflow_id": str(workflow.id),
            "project_id": str(workflow.project_id),
            "requirement_id": str(workflow.requirement_id),
            "current_stage": workflow.current_stage.value,
            "halt": False,
            "run_id": str(run_id),
        }
        try:
            await self._graph.ainvoke(state, {"recursion_limit": 100})
        except Exception as error:
            failed = await self._repository.get_workflow(
                workflow.project_id, workflow.requirement_id
            )
            if failed is not None:
                failed.status = OrchestratorStatus.FAILED
                failed.last_error = sanitized_error(error)
                await self._repository.commit()
            raise
        finally:
            await self._repository.release_lease(workflow.id, run_id)
        current = await self._repository.get_workflow(workflow.project_id, workflow.requirement_id)
        if current is None:
            raise NotFoundError("Orchestrator workflow")
        return self._response(current)

    def _build_graph(self):  # type: ignore[no-untyped-def]
        builder = StateGraph(GraphState)
        routes: dict[str, str] = {}
        for stage in OrchestratorStage:
            node_name = stage.value
            builder.add_node(node_name, self._node)
            routes[stage.value] = node_name
        routes["__end__"] = END
        builder.add_conditional_edges(START, self._route, routes)
        for stage in OrchestratorStage:
            builder.add_conditional_edges(stage.value, self._route, routes)
        return builder.compile()

    @staticmethod
    def _route(state: GraphState) -> str:
        return "__end__" if state["halt"] else state["current_stage"]

    async def _node(self, state: GraphState) -> GraphState:
        workflow = await self._repository.get_workflow(
            UUID(state["project_id"]), UUID(state["requirement_id"])
        )
        if workflow is None:
            raise NotFoundError("Orchestrator workflow")
        if not await self._repository.try_acquire_lease(
            workflow.id, UUID(state["run_id"]), self._lease_expiry()
        ):
            raise OrchestratorConflictError("Orchestrator execution lease was lost.")
        stage = OrchestratorStage(state["current_stage"])
        execution = OrchestratorExecution(
            workflow_id=workflow.id,
            stage=stage,
            agent_name=STAGE_AGENT.get(stage),
            status=OrchestratorExecutionStatus.RUNNING,
            input_json={
                "project_id": str(workflow.project_id),
                "requirement_id": str(workflow.requirement_id),
                "stage": stage.value,
            },
            output_json={},
        )
        self._repository.add(execution)
        await self._repository.commit()
        execution_id = execution.id
        try:
            next_stage, pending_action, detail = await self._handle_stage(workflow, stage)
            completed = list(workflow.completed_stages)
            if next_stage != stage and stage.value not in completed:
                completed.append(stage.value)
            workflow.completed_stages = completed
            workflow.current_stage = next_stage
            workflow.current_agent = STAGE_AGENT.get(next_stage)
            workflow.pending_user_action = pending_action
            workflow.artifact_status = await self._artifact_snapshot(
                workflow.project_id, workflow.requirement_id
            )
            workflow.status = (
                OrchestratorStatus.COMPLETED
                if next_stage == OrchestratorStage.COMPLETED
                else OrchestratorStatus.WAITING_USER_ACTION
                if pending_action
                else OrchestratorStatus.ACTIVE
            )
            workflow.last_error = None
            execution.status = (
                OrchestratorExecutionStatus.WAITING
                if pending_action
                else OrchestratorExecutionStatus.SUCCEEDED
            )
            execution.output_json = {
                "next_stage": next_stage.value,
                "pending_user_action": pending_action,
                "detail": detail,
                "artifact_status": workflow.artifact_status,
            }
            execution.completed_at = datetime.now(timezone.utc)
            await self._repository.commit()
            return {
                **state,
                "current_stage": next_stage.value,
                "halt": bool(pending_action) or next_stage == OrchestratorStage.COMPLETED,
            }
        except Exception as error:
            await self._repository.rollback()
            persisted_execution = await self._repository.get_execution(execution_id)
            persisted_workflow = await self._repository.get_workflow(
                UUID(state["project_id"]), UUID(state["requirement_id"])
            )
            error_message = sanitized_error(error)
            if persisted_execution is not None:
                persisted_execution.status = OrchestratorExecutionStatus.FAILED
                persisted_execution.error_message = error_message
                persisted_execution.completed_at = datetime.now(timezone.utc)
            if persisted_workflow is not None:
                persisted_workflow.status = OrchestratorStatus.FAILED
                persisted_workflow.last_error = error_message
            await self._repository.commit()
            raise

    async def _handle_stage(
        self, workflow: OrchestratorWorkflow, stage: OrchestratorStage
    ) -> tuple[OrchestratorStage, str | None, str]:
        project_id = workflow.project_id
        requirement_id = workflow.requirement_id
        project = await self._repository.get_project(project_id)
        requirement = await self._repository.get_requirement(project_id, requirement_id)
        if project is None:
            raise NotFoundError("Project")
        if requirement is None:
            raise NotFoundError("Requirement")

        if stage == OrchestratorStage.PROJECT_CONTEXT:
            if project.project_type == ProjectType.ENHANCEMENT:
                missing = missing_enhancement_context(project.context)
                if missing:
                    raise ContextIncompleteError(missing)
            if project.status != ProjectStatus.READY_FOR_ANALYSIS:
                raise ProjectNotReadyError()
            return OrchestratorStage.REQUIREMENT_ANALYSIS, None, "Project context gate passed."

        if stage == OrchestratorStage.REQUIREMENT_ANALYSIS:
            if requirement.analysis_readiness is None:
                result = await self._requirement_service.analyze(project_id, requirement_id)
                readiness = result.readiness
            else:
                readiness = requirement.analysis_readiness
            if readiness == RequirementReadiness.READY:
                return OrchestratorStage.REQUIREMENT_READY, None, "Requirement is ready."
            if readiness == RequirementReadiness.NEEDS_CLARIFICATION:
                return (
                    OrchestratorStage.CLARIFICATION,
                    "ANSWER_CLARIFICATION",
                    "Requirement Analyst needs user clarification.",
                )
            return (
                OrchestratorStage.CLARIFICATION,
                "RESOLVE_BLOCKED_REQUIREMENT",
                "Requirement Analyst marked the requirement blocked.",
            )

        if stage == OrchestratorStage.CLARIFICATION:
            if requirement.analysis_readiness == RequirementReadiness.READY:
                return OrchestratorStage.REQUIREMENT_READY, None, "Clarification was resolved."
            action = (
                "ANSWER_CLARIFICATION"
                if requirement.analysis_readiness == RequirementReadiness.NEEDS_CLARIFICATION
                else "RESOLVE_BLOCKED_REQUIREMENT"
            )
            return stage, action, "Waiting for a user-provided requirement decision."

        if stage == OrchestratorStage.REQUIREMENT_READY:
            if requirement.analysis_readiness != RequirementReadiness.READY:
                raise OrchestratorConflictError("TO-BE work cannot start before requirement READY.")
            return OrchestratorStage.RESEARCH, None, "Requirement readiness gate passed."

        artifacts = {
            item.artifact_type: item
            for item in await self._repository.list_artifacts(project_id, requirement_id)
        }

        if stage == OrchestratorStage.RESEARCH:
            if ArtifactType.RESEARCH not in artifacts:
                await self._discovery_service.run_research(project_id, requirement_id)
            next_stage = (
                OrchestratorStage.EXISTING_SYSTEM_ANALYSIS
                if project.project_type in {ProjectType.NEW_FEATURE, ProjectType.ENHANCEMENT}
                else OrchestratorStage.SOLUTION_DESIGN
            )
            return next_stage, None, "Research Artifact is available."

        if stage == OrchestratorStage.EXISTING_SYSTEM_ANALYSIS:
            if ArtifactType.EXISTING_SYSTEM_ANALYSIS not in artifacts:
                evidence = [
                    ExistingEvidenceInput.model_validate(item)
                    for item in workflow.state_json.get("existing_system_evidence", [])
                ]
                await self._discovery_service.analyze_existing_system(
                    project_id,
                    AnalyzeExistingSystemRequest(
                        requirement_id=requirement_id,
                        evidence=evidence,
                    ),
                )
            return OrchestratorStage.SOLUTION_DESIGN, None, "Existing system was analyzed."

        if stage == OrchestratorStage.SOLUTION_DESIGN:
            solution = await self._repository.get_solution_workflow(project_id, requirement_id)
            if solution is None:
                await self._solution_service.generate(project_id, requirement_id)
            return (
                OrchestratorStage.USER_APPROVAL,
                "APPROVE_SOLUTION",
                "Solution generated; exact version requires a human decision.",
            )

        if stage == OrchestratorStage.USER_APPROVAL:
            solution = await self._repository.get_solution_workflow(project_id, requirement_id)
            if solution is None:
                return OrchestratorStage.SOLUTION_DESIGN, None, "Solution is missing."
            if solution.status == SolutionWorkflowStatus.APPROVED:
                return (
                    OrchestratorStage.FLOW_UI_TECHNICAL_DESIGN,
                    None,
                    "Approved current Solution unlocks technical design.",
                )
            action = {
                SolutionWorkflowStatus.WAITING_USER_APPROVAL: "APPROVE_SOLUTION",
                SolutionWorkflowStatus.REVISION_REQUESTED: "RETRY_SOLUTION_REVISION",
                SolutionWorkflowStatus.REJECTED: "REOPEN_OR_REVISE_SOLUTION",
            }[solution.status]
            return stage, action, f"Solution state is {solution.status.value}."

        if stage == OrchestratorStage.FLOW_UI_TECHNICAL_DESIGN:
            solution = await self._repository.get_solution_workflow(project_id, requirement_id)
            if solution is None or solution.status != SolutionWorkflowStatus.APPROVED:
                raise OrchestratorConflictError(
                    "Technical design cannot run before current Solution approval."
                )
            if ArtifactType.PROCESS_FLOW not in artifacts:
                await self._design_service.run_flow(project_id, requirement_id)
            if not {
                ArtifactType.DATABASE_DESIGN,
                ArtifactType.API_SPECIFICATION,
            }.issubset(artifacts):
                await self._design_service.run_technical_architecture(project_id, requirement_id)
            refreshed = {
                item.artifact_type
                for item in await self._repository.list_artifacts(project_id, requirement_id)
            }
            if ArtifactType.UI_PROTOTYPE not in refreshed:
                await self._design_service.run_ui_prototype(project_id, requirement_id)
            return OrchestratorStage.QA, None, "Flow, UI, database, and API artifacts are ready."

        if stage == OrchestratorStage.QA:
            quality = await self._repository.get_quality_workflow(project_id, requirement_id)
            if quality is None:
                await self._quality_service.run_qa(project_id, requirement_id)
            return OrchestratorStage.SA_REVIEW, None, "QA artifacts are ready."

        if stage == OrchestratorStage.SA_REVIEW:
            quality = await self._repository.get_quality_workflow(project_id, requirement_id)
            if quality is None or quality.status == QualityWorkflowStatus.READY_FOR_REVIEW:
                await self._quality_service.run_review(project_id, requirement_id)
                quality = await self._repository.get_quality_workflow(project_id, requirement_id)
            if quality is None:
                raise OrchestratorConflictError("SA Review did not produce a quality workflow.")
            if quality.status == QualityWorkflowStatus.PASSED:
                return OrchestratorStage.HANDOFF_READY, None, "SA Reviewer passed all artifacts."
            if quality.status == QualityWorkflowStatus.REVISION_REQUIRED:
                return OrchestratorStage.REVISION_LOOP, None, "Reviewer routed a revision."
            return (
                stage,
                "QUALITY_MANUAL_INTERVENTION",
                "Maximum revision guard requires user intervention.",
            )

        if stage == OrchestratorStage.REVISION_LOOP:
            quality = await self._repository.get_quality_workflow(project_id, requirement_id)
            if quality is None or quality.status != QualityWorkflowStatus.REVISION_REQUIRED:
                return OrchestratorStage.SA_REVIEW, None, "No pending revision remains."
            target = self._next_revision_target(quality.issues_json)
            if target is None:
                raise OrchestratorConflictError(
                    "Reviewer did not provide a routable artifact issue."
                )
            await self._quality_service.revise(project_id, requirement_id, target)
            revised_quality = await self._repository.get_quality_workflow(
                project_id, requirement_id
            )
            history = list(workflow.revision_history)
            history.append(
                {
                    "revision": revised_quality.revision_count if revised_quality else None,
                    "artifact": target.value,
                    "routed_to": STAGE_AGENT[OrchestratorStage.REVISION_LOOP],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            workflow.revision_history = history
            return OrchestratorStage.SA_REVIEW, None, f"Revised {target.value}."

        if stage == OrchestratorStage.HANDOFF_READY:
            quality = await self._repository.get_quality_workflow(project_id, requirement_id)
            if quality is None or quality.status != QualityWorkflowStatus.PASSED:
                raise OrchestratorConflictError("Handoff requires a current reviewer PASS.")
            handoff = await self._repository.get_handoff_workflow(project_id, requirement_id)
            if handoff is None:
                await self._handoff_service.plan(project_id, requirement_id)
                handoff = await self._repository.get_handoff_workflow(project_id, requirement_id)
            if handoff and handoff.status == HandoffWorkflowStatus.PACKAGE_READY:
                return OrchestratorStage.COMPLETED, None, "Handoff package is complete."
            return (
                stage,
                "PREVIEW_AND_EXPORT_HANDOFF",
                "Development Tasks are ready for preview before package export.",
            )

        return OrchestratorStage.COMPLETED, None, "Workflow completed."

    @staticmethod
    def _next_revision_target(issues: list[dict]) -> ArtifactType | None:
        group_order = (
            ArtifactType.PROCESS_FLOW,
            ArtifactType.UI_PROTOTYPE,
            ArtifactType.DATABASE_DESIGN,
            ArtifactType.API_SPECIFICATION,
            ArtifactType.TEST_SCENARIO,
            ArtifactType.ACCEPTANCE_CRITERIA,
        )
        issue_types = {item.get("artifact") for item in issues}
        return next((item for item in group_order if item.value in issue_types), None)

    async def _artifact_snapshot(self, project_id: UUID, requirement_id: UUID) -> dict:
        return {
            item.artifact_type.value: {
                "version": item.current_version,
                "status": item.status.value,
            }
            for item in await self._repository.list_artifacts(project_id, requirement_id)
        }

    def _lease_expiry(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=self._lease_seconds)

    @staticmethod
    def _response(workflow: OrchestratorWorkflow) -> OrchestratorWorkflowResponse:
        return OrchestratorWorkflowResponse(
            id=workflow.id,
            project_id=workflow.project_id,
            requirement_id=workflow.requirement_id,
            current_stage=workflow.current_stage,
            status=workflow.status,
            current_agent=workflow.current_agent,
            completed_stages=[OrchestratorStage(item) for item in workflow.completed_stages],
            pending_user_action=workflow.pending_user_action,
            artifact_status=workflow.artifact_status,
            revision_history=workflow.revision_history,
            last_error=workflow.last_error,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            executions=workflow.executions,
        )
