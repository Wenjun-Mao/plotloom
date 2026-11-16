"""Authenticated ordered-reference request parsing and typed public admission."""
from __future__ import annotations

import json
from typing import Any

from fastapi import Depends, Request
from pydantic import ValidationError

from .contracts import GatewayError
from .reference_audio_contracts import REFERENCE_MAX_AUDIOS
from .voice_reference import MAX_VOICE_BYTES
from .reference_contracts import (
    REFERENCE_MAX_BYTES, REFERENCE_MAX_IMAGES,
    CreateReferenceJobFromUrlsRequest, CreateReferenceJobRequest,
)


def unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def parse_reference_request(content: bytes | str, *, urls: bool = False):
    try:
        if len(content) > 65_536:
            raise ValueError("request metadata too large")
        payload = json.loads(content, object_pairs_hook=unique_json_object)
        model = CreateReferenceJobFromUrlsRequest if urls else CreateReferenceJobRequest
        return model.model_validate(payload)
    except (ValueError, UnicodeDecodeError, ValidationError):
        raise GatewayError("reference_request_invalid", 422) from None


def install_reference_api(app, gateway, authorize, job_response) -> None:
    @app.post("/v1/video-jobs/from-reference-images", dependencies=[Depends(authorize)], status_code=202)
    async def create_reference_job(request: Request) -> dict[str, Any]:
        media_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
        contents, audios = [], []
        if media_type == "application/json":
            source_request = parse_reference_request(await request.body(), urls=True)
            for reference in source_request.references:
                remaining = REFERENCE_MAX_BYTES - sum(map(len, contents))
                if remaining <= 0:
                    raise GatewayError("reference_images_size_invalid", 413)
                contents.append(gateway.source_images.fetch(reference.source_url, max_bytes=remaining))
            for audio in source_request.audio_references:
                audios.append(gateway.source_images.fetch(audio.source_url,
                    max_bytes=MAX_VOICE_BYTES, empty_code="voice_size_invalid"))
        elif media_type == "multipart/form-data":
            async with request.form(max_files=REFERENCE_MAX_IMAGES + REFERENCE_MAX_AUDIOS,
                                    max_fields=1, max_part_size=65_536) as form:
                if set(form) not in ({"request", "images"}, {"request", "images", "audios"}) or len(form.getlist("request")) != 1:
                    raise GatewayError("reference_request_fields_invalid", 422)
                metadata = form.get("request")
                if not isinstance(metadata, str):
                    raise GatewayError("reference_request_invalid", 422)
                source_request = parse_reference_request(metadata)
                images = form.getlist("images")
                audio_files = form.getlist("audios")
                if len(images) != len(source_request.references):
                    raise GatewayError("reference_image_count_mismatch", 422)
                if len(audio_files) != len(source_request.audio_references):
                    raise GatewayError("reference_audio_count_mismatch", 422)
                for image in images:
                    if not callable(getattr(image, "read", None)):
                        raise GatewayError("reference_image_file_required", 422)
                    remaining = REFERENCE_MAX_BYTES - sum(map(len, contents))
                    content = await image.read(remaining + 1)
                    if len(content) > remaining:
                        raise GatewayError("reference_images_size_invalid", 413)
                    contents.append(content)
                for audio in audio_files:
                    if not callable(getattr(audio, "read", None)):
                        raise GatewayError("reference_audio_file_required", 422)
                    audios.append(await audio.read(MAX_VOICE_BYTES + 1))
        else:
            raise GatewayError("request_media_type_not_supported", 415)
        job = gateway.reference_jobs.create(source_request, contents, audios)
        return job_response(gateway, job)
