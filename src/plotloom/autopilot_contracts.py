"""Typed pre-video authority, frozen policy and immutable decision evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .art_style import ArtRenderStyle
from .cast_style import CastRenderStyle
from .codex_exec_contracts import CodexExecProfile, ExecutorBinding
from .domain import CamelModel, contains_secret_setting, contains_secret_value
from .geometry_preparation import geometry_policy
from .geometry_preparation_contracts import GeometryPolicy, GeometryPreparation

POLICY_VERSION = "plotloom.pre-video.v4"
PREVIOUS_POLICY_VERSION = "plotloom.pre-video.v3"
RETAINED_POLICY_VERSIONS = {"plotloom.pre-video.v1", "plotloom.pre-video.v2", PREVIOUS_POLICY_VERSION, POLICY_VERSION}
HASH = r"^[a-f0-9]{64}$"
RunState = Literal["running", "waiting", "paused", "cancelled", "stale", "blocked", "awaiting_review", "handed_off", "taken_over"]


class OperationScope(str, Enum):
    SOURCE = "source_adoption"
    TEXT = "text_adoption"
    INSTALL = "production_installation"
    IMAGE = "image_generation"
    GEOMETRY = "geometry_preparation"
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
    version: Literal["plotloom.pre-video.v1", "plotloom.pre-video.v2", PREVIOUS_POLICY_VERSION, POLICY_VERSION] = PREVIOUS_POLICY_VERSION
    geometry_preparation: GeometryPolicy | None = Field(default_factory=geometry_policy, exclude_if=lambda value: value is None)
    # Older retained policies had no style-authority member. Keep omission
    # stable when those rows are decoded and re-encoded.
    style_authority: Literal["preset", "brief"] | None = Field(default="preset", exclude_if=lambda value: value is None)
    render_style: CastRenderStyle | None = None
    art_render_style: ArtRenderStyle | None = None
    max_images: int = Field(default=80, ge=1, le=256)
    max_jobs: int = Field(default=96, ge=9, le=288)
    early_reference_limit: int | None = Field(default=None, ge=0, le=4, strict=True, exclude_if=lambda value: value is None)
    image_width: int = Field(ge=64, le=4096)
    image_height: int = Field(ge=64, le=4096)
    code_revision: str = Field(pattern=r"^[a-f0-9]{7,64}$")
    specialist_bindings: dict[Literal["text", "image"], str] | None = Field(default=None, exclude_if=lambda value: value is None)
    executor_binding: ExecutorBinding | None = Field(default=None, exclude_if=lambda value: value is None)
    execution_pins: dict[str, dict[str, str]]
    brief: dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def retained_policy(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            if value.get("version") == POLICY_VERSION and "styleAuthority" not in value and "style_authority" not in value:
                value["styleAuthority"] = "preset"
            elif value.get("version") in {"plotloom.pre-video.v1", "plotloom.pre-video.v2", PREVIOUS_POLICY_VERSION} and "styleAuthority" not in value and "style_authority" not in value:
                value["styleAuthority"] = None
            if value.get("version") == "plotloom.pre-video.v1":
                return {key: item for key, item in value.items() if key != "geometry_preparation"} | {"geometryPreparation": value.get("geometryPreparation", value.get("geometry_preparation"))}
        return value

    @property
    def effective_style_authority(self):
        return self.style_authority or "preset"

    @model_validator(mode="after")
    def validate_frozen_authority(self):
        if self.early_reference_limit is not None and (
            self.version != POLICY_VERSION or self.executor_binding is None
            or self.executor_binding.contract_version != "plotloom.codex-exec.v8"
        ):
            raise ValueError("early reference permission requires the current bounded CLI pool")
        if (self.version in {"plotloom.pre-video.v2", PREVIOUS_POLICY_VERSION, POLICY_VERSION}) != (self.geometry_preparation is not None):
            raise ValueError("geometry preparation permission belongs only to policy v2, v3 or v4")
        if self.version not in {PREVIOUS_POLICY_VERSION, POLICY_VERSION} and self.effective_style_authority != "preset":
            raise ValueError("retained autopilot policies must keep their original preset authority")
        if self.effective_style_authority == "brief" and (self.render_style is not None or self.art_render_style is not None):
            raise ValueError("Brief style authority cannot carry independent render presets")
        if self.effective_style_authority == "preset" and (self.render_style is None or self.art_render_style is None):
            raise ValueError("preset style authority requires both frozen render styles")
        if self.version == POLICY_VERSION:
            if self.specialist_bindings is not None or not isinstance(self.executor_binding, CodexExecProfile):
                raise ValueError("new pre-video launches require one frozen Codex Exec profile")
        else:
            if self.executor_binding is not None or self.specialist_bindings is None:
                raise ValueError("retained specialist-chat policies require their original bindings")
            if set(self.specialist_bindings) != {"text", "image"} or len(set(self.specialist_bindings.values())) != 2:
                raise ValueError("two distinct native specialist bindings are required")
        payload = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise ValueError("autopilot policy cannot contain credentials")
        return self


class LaunchRequest(CamelModel):
    expected_brief_revision: int = Field(ge=1)
    style_authority: Literal["preset", "brief"] = "preset"
    render_style: CastRenderStyle | None = None
    art_render_style: ArtRenderStyle | None = None
    max_images: int = Field(default=80, ge=1, le=256)
    max_jobs: int = Field(default=96, ge=9, le=288)


class CheckpointEvidence(CamelModel):
    geometry_preparation: GeometryPreparation | None = Field(default=None, exclude_if=lambda value: value is None)
    owner: str
    subject_id: str
    job_id: str | None = None
    request_hash: str | None = Field(default=None, pattern=HASH)
    execution_pin: dict[str, str] | None = None
    delivery_hash: str | None = Field(default=None, pattern=HASH)
    executor_attempt_id: UUID | None = Field(default=None, exclude_if=lambda value: value is None)
    executor_receipt_hash: str | None = Field(default=None, pattern=HASH, exclude_if=lambda value: value is None)
    result: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def executor_receipt_requires_attempt(self):
        if self.executor_receipt_hash is not None and self.executor_attempt_id is None:
            raise ValueError("CLI receipt evidence requires its exact project attempt")
        return self


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
    geometry_preparation: GeometryPreparation | None = Field(default=None, exclude_if=lambda value: value is None)
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


class RunActivity(CamelModel):
    """Public job progress; process, session and private storage facts stay host-owned."""
    operation_key: str
    owner: str
    subject_id: str
    job_id: str
    domain: Literal["text", "image"]
    state: Literal["waiting", "queued", "generating", "validating", "unknown", "cancelling", "delivered", "adopted", "failed"]


class RunView(CamelModel):
    predecessor_run_id: str | None = None
    lifetime_jobs: int = 0
    lifetime_images: int = 0
    id: str
    project_id: str
    revision: int
    state: RunState
    phase: str
    policy: LaunchPolicy
    blocker: dict[str, str] | None
    checkpoints: list[dict[str, Any]]
    activities: list[RunActivity] = Field(default_factory=list)
    material_current: bool = True
    frames: list[ProvisionalFrame]
    bundle: dict[str, Any] | None
    bundle_hash: str | None
    handoff: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class RunControlRequest(CamelModel):
    expected_revision: int = Field(ge=1)
    action: Literal["pause", "resume", "cancel", "takeover"]


class ContinueRequest(LaunchRequest):
    expected_run_id: str = Field(min_length=1)
    expected_run_revision: int = Field(ge=1)
    expected_material_closure: str = Field(pattern=HASH)
