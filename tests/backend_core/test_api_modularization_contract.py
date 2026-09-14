"""Characterize both factories against the original API-monolith export."""

from __future__ import annotations

from contextlib import asynccontextmanager
import inspect
from pathlib import Path

from fastapi import FastAPI

from plotloom.api import create_app, create_project_folder_authoring_app
from plotloom.project_storage import ProjectFolderStorage


@asynccontextmanager
async def _injected_lifespan(_app: FastAPI):
    yield


class _CompletionObserverScheduler:
    def __init__(self) -> None:
        self.observer: object | None = None

    def set_completion_observer(self, observer: object) -> None:
        self.observer = observer


def _route_inventory(app: FastAPI) -> list[dict[str, object]]:
    return sorted(
        [
            {
                "path": route.path,
                "methods": sorted(route.methods or []),
                "name": route.name,
                "include_in_schema": route.include_in_schema,
            }
            for route in app.routes
            if hasattr(route, "methods")
        ],
        key=lambda item: (item["path"], item["methods"], item["name"]),
    )


def _operation_inventory(app: FastAPI) -> dict[str, object]:
    return {
        path: {
            method: {
                key: operation[key]
                for key in (
                    "operationId",
                    "deprecated",
                    "parameters",
                    "responses",
                    "requestBody",
                )
                if key in operation
            }
            for method, operation in sorted(operations.items())
        }
        for path, operations in sorted(app.openapi()["paths"].items())
    }


def _describe(app: FastAPI) -> dict[str, object]:
    return {
        "routes": _route_inventory(app),
        "openapi": {
            "paths": _operation_inventory(app),
            "schemas": app.openapi().get("components", {}).get("schemas", {}),
        },
        "state_keys": sorted(app.state._state),
        "static_mount": [
            {
                "path": route.path,
                "name": route.name,
                "app_type": type(route.app).__name__,
            }
            for route in app.routes
            if route.__class__.__name__ == "Mount"
        ],
    }


def test_direct_factory_accepts_production_runtime_collaborators(tmp_path: Path) -> None:
    """The folder factory remains explicit; runtime adds its typed owners."""

    static = tmp_path / "contract-static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html>")
    outputs = tmp_path / "outputs"
    application_data = tmp_path / "application-data"
    outputs.mkdir()
    application_data.mkdir()
    scheduler = _CompletionObserverScheduler()
    normal = create_app(
        run_scheduler=scheduler, static_dir=static, lifespan=_injected_lifespan
    )
    folder = create_project_folder_authoring_app(
        ProjectFolderStorage(
            outputs_root=outputs, application_data_root=application_data
        )
    )
    try:
        signature = inspect.signature(create_project_folder_authoring_app)
        assert {"run_dispatcher", "text_admission", "static_dir", "lifespan"}.issubset(
            signature.parameters
        )
        assert normal.router.lifespan_context is _injected_lifespan
        assert scheduler.observer is not None
        assert "project_folder_storage" in folder.state._state
        assert "/api/v2/projects/{project_id}/snapshots" in folder.openapi()["paths"]
    finally:
        normal.state.repository.close()
