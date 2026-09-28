from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_development_handoff_service
from app.domain.handoff import HandoffWorkflowStatus
from app.main import app
from app.schemas.handoff import DevelopmentPlanResponse, HandoffWorkflowResponse
from app.services.development_handoff import ExportedFile
from app.tests.test_requirement_analysis_api import sample_response

client = TestClient(app)


def test_development_handoff_routes_and_download() -> None:
    sample = sample_response()
    project_id = sample.requirement.project_id
    requirement_id = sample.requirement.id
    now = datetime.now(timezone.utc)
    workflow = HandoffWorkflowResponse(
        id=uuid4(),
        project_id=project_id,
        requirement_id=requirement_id,
        status=HandoffWorkflowStatus.TASKS_READY,
        current_task_version=1,
        current_package_version=0,
        task_artifact=sample.artifact,
        current_package=None,
        packages=[],
        created_at=now,
        updated_at=now,
    )
    service = AsyncMock()
    service.plan.return_value = DevelopmentPlanResponse(
        execution_id=uuid4(), workflow=workflow
    )
    service.generate_package.return_value = workflow
    service.get.return_value = workflow
    service.download.return_value = ExportedFile(
        content=b'{"package":"ready"}',
        content_type="application/json; charset=utf-8",
        filename="development-handoff-v1.json",
    )
    app.dependency_overrides[get_development_handoff_service] = lambda: service

    plan = client.post(
        f"/api/v1/projects/{project_id}/handoff/plan",
        json={"requirement_id": str(requirement_id)},
    )
    generate = client.post(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}/handoff/generate",
        json={"expected_task_version": 1},
    )
    detail = client.get(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}/handoff"
    )
    download = client.get(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}/"
        "handoff/packages/1/download/json"
    )
    app.dependency_overrides.clear()

    assert [plan.status_code, generate.status_code, detail.status_code] == [200, 200, 200]
    assert download.status_code == 200
    assert download.headers["content-disposition"].endswith(
        'filename="development-handoff-v1.json"'
    )
