from typing import Any, Optional


class ApplicationError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


class ServiceUnavailableError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=message,
            status_code=503,
        )


class NotFoundError(ApplicationError):
    def __init__(self, resource: str) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} was not found.",
            status_code=404,
        )


class ContextIncompleteError(ApplicationError):
    def __init__(self, missing_fields: list[str]) -> None:
        super().__init__(
            code="CONTEXT_INCOMPLETE",
            message="Enhancement AS-IS context is incomplete.",
            status_code=409,
            details=[
                {"field": field, "reason": "required_for_enhancement"} for field in missing_fields
            ],
        )


class ProjectNotReadyError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="PROJECT_NOT_READY",
            message="Project context must be ready for analysis before requirement intake.",
            status_code=409,
        )


class ArtifactContentInvalidError(ApplicationError):
    def __init__(self, details: list[dict[str, Any]]) -> None:
        super().__init__(
            code="ARTIFACT_CONTENT_INVALID",
            message="Artifact content does not match the schema for its artifact type.",
            status_code=422,
            details=details,
        )


class ArtifactConflictError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="ARTIFACT_CONFLICT",
            message="The artifact or artifact version already exists.",
            status_code=409,
        )


class ClarificationPendingError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="CLARIFICATION_PENDING",
            message="Answer every pending clarification before running analysis again.",
            status_code=409,
        )


class ClarificationAnswerInvalidError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="CLARIFICATION_ANSWER_INVALID",
            message=message,
            status_code=422,
        )


class AgentExecutionError(ApplicationError):
    def __init__(self, execution_id: str) -> None:
        super().__init__(
            code="AGENT_EXECUTION_FAILED",
            message="AI agent execution could not be completed.",
            status_code=502,
            details=[{"execution_id": execution_id}],
        )


class RequirementNotReadyError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="REQUIREMENT_NOT_READY",
            message="Requirement Baseline must be READY before specialist analysis.",
            status_code=409,
        )


class ArtifactDependencyMissingError(ApplicationError):
    def __init__(self, artifact_type: str) -> None:
        super().__init__(
            code="ARTIFACT_DEPENDENCY_MISSING",
            message=f"Required {artifact_type} artifact was not found.",
            status_code=409,
        )


class SolutionWorkflowConflictError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(code="SOLUTION_WORKFLOW_CONFLICT", message=message, status_code=409)


class TechnicalDesignBlockedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="TECHNICAL_DESIGN_BLOCKED",
            message="Downstream design requires an approved current Solution version.",
            status_code=409,
        )


class QualityGateBlockedError(ApplicationError):
    def __init__(
        self, message: str = "Quality gate has not passed for the current artifacts."
    ) -> None:
        super().__init__(code="QUALITY_GATE_BLOCKED", message=message, status_code=409)


class QualityWorkflowConflictError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(code="QUALITY_WORKFLOW_CONFLICT", message=message, status_code=409)


class MaximumRevisionReachedError(ApplicationError):
    def __init__(self, maximum: int) -> None:
        super().__init__(
            code="MAXIMUM_REVISION_REACHED",
            message=f"Quality revision limit of {maximum} has been reached.",
            status_code=409,
        )


class OrchestratorConflictError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(code="ORCHESTRATOR_CONFLICT", message=message, status_code=409)
