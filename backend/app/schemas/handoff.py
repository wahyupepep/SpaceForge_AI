from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.handoff import HandoffWorkflowStatus
from app.schemas.artifact import ArtifactResponse


class PlanDevelopmentRequest(BaseModel):
    requirement_id: UUID


class GenerateHandoffRequest(BaseModel):
    expected_task_version: int = Field(ge=1)


class ArtifactSourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str
    artifact_id: UUID
    version: int


class HandoffSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: str
    slug: str
    title: str
    source_artifacts: list[ArtifactSourceReference]
    content: object


class TraceabilityEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    requirement: str
    acceptance_criteria: list[str]
    reference_artifacts: list[str]


class TrelloCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    target_list: str
    labels: list[str]
    dependencies: list[str]
    checklist: list[str]
    reference_artifacts: list[str]


class TrelloList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    position: int


class TrelloReadyContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    board_name: str
    lists: list[TrelloList]
    cards: list[TrelloCard]


class HandoffPackageContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_name: str
    project_id: UUID
    requirement_id: UUID
    source_versions: dict[str, int]
    sections: list[HandoffSection]
    traceability: list[TraceabilityEntry]
    trello_ready: TrelloReadyContent


class HandoffPackageResponse(BaseModel):
    id: UUID
    version: int
    development_task_version_id: UUID
    source_versions: dict[str, int]
    content_json: HandoffPackageContent
    created_at: datetime


class HandoffWorkflowResponse(BaseModel):
    id: UUID
    project_id: UUID
    requirement_id: UUID
    status: HandoffWorkflowStatus
    current_task_version: int
    current_package_version: int
    task_artifact: ArtifactResponse
    current_package: Optional[HandoffPackageResponse]
    packages: list[HandoffPackageResponse]
    created_at: datetime
    updated_at: datetime


class DevelopmentPlanResponse(BaseModel):
    execution_id: UUID
    workflow: HandoffWorkflowResponse
