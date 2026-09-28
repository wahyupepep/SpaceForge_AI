from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.schemas.artifact import ArtifactResponse


class RunDesignAgentRequest(BaseModel):
    requirement_id: UUID


class DesignAgentResponse(BaseModel):
    execution_id: UUID
    artifacts: list[ArtifactResponse]
