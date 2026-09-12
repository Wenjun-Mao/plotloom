"""Strict Atlas Wan boundary used by P2, with no compatibility guessing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, Protocol


class VideoProviderError(RuntimeError):
    pass


DispatchPhase = Literal["keyframe_read", "upload", "request_compile", "submit", "submit_response_parse", "poll"]
DispatchCode = Literal[
    "transport_unavailable",
    "http_rejected",
    "invalid_json",
    "invalid_envelope",
    "invalid_upload_url",
    "local_precondition_failed",
]


@dataclass(frozen=True)
class WanDispatchDiagnostic:
    """Allowlisted evidence for a claimed dispatch that cannot reveal provider data."""

    phase: DispatchPhase
    code: DispatchCode
    status_code: int | None = None

    _phases: ClassVar[frozenset[str]] = frozenset({
        "keyframe_read", "upload", "request_compile", "submit", "submit_response_parse", "poll",
    })
    _codes: ClassVar[frozenset[str]] = frozenset({
        "transport_unavailable", "http_rejected", "invalid_json", "invalid_envelope",
        "invalid_upload_url", "local_precondition_failed",
    })

    def __post_init__(self) -> None:
        # These values are persisted after a claimed remote dispatch. Runtime
        # validation, rather than type annotations alone, keeps that boundary
        # closed to response text, signed URLs, and unexpected exception data.
        if self.phase not in self._phases:
            raise ValueError("dispatch phase is not allowlisted")
        if self.code not in self._codes:
            raise ValueError("dispatch code is not allowlisted")
        if self.status_code is not None and (type(self.status_code) is not int or not 100 <= self.status_code <= 599):
            raise ValueError("dispatch HTTP status must be an HTTP status code")

    @property
    def outcome_error(self) -> str:
        """Stable persistence code; deliberately excludes exception text and URLs."""

        status = f"_status_{self.status_code}" if self.status_code is not None else ""
        return f"dispatch_{self.phase}_{self.code}{status}"


class WanDispatchError(VideoProviderError):
    """A safe dispatch diagnosis suitable for the durable unknown-outcome record."""

    def __init__(self, diagnostic: WanDispatchDiagnostic) -> None:
        self.diagnostic = diagnostic
        super().__init__(diagnostic.outcome_error)


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
