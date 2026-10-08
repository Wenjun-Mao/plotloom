"""Public, review-only contract for the F5 source-to-canonical bridge."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .domain import CamelModel
from .production_presentation import ProductionPresentation

ProductionBridgeStatus = Literal["missing", "ready", "accepted", "stale"]


class CanonicalReplacementHead(CamelModel):
    revision: int = Field(ge=0)
    entity_revision_id: str | None
    content_hash: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["missing", "ready", "stale"]


class ProductionBridgeReplacementTarget(CamelModel):
    installed_admission_id: str | None
    bible: CanonicalReplacementHead
    graph: CanonicalReplacementHead
    scene_beats: CanonicalReplacementHead
    storyboard: CanonicalReplacementHead


class ProductionBridgePrepareRequest(CamelModel):
    expected_proposal_revision: int = Field(ge=0)
    expected_proposal_content_hash: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    expected_source_inputs_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    replacement_target: ProductionBridgeReplacementTarget


class BridgePrepareAvailable(CamelModel):
    status: Literal["available"] = "available"
    request: ProductionBridgePrepareRequest


class BridgePrepareUnavailable(CamelModel):
    status: Literal["unavailable"] = "unavailable"
    reason: str


class InstalledProduction(CamelModel):
    admission_id: str
    proposal_revision: int
    proposal_content_hash: str
    inputs: dict[str, Any]
    installed_stage_revisions: dict[str, int]
    status: Literal["current", "outdated"]
    stale_reasons: list[str]
    cuts: list[dict[str, Any]]
    scenes: list[dict[str, Any]]
    runtime_choice: dict[str, Any] | None


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

    suggestion_origin: Literal["none", "model_inference.v1", "codex_native.v1"]
    review_state: Literal["pending", "model_suggested", "author_saved"]
    entries: list[ProductionBridgeIntentEntry] = Field(min_length=1)
    provenance: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_review_binding(self) -> ProductionBridgeIntentPackage:
        has_model = self.suggestion_origin in {"model_inference.v1", "codex_native.v1"}
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
    replacement_target: ProductionBridgeReplacementTarget
    intent_package: ProductionBridgeIntentPackage
    presentation: ProductionPresentation
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
    intent_job: ProductionBridgeIntentJob | None = None
    simulation_label: str | None = None
    installation: InstalledProduction | None
    preparation: BridgePrepareAvailable | BridgePrepareUnavailable


class ProductionBridgeIntentJob(CamelModel):
    id: str
    transport: Literal["text_api", "codex_native"]
    status: Literal["queued", "dispatched", "ready", "stale", "failed", "cancelled", "outcome_unknown"]
    proposal_revision: int
    proposal_content_hash: str
    profile_id: str | None
    profile_version: int | None
    prompt_version: str
    created_at: datetime
    updated_at: datetime
    error_code: str | None = None
    error_message: str | None = None
    result_proposal_revision: int | None = None
    provider_request_id: str | None = None
    response_hash: str | None = None

    @model_validator(mode="after")
    def transport_owns_profile(self):
        if self.transport == "codex_native" and (self.profile_id is not None or self.profile_version is not None):
            raise ValueError("native intent cannot claim an API profile")
        if self.transport == "text_api" and (self.profile_id is None or self.profile_version is None):
            raise ValueError("API intent requires its frozen profile identity")
        return self


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
