from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.dependencies import get_design_generation_service
from app.main import app
from app.schemas.design import DesignAgentResponse
from app.services.design_generation import PrototypeFile
from app.tests.test_requirement_analysis_api import sample_response

client = TestClient(app)


def test_design_routes_and_sandboxed_prototype_response() -> None:
    sample = sample_response()
    response = DesignAgentResponse(execution_id=sample.execution_id, artifacts=[sample.artifact])
    service = AsyncMock()
    service.run_flow.return_value = response
    service.run_ui_prototype.return_value = response
    service.run_technical_architecture.return_value = response
    service.read_prototype_file.return_value = PrototypeFile(
        content=b"<!doctype html><html></html>",
        content_type="text/html; charset=utf-8",
        filename="approval.html",
    )
    app.dependency_overrides[get_design_generation_service] = lambda: service
    project_id = sample.requirement.project_id
    requirement_id = sample.requirement.id
    payload = {"requirement_id": str(requirement_id)}

    flow = client.post(f"/api/v1/projects/{project_id}/design/flow", json=payload)
    ui = client.post(f"/api/v1/projects/{project_id}/design/ui-prototype", json=payload)
    technical = client.post(
        f"/api/v1/projects/{project_id}/design/technical-architecture", json=payload
    )
    prototype = client.get(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}/"
        f"ui-prototypes/{sample.artifact.id}/versions/1/files/approval.html"
    )
    app.dependency_overrides.clear()

    assert [flow.status_code, ui.status_code, technical.status_code] == [200, 200, 200]
    assert prototype.status_code == 200
    assert "sandbox allow-scripts" in prototype.headers["content-security-policy"]
    assert prototype.text.startswith("<!doctype html>")
