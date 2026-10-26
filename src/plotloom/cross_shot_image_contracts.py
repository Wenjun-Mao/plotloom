"""Explicit target use, separate from immutable image origin (ADR 0189)."""
from typing import Literal

from pydantic import Field

from plotloom.domain_base import CamelModel


class ReviewedFrameSource(CamelModel):
    binding_id: str = Field(min_length=1, max_length=36)
    binding_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    visual_intent_id: str = Field(min_length=1, max_length=36)
    visual_intent_revision: int = Field(ge=1)
    intent_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    asset_id: str = Field(min_length=1, max_length=36)
    original_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_shot_id: str = Field(min_length=1, max_length=100)
    origin_shot_id: str | None
    origin_job_id: str | None
    origin_candidate_id: str | None
    origin_request_hash: str | None
    origin_delivery_hash: str | None


class TargetUseContext(CamelModel):
    approval_id: str = Field(min_length=1, max_length=36)
    storyboard_entity_revision_id: str = Field(min_length=1, max_length=36)
    storyboard_revision: int = Field(ge=1)
    presentation_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class CrossShotTargetUse(CamelModel):
    kind: Literal["cross_shot_initial_keyframe"]
    target_shot_id: str = Field(min_length=1, max_length=100)
    source: ReviewedFrameSource
    target_context: TargetUseContext


def intent_stream(intent: dict) -> tuple[str | None, str | None]:
    use = intent.get("targetUse")
    return intent.get("role"), use.get("targetShotId") if isinstance(use, dict) else None
