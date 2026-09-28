from fastapi.testclient import TestClient

from app.api.v1.routes.health import database_is_ready
from app.main import app

client = TestClient(app)


async def database_available() -> bool:
    return True


async def database_unavailable() -> bool:
    return False


def test_health_check() -> None:
    app.dependency_overrides[database_is_ready] = database_available
    response = client.get("/api/v1/health")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-request-id"]
    assert response.json() == {
        "status": "ok",
        "service": "specforge-api",
        "environment": "development",
        "database": "ok",
    }


def test_request_size_limit_returns_structured_error() -> None:
    response = client.post(
        "/api/v1/projects",
        content=b"{}",
        headers={"content-length": "6000000"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_health_check_uses_standard_error_when_database_is_unavailable() -> None:
    app.dependency_overrides[database_is_ready] = database_unavailable
    response = client.get("/api/v1/health")
    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "SERVICE_UNAVAILABLE",
            "message": "Database connection is unavailable.",
            "details": [],
        }
    }
