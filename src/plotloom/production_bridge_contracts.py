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


class ProductionBridgeProposal(CamelModel):
    revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    inputs: dict[str, Any]
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
