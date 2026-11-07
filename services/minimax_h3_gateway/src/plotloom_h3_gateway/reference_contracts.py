"""Caller-owned ordered stills and explicit millisecond timing for Ref2VA."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from .contracts import AspectPolicy, SourceUrlAssetRequest

REFERENCE_MAX_IMAGES = 9
REFERENCE_MAX_BYTES = 20 * 1024 * 1024
REFERENCE_RESOLUTIONS = ("960x544", "576x1024")


def reference_frame(at_ms: int) -> int:
    return (at_ms * 24 + 500) // 1000


def reference_frame_count(duration_ms: int) -> int:
    requested = (duration_ms * 24 + 999) // 1000
    return requested + (5 - requested % 17) % 17


class ReferenceTime(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at_ms: StrictInt = Field(alias="atMs", ge=0, lt=15_000)


class ReferenceSource(ReferenceTime, SourceUrlAssetRequest):
    """A URL is fetched during admission and never persisted."""


class CreateReferenceJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=8_000)
    resolution: Literal["960x544", "576x1024"]
    aspect_policy: AspectPolicy = Field(alias="aspectPolicy")
    duration_ms: StrictInt = Field(alias="durationMs", ge=5_000, le=15_000)
    seed: StrictInt | None = Field(default=None, ge=0, le=2**63 - 1)
    references: list[ReferenceTime] = Field(min_length=1, max_length=REFERENCE_MAX_IMAGES)

    @model_validator(mode="after")
    def validate_timeline(self) -> CreateReferenceJobRequest:
        times = [item.at_ms for item in self.references]
        frames = [reference_frame(value) for value in times]
        if times[0] != 0 or any(value >= self.duration_ms for value in times):
            raise ValueError("references must start at zero and precede the requested end")
        if any(left >= right for left, right in zip(times, times[1:])):
            raise ValueError("reference times must be strictly increasing")
        if any(left >= right for left, right in zip(frames, frames[1:])):
            raise ValueError("quantized reference frames must be distinct and increasing")
        if frames[-1] >= reference_frame_count(self.duration_ms):
            raise ValueError("reference frame must be inside the native video")
        return self


class CreateReferenceJobFromUrlsRequest(CreateReferenceJobRequest):
    references: list[ReferenceSource] = Field(min_length=1, max_length=REFERENCE_MAX_IMAGES)
