from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.solution import SolutionApprovalAction, SolutionWorkflowStatus
from app.schemas.artifact import ArtifactResponse


class GenerateSolutionRequest(BaseModel):
    requirement_id: UUID


class SolutionApprovalRequest(BaseModel):
    action: SolutionApprovalAction
    note: Optional[str] = Field(default=None, max_length=5000)
    acted_by: str = Field(default="USER", min_length=1, max_length=100)
    expected_version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_note(self) -> SolutionApprovalRequest:
        self.note = self.note.strip() if self.note else None
        if self.action == SolutionApprovalAction.REQUEST_REVISION and not self.note:
            raise ValueError("note is required when requesting a revision")
        return self


class SolutionApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_version_id: UUID
    action: SolutionApprovalAction
    note: Optional[str]
    acted_by: str
    created_at: datetime


class SolutionWorkflowResponse(BaseModel):
    id: UUID
    project_id: UUID
    requirement_id: UUID
    status: SolutionWorkflowStatus
    current_version: int
    technical_design_allowed: bool
    artifact: ArtifactResponse
    approvals: list[SolutionApprovalResponse]
    created_at: datetime
    updated_at: datetime


class SolutionAnalysisResponse(BaseModel):
    execution_id: UUID
    workflow: SolutionWorkflowResponse
