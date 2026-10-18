"""Explicit whole-pack judgments, distinct from authored observation prose."""
from typing import Literal

from pydantic import Field, model_validator

from .domain import CamelModel
from .managed_media import VisualIntentInput
from .source_endorsed_intent import SourceEndorsedIntent

ASSERTION_VERSION = "whole-pack-material.v1"


class SavedIntentContext(CamelModel):
    kind: Literal["storyboard", "reviewed_intent"]
    source_id: str
    revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    shot_id: str
    intent: SourceEndorsedIntent | VisualIntentInput


class BulkIdentityJudgment(CamelModel):
    character_id: str = Field(min_length=1, max_length=128)
    judgment: Literal["pass", "fail", "unassessable"]
    comment: str | None = Field(default=None, max_length=2000, exclude_if=lambda value: value is None)
    production_decision: Literal["hold", "authorize"] | None = Field(default=None, exclude_if=lambda value: value is None)
    uncertainty_reason: str | None = Field(default=None, max_length=2000, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def explicit_exception(self):
        if self.judgment == "unassessable":
            if self.production_decision is None or not self.uncertainty_reason or not self.uncertainty_reason.strip():
                raise ValueError("unassessable identity requires a separate decision and reason")
        elif self.production_decision is not None or self.uncertainty_reason is not None:
            raise ValueError("uncertainty fields belong only to unassessable identity")
        if self.judgment == "fail" and (not self.comment or not self.comment.strip()):
            raise ValueError("identity failure requires an explanation")
        return self


class BulkFrameObservation(CamelModel):
    shot_id: str
    asset_id: str
    intent_context: SavedIntentContext
    intent: SourceEndorsedIntent | VisualIntentInput
    compatibility: Literal["pass", "fail", "hold"]
    comment: str | None = Field(default=None, max_length=2000, exclude_if=lambda value: value is None)
    comparisons: list[BulkIdentityJudgment] = Field(max_length=8)

    @property
    def compatibility_note(self):
        # Comments remain unchanged in the typed receipt. This legacy column is
        # always absent for bulk judgments, so no comment can impersonate prose.
        return ""

    @model_validator(mode="after")
    def exact_frame(self):
        if self.intent.role != "shot_keyframe" or self.intent_context.shot_id != self.shot_id:
            raise ValueError("bulk intent must target this shot keyframe")
        ids = [item.character_id for item in self.comparisons]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate visible-character judgment")
        if self.compatibility != "pass" and (not self.comment or not self.comment.strip()):
            raise ValueError("flagged frame requires an explanation")
        return self


class BulkComparisonBasis(CamelModel):
    version: Literal["whole-pack-material.v1"] = ASSERTION_VERSION
    receipt_id: str
    bundle_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    shot_id: str


class StoredBulkIdentityJudgment(BulkIdentityJudgment):
    confirmation: BulkComparisonBasis


def stored_bulk_comparisons(observation, receipt_id, bundle_hash):
    basis = BulkComparisonBasis(receipt_id=receipt_id, bundle_hash=bundle_hash, shot_id=observation.shot_id)
    return [StoredBulkIdentityJudgment(**item.model_dump(), confirmation=basis).model_dump(mode="json", by_alias=True, exclude_none=True)
        for item in observation.comparisons]
