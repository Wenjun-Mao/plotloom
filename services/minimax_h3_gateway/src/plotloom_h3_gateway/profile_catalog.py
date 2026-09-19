"""Versioned MiniMax-H3 profiles and complete sampling recipes.

The public gateway catalog contains only currently admitted profiles. Retired
profiles remain addressable internally so that a historical job keeps its
original interpretation, but they can never be selected for new work.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROFILE_CONTRACT_VERSION = 5
FRAMES_PER_SECOND = 24
MIN_DURATION_SECONDS = 5
MAX_DURATION_SECONDS = 15
FRAME_GRID_INTERVAL = 17
FRAME_GRID_OFFSET = 5


@dataclass(frozen=True)
class H3SamplingRecipe:
    """Atomic, reviewed H3 sampling values rendered into every workflow."""

    recipe_id: str
    recipe_version: int
    lora_file: str
    lora_strength: float
    inference_steps: int
    video_sigma_shift: float
    audio_sigma_shift: float
    sampler: str
    scheduler: str
    denoise: float

    def public_descriptor(self) -> dict[str, Any]:
        return {
            "id": self.recipe_id,
            "version": self.recipe_version,
            "loraFile": self.lora_file,
            "loraStrength": self.lora_strength,
            "inferenceSteps": self.inference_steps,
            "videoSigmaShift": self.video_sigma_shift,
            "audioSigmaShift": self.audio_sigma_shift,
            "sampler": self.sampler,
            "scheduler": self.scheduler,
            "denoise": self.denoise,
        }


# This recipe is retained only to read and, if needed, finish a job accepted
# by the original gateway. Its 12/3 values reproduce the former implicit
# ComfyUI defaults; it is intentionally not an admission target.
LEGACY_IMPLICIT_TURBO4_V1 = H3SamplingRecipe(
    "lightx2v_fl2va_turbo4_v1_implicit_h3_defaults",
    1,
    "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
    1.0,
    4,
    12.0,
    3.0,
    "res_multistep",
    "simple",
    1.0,
)

# LightX2V's published FL2VA 4-step v1.0 768p recipe. The explicit 6/3
# shifts are the material repair: no rendered graph may inherit H3 defaults.
LIGHTX2V_FL2VA_TURBO4_V1 = H3SamplingRecipe(
    "lightx2v_fl2va_turbo4_v1_768p",
    1,
    "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
    1.0,
    4,
    6.0,
    3.0,
    "res_multistep",
    "simple",
    1.0,
)


@dataclass(frozen=True)
class GatewayProfile:
    profile_id: str
    profile_version: int
    label: str
    orientation: str
    tier: str
    width: int
    height: int
    recipe: H3SamplingRecipe
    accepts_new_jobs: bool
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
            "samplingRecipe": self.recipe.public_descriptor(),
        }


def _profiles(
    *,
    version: int,
    recipe: H3SamplingRecipe,
    accepts_new_jobs: bool,
) -> tuple[GatewayProfile, ...]:
    suffix = f"v{version}"
    label_suffix = (
        " · Corrected recipe" if accepts_new_jobs else " · Retired observed recipe"
    )
    geometries = (
        ("portrait", "fast", "576x1024", "Portrait · Fast", 576, 1024),
        ("portrait", "standard", "608x1088", "Portrait · Standard", 608, 1088),
        (
            "portrait",
            "high_resolution",
            "704x1280",
            "Portrait · High resolution",
            704,
            1280,
        ),
        ("landscape", "fast", "832x480", "Landscape · Fast", 832, 480),
        ("landscape", "standard", "960x544", "Landscape · Standard", 960, 544),
        (
            "landscape",
            "high_resolution",
            "1280x704",
            "Landscape · High resolution",
            1280,
            704,
        ),
    )
    return tuple(
        GatewayProfile(
            profile_id=f"minimax_h3_fp8_turbo4_{orientation}_{resolution}_{suffix}",
            profile_version=version,
            label=f"{label} · {width} × {height}{label_suffix}",
            orientation=orientation,
            tier=tier,
            width=width,
            height=height,
            recipe=recipe,
            accepts_new_jobs=accepts_new_jobs,
        )
        for orientation, tier, resolution, label, width, height in geometries
    )


H3_RETIRED_GATEWAY_PROFILES = _profiles(
    version=1, recipe=LEGACY_IMPLICIT_TURBO4_V1, accepts_new_jobs=False,
)
H3_GATEWAY_PROFILES = _profiles(
    version=2, recipe=LIGHTX2V_FL2VA_TURBO4_V1, accepts_new_jobs=True,
)
H3_ALL_GATEWAY_PROFILES = H3_RETIRED_GATEWAY_PROFILES + H3_GATEWAY_PROFILES
H3_GATEWAY_PROFILES_BY_ID = {item.profile_id: item for item in H3_ALL_GATEWAY_PROFILES}


def profile(profile_id: str) -> GatewayProfile:
    """Find a profile for a stored job, including a retired historical one."""

    value = H3_GATEWAY_PROFILES_BY_ID.get(profile_id)
    if value is None:
        raise KeyError(profile_id)
    return value


def admitted_profile(profile_id: str) -> GatewayProfile:
    """Find a current profile that may receive a brand-new job."""

    value = profile(profile_id)
    if not value.accepts_new_jobs:
        raise KeyError(profile_id)
    return value


def active_lora_files() -> frozenset[str]:
    return frozenset(item.recipe.lora_file for item in H3_GATEWAY_PROFILES)


def frame_count_for_duration_seconds(duration_seconds: int) -> int:
    """Snap a requested whole-second duration to H3's native 17k + 5 grid."""

    if not MIN_DURATION_SECONDS <= duration_seconds <= MAX_DURATION_SECONDS:
        raise ValueError("durationSeconds must be within the supported 5-15 second range")
    requested_frames = duration_seconds * FRAMES_PER_SECOND
    return requested_frames + (FRAME_GRID_OFFSET - requested_frames % FRAME_GRID_INTERVAL) % FRAME_GRID_INTERVAL


def delivered_duration_seconds(frame_count: int) -> float:
    return frame_count / FRAMES_PER_SECOND
