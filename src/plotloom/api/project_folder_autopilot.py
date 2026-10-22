"""Explicit one-start pre-video admission and durable read/control routes."""
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, status

from ..autopilot_contracts import (
    ContinueRequest,
    LaunchRequest,
    RunControlRequest,
    RunView,
)
from ..autopilot_handoff_contracts import BulkHumanHandoffRequest, HumanHandoffRequest
from ..autopilot_service import AutopilotService
from ..persistence.project.autopilot_handoff import record_handoff, review_material


def register_autopilot_runtime(app, opened_project, registry):
    service = AutopilotService(app.state.project_folder_storage, registry)
    app.state.autopilot_service = service
    base_lifespan = app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(owned_app):
        async with base_lifespan(owned_app) as state:
            with service.runtime_owner():
                yield state
    app.router.lifespan_context = lifespan
    register_autopilot_routes(app, opened_project, service)


def register_autopilot_routes(app: FastAPI, opened_project, service):
    from ..text_correction_contracts import TextRetryGrant

    @app.get("/api/v2/projects/{project_id}/autopilot/text-failure")
    def text_failure(project_id: str, stage: Literal["outline", "characters", "art"] | None = None):
        from ..autopilot_text_failures import failure_context
        with opened_project(project_id) as store:
            return failure_context(store, service.registry, stage=stage)

    @app.post("/api/v2/projects/{project_id}/autopilot/text-retry", response_model=RunView)
    def text_retry(project_id: str, body: TextRetryGrant):
        return service.retry_text(project_id, body)

    @app.get("/api/v2/autopilot/controller")
    def controller_status():
        return {"blocker": service.controller_blocker}

    @app.get("/api/v2/projects/{project_id}/autopilot/launch-context")
    def launch_context(project_id: str):
        from ..exceptions import InvalidTransitionError
        from ..persistence.project.autopilot_freshness import assert_fresh
        with opened_project(project_id) as store, store.repository._read() as session:
            project = store.repository._project_access.rows.project(session, project_id)
            eligible = project.archived_at is None
            try:
                assert_fresh(session, project_id)
            except InvalidTransitionError:
                eligible = False
            return {"eligible": eligible, "briefRevision": project.revision}

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

    @app.get("/api/v2/projects/{project_id}/autopilot/review")
    def review(project_id: str):
        with opened_project(project_id) as store:
            return review_material(store)

    @app.get("/api/v2/projects/{project_id}/autopilot/delivery-evidence")
    def delivery_evidence(project_id: str):
        # One authority admission for the exact gallery metadata projection.
        with opened_project(project_id) as store:
            media = store.media
            return {"assets": media.list_managed_assets(project_id),
                "characters": media.list_character_reference_proposals(project_id),
                "art": media.list_art_reference_proposals(project_id),
                "images": media.list_image_jobs(project_id)}

    @app.get("/api/v2/projects/{project_id}/autopilot/continuation-context")
    def continuation_context(project_id: str):
        with opened_project(project_id) as store:
            return store.repository.autopilot.continuation_context(project_id)

    @app.post("/api/v2/projects/{project_id}/autopilot/continue", response_model=RunView)
    def continue_material(project_id: str, body: ContinueRequest):
        return service.continue_material(project_id, body)

    @app.post("/api/v2/projects/{project_id}/autopilot/handoff", response_model=RunView)
    def handoff(project_id: str, body: BulkHumanHandoffRequest | HumanHandoffRequest):
        with opened_project(project_id) as store:
            return record_handoff(store, body)
