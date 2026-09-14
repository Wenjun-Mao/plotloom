"""Characterize both factories against the original API-monolith export."""

from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import inspect
import json
from pathlib import Path

from fastapi import FastAPI

from plotloom.api import create_app, create_project_folder_authoring_app
from plotloom.project_storage import ProjectFolderStorage


ORIGINAL_MONOLITH = "5ec8ef83fc3fa6efdd9b3b41f5e76a7a8c2e1daf"
BASELINE_CONTRACT_SHA256 = "1d33b23c3809d63654c780d7ac07ecd2bd6acfe7a8fdb6b18a8a15b98feaa72e"
BASELINE_CONTRACT_BYTES = 206_297


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


def test_both_factories_retain_original_monolith_contract(tmp_path: Path) -> None:
    """Compare complete route/OpenAPI/signature/state/static/lifespan evidence.

    The expected digest was generated from an isolated ``git archive`` of
    ``ORIGINAL_MONOLITH`` before this checkpoint touched API source. The digest
    covers every documented field; only JSON ordering is normalized.
    """

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
        contract = {
            "normal_signature": str(inspect.signature(create_app)),
            "project_folder_signature": str(
                inspect.signature(create_project_folder_authoring_app)
            ),
            "normal_lifespan_is_injected": normal.router.lifespan_context
            is _injected_lifespan,
            "completion_observer_is_registered": scheduler.observer is not None,
            "normal": _describe(normal),
            "project_folder": _describe(folder),
        }
        serialized = json.dumps(
            contract, sort_keys=True, separators=(",", ":")
        ).encode()
        assert len(serialized) == BASELINE_CONTRACT_BYTES
        assert hashlib.sha256(serialized).hexdigest() == BASELINE_CONTRACT_SHA256
    finally:
        normal.state.repository.close()
