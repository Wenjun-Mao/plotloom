"""Gateway-owned, typed MiniMax-H3 geometry allowlist.

This module intentionally exposes only metadata that is safe to return from
``/health``. The ComfyUI graph and model paths remain server-side.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


TURBO_4STEP_LORA = "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"
PROFILE_CONTRACT_VERSION = 3


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
    fps: int = 24
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
