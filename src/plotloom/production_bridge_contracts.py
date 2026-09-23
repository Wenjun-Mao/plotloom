"""Public, review-only contract for the F5 source-to-canonical bridge."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .domain import CamelModel


ProductionBridgeStatus = Literal["missing", "ready", "accepted", "stale"]


class ProductionBridgeConflict(CamelModel):
    code: str
    message: str
    section_id: str | None = None
    episode: int | None = None
    scene_index: int | None = None


class ProductionBridgeIntentEntry(CamelModel):
    """Trusted target and source evidence with separately reviewable wording."""

    id: str
    target_kind: Literal["scene_objective", "beat_purpose"]
    target_id: str
    source_coordinates: dict[str, Any]
    source_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_excerpt: str = Field(min_length=1)
    suggested_text: str | None = None
    text: str


class ProductionBridgeIntentPackage(CamelModel):
    """One whole-package review binding, never independent questions."""

    suggestion_origin: Literal["none", "model_inference.v1"]
    review_state: Literal["pending", "model_suggested", "author_saved"]
    entries: list[ProductionBridgeIntentEntry] = Field(min_length=1)
    provenance: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_review_binding(self) -> "ProductionBridgeIntentPackage":
        has_model = self.suggestion_origin == "model_inference.v1"
        if has_model != (self.provenance is not None):
            raise ValueError("model suggestion origin and provenance must agree")
        if has_model and any(not entry.suggested_text or not entry.suggested_text.strip() for entry in self.entries):
            raise ValueError("model suggestion must cover every intent entry")
        if not has_model and any(entry.suggested_text is not None for entry in self.entries):
            raise ValueError("source evidence cannot be stored as a model suggestion")
        if self.review_state == "model_suggested" and not has_model:
            raise ValueError("model-suggested review requires model origin")
        if self.review_state == "model_suggested" and any(entry.text != entry.suggested_text for entry in self.entries):
            raise ValueError("unreviewed model text must match its original suggestion")
        if self.review_state == "pending":
            if any(entry.text.strip() for entry in self.entries):
                raise ValueError("pending intent text must be blank")
        elif any(not entry.text.strip() for entry in self.entries):
            raise ValueError("reviewed intent text must cover every entry")
        return self


class ProductionBridgeProposal(CamelModel):
    revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    inputs: dict[str, Any]
    intent_package: ProductionBridgeIntentPackage
    scenes: list[dict[str, Any]]
    cuts: list[dict[str, Any]]
    conflicts: list[ProductionBridgeConflict] = Field(default_factory=list)
    advisories: list[ProductionBridgeConflict] = Field(default_factory=list)
    installable: bool
    prepared_at: datetime


class ProductionBridgeState(CamelModel):
    proposal: ProductionBridgeProposal | None = None
    status: ProductionBridgeStatus
    stale_reasons: list[str] = Field(default_factory=list)
    installed_stage_revisions: dict[str, int] | None = None
    installed_storyboard_current: bool = False
    intent_job: "ProductionBridgeIntentJob | None" = None
    simulation_label: str | None = None


class ProductionBridgeIntentJob(CamelModel):
    id: str
    status: Literal["queued", "dispatched", "ready", "stale", "failed", "cancelled", "outcome_unknown"]
    proposal_revision: int
    proposal_content_hash: str
    profile_id: str
    profile_version: int
    prompt_version: str
    created_at: datetime
    updated_at: datetime
    error_code: str | None = None
    error_message: str | None = None
    result_proposal_revision: int | None = None
    provider_request_id: str | None = None
    response_hash: str | None = None


class ProductionBridgeIntentGenerateRequest(CamelModel):
    expected_proposal_revision: int = Field(ge=1)
    expected_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    provider_profile_id: str | None = None


class ProductionBridgeAcceptRequest(CamelModel):
    expected_proposal_revision: int = Field(ge=1)
    expected_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class ProductionBridgeIntentTextUpdate(CamelModel):
    id: str
    text: str = Field(min_length=1)


class ProductionBridgeIntentUpdateRequest(CamelModel):
    expected_proposal_revision: int = Field(ge=1)
    expected_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    entries: list[ProductionBridgeIntentTextUpdate] = Field(min_length=1)
