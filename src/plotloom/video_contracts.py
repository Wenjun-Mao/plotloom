"""P2 Wan video-job wire contracts, kept outside the canonical story model.

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
    requested_duration_seconds: Literal[5] = 5
    resolution: Literal["720p"] = "720p"
    audio: Literal[True] = True

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

