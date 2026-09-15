"""Provider-neutral video contracts used by P2 production jobs.

Concrete adapter implementations live in ``plotloom.video_backends`` and
share only the small production boundary below. A provider name or model
string never selects a permissive compatibility path.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any, ClassVar, Literal, Protocol
from urllib.parse import urlparse

from .domain import contains_secret_setting, contains_secret_value
from .video_ingestion import ObservedVideo, assert_public_https_url


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
class VideoBackendInstanceIdentity:
    """Secret-free fingerprint of one configured transport instance.

    Project evidence must distinguish two H3 gateways without copying their
    endpoint, credentials, or a signed URL into a portable folder.  The
    transport derives this fingerprint from its local configuration; only the
    type and digest cross the project boundary.
    """

    kind: str
    fingerprint: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", self.kind):
            raise ValueError("video backend identity kind is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", self.fingerprint):
            raise ValueError("video backend identity fingerprint is invalid")

    @classmethod
    def from_public_configuration(
        cls, kind: str, configuration: dict[str, Any]
    ) -> "VideoBackendInstanceIdentity":
        """Hash validated, non-secret transport configuration locally.

        URL-bearing values are allowed only as bare HTTP(S) roots.  This keeps
        credentials, query/signed URLs, and userinfo out of both the frozen
        evidence and the value used to derive it.
        """

        if contains_secret_setting(configuration) or contains_secret_value(configuration):
            raise ValueError("video backend identity configuration must be secret-free")

        def validate(value: Any) -> None:
            if isinstance(value, dict):
                for child in value.values():
                    validate(child)
            elif isinstance(value, list):
                for child in value:
                    validate(child)
            elif isinstance(value, str):
                parsed = urlparse(value)
                if parsed.scheme and (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.netloc
                    or parsed.username
                    or parsed.password
                    or parsed.path not in {"", "/"}
                    or parsed.query
                    or parsed.fragment
                ):
                    raise ValueError(
                        "video backend identity URL must be a credential-free HTTP(S) root"
                    )
            elif value is not None and not isinstance(value, (bool, int, float)):
                raise ValueError("video backend identity configuration is not JSON data")

        validate(configuration)
        encoded = json.dumps(
            configuration, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return cls(kind=kind, fingerprint=sha256(encoded).hexdigest())

    def snapshot(self) -> dict[str, str]:
        return {"kind": self.kind, "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class VideoBackendBinding:
    """The adapter contract plus one configured backend instance."""

    adapter_id: str
    adapter_version: str
    instance: VideoBackendInstanceIdentity

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", self.adapter_id):
            raise ValueError("video backend adapter ID is invalid")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,62}", self.adapter_version):
            raise ValueError("video backend adapter version is invalid")

    def snapshot(self) -> dict[str, Any]:
        return {
            "adapterId": self.adapter_id,
            "adapterVersion": self.adapter_version,
            "instance": self.instance.snapshot(),
        }

    def matches_snapshot(self, provider: Any) -> bool:
        return isinstance(provider, dict) and provider.get("backendBinding") == self.snapshot()


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
    cost_policy: Literal["wan_paid_pilot_v1", "local_capacity_v1"]
    # Only catalog-backed H3 contracts persist these author opt-ins. Historical
    # Wan and V1 H3 snapshot bytes stay untouched.
    allow_letterbox: bool = False
    allow_center_crop: bool = False
    # Optional profile metadata is used by gateway-owned catalog adapters.
    # Wan V1/V2 snapshots intentionally omit it byte-for-byte.
    profile_id: str | None = None
    profile_version: int | None = None
    width: int | None = None
    height: int | None = None

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", self.adapter_id):
            raise ValueError("video adapter ID is invalid")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,62}", self.adapter_version):
            raise ValueError("video adapter version is invalid")
        if not self.provider or not self.model or self.capability_version < 1:
            raise ValueError("video production capability is invalid")
        if self.cost_policy not in {"wan_paid_pilot_v1", "local_capacity_v1"}:
            raise ValueError("video cost policy is not a supported versioned contract")
        if self.requested_seconds < 1 or self.requested_seconds > 30:
            raise ValueError("video duration is invalid")
        if not self.resolution:
            raise ValueError("video resolution is required")
        if self.seed is not None and not 0 <= self.seed <= 2**63 - 1:
            raise ValueError("video seed is invalid")
        profile_parts = (self.profile_id, self.profile_version, self.width, self.height)
        if any(part is not None for part in profile_parts):
            if (
                not isinstance(self.profile_id, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", self.profile_id)
                or not isinstance(self.profile_version, int)
                or self.profile_version < 1
                or not isinstance(self.width, int)
                or not isinstance(self.height, int)
                or self.width < 32
                or self.height < 32
                or self.width % 32
                or self.height % 32
            ):
                raise ValueError("video profile contract is invalid")
            if self.allow_letterbox and self.allow_center_crop:
                raise ValueError("video input-frame modes are mutually exclusive")
            expected_policy = (
                "cover_center_crop" if self.allow_center_crop
                else "contain_pad" if self.allow_letterbox
                else "reject_mismatch"
            )
            if self.aspect_policy != expected_policy:
                raise ValueError("video input-frame mode does not match its aspect policy")
        elif self.allow_letterbox or self.allow_center_crop:
            raise ValueError("input-frame mode requires a frozen video profile")

    def provider_snapshot(self) -> dict[str, Any]:
        return {
            "adapterId": self.adapter_id,
            "adapterVersion": self.adapter_version,
            "provider": self.provider,
            "model": self.model,
            "capabilityVersion": self.capability_version,
            "costPolicy": self.cost_policy,
        }

    @property
    def tracks_paid_wan_pilot(self) -> bool:
        """Compatibility view for the retained Wan lifecycle only."""

        return self.cost_policy == "wan_paid_pilot_v1"

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
        if self.profile_id is not None:
            request |= {
                "profileId": self.profile_id,
                "profileVersion": self.profile_version,
                "width": self.width,
                "height": self.height,
                "allowLetterbox": self.allow_letterbox,
                "allowCenterCrop": self.allow_center_crop,
            }
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


class VideoProviderPort(Protocol):
    def configured_backend_identity(self) -> VideoBackendInstanceIdentity: ...

    def upload(self, image: bytes, *, mime_type: str) -> str: ...
    def submit(
        self, payload: dict[str, Any], *, idempotency_key: str | None = None
    ) -> dict[str, Any]: ...
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
        profile_id: str | None,
    ) -> dict[str, Any]: ...

    def prediction_id(
        self,
        payload: dict[str, Any],
        *,
        expected_profile_id: str | None = None,
        expected_aspect_policy: str | None = None,
    ) -> str: ...

    def completed_output(
        self,
        payload: dict[str, Any],
        *,
        expected_profile_id: str | None = None,
        expected_aspect_policy: str | None = None,
    ) -> str | None: ...

    def validate_output_reference(self, value: str) -> None: ...

    def validate_observed_output(self, observed: ObservedVideo, *, profile_id: str | None = None) -> None: ...

    def production_contract(
        self,
        *,
        requested_seconds: int | None,
        resolution: str | None,
        audio: bool | None,
        aspect_policy: str | None,
        allow_letterbox: bool,
        allow_center_crop: bool,
        seed: int | None,
        profile_id: str | None,
    ) -> VideoProductionContract | None: ...

    def public_capability(self) -> dict[str, Any]: ...


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

    def production_contract(
        self,
        *,
        requested_seconds: int | None,
        resolution: str | None,
        audio: bool | None,
        aspect_policy: str | None,
        allow_letterbox: bool,
        allow_center_crop: bool,
        seed: int | None,
        profile_id: str | None = None,
    ) -> None:
        # V1 Wan snapshots have no seed or aspect-policy fields. Keep that
        # historical request projection exact rather than allowing future
        # backend fields to leak into it.
        if aspect_policy is not None or allow_letterbox or allow_center_crop or seed is not None or profile_id is not None:
            raise VideoProviderError("Atlas Wan does not accept H3 aspect policy or seed")
        return None

    def public_capability(self) -> dict[str, Any]:
        caps = self.capabilities
        return {
            "enabled": True,
            "adapterId": self.adapter_id,
            "adapterVersion": self.adapter_version,
            "provider": caps.provider,
            "model": caps.model,
            "durationSeconds": caps.durations[0],
            "resolution": caps.resolutions[0],
            "width": None,
            "height": None,
            "fps": None,
            "frameCount": None,
            "nativeAudio": caps.native_audio,
            "requiresAspectPolicy": False,
            "tracksPaidWanPilot": True,
        }

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
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        caps = self.capabilities
        if duration not in caps.durations or resolution not in caps.resolutions or audio is not True:
            raise VideoProviderError("Wan P2 capability mismatch")
        if aspect_policy is not None or seed is not None or profile_id is not None:
            raise VideoProviderError("Wan P2 request includes unsupported H3 fields")
        if not uploaded_asset.startswith("https://"):
            raise VideoProviderError("uploaded image URL must be HTTPS")
        return {"model": caps.model, "prompt": prompt, "image": uploaded_asset, "duration": duration, "resolution": resolution, "audio": True}

    @staticmethod
    def prediction_id(
        payload: dict[str, Any],
        *,
        expected_profile_id: str | None = None,
        expected_aspect_policy: str | None = None,
    ) -> str:
        if expected_profile_id is not None:
            raise VideoProviderError("Wan P2 response includes an unsupported profile")
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        value = data.get("id") if isinstance(data, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise VideoProviderError("Atlas response has no documented prediction id")
        return value

    @staticmethod
    def completed_output(
        payload: dict[str, Any],
        *,
        expected_profile_id: str | None = None,
        expected_aspect_policy: str | None = None,
    ) -> str | None:
        if expected_profile_id is not None:
            raise VideoProviderError("Wan P2 response includes an unsupported profile")
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
        # Atlas remains the only adapter permitted to resolve an external
        # public output. The generic job service delegates this boundary to
        # the selected adapter rather than branching on adapter class.
        assert_public_https_url(value)

    @staticmethod
    def validate_observed_output(_observed: ObservedVideo, *, profile_id: str | None = None) -> None:
        # Browser-playability and native-audio checks remain shared ingestion
        # requirements. Atlas has no separately evidenced fixed frame profile.
        if profile_id is not None:
            raise VideoProviderError("Wan P2 output includes an unsupported profile")
        return None
