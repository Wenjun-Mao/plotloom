"""Public, review-only contract for the F5 source-to-canonical bridge."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

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
    method: Literal["pending_inference.v1", "model_inference.v1", "author_reviewed.v1", "source_excerpt_seed.v1"]
    suggested_text: str = Field(min_length=1)
    text: str


class ProductionBridgeIntentPackage(CamelModel):
    """One whole-package review binding, never independent questions."""

    method: Literal["pending_inference.v1", "model_inference.v1", "author_reviewed.v1", "source_excerpt_seed.v1"]
    entries: list[ProductionBridgeIntentEntry] = Field(min_length=1)
    provenance: dict[str, Any] | None = None


class ProductionBridgeProposal(CamelModel):
    revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    inputs: dict[str, Any]
    intent_package: ProductionBridgeIntentPackage
    scenes: list[dict[str, Any]]
    cuts: list[dict[str, Any]]
    conflicts: list[ProductionBridgeConflict] = Field(default_factory=list)
    installable: bool
    prepared_at: datetime


class ProductionBridgeState(CamelModel):
    proposal: ProductionBridgeProposal | None = None
    status: ProductionBridgeStatus
    stale_reasons: list[str] = Field(default_factory=list)
    installed_stage_revisions: dict[str, int] | None = None
    intent_job: "ProductionBridgeIntentJob | None" = None


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
