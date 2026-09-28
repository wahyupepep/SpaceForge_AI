from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.artifacts import ArtifactStatus, ArtifactType


class ArtifactCreate(BaseModel):
    artifact_type: ArtifactType
    content_json: dict
    created_by: str = Field(default="USER", min_length=1, max_length=100)
    requirement_id: Optional[UUID] = None
    status: ArtifactStatus = ArtifactStatus.DRAFT


class ArtifactVersionCreate(BaseModel):
    content_json: dict
    created_by: str = Field(default="USER", min_length=1, max_length=100)
    status: Optional[ArtifactStatus] = None


class ArtifactVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: int
    content_json: dict
    created_by: str
    created_at: datetime


class ArtifactResponse(BaseModel):
    id: UUID
    project_id: UUID
    requirement_id: Optional[UUID]
    artifact_type: ArtifactType
    version: int
    content_json: dict
    status: ArtifactStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    versions: list[ArtifactVersionResponse] = Field(default_factory=list)
