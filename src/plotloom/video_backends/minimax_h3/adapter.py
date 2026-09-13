"""Frozen Plotloom adapter for the private MiniMax-H3 gateway contract."""
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
class H3Capabilities:
    """The one evidence-backed H3 profile exposed by the gateway."""

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
            seed=seed if seed is not None else randbits(63),
            tracks_paid_wan_pilot=False,
        )

    def public_capability(self) -> dict[str, Any]:
        """Return the safe H3 projection used by the generic workbench."""

        caps = self.capabilities
        return {
            "enabled": True,
            "adapterId": caps.adapter_id,
            "adapterVersion": caps.adapter_version,
            "provider": caps.provider,
            "model": caps.model,
            "durationSeconds": caps.duration_seconds,
            "resolution": caps.resolution,
            "width": caps.width,
            "height": caps.height,
            "fps": caps.fps,
            "frameCount": caps.frame_count,
            "nativeAudio": caps.native_audio,
            "requiresAspectPolicy": True,
            "tracksPaidWanPilot": False,
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
        """Fail closed if the gateway did not deliver its frozen H3 profile."""

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
