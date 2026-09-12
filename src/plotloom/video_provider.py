"""Strict Atlas Wan boundary used by P2, with no compatibility guessing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class VideoProviderError(RuntimeError):
    pass


class RemotePredictionFailed(VideoProviderError):
    """The provider explicitly reported a known prediction terminal failure."""


@dataclass(frozen=True)
class WanCapabilities:
    provider: str = "atlascloud"
    model: str = "alibaba/wan-3.0/image-to-video"
    request_image_field: str = "image"
    durations: tuple[int, ...] = (5,)
    resolutions: tuple[str, ...] = ("720p",)
    native_audio: bool = True
    request_version: int = 1


WAN_3_IMAGE_TO_VIDEO = WanCapabilities()


class VideoProviderPort(Protocol):
    def upload(self, image: bytes, *, mime_type: str) -> str: ...
    def submit(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def poll(self, prediction_id: str) -> dict[str, Any]: ...
    def download(self, url: str) -> bytes: ...


class AtlasWanAdapter:
    """Compile only fields documented for Wan 3 image-to-video.

    The documented generic and model response envelopes disagree.  Rather
    than recursively scanning arbitrary JSON, this adapter accepts only the
    two explicitly evidenced envelopes.  A real observed response can extend
    this narrow parser in a later, reviewed change.
    """

    capabilities = WAN_3_IMAGE_TO_VIDEO

    def compile(self, *, prompt: str, image_url: str, duration: int, resolution: str, audio: bool) -> dict[str, Any]:
        caps = self.capabilities
        if duration not in caps.durations or resolution not in caps.resolutions or audio is not True:
            raise VideoProviderError("Wan P2 capability mismatch")
        if not image_url.startswith("https://"):
            raise VideoProviderError("uploaded image URL must be HTTPS")
        return {"model": caps.model, "prompt": prompt, "image": image_url, "duration": duration, "resolution": resolution, "audio": True}

    @staticmethod
    def prediction_id(payload: dict[str, Any]) -> str:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        value = data.get("id") if isinstance(data, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise VideoProviderError("Atlas response has no documented prediction id")
        return value

    @staticmethod
    def completed_output(payload: dict[str, Any]) -> str | None:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if not isinstance(data, dict):
            raise VideoProviderError("Atlas prediction response is not a documented object")
        status = data.get("status")
        if not isinstance(status, str):
            raise VideoProviderError("Atlas prediction response has no documented status")
        if status in {"failed", "error", "cancelled", "canceled"}:
            raise RemotePredictionFailed("Atlas prediction reported failure")
        if status not in {"completed", "succeeded", "success"}:
            return None
        outputs = data.get("outputs")
        if not isinstance(outputs, list) or len(outputs) != 1 or not isinstance(outputs[0], str):
            raise VideoProviderError("completed Atlas prediction has no single documented output URL")
        return outputs[0]
