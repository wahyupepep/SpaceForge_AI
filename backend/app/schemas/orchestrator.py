from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.orchestrator import (
    OrchestratorExecutionStatus,
    OrchestratorStage,
    OrchestratorStatus,
)
from app.schemas.discovery import ExistingEvidenceInput


class StartOrchestratorRequest(BaseModel):
    requirement_id: UUID
    existing_system_evidence: list[ExistingEvidenceInput] = Field(default_factory=list)


class OrchestratorExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    stage: OrchestratorStage
    agent_name: str | None
    status: OrchestratorExecutionStatus
    input_json: dict
    output_json: dict
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class OrchestratorWorkflowResponse(BaseModel):
    id: UUID
    project_id: UUID
    requirement_id: UUID
    current_stage: OrchestratorStage
    status: OrchestratorStatus
    current_agent: str | None
    completed_stages: list[OrchestratorStage]
    pending_user_action: str | None
    artifact_status: dict[str, dict]
    revision_history: list[dict]
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    executions: list[OrchestratorExecutionResponse] = Field(default_factory=list)
