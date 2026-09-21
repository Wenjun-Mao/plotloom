"""Narrow local SGLang transport for Qwen-Image-2.1.

The public gateway owns admission, serialization, and files.  This module
only speaks the documented loopback SGLang image API and deliberately does
not expose arbitrary model/request controls.
"""
from __future__ import annotations

import base64
from typing import Any

import requests

from .contracts import (
    QWEN_IMAGE_GUIDANCE_SCALE,
    QWEN_IMAGE_STEPS,
    GatewayError,
    GatewaySettings,
)


class QwenImageClient:
    """Call the local, private Qwen image service with one output only."""

    def __init__(self, settings: GatewaySettings, session: requests.Session | Any) -> None:
        self.settings = settings
        self.session = session

    def preflight(self) -> None:
        """Require the private service to answer before a job claims the lane."""

        try:
            response = self.session.get(
                f"{self.settings.qwen_image_url}/health",
                timeout=5,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise GatewayError("qwen_image_unavailable", 503) from error

    def generate(
        self, *, prompt: str, width: int, height: int, seed: int, background_mode: str
    ) -> bytes:
        payload = self._base_payload(
            prompt=prompt, width=width, height=height, seed=seed, background_mode=background_mode
        )
        payload["enable_cache_dit"] = False
        return self._post_json("/v1/images/generations", payload)

    def edit(
        self, *, prompt: str, width: int, height: int, seed: int, background_mode: str,
        source_name: str, source_content: bytes,
    ) -> bytes:
        fields = {
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in self._base_payload(
                prompt=prompt, width=width, height=height, seed=seed,
                background_mode=background_mode,
            ).items()
        }
        try:
            response = self.session.post(
                f"{self.settings.qwen_image_url}/v1/images/edits",
                data=fields,
                files={"image[]": (source_name, source_content, "image/png")},
                timeout=self.settings.qwen_image_request_timeout_seconds,
            )
        except requests.RequestException as error:
            raise GatewayError("qwen_image_submit_outcome_unknown") from error
        return self._decode_response(response)

    def _base_payload(
        self, *, prompt: str, width: int, height: int, seed: int, background_mode: str
    ) -> dict[str, Any]:
        return {
            "model": self.settings.qwen_image_model,
            "prompt": prompt,
            "n": 1,
            "size": f"{width}x{height}",
            "num_inference_steps": QWEN_IMAGE_STEPS,
            "guidance_scale": QWEN_IMAGE_GUIDANCE_SCALE,
            "seed": seed,
            "generator_device": "cpu",
            "output_format": "png",
            "response_format": "b64_json",
            "background": "transparent" if background_mode == "transparent" else "auto",
        }

    def _post_json(self, path: str, payload: dict[str, Any]) -> bytes:
        try:
            response = self.session.post(
                f"{self.settings.qwen_image_url}{path}",
                json=payload,
                timeout=self.settings.qwen_image_request_timeout_seconds,
            )
        except requests.RequestException as error:
            raise GatewayError("qwen_image_submit_outcome_unknown") from error
        return self._decode_response(response)

    @staticmethod
    def _decode_response(response: Any) -> bytes:
        try:
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise GatewayError("qwen_image_generation_failed") from error
        if not isinstance(payload, dict) or set(payload) != {
            "id", "created", "data", "peak_memory_mb", "inference_time_s", "usage"
        }:
            raise GatewayError("qwen_image_response_invalid")
        if not isinstance(payload["id"], str) or not payload["id"]:
            raise GatewayError("qwen_image_response_invalid")
        if isinstance(payload["created"], bool) or not isinstance(payload["created"], int):
            raise GatewayError("qwen_image_response_invalid")
        for field in ("peak_memory_mb", "inference_time_s"):
            value = payload[field]
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise GatewayError("qwen_image_response_invalid")
        usage = payload["usage"]
        if usage is not None and not isinstance(usage, dict):
            raise GatewayError("qwen_image_response_invalid")
        entries = payload.get("data")
        if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
            raise GatewayError("qwen_image_response_invalid")
        entry = entries[0]
        if set(entry) != {"b64_json", "url", "revised_prompt", "file_path", "resize"}:
            raise GatewayError("qwen_image_response_invalid")
        encoded = entry["b64_json"]
        if not isinstance(encoded, str) or not encoded or entry["url"] is not None:
            raise GatewayError("qwen_image_response_invalid")
        for field in ("revised_prompt", "file_path", "resize"):
            if entry[field] is not None and not isinstance(entry[field], str):
                raise GatewayError("qwen_image_response_invalid")
        try:
            return base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as error:
            raise GatewayError("qwen_image_response_invalid") from error
