"""Runtime controls must agree with the routes composed by the service."""

from pathlib import Path

from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.project_storage import ProjectFolderStorage
from plotloom.runtime import build_runtime_app
from tests.test_production_project_folder_runtime import _settings


def test_native_composition_does_not_advertise_api_provider_controls(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        response = client.get("/api/v2/runtime-capabilities")
        assert response.status_code == 200
        assert response.json() == {
            "durableProjectDrafts": True,
            "durableMediaDrafts": True,
            "explicitProjectClose": True,
            "portableSnapshots": True,
            "apiTextPipeline": False,
        }
        assert client.get("/api/v2/text-provider-profiles").status_code == 404
        assert client.get("/api/v2/authoring-draft-capabilities").status_code == 404
        routes = {route.path for route in client.app.routes}
        assert "/api/v2/projects/{project_id}/runs" in routes
        assert "/api/v2/projects/{project_id}/pipeline-runs" not in routes
        assert "/api/v2/projects/{project_id}/rebuilds" not in routes
        assert not any(path.startswith("/api/v2/runs/") for path in routes)


def test_api_composition_advertises_its_actual_provider_routes(tmp_path: Path) -> None:
    with TestClient(build_runtime_app(_settings(tmp_path))) as client:
        capabilities = client.get("/api/v2/runtime-capabilities")
        assert capabilities.status_code == 200
        assert capabilities.json()["apiTextPipeline"] is True
        assert client.get("/api/v2/text-provider-profiles").status_code == 200
        routes = {route.path for route in client.app.routes}
        for path in (
            "/api/v2/projects/{project_id}/pipeline-runs",
            "/api/v2/projects/{project_id}/rebuilds",
            "/api/v2/runs/{run_id}/progress",
            "/api/v2/runs/{run_id}/trace",
            "/api/v2/runs/{run_id}/execution-trace",
            "/api/v2/runs/{run_id}/resume",
            "/api/v2/runs/{run_id}/cancel",
        ):
            assert path in routes
