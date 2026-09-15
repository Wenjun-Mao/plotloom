"""Gateway-owned, typed MiniMax-H3 geometry allowlist.

This module intentionally exposes only metadata that is safe to return from
``/health``. The ComfyUI graph and model paths remain server-side.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


TURBO_4STEP_LORA = "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"
PROFILE_CONTRACT_VERSION = 4
FRAMES_PER_SECOND = 24
MIN_DURATION_SECONDS = 5
MAX_DURATION_SECONDS = 15
FRAME_GRID_INTERVAL = 17
FRAME_GRID_OFFSET = 5


@dataclass(frozen=True)
class GatewayProfile:
    profile_id: str
    profile_version: int
    label: str
    orientation: str
    tier: str
    width: int
    height: int
    duration_seconds: int = 5
    fps: int = FRAMES_PER_SECOND
    frame_count: int = 124

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
            "minDurationSeconds": MIN_DURATION_SECONDS,
            "maxDurationSeconds": MAX_DURATION_SECONDS,
            "fps": self.fps,
            "frameCount": self.frame_count,
            "nativeAudio": True,
        }


H3_GATEWAY_PROFILES = (
    GatewayProfile("minimax_h3_fp8_turbo4_portrait_576x1024_v1", 1, "Portrait · Fast · 576 × 1024", "portrait", "fast", 576, 1024),
    GatewayProfile("minimax_h3_fp8_turbo4_portrait_608x1088_v1", 1, "Portrait · Standard · 608 × 1088", "portrait", "standard", 608, 1088),
    GatewayProfile("minimax_h3_fp8_turbo4_portrait_704x1280_v1", 1, "Portrait · High resolution · 704 × 1280", "portrait", "high_resolution", 704, 1280),
    GatewayProfile("minimax_h3_fp8_turbo4_landscape_832x480_v1", 1, "Landscape · Fast · 832 × 480", "landscape", "fast", 832, 480),
    GatewayProfile("minimax_h3_fp8_turbo4_landscape_960x544_v1", 1, "Landscape · Standard · 960 × 544", "landscape", "standard", 960, 544),
    GatewayProfile("minimax_h3_fp8_turbo4_landscape_1280x704_v1", 1, "Landscape · High resolution · 1280 × 704", "landscape", "high_resolution", 1280, 704),
)
H3_GATEWAY_PROFILES_BY_ID = {profile.profile_id: profile for profile in H3_GATEWAY_PROFILES}


def profile(profile_id: str) -> GatewayProfile:
    value = H3_GATEWAY_PROFILES_BY_ID.get(profile_id)
    if value is None:
        raise KeyError(profile_id)
    return value


def frame_count_for_duration_seconds(duration_seconds: int) -> int:
    """Snap a requested whole-second duration to H3's native 17k + 5 grid."""

    if not MIN_DURATION_SECONDS <= duration_seconds <= MAX_DURATION_SECONDS:
        raise ValueError("durationSeconds must be within the supported 5-15 second range")
    requested_frames = duration_seconds * FRAMES_PER_SECOND
    return requested_frames + (FRAME_GRID_OFFSET - requested_frames % FRAME_GRID_INTERVAL) % FRAME_GRID_INTERVAL


def delivered_duration_seconds(frame_count: int) -> float:
    return frame_count / FRAMES_PER_SECOND
