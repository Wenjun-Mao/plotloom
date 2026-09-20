"""Reviewed MiniMax-H3 quality and resolution contract.

The public gateway accepts a deliberately small pair of independent choices:
an integer quality level and an exact output resolution. A job freezes their
fully resolved execution descriptor at admission; this catalog is therefore
only an admission source, never a mutable dispatch dependency.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


GENERATION_CONTRACT_VERSION = 6
FRAMES_PER_SECOND = 24
MIN_DURATION_SECONDS = 5
MAX_DURATION_SECONDS = 15
FRAME_GRID_INTERVAL = 17
FRAME_GRID_OFFSET = 5
DEFAULT_QUALITY = 1
WORKFLOW_RENDERER_VERSION = 3


@dataclass(frozen=True)
class H3SamplingRecipe:
    """One complete, reviewed H3 sampling path."""

    recipe_id: str
    recipe_version: int
    topology: str
    lora_file: str | None
    lora_strength: float | None
    inference_steps: int
    video_sigma_shift: float | None
    audio_sigma_shift: float | None
    sampler: str
    scheduler: str
    denoise: float


@dataclass(frozen=True)
class H3Resolution:
    value: str
    width: int
    height: int


@dataclass(frozen=True)
class H3ExecutionProfile:
    """A fully materialized, dispatch-safe quality/resolution selection."""

    quality: int
    resolution: H3Resolution
    recipe: H3SamplingRecipe

    @property
    def width(self) -> int:
        return self.resolution.width

    @property
    def height(self) -> int:
        return self.resolution.height

    def snapshot(self) -> dict[str, Any]:
        """Return the exact execution semantics saved with every job."""

        return {
            "generationContractVersion": GENERATION_CONTRACT_VERSION,
            "workflowRendererVersion": WORKFLOW_RENDERER_VERSION,
            "quality": self.quality,
            "resolution": self.resolution.value,
            "width": self.width,
            "height": self.height,
            "fps": FRAMES_PER_SECOND,
            "recipe": asdict(self.recipe),
        }

    def snapshot_json(self) -> str:
        return json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":"))


RESOLUTIONS = tuple(
    H3Resolution(value, width, height)
    for value, width, height in (
        ("832x480", 832, 480),
        ("960x544", 960, 544),
        ("1280x704", 1280, 704),
        ("576x1024", 576, 1024),
        ("608x1088", 608, 1088),
        ("704x1280", 704, 1280),
    )
)
RESOLUTIONS_BY_VALUE = {item.value: item for item in RESOLUTIONS}

QUALITY_RECIPES = {
    1: H3SamplingRecipe(
        "lightx2v_fl2va_turbo4_v1_2", 1, "turbo",
        "minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors", 1.0,
        4, 6.0, 3.0, "euler", "simple", 1.0,
    ),
    2: H3SamplingRecipe(
        "lightx2v_fl2va_turbo4_v1_0", 1, "turbo",
        "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors", 1.0,
        4, 6.0, 3.0, "res_multistep", "simple", 1.0,
    ),
    3: H3SamplingRecipe(
        "lightx2v_fl2va_turbo8_v1_0", 1, "turbo",
        "minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors", 1.0,
        8, 6.0, 3.0, "euler", "simple", 1.0,
    ),
    8: H3SamplingRecipe(
        "minimax_h3_base20", 1, "base", None, None,
        20, None, None, "res_multistep", "simple", 1.0,
    ),
}


def admitted_execution(*, quality: int, resolution: str) -> H3ExecutionProfile:
    """Resolve a caller's two public choices or reject them deterministically."""

    recipe = QUALITY_RECIPES.get(quality)
    selected_resolution = RESOLUTIONS_BY_VALUE.get(resolution)
    if recipe is None:
        raise KeyError("quality")
    if selected_resolution is None:
        raise KeyError("resolution")
    return H3ExecutionProfile(quality=quality, resolution=selected_resolution, recipe=recipe)


def execution_from_snapshot(value: str) -> H3ExecutionProfile:
    """Rehydrate only an already-frozen execution descriptor for dispatch."""

    try:
        payload = json.loads(value)
        if not isinstance(payload, dict):
            raise ValueError
        recipe_payload = payload["recipe"]
        if (
            payload["generationContractVersion"] != GENERATION_CONTRACT_VERSION
            or payload["workflowRendererVersion"] != WORKFLOW_RENDERER_VERSION
            or not isinstance(recipe_payload, dict)
        ):
            raise ValueError
        # Do not resolve the stored choice through QUALITY_RECIPES here. A
        # queued job owns its complete recipe and must survive a later catalog
        # edit or retirement unchanged.
        quality = int(payload["quality"])
        resolution = H3Resolution(
            str(payload["resolution"]), int(payload["width"]), int(payload["height"])
        )
        if RESOLUTIONS_BY_VALUE.get(resolution.value) != resolution:
            raise ValueError
        recipe = H3SamplingRecipe(**recipe_payload)
        if recipe.topology not in {"turbo", "base"}:
            raise ValueError
        if recipe.topology == "turbo" and (
            not recipe.lora_file or recipe.lora_strength is None
            or recipe.video_sigma_shift is None or recipe.audio_sigma_shift is None
        ):
            raise ValueError
        if recipe.topology == "base" and any(
            item is not None
            for item in (recipe.lora_file, recipe.lora_strength, recipe.video_sigma_shift, recipe.audio_sigma_shift)
        ):
            raise ValueError
        return H3ExecutionProfile(quality, resolution, recipe)
    except (KeyError, TypeError, ValueError):
        raise ValueError("invalid frozen H3 execution snapshot") from None


def active_lora_files() -> frozenset[str]:
    return frozenset(
        recipe.lora_file for recipe in QUALITY_RECIPES.values() if recipe.lora_file is not None
    )


def frame_count_for_duration_seconds(duration_seconds: int) -> int:
    """Snap a requested whole-second duration to H3's native 17k + 5 grid."""

    if not MIN_DURATION_SECONDS <= duration_seconds <= MAX_DURATION_SECONDS:
        raise ValueError("durationSeconds must be within the supported 5-15 second range")
    requested_frames = duration_seconds * FRAMES_PER_SECOND
    return requested_frames + (FRAME_GRID_OFFSET - requested_frames % FRAME_GRID_INTERVAL) % FRAME_GRID_INTERVAL


def delivered_duration_seconds(frame_count: int) -> float:
    return frame_count / FRAMES_PER_SECOND
