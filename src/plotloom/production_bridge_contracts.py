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
    """One author-reviewable canonical value seeded from exact source text."""

    id: str
    target_kind: Literal["scene_objective", "beat_purpose"]
    target_id: str
    source_coordinates: dict[str, Any]
    source_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    method: Literal["source_excerpt_seed.v1"]
    suggested_text: str = Field(min_length=1)
    text: str = Field(min_length=1)


class ProductionBridgeIntentPackage(CamelModel):
    """A single source-excerpt review package, never independent questions."""

    method: Literal["source_excerpt_seed.v1"]
    entries: list[ProductionBridgeIntentEntry] = Field(min_length=1)


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
