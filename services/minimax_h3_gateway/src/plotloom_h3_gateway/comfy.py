"""Narrow ComfyUI transport used by the trusted H3 gateway worker."""
from __future__ import annotations

from typing import Any

import requests

from .contracts import GatewayError, GatewaySettings
from .profile_catalog import TURBO_4STEP_LORA


class ComfyClient:
    """Own transport, readiness and profile checks; never accepts arbitrary graphs."""

    def __init__(self, settings: GatewaySettings, session: requests.Session | Any) -> None:
        self.settings = settings
        self.session = session

    def queue_depth(self) -> int:
        payload = self._get_json("/queue", code="comfy_unavailable")
        if not isinstance(payload, dict):
            raise GatewayError("comfy_queue_invalid", 503)
        active = payload.get("queue_running", [])
        pending = payload.get("queue_pending", [])
        if not isinstance(active, list) or not isinstance(pending, list):
            raise GatewayError("comfy_queue_invalid", 503)
        return len(active) + len(pending)

    def preflight(self) -> None:
        self._get_json("/system_stats", code="comfy_unavailable")
        object_info = self._get_json("/object_info", code="comfy_profile_unavailable")
        required = (
            ("UNETLoader", "unet_name", "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"),
            ("CLIPLoader", "clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
            ("VAELoader", "vae_name", "minimax_h3_video_vae_fp16.safetensors"),
            ("VAELoader", "vae_name", "minimax_h3_audio_vae_fp32.safetensors"),
            ("LoraLoaderModelOnly", "lora_name", TURBO_4STEP_LORA),
        )
        for node_type, input_name, expected in required:
            try:
                options = object_info[node_type]["input"]["required"][input_name][0]
            except (KeyError, IndexError, TypeError) as error:
                raise GatewayError("comfy_profile_unavailable", 503) from error
            if not isinstance(options, list) or expected not in options:
                raise GatewayError("comfy_profile_unavailable", 503)
        if "MiniMaxH3ImageToVideo" not in object_info or "PrimitiveInt" not in object_info:
            raise GatewayError("comfy_profile_unavailable", 503)

    def submit(self, *, workflow: dict[str, Any], client_id: str) -> str:
        try:
            response = self.session.post(
                f"{self.settings.comfy_url}/prompt",
                json={"prompt": workflow, "client_id": client_id},
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            raise GatewayError("submit_outcome_unknown") from error
        prompt_id = payload.get("prompt_id") if isinstance(payload, dict) else None
        if not isinstance(prompt_id, str) or not prompt_id:
            raise GatewayError("submit_response_invalid")
        return prompt_id

    def history(self, prompt_id: str | None) -> object | None:
        try:
            response = self.session.get(
                f"{self.settings.comfy_url}/history/{prompt_id}",
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            return None

    def _get_json(self, path: str, *, code: str) -> object:
        try:
            response = self.session.get(f"{self.settings.comfy_url}{path}", timeout=5)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            raise GatewayError(code, 503) from error
