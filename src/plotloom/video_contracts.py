"""P2 video-job wire contracts, kept outside the canonical story model.

These values describe a paid production attempt.  They deliberately cannot be
used to mutate a Shot, DialogueCue, or AudioPlan.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from .domain import CamelModel


class VideoJobRequest(CamelModel):
    approval_id: str = Field(min_length=1, max_length=36)
    shot_id: str = Field(min_length=1, max_length=100)
    storyboard_revision: int = Field(ge=1)
    expected_selection_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=255)
    # The active trusted adapter fills its observed defaults.  H3 additionally
    # requires the caller to choose how a non-16:9 source frame is prepared;
    # legacy Wan preparation keeps its historic defaults when no adapter is
    # active in an offline fixture.
    requested_duration_seconds: Literal[5] | None = None
    resolution: str | None = Field(default=None, min_length=3, max_length=32)
    audio: Literal[True] | None = None
    aspect_policy: Literal["cover_center_crop", "contain_pad", "reject_mismatch"] | None = None
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)
    profile_id: str | None = Field(default=None, min_length=3, max_length=63, pattern=r"^[a-z][a-z0-9_]{0,62}$")

    @field_validator("idempotency_key")
    @classmethod
    def idempotency_key_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("idempotencyKey must not be blank")
        return value


class VideoReviewRequest(CamelModel):
    reviewer: str = Field(min_length=1, max_length=160)
    decision: Literal["select", "reject"]
    note: str = Field(min_length=2, max_length=2_000)

    @field_validator("reviewer", "note")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("review text must not be blank")
        return value
