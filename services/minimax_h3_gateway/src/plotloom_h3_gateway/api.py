"""FastAPI presentation layer for the narrow trusted H3 gateway contract."""
from __future__ import annotations

import hmac
import json
from contextlib import asynccontextmanager
from typing import Any

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

from .contracts import (
    CreateJobFromImageRequest,
    CreateJobFromSourceUrlRequest,
    CreateJobRequest,
    GatewayError,
    GatewaySettings,
    MAX_UPLOAD_BYTES,
    SourceUrlAssetRequest,
)
from .gateway import H3Gateway
from .worker import GatewayDispatchWorker


def create_app(
    settings: GatewaySettings | None = None,
    *,
    session: requests.Session | Any | None = None,
    source_session: requests.Session | Any | None = None,
) -> FastAPI:
    """Create the authenticated HTTP boundary around one durable gateway."""

    gateway = H3Gateway(
        settings or GatewaySettings.from_environment(),
        session=session,
        source_session=source_session,
    )

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

    app = FastAPI(title="Plotloom MiniMax-H3 gateway", version="1.3", lifespan=lifespan)
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
    async def upload_asset(request: Request) -> dict[str, Any]:
        content = await _asset_content(request, gateway)
        asset = gateway.add_asset(content)
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

    @app.post("/v1/video-jobs/from-image", dependencies=[Depends(authorize)], status_code=202)
    async def create_video_job_from_image(request: Request) -> dict[str, Any]:
        content, job_request = await _one_step_submission(request, gateway)
        return _job_response(
            gateway,
            gateway.create_job_from_image(job_request, content=content),
        )

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


async def _asset_content(request: Request, gateway: H3Gateway) -> bytes:
    media_type = _request_media_type(request)
    if media_type == "multipart/form-data":
        content, _ = await _read_multipart_image(request, allowed_fields={"image"})
        return content
    if media_type == "application/json":
        payload = await _json_object(request)
        source = _validated_model(SourceUrlAssetRequest, payload)
        return gateway.source_images.fetch(source.source_url)
    raise GatewayError("request_media_type_not_supported", 415)


async def _one_step_submission(
    request: Request, gateway: H3Gateway
) -> tuple[bytes, CreateJobFromImageRequest]:
    media_type = _request_media_type(request)
    if media_type == "multipart/form-data":
        content, fields = await _read_multipart_image(
            request,
            allowed_fields={"image", "prompt", "aspectPolicy", "profileId", "seed", "idempotencyKey"},
        )
        _reject_one_step_idempotency(fields)
        job_request = _validated_model(CreateJobFromImageRequest, fields)
        gateway.validate_image_job_request(job_request)
        return content, job_request
    if media_type == "application/json":
        payload = await _json_object(request)
        _reject_one_step_idempotency(payload)
        source_request = _validated_model(CreateJobFromSourceUrlRequest, payload)
        gateway.validate_image_job_request(source_request)
        return gateway.source_images.fetch(source_request.source_url), source_request
    raise GatewayError("request_media_type_not_supported", 415)


def _request_media_type(request: Request) -> str:
    return request.headers.get("content-type", "").partition(";")[0].strip().lower()


async def _json_object(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise GatewayError("request_body_invalid", 400) from None
    if not isinstance(payload, dict):
        raise GatewayError("request_body_invalid", 400)
    return payload


async def _read_multipart_image(
    request: Request, *, allowed_fields: set[str]
) -> tuple[bytes, dict[str, Any]]:
    form = await request.form()
    received_fields = set(form.keys())
    if received_fields - allowed_fields:
        raise GatewayError("request_fields_invalid", 422)
    for field in received_fields:
        if len(form.getlist(field)) != 1:
            raise GatewayError("request_fields_invalid", 422)
    image = form.get("image")
    if image is None or not callable(getattr(image, "read", None)):
        raise GatewayError("image_file_required", 422)
    content = await image.read(MAX_UPLOAD_BYTES + 1)
    fields = {field: form.get(field) for field in received_fields if field != "image"}
    return content, fields


def _validated_model(model: type[BaseModel], payload: dict[str, Any]) -> Any:
    try:
        return model.model_validate(payload)
    except ValidationError as error:
        has_source_url_error = any(
            "sourceUrl" in issue["loc"] or "source_url" in issue["loc"]
            for issue in error.errors()
        )
        raise GatewayError("source_url_invalid" if has_source_url_error else "request_invalid", 422) from error


def _reject_one_step_idempotency(payload: dict[str, Any]) -> None:
    if "idempotencyKey" in payload:
        raise GatewayError("one_step_idempotency_not_supported", 422)
