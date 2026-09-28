from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_artifact_service, get_requirement_service
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.requirements import RequirementStatus
from app.main import app
from app.schemas.artifact import ArtifactResponse, ArtifactVersionResponse
from app.schemas.requirement import RequirementResponse

client = TestClient(app)


def sample_requirement(project_id=None) -> RequirementResponse:
    now = datetime.now(timezone.utc)
    return RequirementResponse(
        id=uuid4(),
        project_id=project_id or uuid4(),
        title="Tiered approval",
        raw_requirement="Add approval tiers based on amount.",
        business_objective="Reduce risk.",
        status=RequirementStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )


def sample_artifact(project_id, requirement_id) -> ArtifactResponse:
    now = datetime.now(timezone.utc)
    content = {
        "feature": "Tiered approval",
        "business_objective": "Reduce risk",
        "problem_statement": "Controls are insufficient",
        "actors": [],
        "known_requirements": [],
        "business_rules": [],
        "constraints": [],
        "dependencies": [],
        "assumptions": [],
        "unknown_information": [],
    }
    version = ArtifactVersionResponse(
        id=uuid4(), version=1, content_json=content, created_by="USER", created_at=now
    )
    return ArtifactResponse(
        id=uuid4(),
        project_id=project_id,
        requirement_id=requirement_id,
        artifact_type=ArtifactType.REQUIREMENT_BASELINE,
        version=1,
        content_json=content,
        status=ArtifactStatus.DRAFT,
        created_by="USER",
        created_at=now,
        updated_at=now,
        versions=[version],
    )


def test_requirement_crud_routes_use_service_contract() -> None:
    requirement = sample_requirement()
    service = AsyncMock()
    service.create.return_value = requirement
    service.list.return_value = [requirement]
    service.get.return_value = requirement
    service.update.return_value = requirement
    app.dependency_overrides[get_requirement_service] = lambda: service

    payload = {"title": requirement.title, "raw_requirement": requirement.raw_requirement}
    create = client.post(f"/api/v1/projects/{requirement.project_id}/requirements", json=payload)
    listed = client.get(f"/api/v1/projects/{requirement.project_id}/requirements")
    fetched = client.get(f"/api/v1/projects/{requirement.project_id}/requirements/{requirement.id}")
    updated = client.patch(
        f"/api/v1/projects/{requirement.project_id}/requirements/{requirement.id}",
        json={"title": "Updated"},
    )
    deleted = client.delete(
        f"/api/v1/projects/{requirement.project_id}/requirements/{requirement.id}"
    )
    app.dependency_overrides.clear()

    assert [create.status_code, listed.status_code, fetched.status_code] == [201, 200, 200]
    assert updated.status_code == 200
    assert deleted.status_code == 204


def test_artifact_routes_expose_current_and_version_history() -> None:
    requirement = sample_requirement()
    artifact = sample_artifact(requirement.project_id, requirement.id)
    service = AsyncMock()
    service.create.return_value = artifact
    service.list.return_value = [artifact]
    service.get.return_value = artifact
    service.create_version.return_value = artifact
    app.dependency_overrides[get_artifact_service] = lambda: service

    create = client.post(
        f"/api/v1/projects/{requirement.project_id}/artifacts",
        json={
            "artifact_type": "REQUIREMENT_BASELINE",
            "requirement_id": str(requirement.id),
            "content_json": artifact.content_json,
        },
    )
    listed = client.get(f"/api/v1/projects/{requirement.project_id}/artifacts")
    fetched = client.get(f"/api/v1/projects/{requirement.project_id}/artifacts/{artifact.id}")
    versioned = client.post(
        f"/api/v1/projects/{requirement.project_id}/artifacts/{artifact.id}/versions",
        json={"content_json": artifact.content_json},
    )
    app.dependency_overrides.clear()

    assert [create.status_code, listed.status_code, fetched.status_code] == [201, 200, 200]
    assert versioned.status_code == 201
    assert fetched.json()["versions"][0]["version"] == 1
