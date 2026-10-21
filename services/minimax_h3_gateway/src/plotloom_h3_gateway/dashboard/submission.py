"""Bounded single-shot forwarding; the gateway remains the only admission owner."""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests
from pydantic import ValidationError
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.requests import Request

from ..contracts import (
    MAX_UPLOAD_BYTES,
    CreateImageJobFromSourceUrlRequest,
    CreateImageJobRequest,
)
from ..profile_catalog import admitted_execution

GATEWAY_IMAGE_URL = "http://100.64.35.71:8090/v1/video-jobs/from-image"
MAX_BODY = 2 * MAX_UPLOAD_BYTES + 65536
UNKNOWN = "submission_outcome_unknown"
REJECTIONS = {
    "source_url_invalid", "source_url_fetch_failed", "source_url_too_large", "source_url_empty",
    "request_invalid", "image_file_required", "image_size_invalid", "image_decode_invalid",
    "image_pixels_exceed_limit", "unsupported_image_format", "input_aspect_mismatch",
    "input_prepare_failed", "quality_not_supported", "resolution_not_supported",
}


class SubmissionError(Exception):
    def __init__(self, code, status=422):
        self.code, self.status = code, status


async def validated_body(request: Request) -> tuple[bytes, str]:
    media_type = request.headers.get("content-type", "")
    kind = media_type.partition(";")[0].strip().lower()
    if kind not in {"application/json", "multipart/form-data"}:
        raise SubmissionError("request_media_type_not_supported", 415)
    limit = 131072 if kind == "application/json" else MAX_BODY
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            raise SubmissionError("request_too_large", 413)
        body.extend(chunk)
    raw = bytes(body)
    try:
        if kind == "application/json":
            fields = json.loads(raw)
            model = CreateImageJobFromSourceUrlRequest.model_validate(fields)
        else:
            async def receive():
                return {"type": "http.request", "body": raw, "more_body": False}

            parsed = Request(request.scope, receive)
            async with parsed.form(max_files=2, max_fields=6, max_part_size=32768) as form:
                allowed = {"image", "endImage", "prompt", "quality", "resolution",
                           "durationSeconds", "seed", "aspectPolicy"}
                if set(form) - allowed or any(len(form.getlist(k)) != 1 for k in form):
                    raise SubmissionError("request_fields_invalid")
                if not isinstance(form.get("image"), UploadFile):
                    raise SubmissionError("image_file_required")
                for key in ("image", "endImage"):
                    if key not in form:
                        continue
                    file = form[key]
                    if not isinstance(file, UploadFile) or not file.size or file.size > MAX_UPLOAD_BYTES:
                        raise SubmissionError("image_file_invalid")
                fields = {k: v for k, v in form.items() if k not in {"image", "endImage"}}
                model = CreateImageJobRequest.model_validate(fields)
        admitted_execution(quality=model.quality, resolution=model.resolution)
    except (ValueError, TypeError, KeyError, ValidationError, HTTPException):
        raise SubmissionError("request_invalid") from None
    return raw, media_type


class GatewaySubmission:
    def __init__(self, key: str, *, session=None):
        self.key = key
        self.session = session or requests.Session()
        self.session.trust_env = False

    @classmethod
    def from_key_file(cls, path: str | None):
        if not path:
            return None
        key = Path(path).read_text().strip()
        if not key or "\n" in key or "\r" in key:
            raise RuntimeError("invalid dashboard gateway key file")
        return cls(key)

    def submit(self, raw: bytes, media_type: str) -> dict:
        # No retries: gateway admission may already have committed on any lost reply.
        try:
            with self.session.post(
                GATEWAY_IMAGE_URL, data=raw,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": media_type},
                timeout=(5, 90), allow_redirects=False, stream=True,
            ) as response:
                body = bytearray()
                for chunk in response.iter_content(8192):
                    if len(body) + len(chunk) > 65536:
                        raise SubmissionError(UNKNOWN, 502)
                    body.extend(chunk)
                try:
                    value = json.loads(body)
                except (ValueError, TypeError):
                    raise SubmissionError(UNKNOWN, 502) from None
                if not isinstance(value, dict):
                    raise SubmissionError(UNKNOWN, 502)
                if 400 <= response.status_code < 500:
                    code = value.get("error")
                    if response.status_code in {401, 403}:
                        raise SubmissionError("gateway_submission_unauthorized", 503)
                    if isinstance(code, str) and code in REJECTIONS:
                        raise SubmissionError(code, response.status_code)
                    raise SubmissionError("gateway_request_rejected", 422)
                if response.status_code != 202 or not re.fullmatch(r"h3_[0-9a-f]{32}", str(value.get("id"))):
                    raise SubmissionError(UNKNOWN, 502)
                # Never forward upstream bodies, headers or credentials to the browser.
                return {"id": value["id"], "status": "accepted"}
        except requests.RequestException:
            raise SubmissionError(UNKNOWN, 502) from None
