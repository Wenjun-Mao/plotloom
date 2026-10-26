"""Frozen Plotloom adapter for the private MiniMax-H3 profile catalog."""
from __future__ import annotations

import re
from secrets import randbits
from typing import Any

from .catalog import (
    H3Profile,
    H3_PROFILES,
    H3_PROFILES_BY_ID,
    H3_ALL_PROFILES_BY_ID,
    DEFAULT_H3_PROFILE_ID,
    H3_PROFILE_CONTRACT_VERSION,
    H3_CATALOG_ID,
    H3_QUALIFIED_DURATION_FRAMES,
)

from ...video_ingestion import ObservedVideo
from ...video_provider import (
    RemoteOutcomeUnknown,
    RemotePredictionFailed,
    VideoOutputContractError,
    VideoProductionContract,
    VideoProviderError,
)


class MiniMaxH3GatewayAdapter:
    """Compile and validate only profiles in the private H3 catalog."""

    adapter_id = "minimax_h3_gateway"
    adapter_version = "6"
    _JOB_ID = re.compile(r"^h3_[0-9a-f]{32}$")
    # New Plotloom work must receive a fully composed reviewed keyframe.
    _ASPECT_POLICIES = frozenset({"cover_center_crop", "contain_pad", "reject_mismatch"})
    _NEW_JOB_ASPECT_POLICY = "reject_mismatch"
    _LETTERBOX_ASPECT_POLICY = "contain_pad"
    _CENTER_CROP_ASPECT_POLICY = "cover_center_crop"

    def _profile(self, profile_id: str | None, *, default_if_missing: bool = False) -> H3Profile:
        if profile_id is None and not default_if_missing:
            raise VideoProviderError("H3 frozen request requires an explicit profile")
        resolved = profile_id or DEFAULT_H3_PROFILE_ID
        profile = H3_PROFILES_BY_ID.get(resolved)
        if profile is None:
            raise VideoProviderError("H3 profile is not allowlisted")
        return profile

    def _frozen_profile(
        self, profile_id: str | None, *, profile_version: int | None = None,
        width: int | None = None, height: int | None = None, fps: int | None = None,
        quality: int | None = None,
    ) -> H3Profile:
        """Refuse catalog drift when a prepared job resumes after restart."""

        if profile_id is None:
            raise VideoProviderError("H3 frozen request requires an explicit profile")
        profile = H3_ALL_PROFILES_BY_ID.get(profile_id)
        if profile is None:
            raise VideoProviderError("H3 frozen profile contract no longer matches the trusted catalog")
        if any(
            actual is not None and actual != expected
            for actual, expected in (
                (profile_version, profile.profile_version), (width, profile.width),
                (height, profile.height), (fps, profile.fps), (quality, profile.quality),
            )
        ):
            raise VideoProviderError("H3 frozen profile contract no longer matches the trusted catalog")
        return profile

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
    ) -> VideoProductionContract:
        profile = self._profile(profile_id, default_if_missing=True)
        duration = profile.duration_seconds if requested_seconds is None else requested_seconds
        frame_count = H3_QUALIFIED_DURATION_FRAMES.get(duration) if type(duration) is int else None
        if frame_count is None:
            raise VideoProviderError("H3 duration capability mismatch")
        if resolution not in {None, profile.resolution}:
            raise VideoProviderError("H3 resolution capability mismatch")
        if audio not in {None, True}:
            raise VideoProviderError("H3 native audio is required")
        if allow_letterbox and allow_center_crop:
            raise VideoProviderError("H3 input-frame modes are mutually exclusive")
        expected_policy = (
            self._CENTER_CROP_ASPECT_POLICY if allow_center_crop
            else self._LETTERBOX_ASPECT_POLICY if allow_letterbox
            else self._NEW_JOB_ASPECT_POLICY
        )
        if aspect_policy != expected_policy:
            raise VideoProviderError(
                "H3 new jobs require reject_mismatch with a prepared keyframe, "
                "explicit allowLetterbox with contain_pad, or explicit "
                "allowCenterCrop with cover_center_crop"
            )
        return VideoProductionContract(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            provider="minimax_h3_gateway",
            model=profile.profile_id,
            capability_version=H3_PROFILE_CONTRACT_VERSION,
            requested_seconds=duration,
            resolution=profile.resolution,
            audio=True,
            aspect_policy=aspect_policy,
            allow_letterbox=allow_letterbox,
            allow_center_crop=allow_center_crop,
            seed=seed if seed is not None else randbits(63),
            cost_policy="local_capacity_v1",
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            width=profile.width,
            height=profile.height,
            fps=profile.fps,
            frame_count=frame_count,
            quality=profile.quality,
        )

    def public_capability(self) -> dict[str, Any]:
        """Return the secret-free new-job catalog; portrait fast is the UI default."""

        default = self._profile(DEFAULT_H3_PROFILE_ID)
        return {
            "enabled": True,
            "adapterId": self.adapter_id,
            "adapterVersion": self.adapter_version,
            "provider": "minimax_h3_gateway",
            "model": H3_CATALOG_ID,
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
            "allowsCenterCrop": True,
            "tracksPaidWanPilot": False,
            "profileContractVersion": H3_PROFILE_CONTRACT_VERSION,
            "defaultQuality": default.quality,
            # Plotloom's generic video-review UI still needs one internal
            # geometry selection. It never crosses the gateway boundary: the
            # transport serializes its frozen quality and resolution.
            "defaultProfileId": default.profile_id,
            "qualifiedDurationSeconds": sorted(H3_QUALIFIED_DURATION_FRAMES),
            "qualities": [1, 8],
            "resolutions": list(dict.fromkeys(profile.resolution for profile in H3_PROFILES)),
            "profiles": [profile.product_descriptor() for profile in H3_PROFILES],
        }

    def compile_image(
        self,
        *,
        prompt: str,
        duration: int,
        resolution: str,
        audio: bool,
        aspect_policy: str | None,
        seed: int | None,
        profile_id: str | None,
        profile_version: int | None = None,
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
        frame_count: int | None = None,
        quality: int | None = None,
    ) -> dict[str, Any]:
        profile = self._frozen_profile(
            profile_id, profile_version=profile_version, width=width, height=height, fps=fps,
            quality=quality,
        )
        if profile.profile_version >= 2 and quality is None:
            raise VideoProviderError("H3 frozen request has no quality")
        if (
            type(duration) is not int
            or duration not in H3_QUALIFIED_DURATION_FRAMES
            or resolution != profile.resolution
            or audio is not True
            or frame_count is not None and frame_count != H3_QUALIFIED_DURATION_FRAMES[duration]
        ):
            raise VideoProviderError("H3 frozen request does not match its profile")
        if aspect_policy not in self._ASPECT_POLICIES or seed is None:
            raise VideoProviderError("H3 frozen request is incomplete")
        return {
            "prompt": prompt,
            "quality": profile.quality,
            "resolution": profile.resolution,
            "aspectPolicy": aspect_policy,
            "seed": seed,
            "durationSeconds": duration,
        }

    @classmethod
    def prediction_id(
        cls,
        payload: dict[str, Any],
        *,
        expected_profile_id: str | None,
        expected_aspect_policy: str | None = None,
        expected_duration_seconds: int | None = None,
        expected_frame_count: int | None = None,
        expected_seed: int | None = None,
        expected_profile_version: int | None = None,
        expected_width: int | None = None,
        expected_height: int | None = None,
        expected_fps: int | None = None,
    ) -> str:
        value = payload.get("id")
        if not isinstance(value, str) or not cls._JOB_ID.fullmatch(value):
            raise VideoProviderError("H3 response has no documented job ID")
        if expected_profile_id is None:
            raise VideoProviderError("H3 response requires a frozen profile")
        profile = cls()._frozen_profile(
            expected_profile_id, profile_version=expected_profile_version,
            width=expected_width, height=expected_height, fps=expected_fps,
        )
        if payload.get("quality") != profile.quality or payload.get("resolution") != profile.resolution:
            raise VideoProviderError("H3 response quality or resolution does not match frozen job")
        if expected_aspect_policy is not None and payload.get("aspectPolicy") != expected_aspect_policy:
            raise VideoProviderError("H3 response aspect policy does not match frozen job")
        if expected_duration_seconds is not None and payload.get("requestedDurationSeconds") != expected_duration_seconds:
            raise VideoProviderError("H3 response duration does not match frozen job")
        if expected_frame_count is not None and payload.get("frameCount") != expected_frame_count:
            raise VideoProviderError("H3 response frame count does not match frozen job")
        if expected_seed is not None and payload.get("seed") != expected_seed:
            raise VideoProviderError("H3 response seed does not match frozen job")
        return value

    @classmethod
    def completed_output(
        cls,
        payload: dict[str, Any],
        *,
        expected_profile_id: str | None,
        expected_aspect_policy: str | None = None,
        expected_duration_seconds: int | None = None,
        expected_frame_count: int | None = None,
        expected_seed: int | None = None,
        expected_profile_version: int | None = None,
        expected_width: int | None = None,
        expected_height: int | None = None,
        expected_fps: int | None = None,
    ) -> str | None:
        cls.prediction_id(
            payload,
            expected_profile_id=expected_profile_id,
            expected_aspect_policy=expected_aspect_policy,
            expected_duration_seconds=expected_duration_seconds,
            expected_frame_count=expected_frame_count,
            expected_seed=expected_seed,
            expected_profile_version=expected_profile_version,
            expected_width=expected_width,
            expected_height=expected_height,
            expected_fps=expected_fps,
        )
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
        return cls.prediction_id(
            payload,
            expected_profile_id=expected_profile_id,
            expected_aspect_policy=expected_aspect_policy,
            expected_duration_seconds=expected_duration_seconds,
            expected_frame_count=expected_frame_count,
            expected_seed=expected_seed,
            expected_profile_version=expected_profile_version,
            expected_width=expected_width,
            expected_height=expected_height,
            expected_fps=expected_fps,
        )

    @classmethod
    def validate_output_reference(cls, value: str) -> None:
        if not cls._JOB_ID.fullmatch(value):
            raise VideoProviderError("H3 output reference is not a gateway job ID")

    def validate_observed_output(
        self, observed: ObservedVideo, *, profile_id: str | None,
        requested_seconds: int | None = None, expected_frame_count: int | None = None,
        expected_fps: int | None = None, expected_profile_version: int | None = None,
        expected_width: int | None = None, expected_height: int | None = None,
    ) -> None:
        """Fail closed if delivery differs from the immutable selected profile."""

        profile = self._frozen_profile(
            profile_id, profile_version=expected_profile_version, width=expected_width,
            height=expected_height, fps=expected_fps,
        )
        if type(requested_seconds) is not int or requested_seconds not in H3_QUALIFIED_DURATION_FRAMES:
            raise VideoOutputContractError("h3_output_profile_mismatch")
        frame_count = H3_QUALIFIED_DURATION_FRAMES[requested_seconds]
        if expected_frame_count != frame_count or expected_fps != profile.fps:
            raise VideoOutputContractError("h3_output_profile_mismatch")
        expected_duration = frame_count / profile.fps
        if (
            (observed.width, observed.height) != (profile.width, profile.height)
            or observed.video_codec != "h264"
            or observed.audio_codec != "aac"
            or observed.frame_rate is None
            or abs(observed.frame_rate - expected_fps) > 0.01
            or observed.frame_count != expected_frame_count
            or abs(observed.duration_seconds - expected_duration) > (1 / profile.fps)
        ):
            raise VideoOutputContractError("h3_output_profile_mismatch")
