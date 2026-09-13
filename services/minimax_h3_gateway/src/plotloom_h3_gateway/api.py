"""FastAPI presentation layer for the narrow trusted H3 gateway contract."""
from __future__ import annotations

import hmac
import json
from contextlib import asynccontextmanager
from typing import Any

import requests
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import Response

from .contracts import CreateJobRequest, GatewayError, GatewaySettings, MAX_UPLOAD_BYTES
from .gateway import H3Gateway
from .worker import GatewayDispatchWorker


def create_app(
    settings: GatewaySettings | None = None, *, session: requests.Session | Any | None = None
) -> FastAPI:
    """Create the authenticated HTTP boundary around one durable gateway."""

    gateway = H3Gateway(settings or GatewaySettings.from_environment(), session=session)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker = GatewayDispatchWorker(gateway)
        app.state.dispatch_worker = worker
        if gateway.settings.dispatch_worker_enabled:
            worker.start()
        try:
            yield
        finally:
            if gateway.settings.dispatch_worker_enabled:
                worker.stop()

    app = FastAPI(title="Plotloom MiniMax-H3 gateway", version="1.2", lifespan=lifespan)
    app.state.gateway = gateway

    def authorize(authorization: str | None = Header(default=None)) -> None:
        expected = f"Bearer {gateway.settings.api_key}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.exception_handler(GatewayError)
    async def handle_gateway_error(_: Any, error: GatewayError) -> Response:
        return Response(
            content=json.dumps({"error": error.code}),
            status_code=error.status_code,
            media_type="application/json",
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return gateway.health()

    @app.post("/v1/assets", dependencies=[Depends(authorize)])
    async def upload_asset(image: UploadFile = File(...)) -> dict[str, Any]:
        content = await image.read(MAX_UPLOAD_BYTES + 1)
        asset = gateway.add_asset(content, mime_type=(image.content_type or "").lower())
        return {
            "assetId": asset["id"],
            "mimeType": asset["mime_type"],
            "width": asset["width"],
            "height": asset["height"],
            "sha256": asset["sha256"],
        }

    @app.post("/v1/video-jobs", dependencies=[Depends(authorize)], status_code=202)
    def create_video_job(request: CreateJobRequest) -> dict[str, Any]:
        return _job_response(gateway, gateway.create_job(request))

    @app.get("/v1/video-jobs/{job_id}", dependencies=[Depends(authorize)])
    def get_video_job(job_id: str) -> dict[str, Any]:
        return _job_response(gateway, gateway.refresh_job(job_id))

    @app.post("/v1/video-jobs/{job_id}/cancel", dependencies=[Depends(authorize)])
    def cancel_video_job(job_id: str) -> dict[str, Any]:
        return _job_response(gateway, gateway.cancel_job(job_id))

    @app.get("/v1/video-jobs/{job_id}/output", dependencies=[Depends(authorize)])
    def get_output(job_id: str) -> Response:
        return Response(content=gateway.read_output(job_id), media_type="video/mp4")

    return app


def _job_response(gateway: H3Gateway, job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["id"],
        "status": job["status"],
        "profileId": job["profile_id"],
        "aspectPolicy": job["aspect_policy"],
        "error": job["error_code"],
        "outputReady": gateway.output_is_ready(job),
    }
