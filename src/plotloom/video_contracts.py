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
    # The active trusted adapter fills its observed defaults. New H3 work pins
    # `reject_mismatch` unless the author records one explicit gateway-owned
    # input-frame choice; the broader literals remain readable for historical
    # snapshots and direct gateway recovery only.
    requested_duration_seconds: Literal[5, 8] | None = None
    playback_intent: Literal["source_exact", "segment_required"] = "source_exact"
    resolution: str | None = Field(default=None, min_length=3, max_length=32)
    audio: Literal[True] | None = None
    aspect_policy: Literal["cover_center_crop", "contain_pad", "reject_mismatch"] | None = None
    # This is an explicit author decision for a mismatched H3 keyframe. It is
    # deliberately narrower than a general validation bypass: output-profile,
    # provenance, currentness, and selection checks still apply.
    allow_letterbox: bool = False
    # This records consent for the gateway, and only the gateway, to make a
    # deterministic centered crop from the still whose original bytes and
    # reviewed binding remain frozen in the video snapshot.
    allow_center_crop: bool = False
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
    expected_selection_revision: int = Field(ge=0)

    @field_validator("reviewer", "note")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("review text must not be blank")
        return value


class VideoDiscardRequest(CamelModel):
    expected_selection_revision: int = Field(ge=0)


class VideoDiscardUnselectedRequest(VideoDiscardRequest):
    shot_id: str = Field(min_length=1, max_length=100)
    video_job_ids: list[str] = Field(min_length=1, max_length=100)


class VideoSegmentPrepareRequest(CamelModel):
    in_frame: int = Field(ge=0)
    out_frame: int = Field(ge=1)
    expected_selection_revision: int = Field(ge=0)


class VideoSegmentSelectRequest(CamelModel):
    reviewer: str = Field(min_length=1, max_length=160)
    note: str = Field(min_length=2, max_length=2_000)
    expected_selection_revision: int = Field(ge=0)
