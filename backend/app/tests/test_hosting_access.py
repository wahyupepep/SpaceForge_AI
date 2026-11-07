from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_optional_current_user, get_project_service
from app.core.config import settings
from app.db.session import get_db_session
from app.main import app


@pytest.fixture
def protected_client(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "auth_required", True)
    session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.clear()


def test_production_project_list_requires_login(protected_client):  # type: ignore[no-untyped-def]
    client, session = protected_client
    app.dependency_overrides[get_optional_current_user] = lambda: None

    response = client.get("/api/v1/projects")
    assert response.status_code == 401
    session.scalar.assert_not_awaited()


@pytest.mark.parametrize("suffix", ["/requirements", "/orchestrator-workflows", "/evidence"])
def test_nested_project_routes_reject_another_owners_project(protected_client, suffix):  # type: ignore[no-untyped-def]
    client, session = protected_client
    session.scalar.return_value = None
    app.dependency_overrides[get_optional_current_user] = lambda: SimpleNamespace(id=uuid4())

    response = client.get(f"/api/v1/projects/{uuid4()}{suffix}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_owner_can_access_the_project(protected_client):  # type: ignore[no-untyped-def]
    client, session = protected_client
    project_id = uuid4()
    session.scalar.return_value = project_id
    app.dependency_overrides[get_optional_current_user] = lambda: SimpleNamespace(id=uuid4())
    service = AsyncMock()
    app.dependency_overrides[get_project_service] = lambda: service

    response = client.delete(f"/api/v1/projects/{project_id}")
    assert response.status_code == 204
    service.delete.assert_awaited_once_with(project_id)
