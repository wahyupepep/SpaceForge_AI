from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_project_service
from app.core.errors import ContextIncompleteError
from app.domain.projects import ProjectStatus, ProjectType
from app.main import app
from app.schemas.project import ProjectContextResponse, ProjectResponse

client = TestClient(app)


def sample_project() -> ProjectResponse:
    now = datetime.now(timezone.utc)
    return ProjectResponse(
        id=uuid4(),
        name="Approval enhancement",
        description="Improve approvals.",
        project_type=ProjectType.ENHANCEMENT,
        business_objective="Reduce risk.",
        status=ProjectStatus.DRAFT,
        owner_id=None,
        context=ProjectContextResponse(id=uuid4(), created_at=now, updated_at=now),
        missing_context_fields=["current_flow"],
        created_at=now,
        updated_at=now,
    )


def test_project_crud_routes_use_service_contract() -> None:
    project = sample_project()
    service = AsyncMock()
    service.create.return_value = project
    service.list.return_value = [project]
    service.get.return_value = project
    service.update.return_value = project
    service.delete.return_value = None
    app.dependency_overrides[get_project_service] = lambda: service

    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": project.name,
            "description": project.description,
            "project_type": project.project_type,
            "business_objective": project.business_objective,
            "context": {},
        },
    )
    list_response = client.get("/api/v1/projects")
    get_response = client.get(f"/api/v1/projects/{project.id}")
    update_response = client.patch(f"/api/v1/projects/{project.id}", json={"name": "Updated"})
    delete_response = client.delete(f"/api/v1/projects/{project.id}")
    app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert delete_response.status_code == 204


def test_submit_route_returns_structured_incomplete_context_error() -> None:
    project = sample_project()
    service = AsyncMock()
    service.submit_for_analysis.side_effect = ContextIncompleteError(
        ["current_flow", "current_rules"]
    )
    app.dependency_overrides[get_project_service] = lambda: service

    response = client.post(f"/api/v1/projects/{project.id}/submit-for-analysis")
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "CONTEXT_INCOMPLETE",
        "message": "Enhancement AS-IS context is incomplete.",
        "details": [
            {"field": "current_flow", "reason": "required_for_enhancement"},
            {"field": "current_rules", "reason": "required_for_enhancement"},
        ],
    }


def test_invalid_project_id_uses_standard_validation_error() -> None:
    response = client.get("/api/v1/projects/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
