"""Explicit one-start pre-video admission and durable read/control routes."""
from fastapi import FastAPI, status
from contextlib import asynccontextmanager
from ..autopilot_contracts import LaunchRequest, RunControlRequest, RunView
from ..autopilot_service import AutopilotService


def register_autopilot_runtime(app, opened_project, registry):
    service = AutopilotService(app.state.project_folder_storage, registry)
    app.state.autopilot_service = service
    base_lifespan = app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(owned_app):
        async with base_lifespan(owned_app) as state:
            service.start()
            try:
                yield state
            finally:
                service.close()
    app.router.lifespan_context = lifespan
    register_autopilot_routes(app, opened_project, service)


def register_autopilot_routes(app: FastAPI, opened_project, service):
    @app.get("/api/v2/autopilot/controller")
    def controller_status():
        return {"blocker": service.controller_blocker}

    @app.get("/api/v2/projects/{project_id}/autopilot", response_model=RunView | None)
    def current(project_id: str):
        with opened_project(project_id) as store:
            return store.repository.autopilot.current(project_id)

    @app.post("/api/v2/projects/{project_id}/autopilot/start", response_model=RunView, status_code=status.HTTP_201_CREATED)
    def start(project_id: str, body: LaunchRequest):
        return service.launch(project_id, body)

    @app.post("/api/v2/projects/{project_id}/autopilot/control", response_model=RunView)
    def control(project_id: str, body: RunControlRequest):
        return service.control(project_id, body)
