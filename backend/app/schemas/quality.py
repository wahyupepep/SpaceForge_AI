from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.domain.artifacts import ArtifactType
from app.domain.quality import QualityWorkflowStatus, ReviewDecision, ReviewSeverity
from app.schemas.artifact import ArtifactResponse


class RunQualityRequest(BaseModel):
    requirement_id: UUID


class RevisionRequest(BaseModel):
    artifact_type: ArtifactType


class ReviewIssueResponse(BaseModel):
    artifact: ArtifactType
    issue: str
    severity: ReviewSeverity
    reason: str
    recommended_revision: str


class QualityWorkflowResponse(BaseModel):
    id: UUID
    project_id: UUID
    requirement_id: UUID
    status: QualityWorkflowStatus
    decision: Optional[ReviewDecision]
    revision_count: int
    max_revisions: int
    development_handoff_allowed: bool
    reviewed_versions: dict[str, int]
    issues: list[ReviewIssueResponse]
    created_at: datetime
    updated_at: datetime


class QualityAgentResponse(BaseModel):
    execution_id: UUID
    workflow: QualityWorkflowResponse
    artifacts: list[ArtifactResponse]
