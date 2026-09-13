"""Frozen Plotloom adapter for the private MiniMax-H3 profile catalog."""
from __future__ import annotations

from dataclasses import dataclass
import re
from secrets import randbits
from typing import Any

from ...video_ingestion import ObservedVideo
from ...video_provider import (
    RemoteOutcomeUnknown,
    RemotePredictionFailed,
    VideoOutputContractError,
    VideoProductionContract,
    VideoProviderError,
)


@dataclass(frozen=True)
class H3Profile:
    """A reviewed geometry in the narrow H3 gateway contract.

    ``selectable`` distinguishes the old 864x480 contract kept only to
    retrieve historical jobs from the new catalog exposed to authors.
    """

    profile_id: str
    profile_version: int
    label: str
    orientation: str
    tier: str
    width: int
    height: int
    selectable: bool
    duration_seconds: int = 5
    fps: int = 24
    frame_count: int = 124
    native_audio: bool = True
    lora_id: str = "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    def public_descriptor(self) -> dict[str, Any]:
        return {
            "id": self.profile_id,
            "version": self.profile_version,
            "label": self.label,
            "orientation": self.orientation,
            "tier": self.tier,
            "width": self.width,
            "height": self.height,
            "durationSeconds": self.duration_seconds,
            "fps": self.fps,
            "frameCount": self.frame_count,
            "nativeAudio": self.native_audio,
            "selectable": self.selectable,
        }


# The catalog is deliberately an allowlist, not a width/height calculator.
# Each entry corresponds to a trusted gateway workflow rendering and is frozen
# into the job snapshot. The old profile remains only for queued/history jobs.
LEGACY_H3_PROFILE = H3Profile(
    "minimax_h3_fp8_turbo4_480p", 1, "Legacy landscape · 864 × 480",
    "landscape", "legacy", 864, 480, False,
)
H3_PORTRAIT_FAST = H3Profile(
    "minimax_h3_fp8_turbo4_portrait_576x1024_v1", 1, "Portrait · Fast · 576 × 1024",
    "portrait", "fast", 576, 1024, True,
)
H3_PORTRAIT_STANDARD = H3Profile(
    "minimax_h3_fp8_turbo4_portrait_608x1088_v1", 1, "Portrait · Standard · 608 × 1088",
    "portrait", "standard", 608, 1088, True,
)
H3_PORTRAIT_HIGH = H3Profile(
    "minimax_h3_fp8_turbo4_portrait_704x1280_v1", 1, "Portrait · High resolution · 704 × 1280",
    "portrait", "high_resolution", 704, 1280, True,
)
H3_LANDSCAPE_FAST = H3Profile(
    "minimax_h3_fp8_turbo4_landscape_832x480_v1", 1, "Landscape · Fast · 832 × 480",
    "landscape", "fast", 832, 480, True,
)
H3_LANDSCAPE_STANDARD = H3Profile(
    "minimax_h3_fp8_turbo4_landscape_960x544_v1", 1, "Landscape · Standard · 960 × 544",
    "landscape", "standard", 960, 544, True,
)
H3_LANDSCAPE_HIGH = H3Profile(
    "minimax_h3_fp8_turbo4_landscape_1280x704_v1", 1, "Landscape · High resolution · 1280 × 704",
    "landscape", "high_resolution", 1280, 704, True,
)
H3_PROFILES = (
    LEGACY_H3_PROFILE,
    H3_PORTRAIT_FAST,
    H3_PORTRAIT_STANDARD,
    H3_PORTRAIT_HIGH,
    H3_LANDSCAPE_FAST,
    H3_LANDSCAPE_STANDARD,
    H3_LANDSCAPE_HIGH,
)
H3_PROFILES_BY_ID = {profile.profile_id: profile for profile in H3_PROFILES}
DEFAULT_NEW_H3_PROFILE_ID = H3_PORTRAIT_FAST.profile_id
H3_PROFILE_CONTRACT_VERSION = 2
# Compatibility import for callers that only need the historical descriptor.
MINIMAX_H3_480P = LEGACY_H3_PROFILE


class MiniMaxH3GatewayAdapter:
    """Compile and validate only profiles in the private H3 catalog."""

    adapter_id = "minimax_h3_gateway"
    adapter_version = "2"
    _JOB_ID = re.compile(r"^h3_[0-9a-f]{32}$")
    # The gateway retains the broader set to retrieve historical snapshots,
    # but new Plotloom work must receive a fully composed reviewed keyframe.
    _ASPECT_POLICIES = frozenset({"cover_center_crop", "contain_pad", "reject_mismatch"})
    _NEW_JOB_ASPECT_POLICY = "reject_mismatch"
    _LETTERBOX_ASPECT_POLICY = "contain_pad"

    def _profile(self, profile_id: str | None, *, legacy_if_missing: bool = False) -> H3Profile:
        resolved = profile_id or (LEGACY_H3_PROFILE.profile_id if legacy_if_missing else DEFAULT_NEW_H3_PROFILE_ID)
        profile = H3_PROFILES_BY_ID.get(resolved)
        if profile is None:
            raise VideoProviderError("H3 profile is not allowlisted")
        return profile

    def production_contract(
        self,
        *,
        requested_seconds: int | None,
        resolution: str | None,
        audio: bool | None,
        aspect_policy: str | None,
        allow_letterbox: bool,
        seed: int | None,
        profile_id: str | None,
    ) -> VideoProductionContract:
        profile = self._profile(profile_id)
        if not profile.selectable:
            raise VideoProviderError("H3 legacy profile cannot prepare new jobs")
        if requested_seconds not in {None, profile.duration_seconds}:
            raise VideoProviderError("H3 duration capability mismatch")
        if resolution not in {None, profile.resolution}:
            raise VideoProviderError("H3 resolution capability mismatch")
        if audio not in {None, True}:
            raise VideoProviderError("H3 native audio is required")
        expected_policy = (
            self._LETTERBOX_ASPECT_POLICY if allow_letterbox else self._NEW_JOB_ASPECT_POLICY
        )
        if aspect_policy != expected_policy:
            raise VideoProviderError(
                "H3 new jobs require reject_mismatch with a prepared keyframe, "
                "or explicit allowLetterbox with contain_pad"
            )
        return VideoProductionContract(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            provider="minimax_h3_gateway",
            model=profile.profile_id,
            capability_version=H3_PROFILE_CONTRACT_VERSION,
            requested_seconds=profile.duration_seconds,
            resolution=profile.resolution,
            audio=True,
            aspect_policy=aspect_policy,
            allow_letterbox=allow_letterbox,
            seed=seed if seed is not None else randbits(63),
            tracks_paid_wan_pilot=False,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            width=profile.width,
            height=profile.height,
        )

    def public_capability(self) -> dict[str, Any]:
        """Return the secret-free new-job catalog; portrait fast is the UI default."""

        default = self._profile(DEFAULT_NEW_H3_PROFILE_ID)
        return {
            "enabled": True,
            "adapterId": self.adapter_id,
            "adapterVersion": self.adapter_version,
            "provider": "minimax_h3_gateway",
            "model": default.profile_id,
            "durationSeconds": default.duration_seconds,
            "resolution": default.resolution,
            "width": default.width,
            "height": default.height,
            "fps": default.fps,
            "frameCount": default.frame_count,
            "nativeAudio": True,
            "requiresAspectPolicy": False,
            "inputAspectPolicy": self._NEW_JOB_ASPECT_POLICY,
            "allowsLetterbox": True,
            "tracksPaidWanPilot": False,
            "profileContractVersion": H3_PROFILE_CONTRACT_VERSION,
            "defaultProfileId": DEFAULT_NEW_H3_PROFILE_ID,
            "profiles": [profile.public_descriptor() for profile in H3_PROFILES],
        }

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
    ) -> dict[str, Any]:
        # A V1 frozen H3 snapshot has no profile ID. It can only mean the
        # former one-profile gateway, never today's portrait default.
        profile = self._profile(profile_id, legacy_if_missing=True)
        if duration != profile.duration_seconds or resolution != profile.resolution or audio is not True:
            raise VideoProviderError("H3 frozen request does not match its profile")
        if aspect_policy not in self._ASPECT_POLICIES or seed is None:
            raise VideoProviderError("H3 frozen request is incomplete")
        if not uploaded_asset.startswith("asset_"):
            raise VideoProviderError("H3 upload response has no asset ID")
        return {
            "assetId": uploaded_asset,
            "prompt": prompt,
            "profileId": profile.profile_id,
            "aspectPolicy": aspect_policy,
            "seed": seed,
        }

    @classmethod
    def prediction_id(cls, payload: dict[str, Any], *, expected_profile_id: str | None) -> str:
        value = payload.get("id")
        if not isinstance(value, str) or not cls._JOB_ID.fullmatch(value):
            raise VideoProviderError("H3 response has no documented job ID")
        expected = expected_profile_id or LEGACY_H3_PROFILE.profile_id
        if payload.get("profileId") != expected:
            raise VideoProviderError("H3 response profile does not match frozen job")
        return value

    @classmethod
    def completed_output(cls, payload: dict[str, Any], *, expected_profile_id: str | None) -> str | None:
        cls.prediction_id(payload, expected_profile_id=expected_profile_id)
        status = payload.get("status")
        if not isinstance(status, str):
            raise VideoProviderError("H3 job response has no documented status")
        if status in {"failed", "cancelled"}:
            raise RemotePredictionFailed("H3 gateway reported terminal failure")
        if status == "outcome_unknown":
            raise RemoteOutcomeUnknown("H3 gateway cannot establish Comfy submission outcome")
        if status in {"reserved", "queued", "submitting", "submitted", "running", "transfer_pending"}:
            return None
        if status != "succeeded":
            raise VideoProviderError("H3 completed response is invalid")
        if payload.get("outputReady") is not True:
            raise VideoOutputContractError("h3_gateway_output_expired")
        return cls.prediction_id(payload, expected_profile_id=expected_profile_id)

    @classmethod
    def validate_output_reference(cls, value: str) -> None:
        if not cls._JOB_ID.fullmatch(value):
            raise VideoProviderError("H3 output reference is not a gateway job ID")

    def validate_observed_output(self, observed: ObservedVideo, *, profile_id: str | None) -> None:
        """Fail closed if delivery differs from the immutable selected profile."""

        profile = self._profile(profile_id, legacy_if_missing=True)
        expected_duration = profile.frame_count / profile.fps
        if (
            (observed.width, observed.height) != (profile.width, profile.height)
            or observed.video_codec != "h264"
            or observed.audio_codec != "aac"
            or observed.frame_rate is None
            or abs(observed.frame_rate - profile.fps) > 0.01
            or observed.frame_count != profile.frame_count
            or abs(observed.duration_seconds - expected_duration) > (1 / profile.fps)
        ):
            raise VideoOutputContractError("h3_output_profile_mismatch")
