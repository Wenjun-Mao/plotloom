"""Typed pre-video authority, frozen policy and immutable decision evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, model_validator

from .art_style import ArtRenderStyle
from .cast_style import CastRenderStyle
from .domain import CamelModel, contains_secret_setting, contains_secret_value

POLICY_VERSION = "plotloom.pre-video.v1"
HASH = r"^[a-f0-9]{64}$"
RunState = Literal["running", "waiting", "paused", "cancelled", "stale", "blocked", "awaiting_review", "handed_off", "taken_over"]


class OperationScope(str, Enum):
    SOURCE = "source_adoption"
    TEXT = "text_adoption"
    INSTALL = "production_installation"
    IMAGE = "image_generation"
    SELECT = "provisional_selection"
    EVIDENCE = "receipt_reconciliation"
    HANDOFF = "human_handoff"


@dataclass(frozen=True)
class CommandAuthority:
    """Server-only command identity; never parsed from a browser request."""
    run_id: str
    claim: str
    scope: OperationScope


class LaunchPolicy(CamelModel):
    version: Literal[POLICY_VERSION] = POLICY_VERSION
    render_style: CastRenderStyle
    art_render_style: ArtRenderStyle
    max_images: int = Field(default=80, ge=1, le=256)
    max_jobs: int = Field(default=96, ge=9, le=288)
    image_width: int = Field(ge=64, le=4096)
    image_height: int = Field(ge=64, le=4096)
    specialist_bindings: dict[Literal["text", "image"], str]
    execution_pins: dict[str, dict[str, str]]
    brief: dict[str, Any]

    @model_validator(mode="after")
    def validate_frozen_authority(self):
        if set(self.specialist_bindings) != {"text", "image"} or len(set(self.specialist_bindings.values())) != 2:
            raise ValueError("two distinct native specialist bindings are required")
        payload = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise ValueError("autopilot policy cannot contain credentials")
        return self


class LaunchRequest(CamelModel):
    expected_brief_revision: int = Field(ge=1)
    render_style: CastRenderStyle
    art_render_style: ArtRenderStyle
    max_images: int = Field(default=80, ge=1, le=256)
    max_jobs: int = Field(default=96, ge=9, le=288)


class CheckpointEvidence(CamelModel):
    owner: str
    subject_id: str
    job_id: str | None = None
    request_hash: str | None = Field(default=None, pattern=HASH)
    execution_pin: dict[str, str] | None = None
    delivery_hash: str | None = Field(default=None, pattern=HASH)
    result: dict[str, Any] = Field(default_factory=dict)


class MachineDecision(CamelModel):
    actor: Literal["machine"] = "machine"
    scope: OperationScope
    policy_hash: str = Field(pattern=HASH)
    subject: dict[str, Any]
    upstream_hash: str = Field(pattern=HASH)
    evidence: CheckpointEvidence
    selected_assets: list[dict[str, str]] = Field(default_factory=list)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def no_human_scope(self):
        if self.scope == OperationScope.HANDOFF:
            raise ValueError("machine authority cannot grant human handoff")
        return self


class ProvisionalFrame(CamelModel):
    shot_id: str
    scene_id: str
    job_id: str
    asset_id: str
    original_hash: str = Field(pattern=HASH)
    storyboard_revision: int = Field(ge=1)
    storyboard_hash: str = Field(pattern=HASH)
    request_hash: str = Field(pattern=HASH)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    character_identity: list[dict[str, Any]]


class RunView(CamelModel):
    id: str
    project_id: str
    revision: int
    state: RunState
    phase: str
    policy: LaunchPolicy
    blocker: dict[str, str] | None
    checkpoints: list[dict[str, Any]]
    frames: list[ProvisionalFrame]
    bundle: dict[str, Any] | None
    bundle_hash: str | None
    handoff: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class RunControlRequest(CamelModel):
    expected_revision: int = Field(ge=1)
    action: Literal["pause", "resume", "cancel", "takeover"]
