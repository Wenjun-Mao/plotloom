"""Explicit setup/draft/Start and atomic whole-pack review routes."""
from contextlib import asynccontextmanager

from pydantic import Field

from plotloom.domain_base import CamelModel
from ..video_batch_contracts import (
    BatchConfirmation,
    BatchControl,
    BatchDirectionsDraft,
    BatchRejectedReplacement,
    BatchSetup,
    BatchStart,
)
from ..video_batch_runtime import VideoBatchRuntime
from ..video_batch_service import VideoBatchService


class DraftRequest(CamelModel):
    expected_revision: int = Field(ge=1)

class EditDirections(DraftRequest):
    draft: BatchDirectionsDraft


def register_video_batch_runtime(app, storage, registry, video):
    service = VideoBatchService(storage, registry, video)
    runtime = VideoBatchRuntime(service)
    app.state.video_batch_service, app.state.video_batch_runtime = service, runtime
    base = app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(owned_app):
        async with base(owned_app) as state:
            with runtime.runtime_owner():
                yield state
    app.router.lifespan_context = lifespan
    prefix = "/api/v2/projects/{project_id}/video-batch"

    @app.get(prefix)
    def current(project_id: str):
        return service.current(project_id)

    @app.post(prefix + "/setup")
    def setup(project_id: str, body: BatchSetup):
        return service.setup(project_id, body)

    @app.post(prefix + "/replace-rejected")
    def replace_rejected(project_id: str, body: BatchRejectedReplacement):
        return service.replace_rejected(project_id, body)

    @app.post(prefix + "/draft")
    def draft(project_id: str, body: DraftRequest):
        return service.draft(project_id, body.expected_revision)

    @app.post(prefix + "/directions")
    def edit(project_id: str, body: EditDirections):
        return service.edit_directions(project_id, body.expected_revision, body.draft)

    @app.post(prefix + "/start")
    def start(project_id: str, body: BatchStart):
        return service.start(project_id, body)

    @app.post(prefix + "/control")
    def control(project_id: str, body: BatchControl):
        return service.control(project_id, body)

    @app.get(prefix + "/review")
    def review(project_id: str):
        return service.review(project_id)

    @app.post(prefix + "/confirm")
    def confirm(project_id: str, body: BatchConfirmation):
        return service.confirm(project_id, body)
