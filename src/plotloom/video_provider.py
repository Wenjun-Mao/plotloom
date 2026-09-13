"""Versioned video-adapter contracts used by P2 production jobs.

The Atlas and H3 adapters deliberately share only the small production
boundary below.  A provider name or model string never selects a permissive
compatibility path.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, ClassVar, Literal, Protocol

from .video_ingestion import ObservedVideo


class VideoProviderError(RuntimeError):
    pass


class VideoOutputContractError(VideoProviderError):
    """A downloaded known job does not satisfy its frozen output profile."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


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


class RemoteOutcomeUnknown(VideoProviderError):
    """A gateway knows its local job but cannot establish provider submission."""


@dataclass(frozen=True)
class VideoProductionContract:
    """Trusted adapter-owned values frozen into a new video snapshot.

    This is intentionally not a browser request model.  An adapter normalises
    and validates it before the repository enters the durable dispatch path.
    """

    adapter_id: str
    adapter_version: str
    provider: str
    model: str
    capability_version: int
    requested_seconds: int
    resolution: str
    audio: bool
    aspect_policy: str | None
    seed: int | None
    tracks_paid_wan_pilot: bool

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", self.adapter_id):
            raise ValueError("video adapter ID is invalid")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,62}", self.adapter_version):
            raise ValueError("video adapter version is invalid")
        if not self.provider or not self.model or self.capability_version < 1:
            raise ValueError("video production capability is invalid")
        if self.requested_seconds < 1 or self.requested_seconds > 30:
            raise ValueError("video duration is invalid")
        if not self.resolution:
            raise ValueError("video resolution is required")
        if self.seed is not None and not 0 <= self.seed <= 2**63 - 1:
            raise ValueError("video seed is invalid")

    def provider_snapshot(self) -> dict[str, Any]:
        return {
            "adapterId": self.adapter_id,
            "adapterVersion": self.adapter_version,
            "provider": self.provider,
            "model": self.model,
            "capabilityVersion": self.capability_version,
            "costPolicy": "wan_paid_pilot_v1" if self.tracks_paid_wan_pilot else "local_capacity_v1",
        }

    def request_snapshot(self) -> dict[str, Any]:
        request: dict[str, Any] = {
            "durationSeconds": self.requested_seconds,
            "resolution": self.resolution,
            "audio": self.audio,
        }
        if self.aspect_policy is not None:
            request["aspectPolicy"] = self.aspect_policy
        if self.seed is not None:
            request["seed"] = self.seed
        return request


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


@dataclass(frozen=True)
class H3Capabilities:
    provider: str = "minimax_h3_gateway"
    model: str = "minimax_h3_fp8_turbo4_480p"
    adapter_id: str = "minimax_h3_gateway"
    adapter_version: str = "1"
    duration_seconds: int = 5
    resolution: str = "480p"
    width: int = 864
    height: int = 480
    fps: int = 24
    frame_count: int = 124
    native_audio: bool = True
    capability_version: int = 1


MINIMAX_H3_480P = H3Capabilities()


class VideoProviderPort(Protocol):
    def upload(self, image: bytes, *, mime_type: str) -> str: ...
    def submit(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def poll(self, prediction_id: str) -> dict[str, Any]: ...
    def download(self, url: str) -> bytes: ...


class VideoAdapterPort(Protocol):
    """Strict adapter behaviour consumed by ``VideoJobService``."""

    def compile(
        self,
        *,
        prompt: str,
        uploaded_asset: str,
        duration: int,
        resolution: str,
        audio: bool,
        aspect_policy: str | None,
        seed: int | None,
    ) -> dict[str, Any]: ...

    def prediction_id(self, payload: dict[str, Any]) -> str: ...

    def completed_output(self, payload: dict[str, Any]) -> str | None: ...

    def validate_output_reference(self, value: str) -> None: ...

    def validate_observed_output(self, observed: ObservedVideo) -> None: ...


class AtlasWanAdapter:
    """Compile only fields documented for Wan 3 image-to-video.

    The documented generic and model response envelopes disagree.  Rather
    than recursively scanning arbitrary JSON, this adapter accepts only the
    two explicitly evidenced envelopes.  A real observed response can extend
    this narrow parser in a later, reviewed change.
    """

    capabilities = WAN_3_IMAGE_TO_VIDEO

    adapter_id = "atlas_wan"
    adapter_version = "1"

    def compile(
        self,
        *,
        prompt: str,
        uploaded_asset: str,
        duration: int,
        resolution: str,
        audio: bool,
        aspect_policy: str | None = None,
        seed: int | None = None,
    ) -> dict[str, Any]:
        caps = self.capabilities
        if duration not in caps.durations or resolution not in caps.resolutions or audio is not True:
            raise VideoProviderError("Wan P2 capability mismatch")
        if aspect_policy is not None or seed is not None:
            raise VideoProviderError("Wan P2 request includes unsupported H3 fields")
        if not uploaded_asset.startswith("https://"):
            raise VideoProviderError("uploaded image URL must be HTTPS")
        return {"model": caps.model, "prompt": prompt, "image": uploaded_asset, "duration": duration, "resolution": resolution, "audio": True}

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

    @staticmethod
    def validate_output_reference(value: str) -> None:
        # Keep the existing public-download boundary in ``VideoJobService`` so
        # it remains visibly adjacent to media ingestion rather than hiding it
        # in a general parser.
        if not value.startswith("https://"):
            raise VideoProviderError("Atlas output must be an HTTPS URL")

    @staticmethod
    def validate_observed_output(_observed: ObservedVideo) -> None:
        # Browser-playability and native-audio checks remain shared ingestion
        # requirements. Atlas has no separately evidenced fixed frame profile.
        return None


class MiniMaxH3GatewayAdapter:
    """Compile and parse only the private gateway's version-one contract."""

    capabilities = MINIMAX_H3_480P
    _JOB_ID = re.compile(r"^h3_[0-9a-f]{32}$")
    _ASPECT_POLICIES = frozenset({"cover_center_crop", "contain_pad", "reject_mismatch"})

    def production_contract(
        self,
        *,
        requested_seconds: int | None,
        resolution: str | None,
        audio: bool | None,
        aspect_policy: str | None,
        seed: int | None,
    ) -> VideoProductionContract:
        caps = self.capabilities
        if requested_seconds not in {None, caps.duration_seconds}:
            raise VideoProviderError("H3 duration capability mismatch")
        if resolution not in {None, caps.resolution}:
            raise VideoProviderError("H3 resolution capability mismatch")
        if audio not in {None, True}:
            raise VideoProviderError("H3 native audio is required")
        if aspect_policy not in self._ASPECT_POLICIES:
            raise VideoProviderError("H3 requires an explicit input aspect policy")
        if seed is None:
            raise VideoProviderError("H3 requires a frozen seed")
        return VideoProductionContract(
            adapter_id=caps.adapter_id,
            adapter_version=caps.adapter_version,
            provider=caps.provider,
            model=caps.model,
            capability_version=caps.capability_version,
            requested_seconds=caps.duration_seconds,
            resolution=caps.resolution,
            audio=True,
            aspect_policy=aspect_policy,
            seed=seed,
            tracks_paid_wan_pilot=False,
        )

    def compile(
        self,
        *,
        prompt: str,
        uploaded_asset: str,
        duration: int,
        resolution: str,
        audio: bool,
        aspect_policy: str | None,
        seed: int | None,
    ) -> dict[str, Any]:
        contract = self.production_contract(
            requested_seconds=duration,
            resolution=resolution,
            audio=audio,
            aspect_policy=aspect_policy,
            seed=seed,
        )
        if not uploaded_asset.startswith("asset_"):
            raise VideoProviderError("H3 upload response has no asset ID")
        return {
            "assetId": uploaded_asset,
            "prompt": prompt,
            "profileId": contract.model,
            "aspectPolicy": contract.aspect_policy,
            "seed": contract.seed,
        }

    @classmethod
    def prediction_id(cls, payload: dict[str, Any]) -> str:
        value = payload.get("id")
        if not isinstance(value, str) or not cls._JOB_ID.fullmatch(value):
            raise VideoProviderError("H3 response has no documented job ID")
        return value

    @classmethod
    def completed_output(cls, payload: dict[str, Any]) -> str | None:
        job_id = cls.prediction_id(payload)
        status = payload.get("status")
        if not isinstance(status, str):
            raise VideoProviderError("H3 job response has no documented status")
        if status in {"failed", "cancelled"}:
            raise RemotePredictionFailed("H3 gateway reported terminal failure")
        if status == "outcome_unknown":
            raise RemoteOutcomeUnknown("H3 gateway cannot establish Comfy submission outcome")
        if status in {"reserved", "submitted", "running"}:
            return None
        if status != "succeeded" or payload.get("outputReady") is not True:
            raise VideoProviderError("H3 completed response is invalid")
        return job_id

    @classmethod
    def validate_output_reference(cls, value: str) -> None:
        if not cls._JOB_ID.fullmatch(value):
            raise VideoProviderError("H3 output reference is not a gateway job ID")

    def validate_observed_output(self, observed: ObservedVideo) -> None:
        """Fail closed if the gateway did not deliver its frozen H3 profile.

        The workbench advertises a 124-frame, 24-fps, 864x480 H3 candidate.
        Accepting a merely playable but differently shaped file would make that
        provenance claim false and can reintroduce the visual stretching this
        profile's explicit aspect policy was created to avoid.
        """

        caps = self.capabilities
        expected_duration = caps.frame_count / caps.fps
        if (
            (observed.width, observed.height) != (caps.width, caps.height)
            or observed.video_codec != "h264"
            or observed.audio_codec != "aac"
            or observed.frame_rate is None
            or abs(observed.frame_rate - caps.fps) > 0.01
            or observed.frame_count != caps.frame_count
            or abs(observed.duration_seconds - expected_duration) > (1 / caps.fps)
        ):
            raise VideoOutputContractError("h3_output_profile_mismatch")
