"""FastAPI presentation layer for the trusted direct H3 gateway contract."""
from __future__ import annotations

import hmac
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

from .contracts import (
    CreateImageJobFromSourceUrlRequest,
    CreateImageJobRequest,
    CreateQwenEditImageJobFromSourceUrlRequest,
    CreateQwenEditImageJobRequest,
    CreateQwenTextImageJobRequest,
    CreateTextJobRequest,
    GatewayError,
    GatewaySettings,
    MAX_UPLOAD_BYTES,
)
from .gateway import H3Gateway
from .worker import GatewayDispatchWorker


def create_app(
    settings: GatewaySettings | None = None, *, session: requests.Session | Any | None = None,
    source_session: requests.Session | Any | None = None,
    qwen_session: requests.Session | Any | None = None,
) -> FastAPI:
    """Create the authenticated HTTP boundary around one durable gateway."""

    gateway = H3Gateway(
        settings or GatewaySettings.from_environment(), session=session,
        source_session=source_session, qwen_session=qwen_session,
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

    app = FastAPI(title="Plotloom generation gateway", version="7.0", lifespan=lifespan)
    app.state.gateway = gateway

    def authorize(authorization: str | None = Header(default=None)) -> None:
        expected = f"Bearer {gateway.settings.api_key}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.exception_handler(GatewayError)
    async def handle_gateway_error(_: Any, error: GatewayError) -> Response:
        return Response(content=json.dumps({"error": error.code}), status_code=error.status_code, media_type="application/json")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return gateway.health()

    @app.post("/v1/video-jobs/from-image", dependencies=[Depends(authorize)], status_code=202)
    async def create_video_job_from_image(request: Request) -> dict[str, Any]:
        start_content, end_content, job_request = await _image_submission(request, gateway)
        return _job_response(gateway, gateway.create_image_job(job_request, start_content=start_content, end_content=end_content))

    @app.post("/v1/video-jobs/from-text", dependencies=[Depends(authorize)], status_code=202)
    async def create_video_job_from_text(request: Request) -> dict[str, Any]:
        if _request_media_type(request) != "application/json":
            raise GatewayError("request_media_type_not_supported", 415)
        job_request = _validated_model(CreateTextJobRequest, await _json_object(request))
        return _job_response(gateway, gateway.create_text_job(job_request))

    @app.get("/v1/video-jobs/{job_id}", dependencies=[Depends(authorize)])
    def get_video_job(job_id: str) -> dict[str, Any]:
        job = gateway.refresh_job(job_id)
        _require_backend(job, "h3_video")
        return _job_response(gateway, job)

    @app.post("/v1/video-jobs/{job_id}/cancel", dependencies=[Depends(authorize)])
    def cancel_video_job(job_id: str) -> dict[str, Any]:
        job = gateway.store.get_job(job_id)
        _require_backend(job, "h3_video")
        return _job_response(gateway, gateway.cancel_job(job_id))

    @app.get("/v1/video-jobs/{job_id}/output", dependencies=[Depends(authorize)])
    def get_output(job_id: str) -> Response:
        _require_backend(gateway.store.get_job(job_id), "h3_video")
        return Response(content=gateway.read_output(job_id), media_type="video/mp4")

    @app.post("/v1/image-jobs/from-text", dependencies=[Depends(authorize)], status_code=202)
    async def create_image_job_from_text(request: Request) -> dict[str, Any]:
        if _request_media_type(request) != "application/json":
            raise GatewayError("request_media_type_not_supported", 415)
        job_request = _validated_model(CreateQwenTextImageJobRequest, await _json_object(request))
        return _job_response(gateway, gateway.create_qwen_text_image_job(job_request))

    @app.post("/v1/image-jobs/from-image", dependencies=[Depends(authorize)], status_code=202)
    async def create_image_job_from_image(request: Request) -> dict[str, Any]:
        source_content, job_request = await _qwen_image_submission(request, gateway)
        return _job_response(
            gateway, gateway.create_qwen_edit_image_job(job_request, source_content=source_content)
        )

    @app.get("/v1/image-jobs/{job_id}", dependencies=[Depends(authorize)])
    def get_image_job(job_id: str) -> dict[str, Any]:
        job = gateway.refresh_job(job_id)
        _require_backend(job, "qwen_image")
        return _job_response(gateway, job)

    @app.post("/v1/image-jobs/{job_id}/cancel", dependencies=[Depends(authorize)])
    def cancel_image_job(job_id: str) -> dict[str, Any]:
        job = gateway.store.get_job(job_id)
        _require_backend(job, "qwen_image")
        return _job_response(gateway, gateway.cancel_job(job_id))

    @app.get("/v1/image-jobs/{job_id}/output", dependencies=[Depends(authorize)])
    def get_image_output(job_id: str) -> Response:
        job = gateway.store.get_job(job_id)
        _require_backend(job, "qwen_image")
        return Response(content=gateway.read_output(job_id), media_type="image/png")

    return app


def _job_response(gateway: H3Gateway, job: dict[str, Any]) -> dict[str, Any]:
    submitted = _iso_timestamp(job.get("generation_submitted_at_ms"))
    completed = _iso_timestamp(job.get("generation_completed_at_ms"))
    elapsed: int | None = None
    if isinstance(job.get("generation_submitted_at_ms"), int):
        end = job.get("generation_completed_at_ms")
        elapsed = (int(end) if isinstance(end, int) else _now_ms()) - int(job["generation_submitted_at_ms"])
    common = {
        "id": job["id"], "status": job["status"], "inputMode": job["input_mode"],
        "generationSubmittedAt": submitted, "generationCompletedAt": completed,
        "generationElapsedMs": elapsed, "error": job["error_code"],
        "outputReady": gateway.output_is_ready(job),
    }
    if job.get("backend", "h3_video") == "qwen_image":
        return {
            **common, "resolution": job["resolution"], "backgroundMode": job["background_mode"],
            "seed": job["seed"], "outputContentType": job["output_mime_type"],
            "outputWidth": job["output_width"], "outputHeight": job["output_height"],
        }
    return {
        **common, "quality": job["quality"], "resolution": job["resolution"],
        "aspectPolicy": job["aspect_policy"], "seed": job["seed"],
        "requestedDurationSeconds": job["requested_duration_seconds"], "frameCount": job["frame_count"],
        "actualDurationSeconds": job["frame_count"] / job["fps"],
    }


def _require_backend(job: dict[str, Any], backend: str) -> None:
    if job.get("backend", "h3_video") != backend:
        raise GatewayError("job_not_found", 404)


async def _image_submission(request: Request, gateway: H3Gateway) -> tuple[bytes, bytes | None, CreateImageJobRequest]:
    media_type = _request_media_type(request)
    if media_type == "multipart/form-data":
        start, end, fields = await _read_multipart_images(request)
        job_request = _validated_model(CreateImageJobRequest, fields)
        gateway.validate_image_job_request(job_request)
        return start, end, job_request
    if media_type == "application/json":
        source_request = _validated_model(CreateImageJobFromSourceUrlRequest, await _json_object(request))
        gateway.validate_image_job_request(source_request)
        start = gateway.source_images.fetch(source_request.source_url)
        end = gateway.source_images.fetch(source_request.end_source_url) if source_request.end_source_url else None
        return start, end, source_request
    raise GatewayError("request_media_type_not_supported", 415)


async def _qwen_image_submission(
    request: Request, gateway: H3Gateway
) -> tuple[bytes, CreateQwenEditImageJobRequest]:
    media_type = _request_media_type(request)
    if media_type == "multipart/form-data":
        image, fields = await _read_qwen_multipart_image(request)
        return image, _validated_model(CreateQwenEditImageJobRequest, fields)
    if media_type == "application/json":
        source_request = _validated_model(
            CreateQwenEditImageJobFromSourceUrlRequest, await _json_object(request)
        )
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


async def _read_multipart_images(request: Request) -> tuple[bytes, bytes | None, dict[str, Any]]:
    form = await request.form()
    allowed = {"image", "endImage", "prompt", "aspectPolicy", "quality", "resolution", "seed", "durationSeconds"}
    received = set(form.keys())
    if received - allowed or any(len(form.getlist(field)) != 1 for field in received):
        raise GatewayError("request_fields_invalid", 422)
    image = form.get("image")
    if image is None or not callable(getattr(image, "read", None)):
        raise GatewayError("image_file_required", 422)
    end_image = form.get("endImage")
    if end_image is not None and not callable(getattr(end_image, "read", None)):
        raise GatewayError("end_image_file_invalid", 422)
    start = await image.read(MAX_UPLOAD_BYTES + 1)
    end = await end_image.read(MAX_UPLOAD_BYTES + 1) if end_image is not None else None
    fields = {field: form.get(field) for field in received if field not in {"image", "endImage"}}
    return start, end, fields


async def _read_qwen_multipart_image(request: Request) -> tuple[bytes, dict[str, Any]]:
    form = await request.form()
    allowed = {"image", "prompt", "resolution", "seed", "backgroundMode"}
    received = set(form.keys())
    if received - allowed or any(len(form.getlist(field)) != 1 for field in received):
        raise GatewayError("request_fields_invalid", 422)
    image = form.get("image")
    if image is None or not callable(getattr(image, "read", None)):
        raise GatewayError("image_file_required", 422)
    content = await image.read(MAX_UPLOAD_BYTES + 1)
    return content, {field: form.get(field) for field in received if field != "image"}


def _validated_model(model: type[BaseModel], payload: dict[str, Any]) -> Any:
    try:
        return model.model_validate(payload)
    except ValidationError as error:
        fields = {str(item) for issue in error.errors() for item in issue["loc"]}
        if "sourceUrl" in fields or "source_url" in fields or "endSourceUrl" in fields or "end_source_url" in fields:
            raise GatewayError("source_url_invalid", 422) from error
        raise GatewayError("request_invalid", 422) from error


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _iso_timestamp(value: object) -> str | None:
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
