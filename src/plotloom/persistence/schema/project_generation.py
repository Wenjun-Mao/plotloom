from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

from ...domain import WorkUnitStatus

class GenerationRunRow(Base):
    __tablename__ = "v2_generation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    repair_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    repair_source: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    work_unit_repair_scope_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    provider_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    requested_stages: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    canonical_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    legacy_unsealed: Mapped[bool] = mapped_column(nullable=False, default=True)
    result_revision_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failed_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GenerationAttemptRow(Base):
    __tablename__ = "v2_generation_attempts"
    __table_args__ = (
        # Work-unit attempts have an identity-local sequence.  SQLite treats
        # NULL values as distinct, so legacy attempts (which have no unit) do
        # not collide with this new durable contract.
        UniqueConstraint("work_unit_id", "attempt_number"),
        # Keep the legacy create_attempt(run, stage) API deterministic without
        # imposing its stage-wide numbering on independent work units.
        Index(
            "uq_v2_generation_attempts_legacy_run_stage_attempt_number",
            "run_id",
            "stage",
            "attempt_number",
            unique=True,
            sqlite_where=text("work_unit_id IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), index=True)
    work_unit_id: Mapped[str | None] = mapped_column(
        ForeignKey("v2_generation_work_units.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="primary")
    source_attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("v2_generation_attempts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_persisted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    outcome_unknown: Mapped[bool] = mapped_column(nullable=False, default=False)
    outcome_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArtifactRow(Base):
    __tablename__ = "v2_artifacts"
    __table_args__ = (
        # Historical, legacy artifact bags may contain repeated kinds.  New
        # work-unit producer attempts cannot: their seal evidence is exactly
        # one artifact of each required kind.
        Index(
            "uq_v2_artifacts_work_unit_attempt_kind",
            "attempt_id",
            "kind",
            unique=True,
            sqlite_where=text("work_unit_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("v2_generation_attempts.id", ondelete="RESTRICT"), nullable=True
    )
    work_unit_id: Mapped[str | None] = mapped_column(
        ForeignKey("v2_generation_work_units.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    source_artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[Any] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GenerationPlanRow(Base):
    __tablename__ = "v2_generation_plans"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), primary_key=True
    )
    plan_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StagePlanRow(Base):
    __tablename__ = "v2_generation_stage_plans"
    __table_args__ = (
        UniqueConstraint("run_id", "stage"),
        UniqueConstraint("run_id", "stage_plan_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), index=True
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    generation_plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dependency_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GenerationWorkUnitRow(Base):
    __tablename__ = "v2_generation_work_units"
    __table_args__ = (UniqueConstraint("stage_plan_id", "sequence"),)

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), index=True
    )
    stage_plan_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_stage_plans.id", ondelete="CASCADE"), index=True
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    selector: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    generation_plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dependency_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_dependency_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    budget: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    context_window_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=WorkUnitStatus.QUEUED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SealedStageAggregateRow(Base):
    __tablename__ = "v2_sealed_stage_aggregates"
    __table_args__ = (UniqueConstraint("stage_plan_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), index=True
    )
    stage_plan_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_stage_plans.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkUnitRepairScopeRow(Base):
    """Immutable exact-repair boundary, separate from legacy stage repair."""

    __tablename__ = "v2_generation_work_unit_repair_scopes"

    child_run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), primary_key=True
    )
    parent_run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    target_work_unit_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_work_units.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FragmentReuseBindingRow(Base):
    """A child-owned, audited mapping to one immutable parent candidate."""

    __tablename__ = "v2_generation_fragment_reuse_bindings"
    __table_args__ = (UniqueConstraint("child_work_unit_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    child_run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_stage_plan_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_stage_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_work_unit_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_work_units.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="RESTRICT"), nullable=False
    )
    source_work_unit_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_work_units.id", ondelete="RESTRICT"), nullable=False
    )
    source_stage_plan_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_stage_plans.id", ondelete="RESTRICT"), nullable=False
    )
    source_candidate_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("v2_artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    binding_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    binding: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkUnitRepairIdempotencyRow(Base):
    __tablename__ = "v2_generation_work_unit_repair_idempotency"

    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="RESTRICT"), nullable=False
    )
    target_work_unit_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_work_units.id", ondelete="RESTRICT"), nullable=False
    )
    child_run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MediaTaskRow(Base):
    __tablename__ = "v2_media_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), index=True)
    shot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    storyboard_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    derived_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_components: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    public_settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    provider_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    output_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)



class StoryGraphTopologyRow(Base):
    __tablename__ = "v2_generation_story_graph_topologies"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), primary_key=True
    )
    generation_plan_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    topology_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    topology: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# This intentionally names the project-owned port instead of using
# ``Base.metadata`` wholesale.  Profiles, profile selection, global accounting,
# and video-pilot accounting remain installation-owned.  Still/image evidence,
# review decisions, and the manual handoff lifecycle are project facts and
# therefore travel with the canonical project database.
