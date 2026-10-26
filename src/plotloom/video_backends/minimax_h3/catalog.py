"""Reviewed Plotloom client H3 catalogue; independent of the Gateway service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class H3Profile:
    """A reviewed geometry in the narrow H3 gateway contract."""

    profile_id: str
    profile_version: int
    label: str
    orientation: str
    tier: str
    width: int
    height: int
    quality: int = 1
    duration_seconds: int = 5
    fps: int = 24
    frame_count: int = 124
    min_duration_seconds: int = 5
    max_duration_seconds: int = 15
    native_audio: bool = True
    sampling_recipe: "H3SamplingRecipe | None" = None

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    def public_descriptor(self) -> dict[str, Any]:
        """Gateway health descriptor; preserve the deployed 5--15 envelope."""

        descriptor = {
            "id": self.profile_id,
            "version": self.profile_version,
            "label": self.label,
            "orientation": self.orientation,
            "tier": self.tier,
            "width": self.width,
            "height": self.height,
            "quality": self.quality,
            "durationSeconds": self.duration_seconds,
            "minDurationSeconds": self.min_duration_seconds,
            "maxDurationSeconds": self.max_duration_seconds,
            "fps": self.fps,
            "frameCount": self.frame_count,
            "nativeAudio": self.native_audio,
        }
        if self.sampling_recipe is not None:
            descriptor["samplingRecipe"] = self.sampling_recipe.public_descriptor()
        return descriptor

    def product_descriptor(self) -> dict[str, Any]:
        """Product projection; profile timing is a five-second default only."""

        descriptor = self.public_descriptor()
        descriptor.pop("minDurationSeconds")
        descriptor.pop("maxDurationSeconds")
        return descriptor


@dataclass(frozen=True)
class H3SamplingRecipe:
    """Exact recipe held in a frozen client-side H3 profile contract."""

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

    def public_descriptor(self) -> dict[str, Any]:
        return {
            "id": self.recipe_id,
            "version": self.recipe_version,
            "topology": self.topology,
            "loraFile": self.lora_file,
            "loraStrength": self.lora_strength,
            "inferenceSteps": self.inference_steps,
            "videoSigmaShift": self.video_sigma_shift,
            "audioSigmaShift": self.audio_sigma_shift,
            "sampler": self.sampler,
            "scheduler": self.scheduler,
            "denoise": self.denoise,
        }


# The two Plotloom choices are independently reviewed; the gateway owns its
# broader colleague API. Base-20 has no Turbo LoRA or explicit sigma nodes.
_QUALITY_1_RECIPE = H3SamplingRecipe(
    "lightx2v_fl2va_turbo4_v1_2",
    1,
    "turbo",
    "minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors",
    1.0,
    4,
    6.0,
    3.0,
    "euler",
    "simple",
    1.0,
)
_QUALITY_8_RECIPE = H3SamplingRecipe(
    "minimax_h3_base20", 1, "base", None, None, 20, None, None,
    "res_multistep", "simple", 1.0,
)


def _profiles(
    *,
    version: int,
    quality: int,
    recipe: H3SamplingRecipe,
) -> tuple[H3Profile, ...]:
    suffix = f"v{version}"
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
        H3Profile(
            profile_id=f"minimax_h3_quality{quality}_{orientation}_{resolution}_{suffix}",
            profile_version=version,
            label=f"{label} · {width} × {height} · Quality {quality}",
            orientation=orientation,
            tier=tier,
            width=width,
            height=height,
            quality=quality,
            sampling_recipe=recipe,
        )
        for orientation, tier, resolution, label, width, height in geometries
    )


_LEGACY_QUALITY_1_PROFILES = _profiles(version=1, quality=1, recipe=_QUALITY_1_RECIPE)
H3_PROFILES = (
    *_profiles(version=2, quality=8, recipe=_QUALITY_8_RECIPE),
    *_profiles(version=2, quality=1, recipe=_QUALITY_1_RECIPE),
)
H3_PROFILES_BY_ID = {profile.profile_id: profile for profile in H3_PROFILES}
H3_ALL_PROFILES_BY_ID = {
    **{profile.profile_id: profile for profile in _LEGACY_QUALITY_1_PROFILES},
    **H3_PROFILES_BY_ID,
}
DEFAULT_H3_PROFILE_ID = H3_PROFILES[0].profile_id
H3_PROFILE_CONTRACT_VERSION = 6
# This identifier is the client-side admission anchor for the reviewed gateway
# catalog.  It is distinct from individual frozen profile IDs, which remain
# valid explicit runtime selections.
H3_CATALOG_ID = "minimax_h3_gateway_catalog_v7"
H3_QUALIFIED_DURATION_FRAMES = {
    seconds: seconds * 24 + (5 - seconds * 24 % 17) % 17
    for seconds in range(5, 16)
}
