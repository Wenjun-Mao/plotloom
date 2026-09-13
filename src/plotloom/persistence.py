from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Literal

from sqlalchemy import (
    Boolean,
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    event,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from .domain import (
    PUBLIC_PROVIDER_SETTING_FIELDS,
    STAGE_ORDER,
    TERMINAL_MEDIA_TASK_STATUSES,
    TERMINAL_RUN_STATUSES,
    TERMINAL_WORK_UNIT_STATUSES,
    Artifact,
    AuthoringDraft,
    AuthoringDraftScope,
    ImageDirectionDraftPayload,
    ArtifactKind,
    AttemptStatus,
    CanonicalSnapshot,
    DialogueTimingProfile,
    EntityRevision,
    FragmentReuseBinding,
    FragmentReuseKind,
    FrozenFragmentReuseSource,
    GateEvaluation,
    GateEvidence,
    GateResult,
    GenerationAttempt,
    GenerationAttemptKind,
    GenerationPlanTrace,
    GenerationRun,
    GenerationWorkUnitTrace,
    InitialStage,
    MediaKind,
    MediaPromptContext,
    MediaTask,
    MediaTaskStatus,
    Project,
    ProjectBrief,
    ProjectCreation,
    ProjectDuplicateResult,
    ProjectLifecycleStatus,
    ProjectSummary,
    LatestRunSummary,
    ProviderSettings,
    RepairSource,
    RunProgress,
    RunProgressActions,
    RunProgressAttempt,
    RunProgressStage,
    RunProgressUnit,
    RunKind,
    RunExecutionTrace,
    RunStatus,
    RunTrace,
    StageEnvelope,
    StageHead,
    StageName,
    StagePayload,
    StageStatus,
    StartupRecoveryPlan,
    StoryBible,
    Storyboard,
    StoryGraphTopologyTrace,
    SealedStageAggregateTrace,
    StagePlanTrace,
    WorkUnitFailureDisposition,
    WorkUnitRepairEligibility,
    WorkUnitRepairRunCreation,
    WorkUnitRepairScope,
    WorkUnitStatus,
    VisualIntentDraftPayload,
    downstream_stages,
    stage_payload_model,
    upstream_stages,
    new_id,
    validate_initial_stage_prefix,
    utc_now,
    contains_secret_setting,
    contains_secret_value,
    is_secret_setting_name,
    validate_public_provider_snapshot,
)
from .generation.aggregation import aggregate_stage_fragments
from .generation.dialogue_capacity import DIALOGUE_CAPACITY_POLICY_VERSION
from .generation.fragments import (
    SceneBeatsFragment,
    StoryBibleFragment,
    StoryGraphFragment,
    StoryboardFragment,
)
from .generation.planning import (
    DEFAULT_STAGE_BUDGETS,
    GenerationPlan,
    PLANNING_POLICY_VERSION,
    PlanningError,
    StageBudget,
    StagePlan,
    create_generation_plan,
    plan_stage,
)
from .generation.scene_timing_allocation import (
    SCENE_TIMING_ALLOCATION_VERSION,
    SceneTimingAllocation,
)
from .join_state_values import JOIN_STATE_VALUE_CONTRACT_VERSION
from .keyframe_preparation import has_matching_aspect
from .video_provider import VideoProductionContract
from .generation.story_graph_topology import (
    StoryGraphTopology,
    plan_story_graph_topology,
)
from .generation.prompts import canonical_json
from .provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
    PROFILE_ID_PATTERN,
    PresetId,
    ProviderProfileSelection,
    StageMaxOutputTokens,
    TextProviderCapabilities,
    TextProviderProfile,
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
    V2ExtractionPolicy,
    execution_preset,
    is_v2_snapshot,
    is_v3_snapshot,
)
from .exceptions import (
    BootstrapContentionError,
    IdempotencyConflictError,
    InvalidTransitionError,
    KeyframeAspectMismatchError,
    LifecycleContentionError,
    NotFoundError,
    ProjectBusyError,
    ProjectManagedAssetsPresentError,
    ProductionPipelineNotReadyError,
    RepairEligibilityError,
    RevisionConflictError,
    StagePrerequisiteError,
    SchemaResetRequiredError,
)
from .image_job_contracts import ImageJobError
from .schema import SchemaMigrator, sqlite_database_path
from .validation import STORYBOARD_GATE_SET_VERSION, validate_stage_payload


LEGACY_STAGE_SCHEMA_VERSION = 1
CURRENT_STAGE_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class ApprovalDecision:
    """A read projection of one immutable human decision in the approval ledger."""

    id: str
    project_id: str
    entity_revision_id: str
    subject_type: str
    subject_id: str
    subject_revision: int
    content_hash: str
    canonical_input_revisions: tuple[tuple[StageName, int], ...]
    gate_set_version: str
    decision: str
    reviewer: str
    note: str | None
    created_at: datetime


@dataclass(frozen=True)
class ApprovalClosure:
    """Derived current applicability of an append-only approval decision."""

    decision: ApprovalDecision
    active: bool
    stale_reasons: tuple[str, ...]


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "v2_projects"
    __table_args__ = (
        Index(
            "ix_v2_projects_lifecycle_status_created_at_id",
            "lifecycle_status",
            "created_at",
            "id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lifecycle_status: Mapped[str] = mapped_column(String(16), nullable=False, default=ProjectLifecycleStatus.ACTIVE.value)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    brief: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectCreationIdempotencyRow(Base):
    __tablename__ = "v2_project_creation_idempotency"

    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectDuplicateIdempotencyRow(Base):
    __tablename__ = "v2_project_duplicate_idempotency"

    idempotency_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    copied_through: Mapped[str | None] = mapped_column(String(32), nullable=True)
    omitted_stages: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EntityRevisionRow(Base):
    __tablename__ = "v2_entity_revisions"
    __table_args__ = (UniqueConstraint("project_id", "stage", "revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    input_revisions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StageHeadRow(Base):
    __tablename__ = "v2_stage_heads"
    __table_args__ = (UniqueConstraint("project_id", "stage"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entity_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    input_revisions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    stale_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthoringDraftRow(Base):
    """Mutable, allowlisted editor state owned by exactly one project DB."""

    __tablename__ = "v2_authoring_drafts"
    __table_args__ = (UniqueConstraint("project_id", "editor_scope", "entity_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), index=True
    )
    editor_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(160), nullable=False)
    base_canonical_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    draft_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GateResultRow(Base):
    """An immutable evaluation result for one exact canonical revision."""

    __tablename__ = "v2_gate_results"
    __table_args__ = (
        UniqueConstraint("entity_revision_id", "gate_set_version", "gate_id"),
        UniqueConstraint("entity_revision_id", "gate_set_version", "sequence"),
        Index("ix_v2_gate_results_project_id", "project_id"),
        Index("ix_v2_gate_results_entity_revision_id", "entity_revision_id"),
    )

    id: Mapped[str] = mapped_column(String(256), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    entity_revision_id: Mapped[str] = mapped_column(
        ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluation_input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    gate_set_version: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    # Gate IDs include stable authoring IDs to make review paths readable.
    # They are intentionally unbounded text; the row primary key is a fixed
    # hash so database identity never depends on authored identifier length.
    gate_id: Mapped[str] = mapped_column(Text, nullable=False)
    gate_version: Mapped[str] = mapped_column(String(128), nullable=False)
    required: Mapped[bool] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_path: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApprovalDecisionRow(Base):
    """Append-only human approval ledger; current state is derived, never stored."""

    __tablename__ = "v2_approval_decisions"
    __table_args__ = (
        Index("ix_v2_approval_decisions_project_id_created_at", "project_id", "created_at"),
        Index("ix_v2_approval_decisions_entity_revision_id", "entity_revision_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    entity_revision_id: Mapped[str] = mapped_column(
        ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_input_revisions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    gate_set_version: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(256), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


class ManagedAssetRow(Base):
    """One project-scoped declaration over immutable imported bytes."""

    __tablename__ = "v2_managed_assets"
    __table_args__ = (Index("ix_v2_managed_assets_project_id_created_at", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    original_uri: Mapped[str] = mapped_column(Text, nullable=False)
    original_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    display_uri: Mapped[str] = mapped_column(Text, nullable=False)
    display_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(32), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ManagedAssetProvenanceRow(Base):
    """An immutable origin declaration, intentionally separate from byte identity."""

    __tablename__ = "v2_managed_asset_provenance"
    __table_args__ = (Index("ix_v2_managed_asset_provenance_asset_id", "asset_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    declaration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VisualIntentRow(Base):
    __tablename__ = "v2_visual_intents"
    __table_args__ = (Index("ix_v2_visual_intents_project_id_asset_id", "project_id", "asset_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    intent: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VisualSelectionStateRow(Base):
    __tablename__ = "v2_visual_selection_states"

    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewedShotBindingRow(Base):
    __tablename__ = "v2_reviewed_shot_bindings"
    __table_args__ = (
        Index("ix_v2_reviewed_shot_bindings_project_shot_revision", "project_id", "shot_id", "selection_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    visual_intent_id: Mapped[str | None] = mapped_column(ForeignKey("v2_visual_intents.id", ondelete="RESTRICT"), nullable=True)
    visual_intent_revision: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    storyboard_entity_revision_id: Mapped[str] = mapped_column(ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False)
    approval_id: Mapped[str] = mapped_column(ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False)
    shot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    scene_id: Mapped[str] = mapped_column(String(100), nullable=False)
    storyboard_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    selection_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    compatibility_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StillPreviewRow(Base):
    __tablename__ = "v2_still_previews"
    __table_args__ = (Index("ix_v2_still_previews_project_id_created_at", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    storyboard_entity_revision_id: Mapped[str] = mapped_column(ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False)
    approval_id: Mapped[str] = mapped_column(ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False)
    scene_id: Mapped[str] = mapped_column(String(100), nullable=False)
    selection_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# P2 intentionally has its own lifecycle.  These rows are not MediaTask rows:
# historical raw-Shot media submission remains disabled by MediaJobRunner.
class VideoPilotLedgerRow(Base):
    __tablename__ = "v2_video_pilot_ledger"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    limit_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VideoPilotLedgerEventRow(Base):
    __tablename__ = "v2_video_pilot_ledger_events"
    __table_args__ = (Index("ix_v2_video_pilot_ledger_events_ledger_created", "ledger_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ledger_id: Mapped[str] = mapped_column(ForeignKey("v2_video_pilot_ledger.id", ondelete="RESTRICT"), nullable=False)
    video_job_id: Mapped[str] = mapped_column(String(67), nullable=False)
    event: Mapped[str] = mapped_column(String(48), nullable=False)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VideoJobRow(Base):
    __tablename__ = "v2_video_jobs"
    __table_args__ = (
        UniqueConstraint("project_id", "idempotency_key", name="uq_v2_video_jobs_project_idempotency"),
        Index("ix_v2_video_jobs_project_created", "project_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(67), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_prediction_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    output_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VideoReviewRow(Base):
    __tablename__ = "v2_video_reviews"
    __table_args__ = (Index("ix_v2_video_reviews_job_created", "video_job_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_job_id: Mapped[str] = mapped_column(ForeignKey("v2_video_jobs.id", ondelete="RESTRICT"), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(160), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductionUnitRow(Base):
    """A single-shot approved projection frozen for P1 image work."""

    __tablename__ = "v2_production_units"
    __table_args__ = (Index("ix_v2_production_units_project_id_created_at", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    approval_id: Mapped[str] = mapped_column(ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False)
    storyboard_entity_revision_id: Mapped[str] = mapped_column(ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False)
    shot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    scene_id: Mapped[str] = mapped_column(String(100), nullable=False)
    storyboard_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ImageJobRow(Base):
    """One immutable manual assignment and its current applicability state."""

    __tablename__ = "v2_image_jobs"
    __table_args__ = (Index("ix_v2_image_jobs_project_id_created_at", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(67), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    production_unit_id: Mapped[str] = mapped_column(ForeignKey("v2_production_units.id", ondelete="RESTRICT"), nullable=False)
    parent_job_id: Mapped[str | None] = mapped_column(ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=True)
    parent_candidate_asset_id: Mapped[str | None] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ImageJobDeliveryRow(Base):
    """Immutable reconciliation evidence, including rejected/late packages."""

    __tablename__ = "v2_image_job_deliveries"
    __table_args__ = (
        UniqueConstraint("job_id", "delivery_id", name="uq_v2_image_job_delivery_identity"),
        Index("ix_v2_image_job_deliveries_job_id_created_at", "job_id", "created_at"),
        Index(
            "uq_v2_image_job_final_delivery",
            "job_id",
            unique=True,
            sqlite_where=text("delivery_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    diagnostic_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ImageJobCandidateRow(Base):
    """Link a managed original to the exact manual image delivery that produced it."""

    __tablename__ = "v2_image_job_candidates"
    __table_args__ = (
        UniqueConstraint("delivery_id", "asset_id", name="uq_v2_image_job_candidate_delivery_asset"),
        Index("ix_v2_image_job_candidates_job_id_created_at", "job_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("v2_image_jobs.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str] = mapped_column(ForeignKey("v2_image_job_deliveries.id", ondelete="RESTRICT"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    output_filename: Mapped[str] = mapped_column(String(180), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterReferenceStateRow(Base):
    """The mutable pointer/revision over immutable reference decisions."""

    __tablename__ = "v2_character_reference_states"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterReferenceDecisionRow(Base):
    """An append-only asset/hash/context reference decision for one character."""

    __tablename__ = "v2_character_reference_decisions"
    __table_args__ = (
        UniqueConstraint("project_id", "character_id", "reference_revision", name="uq_v2_character_reference_revision"),
        Index("ix_v2_character_reference_decisions_project_character", "project_id", "character_id", "reference_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    character_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    character_context: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    character_context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    complementary_asset_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    asset_hashes: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    reviewer: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterReferenceProposalRow(Base):
    """A non-Approval exploratory character appearance request."""

    __tablename__ = "v2_character_reference_proposals"
    __table_args__ = (Index("ix_v2_character_reference_proposals_project_created", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(67), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    character_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_candidate_asset_id: Mapped[str | None] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterReferenceProposalDeliveryRow(Base):
    __tablename__ = "v2_character_reference_proposal_deliveries"
    __table_args__ = (
        UniqueConstraint("proposal_id", "delivery_id", name="uq_v2_character_proposal_delivery_identity"),
        Index("uq_v2_character_proposal_final_delivery", "proposal_id", unique=True, sqlite_where=text("delivery_id IS NOT NULL")),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("v2_character_reference_proposals.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    diagnostic_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CharacterReferenceProposalCandidateRow(Base):
    __tablename__ = "v2_character_reference_proposal_candidates"
    __table_args__ = (UniqueConstraint("delivery_id", "asset_id", name="uq_v2_character_proposal_candidate_asset"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("v2_character_reference_proposals.id", ondelete="RESTRICT"), nullable=False)
    delivery_id: Mapped[str] = mapped_column(ForeignKey("v2_character_reference_proposal_deliveries.id", ondelete="RESTRICT"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False)
    output_filename: Mapped[str] = mapped_column(String(180), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SamePersonReviewStateRow(Base):
    __tablename__ = "v2_same_person_review_states"

    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SamePersonReviewRow(Base):
    __tablename__ = "v2_same_person_reviews"
    __table_args__ = (Index("ix_v2_same_person_reviews_project_binding_revision", "project_id", "binding_id", "review_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False)
    binding_id: Mapped[str] = mapped_column(ForeignKey("v2_reviewed_shot_bindings.id", ondelete="RESTRICT"), nullable=False)
    review_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_bindings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    comparisons: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    reviewer: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProviderSettingsRow(Base):
    __tablename__ = "v2_provider_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TextProviderProfileRow(Base):
    __tablename__ = "v2_text_provider_profiles"

    id: Mapped[str] = mapped_column(String(63), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    availability_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adapter_id: Mapped[str] = mapped_column(String(120), nullable=False, default="openai_compatible")
    adapter_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProviderProfileSelectionRow(Base):
    __tablename__ = "v2_provider_profile_selection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active_profile_id: Mapped[str] = mapped_column(
        ForeignKey("v2_text_provider_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
PROJECT_TEXT_PIPELINE_TABLE_NAMES = frozenset(
    {
        "v2_projects",
        "v2_entity_revisions",
        "v2_stage_heads",
        "v2_authoring_drafts",
        "v2_gate_results",
        "v2_generation_runs",
        "v2_generation_attempts",
        "v2_artifacts",
        "v2_generation_plans",
        "v2_generation_stage_plans",
        "v2_generation_work_units",
        "v2_sealed_stage_aggregates",
        "v2_generation_work_unit_repair_scopes",
        "v2_generation_fragment_reuse_bindings",
        "v2_generation_work_unit_repair_idempotency",
        "v2_generation_story_graph_topologies",
        "v2_media_tasks",
        "v2_approval_decisions",
        "v2_managed_assets",
        "v2_managed_asset_provenance",
        "v2_visual_intents",
        "v2_visual_selection_states",
        "v2_reviewed_shot_bindings",
        "v2_still_previews",
        "v2_production_units",
        "v2_image_jobs",
        "v2_image_job_deliveries",
        "v2_image_job_candidates",
        "v2_character_reference_states",
        "v2_character_reference_decisions",
        "v2_character_reference_proposals",
        "v2_character_reference_proposal_deliveries",
        "v2_character_reference_proposal_candidates",
        "v2_same_person_review_states",
        "v2_same_person_reviews",
    }
)


def _json_data(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=False)
    return value


def _contains_unredacted_secret_setting(value: Any) -> bool:
    """Allow explicit redaction markers while rejecting secret-shaped fields."""

    if isinstance(value, dict):
        for key, child in value.items():
            if is_secret_setting_name(key) and child != "[redacted]":
                return True
            if _contains_unredacted_secret_setting(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_unredacted_secret_setting(child) for child in value)
    return False


def stable_hash(value: Any) -> str:
    encoded = json.dumps(_json_data(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _stored_utc(value: datetime) -> datetime:
    """Restore SQLite's offset-less UTC storage to the public datetime contract."""

    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class SQLiteRepository:
    """Transactional canonical store with immutable entity revisions and mutable heads."""

    def __init__(
        self,
        database_url: str = "sqlite://",
        *,
        create_schema: bool = True,
        sqlite_busy_timeout_ms: int = 1_000,
        schema_scope: Literal["full", "project"] = "full",
    ) -> None:
        if sqlite_busy_timeout_ms < 1:
            raise ValueError("sqlite_busy_timeout_ms must be at least 1")
        if schema_scope not in {"full", "project"}:
            raise ValueError("schema_scope must be 'full' or 'project'")
        self._sqlite_busy_timeout_ms = sqlite_busy_timeout_ms
        self._bootstrap_retry_after_seconds = max(1, (sqlite_busy_timeout_ms + 999) // 1_000)
        self._schema_scope = schema_scope
        engine_options: dict[str, Any] = {"future": True}
        database_path = sqlite_database_path(database_url)
        if database_url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_options["poolclass"] = StaticPool
        elif database_path is not None:
            database_path.parent.mkdir(parents=True, exist_ok=True)
            if create_schema and schema_scope == "full":
                SchemaMigrator(database_url).upgrade()
        self.engine = create_engine(database_url, **engine_options)
        if database_url.startswith("sqlite"):
            file_database = database_path is not None

            @event.listens_for(self.engine, "connect")
            def configure_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute(f"PRAGMA busy_timeout={self._sqlite_busy_timeout_ms}")
                cursor.close()

            if file_database:
                # Journal mode is database-wide and changing it takes a write
                # lock. Doing that in every connection callback races an
                # unrelated BEGIN IMMEDIATE from another repository instance.
                # Configure it once, synchronously, before this repository is
                # published to concurrent callers.
                with self.engine.connect() as connection:
                    current_mode = connection.exec_driver_sql(
                        "PRAGMA journal_mode"
                    ).scalar_one()
                    if str(current_mode).lower() != "wal":
                        connection.exec_driver_sql("PRAGMA journal_mode=WAL").scalar_one()

        self._sessions = sessionmaker(bind=self.engine, expire_on_commit=False, class_=Session)
        self._write_lock = RLock()
        if create_schema and (database_path is None or schema_scope == "project"):
            Base.metadata.create_all(self.engine, tables=self._schema_tables())

    def _schema_tables(self) -> list[Any]:
        if self._schema_scope == "full":
            return list(Base.metadata.sorted_tables)
        return [
            table
            for table in Base.metadata.sorted_tables
            if table.name in PROJECT_TEXT_PIPELINE_TABLE_NAMES
        ]

    def close(self) -> None:
        self.engine.dispose()

    @contextmanager
    def _read(self) -> Iterator[Session]:
        with self._sessions() as session:
            yield session

    @contextmanager
    def _write(self) -> Iterator[Session]:
        with self._write_lock, self._sessions.begin() as session:
            yield session

    @contextmanager
    def _bootstrap_write(self) -> Iterator[Session]:
        """Serialize creation-key decisions across repository instances.

        The in-process lock protects one repository instance.  SQLite's
        immediate transaction supplies the equivalent write boundary for
        separate repository instances (and therefore separate processes)
        before either can observe a missing idempotency binding.
        """

        with self._write_lock, self._sessions() as session:
            try:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield session
                session.commit()
            except OperationalError as error:
                session.rollback()
                if self._is_sqlite_lock_contention(error):
                    raise BootstrapContentionError(self._bootstrap_retry_after_seconds) from error
                raise
            except BaseException:
                session.rollback()
                raise

    @contextmanager
    def _lifecycle_write(self) -> Iterator[Session]:
        """Serialize project lifecycle and project-owned writes across processes.

        A lifecycle revision is an optimistic concurrency token, so its check
        and mutation must share SQLite's writer lease.  The same lease is used
        by project-owned entry writes to prevent a stale active-project read
        from creating work immediately after a successful archive.
        """

        if self.engine.dialect.name != "sqlite":
            with self._write() as session:
                yield session
            return
        with self._write_lock, self._sessions() as session:
            try:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield session
                session.commit()
            except OperationalError as error:
                session.rollback()
                if self._is_sqlite_lock_contention(error):
                    raise LifecycleContentionError(self._bootstrap_retry_after_seconds) from error
                raise
            except BaseException:
                session.rollback()
                raise

    @contextmanager
    def _work_unit_claim_write(self) -> Iterator[Session]:
        """Serialize a work-unit claim before inspecting its current state.

        ``_write`` is sufficient for ordinary repository mutations, but a
        work-unit claim is a read-then-write transition that must also be safe
        across distinct repository instances.  SQLite has no row-level
        ``SELECT FOR UPDATE``; an immediate transaction is its durable writer
        lease.  A bounded lock timeout is surfaced as a domain transition
        conflict instead of leaking a SQLite driver error to a runner.
        """

        with self._write_lock, self._sessions() as session:
            try:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                yield session
                session.commit()
            except OperationalError as error:
                session.rollback()
                if self._is_sqlite_lock_contention(error):
                    raise InvalidTransitionError(
                        "work-unit allocation is temporarily contended; retry after the active claim commits"
                    ) from error
                raise
            except BaseException:
                session.rollback()
                raise

    @staticmethod
    def _is_sqlite_lock_contention(error: OperationalError) -> bool:
        message = str(error).lower()
        return "database is locked" in message or "database table is locked" in message

    @staticmethod
    def _project(row: ProjectRow) -> Project:
        return Project(
            id=row.id,
            revision=row.revision,
            lifecycle_revision=row.lifecycle_revision,
            lifecycle_status=ProjectLifecycleStatus(row.lifecycle_status),
            archived_at=_stored_utc(row.archived_at) if row.archived_at else None,
            brief=ProjectBrief.model_validate(row.brief),
            created_at=_stored_utc(row.created_at),
            updated_at=_stored_utc(row.updated_at),
        )

    @staticmethod
    def _latest_run_summary(row: GenerationRunRow) -> LatestRunSummary:
        return LatestRunSummary(
            id=row.id,
            kind=RunKind(row.kind),
            status=RunStatus(row.status),
            requested_stages=[StageName(stage) for stage in row.requested_stages],
            created_at=_stored_utc(row.created_at),
            finished_at=_stored_utc(row.finished_at) if row.finished_at else None,
        )

    @staticmethod
    def _stage_head(row: StageHeadRow) -> StageHead:
        return StageHead(
            stage=StageName(row.stage),
            status=StageStatus(row.status),
            revision=row.revision,
            entity_revision_id=row.entity_revision_id,
            content_hash=row.content_hash,
            schema_version=row.schema_version,
            input_revisions={StageName(key): value for key, value in row.input_revisions.items()},
            stale_reasons=list(row.stale_reasons),
            updated_at=row.updated_at,
        )

    @staticmethod
    def _entity_revision(row: EntityRevisionRow) -> EntityRevision:
        return EntityRevision(
            id=row.id,
            project_id=row.project_id,
            stage=StageName(row.stage),
            revision=row.revision,
            parent_revision_id=row.parent_revision_id,
            content_hash=row.content_hash,
            schema_version=row.schema_version,
            input_revisions={StageName(key): value for key, value in row.input_revisions.items()},
            payload=row.payload,
            created_at=row.created_at,
        )

    @staticmethod
    def _decode_stage_payload(
        stage: StageName,
        payload: dict[str, Any],
        schema_version: int | None,
    ) -> StagePayload:
        """Use the stored schema version, never the application's current default."""

        if schema_version not in {LEGACY_STAGE_SCHEMA_VERSION, CURRENT_STAGE_SCHEMA_VERSION}:
            raise SchemaResetRequiredError(stage=stage, schema_version=schema_version)
        return stage_payload_model(stage, schema_version=schema_version).model_validate(payload)

    @classmethod
    def _decode_current_stage_payload(
        cls,
        stage: StageName,
        payload: dict[str, Any],
        schema_version: int | None,
    ) -> StagePayload:
        """Decode a live authoring/runtime input, which must use schema V2.

        V1 remains readable as raw historical revision/run evidence. It is not
        a valid current project input because its free-text dialogue, audio,
        timing, and entity state cannot be upgraded without guessing.
        """

        if schema_version != CURRENT_STAGE_SCHEMA_VERSION:
            raise SchemaResetRequiredError(stage=stage, schema_version=schema_version)
        return cls._decode_stage_payload(stage, payload, schema_version)

    @staticmethod
    def _gate_result(row: GateResultRow) -> GateResult:
        return GateResult(
            id=row.id,
            gate_id=row.gate_id,
            gate_set_version=row.gate_version,
            evaluated_input_hash=row.evaluation_input_hash,
            required=row.required,
            status=row.status,
            severity=row.severity,
            entity_path=tuple(row.entity_path),
            evidence=tuple(GateEvidence.model_validate(item) for item in row.evidence),
            reason=row.reason,
        )

    @staticmethod
    def _approval_decision(row: ApprovalDecisionRow) -> ApprovalDecision:
        return ApprovalDecision(
            id=row.id,
            project_id=row.project_id,
            entity_revision_id=row.entity_revision_id,
            subject_type=row.subject_type,
            subject_id=row.subject_id,
            subject_revision=row.subject_revision,
            content_hash=row.content_hash,
            canonical_input_revisions=tuple(
                (StageName(stage), revision)
                for stage, revision in sorted(row.canonical_input_revisions.items())
            ),
            gate_set_version=row.gate_set_version,
            decision=row.decision,
            reviewer=row.reviewer,
            note=row.note,
            created_at=_stored_utc(row.created_at),
        )

    @staticmethod
    def _run(row: GenerationRunRow) -> GenerationRun:
        return GenerationRun(
            id=row.id,
            project_id=row.project_id,
            kind=RunKind(row.kind),
            parent_run_id=row.parent_run_id,
            repair_stage=StageName(row.repair_stage) if row.repair_stage else None,
            repair_source=RepairSource.model_validate(row.repair_source) if row.repair_source else None,
            work_unit_repair_scope_id=row.work_unit_repair_scope_id,
            provider_snapshot=dict(row.provider_snapshot),
            requested_stages=[StageName(stage) for stage in row.requested_stages],
            status=RunStatus(row.status),
            canonical_snapshot=CanonicalSnapshot.model_validate(row.canonical_snapshot),
            instructions=row.instructions,
            legacy_unsealed=row.legacy_unsealed,
            result_revision_ids=list(row.result_revision_ids),
            error=row.error,
            failure_code=row.failure_code,
            failed_stage=StageName(row.failed_stage) if row.failed_stage else None,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )

    @staticmethod
    def _attempt(row: GenerationAttemptRow) -> GenerationAttempt:
        return GenerationAttempt(
            id=row.id,
            run_id=row.run_id,
            work_unit_id=row.work_unit_id,
            stage=StageName(row.stage),
            attempt_number=row.attempt_number,
            attempt_kind=GenerationAttemptKind(row.attempt_kind),
            source_attempt_id=row.source_attempt_id,
            status=AttemptStatus(row.status),
            provider=row.provider,
            model=row.model,
            error=row.error,
            dispatched_at=row.dispatched_at,
            response_persisted_at=row.response_persisted_at,
            provider_request_id=row.provider_request_id,
            outcome_unknown=row.outcome_unknown,
            outcome_code=row.outcome_code,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )

    @staticmethod
    def _artifact(row: ArtifactRow) -> Artifact:
        return Artifact(
            id=row.id,
            run_id=row.run_id,
            attempt_id=row.attempt_id,
            work_unit_id=row.work_unit_id,
            source_artifact_id=row.source_artifact_id,
            stage=StageName(row.stage) if row.stage else None,
            kind=ArtifactKind(row.kind),
            media_type=row.media_type,
            content=row.content,
            content_hash=row.content_hash,
            created_at=row.created_at,
        )

    @staticmethod
    def _generation_plan_trace(row: GenerationPlanRow) -> GenerationPlanTrace:
        return GenerationPlanTrace(run_id=row.run_id, plan_hash=row.plan_hash, plan=dict(row.plan))

    @staticmethod
    def _stage_plan_trace(row: StagePlanRow) -> StagePlanTrace:
        return StagePlanTrace(
            id=row.id,
            run_id=row.run_id,
            stage=StageName(row.stage),
            stage_plan_hash=row.stage_plan_hash,
            dependency_hash=row.dependency_hash,
            plan=dict(row.plan),
        )

    @staticmethod
    def _work_unit_trace(row: GenerationWorkUnitRow) -> GenerationWorkUnitTrace:
        return GenerationWorkUnitTrace(
            id=row.id,
            run_id=row.run_id,
            stage_plan_id=row.stage_plan_id,
            stage=StageName(row.stage),
            sequence=row.sequence,
            selector=dict(row.selector),
            input_hash=row.input_hash,
            dependency_hash=row.dependency_hash,
            unit_dependency_hash=row.unit_dependency_hash,
            budget=dict(row.budget),
            estimated_input_tokens=row.estimated_input_tokens,
            context_window_tokens=row.context_window_tokens,
            status=WorkUnitStatus(row.status),
        )

    @staticmethod
    def _sealed_aggregate_trace(row: SealedStageAggregateRow) -> SealedStageAggregateTrace:
        return SealedStageAggregateTrace(
            id=row.id,
            run_id=row.run_id,
            stage_plan_id=row.stage_plan_id,
            stage=StageName(row.stage),
            manifest_hash=row.manifest_hash,
            manifest=dict(row.manifest),
            payload=dict(row.payload),
            created_at=_stored_utc(row.created_at),
        )

    @staticmethod
    def _repair_scope(row: WorkUnitRepairScopeRow) -> WorkUnitRepairScope:
        scope = WorkUnitRepairScope.model_validate(row.scope)
        if (
            scope.child_run_id != row.child_run_id
            or scope.scope_hash != row.scope_hash
            or stable_hash(SQLiteRepository._scope_hash_payload(row.scope)) != row.scope_hash
        ):
            raise InvalidTransitionError("stored exact repair scope identity is inconsistent")
        return scope

    @staticmethod
    def _fragment_reuse_binding(row: FragmentReuseBindingRow) -> FragmentReuseBinding:
        binding = FragmentReuseBinding.model_validate(row.binding)
        if (
            binding.id != row.id
            or binding.child_run_id != row.child_run_id
            or binding.child_stage_plan_id != row.child_stage_plan_id
            or binding.child_work_unit_id != row.child_work_unit_id
            or binding.binding_hash != row.binding_hash
            or stable_hash(
                {
                    key: value
                    for key, value in row.binding.items()
                    if key not in {"id", "bindingHash"}
                }
            )
            != row.binding_hash
        ):
            raise InvalidTransitionError("stored fragment reuse binding identity is inconsistent")
        return binding

    @staticmethod
    def _text_provider_profile(row: TextProviderProfileRow) -> TextProviderProfile:
        configuration = TextProviderProfileSnapshot.model_validate(row.settings)
        return TextProviderProfile(
            profile_id=row.id,
            display_name=row.display_name,
            configuration=configuration,
            revision=row.revision,
            enabled=row.enabled,
            availability_revision=row.availability_revision,
            adapter_id=row.adapter_id,
            adapter_version=row.adapter_version,
            created_at=_stored_utc(row.created_at),
            updated_at=_stored_utc(row.updated_at),
        )

    @staticmethod
    def _provider_profile_selection(
        row: ProviderProfileSelectionRow,
    ) -> ProviderProfileSelection:
        return ProviderProfileSelection(
            active_profile_id=row.active_profile_id,
            revision=row.revision,
            updated_at=_stored_utc(row.updated_at),
        )

    @staticmethod
    def _story_graph_topology_trace(
        row: StoryGraphTopologyRow,
    ) -> StoryGraphTopologyTrace:
        return StoryGraphTopologyTrace(
            run_id=row.run_id,
            generation_plan_hash=row.generation_plan_hash,
            topology_hash=row.topology_hash,
            topology=dict(row.topology),
            created_at=_stored_utc(row.created_at),
        )

    @staticmethod
    def _media_task(row: MediaTaskRow) -> MediaTask:
        return MediaTask(
            id=row.id,
            project_id=row.project_id,
            shot_id=row.shot_id,
            storyboard_revision=row.storyboard_revision,
            kind=MediaKind(row.kind),
            status=MediaTaskStatus(row.status),
            derived_prompt=row.derived_prompt,
            prompt_components=row.prompt_components,
            provider=row.provider,
            public_settings=row.public_settings,
            provider_task_id=row.provider_task_id,
            output_uri=row.output_uri,
            error=row.error,
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )

    @staticmethod
    def _project_row(session: Session, project_id: str) -> ProjectRow:
        row = session.get(ProjectRow, project_id)
        if row is None:
            raise NotFoundError(f"project not found: {project_id}")
        return row

    @staticmethod
    def _stage_row(session: Session, project_id: str, stage: StageName) -> StageHeadRow:
        row = session.scalar(
            select(StageHeadRow).where(StageHeadRow.project_id == project_id, StageHeadRow.stage == stage.value)
        )
        if row is None:
            raise NotFoundError(f"stage head not found: {project_id}/{stage.value}")
        return row

    @staticmethod
    def _run_row(session: Session, run_id: str) -> GenerationRunRow:
        row = session.get(GenerationRunRow, run_id)
        if row is None:
            raise NotFoundError(f"run not found: {run_id}")
        return row

    @staticmethod
    def _media_task_row(session: Session, task_id: str) -> MediaTaskRow:
        row = session.get(MediaTaskRow, task_id)
        if row is None:
            raise NotFoundError(f"media task not found: {task_id}")
        return row

    @staticmethod
    def _creation_fingerprint(brief: ProjectBrief, stages: Sequence[InitialStage]) -> str:
        return stable_hash(
            {
                "brief": brief.model_dump(mode="json", by_alias=False),
                "initialStages": [
                    {"stage": stage.stage.value, "payload": stage.payload}
                    for stage in stages
                ],
            }
        )

    def _create_project_row_in_session(
        self,
        session: Session,
        brief: ProjectBrief,
        now: datetime,
    ) -> ProjectRow:
        project = Project(brief=brief, created_at=now, updated_at=now)
        row = ProjectRow(
            id=project.id,
            revision=project.revision,
            lifecycle_revision=project.lifecycle_revision,
            lifecycle_status=project.lifecycle_status.value,
            archived_at=None,
            brief=brief.model_dump(mode="json", by_alias=False),
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        for stage in STAGE_ORDER:
            session.add(
                StageHeadRow(
                    id=f"{project.id}:{stage.value}",
                    project_id=project.id,
                    stage=stage.value,
                    status=StageStatus.MISSING.value,
                    revision=0,
                    entity_revision_id=None,
                    content_hash=None,
                    schema_version=CURRENT_STAGE_SCHEMA_VERSION,
                    input_revisions={},
                    stale_reasons=[],
                    updated_at=now,
                )
            )
        return row

    @staticmethod
    def _assert_active_project(project_row: ProjectRow) -> None:
        if ProjectLifecycleStatus(project_row.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            raise InvalidTransitionError("archived projects are read-only")

    @staticmethod
    def _assert_lifecycle_revision(project_row: ProjectRow, expected_lifecycle_revision: int) -> None:
        if project_row.lifecycle_revision != expected_lifecycle_revision:
            raise RevisionConflictError(
                "project-lifecycle", expected_lifecycle_revision, project_row.lifecycle_revision
            )

    @staticmethod
    def _project_is_busy_in_session(session: Session, project_id: str) -> bool:
        nonterminal_run = session.scalar(
            select(GenerationRunRow.id)
            .where(
                GenerationRunRow.project_id == project_id,
                GenerationRunRow.status.not_in(
                    [status.value for status in TERMINAL_RUN_STATUSES]
                ),
            )
            .limit(1)
        )
        nonterminal_media = session.scalar(
            select(MediaTaskRow.id)
            .where(
                MediaTaskRow.project_id == project_id,
                MediaTaskRow.status.not_in(
                    [status.value for status in TERMINAL_MEDIA_TASK_STATUSES]
                ),
            )
            .limit(1)
        )
        nonterminal_work_unit = session.scalar(
            select(GenerationWorkUnitRow.id)
            .join(GenerationRunRow, GenerationWorkUnitRow.run_id == GenerationRunRow.id)
            .where(
                GenerationRunRow.project_id == project_id,
                GenerationWorkUnitRow.status.not_in(
                    [status.value for status in TERMINAL_WORK_UNIT_STATUSES]
                ),
            )
            .limit(1)
        )
        return (
            nonterminal_run is not None
            or nonterminal_media is not None
            or nonterminal_work_unit is not None
        )

    def _stage_envelopes_in_session(self, session: Session, project_id: str) -> list[StageEnvelope]:
        rows = session.scalars(
            select(StageHeadRow).where(StageHeadRow.project_id == project_id)
        ).all()
        by_stage = {StageName(row.stage): row for row in rows}
        envelopes: list[StageEnvelope] = []
        for stage in STAGE_ORDER:
            row = by_stage[stage]
            payload: StagePayload | None = None
            if row.entity_revision_id is not None:
                revision = session.get(EntityRevisionRow, row.entity_revision_id)
                if revision is None:
                    raise NotFoundError(f"entity revision not found: {row.entity_revision_id}")
                payload = self._decode_current_stage_payload(
                    stage, revision.payload, revision.schema_version
                )
            envelopes.append(StageEnvelope(head=self._stage_head(row), payload=payload))
        return envelopes

    def _project_creation_in_session(self, session: Session, project_row: ProjectRow) -> ProjectCreation:
        return ProjectCreation(
            **self._project(project_row).model_dump(mode="python"),
            stages=self._stage_envelopes_in_session(session, project_row.id),
        )

    def create_project(
        self,
        brief: ProjectBrief,
        *,
        initial_stages: Sequence[InitialStage | dict[str, Any]] = (),
        idempotency_key: str | None = None,
    ) -> ProjectCreation:
        normalized_stages = [InitialStage.model_validate(stage) for stage in initial_stages]
        validate_initial_stage_prefix(normalized_stages)
        fingerprint = self._creation_fingerprint(brief, normalized_stages)
        key = idempotency_key.strip() if idempotency_key is not None else None
        if key is not None and (not key or len(key) > 255):
            raise ValueError("idempotency key must contain between 1 and 255 characters")

        with self._bootstrap_write() as session:
            if key is not None:
                existing = session.get(ProjectCreationIdempotencyRow, key)
                if existing is not None:
                    if existing.request_fingerprint != fingerprint:
                        raise IdempotencyConflictError()
                    return self._project_creation_in_session(
                        session, self._project_row(session, existing.project_id)
                    )

            now = utc_now()
            project_row = self._create_project_row_in_session(session, brief, now)
            for initial_stage in normalized_stages:
                payload = stage_payload_model(
                    initial_stage.stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION
                ).model_validate(initial_stage.payload)
                self._install_stage_in_session(
                    session,
                    project_row,
                    initial_stage.stage,
                    payload,
                    expected_revision=0,
                    now=now,
                    allow_noop=False,
                )
            if key is not None:
                # Persist the aggregate before its durable key binding.  The
                # ORM rows intentionally have no relationship attributes, so
                # this explicit boundary makes the foreign-key ordering part
                # of the bootstrap contract rather than a unit-of-work
                # implementation detail.
                session.flush()
                session.add(
                    ProjectCreationIdempotencyRow(
                        idempotency_key=key,
                        request_fingerprint=fingerprint,
                        project_id=project_row.id,
                        created_at=now,
                    )
                )
            return self._project_creation_in_session(session, project_row)

    def get_project(self, project_id: str) -> Project:
        with self._read() as session:
            return self._project(self._project_row(session, project_id))

    def list_projects(
        self,
        *,
        lifecycle_status: ProjectLifecycleStatus | None = ProjectLifecycleStatus.ACTIVE,
        limit: int = 50,
        cursor: tuple[datetime, str] | None = None,
    ) -> tuple[list[ProjectSummary], tuple[datetime, str] | None]:
        """Return one stable page ordered by immutable `(created_at, id)` facts.

        The cursor is deliberately represented internally as the actual sort
        tuple.  The HTTP layer alone owns its opaque encoding, keeping storage
        ordering independent from a presentation format.
        """

        if not 1 <= limit <= 200:
            raise ValueError("project list limit must be between 1 and 200")
        with self._read() as session:
            statement = select(ProjectRow)
            if lifecycle_status is not None:
                statement = statement.where(ProjectRow.lifecycle_status == lifecycle_status.value)
            if cursor is not None:
                created_at, project_id = cursor
                statement = statement.where(
                    (ProjectRow.created_at < created_at)
                    | ((ProjectRow.created_at == created_at) & (ProjectRow.id < project_id))
                )
            rows = session.scalars(
                statement.order_by(ProjectRow.created_at.desc(), ProjectRow.id.desc()).limit(limit + 1)
            ).all()
            page_rows = rows[:limit]
            has_more = len(rows) > limit
            summaries: list[ProjectSummary] = []
            for row in page_rows:
                stage_rows = session.scalars(
                    select(StageHeadRow).where(StageHeadRow.project_id == row.id)
                ).all()
                statuses = {StageName(head.stage): StageStatus(head.status) for head in stage_rows}
                latest_run = session.scalar(
                    select(GenerationRunRow)
                    .where(GenerationRunRow.project_id == row.id)
                    .order_by(GenerationRunRow.created_at.desc(), GenerationRunRow.id.desc())
                    .limit(1)
                )
                summaries.append(
                    ProjectSummary(
                        **self._project(row).model_dump(mode="python"),
                        stage_statuses=statuses,
                        latest_run=self._latest_run_summary(latest_run) if latest_run else None,
                    )
                )
            next_cursor = None
            if has_more and page_rows:
                last = page_rows[-1]
                next_cursor = (last.created_at, last.id)
            return summaries, next_cursor

    def archive_project(self, project_id: str, expected_lifecycle_revision: int) -> Project:
        with self._lifecycle_write() as session:
            row = self._project_row(session, project_id)
            self._assert_lifecycle_revision(row, expected_lifecycle_revision)
            if ProjectLifecycleStatus(row.lifecycle_status) == ProjectLifecycleStatus.ARCHIVED:
                return self._project(row)
            if self._project_is_busy_in_session(session, project_id):
                raise ProjectBusyError()
            now = utc_now()
            row.lifecycle_status = ProjectLifecycleStatus.ARCHIVED.value
            row.archived_at = now
            row.lifecycle_revision += 1
            row.updated_at = now
            return self._project(row)

    def restore_project(self, project_id: str, expected_lifecycle_revision: int) -> Project:
        with self._lifecycle_write() as session:
            row = self._project_row(session, project_id)
            self._assert_lifecycle_revision(row, expected_lifecycle_revision)
            if ProjectLifecycleStatus(row.lifecycle_status) == ProjectLifecycleStatus.ACTIVE:
                return self._project(row)
            now = utc_now()
            row.lifecycle_status = ProjectLifecycleStatus.ACTIVE.value
            row.archived_at = None
            row.lifecycle_revision += 1
            row.updated_at = now
            return self._project(row)

    @staticmethod
    def _duplicate_fingerprint(
        project_id: str,
        expected_lifecycle_revision: int,
        title: str | None,
    ) -> str:
        return stable_hash(
            {
                "projectId": project_id,
                "expectedLifecycleRevision": expected_lifecycle_revision,
                "title": title,
            }
        )

    def _duplicate_result_in_session(
        self,
        session: Session,
        project_id: str,
        copied_through: str | None,
        omitted_stages: Sequence[str],
    ) -> ProjectDuplicateResult:
        return ProjectDuplicateResult(
            project=self._project_creation_in_session(session, self._project_row(session, project_id)),
            copied_through=StageName(copied_through) if copied_through else None,
            omitted_stages=[StageName(stage) for stage in omitted_stages],
        )

    def duplicate_project(
        self,
        project_id: str,
        expected_lifecycle_revision: int,
        *,
        title: str | None = None,
        idempotency_key: str | None = None,
    ) -> ProjectDuplicateResult:
        normalized_title = title.strip() if title is not None else None
        if normalized_title == "":
            raise ValueError("duplicate title must not be blank")
        key = idempotency_key.strip() if idempotency_key is not None else None
        if key is not None and (not key or len(key) > 255):
            raise ValueError("idempotency key must contain between 1 and 255 characters")
        fingerprint = self._duplicate_fingerprint(
            project_id, expected_lifecycle_revision, normalized_title
        )

        # Duplicate-key decisions must be made at SQLite's immediate write
        # boundary, exactly like project creation.  Otherwise two processes
        # can both observe an unbound key and create distinct copies.
        with self._bootstrap_write() as session:
            if key is not None:
                existing = session.get(ProjectDuplicateIdempotencyRow, key)
                if existing is not None:
                    if existing.request_fingerprint != fingerprint:
                        raise IdempotencyConflictError()
                    return self._duplicate_result_in_session(
                        session,
                        existing.project_id,
                        existing.copied_through,
                        existing.omitted_stages,
                    )

            source = self._project_row(session, project_id)
            self._assert_lifecycle_revision(source, expected_lifecycle_revision)
            source_brief = ProjectBrief.model_validate(source.brief)
            brief_data = source_brief.model_dump(mode="python")
            if normalized_title is not None:
                brief_data["title"] = normalized_title
            duplicate_brief = ProjectBrief.model_validate(brief_data)
            now = utc_now()
            duplicate = self._create_project_row_in_session(session, duplicate_brief, now)

            copied: list[StageName] = []
            for stage in STAGE_ORDER:
                source_head = self._stage_row(session, source.id, stage)
                if source_head.status != StageStatus.READY.value:
                    break
                payload = self._load_stage_payload(session, source.id, stage)
                self._install_stage_in_session(
                    session,
                    duplicate,
                    stage,
                    payload,
                    expected_revision=0,
                    now=now,
                    allow_noop=False,
                )
                copied.append(stage)
            copied_through = copied[-1] if copied else None
            omitted = list(STAGE_ORDER[len(copied) :])
            if key is not None:
                session.flush()
                session.add(
                    ProjectDuplicateIdempotencyRow(
                        idempotency_key=key,
                        request_fingerprint=fingerprint,
                        project_id=duplicate.id,
                        copied_through=copied_through.value if copied_through else None,
                        omitted_stages=[stage.value for stage in omitted],
                        created_at=now,
                    )
                )
            return self._duplicate_result_in_session(
                session,
                duplicate.id,
                copied_through.value if copied_through else None,
                [stage.value for stage in omitted],
            )

    def permanent_delete_project(
        self,
        project_id: str,
        expected_lifecycle_revision: int,
        confirmation_title: str,
    ) -> None:
        if not confirmation_title.strip():
            raise ValueError("confirmation title must not be blank")
        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_lifecycle_revision(project, expected_lifecycle_revision)
            if ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ARCHIVED:
                raise InvalidTransitionError("only archived projects can be permanently deleted")
            if confirmation_title != ProjectBrief.model_validate(project.brief).title:
                raise InvalidTransitionError("confirmation title does not match the project title")
            if self._project_is_busy_in_session(session, project_id):
                raise ProjectBusyError()
            # The byte store is shared and content addressed.  Until a
            # media-aware whole-project erasure contract exists, deleting the
            # relational project first would orphan protected originals and
            # immutable preview history.  Refuse before any delete mutation.
            if session.scalar(
                select(ManagedAssetRow.id)
                .where(ManagedAssetRow.project_id == project_id)
                .limit(1)
            ) is not None:
                raise ProjectManagedAssetsPresentError()

            # Generation-run repair lineage uses a self-referential RESTRICT
            # foreign key.  Deleting leaf runs first preserves that durable
            # lineage contract while letting every other project-owned record
            # cascade from its run or project parent.
            remaining_run_ids = set(
                session.scalars(
                    select(GenerationRunRow.id).where(GenerationRunRow.project_id == project_id)
                ).all()
            )
            while remaining_run_ids:
                referenced_parents = set(
                    session.scalars(
                        select(GenerationRunRow.parent_run_id).where(
                            GenerationRunRow.parent_run_id.in_(remaining_run_ids)
                        )
                    ).all()
                )
                leaves = remaining_run_ids - {parent for parent in referenced_parents if parent is not None}
                if not leaves:
                    raise InvalidTransitionError("generation run lineage cannot be deleted safely")
                session.execute(delete(GenerationRunRow).where(GenerationRunRow.id.in_(leaves)))
                session.flush()
                remaining_run_ids -= leaves
            session.delete(project)

    @staticmethod
    def _managed_asset_dict(row: ManagedAssetRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "projectId": row.project_id,
            "originalHash": row.original_hash,
            "displayHash": row.display_hash,
            "mimeType": row.mime_type,
            "byteSize": row.byte_size,
            "width": row.width,
            "height": row.height,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def record_managed_import(
        self,
        project_id: str,
        *,
        original_hash: str,
        display_hash: str,
        mime_type: str,
        byte_size: int,
        width: int,
        height: int,
        declaration: dict[str, Any],
        publish: Callable[[], tuple[str, str]],
    ) -> dict[str, Any]:
        """Publish one independent project provenance record over stored bytes."""

        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            # Publish under the same lifecycle writer lease that admits the
            # immutable metadata, so a rejected/archived project never leaves
            # a newly written unowned blob behind.
            original_uri, display_uri = publish()
            now = utc_now()
            asset = ManagedAssetRow(
                id=new_id(), project_id=project_id, original_uri=original_uri,
                original_hash=original_hash, display_uri=display_uri,
                display_hash=display_hash, mime_type=mime_type, byte_size=byte_size,
                width=width, height=height, created_at=now,
            )
            session.add(asset)
            # These rows intentionally have no ORM relationship (their
            # history stays one-way immutable), so establish the asset FK
            # before adding the independent provenance declaration.
            session.flush()
            session.add(ManagedAssetProvenanceRow(
                id=new_id(), project_id=project_id, asset_id=asset.id,
                declaration=declaration, created_at=now,
            ))
            session.flush()
            return self._managed_asset_dict(asset)

    def get_managed_asset_storage(self, project_id: str, asset_id: str) -> dict[str, Any]:
        with self._read() as session:
            asset = session.get(ManagedAssetRow, asset_id)
            if asset is None or asset.project_id != project_id:
                raise NotFoundError(f"managed asset not found: {asset_id}")
            return {
                **self._managed_asset_dict(asset),
                "originalUri": asset.original_uri,
                "displayUri": asset.display_uri,
            }

    def reviewed_keyframe_crop_source(
        self,
        project_id: str,
        *,
        binding_id: str,
        expected_selection_revision: int,
    ) -> dict[str, Any]:
        """Read the exact current selected source for a proposed crop.

        The write method repeats these checks. This read projection only lets
        the API obtain bytes for a transform; it does not authorize publishing
        a derivative after a selection has changed.
        """

        with self._read() as session:
            self._assert_active_project(self._project_row(session, project_id))
            state = self._selection_state_in_session(session, project_id, utc_now())
            if state.revision != expected_selection_revision:
                raise RevisionConflictError(
                    "visual-selection", expected_selection_revision, state.revision
                )
            binding = session.get(ReviewedShotBindingRow, binding_id)
            if (
                binding is None
                or not self._reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding
                )
            ):
                raise InvalidTransitionError(
                    "keyframe crop needs the current reviewed selected keyframe"
                )
            asset = session.get(ManagedAssetRow, binding.asset_id)
            if asset is None or asset.project_id != project_id:
                raise InvalidTransitionError("selected keyframe bytes are unavailable")
            return {
                "bindingId": binding.id,
                "selectionRevision": binding.selection_revision,
                "assetId": asset.id,
                "originalHash": asset.original_hash,
                "mimeType": asset.mime_type,
                "width": asset.width,
                "height": asset.height,
                "originalUri": asset.original_uri,
            }

    def record_reviewed_keyframe_center_crop(
        self,
        project_id: str,
        *,
        source: dict[str, Any],
        target_profile: dict[str, Any],
        expected_selection_revision: int,
        original_hash: str,
        display_hash: str,
        mime_type: str,
        byte_size: int,
        width: int,
        height: int,
        publish: Callable[[], tuple[str, str]],
    ) -> dict[str, Any]:
        """Persist a source-bound crop without selecting it for the Shot."""

        with self._lifecycle_write() as session:
            self._assert_active_project(self._project_row(session, project_id))
            state = self._selection_state_in_session(session, project_id, utc_now())
            if state.revision != expected_selection_revision:
                raise RevisionConflictError(
                    "visual-selection", expected_selection_revision, state.revision
                )
            binding = session.get(ReviewedShotBindingRow, source["bindingId"])
            if (
                binding is None
                or binding.asset_id != source["assetId"]
                or binding.selection_revision != source["selectionRevision"]
                or not self._reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding
                )
            ):
                raise InvalidTransitionError(
                    "keyframe crop source is no longer the current reviewed keyframe"
                )
            source_asset = session.get(ManagedAssetRow, binding.asset_id)
            if (
                source_asset is None
                or source_asset.project_id != project_id
                or source_asset.original_hash != source["originalHash"]
            ):
                raise InvalidTransitionError("keyframe crop source bytes are unavailable")
            target_width, target_height = int(target_profile["width"]), int(target_profile["height"])
            if has_matching_aspect(
                source_asset.width, source_asset.height, target_width, target_height
            ):
                raise InvalidTransitionError(
                    "keyframe already matches the requested profile aspect"
                )
            if (width, height) != (target_width, target_height):
                raise InvalidTransitionError(
                    "derived keyframe crop does not match the requested profile"
                )
            original_uri, display_uri = publish()
            now = utc_now()
            asset = ManagedAssetRow(
                id=new_id(), project_id=project_id, original_uri=original_uri,
                original_hash=original_hash, display_uri=display_uri,
                display_hash=display_hash, mime_type=mime_type,
                byte_size=byte_size, width=width, height=height, created_at=now,
            )
            session.add(asset)
            session.flush()
            session.add(ManagedAssetProvenanceRow(
                id=new_id(), project_id=project_id, asset_id=asset.id,
                declaration={
                    "origin": "plotloom_keyframe_center_crop",
                    "sourceBindingId": binding.id,
                    "sourceAssetId": source_asset.id,
                    "sourceOriginalHash": source_asset.original_hash,
                    "targetProfile": dict(target_profile),
                    "transform": {
                        "version": 1,
                        "strategy": "cover_center_crop",
                        "centering": [0.5, 0.5],
                    },
                },
                created_at=now,
            ))
            session.flush()
            return self._managed_asset_dict(asset)

    def list_managed_assets(self, project_id: str) -> list[dict[str, Any]]:
        with self._read() as session:
            self._project_row(session, project_id)
            rows = session.scalars(
                select(ManagedAssetRow)
                .where(ManagedAssetRow.project_id == project_id)
                .order_by(ManagedAssetRow.created_at, ManagedAssetRow.id)
            ).all()
            result = []
            for row in rows:
                provenance = session.scalar(
                    select(ManagedAssetProvenanceRow)
                    .where(ManagedAssetProvenanceRow.asset_id == row.id)
                    .order_by(ManagedAssetProvenanceRow.created_at)
                    .limit(1)
                )
                result.append({
                    **self._managed_asset_dict(row),
                    "provenance": provenance.declaration if provenance else None,
                })
            return result

    def create_visual_intent(
        self,
        project_id: str,
        asset_id: str,
        intent: dict[str, Any],
        *,
        consumed_draft: tuple[str, int, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            asset = session.get(ManagedAssetRow, asset_id)
            if asset is None or asset.project_id != project_id:
                raise NotFoundError(f"managed asset not found: {asset_id}")
            if consumed_draft is not None:
                entity_id, draft_revision, draft_payload = consumed_draft
                self._consume_exact_authoring_draft_in_session(
                    session,
                    project,
                    editor_scope="visual_intent",
                    entity_id=entity_id,
                    expected_draft_revision=draft_revision,
                    canonical_base_revision=self._stage_row(
                        session, project_id, StageName.STORYBOARD
                    ).revision,
                    canonical_payload=draft_payload,
                )
            previous = session.scalar(
                select(VisualIntentRow.revision)
                .where(VisualIntentRow.project_id == project_id, VisualIntentRow.asset_id == asset_id)
                .order_by(VisualIntentRow.revision.desc()).limit(1)
            ) or 0
            row = VisualIntentRow(
                id=new_id(), project_id=project_id, asset_id=asset_id,
                revision=previous + 1, intent=intent, created_at=utc_now(),
            )
            session.add(row)
            session.flush()
            return {"id": row.id, "assetId": asset_id, "revision": row.revision, "intent": row.intent}

    def list_visual_intents(self, project_id: str) -> list[dict[str, Any]]:
        with self._read() as session:
            self._project_row(session, project_id)
            rows = session.scalars(
                select(VisualIntentRow)
                .where(VisualIntentRow.project_id == project_id)
                .order_by(VisualIntentRow.asset_id, VisualIntentRow.revision.desc())
            ).all()
            # A single imported still can legitimately serve more than one
            # authoring role.  Currentness is role-scoped, so do not hide the
            # latest location reference behind a later shot-keyframe revision.
            latest: dict[tuple[str, str | None], VisualIntentRow] = {}
            for row in rows:
                latest.setdefault((row.asset_id, row.intent.get("role")), row)
            return [
                {"id": row.id, "assetId": row.asset_id, "revision": row.revision, "intent": row.intent}
                for row in latest.values()
            ]

    @staticmethod
    def _latest_visual_intent_for_role_in_session(
        session: Session, project_id: str, asset_id: str, role: str | None
    ) -> VisualIntentRow | None:
        """Return the latest intent in the asset's role-specific stream."""

        return next(
            (
                candidate
                for candidate in session.scalars(
                    select(VisualIntentRow)
                    .where(
                        VisualIntentRow.project_id == project_id,
                        VisualIntentRow.asset_id == asset_id,
                    )
                    .order_by(VisualIntentRow.revision.desc())
                )
                if candidate.intent.get("role") == role
            ),
            None,
        )

    def _reviewed_binding_admission_eligible_in_session(
        self,
        session: Session,
        project_id: str,
        binding: ReviewedShotBindingRow,
        *,
        approval: ApprovalDecisionRow | None = None,
    ) -> bool:
        """Whether a binding can contribute to a new preview right now.

        Historical rows deliberately remain readable.  New projections may use
        only the latest binding for the Shot, latest intent in the bound
        asset/role stream, and the current exact storyboard approval.
        """

        if binding.project_id != project_id:
            return False
        latest_binding = session.scalar(
            select(ReviewedShotBindingRow)
            .where(
                ReviewedShotBindingRow.project_id == project_id,
                ReviewedShotBindingRow.shot_id == binding.shot_id,
            )
            .order_by(ReviewedShotBindingRow.selection_revision.desc())
            .limit(1)
        )
        if latest_binding is None or latest_binding.id != binding.id:
            return False
        intent = session.get(VisualIntentRow, binding.visual_intent_id)
        if (
            intent is None
            or intent.project_id != project_id
            or intent.asset_id != binding.asset_id
            or intent.revision != binding.visual_intent_revision
        ):
            return False
        latest_intent = self._latest_visual_intent_for_role_in_session(
            session, project_id, binding.asset_id, intent.intent.get("role")
        )
        if (
            latest_intent is None
            or latest_intent.id != intent.id
            or latest_intent.revision != intent.revision
        ):
            return False
        if approval is None:
            try:
                approval = self._approval_is_active_in_session(session, binding.approval_id)
            except (InvalidTransitionError, NotFoundError):
                return False
        return (
            approval.project_id == project_id
            and binding.approval_id == approval.id
            and binding.storyboard_entity_revision_id == approval.entity_revision_id
            and binding.storyboard_revision == approval.subject_revision
        )

    def list_current_reviewed_keyframes(self, project_id: str) -> list[dict[str, Any]]:
        with self._read() as session:
            self._project_row(session, project_id)
            rows = session.scalars(
                select(ReviewedShotBindingRow)
                .where(ReviewedShotBindingRow.project_id == project_id)
                .order_by(ReviewedShotBindingRow.selection_revision.desc())
            ).all()
            latest: dict[str, ReviewedShotBindingRow] = {}
            for row in rows:
                latest.setdefault(row.shot_id, row)
            return [
                {
                    "id": row.id, "assetId": row.asset_id, "shotId": row.shot_id,
                    "sceneId": row.scene_id, "selectionRevision": row.selection_revision,
                    "visualIntentId": row.visual_intent_id,
                    "visualIntentRevision": row.visual_intent_revision,
                    "compatibilityNote": row.compatibility_note,
                }
                for row in latest.values()
                if self._reviewed_binding_admission_eligible_in_session(session, project_id, row)
            ]

    def _approval_is_active_in_session(self, session: Session, decision_id: str) -> ApprovalDecisionRow:
        decision = session.get(ApprovalDecisionRow, decision_id)
        if decision is None:
            raise NotFoundError(f"approval decision not found: {decision_id}")
        if decision.decision != "approve":
            raise InvalidTransitionError("reviewed selection requires an active approval")
        latest = session.scalar(
            select(ApprovalDecisionRow)
            .where(
                ApprovalDecisionRow.entity_revision_id == decision.entity_revision_id,
                ApprovalDecisionRow.subject_type == decision.subject_type,
                ApprovalDecisionRow.subject_id == decision.subject_id,
            )
            .order_by(ApprovalDecisionRow.created_at.desc(), ApprovalDecisionRow.id.desc())
            .limit(1)
        )
        if latest is None or latest.id != decision.id:
            raise InvalidTransitionError("reviewed selection approval is revoked or superseded")
        revision = session.get(EntityRevisionRow, decision.entity_revision_id)
        head = self._stage_row(session, decision.project_id, StageName.STORYBOARD)
        if revision is None or (
            head.status != StageStatus.READY.value
            or head.entity_revision_id != decision.entity_revision_id
            or head.content_hash != decision.content_hash
            or revision.revision != decision.subject_revision
        ):
            raise InvalidTransitionError("reviewed selection approval is stale")
        gates = session.scalars(
            select(GateResultRow).where(
                GateResultRow.entity_revision_id == decision.entity_revision_id,
                GateResultRow.gate_set_version == decision.gate_set_version,
            )
        ).all()
        if not gates or any(not self._gate_result(gate).passed for gate in gates):
            raise InvalidTransitionError("reviewed selection approval gates are no longer passing")
        return decision

    @staticmethod
    def _selection_state_in_session(session: Session, project_id: str, now: datetime) -> VisualSelectionStateRow:
        state = session.get(VisualSelectionStateRow, project_id)
        if state is None:
            state = VisualSelectionStateRow(project_id=project_id, revision=0, updated_at=now)
            session.add(state)
            session.flush()
        return state

    def select_reviewed_keyframe(
        self,
        project_id: str,
        *,
        asset_id: str,
        shot_id: str,
        scene_id: str,
        expected_selection_revision: int,
        storyboard_revision: int,
        approval_id: str,
        compatibility_note: str,
        visual_intent_id: str,
        visual_intent_revision: int,
    ) -> dict[str, Any]:
        """Append an immutable reviewed binding under one lifecycle writer lease."""

        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            now = utc_now()
            state = self._selection_state_in_session(session, project_id, now)
            if state.revision != expected_selection_revision:
                raise RevisionConflictError("visual-selection", expected_selection_revision, state.revision)
            approval = self._approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("approval does not match the requested storyboard revision")
            head = self._stage_row(session, project_id, StageName.STORYBOARD)
            if head.revision != storyboard_revision or head.entity_revision_id != approval.entity_revision_id:
                raise RevisionConflictError("storyboard", storyboard_revision, head.revision)
            asset = session.get(ManagedAssetRow, asset_id)
            if asset is None or asset.project_id != project_id:
                raise NotFoundError(f"managed asset not found: {asset_id}")
            generated_candidate = session.scalar(
                select(ImageJobCandidateRow)
                .where(ImageJobCandidateRow.asset_id == asset_id)
                .order_by(ImageJobCandidateRow.created_at.desc())
                .limit(1)
            )
            if generated_candidate is not None:
                generated_job = session.get(ImageJobRow, generated_candidate.job_id)
                if generated_job is None or not self._image_job_is_current_in_session(session, generated_job):
                    raise InvalidTransitionError(
                        "image-job candidate is no longer applicable and cannot be selected"
                    )
            intent = session.get(VisualIntentRow, visual_intent_id)
            if (
                intent is None or intent.project_id != project_id or intent.asset_id != asset_id
                or intent.revision != visual_intent_revision
            ):
                raise InvalidTransitionError("reviewed keyframe must bind an exact current-project visual intent")
            latest_intent = self._latest_visual_intent_for_role_in_session(
                session, project_id, asset_id, intent.intent.get("role")
            )
            if latest_intent is None or latest_intent.id != intent.id:
                raise InvalidTransitionError("reviewed keyframe must bind the current visual intent revision")
            storyboard = self._load_stage_payload(session, project_id, StageName.STORYBOARD)
            shot = next((item for item in storyboard.shots if item.id == shot_id), None)
            if shot is None or shot.scene_id != scene_id:
                raise InvalidTransitionError("reviewed keyframe must target a current shot in its declared scene")
            state.revision += 1
            state.updated_at = now
            binding = ReviewedShotBindingRow(
                id=new_id(), project_id=project_id, asset_id=asset_id,
                visual_intent_id=intent.id, visual_intent_revision=intent.revision,
                storyboard_entity_revision_id=approval.entity_revision_id,
                approval_id=approval.id, shot_id=shot_id, scene_id=scene_id,
                storyboard_revision=storyboard_revision,
                selection_revision=state.revision, compatibility_note=compatibility_note,
                created_at=now,
            )
            session.add(binding)
            session.flush()
            return {
                "id": binding.id, "assetId": asset_id, "shotId": shot_id,
                "sceneId": scene_id, "selectionRevision": state.revision,
                "storyboardRevision": storyboard_revision, "visualIntentId": intent.id,
                "visualIntentRevision": intent.revision,
            }

    def create_still_preview(
        self,
        project_id: str,
        *,
        scene_id: str,
        shot_ids: list[str],
        expected_selection_revision: int,
        storyboard_revision: int,
        approval_id: str,
    ) -> dict[str, Any]:
        """Freeze one coherent, contiguous reviewed still sequence."""

        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            state = self._selection_state_in_session(session, project_id, utc_now())
            if state.revision != expected_selection_revision:
                raise RevisionConflictError("visual-selection", expected_selection_revision, state.revision)
            approval = self._approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("approval does not match the requested storyboard revision")
            storyboard = self._load_stage_payload(session, project_id, StageName.STORYBOARD)
            scene_shots = sorted(
                (item for item in storyboard.shots if item.scene_id == scene_id), key=lambda item: item.order
            )
            ordered_ids = [item.id for item in scene_shots]
            try:
                start = ordered_ids.index(shot_ids[0])
            except ValueError as error:
                raise InvalidTransitionError("preview shots must belong to the requested current scene") from error
            if ordered_ids[start : start + len(shot_ids)] != shot_ids:
                raise InvalidTransitionError("preview shots must be one contiguous scene subset in storyboard order")
            bindings = session.scalars(
                select(ReviewedShotBindingRow)
                .where(ReviewedShotBindingRow.project_id == project_id, ReviewedShotBindingRow.shot_id.in_(shot_ids))
                .order_by(ReviewedShotBindingRow.selection_revision.desc())
            ).all()
            latest: dict[str, ReviewedShotBindingRow] = {}
            for binding in bindings:
                latest.setdefault(binding.shot_id, binding)
            if set(latest) != set(shot_ids):
                raise InvalidTransitionError("preview has missing reviewed keyframes")
            frames = []
            by_id = {shot.id: shot for shot in scene_shots}
            for shot_id in shot_ids:
                binding = latest[shot_id]
                if (
                    binding.scene_id != scene_id
                    or binding.storyboard_entity_revision_id != approval.entity_revision_id
                    or binding.approval_id != approval.id
                ):
                    raise InvalidTransitionError("reviewed keyframe does not match the current approved storyboard")
                intent = session.get(VisualIntentRow, binding.visual_intent_id)
                if intent is None or intent.asset_id != binding.asset_id or intent.revision != binding.visual_intent_revision:
                    raise InvalidTransitionError("reviewed keyframe is missing its exact visual intent")
                if not self._reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding, approval=approval
                ):
                    raise InvalidTransitionError(
                        "reviewed keyframe is no longer current for preview admission"
                    )
                asset = session.get(ManagedAssetRow, binding.asset_id)
                if asset is None:
                    raise InvalidTransitionError("preview references unavailable managed media")
                frame: dict[str, Any] = {
                    "shotId": shot_id, "assetId": asset.id, "displayHash": asset.display_hash,
                    "durationMs": by_id[shot_id].duration_units,
                    "bindingId": binding.id, "visualIntentId": intent.id,
                    "visualIntentRevision": intent.revision,
                }
                identity_mapping = self._identity_mapping_for_binding_in_session(session, binding)
                if identity_mapping:
                    review = self.current_same_person_review_for_binding(session, project_id, binding)
                    if review is None:
                        raise InvalidTransitionError(
                            "identity-aware reviewed keyframe needs a current explicit same-person review before preview admission"
                        )
                    frame["identityReviewId"] = review.id
                    frame["identityReferenceDecisionIds"] = [item["referenceDecisionId"] for item in identity_mapping]
                frames.append(frame)
            manifest = {
                "projectionVersion": 1, "sceneId": scene_id, "shotIds": shot_ids,
                "storyboardRevision": storyboard_revision, "storyboardEntityRevisionId": approval.entity_revision_id,
                "approvalId": approval.id, "approvalGateSetVersion": approval.gate_set_version,
                # Database JSON keys are canonical stage strings already;
                # preserve them verbatim so the frozen receipt matches the
                # approval-closure projection used by ``preview_view``.
                "canonicalInputRevisions": dict(approval.canonical_input_revisions),
                "selectionRevision": state.revision, "frames": frames,
            }
            preview = StillPreviewRow(
                id=new_id(), project_id=project_id,
                storyboard_entity_revision_id=approval.entity_revision_id,
                approval_id=approval.id, scene_id=scene_id,
                selection_revision=state.revision, manifest=manifest,
                manifest_hash=stable_hash(manifest), created_at=utc_now(),
            )
            session.add(preview)
            session.flush()
            return {"id": preview.id, "manifest": preview.manifest, "manifestHash": preview.manifest_hash, "createdAt": _stored_utc(preview.created_at).isoformat()}

    def list_still_previews(self, project_id: str) -> list[dict[str, Any]]:
        with self._read() as session:
            self._project_row(session, project_id)
            previews = session.scalars(
                select(StillPreviewRow)
                .where(StillPreviewRow.project_id == project_id)
                .order_by(StillPreviewRow.created_at.desc(), StillPreviewRow.id.desc())
            ).all()
            return [
                {"id": item.id, "manifest": item.manifest, "manifestHash": item.manifest_hash, "createdAt": _stored_utc(item.created_at).isoformat()}
                for item in previews
            ]

    def visual_selection_revision(self, project_id: str) -> int:
        with self._read() as session:
            self._project_row(session, project_id)
            state = session.get(VisualSelectionStateRow, project_id)
            return state.revision if state is not None else 0

    def reviewed_preview_dependencies_current(self, project_id: str, frame: dict[str, Any]) -> bool:
        """Check only the frozen frame's reviewed binding and intent stream."""

        with self._read() as session:
            binding = session.get(ReviewedShotBindingRow, frame["bindingId"])
            if (
                binding is None or binding.project_id != project_id
                or binding.asset_id != frame["assetId"]
                or binding.visual_intent_id != frame.get("visualIntentId")
                or binding.visual_intent_revision != frame.get("visualIntentRevision")
            ):
                return False
            if not self._reviewed_binding_admission_eligible_in_session(session, project_id, binding):
                return False
            review_id = frame.get("identityReviewId")
            if review_id is None:
                # Historic/P0 frames and V3 character-free shots have no
                # same-person dependency. A visible V3 cast must have had a
                # review attached during preview admission.
                return not self._identity_mapping_for_binding_in_session(session, binding)
            review = session.get(SamePersonReviewRow, review_id)
            return review is not None and self._same_person_review_is_current_in_session(session, project_id, review)

    # The one P2 ledger ID is deliberately not project-scoped.  A new project,
    # process, or repository instance therefore cannot reset the pilot cap.
    _P2_LEDGER_ID = "wan-3.0-pilot-100-requested-seconds"

    @staticmethod
    def _video_job_id() -> str:
        return f"vj_{new_id().replace('-', '')}"

    @staticmethod
    def _video_job_dict(row: VideoJobRow, *, current: bool, selected: bool = False) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "state": row.state,
            "requestHash": row.request_hash, "snapshot": row.snapshot,
            "snapshotHash": row.snapshot_hash, "requestedSeconds": row.requested_seconds,
            "providerPredictionId": row.provider_prediction_id,
            "outputHash": row.output_hash, "observed": row.observed, "error": row.error,
            "current": current, "selected": selected,
            "createdAt": _stored_utc(row.created_at).isoformat(),
            "dispatchedAt": _stored_utc(row.dispatched_at).isoformat() if row.dispatched_at else None,
            "cancelRequestedAt": _stored_utc(row.cancel_requested_at).isoformat() if row.cancel_requested_at else None,
        }

    @staticmethod
    def _video_ledger_in_session(session: Session, now: datetime) -> VideoPilotLedgerRow:
        row = session.get(VideoPilotLedgerRow, SQLiteRepository._P2_LEDGER_ID)
        if row is None:
            row = VideoPilotLedgerRow(
                id=SQLiteRepository._P2_LEDGER_ID, limit_seconds=100,
                reserved_seconds=0, created_at=now, updated_at=now,
            )
            session.add(row)
            session.flush()
        return row

    @staticmethod
    def _video_job_tracks_paid_wan_pilot(row: VideoJobRow) -> bool:
        """Preserve V1 Wan accounting without charging local backends.

        Historical snapshots have no adapter or cost-policy fields.  Their
        exact documented Atlas capability record is the compatibility signal;
        unknown future contracts fail closed for accounting rather than being
        silently treated as paid Wan work.
        """

        provider = row.snapshot.get("provider")
        if not isinstance(provider, dict):
            return False
        if provider.get("costPolicy") == "wan_paid_pilot_v1":
            return True
        return (
            "costPolicy" not in provider
            and provider.get("provider") == "atlascloud"
            and provider.get("model") == "alibaba/wan-3.0/image-to-video"
            and provider.get("capabilityVersion") == 1
            and provider.get("imageField") == "image"
        )

    def _video_job_current_in_session(self, session: Session, row: VideoJobRow) -> bool:
        project = session.get(ProjectRow, row.project_id)
        snapshot = row.snapshot
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        try:
            approval = self._approval_is_active_in_session(session, str(snapshot["approvalId"]))
        except (KeyError, InvalidTransitionError, NotFoundError):
            return False
        binding = session.get(ReviewedShotBindingRow, snapshot.get("keyframe", {}).get("bindingId"))
        asset = session.get(ManagedAssetRow, snapshot.get("keyframe", {}).get("assetId"))
        identity = snapshot.get("identityLineage", [])
        if not isinstance(identity, list):
            return False
        review_id = snapshot.get("samePersonReviewId")
        if identity:
            try:
                bible = self._load_stage_payload(session, row.project_id, StageName.STORY_BIBLE)
            except (NotFoundError, SchemaResetRequiredError):
                return False
            characters = {character.id: character for character in bible.characters}
            for frozen in identity:
                if not isinstance(frozen, dict):
                    return False
                character = characters.get(frozen.get("characterId"))
                current = self._current_character_reference_in_session(session, row.project_id, character) if character else None
                if (
                    current is None
                    or current.id != frozen.get("referenceDecisionId")
                    or current.reference_revision != frozen.get("referenceRevision")
                    or current.character_context_hash != frozen.get("characterContextHash")
                ):
                    return False
                expected_assets = {item["assetId"]: item["originalHash"] for item in current.asset_hashes}
                frozen_assets = frozen.get("assets")
                if (
                    not isinstance(frozen_assets, list)
                    or len(frozen_assets) != len(expected_assets)
                    or any(
                        not isinstance(item, dict)
                        or expected_assets.get(item.get("assetId")) != item.get("originalHash")
                        for item in frozen_assets
                    )
                ):
                    return False
            # A generated V3 keyframe additionally needs its independent,
            # explicitly attributed same-person review. An imported selected
            # keyframe follows the separate provenance path: its attributed
            # keyframe-selection comparison and current character-reference
            # decision are frozen together below.
            if review_id is not None:
                review = session.get(SamePersonReviewRow, review_id)
                if review is None or not self._same_person_review_is_current_in_session(session, row.project_id, review):
                    return False
                if binding is None or review.binding_id != binding.id:
                    return False
        return bool(
            approval.project_id == row.project_id
            and approval.entity_revision_id == snapshot.get("storyboardEntityRevisionId")
            and binding is not None and asset is not None
            and binding.project_id == row.project_id
            and binding.shot_id == snapshot.get("shot", {}).get("id")
            and binding.selection_revision == snapshot.get("keyframe", {}).get("selectionRevision")
            and asset.original_hash == snapshot.get("keyframe", {}).get("originalHash")
            and self._reviewed_binding_admission_eligible_in_session(session, row.project_id, binding, approval=approval)
        )

    def video_budget(self) -> dict[str, Any]:
        with self._read() as session:
            row = session.get(VideoPilotLedgerRow, self._P2_LEDGER_ID)
            if row is None:
                return {"limitSeconds": 100, "reservedSeconds": 0, "remainingSeconds": 100, "attempts": []}
            events = session.scalars(select(VideoPilotLedgerEventRow).where(VideoPilotLedgerEventRow.ledger_id == row.id).order_by(VideoPilotLedgerEventRow.created_at, VideoPilotLedgerEventRow.id)).all()
            return {"limitSeconds": row.limit_seconds, "reservedSeconds": row.reserved_seconds, "remainingSeconds": row.limit_seconds - row.reserved_seconds, "attempts": [{"videoJobId": event.video_job_id, "event": event.event, "seconds": event.seconds, "createdAt": _stored_utc(event.created_at).isoformat()} for event in events]}

    def prepare_video_job(
        self, project_id: str, *, approval_id: str, shot_id: str, storyboard_revision: int,
        expected_selection_revision: int, idempotency_key: str, requested_seconds: int = 5,
        resolution: str = "720p", audio: bool = True,
        production_contract: VideoProductionContract | None = None,
    ) -> dict[str, Any]:
        """Freeze current audiovisual lineage and atomically reserve the shared cap."""
        if production_contract is None:
            if requested_seconds != 5 or resolution != "720p" or audio is not True:
                raise InvalidTransitionError("P2 only admits Wan 5-second 720p native-audio requests")
            compiler_version = "p2-wan-v1"
            provider_snapshot = {
                "provider": "atlascloud", "model": "alibaba/wan-3.0/image-to-video",
                "capabilityVersion": 1, "imageField": "image",
            }
            request_snapshot = {
                "durationSeconds": requested_seconds, "resolution": resolution, "audio": audio,
            }
            tracks_paid_wan_pilot = True
        else:
            requested_seconds = production_contract.requested_seconds
            resolution = production_contract.resolution
            audio = production_contract.audio
            compiler_version = (
                "p2-video-adapters-v2" if production_contract.profile_id is not None
                else "p2-video-adapters-v1"
            )
            provider_snapshot = production_contract.provider_snapshot()
            request_snapshot = production_contract.request_snapshot()
            tracks_paid_wan_pilot = production_contract.tracks_paid_wan_pilot
        with self._lifecycle_write() as session:
            now = utc_now()
            self._assert_active_project(self._project_row(session, project_id))
            approval = self._approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("video job approval does not match current storyboard")
            state = self._selection_state_in_session(session, project_id, now)
            if state.revision != expected_selection_revision:
                raise RevisionConflictError("visual-selection", expected_selection_revision, state.revision)
            storyboard = self._load_stage_payload(session, project_id, StageName.STORYBOARD)
            story_bible = self._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            scene_beats = self._load_stage_payload(session, project_id, StageName.SCENE_BEATS)
            shot = next((item for item in storyboard.shots if item.id == shot_id), None)
            if shot is None:
                raise InvalidTransitionError("video job must target one current storyboard shot")
            binding = session.scalar(select(ReviewedShotBindingRow).where(ReviewedShotBindingRow.project_id == project_id, ReviewedShotBindingRow.shot_id == shot_id).order_by(ReviewedShotBindingRow.selection_revision.desc()).limit(1))
            if binding is None or not self._reviewed_binding_admission_eligible_in_session(session, project_id, binding, approval=approval):
                raise InvalidTransitionError("video job needs the current reviewed selected keyframe")
            asset = session.get(ManagedAssetRow, binding.asset_id)
            if asset is None or asset.project_id != project_id:
                raise InvalidTransitionError("selected keyframe bytes are unavailable")
            # New catalog-backed H3 contracts use an exact profile geometry.
            # A mismatched source is normally rejected before a row,
            # reservation, or provider call. The narrow exception is an
            # explicit frozen letterbox request: the creator is asking the
            # gateway to retain black canvas as part of the input, not asking
            # Plotloom to waive profile, provenance, or output checks.
            if (
                production_contract is not None
                and production_contract.profile_id is not None
                and production_contract.width is not None
                and production_contract.height is not None
            ):
                expected_policy = (
                    "contain_pad"
                    if production_contract.allow_letterbox
                    else "reject_mismatch"
                )
                if production_contract.aspect_policy != expected_policy:
                    raise InvalidTransitionError(
                        "new H3 video job aspect policy does not match its frozen input-frame mode"
                    )
                if (
                    not production_contract.allow_letterbox
                    and not has_matching_aspect(
                        asset.width,
                        asset.height,
                        production_contract.width,
                        production_contract.height,
                    )
                ):
                    raise KeyframeAspectMismatchError(
                        asset.width,
                        asset.height,
                        production_contract.width,
                        production_contract.height,
                    )
            intent = session.get(VisualIntentRow, binding.visual_intent_id)
            if intent is None:
                raise InvalidTransitionError("selected keyframe visual intent is unavailable")
            context = self._image_job_resolved_context(shot=shot, storyboard=storyboard, story_bible=story_bible, scene_beats=scene_beats)
            generated_identity = self._identity_mapping_for_binding_in_session(session, binding)
            identity_lineage = generated_identity
            if identity_lineage is None:
                characters = {character.id: character for character in story_bible.characters}
                identity_lineage = []
                for character_id in shot.character_ids:
                    character = characters.get(character_id)
                    decision = self._current_character_reference_in_session(session, project_id, character) if character else None
                    if decision is None:
                        raise InvalidTransitionError(
                            "video job needs a current explicit character reference for each visible character"
                        )
                    identity_lineage.append({
                        "characterId": character_id,
                        "referenceDecisionId": decision.id,
                        "referenceRevision": decision.reference_revision,
                        "characterContextHash": decision.character_context_hash,
                        "assets": list(decision.asset_hashes),
                    })
            same_person_review = self.current_same_person_review_for_binding(session, project_id, binding)
            if generated_identity and same_person_review is None:
                raise InvalidTransitionError("identity-aware keyframe requires a current explicit same-person review before video admission")
            snapshot = {
                "snapshotVersion": (
                    1 if production_contract is None
                    else 3 if production_contract.profile_id is not None
                    else 2
                ),
                "compilerVersion": compiler_version, "approvalId": approval.id,
                "approvalGateSetVersion": approval.gate_set_version, "storyboardEntityRevisionId": approval.entity_revision_id,
                "storyboardRevision": storyboard_revision, "canonicalInputRevisions": dict(approval.canonical_input_revisions),
                "shot": shot.model_dump(mode="json", by_alias=True), "resolvedContext": context,
                "keyframe": {"bindingId": binding.id, "selectionRevision": binding.selection_revision,
                    "assetId": asset.id, "originalHash": asset.original_hash, "mimeType": asset.mime_type,
                    "width": asset.width, "height": asset.height, "visualIntentId": intent.id,
                    "visualIntentRevision": intent.revision, "intent": intent.intent},
                "identityLineage": identity_lineage,
                "samePersonReviewId": same_person_review.id if same_person_review is not None else None,
                "provider": provider_snapshot,
                "request": request_snapshot,
            }
            fingerprint = stable_hash({"snapshot": snapshot, "idempotencyKey": idempotency_key})
            existing = session.scalar(select(VideoJobRow).where(VideoJobRow.project_id == project_id, VideoJobRow.idempotency_key == idempotency_key))
            if existing is not None:
                if existing.request_hash != fingerprint:
                    raise IdempotencyConflictError("video-job idempotency key was reused with different frozen input")
                return self._video_job_dict(existing, current=self._video_job_current_in_session(session, existing)) | {"idempotent": True}
            ledger: VideoPilotLedgerRow | None = None
            if tracks_paid_wan_pilot:
                ledger = self._video_ledger_in_session(session, now)
                if ledger.reserved_seconds + requested_seconds > ledger.limit_seconds:
                    raise InvalidTransitionError("P2 requested-second allowance would be exceeded")
            job = VideoJobRow(id=self._video_job_id(), project_id=project_id, idempotency_key=idempotency_key,
                request_hash=fingerprint, snapshot=snapshot, snapshot_hash=stable_hash(snapshot), requested_seconds=requested_seconds,
                state="prepared", provider_prediction_id=None, output_uri=None, output_hash=None, observed=None, error=None,
                created_at=now, updated_at=now, dispatched_at=None, cancel_requested_at=None)
            if ledger is not None:
                ledger.reserved_seconds += requested_seconds
                ledger.updated_at = now
            session.add(job)
            if ledger is not None:
                session.add(VideoPilotLedgerEventRow(id=new_id(), ledger_id=ledger.id, video_job_id=job.id, event="reserved", seconds=requested_seconds, created_at=now))
            session.flush()
            return self._video_job_dict(job, current=True) | {"idempotent": False}

    def claim_video_dispatch(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        """Cross the durable dispatch boundary before any POST; never retry it."""
        with self._lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state != "prepared":
                raise InvalidTransitionError("video job cannot be submitted again; reconcile its existing attempt")
            if not self._video_job_current_in_session(session, job):
                raise InvalidTransitionError("video job frozen inputs are stale; prepare a new attempt")
            now = utc_now()
            job.state, job.dispatched_at, job.updated_at = "dispatching", now, now
            if self._video_job_tracks_paid_wan_pilot(job):
                ledger = self._video_ledger_in_session(session, now)
                session.add(VideoPilotLedgerEventRow(id=new_id(), ledger_id=ledger.id, video_job_id=job.id, event="dispatch_claimed", seconds=job.requested_seconds, created_at=now))
            return self._video_job_dict(job, current=True)

    def record_video_submission(self, project_id: str, video_job_id: str, prediction_id: str) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state != "dispatching" or job.provider_prediction_id is not None:
                raise InvalidTransitionError("video submission cannot be recorded from this state")
            job.provider_prediction_id, job.state, job.updated_at = prediction_id, "submitted", utc_now()
            return self._video_job_dict(job, current=self._video_job_current_in_session(session, job))

    def record_video_outcome_unknown(self, project_id: str, video_job_id: str, message: str) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"dispatching", "submitted"}:
                raise InvalidTransitionError("only a dispatched video job can have unknown outcome")
            job.state, job.error, job.updated_at = "outcome_unknown", message[:2_000], utc_now()
            return self._video_job_dict(job, current=False)

    def record_video_output(self, project_id: str, video_job_id: str, *, uri: str, digest: str, observed: dict[str, Any]) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"submitted", "retrieve_needed"}:
                raise InvalidTransitionError("video output can only be ingested from a known submitted attempt")
            job.output_uri, job.output_hash, job.observed, job.state, job.updated_at = uri, digest, observed, "ingested", utc_now()
            return self._video_job_dict(job, current=self._video_job_current_in_session(session, job))

    def record_video_retrieve_needed(self, project_id: str, video_job_id: str, message: str) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"submitted", "retrieve_needed"}:
                raise InvalidTransitionError("only a known submitted video can await retrieval")
            job.state, job.error, job.updated_at = "retrieve_needed", message[:2_000], utc_now()
            return self._video_job_dict(job, current=self._video_job_current_in_session(session, job))

    def record_video_remote_failed(self, project_id: str, video_job_id: str, code: str) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state not in {"submitted", "retrieve_needed"}:
                raise InvalidTransitionError("only a known submitted video can record remote failure")
            job.state, job.error, job.updated_at = "failed", code, utc_now()
            return self._video_job_dict(job, current=False)

    def recover_video_dispatches(self) -> list[str]:
        """A restart never replays a POST whose durable claim was entered."""
        with self._lifecycle_write() as session:
            rows = session.scalars(select(VideoJobRow).where(VideoJobRow.state == "dispatching")).all()
            now = utc_now()
            for row in rows:
                row.state, row.error, row.updated_at = "outcome_unknown", "restart_dispatch_outcome_unknown", now
            return [row.id for row in rows]

    def cancel_video_job(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state == "prepared":
                # Only this proven pre-dispatch path releases a reservation.
                if self._video_job_tracks_paid_wan_pilot(job):
                    ledger = self._video_ledger_in_session(session, utc_now())
                    ledger.reserved_seconds -= job.requested_seconds
                    ledger.updated_at = utc_now()
                    session.add(VideoPilotLedgerEventRow(id=new_id(), ledger_id=ledger.id, video_job_id=job.id, event="released_before_dispatch", seconds=-job.requested_seconds, created_at=utc_now()))
                job.state = "cancelled"
            elif job.state in {"dispatching", "submitted", "retrieve_needed", "outcome_unknown"}:
                # Cancellation is local adoption intent, not a fabricated
                # remote state. Keep the known task state recoverable.
                job.cancel_requested_at = utc_now()
            job.updated_at = utc_now()
            return self._video_job_dict(job, current=False)

    def list_video_jobs(self, project_id: str) -> list[dict[str, Any]]:
        with self._read() as session:
            self._project_row(session, project_id)
            rows = session.scalars(select(VideoJobRow).where(VideoJobRow.project_id == project_id).order_by(VideoJobRow.created_at.desc(), VideoJobRow.id.desc())).all()
            decisions = session.scalars(select(VideoReviewRow).where(VideoReviewRow.video_job_id.in_([row.id for row in rows])).order_by(VideoReviewRow.created_at.desc(), VideoReviewRow.id.desc())).all()
            latest: dict[str, VideoReviewRow] = {}
            jobs_by_id = {row.id: row for row in rows}
            latest_by_shot: dict[str, VideoReviewRow] = {}
            for decision in decisions:
                latest.setdefault(decision.video_job_id, decision)
                source = jobs_by_id.get(decision.video_job_id)
                if source is not None:
                    latest_by_shot.setdefault(str(source.snapshot.get("shot", {}).get("id")), decision)
            return [self._video_job_dict(row, current=self._video_job_current_in_session(session, row), selected=(latest_by_shot.get(str(row.snapshot.get("shot", {}).get("id"))) is not None and latest_by_shot[str(row.snapshot.get("shot", {}).get("id"))].video_job_id == row.id and latest_by_shot[str(row.snapshot.get("shot", {}).get("id"))].decision == "select" and self._video_job_current_in_session(session, row))) for row in rows]

    def get_video_output_storage(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        with self._read() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id or job.state != "ingested" or not job.output_uri or not job.output_hash:
                raise NotFoundError("locally ingested video candidate not found")
            return {"uri": job.output_uri, "hash": job.output_hash, "mimeType": "video/mp4"}

    def review_video_job(self, project_id: str, video_job_id: str, *, reviewer: str, decision: str, note: str) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError("video job not found")
            if job.state != "ingested" or not self._video_job_current_in_session(session, job):
                raise InvalidTransitionError("only a current locally ingested video candidate can be reviewed")
            review = VideoReviewRow(id=new_id(), video_job_id=job.id, reviewer=reviewer, decision=decision, note=note, created_at=utc_now())
            session.add(review)
            return {"id": review.id, "videoJobId": job.id, "reviewer": reviewer, "decision": decision, "note": note, "createdAt": _stored_utc(review.created_at).isoformat()}

    @staticmethod
    def _character_reference_context(character: Any) -> dict[str, Any]:
        """Freeze only identity-relevant canonical facts; display-name edits do not transfer identity."""

        payload = character.model_dump(mode="json", by_alias=True)
        return {
            "characterId": payload["id"],
            "description": payload["description"],
            "visualAnchors": payload["visualAnchors"],
            "traits": payload["traits"],
            "continuityRules": payload["continuityRules"],
            "allowedStates": payload["allowedStates"],
        }

    @staticmethod
    def _character_reference_state_in_session(
        session: Session, project_id: str, character_id: str, now: datetime
    ) -> CharacterReferenceStateRow:
        state = session.get(CharacterReferenceStateRow, (project_id, character_id))
        if state is None:
            state = CharacterReferenceStateRow(
                project_id=project_id, character_id=character_id, revision=0,
                active_decision_id=None, updated_at=now,
            )
            session.add(state)
            session.flush()
        return state

    @staticmethod
    def _reference_decision_dict(row: CharacterReferenceDecisionRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "characterId": row.character_id,
            "referenceRevision": row.reference_revision, "characterContext": row.character_context,
            "characterContextHash": row.character_context_hash, "primaryAssetId": row.primary_asset_id,
            "complementaryAssetIds": list(row.complementary_asset_ids), "assetHashes": list(row.asset_hashes),
            "reviewer": row.reviewer, "notes": row.notes, "current": current,
            "revokedAt": _stored_utc(row.revoked_at).isoformat() if row.revoked_at else None,
            "revokedBy": row.revoked_by, "revocationReason": row.revocation_reason,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _current_character_reference_in_session(
        self, session: Session, project_id: str, character: Any
    ) -> CharacterReferenceDecisionRow | None:
        state = session.get(CharacterReferenceStateRow, (project_id, character.id))
        if state is None or state.active_decision_id is None:
            return None
        decision = session.get(CharacterReferenceDecisionRow, state.active_decision_id)
        if decision is None or decision.project_id != project_id or decision.character_id != character.id:
            return None
        if decision.revoked_at is not None:
            return None
        context = self._character_reference_context(character)
        if decision.character_context_hash != stable_hash(context):
            return None
        asset_ids = [decision.primary_asset_id, *list(decision.complementary_asset_ids)]
        assets = [session.get(ManagedAssetRow, asset_id) for asset_id in asset_ids]
        if any(asset is None or asset.project_id != project_id for asset in assets):
            return None
        by_id = {item["assetId"]: item["originalHash"] for item in decision.asset_hashes}
        if any(asset is None or by_id.get(asset.id) != asset.original_hash for asset in assets):
            return None
        return decision

    def create_character_reference_decision(
        self,
        project_id: str,
        *,
        character_id: str,
        primary_asset_id: str,
        complementary_asset_ids: list[str],
        expected_reference_revision: int,
        reviewer: str,
        notes: str,
    ) -> dict[str, Any]:
        """Select, never infer, a compact stable-identity reference set."""

        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            bible = self._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            character = next((item for item in bible.characters if item.id == character_id), None)
            if character is None:
                raise InvalidTransitionError("character reference must name a current canonical character")
            now = utc_now()
            state = self._character_reference_state_in_session(session, project_id, character_id, now)
            if state.revision != expected_reference_revision:
                raise RevisionConflictError("character-reference", expected_reference_revision, state.revision)
            asset_ids = [primary_asset_id, *complementary_asset_ids]
            if len(asset_ids) > 3 or len(asset_ids) != len(set(asset_ids)):
                raise InvalidTransitionError("character reference requires one primary and at most two distinct complementary assets")
            assets = [session.get(ManagedAssetRow, asset_id) for asset_id in asset_ids]
            if any(asset is None or asset.project_id != project_id for asset in assets):
                raise NotFoundError("character reference asset not found in this project")
            context = self._character_reference_context(character)
            state.revision += 1
            state.updated_at = now
            decision = CharacterReferenceDecisionRow(
                id=new_id(), project_id=project_id, character_id=character_id,
                reference_revision=state.revision, character_context=context,
                character_context_hash=stable_hash(context), primary_asset_id=primary_asset_id,
                complementary_asset_ids=complementary_asset_ids,
                asset_hashes=[{"assetId": asset.id, "originalHash": asset.original_hash} for asset in assets if asset is not None],
                reviewer=reviewer.strip(), notes=notes.strip(), revoked_at=None, revoked_by=None,
                revocation_reason=None, created_at=now,
            )
            session.add(decision)
            session.flush()
            state.active_decision_id = decision.id
            session.flush()
            return self._reference_decision_dict(decision, current=True) | {"stateRevision": state.revision}

    def revoke_character_reference_decision(
        self,
        project_id: str,
        *,
        character_id: str,
        expected_reference_revision: int,
        reviewer: str,
        reason: str,
    ) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            self._assert_active_project(self._project_row(session, project_id))
            now = utc_now()
            state = self._character_reference_state_in_session(session, project_id, character_id, now)
            if state.revision != expected_reference_revision:
                raise RevisionConflictError("character-reference", expected_reference_revision, state.revision)
            if state.active_decision_id is None:
                raise InvalidTransitionError("character has no active reference decision to revoke")
            decision = session.get(CharacterReferenceDecisionRow, state.active_decision_id)
            if decision is None or decision.project_id != project_id:
                raise InvalidTransitionError("active character reference decision is unavailable")
            decision.revoked_at = now
            decision.revoked_by = reviewer.strip()
            decision.revocation_reason = reason.strip()
            state.revision += 1
            state.active_decision_id = None
            state.updated_at = now
            session.flush()
            return self._reference_decision_dict(decision, current=False) | {"stateRevision": state.revision}

    def list_character_reference_decisions(self, project_id: str) -> dict[str, Any]:
        with self._read() as session:
            self._project_row(session, project_id)
            bible = self._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            characters = {item.id: item for item in bible.characters}
            rows = session.scalars(
                select(CharacterReferenceDecisionRow)
                .where(CharacterReferenceDecisionRow.project_id == project_id)
                .order_by(CharacterReferenceDecisionRow.created_at.desc(), CharacterReferenceDecisionRow.id.desc())
            ).all()
            states = session.scalars(
                select(CharacterReferenceStateRow).where(CharacterReferenceStateRow.project_id == project_id)
            ).all()
            state_by_character = {item.character_id: item for item in states}
            return {
                "states": [{
                    "characterId": character_id, "revision": state.revision,
                    "activeDecisionId": state.active_decision_id,
                    "current": self._current_character_reference_in_session(session, project_id, characters[character_id]) is not None
                    if character_id in characters else False,
                } for character_id, state in sorted(state_by_character.items())],
                "decisions": [self._reference_decision_dict(
                    row,
                    current=(
                        row.revoked_at is None
                        and row.character_id in characters
                        and state_by_character.get(row.character_id) is not None
                        and state_by_character[row.character_id].active_decision_id == row.id
                        and self._current_character_reference_in_session(session, project_id, characters[row.character_id]) is not None
                    ),
                ) for row in rows],
            }

    @staticmethod
    def _proposal_dict(row: CharacterReferenceProposalRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "characterId": row.character_id,
            "parentCandidateAssetId": row.parent_candidate_asset_id, "request": row.request,
            "requestHash": row.request_hash, "state": row.state, "current": current,
            "exportedAt": _stored_utc(row.exported_at).isoformat() if row.exported_at else None,
            "cancelledAt": _stored_utc(row.cancelled_at).isoformat() if row.cancelled_at else None,
            "cancellationReason": row.cancellation_reason,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _proposal_is_current_in_session(
        self, session: Session, proposal: CharacterReferenceProposalRow
    ) -> bool:
        if proposal.state == "cancelled":
            return False
        project = session.get(ProjectRow, proposal.project_id)
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        try:
            bible = self._load_stage_payload(session, proposal.project_id, StageName.STORY_BIBLE)
        except (NotFoundError, SchemaResetRequiredError):
            return False
        character = next((item for item in bible.characters if item.id == proposal.character_id), None)
        snapshot = proposal.request.get("frozenSnapshot")
        if character is None or not isinstance(snapshot, dict):
            return False
        return snapshot.get("characterContextHash") == stable_hash(self._character_reference_context(character))

    def prepare_character_reference_proposal(
        self,
        project_id: str,
        *,
        character_id: str,
        story_bible_revision: int,
        visual_direction: str,
        parent_candidate_asset_id: str | None,
    ) -> dict[str, Any]:
        """Freeze a story-first exploratory request without creating a fake Shot or Approval."""

        with self._lifecycle_write() as session:
            self._assert_active_project(self._project_row(session, project_id))
            head = self._stage_row(session, project_id, StageName.STORY_BIBLE)
            if head.revision != story_bible_revision:
                raise RevisionConflictError("story-bible", story_bible_revision, head.revision)
            bible = self._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            character = next((item for item in bible.characters if item.id == character_id), None)
            if character is None:
                raise InvalidTransitionError("character reference proposal must name a current canonical character")
            references: list[dict[str, Any]] = []
            if parent_candidate_asset_id is not None:
                candidate = session.scalar(
                    select(CharacterReferenceProposalCandidateRow)
                    .where(CharacterReferenceProposalCandidateRow.asset_id == parent_candidate_asset_id)
                    .order_by(CharacterReferenceProposalCandidateRow.created_at.desc()).limit(1)
                )
                parent = session.get(CharacterReferenceProposalRow, candidate.proposal_id) if candidate else None
                asset = session.get(ManagedAssetRow, parent_candidate_asset_id)
                if (
                    candidate is None or parent is None or asset is None or asset.project_id != project_id
                    or parent.character_id != character_id or not self._proposal_is_current_in_session(session, parent)
                ):
                    raise InvalidTransitionError("proposal refinement must name a current candidate for the same character")
                references.append({
                    "assetId": asset.id, "role": "parent_output", "required": True,
                    "originalHash": asset.original_hash, "mimeType": asset.mime_type,
                    "byteSize": asset.byte_size, "width": asset.width, "height": asset.height,
                })
            context = self._character_reference_context(character)
            job_id = self._image_job_id()
            snapshot = {
                "snapshotVersion": 3, "compilerVersion": "plotloom.character-reference-proposal.v1",
                "projectId": project_id, "target": "character_reference_proposal",
                "characterId": character_id, "storyBibleRevision": story_bible_revision,
                "storyBibleEntityRevisionId": head.entity_revision_id,
                "characterContext": context, "characterContextHash": stable_hash(context),
                "visualDirection": visual_direction.strip(), "references": references,
                "authority": "exploratory_only_no_storyboard_approval_or_keyframe_selection",
            }
            request = {
                "schemaVersion": 3, "jobId": job_id, "executionContract": "codex_specialist.v2",
                "specialistPreflight": {"version": "p1.5-pin.v1", "skillVersion": "plotloom-image-specialist.v3", "executionContract": "codex_specialist.v2"},
                "kind": "refinement" if parent_candidate_asset_id else "original",
                "target": "character_reference_proposal", "frozenSnapshot": snapshot,
            }
            proposal = CharacterReferenceProposalRow(
                id=job_id, project_id=project_id, character_id=character_id,
                parent_candidate_asset_id=parent_candidate_asset_id, request=request,
                request_hash=stable_hash(request), state="prepared", exported_at=None,
                cancelled_at=None, cancellation_reason=None, created_at=utc_now(),
            )
            session.add(proposal)
            session.flush()
            return {"proposal": self._proposal_dict(proposal, current=True)}

    def character_reference_proposal_package_sources(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._read() as session:
            self._assert_active_project(self._project_row(session, project_id))
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            if not self._proposal_is_current_in_session(session, proposal):
                raise InvalidTransitionError("character reference proposal is no longer current and cannot be copied")
            sources: list[dict[str, Any]] = []
            for reference in proposal.request["frozenSnapshot"].get("references", []):
                asset = session.get(ManagedAssetRow, reference.get("assetId"))
                if asset is None or asset.project_id != project_id or asset.original_hash != reference.get("originalHash"):
                    raise InvalidTransitionError("frozen proposal reference bytes are unavailable")
                sources.append({
                    "role": reference["role"], "contentHash": asset.original_hash,
                    "mimeType": asset.mime_type, "originalUri": asset.original_uri,
                })
            return {"proposal": self._proposal_dict(proposal, current=True), "references": sources}

    def mark_character_reference_proposal_exported(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            self._assert_active_project(self._project_row(session, project_id))
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            if not self._proposal_is_current_in_session(session, proposal):
                raise InvalidTransitionError("character reference proposal is no longer current and cannot be copied")
            if proposal.exported_at is None:
                proposal.exported_at = utc_now()
                proposal.state = "exported"
                session.flush()
            return self._proposal_dict(proposal, current=True)

    def character_reference_proposal_delivery_context(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        with self._read() as session:
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            return self._proposal_dict(proposal, current=self._proposal_is_current_in_session(session, proposal))

    def record_character_reference_proposal_rejection(self, project_id: str, proposal_id: str, code: str) -> None:
        with self._lifecycle_write() as session:
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            session.add(CharacterReferenceProposalDeliveryRow(
                id=new_id(), proposal_id=proposal_id, delivery_id=None, manifest=None, manifest_hash=None,
                state="rejected", diagnostic_code=code, created_at=utc_now(),
            ))

    def record_character_reference_proposal_delivery(
        self,
        project_id: str,
        proposal_id: str,
        *,
        delivery_id: str,
        manifest: dict[str, Any],
        manifest_hash: str,
        outputs: list[dict[str, Any]],
        publish: Callable[[dict[str, Any]], tuple[str, str]],
    ) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            proposal = session.get(CharacterReferenceProposalRow, proposal_id)
            if proposal is None or proposal.project_id != project_id:
                raise NotFoundError("character reference proposal not found")
            existing = session.scalar(
                select(CharacterReferenceProposalDeliveryRow)
                .where(CharacterReferenceProposalDeliveryRow.proposal_id == proposal_id, CharacterReferenceProposalDeliveryRow.delivery_id == delivery_id)
                .limit(1)
            )
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise ImageJobError("delivery_conflict", "proposal delivery identity was already recorded with different content")
                candidates = session.scalars(
                    select(CharacterReferenceProposalCandidateRow)
                    .where(CharacterReferenceProposalCandidateRow.delivery_id == existing.id)
                    .order_by(CharacterReferenceProposalCandidateRow.created_at, CharacterReferenceProposalCandidateRow.id)
                ).all()
                return {"deliveryId": delivery_id, "state": existing.state, "diagnosticCode": existing.diagnostic_code,
                        "idempotent": True, "candidates": [self._proposal_candidate_dict(session, item) for item in candidates]}
            finalized = session.scalar(
                select(CharacterReferenceProposalDeliveryRow)
                .where(CharacterReferenceProposalDeliveryRow.proposal_id == proposal_id, CharacterReferenceProposalDeliveryRow.delivery_id.is_not(None))
                .limit(1)
            )
            if finalized is not None:
                raise ImageJobError("delivery_finalized", "character proposal already has a final delivery")
            current = proposal.state in {"exported", "delivered"} and self._proposal_is_current_in_session(session, proposal)
            delivery = CharacterReferenceProposalDeliveryRow(
                id=new_id(), proposal_id=proposal_id, delivery_id=delivery_id, manifest=manifest,
                manifest_hash=manifest_hash, state="accepted" if current else "inapplicable",
                diagnostic_code=None if current else "late_or_stale_delivery", created_at=utc_now(),
            )
            session.add(delivery)
            session.flush()
            if not current:
                return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": delivery.diagnostic_code,
                        "idempotent": False, "candidates": []}
            candidates: list[CharacterReferenceProposalCandidateRow] = []
            for output in outputs:
                original_uri, display_uri = publish(output)
                asset = ManagedAssetRow(
                    id=new_id(), project_id=project_id, original_uri=original_uri,
                    original_hash=output["originalHash"], display_uri=display_uri,
                    display_hash=output["displayHash"], mime_type=output["mimeType"], byte_size=output["byteSize"],
                    width=output["width"], height=output["height"], created_at=utc_now(),
                )
                session.add(asset)
                session.flush()
                session.add(ManagedAssetProvenanceRow(
                    id=new_id(), project_id=project_id, asset_id=asset.id,
                    declaration={
                        "origin": "character_reference_proposal", "rights": "unknown", "proposalId": proposal.id,
                        "rightsNote": None, "declaredAdditions": [], "deliveryId": delivery_id,
                        "outputFilename": output["filename"], "actualPrompt": manifest["actualPrompt"],
                        "toolEvidence": manifest["toolEvidence"], "executorProvenance": manifest.get("executorProvenance"),
                        "limitations": manifest.get("limitations", []),
                    }, created_at=utc_now(),
                ))
                candidate = CharacterReferenceProposalCandidateRow(
                    id=new_id(), proposal_id=proposal.id, delivery_id=delivery.id, asset_id=asset.id,
                    output_filename=output["filename"], output_hash=output["originalHash"],
                    role=output["role"], created_at=utc_now(),
                )
                session.add(candidate)
                candidates.append(candidate)
            proposal.state = "delivered"
            session.flush()
            return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": None,
                    "idempotent": False, "candidates": [self._proposal_candidate_dict(session, item) for item in candidates]}

    @staticmethod
    def _proposal_candidate_dict(session: Session, row: CharacterReferenceProposalCandidateRow) -> dict[str, Any]:
        asset = session.get(ManagedAssetRow, row.asset_id)
        return {
            "id": row.id, "assetId": row.asset_id, "proposalId": row.proposal_id,
            "outputFilename": row.output_filename, "outputHash": row.output_hash, "role": row.role,
            "asset": SQLiteRepository._managed_asset_dict(asset) if asset is not None else None,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def list_character_reference_proposals(self, project_id: str) -> list[dict[str, Any]]:
        with self._read() as session:
            self._project_row(session, project_id)
            proposals = session.scalars(
                select(CharacterReferenceProposalRow).where(CharacterReferenceProposalRow.project_id == project_id)
                .order_by(CharacterReferenceProposalRow.created_at.desc(), CharacterReferenceProposalRow.id.desc())
            ).all()
            result: list[dict[str, Any]] = []
            for proposal in proposals:
                deliveries = session.scalars(
                    select(CharacterReferenceProposalDeliveryRow)
                    .where(CharacterReferenceProposalDeliveryRow.proposal_id == proposal.id)
                    .order_by(CharacterReferenceProposalDeliveryRow.created_at.desc(), CharacterReferenceProposalDeliveryRow.id.desc())
                ).all()
                result.append({
                    **self._proposal_dict(proposal, current=self._proposal_is_current_in_session(session, proposal)),
                    "deliveries": [{
                        "id": delivery.id, "deliveryId": delivery.delivery_id, "state": delivery.state,
                        "diagnosticCode": delivery.diagnostic_code, "manifestHash": delivery.manifest_hash,
                        "createdAt": _stored_utc(delivery.created_at).isoformat(),
                        "candidates": [self._proposal_candidate_dict(session, item) for item in session.scalars(
                            select(CharacterReferenceProposalCandidateRow)
                            .where(CharacterReferenceProposalCandidateRow.delivery_id == delivery.id)
                            .order_by(CharacterReferenceProposalCandidateRow.created_at, CharacterReferenceProposalCandidateRow.id)
                        ).all()],
                    } for delivery in deliveries],
                })
            return result

    @staticmethod
    def _same_person_review_state_in_session(
        session: Session, project_id: str, now: datetime
    ) -> SamePersonReviewStateRow:
        state = session.get(SamePersonReviewStateRow, project_id)
        if state is None:
            state = SamePersonReviewStateRow(project_id=project_id, revision=0, updated_at=now)
            session.add(state)
            session.flush()
        return state

    @staticmethod
    def _same_person_review_dict(row: SamePersonReviewRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "bindingId": row.binding_id,
            "reviewRevision": row.review_revision, "referenceBindings": list(row.reference_bindings),
            "comparisons": list(row.comparisons), "reviewer": row.reviewer, "notes": row.notes,
            "current": current, "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _identity_mapping_for_binding_in_session(
        self, session: Session, binding: ReviewedShotBindingRow
    ) -> list[dict[str, Any]] | None:
        candidate = session.scalar(
            select(ImageJobCandidateRow)
            .where(ImageJobCandidateRow.asset_id == binding.asset_id)
            .order_by(ImageJobCandidateRow.created_at.desc()).limit(1)
        )
        if candidate is None:
            return None
        job = session.get(ImageJobRow, candidate.job_id)
        if job is None or job.request.get("schemaVersion") != 3:
            return None
        snapshot = job.request.get("frozenSnapshot")
        mapping = snapshot.get("characterIdentity") if isinstance(snapshot, dict) else None
        if not isinstance(mapping, list) or any(not isinstance(item, dict) for item in mapping):
            return None
        return mapping

    def _same_person_review_is_current_in_session(
        self, session: Session, project_id: str, review: SamePersonReviewRow
    ) -> bool:
        binding = session.get(ReviewedShotBindingRow, review.binding_id)
        if binding is None or binding.project_id != project_id:
            return False
        try:
            approval = self._approval_is_active_in_session(session, binding.approval_id)
        except (InvalidTransitionError, NotFoundError):
            return False
        if not self._reviewed_binding_admission_eligible_in_session(session, project_id, binding, approval=approval):
            return False
        mapping = self._identity_mapping_for_binding_in_session(session, binding)
        if mapping is None:
            return False
        if any(item.get("judgment") != "pass" for item in review.comparisons):
            return False
        expected = {item.get("characterId"): item for item in mapping}
        review_refs = {item.get("characterId"): item for item in review.reference_bindings}
        if set(expected) != set(review_refs):
            return False
        try:
            bible = self._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
        except (NotFoundError, SchemaResetRequiredError):
            return False
        characters = {item.id: item for item in bible.characters}
        for character_id, frozen in expected.items():
            character = characters.get(character_id)
            current = self._current_character_reference_in_session(session, project_id, character) if character else None
            reviewed = review_refs[character_id]
            if (
                current is None
                or current.id != frozen.get("referenceDecisionId")
                or current.reference_revision != frozen.get("referenceRevision")
                or reviewed.get("referenceDecisionId") != current.id
                or reviewed.get("referenceRevision") != current.reference_revision
                or reviewed.get("assetHashes") != [item.get("originalHash") for item in frozen.get("assets", [])]
            ):
                return False
        return True

    def record_same_person_review(
        self,
        project_id: str,
        *,
        binding_id: str,
        expected_review_revision: int,
        reviewer: str,
        comparisons: list[dict[str, Any]],
        notes: str,
    ) -> dict[str, Any]:
        """Persist an explicit human judgment about a v3 generated keyframe."""

        with self._lifecycle_write() as session:
            self._assert_active_project(self._project_row(session, project_id))
            binding = session.get(ReviewedShotBindingRow, binding_id)
            if binding is None or binding.project_id != project_id:
                raise NotFoundError("reviewed keyframe binding not found")
            mapping = self._identity_mapping_for_binding_in_session(session, binding)
            if mapping is None:
                raise InvalidTransitionError("same-person review is only required for identity-aware generated keyframes")
            expected_ids = [item["characterId"] for item in mapping]
            comparison_ids = [item["characterId"] for item in comparisons]
            if comparison_ids != expected_ids:
                raise InvalidTransitionError("same-person review must cover each frozen visible character in role-mapped order")
            now = utc_now()
            state = self._same_person_review_state_in_session(session, project_id, now)
            if state.revision != expected_review_revision:
                raise RevisionConflictError("same-person-review", expected_review_revision, state.revision)
            reference_bindings = [{
                "characterId": item["characterId"], "referenceDecisionId": item["referenceDecisionId"],
                "referenceRevision": item["referenceRevision"],
                "assetHashes": [asset["originalHash"] for asset in item["assets"]],
            } for item in mapping]
            state.revision += 1
            state.updated_at = now
            review = SamePersonReviewRow(
                id=new_id(), project_id=project_id, binding_id=binding_id, review_revision=state.revision,
                reference_bindings=reference_bindings, comparisons=comparisons, reviewer=reviewer.strip(),
                notes=notes.strip(), created_at=now,
            )
            session.add(review)
            session.flush()
            return self._same_person_review_dict(review, current=self._same_person_review_is_current_in_session(session, project_id, review)) | {"stateRevision": state.revision}

    def list_same_person_reviews(self, project_id: str) -> dict[str, Any]:
        with self._read() as session:
            self._project_row(session, project_id)
            state = session.get(SamePersonReviewStateRow, project_id)
            rows = session.scalars(
                select(SamePersonReviewRow).where(SamePersonReviewRow.project_id == project_id)
                .order_by(SamePersonReviewRow.created_at.desc(), SamePersonReviewRow.id.desc())
            ).all()
            return {"revision": state.revision if state else 0, "reviews": [
                self._same_person_review_dict(row, current=self._same_person_review_is_current_in_session(session, project_id, row))
                for row in rows
            ]}

    def current_same_person_review_for_binding(
        self, session: Session, project_id: str, binding: ReviewedShotBindingRow
    ) -> SamePersonReviewRow | None:
        mapping = self._identity_mapping_for_binding_in_session(session, binding)
        if mapping is None:
            return None
        rows = session.scalars(
            select(SamePersonReviewRow)
            .where(SamePersonReviewRow.project_id == project_id, SamePersonReviewRow.binding_id == binding.id)
            .order_by(SamePersonReviewRow.review_revision.desc())
        ).all()
        return next((row for row in rows if self._same_person_review_is_current_in_session(session, project_id, row)), None)

    @staticmethod
    def _image_job_id() -> str:
        return f"ij_{new_id().replace('-', '')}"

    @staticmethod
    def _image_job_dict(row: ImageJobRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "productionUnitId": row.production_unit_id,
            "parentJobId": row.parent_job_id, "parentCandidateAssetId": row.parent_candidate_asset_id,
            "request": row.request, "requestHash": row.request_hash, "state": row.state,
            "current": current,
            "exportedAt": _stored_utc(row.exported_at).isoformat() if row.exported_at else None,
            "cancelledAt": _stored_utc(row.cancelled_at).isoformat() if row.cancelled_at else None,
            "cancellationReason": row.cancellation_reason,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    @staticmethod
    def _production_unit_dict(row: ProductionUnitRow) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "approvalId": row.approval_id,
            "shotId": row.shot_id, "sceneId": row.scene_id,
            "storyboardRevision": row.storyboard_revision, "snapshot": row.snapshot,
            "snapshotHash": row.snapshot_hash, "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def _image_job_is_current_in_session(self, session: Session, job: ImageJobRow) -> bool:
        if job.state == "cancelled":
            return False
        project = session.get(ProjectRow, job.project_id)
        if project is None or ProjectLifecycleStatus(project.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
            return False
        unit = session.get(ProductionUnitRow, job.production_unit_id)
        if unit is None or unit.project_id != job.project_id:
            return False
        try:
            approval = self._approval_is_active_in_session(session, unit.approval_id)
        except (InvalidTransitionError, NotFoundError):
            return False
        if not (
            approval.project_id == job.project_id
            and approval.entity_revision_id == unit.storyboard_entity_revision_id
            and approval.subject_revision == unit.storyboard_revision
        ):
            return False

        # V1 original jobs predate the reviewed-keyframe refinement binding and
        # intentionally retain their historical currentness rule.  V2
        # refinements freeze an exact creator-reviewed VisualIntent, so a new
        # intent revision after Copy makes the resulting delivery inapplicable
        # rather than silently applying it to a changed presentation contract.
        reviewed_intent = unit.snapshot.get("reviewedVisualIntent")
        if reviewed_intent is not None:
            if not isinstance(reviewed_intent, dict):
                return False
            binding_id = reviewed_intent.get("bindingId")
            if not isinstance(binding_id, str):
                return False
            binding = session.get(ReviewedShotBindingRow, binding_id)
            if binding is None:
                return False
            if (
                binding.project_id != job.project_id
                or binding.shot_id != unit.shot_id
                or binding.asset_id != reviewed_intent.get("assetId")
                or binding.selection_revision != reviewed_intent.get("selectionRevision")
                or binding.visual_intent_id != reviewed_intent.get("visualIntentId")
                or binding.visual_intent_revision != reviewed_intent.get("visualIntentRevision")
            ):
                return False
            if not self._reviewed_binding_admission_eligible_in_session(
                session, job.project_id, binding, approval=approval
            ):
                return False

        # V3 freezes one explicit reference decision per visible character.
        # This runs after refinement validation so a parent image cannot
        # override or mask an invalid identity dependency.
        if unit.snapshot.get("snapshotVersion") != 3:
            return True
        identity = unit.snapshot.get("characterIdentity")
        frozen_shot = unit.snapshot.get("shot")
        if not isinstance(identity, list) or not isinstance(frozen_shot, dict):
            return False
        visible = frozen_shot.get("characterIds")
        if (
            not isinstance(visible, list)
            or any(not isinstance(item, dict) for item in identity)
            or [item.get("characterId") for item in identity] != visible
        ):
            return False
        try:
            bible = self._load_stage_payload(session, job.project_id, StageName.STORY_BIBLE)
        except (NotFoundError, SchemaResetRequiredError):
            return False
        characters = {item.id: item for item in bible.characters}
        for mapping in identity:
            if not isinstance(mapping, dict):
                return False
            character = characters.get(mapping.get("characterId"))
            if character is None:
                return False
            decision = self._current_character_reference_in_session(session, job.project_id, character)
            if (
                decision is None
                or decision.id != mapping.get("referenceDecisionId")
                or decision.reference_revision != mapping.get("referenceRevision")
                or decision.character_context_hash != mapping.get("characterContextHash")
            ):
                return False
            expected_assets = [decision.primary_asset_id, *list(decision.complementary_asset_ids)]
            frozen_assets = mapping.get("assets")
            if not isinstance(frozen_assets, list) or [item.get("assetId") for item in frozen_assets if isinstance(item, dict)] != expected_assets:
                return False
            hashes = {item["assetId"]: item["originalHash"] for item in decision.asset_hashes}
            if any(not isinstance(item, dict) or hashes.get(item.get("assetId")) != item.get("originalHash") for item in frozen_assets):
                return False
        return True

    @staticmethod
    def _image_job_resolved_context(
        *,
        shot: Any,
        storyboard: Any,
        story_bible: Any,
        scene_beats: Any,
    ) -> dict[str, Any]:
        """Resolve just the authored facts a specialist needs for one Shot.

        The frozen projection deliberately travels only through canonical
        objects already admitted by the approved storyboard.  It does not
        expose project-wide notes, provider configuration, or any filesystem
        location.  Models from the retained V1 schema do not carry V2 dialogue
        and state links, so their corresponding narrow lists are empty.
        """

        def dump(value: Any) -> dict[str, Any]:
            return value.model_dump(mode="json", by_alias=True)

        def ordered_unique(values: Sequence[str | None]) -> list[str]:
            seen: set[str] = set()
            result: list[str] = []
            for value in values:
                if value is not None and value not in seen:
                    seen.add(value)
                    result.append(value)
            return result

        scene = next((item for item in scene_beats.scenes if item.id == shot.scene_id), None)
        linked_beat_ids = ordered_unique([
            link.beat_id for link in storyboard.shot_beat_links if link.shot_id == shot.id
        ])
        beats_by_id = {item.id: item for item in scene_beats.beats}
        beats = [beats_by_id[beat_id] for beat_id in linked_beat_ids if beat_id in beats_by_id]
        cue_ids = ordered_unique(list(getattr(shot, "cue_ids", [])))
        cues_by_id = {
            item.id: item for item in getattr(scene_beats, "dialogue_cues", [])
        }
        cues = [cues_by_id[cue_id] for cue_id in cue_ids if cue_id in cues_by_id]

        required_entity_states = list(getattr(shot, "required_entity_states", []))
        # `Shot.character_ids` is the authoritative on-screen cast. Scene
        # members, dialogue speakers, and state references remain useful
        # narrative context but cannot silently become visible people in an
        # image request or identity-reference mapping.
        character_ids = ordered_unique(list(getattr(shot, "character_ids", [])))
        prop_ids = ordered_unique([
            *list(getattr(shot, "prop_ids", [])),
            *(state.entity_id for state in required_entity_states if state.entity_type == "prop"),
        ])
        location_ids = ordered_unique([
            getattr(shot, "location_id", None),
            None if scene is None else getattr(scene, "location_id", None),
            *(state.entity_id for state in required_entity_states if state.entity_type == "location"),
        ])
        characters_by_id = {item.id: item for item in story_bible.characters}
        props_by_id = {item.id: item for item in story_bible.props}
        locations_by_id = {item.id: item for item in story_bible.locations}

        return {
            "scene": dump(scene) if scene is not None else None,
            "beats": [dump(item) for item in beats],
            "dialogueCues": [dump(item) for item in cues],
            "characters": [dump(characters_by_id[item_id]) for item_id in character_ids if item_id in characters_by_id],
            "locations": [dump(locations_by_id[item_id]) for item_id in location_ids if item_id in locations_by_id],
            "props": [dump(props_by_id[item_id]) for item_id in prop_ids if item_id in props_by_id],
            "requiredEntityStates": [dump(item) for item in required_entity_states],
        }

    def prepare_image_job(
        self,
        project_id: str,
        *,
        approval_id: str,
        shot_id: str,
        storyboard_revision: int,
        parent_candidate_asset_id: str | None = None,
        keyframe_adaptation: dict[str, Any] | None = None,
        presentation_change: str,
        contract_version: int = 2,
        consumed_draft: tuple[str, int, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Freeze an approved single-shot production unit and manual request."""

        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            approval = self._approval_is_active_in_session(session, approval_id)
            if approval.project_id != project_id or approval.subject_revision != storyboard_revision:
                raise InvalidTransitionError("image job approval does not match the requested storyboard revision")
            storyboard = self._load_stage_payload(session, project_id, StageName.STORYBOARD)
            story_bible = self._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            scene_beats = self._load_stage_payload(session, project_id, StageName.SCENE_BEATS)
            head = self._stage_row(session, project_id, StageName.STORYBOARD)
            if head.revision != storyboard_revision or head.entity_revision_id != approval.entity_revision_id:
                raise RevisionConflictError("storyboard", storyboard_revision, head.revision)
            shot = next((item for item in storyboard.shots if item.id == shot_id), None)
            if shot is None:
                raise InvalidTransitionError("image job must target one current storyboard shot")

            if consumed_draft is not None:
                entity_id, draft_revision, draft_payload = consumed_draft
                self._consume_exact_authoring_draft_in_session(
                    session,
                    project,
                    editor_scope="image_direction",
                    entity_id=entity_id,
                    expected_draft_revision=draft_revision,
                    canonical_base_revision=head.revision,
                    canonical_payload=draft_payload,
                )

            if contract_version not in {2, 3}:
                raise InvalidTransitionError("image job contract version is unsupported")
            if keyframe_adaptation is not None and (
                parent_candidate_asset_id is not None or contract_version != 3
            ):
                raise InvalidTransitionError(
                    "keyframe adaptation requires the identity-aware original-image path"
                )

            references: list[dict[str, Any]] = []
            identity_mappings: list[dict[str, Any]] = []
            if contract_version == 3:
                characters_by_id = {item.id: item for item in story_bible.characters}
                for character_id in shot.character_ids:
                    character = characters_by_id.get(character_id)
                    if character is None:
                        raise InvalidTransitionError("shot character membership is not resolvable in the current story bible")
                    decision = self._current_character_reference_in_session(session, project_id, character)
                    if decision is None:
                        raise ImageJobError(
                            "identity_reference_missing",
                            f"shot character {character_id} needs an explicitly current character reference before an identity-aware job can be prepared",
                        )
                    asset_ids = [decision.primary_asset_id, *list(decision.complementary_asset_ids)]
                    assets = [session.get(ManagedAssetRow, asset_id) for asset_id in asset_ids]
                    if any(asset is None or asset.project_id != project_id for asset in assets):
                        raise ImageJobError("identity_reference_missing", "character reference asset is unavailable")
                    identity_assets: list[dict[str, Any]] = []
                    for ordinal, asset in enumerate(assets):
                        assert asset is not None
                        entry = {
                            "assetId": asset.id, "role": "character_identity", "characterId": character_id,
                            "referenceDecisionId": decision.id, "referenceRevision": decision.reference_revision,
                            "view": "primary" if ordinal == 0 else "complementary",
                            "originalHash": asset.original_hash, "mimeType": asset.mime_type,
                            "byteSize": asset.byte_size, "width": asset.width, "height": asset.height,
                        }
                        references.append(entry)
                        identity_assets.append({
                            "assetId": asset.id, "originalHash": asset.original_hash,
                            "view": entry["view"],
                        })
                    identity_mappings.append({
                        "characterId": character_id, "referenceDecisionId": decision.id,
                        "referenceRevision": decision.reference_revision,
                        "characterContextHash": decision.character_context_hash,
                        "assets": identity_assets,
                    })

            parent_job_id: str | None = None
            reviewed_visual_intent: dict[str, Any] | None = None
            if parent_candidate_asset_id is not None:
                candidate = session.scalar(
                    select(ImageJobCandidateRow)
                    .where(ImageJobCandidateRow.asset_id == parent_candidate_asset_id)
                    .order_by(ImageJobCandidateRow.created_at.desc()).limit(1)
                )
                parent_job = session.get(ImageJobRow, candidate.job_id) if candidate else None
                asset = session.get(ManagedAssetRow, parent_candidate_asset_id)
                if (
                    candidate is None or parent_job is None or asset is None or asset.project_id != project_id
                    or not self._image_job_is_current_in_session(session, parent_job)
                ):
                    raise InvalidTransitionError("refinement must name a current Plotloom image-job candidate")
                binding = session.scalar(
                    select(ReviewedShotBindingRow)
                    .where(
                        ReviewedShotBindingRow.project_id == project_id,
                        ReviewedShotBindingRow.shot_id == shot_id,
                    )
                    .order_by(ReviewedShotBindingRow.selection_revision.desc())
                    .limit(1)
                )
                if (
                    binding is None
                    or binding.asset_id != parent_candidate_asset_id
                    or not self._reviewed_binding_admission_eligible_in_session(
                        session, project_id, binding, approval=approval
                    )
                ):
                    raise InvalidTransitionError(
                        "refinement must name the current creator-reviewed keyframe for this shot"
                    )
                intent = session.get(VisualIntentRow, binding.visual_intent_id)
                if intent is None:
                    raise InvalidTransitionError("refinement reviewed VisualIntent is unavailable")
                parent_job_id = parent_job.id
                reviewed_visual_intent = {
                    "bindingId": binding.id,
                    "assetId": binding.asset_id,
                    "selectionRevision": binding.selection_revision,
                    "visualIntentId": intent.id,
                    "visualIntentRevision": intent.revision,
                    "intent": intent.intent,
                }
                references.append({
                    "assetId": asset.id, "role": "parent_output", "required": True,
                    "originalHash": asset.original_hash, "mimeType": asset.mime_type,
                    "byteSize": asset.byte_size, "width": asset.width, "height": asset.height,
                })

            adaptation_snapshot: dict[str, Any] | None = None
            if keyframe_adaptation is not None:
                binding = session.scalar(
                    select(ReviewedShotBindingRow)
                    .where(
                        ReviewedShotBindingRow.project_id == project_id,
                        ReviewedShotBindingRow.shot_id == shot_id,
                    )
                    .order_by(ReviewedShotBindingRow.selection_revision.desc())
                    .limit(1)
                )
                if binding is None or not self._reviewed_binding_admission_eligible_in_session(
                    session, project_id, binding, approval=approval
                ):
                    raise InvalidTransitionError(
                        "keyframe adaptation needs the current reviewed selected keyframe"
                    )
                asset = session.get(ManagedAssetRow, binding.asset_id)
                intent = session.get(VisualIntentRow, binding.visual_intent_id)
                if (
                    asset is None
                    or asset.project_id != project_id
                    or intent is None
                    or intent.project_id != project_id
                    or intent.asset_id != asset.id
                    or intent.revision != binding.visual_intent_revision
                ):
                    raise InvalidTransitionError(
                        "keyframe adaptation source is unavailable or no longer reviewable"
                    )
                target_width = int(keyframe_adaptation["targetProfile"]["width"])
                target_height = int(keyframe_adaptation["targetProfile"]["height"])
                if has_matching_aspect(asset.width, asset.height, target_width, target_height):
                    raise InvalidTransitionError(
                        "reviewed keyframe already matches the requested adaptation profile"
                    )
                references.append({
                    "assetId": asset.id,
                    "role": "source_keyframe",
                    "required": True,
                    "originalHash": asset.original_hash,
                    "mimeType": asset.mime_type,
                    "byteSize": asset.byte_size,
                    "width": asset.width,
                    "height": asset.height,
                })
                adaptation_snapshot = {
                    "sourceBindingId": binding.id,
                    "sourceSelectionRevision": binding.selection_revision,
                    "sourceAssetId": asset.id,
                    "sourceOriginalHash": asset.original_hash,
                    "sourceVisualIntentId": intent.id,
                    "sourceVisualIntentRevision": intent.revision,
                    "targetProfile": dict(keyframe_adaptation["targetProfile"]),
                    "outputContract": {
                        "width": target_width,
                        "height": target_height,
                        "mimeTypes": ["image/jpeg", "image/png"],
                    },
                }

            if len(references) > 9:
                raise ImageJobError(
                    "identity_reference_excessive",
                    "identity-aware job has more than nine frozen reference attachments; reduce the authored visible cast or reference views",
                )

            shot_payload = shot.model_dump(mode="json", by_alias=True)
            visual_proposal = {
                "title": shot.title, "action": shot.action, "composition": shot.composition,
                "visualIntent": shot.visual_intent, "cameraAngle": shot.camera_angle,
                "cameraMovement": shot.camera_movement,
            }
            resolved_context = self._image_job_resolved_context(
                shot=shot,
                storyboard=storyboard,
                story_bible=story_bible,
                scene_beats=scene_beats,
            )
            snapshot = {
                "snapshotVersion": contract_version, "compilerVersion": f"plotloom.codex-image-job.v{contract_version}",
                "projectId": project_id, "approvalId": approval.id,
                "approvalGateSetVersion": approval.gate_set_version,
                "storyboardEntityRevisionId": approval.entity_revision_id,
                "storyboardRevision": storyboard_revision,
                "canonicalInputRevisions": dict(approval.canonical_input_revisions),
                "shot": shot_payload, "visualProposal": visual_proposal,
                "creatorDirection": {"presentationChange": presentation_change},
                "resolvedContext": resolved_context,
                "references": references,
                "audioContext": shot_payload.get("audioPlan", {}),
            }
            if contract_version == 3:
                snapshot["visibleCharacterIds"] = list(shot.character_ids)
                snapshot["characterIdentity"] = identity_mappings
            if reviewed_visual_intent is not None:
                snapshot["reviewedVisualIntent"] = reviewed_visual_intent
            if adaptation_snapshot is not None:
                snapshot["keyframeAdaptation"] = adaptation_snapshot
            snapshot_hash = stable_hash(snapshot)
            now = utc_now()
            unit = ProductionUnitRow(
                id=new_id(), project_id=project_id, approval_id=approval.id,
                storyboard_entity_revision_id=approval.entity_revision_id, shot_id=shot.id,
                scene_id=shot.scene_id, storyboard_revision=storyboard_revision,
                snapshot=snapshot, snapshot_hash=snapshot_hash, created_at=now,
            )
            session.add(unit)
            session.flush()
            job_id = self._image_job_id()
            request = {
                "schemaVersion": contract_version, "jobId": job_id, "productionUnitId": unit.id,
                "productionSnapshotHash": snapshot_hash,
                "executionContract": "codex_specialist.v2" if contract_version == 3 else "codex_specialist.v1",
                "kind": (
                    "keyframe_adaptation"
                    if adaptation_snapshot is not None
                    else "refinement" if parent_candidate_asset_id else "original"
                ),
                "visualProposal": visual_proposal, "frozenSnapshot": snapshot,
            }
            if contract_version == 3:
                request["specialistPreflight"] = {"version": "p1.5-pin.v1", "skillVersion": "plotloom-image-specialist.v3", "executionContract": "codex_specialist.v2"}
            job = ImageJobRow(
                id=job_id, project_id=project_id, production_unit_id=unit.id,
                parent_job_id=parent_job_id, parent_candidate_asset_id=parent_candidate_asset_id,
                request=request, request_hash=stable_hash(request), state="prepared", exported_at=None,
                cancelled_at=None, cancellation_reason=None, created_at=now,
            )
            session.add(job)
            session.flush()
            return {"job": self._image_job_dict(job, current=True), "productionUnit": self._production_unit_dict(unit)}

    def image_job_package_sources(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._read() as session:
            self._assert_active_project(self._project_row(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            if job.state == "cancelled" or not self._image_job_is_current_in_session(session, job):
                raise InvalidTransitionError("image job is no longer current and cannot be copied")
            sources: list[dict[str, Any]] = []
            for reference in job.request["frozenSnapshot"].get("references", []):
                if reference.get("role") not in {
                    "parent_output", "source_keyframe", "character_identity"
                }:
                    continue
                asset = session.get(ManagedAssetRow, reference.get("assetId"))
                if (
                    asset is None or asset.project_id != project_id
                    or asset.original_hash != reference.get("originalHash")
                ):
                    raise InvalidTransitionError("frozen image-job reference bytes are unavailable")
                sources.append({
                    "role": reference["role"], "contentHash": asset.original_hash,
                    "mimeType": asset.mime_type, "originalUri": asset.original_uri,
                    "characterId": reference.get("characterId"),
                })
            return {"job": self._image_job_dict(job, current=True), "references": sources}

    def mark_image_job_exported(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._lifecycle_write() as session:
            self._assert_active_project(self._project_row(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            if job.state == "cancelled" or not self._image_job_is_current_in_session(session, job):
                raise InvalidTransitionError("image job is no longer current and cannot be copied")
            if job.exported_at is None:
                job.exported_at = utc_now()
                job.state = "exported"
                session.flush()
            return self._image_job_dict(job, current=True)

    def cancel_image_job(self, project_id: str, job_id: str, reason: str) -> dict[str, Any]:
        reason = reason.strip()
        if not reason or len(reason) > 2_000:
            raise ValueError("image job cancellation reason must be between 1 and 2,000 characters")
        with self._lifecycle_write() as session:
            self._assert_active_project(self._project_row(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            if job.state != "cancelled":
                job.state = "cancelled"
                job.cancelled_at = utc_now()
                job.cancellation_reason = reason
                session.flush()
            return self._image_job_dict(job, current=False)

    def image_job_delivery_context(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._read() as session:
            self._assert_active_project(self._project_row(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            return self._image_job_dict(job, current=self._image_job_is_current_in_session(session, job))

    def record_image_job_delivery_rejection(self, project_id: str, job_id: str, code: str) -> None:
        with self._lifecycle_write() as session:
            self._assert_active_project(self._project_row(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            session.add(ImageJobDeliveryRow(
                id=new_id(), job_id=job_id, delivery_id=None, manifest=None, manifest_hash=None,
                state="rejected", diagnostic_code=code, created_at=utc_now(),
            ))

    @staticmethod
    def _image_candidate_dict(session: Session, row: ImageJobCandidateRow) -> dict[str, Any]:
        asset = session.get(ManagedAssetRow, row.asset_id)
        return {
            "id": row.id, "assetId": row.asset_id, "jobId": row.job_id,
            "outputFilename": row.output_filename, "outputHash": row.output_hash, "role": row.role,
            "asset": SQLiteRepository._managed_asset_dict(asset) if asset else None,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def record_image_job_delivery(
        self, project_id: str, job_id: str, *, delivery_id: str, manifest: dict[str, Any],
        manifest_hash: str, outputs: Sequence[dict[str, Any]],
        publish: Callable[[dict[str, Any]], tuple[str, str]],
    ) -> dict[str, Any]:
        """Atomically admit one verified delivery, publishing only after admission.

        The artifact callback runs under the lifecycle writer only after the
        durable final-delivery, project-lifecycle, and currentness checks pass.
        It keeps a duplicate, cancelled, revoked, or archived Refresh from
        creating unowned content-addressed blobs before repository admission.
        """

        with self._lifecycle_write() as session:
            self._assert_active_project(self._project_row(session, project_id))
            job = session.get(ImageJobRow, job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(f"image job not found: {job_id}")
            existing = session.scalar(
                select(ImageJobDeliveryRow)
                .where(ImageJobDeliveryRow.job_id == job_id, ImageJobDeliveryRow.delivery_id == delivery_id)
                .limit(1)
            )
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise ImageJobError("delivery_conflict", "delivery identity was already recorded with different content")
                candidates = session.scalars(
                    select(ImageJobCandidateRow).where(ImageJobCandidateRow.delivery_id == existing.id)
                    .order_by(ImageJobCandidateRow.created_at, ImageJobCandidateRow.id)
                ).all()
                return {"deliveryId": delivery_id, "state": existing.state, "diagnosticCode": existing.diagnostic_code,
                        "idempotent": True, "candidates": [self._image_candidate_dict(session, item) for item in candidates]}
            finalized = session.scalar(
                select(ImageJobDeliveryRow)
                .where(ImageJobDeliveryRow.job_id == job_id, ImageJobDeliveryRow.delivery_id.is_not(None))
                .limit(1)
            )
            if finalized is not None:
                raise ImageJobError("delivery_finalized", "image job already has a final delivery")
            current = job.state in {"exported", "delivered"} and self._image_job_is_current_in_session(session, job)
            delivery = ImageJobDeliveryRow(
                id=new_id(), job_id=job_id, delivery_id=delivery_id, manifest=manifest,
                manifest_hash=manifest_hash, state="accepted" if current else "inapplicable",
                diagnostic_code=None if current else "late_or_stale_delivery", created_at=utc_now(),
            )
            session.add(delivery)
            session.flush()
            if not current:
                return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": delivery.diagnostic_code,
                        "idempotent": False, "candidates": []}
            candidates: list[ImageJobCandidateRow] = []
            for output in outputs:
                original_uri, display_uri = publish(output)
                asset = ManagedAssetRow(
                    id=new_id(), project_id=project_id, original_uri=original_uri,
                    original_hash=output["originalHash"], display_uri=display_uri,
                    display_hash=output["displayHash"], mime_type=output["mimeType"], byte_size=output["byteSize"],
                    width=output["width"], height=output["height"], created_at=utc_now(),
                )
                session.add(asset)
                session.flush()
                session.add(ManagedAssetProvenanceRow(
                    id=new_id(), project_id=project_id, asset_id=asset.id,
                    declaration={
                        "origin": "codex_image_job", "rights": "unknown", "jobId": job.id,
                        "rightsNote": None, "declaredAdditions": [],
                        "deliveryId": delivery_id, "outputFilename": output["filename"],
                        "actualPrompt": manifest["actualPrompt"], "toolEvidence": manifest["toolEvidence"],
                        "limitations": manifest.get("limitations", []),
                    }, created_at=utc_now(),
                ))
                candidate = ImageJobCandidateRow(
                    id=new_id(), job_id=job.id, delivery_id=delivery.id, asset_id=asset.id,
                    output_filename=output["filename"], output_hash=output["originalHash"],
                    role=output["role"], created_at=utc_now(),
                )
                session.add(candidate)
                candidates.append(candidate)
            job.state = "delivered"
            session.flush()
            return {"deliveryId": delivery_id, "state": delivery.state, "diagnosticCode": None,
                    "idempotent": False, "candidates": [self._image_candidate_dict(session, item) for item in candidates]}

    def list_image_jobs(self, project_id: str) -> list[dict[str, Any]]:
        with self._read() as session:
            self._project_row(session, project_id)
            jobs = session.scalars(
                select(ImageJobRow).where(ImageJobRow.project_id == project_id)
                .order_by(ImageJobRow.created_at.desc(), ImageJobRow.id.desc())
            ).all()
            result: list[dict[str, Any]] = []
            for job in jobs:
                deliveries = session.scalars(
                    select(ImageJobDeliveryRow).where(ImageJobDeliveryRow.job_id == job.id)
                    .order_by(ImageJobDeliveryRow.created_at.desc(), ImageJobDeliveryRow.id.desc())
                ).all()
                result.append({
                    **self._image_job_dict(job, current=self._image_job_is_current_in_session(session, job)),
                    "deliveries": [
                        {
                            "id": delivery.id, "deliveryId": delivery.delivery_id, "state": delivery.state,
                            "diagnosticCode": delivery.diagnostic_code, "manifestHash": delivery.manifest_hash,
                            "createdAt": _stored_utc(delivery.created_at).isoformat(),
                            "candidates": [self._image_candidate_dict(session, candidate) for candidate in session.scalars(
                                select(ImageJobCandidateRow).where(ImageJobCandidateRow.delivery_id == delivery.id)
                                .order_by(ImageJobCandidateRow.created_at, ImageJobCandidateRow.id)
                            ).all()],
                        }
                        for delivery in deliveries
                    ],
                })
            return result

    def update_project(self, project_id: str, expected_revision: int, brief: ProjectBrief) -> Project:
        with self._lifecycle_write() as session:
            row = self._project_row(session, project_id)
            self._assert_active_project(row)
            if row.revision != expected_revision:
                raise RevisionConflictError("project", expected_revision, row.revision)
            brief_data = brief.model_dump(mode="json", by_alias=False)
            if row.brief == brief_data:
                return self._project(row)
            row.brief = brief_data
            row.revision += 1
            row.updated_at = utc_now()
            for stage in STAGE_ORDER:
                head = self._stage_row(session, project_id, stage)
                if head.status != StageStatus.MISSING.value:
                    head.status = StageStatus.STALE.value
                    head.stale_reasons = ["project brief revision changed"]
                    head.updated_at = row.updated_at
            return self._project(row)

    def _consume_exact_authoring_draft_in_session(
        self,
        session: Session,
        project: ProjectRow,
        *,
        editor_scope: AuthoringDraftScope,
        entity_id: str,
        expected_draft_revision: int,
        canonical_base_revision: int,
        canonical_payload: dict[str, Any],
    ) -> None:
        """Bind canonical Save to the precise acknowledged authoring buffer.

        A draft revision is a receipt for both its canonical input revision and
        its validated editor payload. Checking all three in the same write
        transaction prevents a request from consuming an unrelated buffer.
        """

        row = session.scalar(
            select(AuthoringDraftRow).where(
                AuthoringDraftRow.project_id == project.id,
                AuthoringDraftRow.editor_scope == editor_scope,
                AuthoringDraftRow.entity_id == entity_id,
            )
        )
        actual_revision = row.draft_revision if row is not None else 0
        if row is None or row.draft_revision != expected_draft_revision:
            raise RevisionConflictError(
                f"authoring draft {editor_scope}/{entity_id}",
                expected_draft_revision,
                actual_revision,
            )
        if row.base_canonical_revision != canonical_base_revision:
            raise RevisionConflictError(
                f"authoring draft canonical base {editor_scope}",
                canonical_base_revision,
                row.base_canonical_revision,
            )
        if row.payload != canonical_payload:
            raise RevisionConflictError(
                f"authoring draft payload {editor_scope}/{entity_id}",
                expected_draft_revision,
                row.draft_revision,
            )
        session.delete(row)

    def update_project_consuming_authoring_draft(
        self,
        project_id: str,
        expected_revision: int,
        brief: ProjectBrief,
        *,
        entity_id: str,
        expected_draft_revision: int,
    ) -> Project:
        """Atomically save a brief and consume the exact acknowledged draft."""

        canonical_payload = brief.model_dump(mode="json", by_alias=True)
        with self._lifecycle_write() as session:
            row = self._project_row(session, project_id)
            self._assert_active_project(row)
            if row.revision != expected_revision:
                raise RevisionConflictError("project", expected_revision, row.revision)
            self._consume_exact_authoring_draft_in_session(
                session,
                row,
                editor_scope="brief",
                entity_id=entity_id,
                expected_draft_revision=expected_draft_revision,
                canonical_base_revision=row.revision,
                canonical_payload=canonical_payload,
            )
            brief_data = brief.model_dump(mode="json", by_alias=False)
            if row.brief != brief_data:
                row.brief = brief_data
                row.revision += 1
                row.updated_at = utc_now()
                for stage in STAGE_ORDER:
                    head = self._stage_row(session, project_id, stage)
                    if head.status != StageStatus.MISSING.value:
                        head.status = StageStatus.STALE.value
                        head.stale_reasons = ["project brief revision changed"]
                        head.updated_at = row.updated_at
            return self._project(row)

    @staticmethod
    def _authoring_draft(row: AuthoringDraftRow) -> AuthoringDraft:
        return AuthoringDraft(
            project_id=row.project_id,
            editor_scope=row.editor_scope,
            entity_id=row.entity_id,
            base_canonical_revision=row.base_canonical_revision,
            draft_revision=row.draft_revision,
            payload=row.payload,
            updated_at=_stored_utc(row.updated_at),
        )

    @staticmethod
    def _validate_authoring_draft_payload(
        editor_scope: AuthoringDraftScope,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Keep draft storage at the authoring contract, never UI/session shape."""

        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise ValueError("authoring drafts must not contain credentials or secret-shaped values")
        if editor_scope == "brief":
            return ProjectBrief.model_validate(payload).model_dump(mode="json", by_alias=True)
        if editor_scope == "visual_intent":
            return VisualIntentDraftPayload.model_validate(payload).model_dump(mode="json", by_alias=True)
        if editor_scope == "image_direction":
            return ImageDirectionDraftPayload.model_validate(payload).model_dump(mode="json", by_alias=True)
        stage = StageName(editor_scope)
        return stage_payload_model(stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION).model_validate(
            payload
        ).model_dump(mode="json", by_alias=True)

    @staticmethod
    def _authoring_draft_base_revision(
        session: Session,
        project: ProjectRow,
        editor_scope: AuthoringDraftScope,
    ) -> int:
        if editor_scope == "brief":
            return project.revision
        if editor_scope in {"visual_intent", "image_direction"}:
            return SQLiteRepository._stage_row(session, project.id, StageName.STORYBOARD).revision
        return SQLiteRepository._stage_row(session, project.id, StageName(editor_scope)).revision

    def list_authoring_drafts(self, project_id: str) -> list[AuthoringDraft]:
        with self._read() as session:
            self._project_row(session, project_id)
            rows = session.scalars(
                select(AuthoringDraftRow)
                .where(AuthoringDraftRow.project_id == project_id)
                .order_by(AuthoringDraftRow.editor_scope, AuthoringDraftRow.entity_id)
            ).all()
            return [self._authoring_draft(row) for row in rows]

    def upsert_authoring_draft(
        self,
        project_id: str,
        *,
        editor_scope: AuthoringDraftScope,
        entity_id: str,
        base_canonical_revision: int,
        expected_draft_revision: int,
        payload: dict[str, Any],
    ) -> AuthoringDraft:
        """CAS one bounded editor buffer against its exact canonical owner."""

        validated_payload = self._validate_authoring_draft_payload(editor_scope, payload)
        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            if editor_scope in {"visual_intent", "image_direction"}:
                # Media drafts are deliberately bound to the current authored
                # storyboard, not just to a browser-supplied opaque key.  This
                # keeps a copied or stale tab from retaining direction for a
                # foreign asset/shot while still leaving the draft noncanonical.
                storyboard = self._load_stage_payload(session, project_id, StageName.STORYBOARD)
                draft_shot_id = str(validated_payload["shotId"])
                if not any(shot.id == draft_shot_id for shot in storyboard.shots):
                    raise ValueError("media authoring draft targets no current storyboard shot")
                if editor_scope == "visual_intent":
                    draft_asset_id = str(validated_payload["assetId"])
                    asset = session.get(ManagedAssetRow, draft_asset_id)
                    if asset is None or asset.project_id != project_id:
                        raise ValueError("visual-intent draft targets no project-owned asset")
                    expected_entity_id = f"{draft_shot_id}:{draft_asset_id}"
                else:
                    expected_entity_id = f"{draft_shot_id}:{validated_payload['targetId']}"
                if entity_id != expected_entity_id:
                    raise ValueError("media authoring draft identity does not match its bounded payload")
            current_base = self._authoring_draft_base_revision(session, project, editor_scope)
            if base_canonical_revision != current_base:
                raise RevisionConflictError(
                    f"authoring draft canonical base {editor_scope}",
                    base_canonical_revision,
                    current_base,
                )
            row = session.scalar(
                select(AuthoringDraftRow).where(
                    AuthoringDraftRow.project_id == project_id,
                    AuthoringDraftRow.editor_scope == editor_scope,
                    AuthoringDraftRow.entity_id == entity_id,
                )
            )
            current_draft_revision = row.draft_revision if row is not None else 0
            if expected_draft_revision != current_draft_revision:
                raise RevisionConflictError(
                    f"authoring draft {editor_scope}/{entity_id}",
                    expected_draft_revision,
                    current_draft_revision,
                )
            now = utc_now()
            if row is None:
                row = AuthoringDraftRow(
                    id=new_id(),
                    project_id=project_id,
                    editor_scope=editor_scope,
                    entity_id=entity_id,
                    base_canonical_revision=base_canonical_revision,
                    draft_revision=1,
                    payload=validated_payload,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.base_canonical_revision = base_canonical_revision
                row.draft_revision += 1
                row.payload = validated_payload
                row.updated_at = now
            session.flush()
            return self._authoring_draft(row)

    def discard_authoring_draft(
        self,
        project_id: str,
        *,
        editor_scope: AuthoringDraftScope,
        entity_id: str,
        expected_draft_revision: int,
    ) -> bool:
        """Consume only one exact acknowledged draft; preserve newer typing."""

        with self._lifecycle_write() as session:
            self._project_row(session, project_id)
            row = session.scalar(
                select(AuthoringDraftRow).where(
                    AuthoringDraftRow.project_id == project_id,
                    AuthoringDraftRow.editor_scope == editor_scope,
                    AuthoringDraftRow.entity_id == entity_id,
                )
            )
            if row is None or row.draft_revision != expected_draft_revision:
                return False
            session.delete(row)
            return True

    def list_stage_heads(self, project_id: str) -> list[StageHead]:
        with self._read() as session:
            self._project_row(session, project_id)
            rows = session.scalars(select(StageHeadRow).where(StageHeadRow.project_id == project_id)).all()
            by_stage = {StageName(row.stage): row for row in rows}
            return [self._stage_head(by_stage[stage]) for stage in STAGE_ORDER]

    def list_stage_envelopes(self, project_id: str) -> list[StageEnvelope]:
        with self._read() as session:
            self._project_row(session, project_id)
            return self._stage_envelopes_in_session(session, project_id)

    def get_stage_head(self, project_id: str, stage: StageName) -> StageHead:
        with self._read() as session:
            self._project_row(session, project_id)
            return self._stage_head(self._stage_row(session, project_id, stage))

    def get_entity_revision(self, revision_id: str) -> EntityRevision:
        with self._read() as session:
            row = session.get(EntityRevisionRow, revision_id)
            if row is None:
                raise NotFoundError(f"entity revision not found: {revision_id}")
            return self._entity_revision(row)

    def record_gate_evaluation(
        self,
        project_id: str,
        entity_revision_id: str,
        evaluation: GateEvaluation,
    ) -> GateEvaluation:
        """Persist one immutable, versioned gate evaluation for a storyboard revision."""

        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            revision = session.get(EntityRevisionRow, entity_revision_id)
            if revision is None or revision.project_id != project_id:
                raise NotFoundError(f"entity revision not found: {entity_revision_id}")
            head = self._stage_row(session, project_id, StageName.STORYBOARD)
            if (
                head.status != StageStatus.READY.value
                or head.entity_revision_id != revision.id
                or head.revision != revision.revision
                or head.content_hash != revision.content_hash
            ):
                raise InvalidTransitionError(
                    "gate evaluation can only bind the current READY storyboard"
                )
            authoritative = self._evaluate_storyboard_revision_in_session(
                session,
                project,
                revision,
            )
            authoritative_semantics = authoritative.model_dump(
                mode="json", by_alias=False
            )
            supplied_semantics = evaluation.model_dump(mode="json", by_alias=False)
            for result in authoritative_semantics["results"]:
                result.pop("id", None)
            for result in supplied_semantics["results"]:
                result.pop("id", None)
            if supplied_semantics != authoritative_semantics:
                raise InvalidTransitionError(
                    "gate evaluation does not match the canonical evaluator receipt"
                )
            return self._record_gate_evaluation_in_session(
                session,
                project_id,
                revision,
                authoritative,
                now=utc_now(),
            )

    def _evaluate_storyboard_revision_in_session(
        self,
        session: Session,
        project: ProjectRow,
        storyboard_revision: EntityRevisionRow,
    ) -> GateEvaluation:
        """Rebuild the only accepted gate receipt from exact canonical inputs."""

        if storyboard_revision.stage != StageName.STORYBOARD.value:
            raise InvalidTransitionError(
                "gate evaluations can only bind storyboard revisions"
            )
        if storyboard_revision.schema_version != CURRENT_STAGE_SCHEMA_VERSION:
            raise SchemaResetRequiredError(
                stage=StageName.STORYBOARD,
                schema_version=storyboard_revision.schema_version,
            )

        def exact_upstream(stage: StageName) -> StagePayload:
            revision_number = storyboard_revision.input_revisions.get(stage.value)
            if revision_number is None:
                raise InvalidTransitionError(
                    f"storyboard revision has no frozen {stage.value} input"
                )
            row = session.scalar(
                select(EntityRevisionRow).where(
                    EntityRevisionRow.project_id == project.id,
                    EntityRevisionRow.stage == stage.value,
                    EntityRevisionRow.revision == revision_number,
                )
            )
            if row is None:
                raise NotFoundError(
                    f"storyboard input revision not found: {stage.value}/{revision_number}"
                )
            return self._decode_current_stage_payload(
                stage, row.payload, row.schema_version
            )

        storyboard = self._decode_current_stage_payload(
            StageName.STORYBOARD,
            storyboard_revision.payload,
            storyboard_revision.schema_version,
        )
        bible = exact_upstream(StageName.STORY_BIBLE)
        scene_beats = exact_upstream(StageName.SCENE_BEATS)
        evaluation = validate_stage_payload(
            StageName.STORYBOARD,
            storyboard,
            schema_version=CURRENT_STAGE_SCHEMA_VERSION,
            brief=ProjectBrief.model_validate(project.brief),
            bible=bible,
            graph=None,
            scene_beats=scene_beats,
        )
        if evaluation is None:
            raise InvalidTransitionError(
                "canonical storyboard evaluator returned no gate receipt"
            )
        return evaluation

    def _record_gate_evaluation_in_session(
        self,
        session: Session,
        project_id: str,
        revision: EntityRevisionRow,
        evaluation: GateEvaluation,
        *,
        now: datetime,
    ) -> GateEvaluation:
        """Bind one deterministic receipt to an exact revision transactionally."""

        if revision.project_id != project_id:
            raise NotFoundError(f"entity revision not found: {revision.id}")
        if revision.stage != StageName.STORYBOARD.value:
            raise InvalidTransitionError("gate evaluations can only bind storyboard revisions")
        if revision.schema_version != CURRENT_STAGE_SCHEMA_VERSION:
            raise SchemaResetRequiredError(
                stage=StageName.STORYBOARD, schema_version=revision.schema_version
            )
        if not evaluation.results:
            raise InvalidTransitionError("gate evaluation must contain at least one result")
        if any(
            result.gate_set_version != evaluation.gate_set_version
            or result.evaluated_input_hash != evaluation.evaluated_input_hash
            for result in evaluation.results
        ):
            raise InvalidTransitionError(
                "gate results must bind the evaluation's exact gate set and input hash"
            )

        existing = session.scalars(
            select(GateResultRow)
            .where(
                GateResultRow.entity_revision_id == revision.id,
                GateResultRow.gate_set_version == evaluation.gate_set_version,
            )
            .order_by(GateResultRow.sequence)
        ).all()
        if existing:
            persisted = GateEvaluation(
                gate_set_version=evaluation.gate_set_version,
                evaluated_input_hash=existing[0].evaluation_input_hash,
                results=tuple(self._gate_result(row) for row in existing),
            )
            persisted_semantics = [
                result.model_dump(mode="json", by_alias=False, exclude={"id"})
                for result in persisted.results
            ]
            requested_semantics = [
                result.model_dump(mode="json", by_alias=False, exclude={"id"})
                for result in evaluation.results
            ]
            if persisted_semantics != requested_semantics:
                raise InvalidTransitionError(
                    "gate evaluation is already recorded for this immutable revision"
                )
            return persisted

        persisted_results: list[GateResult] = []
        for sequence, result in enumerate(evaluation.results):
            identity = hashlib.sha256(
                f"{evaluation.gate_set_version}\0{result.gate_id}".encode("utf-8")
            ).hexdigest()
            persisted_result = result.model_copy(update={"id": f"{revision.id}:{identity}"})
            persisted_results.append(persisted_result)
            session.add(
                GateResultRow(
                    id=persisted_result.id,
                    project_id=project_id,
                    entity_revision_id=revision.id,
                    stage=revision.stage,
                    revision=revision.revision,
                    content_hash=revision.content_hash,
                    evaluation_input_hash=evaluation.evaluated_input_hash,
                    gate_set_version=evaluation.gate_set_version,
                    sequence=sequence,
                    gate_id=result.gate_id,
                    gate_version=result.gate_set_version,
                    required=result.required,
                    severity=result.severity.value,
                    status=result.status.value,
                    entity_path=list(result.entity_path),
                    evidence=[
                        item.model_dump(mode="json", by_alias=False)
                        for item in result.evidence
                    ],
                    reason=result.reason,
                    created_at=now,
                )
            )
        return GateEvaluation(
            gate_set_version=evaluation.gate_set_version,
            evaluated_input_hash=evaluation.evaluated_input_hash,
            results=tuple(persisted_results),
        )

    def get_gate_evaluation(
        self,
        entity_revision_id: str,
        gate_set_version: str,
    ) -> GateEvaluation:
        with self._read() as session:
            revision = session.get(EntityRevisionRow, entity_revision_id)
            if revision is None:
                raise NotFoundError(f"entity revision not found: {entity_revision_id}")
            rows = session.scalars(
                select(GateResultRow)
                .where(
                    GateResultRow.entity_revision_id == entity_revision_id,
                    GateResultRow.gate_set_version == gate_set_version,
                )
                .order_by(GateResultRow.sequence)
            ).all()
            if not rows:
                raise NotFoundError(
                    f"gate evaluation not found: {entity_revision_id}/{gate_set_version}"
                )
            return GateEvaluation(
                gate_set_version=gate_set_version,
                evaluated_input_hash=rows[0].evaluation_input_hash,
                results=tuple(self._gate_result(row) for row in rows),
            )

    def append_approval_decision(
        self,
        project_id: str,
        entity_revision_id: str,
        *,
        decision: str,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
        subject_type: str = "storyboard",
        subject_id: str = "storyboard",
    ) -> ApprovalDecision:
        """Append (never update) an approval or revocation over an exact board."""

        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            revision = session.get(EntityRevisionRow, entity_revision_id)
            if revision is None or revision.project_id != project_id:
                raise NotFoundError(f"entity revision not found: {entity_revision_id}")
            return self._append_approval_decision_in_session(
                session,
                project_id,
                revision,
                decision=decision,
                reviewer=reviewer,
                gate_set_version=gate_set_version,
                note=note,
                subject_type=subject_type,
                subject_id=subject_id,
            )

    def decide_storyboard_approval(
        self,
        project_id: str,
        *,
        expected_revision: int,
        expected_content_hash: str,
        decision: str,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
    ) -> ApprovalDecision:
        """Append a decision only if the exact current storyboard still matches."""

        with self._lifecycle_write() as session:
            project = self._project_row(session, project_id)
            self._assert_active_project(project)
            head = self._stage_row(session, project_id, StageName.STORYBOARD)
            if head.revision != expected_revision:
                raise RevisionConflictError(
                    "stage:storyboard", expected_revision, head.revision
                )
            if (
                head.status != StageStatus.READY.value
                or head.entity_revision_id is None
                or head.content_hash is None
            ):
                raise InvalidTransitionError(
                    "only the current READY storyboard can receive a review decision"
                )
            if head.content_hash != expected_content_hash:
                raise InvalidTransitionError(
                    "storyboard content hash no longer matches the reviewed content"
                )
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            if revision is None:
                raise NotFoundError(
                    f"entity revision not found: {head.entity_revision_id}"
                )
            return self._append_approval_decision_in_session(
                session,
                project_id,
                revision,
                decision=decision,
                reviewer=reviewer,
                gate_set_version=gate_set_version,
                note=note,
                subject_type="storyboard",
                subject_id="storyboard",
            )

    def _append_approval_decision_in_session(
        self,
        session: Session,
        project_id: str,
        revision: EntityRevisionRow,
        *,
        decision: str,
        reviewer: str,
        gate_set_version: str,
        note: str | None,
        subject_type: str,
        subject_id: str,
    ) -> ApprovalDecision:
        normalized_decision = decision.strip().lower()
        normalized_reviewer = reviewer.strip()
        normalized_gate_set_version = gate_set_version.strip()
        if normalized_decision not in {"approve", "revoke"}:
            raise ValueError("approval decision must be approve or revoke")
        if not normalized_reviewer or not normalized_gate_set_version:
            raise ValueError("reviewer and gate_set_version must not be blank")
        if normalized_gate_set_version != STORYBOARD_GATE_SET_VERSION:
            raise InvalidTransitionError(
                "approval requires the current canonical storyboard gate set"
            )
        if subject_type != "storyboard" or subject_id != "storyboard":
            raise InvalidTransitionError(
                "only the canonical storyboard subject is approval-eligible"
            )
        if revision.project_id != project_id:
            raise NotFoundError(f"entity revision not found: {revision.id}")
        if revision.stage != StageName.STORYBOARD.value:
            raise InvalidTransitionError(
                "approval decisions can only bind storyboard revisions"
            )
        if revision.schema_version != CURRENT_STAGE_SCHEMA_VERSION:
            raise SchemaResetRequiredError(
                stage=StageName.STORYBOARD, schema_version=revision.schema_version
            )
        head = self._stage_row(session, project_id, StageName.STORYBOARD)
        if (
            head.status != StageStatus.READY.value
            or head.entity_revision_id != revision.id
            or head.revision != revision.revision
            or head.content_hash != revision.content_hash
        ):
            raise InvalidTransitionError(
                "approval decisions can only bind the current READY storyboard"
            )

        latest = session.scalar(
            select(ApprovalDecisionRow)
            .where(
                ApprovalDecisionRow.entity_revision_id == revision.id,
                ApprovalDecisionRow.subject_type == subject_type,
                ApprovalDecisionRow.subject_id == subject_id,
            )
            .order_by(
                ApprovalDecisionRow.created_at.desc(),
                ApprovalDecisionRow.id.desc(),
            )
            .limit(1)
        )
        if latest is not None and latest.decision == normalized_decision:
            raise InvalidTransitionError(
                f"storyboard revision is already {normalized_decision}d"
            )
        if normalized_decision == "revoke" and (
            latest is None or latest.decision != "approve"
        ):
            raise InvalidTransitionError(
                "only an active approval for this storyboard revision can be revoked"
            )

        gates = session.scalars(
            select(GateResultRow).where(
                GateResultRow.entity_revision_id == revision.id,
                GateResultRow.gate_set_version == normalized_gate_set_version,
            )
        ).all()
        if normalized_decision == "approve":
            if not gates:
                raise InvalidTransitionError(
                    "approval requires a recorded gate evaluation"
                )
            if any(
                gate.content_hash != revision.content_hash
                or gate.revision != revision.revision
                or not self._gate_result(gate).passed
                for gate in gates
            ):
                raise InvalidTransitionError(
                    "approval requires all required gates to pass for the exact revision"
                )

        row = ApprovalDecisionRow(
            id=new_id(),
            project_id=project_id,
            entity_revision_id=revision.id,
            subject_type=subject_type,
            subject_id=subject_id,
            subject_revision=revision.revision,
            content_hash=revision.content_hash,
            canonical_input_revisions=dict(revision.input_revisions),
            gate_set_version=normalized_gate_set_version,
            decision=normalized_decision,
            reviewer=normalized_reviewer,
            note=note,
            created_at=utc_now(),
        )
        session.add(row)
        return self._approval_decision(row)

    def approve_storyboard(
        self,
        project_id: str,
        entity_revision_id: str,
        *,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
    ) -> ApprovalDecision:
        return self.append_approval_decision(
            project_id,
            entity_revision_id,
            decision="approve",
            reviewer=reviewer,
            gate_set_version=gate_set_version,
            note=note,
        )

    def revoke_storyboard_approval(
        self,
        project_id: str,
        entity_revision_id: str,
        *,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
    ) -> ApprovalDecision:
        return self.append_approval_decision(
            project_id,
            entity_revision_id,
            decision="revoke",
            reviewer=reviewer,
            gate_set_version=gate_set_version,
            note=note,
        )

    def list_approval_decisions(self, project_id: str) -> list[ApprovalDecision]:
        with self._read() as session:
            self._project_row(session, project_id)
            rows = session.scalars(
                select(ApprovalDecisionRow)
                .where(ApprovalDecisionRow.project_id == project_id)
                .order_by(ApprovalDecisionRow.created_at, ApprovalDecisionRow.id)
            ).all()
            return [self._approval_decision(row) for row in rows]

    def get_approval_closure(self, decision_id: str) -> ApprovalClosure:
        """Derive applicability from immutable decisions and the current closure."""

        with self._read() as session:
            row = session.get(ApprovalDecisionRow, decision_id)
            if row is None:
                raise NotFoundError(f"approval decision not found: {decision_id}")
            decision = self._approval_decision(row)
            reasons: list[str] = []
            if row.decision != "approve":
                reasons.append("decision is a revocation")
            latest = session.scalar(
                select(ApprovalDecisionRow)
                .where(
                    ApprovalDecisionRow.entity_revision_id == row.entity_revision_id,
                    ApprovalDecisionRow.subject_type == row.subject_type,
                    ApprovalDecisionRow.subject_id == row.subject_id,
                )
                .order_by(ApprovalDecisionRow.created_at.desc(), ApprovalDecisionRow.id.desc())
                .limit(1)
            )
            if latest is None or latest.id != row.id:
                reasons.append("superseded or revoked by a later decision")
            revision = session.get(EntityRevisionRow, row.entity_revision_id)
            if revision is None:
                reasons.append("approved revision is unavailable")
            else:
                head = self._stage_row(session, row.project_id, StageName.STORYBOARD)
                if (
                    head.status != StageStatus.READY.value
                    or head.entity_revision_id != row.entity_revision_id
                    or head.content_hash != row.content_hash
                    or revision.revision != row.subject_revision
                    or revision.content_hash != row.content_hash
                ):
                    reasons.append("storyboard head no longer matches the approved revision")
                for stage, expected_revision in row.canonical_input_revisions.items():
                    upstream = self._stage_row(session, row.project_id, StageName(stage))
                    if upstream.status != StageStatus.READY.value or upstream.revision != expected_revision:
                        reasons.append(f"upstream {stage} revision changed")
                gates = session.scalars(
                    select(GateResultRow).where(
                        GateResultRow.entity_revision_id == row.entity_revision_id,
                        GateResultRow.gate_set_version == row.gate_set_version,
                    )
                ).all()
                if (
                    not gates
                    or any(not self._gate_result(gate).passed for gate in gates)
                ):
                    reasons.append("required gate results are absent or no longer passing")
            return ApprovalClosure(decision=decision, active=not reasons, stale_reasons=tuple(reasons))

    def approval_is_revoked(self, decision_id: str) -> bool:
        """Return whether the exact approved revision was subsequently revoked.

        A preview remains an immutable historical projection after revocation,
        but consumers need to distinguish that explicit human decision from an
        ordinary stale canonical head.
        """

        with self._read() as session:
            decision = session.get(ApprovalDecisionRow, decision_id)
            if decision is None:
                raise NotFoundError(f"approval decision not found: {decision_id}")
            latest = session.scalar(
                select(ApprovalDecisionRow)
                .where(
                    ApprovalDecisionRow.entity_revision_id == decision.entity_revision_id,
                    ApprovalDecisionRow.subject_type == decision.subject_type,
                    ApprovalDecisionRow.subject_id == decision.subject_id,
                )
                .order_by(ApprovalDecisionRow.created_at.desc(), ApprovalDecisionRow.id.desc())
                .limit(1)
            )
            return latest is not None and latest.decision == "revoke"

    def _load_stage_payload(self, session: Session, project_id: str, stage: StageName) -> StagePayload:
        head = self._stage_row(session, project_id, stage)
        if head.entity_revision_id is None:
            raise StagePrerequisiteError(stage, stage, head.status)
        revision = session.get(EntityRevisionRow, head.entity_revision_id)
        if revision is None:
            raise NotFoundError(f"entity revision not found: {head.entity_revision_id}")
        if head.schema_version != revision.schema_version:
            raise SchemaResetRequiredError(stage=stage, schema_version=head.schema_version)
        return self._decode_current_stage_payload(
            stage, revision.payload, revision.schema_version
        )

    def get_stage_payload(self, project_id: str, stage: StageName) -> StagePayload:
        with self._read() as session:
            self._project_row(session, project_id)
            return self._load_stage_payload(session, project_id, stage)

    def _mark_downstream_stale(self, session: Session, project_id: str, stage: StageName, now: datetime) -> None:
        for downstream in downstream_stages(stage):
            row = self._stage_row(session, project_id, downstream)
            if row.status != StageStatus.MISSING.value:
                row.status = StageStatus.STALE.value
                row.stale_reasons = [f"upstream stage {stage.value} revision changed"]
                row.updated_at = now

    def _install_stage_in_session(
        self,
        session: Session,
        project_row: ProjectRow,
        stage: StageName,
        payload: StagePayload,
        *,
        expected_revision: int,
        now: datetime,
        allow_noop: bool,
        dialogue_timing_profile: DialogueTimingProfile | None = None,
    ) -> tuple[StageHead, EntityRevisionRow | None]:
        """Validate and install one canonical revision in the caller's transaction."""

        head = self._stage_row(session, project_row.id, stage)
        if head.revision != expected_revision:
            raise RevisionConflictError(f"stage:{stage.value}", expected_revision, head.revision)

        input_revisions: dict[StageName, int] = {}
        upstream_payloads: dict[StageName, StagePayload] = {}
        for upstream in upstream_stages(stage):
            upstream_head = self._stage_row(session, project_row.id, upstream)
            if upstream_head.status != StageStatus.READY.value:
                raise StagePrerequisiteError(stage, upstream, upstream_head.status)
            input_revisions[upstream] = upstream_head.revision
            upstream_payloads[upstream] = self._load_stage_payload(session, project_row.id, upstream)

        brief = ProjectBrief.model_validate(project_row.brief)
        gate_evaluation = validate_stage_payload(
            stage,
            payload,
            schema_version=CURRENT_STAGE_SCHEMA_VERSION,
            brief=brief,
            bible=upstream_payloads.get(StageName.STORY_BIBLE),  # type: ignore[arg-type]
            graph=upstream_payloads.get(StageName.STORY_GRAPH),  # type: ignore[arg-type]
            scene_beats=upstream_payloads.get(StageName.SCENE_BEATS),  # type: ignore[arg-type]
            dialogue_timing_profile=dialogue_timing_profile,
        )
        payload_data = payload.model_dump(mode="json", by_alias=False)
        content_hash = stable_hash(payload_data)
        next_inputs = {key.value: value for key, value in input_revisions.items()}
        if (
            allow_noop
            and head.status == StageStatus.READY.value
            and head.content_hash == content_hash
            and dict(head.input_revisions) == next_inputs
        ):
            if gate_evaluation is not None and head.entity_revision_id is not None:
                current_revision = session.get(EntityRevisionRow, head.entity_revision_id)
                if current_revision is None:
                    raise NotFoundError(
                        f"entity revision not found: {head.entity_revision_id}"
                    )
                self._record_gate_evaluation_in_session(
                    session,
                    project_row.id,
                    current_revision,
                    gate_evaluation,
                    now=now,
                )
            return self._stage_head(head), None

        revision = EntityRevision(
            project_id=project_row.id,
            stage=stage,
            revision=head.revision + 1,
            parent_revision_id=head.entity_revision_id,
            content_hash=content_hash,
            schema_version=CURRENT_STAGE_SCHEMA_VERSION,
            input_revisions=input_revisions,
            payload=payload_data,
            created_at=now,
        )
        revision_row = EntityRevisionRow(
            id=revision.id,
            project_id=revision.project_id,
            stage=stage.value,
            revision=revision.revision,
            parent_revision_id=revision.parent_revision_id,
            content_hash=revision.content_hash,
            schema_version=CURRENT_STAGE_SCHEMA_VERSION,
            input_revisions=next_inputs,
            payload=payload_data,
            created_at=now,
        )
        session.add(revision_row)
        if gate_evaluation is not None:
            # The models intentionally have no ORM relationships, so flush the
            # new immutable revision before inserting its gate receipts.
            session.flush()
            self._record_gate_evaluation_in_session(
                session,
                project_row.id,
                revision_row,
                gate_evaluation,
                now=now,
            )
        head.status = StageStatus.READY.value
        head.revision = revision.revision
        head.entity_revision_id = revision.id
        head.content_hash = content_hash
        head.schema_version = CURRENT_STAGE_SCHEMA_VERSION
        head.input_revisions = next_inputs
        head.stale_reasons = []
        head.updated_at = now
        self._mark_downstream_stale(session, project_row.id, stage, now)
        return self._stage_head(head), revision_row

    def update_stage(
        self,
        project_id: str,
        stage: StageName,
        expected_revision: int,
        payload: StagePayload | dict[str, Any],
    ) -> StageHead:
        parsed = stage_payload_model(stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION).model_validate(payload)
        with self._lifecycle_write() as session:
            project_row = self._project_row(session, project_id)
            self._assert_active_project(project_row)
            head, _ = self._install_stage_in_session(
                session,
                project_row,
                stage,
                parsed,
                expected_revision=expected_revision,
                now=utc_now(),
                allow_noop=True,
            )
            return head

    def update_stage_consuming_authoring_draft(
        self,
        project_id: str,
        stage: StageName,
        expected_revision: int,
        payload: StagePayload | dict[str, Any],
        *,
        entity_id: str,
        expected_draft_revision: int,
    ) -> StageHead:
        """Atomically install a stage and consume its exact authoring draft."""

        parsed = stage_payload_model(stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION).model_validate(payload)
        canonical_payload = parsed.model_dump(mode="json", by_alias=True)
        with self._lifecycle_write() as session:
            project_row = self._project_row(session, project_id)
            self._assert_active_project(project_row)
            head = self._stage_row(session, project_id, stage)
            if head.revision != expected_revision:
                raise RevisionConflictError(f"stage:{stage.value}", expected_revision, head.revision)
            self._consume_exact_authoring_draft_in_session(
                session,
                project_row,
                editor_scope=stage.value,
                entity_id=entity_id,
                expected_draft_revision=expected_draft_revision,
                canonical_base_revision=head.revision,
                canonical_payload=canonical_payload,
            )
            updated, _ = self._install_stage_in_session(
                session,
                project_row,
                stage,
                parsed,
                expected_revision=expected_revision,
                now=utc_now(),
                allow_noop=True,
            )
            return updated

    @staticmethod
    def _snapshot_fingerprint(
        project_revision: int,
        brief: ProjectBrief,
        heads: Sequence[StageHead],
    ) -> dict[str, Any]:
        return {
            "projectRevision": project_revision,
            "brief": brief.model_dump(mode="json", by_alias=True),
            "stages": {
                head.stage.value: {
                    "status": head.status.value,
                    "revision": head.revision,
                    "entityRevisionId": head.entity_revision_id,
                    "inputRevisions": {key.value: value for key, value in head.input_revisions.items()},
                }
                for head in heads
            },
        }

    def _snapshot_in_session(self, session: Session, project_id: str) -> CanonicalSnapshot:
        project = self._project(self._project_row(session, project_id))
        rows = session.scalars(select(StageHeadRow).where(StageHeadRow.project_id == project_id)).all()
        by_stage = {StageName(row.stage): self._stage_head(row) for row in rows}
        heads = [by_stage[stage] for stage in STAGE_ORDER]
        fingerprint = self._snapshot_fingerprint(project.revision, project.brief, heads)
        return CanonicalSnapshot(
            project_id=project_id,
            project_revision=project.revision,
            brief=project.brief,
            stage_heads={head.stage: head for head in heads},
            snapshot_hash=stable_hash(fingerprint),
        )

    def capture_snapshot(self, project_id: str) -> CanonicalSnapshot:
        with self._read() as session:
            return self._snapshot_in_session(session, project_id)

    def snapshot_is_current(self, snapshot: CanonicalSnapshot) -> bool:
        try:
            current = self.capture_snapshot(snapshot.project_id)
        except NotFoundError:
            return False
        return current.snapshot_hash == snapshot.snapshot_hash

    @staticmethod
    def _relevant_input_stages(requested: Sequence[StageName]) -> set[StageName]:
        return set(requested) | {
            upstream for requested_stage in requested for upstream in upstream_stages(requested_stage)
        }

    def _assert_run_inputs_current_in_session(
        self,
        session: Session,
        row: GenerationRunRow,
    ) -> CanonicalSnapshot:
        if RunStatus(row.status) not in {RunStatus.QUEUED, RunStatus.RUNNING}:
            raise InvalidTransitionError(f"run input preflight is not valid from {row.status}")
        if row.result_revision_ids:
            raise InvalidTransitionError("run input preflight must occur before output installation")
        snapshot = CanonicalSnapshot.model_validate(row.canonical_snapshot)
        project = self._project_row(session, row.project_id)
        if project.revision != snapshot.project_revision:
            raise RevisionConflictError("project", snapshot.project_revision, project.revision)
        requested = [StageName(value) for value in row.requested_stages]
        relevant = self._relevant_input_stages(requested)
        for stage in relevant:
            current = self._stage_row(session, row.project_id, stage)
            expected = snapshot.stage_heads[stage]
            if current.revision != expected.revision or current.entity_revision_id != expected.entity_revision_id:
                raise RevisionConflictError(f"stage:{stage.value}", expected.revision, current.revision)
            if current.status != expected.status.value:
                raise InvalidTransitionError(f"stage {stage.value} status changed after the run was enqueued")
            if stage not in requested and current.status != StageStatus.READY.value:
                requested_stage = next(item for item in requested if stage in upstream_stages(item))
                raise StagePrerequisiteError(requested_stage, stage, current.status)
        return snapshot

    def assert_run_inputs_current(self, run_id: str) -> CanonicalSnapshot:
        with self._read() as session:
            return self._assert_run_inputs_current_in_session(session, self._run_row(session, run_id))

    def get_snapshot_stage_payload(self, run_id: str, stage: StageName) -> StagePayload:
        """Read immutable upstream facts by the run snapshot, never a mutable head.

        Snapshot reads are historical evidence, rather than live authoring
        inputs.  A pre-0010 snapshot has no embedded schemaVersion and the
        ``StageHead`` compatibility default intentionally classifies it as V1.
        Decode it with that frozen version; using the live-only decoder here
        would both make historical runs unreadable and invite callers to infer
        V2 semantics from absent V1 fields.
        """

        with self._read() as session:
            row = self._run_row(session, run_id)
            snapshot = CanonicalSnapshot.model_validate(row.canonical_snapshot)
            head = snapshot.stage_heads[stage]
            if head.entity_revision_id is None:
                raise StagePrerequisiteError(stage, stage, head.status.value)
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            if revision is None or revision.project_id != row.project_id or revision.stage != stage.value:
                raise NotFoundError(f"snapshot entity revision not found: {head.entity_revision_id}")
            if revision.schema_version != head.schema_version:
                raise SchemaResetRequiredError(stage=stage, schema_version=head.schema_version)
            return self._decode_stage_payload(stage, revision.payload, head.schema_version)

    def _run_plan_inputs_in_session(
        self,
        session: Session,
        snapshot: CanonicalSnapshot,
        requested_stages: Sequence[StageName],
    ) -> dict[StageName, StagePayload]:
        """Resolve only canonical facts that existed before the requested range.

        The planner deliberately refuses future selectors.  Reading these rows
        through the run snapshot (rather than current heads) makes enqueue-time
        planning reproducible even if a user edits the project immediately
        after the run is created.
        """

        first = STAGE_ORDER.index(requested_stages[0])
        inputs: dict[StageName, StagePayload] = {}
        for stage in STAGE_ORDER[:first]:
            head = snapshot.stage_heads[stage]
            if head.status != StageStatus.READY or head.entity_revision_id is None:
                continue
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            if revision is None:
                raise NotFoundError(f"snapshot entity revision not found: {head.entity_revision_id}")
            inputs[stage] = self._decode_current_stage_payload(
                stage, revision.payload, revision.schema_version
            )
        return inputs

    def create_run(
        self,
        project_id: str,
        kind: RunKind,
        requested_stages: Sequence[StageName],
        *,
        instructions: str | None = None,
        parent_run_id: str | None = None,
        repair_stage: StageName | None = None,
        repair_source: RepairSource | None = None,
        provider_snapshot: dict[str, Any] | None = None,
    ) -> GenerationRun:
        normalized_provider_snapshot = validate_public_provider_snapshot(provider_snapshot)
        supplied_stages = list(requested_stages)
        requested_set = set(supplied_stages)
        ordered_stages = [stage for stage in STAGE_ORDER if stage in requested_set]
        if not ordered_stages:
            raise ValueError("a generation run must request at least one stage")
        first_index = STAGE_ORDER.index(ordered_stages[0])
        expected_range = list(STAGE_ORDER[first_index : first_index + len(ordered_stages)])
        if supplied_stages != ordered_stages or ordered_stages != expected_range:
            raise InvalidTransitionError(
                "requested stages must be unique, ordered, and form one contiguous canonical range"
            )
        with self._lifecycle_write() as session:
            self._assert_new_run_profile_enabled(session, normalized_provider_snapshot)
            if kind == RunKind.REPAIR and (
                parent_run_id is None or repair_stage is None or repair_source is None
            ):
                raise InvalidTransitionError(
                    "repair runs require a quarantined parent, repair stage, and frozen evidence"
                )
            if kind != RunKind.REPAIR and (
                parent_run_id is not None or repair_stage is not None or repair_source is not None
            ):
                raise InvalidTransitionError("only repair runs may have repair lineage")
            if repair_stage is not None and repair_stage not in ordered_stages:
                raise InvalidTransitionError("repair stage must belong to requestedStages")
            if parent_run_id is not None:
                parent = self._run_row(session, parent_run_id)
                if parent.project_id != project_id or RunStatus(parent.status) != RunStatus.QUARANTINED:
                    raise InvalidTransitionError("repair parent must be a quarantined run from the same project")
            project_row = self._project_row(session, project_id)
            self._assert_active_project(project_row)
            snapshot = self._snapshot_in_session(session, project_id)
            run = GenerationRun(
                project_id=project_id,
                kind=kind,
                parent_run_id=parent_run_id,
                repair_stage=repair_stage,
                repair_source=repair_source,
                provider_snapshot=normalized_provider_snapshot,
                requested_stages=ordered_stages,
                canonical_snapshot=snapshot,
                instructions=instructions,
                legacy_unsealed=False,
            )
            session.add(
                GenerationRunRow(
                    id=run.id,
                    project_id=project_id,
                    kind=kind.value,
                    parent_run_id=parent_run_id,
                    repair_stage=repair_stage.value if repair_stage else None,
                    repair_source=(
                        repair_source.model_dump(mode="json", by_alias=False)
                        if repair_source
                        else None
                    ),
                    work_unit_repair_scope_id=None,
                    provider_snapshot=run.provider_snapshot,
                    requested_stages=[stage.value for stage in ordered_stages],
                    status=run.status.value,
                    canonical_snapshot=snapshot.model_dump(mode="json", by_alias=False),
                    instructions=instructions,
                    legacy_unsealed=False,
                    result_revision_ids=[],
                    error=None,
                    created_at=run.created_at,
                    started_at=None,
                    finished_at=None,
                )
            )
            # Rows intentionally have no ORM relationships.  Flush the parent
            # before adding its plan so SQLite enforces the FK rather than
            # relying on SQLAlchemy's incidental INSERT ordering.
            session.flush()
            topology: StoryGraphTopology | None = None
            if StageName.STORY_GRAPH in ordered_stages:
                topology = plan_story_graph_topology(
                    project_id=project_id,
                    brief=snapshot.brief,
                    max_downstream_work_units=128,
                )
            profile_hash = str(run.provider_snapshot.get("profileHash") or stable_hash(run.provider_snapshot))
            stage_budgets: dict[StageName, StageBudget] | None = None
            if is_v2_snapshot(run.provider_snapshot) or is_v3_snapshot(run.provider_snapshot):
                v2_profile = (
                    TextProviderProfileSnapshotV3.model_validate(run.provider_snapshot)
                    if is_v3_snapshot(run.provider_snapshot)
                    else TextProviderProfileSnapshot.model_validate(run.provider_snapshot)
                )
                stage_budgets = {
                    stage: StageBudget(
                        **{
                            **DEFAULT_STAGE_BUDGETS[stage].model_dump(mode="python"),
                            "max_output_tokens": v2_profile.stage_max_output_tokens.for_stage(
                                stage.value
                            ),
                        }
                    )
                    for stage in ordered_stages
                }
            plan = create_generation_plan(
                run_id=run.id,
                requested_stages=ordered_stages,
                provider_profile_hash=profile_hash,
                story_graph_topology_hash=(
                    topology.topology_hash if topology is not None else None
                ),
                canonical_inputs=self._run_plan_inputs_in_session(session, snapshot, ordered_stages),
                stage_budgets=stage_budgets,
                max_concurrency=int(run.provider_snapshot.get("textMaxConcurrency") or 1),
                canonical_snapshot_hash=snapshot.snapshot_hash,
                canonical_snapshot_bytes=len(
                    canonical_json(snapshot.model_dump(mode="json", by_alias=True)).encode("utf-8")
                ),
                instructions=instructions,
                context_window_tokens=int(
                    run.provider_snapshot.get("textContextWindowTokens") or 32_768
                ),
                provider_output_token_ceiling=int(
                    run.provider_snapshot.get("textMaxOutputTokens") or 8_192
                ),
            )
            session.add(
                GenerationPlanRow(
                    run_id=run.id,
                    plan_hash=plan.plan_hash,
                    plan=plan.model_dump(mode="json", by_alias=False),
                    created_at=run.created_at,
                )
            )
            if topology is not None:
                session.add(
                    StoryGraphTopologyRow(
                        run_id=run.id,
                        generation_plan_hash=plan.plan_hash,
                        topology_hash=topology.topology_hash,
                        topology=topology.model_dump(mode="json", by_alias=True),
                        created_at=run.created_at,
                    )
                )
            return run

    def get_run(self, run_id: str) -> GenerationRun:
        with self._read() as session:
            return self._run(self._run_row(session, run_id))

    def get_generation_plan(self, run_id: str) -> GenerationPlan:
        """Return the immutable enqueue-time plan for a non-legacy run."""

        with self._read() as session:
            self._run_row(session, run_id)
            row = session.get(GenerationPlanRow, run_id)
            if row is None:
                raise NotFoundError(f"generation plan not found for run: {run_id}")
            return GenerationPlan.model_validate(row.plan)

    def get_story_graph_topology(self, run_id: str) -> StoryGraphTopology | None:
        """Return the immutable topology for a run that generates Story Graph."""

        with self._read() as session:
            self._run_row(session, run_id)
            row = session.get(StoryGraphTopologyRow, run_id)
            if row is None:
                return None
            topology = StoryGraphTopology.model_validate(row.topology)
            if topology.topology_hash != row.topology_hash:
                raise InvalidTransitionError("stored Story Graph topology hash is inconsistent")
            if row.generation_plan_hash != self._generation_plan_row_hash(session, run_id):
                raise InvalidTransitionError("Story Graph topology is bound to a different GenerationPlan")
            return topology

    @staticmethod
    def _generation_plan_row_hash(session: Session, run_id: str) -> str:
        row = session.get(GenerationPlanRow, run_id)
        if row is None:
            raise InvalidTransitionError("run has no durable GenerationPlan")
        return row.plan_hash

    @staticmethod
    def _stage_plan_row(session: Session, run_id: str, stage: StageName) -> StagePlanRow | None:
        return session.scalar(
            select(StagePlanRow).where(
                StagePlanRow.run_id == run_id,
                StagePlanRow.stage == stage.value,
            )
        )

    def _sealed_payload_in_session(
        self,
        session: Session,
        run_id: str,
        stage: StageName,
    ) -> StagePayload:
        plan = self._stage_plan_row(session, run_id, stage)
        if plan is None:
            raise InvalidTransitionError(
                f"cannot use {stage.value} as a dependency before its StagePlan exists"
            )
        aggregate = session.scalar(
            select(SealedStageAggregateRow).where(
                SealedStageAggregateRow.stage_plan_id == plan.id
            )
        )
        if aggregate is None:
            raise InvalidTransitionError(
                f"cannot use {stage.value} as a dependency before its aggregate is sealed"
            )
        return self._decode_current_stage_payload(
            stage, aggregate.payload, aggregate.schema_version
        )

    def _expected_stage_dependencies_in_session(
        self,
        session: Session,
        run: GenerationRunRow,
        stage: StageName,
    ) -> dict[StageName, StagePayload]:
        """Resolve a stage's immutable dependency boundary for plan/seal checks."""

        snapshot = CanonicalSnapshot.model_validate(run.canonical_snapshot)
        requested = {StageName(value) for value in run.requested_stages}
        dependencies: dict[StageName, StagePayload] = {}
        for dependency in upstream_stages(stage):
            if dependency in requested:
                dependencies[dependency] = self._sealed_payload_in_session(session, run.id, dependency)
                continue
            head = snapshot.stage_heads[dependency]
            if head.status != StageStatus.READY or head.entity_revision_id is None:
                raise StagePrerequisiteError(stage, dependency, head.status.value)
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            if revision is None:
                raise NotFoundError(f"snapshot entity revision not found: {head.entity_revision_id}")
            dependencies[dependency] = self._decode_current_stage_payload(
                dependency, revision.payload, revision.schema_version
            )
        return dependencies

    def _repair_scope_row_in_session(
        self,
        session: Session,
        child: GenerationRunRow,
    ) -> WorkUnitRepairScopeRow:
        if (
            RunKind(child.kind) != RunKind.REPAIR
            or not child.work_unit_repair_scope_id
            or child.work_unit_repair_scope_id != child.id
        ):
            raise InvalidTransitionError("run is not an exact work-unit repair")
        row = session.get(WorkUnitRepairScopeRow, child.id)
        if row is None:
            raise InvalidTransitionError("exact repair run has no immutable repair scope")
        if row.parent_run_id != child.parent_run_id or row.stage != child.repair_stage:
            raise InvalidTransitionError("exact repair scope does not match its child run")
        self._repair_scope(row)
        return row

    def _validate_repair_scope_in_session(
        self,
        session: Session,
        child: GenerationRunRow,
        *,
        require_source_current: bool,
    ) -> WorkUnitRepairScope:
        """Revalidate frozen target, profile, topology and rejection evidence."""

        scope = self._repair_scope(self._repair_scope_row_in_session(session, child))
        source = self._run_row(session, scope.parent_run_id)
        source_plan_row = session.get(GenerationPlanRow, source.id)
        source_stage_plan = session.get(StagePlanRow, scope.source_stage_plan_id)
        target = session.get(GenerationWorkUnitRow, scope.target_work_unit_id)
        if (
            source_plan_row is None
            or source_stage_plan is None
            or target is None
            or RunStatus(source.status) != RunStatus.QUARANTINED
            or source_plan_row.plan_hash != scope.source_generation_plan_hash
            or GenerationPlan.model_validate(source_plan_row.plan).provider_profile_hash
            != scope.source_provider_profile_hash
            or source_stage_plan.run_id != source.id
            or source_stage_plan.stage_plan_hash != scope.source_stage_plan_hash
            or target.run_id != source.id
            or target.stage_plan_id != source_stage_plan.id
            or target.stage != scope.stage.value
            or target.selector != scope.target_selector
            or target.dependency_hash != scope.target_dependency_hash
            or target.unit_dependency_hash != scope.target_unit_dependency_hash
            or target.input_hash != scope.target_input_hash
            or CanonicalSnapshot.model_validate(source.canonical_snapshot).snapshot_hash
            != scope.source_canonical_snapshot_hash
            or child.provider_snapshot != source.provider_snapshot
            or child.canonical_snapshot != source.canonical_snapshot
            or child.instructions != source.instructions
        ):
            raise RepairEligibilityError("repair.scope_hash_mismatch", "exact repair scope no longer matches frozen run contract")
        if self._work_unit_is_sealed_in_session(session, target):
            raise RepairEligibilityError("repair.target_sealed", "exact repair target was sealed in its source run")
        if WorkUnitStatus(target.status) == WorkUnitStatus.OUTCOME_UNKNOWN:
            raise RepairEligibilityError("repair.target_outcome_unknown", "exact repair target has ambiguous provider outcome")
        if WorkUnitStatus(target.status) != WorkUnitStatus.QUARANTINED:
            raise RepairEligibilityError(
                "repair.target_not_quarantined", "exact repair target is no longer quarantined"
            )
        source_topology = session.get(StoryGraphTopologyRow, source.id)
        if (
            (source_topology.topology_hash if source_topology is not None else None)
            != scope.source_story_graph_topology_hash
        ):
            raise RepairEligibilityError("repair.scope_hash_mismatch", "exact repair topology binding changed")
        rejected = self._latest_rejected_evidence_in_session(session, source=source, unit=target)
        if (
            rejected is None
            or rejected[0].id != scope.failed_attempt_id
            or rejected[1].id != scope.response_artifact_id
            or rejected[2].id != scope.validation_artifact_id
        ):
            raise RepairEligibilityError("repair.parent_evidence_invalid", "exact repair rejection evidence changed")
        if require_source_current:
            if (
                ProjectLifecycleStatus(self._project_row(session, source.project_id).lifecycle_status)
                != ProjectLifecycleStatus.ACTIVE
            ):
                raise RepairEligibilityError("repair.project_archived", "archived projects cannot execute exact repairs")
            if not self._source_snapshot_is_current_in_session(session, source):
                raise RepairEligibilityError("repair.snapshot_stale", "repair source inputs changed after quarantine")
        return scope

    def _repair_stage_dependencies_in_session(
        self,
        session: Session,
        child: GenerationRunRow,
        stage: StageName,
    ) -> dict[StageName, StagePayload]:
        """Resolve exact repair dependencies without accepting caller JSON.

        Before (and including) the repaired stage, uninstalled parent seals
        are the only permissible source for requested upstream stages.  After
        it, every requested upstream stage must be a newly child-owned seal,
        which makes downstream regeneration dependency-correct by construction.
        """

        scope = self._validate_repair_scope_in_session(
            session, child, require_source_current=True
        )
        source = self._run_row(session, scope.parent_run_id)
        if not self._source_snapshot_is_current_in_session(session, source):
            raise RepairEligibilityError(
                "repair.snapshot_stale", "repair source inputs changed after quarantine"
            )
        requested = {StageName(value) for value in child.requested_stages}
        if stage not in requested:
            raise InvalidTransitionError(f"{stage.value} is not requested by this repair run")
        target_index = STAGE_ORDER.index(scope.stage)
        dependencies: dict[StageName, StagePayload] = {}
        snapshot = CanonicalSnapshot.model_validate(child.canonical_snapshot)
        for dependency in upstream_stages(stage):
            if dependency not in requested:
                head = snapshot.stage_heads[dependency]
                if head.status != StageStatus.READY or head.entity_revision_id is None:
                    raise StagePrerequisiteError(stage, dependency, head.status.value)
                revision = session.get(EntityRevisionRow, head.entity_revision_id)
                if revision is None:
                    raise NotFoundError(f"snapshot entity revision not found: {head.entity_revision_id}")
                dependencies[dependency] = self._decode_current_stage_payload(
                    dependency, revision.payload, revision.schema_version
                )
                continue
            child_plan = self._stage_plan_row(session, child.id, dependency)
            if child_plan is not None and session.scalar(
                select(SealedStageAggregateRow.id).where(
                    SealedStageAggregateRow.stage_plan_id == child_plan.id
                )
            ) is not None:
                dependencies[dependency] = self._sealed_payload_in_session(session, child.id, dependency)
                continue
            if STAGE_ORDER.index(stage) > target_index:
                raise InvalidTransitionError(
                    f"cannot plan downstream repair stage {stage.value} before child {dependency.value} is sealed"
                )
            parent_plan = self._stage_plan_row(session, source.id, dependency)
            if parent_plan is None:
                raise RepairEligibilityError(
                    "repair.parent_evidence_invalid",
                    f"repair source has no sealed {dependency.value} StagePlan",
                )
            aggregate = session.scalar(
                select(SealedStageAggregateRow).where(
                    SealedStageAggregateRow.stage_plan_id == parent_plan.id
                )
            )
            if aggregate is None:
                raise RepairEligibilityError(
                    "repair.parent_evidence_invalid",
                    f"repair source {dependency.value} aggregate is not sealed",
                )
            dependencies[dependency] = self._decode_current_stage_payload(
                dependency, aggregate.payload, aggregate.schema_version
            )
        return dependencies

    def get_repair_stage_dependencies(
        self,
        child_run_id: str,
        stage: StageName,
    ) -> dict[StageName, StagePayload]:
        with self._read() as session:
            child = self._run_row(session, child_run_id)
            return self._repair_stage_dependencies_in_session(session, child, stage)

    def _repair_scene_beats_timing_profile_in_session(
        self,
        session: Session,
        child: GenerationRunRow,
    ) -> DialogueTimingProfile:
        """Return the parent Scene Beats profile frozen for an exact repair."""

        if child.parent_run_id is None:
            raise RepairEligibilityError(
                "repair.parent_stage_plan_obsolete",
                "Scene Beats repair has no parent timing provenance",
            )
        parent = self._run_row(session, child.parent_run_id)
        row = self._stage_plan_row(session, parent.id, StageName.SCENE_BEATS)
        if row is None or self._scene_beats_stage_plan_contract_code(row) is not None:
            raise RepairEligibilityError(
                "repair.parent_stage_plan_obsolete",
                "Scene Beats repair parent has no valid frozen timing provenance",
            )
        try:
            return self._frozen_dialogue_timing_profile_from_stage_plan(
                StagePlan.model_validate(row.plan)
            )
        except ValueError as exc:
            raise RepairEligibilityError(
                "repair.parent_stage_plan_obsolete",
                "Scene Beats repair parent has invalid frozen timing provenance",
            ) from exc

    def _repair_storyboard_timing_profile_in_session(
        self,
        session: Session,
        child: GenerationRunRow,
    ) -> DialogueTimingProfile:
        """Return the parent Storyboard profile frozen for an exact repair.

        A repair's child StagePlan has a new run ID and dependency hashes, but
        it is not a new authoring decision.  The profile is therefore copied
        from the quarantined parent StagePlan, never selected from whatever
        default happens to exist when the repair executes.
        """

        # A downstream Storyboard plan may be absent from the parent because a
        # Scene Beats shard quarantined first.  Once this child has sealed its
        # repaired Scene Beats aggregate, that child-local plan is the direct
        # frozen provenance for the downstream regeneration.
        child_scene_beats = self._stage_plan_row(
            session, child.id, StageName.SCENE_BEATS
        )
        if child_scene_beats is not None and session.scalar(
            select(SealedStageAggregateRow.id).where(
                SealedStageAggregateRow.stage_plan_id == child_scene_beats.id
            )
        ) is not None:
            if self._scene_beats_stage_plan_contract_code(child_scene_beats) is not None:
                raise RepairEligibilityError(
                    "repair.parent_stage_plan_obsolete",
                    "repaired Scene Beats has no valid frozen timing provenance",
                )
            try:
                return self._frozen_dialogue_timing_profile_from_stage_plan(
                    StagePlan.model_validate(child_scene_beats.plan)
                )
            except ValueError as exc:
                raise RepairEligibilityError(
                    "repair.parent_stage_plan_obsolete",
                    "repaired Scene Beats has invalid frozen timing provenance",
                ) from exc

        if child.parent_run_id is None:
            raise RepairEligibilityError(
                "repair.parent_stage_plan_obsolete",
                "Storyboard repair has no parent timing provenance",
            )
        parent = self._run_row(session, child.parent_run_id)
        row = self._stage_plan_row(session, parent.id, StageName.STORYBOARD)
        if row is None or self._storyboard_stage_plan_contract_code(row) is not None:
            raise RepairEligibilityError(
                "repair.parent_stage_plan_obsolete",
                "Storyboard repair parent has no valid frozen timing provenance",
            )
        try:
            return self._frozen_dialogue_timing_profile_from_stage_plan(
                StagePlan.model_validate(row.plan)
            )
        except ValueError as exc:
            raise RepairEligibilityError(
                "repair.parent_stage_plan_obsolete",
                "Storyboard repair parent has invalid frozen timing provenance",
            ) from exc

    def get_or_create_stage_plan(
        self,
        run_id: str,
        stage: StageName,
        *,
        dependencies: dict[StageName, StagePayload] | None = None,
    ) -> StagePlan:
        """Durably freeze one exact stage plan once all inputs are available.

        Supplying dependencies is intentionally an assertion, not an override:
        the repository compares them to the frozen snapshot/sealed aggregates
        before planning.  This prevents a caller from manufacturing shard
        selectors from mutable or unrelated JSON.
        """

        with self._write() as session:
            run = self._run_row(session, run_id)
            if run.legacy_unsealed:
                raise InvalidTransitionError("legacy/unsealed runs cannot create StagePlans")
            if RunStatus(run.status) not in {RunStatus.QUEUED, RunStatus.RUNNING}:
                raise InvalidTransitionError(
                    f"cannot create a StagePlan while run is {run.status}"
                )
            plan_row = session.get(GenerationPlanRow, run_id)
            if plan_row is None:
                raise InvalidTransitionError("run has no durable GenerationPlan")
            generation_plan = GenerationPlan.model_validate(plan_row.plan)
            # Startup recovery is not the only path into a durable runner:
            # a live worker can also reach this repository command directly.
            # Do not let it create a current StagePlan from an older frozen
            # GenerationPlan, because that would silently substitute current
            # selector/context/prompt semantics for historical evidence.
            if generation_plan.planning_policy_version != PLANNING_POLICY_VERSION:
                raise PlanningError(
                    "frozen GenerationPlan uses an obsolete planning policy and cannot be executed",
                    code="planning.generation_planning_policy_obsolete",
                    stage=stage,
                )
            if stage == StageName.STORY_GRAPH:
                topology_row = session.get(StoryGraphTopologyRow, run_id)
                if topology_row is None:
                    raise InvalidTransitionError(
                        "new Story Graph stage has no frozen deterministic topology"
                    )
                if (
                    generation_plan.story_graph_topology_hash != topology_row.topology_hash
                    or topology_row.generation_plan_hash != generation_plan.plan_hash
                ):
                    raise InvalidTransitionError(
                        "Story Graph topology does not match the frozen GenerationPlan"
                    )
            expected = (
                self._repair_stage_dependencies_in_session(session, run, stage)
                if run.work_unit_repair_scope_id is not None
                else self._expected_stage_dependencies_in_session(session, run, stage)
            )
            if dependencies is not None:
                if set(dependencies) != set(expected) or any(
                    stable_hash(dependencies[name]) != stable_hash(expected[name]) for name in expected
                ):
                    raise InvalidTransitionError(
                        "StagePlan dependencies must exactly match frozen canonical or sealed inputs"
                    )
            existing = self._stage_plan_row(session, run_id, stage)
            if (
                stage == StageName.STORYBOARD
                and existing is not None
                and self._storyboard_stage_plan_contract_code(existing) is not None
            ):
                # Do not recalculate an already durable plan under a new
                # default.  Exact repair uses this same command, so this also
                # prevents a child repair from inheriting an unprovable timing
                # policy after a restart or a tampering incident.
                raise PlanningError(
                    "frozen Storyboard timing provenance is missing or invalid",
                    code="planning.storyboard_timing_provenance_missing",
                    stage=stage,
                )
            snapshot = CanonicalSnapshot.model_validate(run.canonical_snapshot)
            repair_storyboard_profile = (
                self._repair_storyboard_timing_profile_in_session(session, run)
                if (
                    run.work_unit_repair_scope_id is not None
                    and stage == StageName.STORYBOARD
                )
                else None
            )
            repair_scene_beats_profile = (
                self._repair_scene_beats_timing_profile_in_session(session, run)
                if (
                    run.work_unit_repair_scope_id is not None
                    and stage == StageName.SCENE_BEATS
                )
                else None
            )
            proposed = plan_stage(
                generation_plan,
                stage=stage,
                dependencies=expected,
                brief=snapshot.brief,
                scene_beats_dialogue_timing_profile=repair_scene_beats_profile,
                storyboard_dialogue_timing_profile=repair_storyboard_profile,
            )
            if existing is not None:
                if existing.stage_plan_hash != proposed.stage_plan_hash:
                    raise InvalidTransitionError(
                        f"StagePlan for {stage.value} is immutable and differs from this request"
                    )
                return StagePlan.model_validate(existing.plan)

            stage_row = StagePlanRow(
                id=new_id(),
                run_id=run_id,
                stage=stage.value,
                generation_plan_hash=proposed.generation_plan_hash,
                dependency_hash=proposed.dependency_hash,
                stage_plan_hash=proposed.stage_plan_hash,
                plan=proposed.model_dump(mode="json", by_alias=False),
                created_at=utc_now(),
            )
            session.add(stage_row)
            # Work units reference the StagePlan directly by its durable ID.
            # Keep the FK order explicit for the same reason as run/plan.
            session.flush()
            for unit in proposed.work_units:
                session.add(
                    GenerationWorkUnitRow(
                        id=unit.unit_id,
                        run_id=run_id,
                        stage_plan_id=stage_row.id,
                        stage=stage.value,
                        sequence=unit.sequence,
                        selector=unit.selector.model_dump(mode="json", by_alias=False),
                        generation_plan_hash=unit.generation_plan_hash,
                        dependency_hash=unit.dependency_hash,
                        unit_dependency_hash=unit.unit_dependency_hash,
                        input_hash=unit.input_hash,
                        budget=unit.budget.model_dump(mode="json", by_alias=False),
                        estimated_input_tokens=unit.estimated_input_tokens,
                        context_window_tokens=unit.context_window_tokens,
                        status=WorkUnitStatus.QUEUED.value,
                        created_at=stage_row.created_at,
                    )
                )
            return proposed

    def get_or_create_repair_stage_plan(
        self,
        child_run_id: str,
        stage: StageName,
        *,
        dependencies: dict[StageName, StagePayload] | None = None,
    ) -> StagePlan:
        """Create a child-local plan against repository-resolved repair inputs."""

        with self._read() as session:
            self._repair_scope_row_in_session(session, self._run_row(session, child_run_id))
        return self.get_or_create_stage_plan(child_run_id, stage, dependencies=dependencies)

    def list_stage_plans(self, run_id: str) -> list[StagePlan]:
        with self._read() as session:
            self._run_row(session, run_id)
            rows = session.scalars(
                select(StagePlanRow)
                .where(StagePlanRow.run_id == run_id)
                .order_by(StagePlanRow.created_at, StagePlanRow.stage)
            ).all()
            return [StagePlan.model_validate(row.plan) for row in rows]

    def list_generation_work_units(self, run_id: str) -> list[GenerationWorkUnitTrace]:
        with self._read() as session:
            self._run_row(session, run_id)
            rows = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.run_id == run_id)
                .order_by(GenerationWorkUnitRow.stage, GenerationWorkUnitRow.sequence)
            ).all()
            return [self._work_unit_trace(row) for row in rows]

    def get_fragment_reuse_bindings(self, child_run_id: str) -> list[FragmentReuseBinding]:
        with self._read() as session:
            self._repair_scope_row_in_session(session, self._run_row(session, child_run_id))
            rows = session.scalars(
                select(FragmentReuseBindingRow)
                .where(FragmentReuseBindingRow.child_run_id == child_run_id)
                .order_by(FragmentReuseBindingRow.stage, FragmentReuseBindingRow.created_at, FragmentReuseBindingRow.id)
            ).all()
            return [self._fragment_reuse_binding(row) for row in rows]

    def _validate_frozen_reuse_source_in_session(
        self,
        session: Session,
        *,
        scope: WorkUnitRepairScope,
        frozen: FrozenFragmentReuseSource,
    ) -> tuple[GenerationWorkUnitRow, ArtifactRow, GenerationAttemptRow, list[ArtifactRow]]:
        source = self._run_row(session, scope.parent_run_id)
        if not self._source_snapshot_is_current_in_session(session, source):
            raise RepairEligibilityError("repair.snapshot_stale", "repair source inputs changed after quarantine")
        unit = session.get(GenerationWorkUnitRow, frozen.source_work_unit_id)
        plan = session.get(StagePlanRow, frozen.source_stage_plan_id)
        if (
            unit is None
            or plan is None
            or unit.run_id != source.id
            or unit.stage_plan_id != plan.id
            or unit.stage != frozen.stage.value
            or plan.run_id != source.id
            or plan.stage_plan_hash != frozen.source_stage_plan_hash
            or unit.generation_plan_hash != frozen.source_generation_plan_hash
            or unit.selector != frozen.source_selector
            or unit.dependency_hash != frozen.source_dependency_hash
            or unit.unit_dependency_hash != frozen.source_unit_dependency_hash
            or unit.input_hash != frozen.source_input_hash
        ):
            raise RepairEligibilityError("repair.parent_evidence_invalid", "frozen reusable source no longer matches parent evidence")
        candidate, attempt, evidence = self._required_unit_evidence_in_session(
            session,
            run_id=source.id,
            stage=frozen.stage,
            unit=unit,
            candidate_id=frozen.source_candidate_artifact_id,
        )
        evidence_by_kind = {row.kind: row for row in evidence}
        if (
            candidate.content_hash != frozen.source_candidate_content_hash
            or attempt.id != frozen.source_producer_attempt_id
            or evidence_by_kind[ArtifactKind.RESPONSE.value].id != frozen.source_response_artifact_id
            or evidence_by_kind[ArtifactKind.VALIDATION.value].id != frozen.source_validation_artifact_id
        ):
            raise RepairEligibilityError("repair.parent_evidence_invalid", "frozen reusable evidence IDs or hashes changed")
        return unit, candidate, attempt, evidence

    def prepare_repair_stage_reuse(
        self,
        child_run_id: str,
        stage: StageName,
    ) -> list[FragmentReuseBinding]:
        """Bind the scope's frozen parent candidates to planned child units.

        It creates no candidate artifact.  This separation lets the runner
        make every durable child-local materialization visible and idempotent.
        """

        with self._write() as session:
            child = self._run_row(session, child_run_id)
            scope = self._validate_repair_scope_in_session(
                session, child, require_source_current=True
            )
            child_plan = self._stage_plan_row(session, child_run_id, stage)
            if child_plan is None:
                raise InvalidTransitionError(f"cannot prepare reuse before child {stage.value} StagePlan exists")
            child_units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.stage_plan_id == child_plan.id)
                .order_by(GenerationWorkUnitRow.sequence)
            ).all()
            by_selector = {stable_hash(unit.selector): unit for unit in child_units}
            if len(by_selector) != len(child_units):
                raise InvalidTransitionError("child StagePlan contains duplicate selectors")
            frozen_sources = [item for item in scope.reuse_sources if item.stage == stage]
            frozen_selector_hashes = {stable_hash(item.source_selector) for item in frozen_sources}
            child_selector_hashes = set(by_selector)
            if STAGE_ORDER.index(stage) < STAGE_ORDER.index(scope.stage):
                # Exact repair may never send a new provider request for an
                # upstream stage.  A planner or stored-plan drift that adds
                # even one selector would otherwise turn this into a hidden
                # partial rebuild.
                if child_selector_hashes != frozen_selector_hashes:
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "upstream repair StagePlan selectors must exactly equal frozen reuse selectors",
                    )
            elif STAGE_ORDER.index(stage) > STAGE_ORDER.index(scope.stage):
                if frozen_sources:
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "downstream repair stages cannot carry frozen reuse selectors",
                    )
            if stage == scope.stage:
                target_child = by_selector.get(stable_hash(scope.target_selector))
                source_target = session.get(GenerationWorkUnitRow, scope.target_work_unit_id)
                if (
                    target_child is None
                    or source_target is None
                    or source_target.run_id != scope.parent_run_id
                    or source_target.selector != scope.target_selector
                    or source_target.dependency_hash != scope.target_dependency_hash
                    or source_target.unit_dependency_hash != scope.target_unit_dependency_hash
                    or source_target.input_hash != scope.target_input_hash
                ):
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "target child selector no longer matches the immutable repair scope",
                    )
                unbound_selector_hashes = child_selector_hashes - frozen_selector_hashes
                if unbound_selector_hashes != {stable_hash(scope.target_selector)}:
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "repair StagePlan must leave exactly the scoped target selector unresolved",
                    )
            bindings: list[FragmentReuseBinding] = []
            for frozen in frozen_sources:
                self._validate_frozen_reuse_source_in_session(session, scope=scope, frozen=frozen)
                child_unit = by_selector.get(stable_hash(frozen.source_selector))
                if child_unit is None:
                    raise RepairEligibilityError(
                        "repair.scope_hash_mismatch",
                        "child StagePlan no longer contains the frozen reusable selector",
                    )
                existing = session.scalar(
                    select(FragmentReuseBindingRow).where(
                        FragmentReuseBindingRow.child_work_unit_id == child_unit.id
                    )
                )
                unsigned = {
                    "childRunId": child_run_id,
                    "childStagePlanId": child_plan.id,
                    "childStagePlanHash": child_plan.stage_plan_hash,
                    "childWorkUnitId": child_unit.id,
                    "stage": stage,
                    "kind": frozen.kind,
                    "sourceRunId": scope.parent_run_id,
                    "sourceWorkUnitId": frozen.source_work_unit_id,
                    "sourceStagePlanId": frozen.source_stage_plan_id,
                    "sourceCandidateArtifactId": frozen.source_candidate_artifact_id,
                    "sourceCandidateContentHash": frozen.source_candidate_content_hash,
                    "sourceStagePlanHash": frozen.source_stage_plan_hash,
                    "sourceSelector": frozen.source_selector,
                    "sourceDependencyHash": frozen.source_dependency_hash,
                    "sourceUnitDependencyHash": frozen.source_unit_dependency_hash,
                    "sourceInputHash": frozen.source_input_hash,
                    "sourceProducerAttemptId": frozen.source_producer_attempt_id,
                    "sourceResponseArtifactId": frozen.source_response_artifact_id,
                    "sourceValidationArtifactId": frozen.source_validation_artifact_id,
                    "childSelector": dict(child_unit.selector),
                    "childDependencyHash": child_unit.dependency_hash,
                    "childUnitDependencyHash": child_unit.unit_dependency_hash,
                    "childInputHash": child_unit.input_hash,
                    "createdAt": scope.created_at.isoformat(),
                }
                provisional_binding = FragmentReuseBinding(
                    id=new_id(),
                    **unsigned,
                    binding_hash="pending",
                )
                binding_hash = stable_hash(
                    {
                        key: value
                        for key, value in provisional_binding.model_dump(mode="json", by_alias=True).items()
                        if key not in {"id", "bindingHash"}
                    }
                )
                if existing is not None:
                    binding = self._fragment_reuse_binding(existing)
                    if binding.binding_hash != binding_hash:
                        raise RepairEligibilityError(
                            "repair.scope_hash_mismatch", "existing child reuse binding differs from frozen scope"
                        )
                    bindings.append(binding)
                    continue
                binding = provisional_binding.model_copy(update={"binding_hash": binding_hash})
                session.add(
                    FragmentReuseBindingRow(
                        id=binding.id,
                        child_run_id=binding.child_run_id,
                        child_stage_plan_id=binding.child_stage_plan_id,
                        child_work_unit_id=binding.child_work_unit_id,
                        stage=binding.stage.value,
                        kind=binding.kind.value,
                        source_run_id=binding.source_run_id,
                        source_work_unit_id=binding.source_work_unit_id,
                        source_stage_plan_id=binding.source_stage_plan_id,
                        source_candidate_artifact_id=binding.source_candidate_artifact_id,
                        binding_hash=binding.binding_hash,
                        binding=binding.model_dump(mode="json", by_alias=True),
                        created_at=binding.created_at,
                    )
                )
                bindings.append(binding)
            return bindings

    def materialize_fragment_reuse_binding(
        self,
        child_run_id: str,
        binding_id: str,
    ) -> Artifact:
        """Create one child-owned, metadata-rebound candidate from a binding."""

        with self._write() as session:
            child = self._run_row(session, child_run_id)
            scope = self._validate_repair_scope_in_session(
                session, child, require_source_current=True
            )
            row = session.get(FragmentReuseBindingRow, binding_id)
            if row is None or row.child_run_id != child_run_id:
                raise NotFoundError(f"fragment reuse binding not found for child run: {binding_id}")
            binding = self._fragment_reuse_binding(row)
            frozen = next(
                (
                    item
                    for item in scope.reuse_sources
                    if item.source_candidate_artifact_id == binding.source_candidate_artifact_id
                    and item.source_work_unit_id == binding.source_work_unit_id
                ),
                None,
            )
            if frozen is None:
                raise RepairEligibilityError("repair.scope_hash_mismatch", "binding is absent from immutable repair scope")
            _, source_candidate, _, _ = self._validate_frozen_reuse_source_in_session(
                session, scope=scope, frozen=frozen
            )
            child_unit = session.get(GenerationWorkUnitRow, binding.child_work_unit_id)
            child_plan = session.get(StagePlanRow, binding.child_stage_plan_id)
            if (
                child_unit is None
                or child_plan is None
                or child_unit.run_id != child_run_id
                or child_unit.stage_plan_id != child_plan.id
                or child_unit.stage != binding.stage.value
                or child_plan.stage_plan_hash != binding.child_stage_plan_hash
                or child_unit.selector != binding.child_selector
                or child_unit.dependency_hash != binding.child_dependency_hash
                or child_unit.unit_dependency_hash != binding.child_unit_dependency_hash
                or child_unit.input_hash != binding.child_input_hash
            ):
                raise RepairEligibilityError("repair.scope_hash_mismatch", "child work unit no longer matches reuse binding")
            self._assert_work_unit_unsealed_in_session(session, child_unit)
            existing = session.scalar(
                select(ArtifactRow).where(
                    ArtifactRow.run_id == child_run_id,
                    ArtifactRow.work_unit_id == child_unit.id,
                    ArtifactRow.kind == ArtifactKind.CANDIDATE.value,
                    ArtifactRow.source_artifact_id == source_candidate.id,
                )
            )
            source_fragment = self._fragment_from_artifact(binding.stage, source_candidate)
            rebound = source_fragment.model_copy(
                update={"stage_plan_hash": child_plan.stage_plan_hash, "work_unit_id": child_unit.id}
            )
            content = rebound.model_dump(mode="json", by_alias=False)
            content_hash = stable_hash(content)
            if existing is not None:
                if existing.content_hash != content_hash or existing.attempt_id is not None:
                    raise RepairEligibilityError("repair.scope_hash_mismatch", "existing child reuse candidate differs from binding")
                if WorkUnitStatus(child_unit.status) == WorkUnitStatus.QUEUED:
                    child_unit.status = WorkUnitStatus.SUCCEEDED.value
                return self._artifact(existing)
            if WorkUnitStatus(child_unit.status) != WorkUnitStatus.QUEUED:
                raise InvalidTransitionError(
                    f"cannot materialize reuse while child work unit is {child_unit.status}"
                )
            artifact = Artifact(
                run_id=child_run_id,
                attempt_id=None,
                work_unit_id=child_unit.id,
                source_artifact_id=source_candidate.id,
                stage=binding.stage,
                kind=ArtifactKind.CANDIDATE,
                content=content,
                content_hash=content_hash,
            )
            session.add(
                ArtifactRow(
                    id=artifact.id,
                    run_id=artifact.run_id,
                    attempt_id=None,
                    work_unit_id=artifact.work_unit_id,
                    source_artifact_id=artifact.source_artifact_id,
                    stage=artifact.stage.value if artifact.stage else None,
                    kind=artifact.kind.value,
                    media_type=artifact.media_type,
                    content=content,
                    content_hash=artifact.content_hash,
                    created_at=artifact.created_at,
                )
            )
            child_unit.status = WorkUnitStatus.SUCCEEDED.value
            return artifact

    def materialize_reused_fragment(self, child_run_id: str, binding_id: str) -> Artifact:
        """Compatibility spelling for the explicit fragment-binding command."""

        return self.materialize_fragment_reuse_binding(child_run_id, binding_id)

    @staticmethod
    def _work_unit_is_sealed_in_session(
        session: Session,
        unit: GenerationWorkUnitRow,
    ) -> bool:
        return (
            session.scalar(
                select(SealedStageAggregateRow.id).where(
                    SealedStageAggregateRow.stage_plan_id == unit.stage_plan_id
                )
            )
            is not None
        )

    def _assert_work_unit_unsealed_in_session(
        self,
        session: Session,
        unit: GenerationWorkUnitRow,
    ) -> None:
        if self._work_unit_is_sealed_in_session(session, unit):
            raise InvalidTransitionError(
                "cannot change an attempt or artifact after its work-unit stage aggregate is sealed"
            )

    def _attempt_work_unit_unsealed_in_session(
        self,
        session: Session,
        attempt: GenerationAttemptRow,
    ) -> GenerationWorkUnitRow | None:
        if attempt.work_unit_id is None:
            return None
        unit = session.get(GenerationWorkUnitRow, attempt.work_unit_id)
        if unit is None:
            raise NotFoundError(f"generation work unit not found: {attempt.work_unit_id}")
        self._assert_work_unit_unsealed_in_session(session, unit)
        return unit

    @staticmethod
    def _all_requested_stage_aggregates_are_sealed_in_session(
        session: Session,
        run: GenerationRunRow,
    ) -> bool:
        requested = {StageName(value).value for value in run.requested_stages}
        plans = session.scalars(
            select(StagePlanRow).where(StagePlanRow.run_id == run.id)
        ).all()
        if {plan.stage for plan in plans} != requested:
            return False
        if not plans:
            return False
        sealed_plan_ids = set(
            session.scalars(
                select(SealedStageAggregateRow.stage_plan_id).where(
                    SealedStageAggregateRow.stage_plan_id.in_([plan.id for plan in plans])
                )
            ).all()
        )
        return sealed_plan_ids == {plan.id for plan in plans}

    @staticmethod
    def _obsolete_scene_beats_recovery_code_in_session(
        session: Session,
        run: GenerationRunRow,
    ) -> str | None:
        """Return the stable reason an interrupted Scene Beats run is obsolete.

        Timing allocation and dialogue capacity are part of the immutable
        Scene Beats StagePlan rather than startup defaults. Join-entry facts
        now share that immutable boundary. Old plans (including pristine runs
        created under an older planning policy) must be stopped before a
        runner can recompute dependency or prompt identities.
        """

        requested = {StageName(value) for value in run.requested_stages}
        if StageName.SCENE_BEATS not in requested:
            return None
        generation_plan_row = session.get(GenerationPlanRow, run.id)
        if generation_plan_row is None:
            return "recovery.join_state_value_contract_obsolete"
        try:
            generation_plan = GenerationPlan.model_validate(generation_plan_row.plan)
        except ValueError:
            return "recovery.join_state_value_contract_obsolete"

        plans = session.scalars(
            select(StagePlanRow).where(StagePlanRow.run_id == run.id)
        ).all()
        reached_scene_beats = any(
            StageName(plan.stage) in {StageName.SCENE_BEATS, StageName.STORYBOARD}
            for plan in plans
        )
        if not reached_scene_beats:
            return (
                "recovery.join_state_value_contract_obsolete"
                if generation_plan.planning_policy_version
                != PLANNING_POLICY_VERSION
                else None
            )
        scene_beats_plan = next(
            (plan for plan in plans if plan.stage == StageName.SCENE_BEATS.value),
            None,
        )
        if scene_beats_plan is None:
            return "recovery.scene_timing_contract_obsolete"
        scene_beats_contract_code = (
            SQLiteRepository._scene_beats_stage_plan_contract_code(scene_beats_plan)
        )
        if scene_beats_contract_code is not None:
            return scene_beats_contract_code
        if generation_plan.planning_policy_version != PLANNING_POLICY_VERSION:
            return "recovery.join_state_value_contract_obsolete"
        return None

    @staticmethod
    def _scene_beats_stage_plan_contract_code(
        scene_beats_plan: StagePlanRow,
    ) -> str | None:
        """Classify a persisted Scene Beats plan without supplying defaults.

        The ordering is intentional: an already-reached timing/capacity
        contract predates and is more specific than the later join marker.
        Both branches preserve historical plan JSON; callers only use the
        result to refuse a nonterminal continuation.
        """

        allocation = scene_beats_plan.plan.get("scene_timing_allocation")
        if not isinstance(allocation, dict):
            return "recovery.scene_timing_contract_obsolete"
        try:
            parsed_allocation = SceneTimingAllocation.model_validate(allocation)
            parsed_plan = StagePlan.model_validate(scene_beats_plan.plan)
        except ValueError:
            return "recovery.scene_timing_contract_obsolete"
        # StagePlan keeps these fields optional only to preserve the exact
        # serialized shape of terminal historical evidence.  A nonterminal
        # Scene Beats run cannot be resumed without the complete frozen
        # dialogue contract, however: reconstructing it would change the
        # request identity.  Parsing the full plan also verifies that the
        # profile, capacity plan, timing allocation, and work units remain
        # mutually bound rather than merely individually well-formed.
        if (
            parsed_allocation.allocation_version != SCENE_TIMING_ALLOCATION_VERSION
            or parsed_plan.dialogue_timing_profile is None
            or parsed_plan.dialogue_capacity_plan is None
            or parsed_plan.dialogue_capacity_plan.policy_version
            != DIALOGUE_CAPACITY_POLICY_VERSION
        ):
            return "recovery.scene_timing_contract_obsolete"
        if (
            parsed_plan.join_state_value_contract_version
            != JOIN_STATE_VALUE_CONTRACT_VERSION
            or parsed_plan.join_state_value_contract_hash is None
        ):
            return "recovery.join_state_value_contract_obsolete"
        return None

    @staticmethod
    def _storyboard_stage_plan_contract_code(
        storyboard_plan: StagePlanRow,
    ) -> str | None:
        """Classify StagePlan-local Storyboard timing provenance.

        The canonical Scene Beats payload is intentionally content-only and
        cannot be retroactively credited with a profile from some prior run.
        This check therefore examines only the immutable Storyboard plan.  It
        is used for nonterminal recovery and direct repair planning; terminal
        history is never parsed, rewritten, or upgraded for this purpose.
        """

        try:
            parsed_plan = StagePlan.model_validate(storyboard_plan.plan)
        except ValueError:
            return "recovery.storyboard_timing_provenance_missing"
        if (
            parsed_plan.stage != StageName.STORYBOARD
            or parsed_plan.storyboard_dialogue_timing_profile is None
        ):
            return "recovery.storyboard_timing_provenance_missing"
        return None

    @staticmethod
    def _obsolete_generation_planning_policy_recovery_code_in_session(
        session: Session,
        run: GenerationRunRow,
    ) -> str | None:
        """Refuse any non-legacy run whose plan needs a newer executable policy."""

        requested = {StageName(value) for value in run.requested_stages}
        if StageName.SCENE_BEATS in requested:
            scene_beats_code = (
                SQLiteRepository._obsolete_scene_beats_recovery_code_in_session(
                    session, run
                )
            )
            if scene_beats_code is not None:
                return scene_beats_code
        generation_plan_row = session.get(GenerationPlanRow, run.id)
        if generation_plan_row is None:
            return "recovery.generation_planning_policy_obsolete"
        try:
            generation_plan = GenerationPlan.model_validate(generation_plan_row.plan)
        except ValueError:
            return "recovery.generation_planning_policy_obsolete"
        if generation_plan.planning_policy_version != PLANNING_POLICY_VERSION:
            return "recovery.generation_planning_policy_obsolete"
        if StageName.STORYBOARD in requested:
            storyboard_plan = SQLiteRepository._stage_plan_row(
                session, run.id, StageName.STORYBOARD
            )
            if storyboard_plan is not None:
                contract_code = SQLiteRepository._storyboard_stage_plan_contract_code(
                    storyboard_plan
                )
                if contract_code is not None:
                    return contract_code
        return None

    @staticmethod
    def _recovery_obsolete_contract_stage(
        session: Session,
        run: GenerationRunRow,
        code: str,
    ) -> StageName:
        if code in {
            "recovery.scene_timing_contract_obsolete",
            "recovery.join_state_value_contract_obsolete",
        }:
            return StageName.SCENE_BEATS
        if code == "recovery.storyboard_timing_provenance_missing":
            return StageName.STORYBOARD
        for stage in (StageName(value) for value in run.requested_stages):
            plan = SQLiteRepository._stage_plan_row(session, run.id, stage)
            if plan is None:
                return stage
            sealed = session.scalar(
                select(SealedStageAggregateRow.id).where(
                    SealedStageAggregateRow.stage_plan_id == plan.id
                )
            )
            if sealed is None:
                return stage
        # This branch is defensive: a run with every requested stage sealed
        # normally takes the atomic-commit recovery branch instead.
        return StageName(run.requested_stages[0])

    @staticmethod
    def _cancel_run_work_units_in_session(
        session: Session,
        run_id: str,
        *,
        now: datetime,
        attempt_error: str,
    ) -> None:
        """Close unfinished unit execution when a run reaches cancellation."""

        running_attempts = session.scalars(
            select(GenerationAttemptRow).where(
                GenerationAttemptRow.run_id == run_id,
                GenerationAttemptRow.status == AttemptStatus.RUNNING.value,
            )
        ).all()
        for attempt in running_attempts:
            attempt.status = AttemptStatus.CANCELLED.value
            attempt.error = attempt_error
            attempt.finished_at = now
        units = session.scalars(
            select(GenerationWorkUnitRow).where(GenerationWorkUnitRow.run_id == run_id)
        ).all()
        for unit in units:
            if WorkUnitStatus(unit.status) in {
                WorkUnitStatus.QUEUED,
                WorkUnitStatus.RUNNING,
            }:
                unit.status = WorkUnitStatus.CANCELLED.value

    def allocate_attempt_for_work_unit(
        self,
        work_unit_id: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        attempt_kind: GenerationAttemptKind = GenerationAttemptKind.PRIMARY,
        source_attempt_id: str | None = None,
        max_attempts: int | None = None,
    ) -> GenerationAttempt:
        """Atomically claim one executable work unit for its provider attempt.

        Known schema/semantic rejection may authorize one explicit correction
        attempt through ``allow_correction``. Startup recovery never consumes
        another attempt number: it resumes the same durable identity only when
        the repository can prove either that dispatch never happened or that
        the provider response is already durable.
        """

        try:
            with self._work_unit_claim_write() as session:
                unit = session.get(GenerationWorkUnitRow, work_unit_id)
                if unit is None:
                    raise NotFoundError(f"generation work unit not found: {work_unit_id}")
                run = self._run_row(session, unit.run_id)
                if RunStatus(run.status) != RunStatus.RUNNING:
                    raise InvalidTransitionError(
                        f"cannot allocate a work-unit attempt while run is {run.status}"
                    )
                if WorkUnitStatus(unit.status) != WorkUnitStatus.QUEUED:
                    raise InvalidTransitionError(
                        f"cannot allocate an attempt while work unit is {unit.status}"
                    )

                prior_attempts = session.scalars(
                    select(GenerationAttemptRow)
                    .where(GenerationAttemptRow.work_unit_id == unit.id)
                    .order_by(GenerationAttemptRow.attempt_number)
                ).all()
                if any(AttemptStatus(row.status) == AttemptStatus.RUNNING for row in prior_attempts):
                    raise InvalidTransitionError("work unit already has an active attempt")
                if attempt_kind == GenerationAttemptKind.PRIMARY:
                    if source_attempt_id is not None:
                        raise InvalidTransitionError("a primary attempt cannot name a source attempt")
                    if any(
                        row.dispatched_at is not None
                        or row.response_persisted_at is not None
                        or row.outcome_unknown
                        for row in prior_attempts
                    ):
                        raise InvalidTransitionError(
                            "work unit has prior dispatched or ambiguous evidence and requires an explicit correction"
                        )
                else:
                    if not prior_attempts or source_attempt_id != prior_attempts[-1].id:
                        raise InvalidTransitionError(
                            "a correction must name the latest attempt in its work unit"
                        )
                    source = prior_attempts[-1]
                    if (
                        AttemptStatus(source.status) != AttemptStatus.FAILED
                        or source.response_persisted_at is None
                        or source.outcome_unknown
                        or not source.outcome_code
                    ):
                        raise InvalidTransitionError(
                            "a correction source must be a known rejected response"
                        )

                attempt_number = max(
                    (row.attempt_number for row in prior_attempts),
                    default=0,
                ) + 1
                if max_attempts is not None and attempt_number > max_attempts:
                    raise InvalidTransitionError(
                        f"work unit attempt limit {max_attempts} has been exhausted"
                    )
                attempt = GenerationAttempt(
                    run_id=unit.run_id,
                    work_unit_id=unit.id,
                    stage=StageName(unit.stage),
                    attempt_number=attempt_number,
                    attempt_kind=attempt_kind,
                    source_attempt_id=source_attempt_id,
                    status=AttemptStatus.RUNNING,
                    provider=provider,
                    model=model,
                )
                session.add(
                    GenerationAttemptRow(
                        id=attempt.id,
                        run_id=attempt.run_id,
                        work_unit_id=attempt.work_unit_id,
                        stage=attempt.stage.value,
                        attempt_number=attempt.attempt_number,
                        attempt_kind=attempt.attempt_kind.value,
                        source_attempt_id=attempt.source_attempt_id,
                        status=attempt.status.value,
                        provider=provider,
                        model=model,
                        error=None,
                        dispatched_at=None,
                        response_persisted_at=None,
                        provider_request_id=None,
                        outcome_unknown=False,
                        outcome_code=None,
                        started_at=attempt.started_at,
                        finished_at=None,
                    )
                )
                unit.status = WorkUnitStatus.RUNNING.value
                # Force the DB uniqueness guard inside the claim transaction.
                # If an external writer beat this process, the error below is
                # mapped to the same domain conflict as an observed RUNNING unit.
                session.flush()
                return attempt
        except IntegrityError as error:
            raise InvalidTransitionError("work unit has already been claimed by another allocator") from error

    def get_recoverable_attempt_for_work_unit(
        self,
        work_unit_id: str,
    ) -> GenerationAttempt | None:
        """Return the sole in-flight attempt safe to resume without replay.

        A pre-dispatch attempt may continue to the provider boundary. An
        attempt with a durably stored response may continue local extraction
        and validation. A dispatch marker without a response is intentionally
        excluded because its external outcome is unknown.
        """

        with self._read() as session:
            unit = session.get(GenerationWorkUnitRow, work_unit_id)
            if unit is None:
                raise NotFoundError(f"generation work unit not found: {work_unit_id}")
            if WorkUnitStatus(unit.status) != WorkUnitStatus.RUNNING:
                return None
            rows = session.scalars(
                select(GenerationAttemptRow)
                .where(
                    GenerationAttemptRow.work_unit_id == work_unit_id,
                    GenerationAttemptRow.status == AttemptStatus.RUNNING.value,
                )
                .order_by(GenerationAttemptRow.attempt_number.desc())
            ).all()
            if len(rows) > 1:
                raise InvalidTransitionError("work unit has multiple running attempts")
            if not rows:
                return None
            row = rows[0]
            if row.dispatched_at is not None and row.response_persisted_at is None:
                return None
            return self._attempt(row)

    def mark_attempt_dispatched(self, attempt_id: str) -> GenerationAttempt:
        """Commit the non-idempotent provider-boundary marker before an HTTP call."""

        with self._write() as session:
            row = session.get(GenerationAttemptRow, attempt_id)
            if row is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            if row.work_unit_id is None:
                raise InvalidTransitionError("only work-unit attempts have dispatch markers")
            self._attempt_work_unit_unsealed_in_session(session, row)
            if AttemptStatus(row.status) != AttemptStatus.RUNNING:
                raise InvalidTransitionError(f"cannot dispatch attempt from {row.status}")
            run = self._run_row(session, row.run_id)
            if RunStatus(run.status) != RunStatus.RUNNING:
                raise InvalidTransitionError(
                    f"cannot dispatch attempt while run is {run.status}"
                )
            if row.dispatched_at is None:
                row.dispatched_at = utc_now()
            return self._attempt(row)

    def persist_attempt_response(
        self,
        attempt_id: str,
        content: Any,
        *,
        provider_request_id: str | None = None,
    ) -> Artifact:
        """Atomically retain raw response evidence before parsing or validation."""

        self._assert_secret_free_artifact_content(content)
        with self._write() as session:
            attempt = session.get(GenerationAttemptRow, attempt_id)
            if attempt is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            if attempt.work_unit_id is None or attempt.dispatched_at is None:
                raise InvalidTransitionError("a provider response requires a durable dispatch marker")
            self._attempt_work_unit_unsealed_in_session(session, attempt)
            if AttemptStatus(attempt.status) != AttemptStatus.RUNNING:
                raise InvalidTransitionError(f"cannot persist response while attempt is {attempt.status}")
            existing = session.scalar(
                select(ArtifactRow).where(
                    ArtifactRow.attempt_id == attempt_id,
                    ArtifactRow.kind == ArtifactKind.RESPONSE.value,
                )
            )
            content_hash = stable_hash(content)
            if existing is not None:
                if existing.content_hash != content_hash:
                    raise InvalidTransitionError("provider response evidence is immutable")
                return self._artifact(existing)
            artifact = Artifact(
                run_id=attempt.run_id,
                attempt_id=attempt.id,
                work_unit_id=attempt.work_unit_id,
                stage=StageName(attempt.stage),
                kind=ArtifactKind.RESPONSE,
                content=content,
                content_hash=content_hash,
            )
            session.add(
                ArtifactRow(
                    id=artifact.id,
                    run_id=artifact.run_id,
                    attempt_id=artifact.attempt_id,
                    work_unit_id=artifact.work_unit_id,
                    source_artifact_id=None,
                    stage=artifact.stage.value,
                    kind=artifact.kind.value,
                    media_type=artifact.media_type,
                    content=_json_data(content),
                    content_hash=content_hash,
                    created_at=artifact.created_at,
                )
            )
            attempt.provider_request_id = provider_request_id
            attempt.response_persisted_at = artifact.created_at
            return artifact

    def mark_attempt_outcome_unknown(self, attempt_id: str, *, error: str) -> GenerationAttempt:
        """Record an ambiguous post-dispatch loss without authorizing replay."""

        with self._write() as session:
            row = session.get(GenerationAttemptRow, attempt_id)
            if row is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            if row.work_unit_id is None or row.dispatched_at is None:
                raise InvalidTransitionError("only dispatched work-unit attempts can become outcome_unknown")
            self._attempt_work_unit_unsealed_in_session(session, row)
            if AttemptStatus(row.status) != AttemptStatus.RUNNING:
                raise InvalidTransitionError(f"cannot mark outcome unknown from {row.status}")
            row.status = AttemptStatus.FAILED.value
            row.error = error
            row.outcome_unknown = True
            row.outcome_code = "provider.outcome_unknown"
            row.finished_at = utc_now()
            unit = session.get(GenerationWorkUnitRow, row.work_unit_id)
            if unit is None:
                raise NotFoundError(f"generation work unit not found: {row.work_unit_id}")
            unit.status = WorkUnitStatus.OUTCOME_UNKNOWN.value
            return self._attempt(row)

    def get_run_execution_trace(self, run_id: str) -> RunExecutionTrace:
        """Return only durable plan/work-unit/seal evidence for a run.

        The existing ``RunTrace`` is intentionally left compact and compatible;
        callers that need shard-level diagnostics use this additive endpoint.
        """

        with self._read() as session:
            self._run_row(session, run_id)
            plan = session.get(GenerationPlanRow, run_id)
            topology = session.get(StoryGraphTopologyRow, run_id)
            stage_plans = session.scalars(
                select(StagePlanRow)
                .where(StagePlanRow.run_id == run_id)
                .order_by(StagePlanRow.created_at, StagePlanRow.stage)
            ).all()
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.run_id == run_id)
                .order_by(GenerationWorkUnitRow.stage, GenerationWorkUnitRow.sequence)
            ).all()
            aggregates = session.scalars(
                select(SealedStageAggregateRow)
                .where(SealedStageAggregateRow.run_id == run_id)
                .order_by(SealedStageAggregateRow.created_at, SealedStageAggregateRow.stage)
            ).all()
            return RunExecutionTrace(
                generation_plan=self._generation_plan_trace(plan) if plan is not None else None,
                story_graph_topology=(
                    self._story_graph_topology_trace(topology)
                    if topology is not None
                    else None
                ),
                stage_plans=[self._stage_plan_trace(row) for row in stage_plans],
                work_units=[self._work_unit_trace(row) for row in units],
                sealed_aggregates=[self._sealed_aggregate_trace(row) for row in aggregates],
            )

    @staticmethod
    def _run_max_attempts(row: GenerationRunRow) -> int:
        """Read the frozen correction budget without synthesizing V2 history."""

        if is_v2_snapshot(row.provider_snapshot) or is_v3_snapshot(row.provider_snapshot):
            profile = (
                TextProviderProfileSnapshotV3.model_validate(row.provider_snapshot)
                if is_v3_snapshot(row.provider_snapshot)
                else TextProviderProfileSnapshot.model_validate(row.provider_snapshot)
            )
            return 1 + profile.max_semantic_corrections
        # Historical snapshots have no V2 execution contract.  Their old
        # stage-level attempt behavior must not acquire a new implicit limit.
        return 1

    def get_run_progress(self, run_id: str) -> RunProgress:
        """Return a compact, secret-free polling projection for the workbench."""

        with self._read() as session:
            run = self._run_row(session, run_id)
            plans = {
                StageName(row.stage): row
                for row in session.scalars(
                    select(StagePlanRow).where(StagePlanRow.run_id == run_id)
                ).all()
            }
            sealed_plan_ids = set(
                session.scalars(
                    select(SealedStageAggregateRow.stage_plan_id).where(
                        SealedStageAggregateRow.run_id == run_id
                    )
                ).all()
            )
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.run_id == run_id)
                .order_by(GenerationWorkUnitRow.stage, GenerationWorkUnitRow.sequence)
            ).all()
            attempts = session.scalars(
                select(GenerationAttemptRow)
                .where(GenerationAttemptRow.run_id == run_id)
                .order_by(GenerationAttemptRow.work_unit_id, GenerationAttemptRow.attempt_number.desc())
            ).all()
            latest_by_unit: dict[str, GenerationAttemptRow] = {}
            for attempt in attempts:
                if attempt.work_unit_id is not None and attempt.work_unit_id not in latest_by_unit:
                    latest_by_unit[attempt.work_unit_id] = attempt
            response_usage_by_attempt: dict[str, tuple[int | None, int | None]] = {}
            response_rows = session.scalars(
                select(ArtifactRow).where(
                    ArtifactRow.run_id == run_id,
                    ArtifactRow.kind == ArtifactKind.RESPONSE.value,
                    ArtifactRow.attempt_id.is_not(None),
                )
            ).all()
            for response in response_rows:
                if not isinstance(response.content, dict) or response.attempt_id is None:
                    continue
                usage = response.content.get("usage")
                if not isinstance(usage, dict):
                    continue
                input_tokens = usage.get("inputTokens")
                output_tokens = usage.get("outputTokens")
                response_usage_by_attempt[response.attempt_id] = (
                    input_tokens if isinstance(input_tokens, int) and input_tokens >= 0 else None,
                    output_tokens if isinstance(output_tokens, int) and output_tokens >= 0 else None,
                )
            eligibility_by_unit = {
                item.work_unit_id: item
                for item in (
                    [
                        self._work_unit_repair_eligibility_in_session(session, source=run, unit=unit)
                        for unit in units
                    ]
                    if RunStatus(run.status) == RunStatus.QUARANTINED
                    else []
                )
            }
            max_attempts = self._run_max_attempts(run)
            progress_units: list[RunProgressUnit] = []
            for unit in units:
                attempt = latest_by_unit.get(unit.id)
                latest: RunProgressAttempt | None = None
                if attempt is not None:
                    duration_ms: int | None = None
                    if attempt.finished_at is not None:
                        duration_ms = max(
                            0,
                            int((attempt.finished_at - attempt.started_at).total_seconds() * 1000),
                        )
                    input_tokens, output_tokens = response_usage_by_attempt.get(
                        attempt.id, (None, None)
                    )
                    latest = RunProgressAttempt(
                        attempt_id=attempt.id,
                        attempt_number=attempt.attempt_number,
                        attempt_kind=GenerationAttemptKind(attempt.attempt_kind),
                        source_attempt_id=attempt.source_attempt_id,
                        status=AttemptStatus(attempt.status),
                        outcome_code=attempt.outcome_code,
                        outcome_unknown=attempt.outcome_unknown,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        duration_ms=duration_ms,
                        started_at=_stored_utc(attempt.started_at),
                        finished_at=(
                            _stored_utc(attempt.finished_at) if attempt.finished_at is not None else None
                        ),
                    )
                eligibility = eligibility_by_unit.get(unit.id)
                progress_units.append(
                    RunProgressUnit(
                        work_unit_id=unit.id,
                        stage=StageName(unit.stage),
                        sequence=unit.sequence,
                        status=WorkUnitStatus(unit.status),
                        max_attempts=max_attempts,
                        latest_attempt=latest,
                        sealed=unit.stage_plan_id in sealed_plan_ids,
                        repair_eligible=eligibility.eligible if eligibility is not None else False,
                        repair_reason_code=eligibility.reason_code if eligibility is not None else None,
                    )
                )
            stage_progress: list[RunProgressStage] = []
            for stage_name in [StageName(value) for value in run.requested_stages]:
                plan = plans.get(stage_name)
                stage_units = [unit for unit in progress_units if unit.stage == stage_name]
                stage_progress.append(
                    RunProgressStage(
                        stage=stage_name,
                        stage_plan_id=plan.id if plan is not None else None,
                        stage_plan_hash=plan.stage_plan_hash if plan is not None else None,
                        sealed=plan.id in sealed_plan_ids if plan is not None else False,
                        unit_count=len(stage_units),
                        completed_unit_count=sum(
                            unit.status == WorkUnitStatus.SUCCEEDED for unit in stage_units
                        ),
                        quarantined_unit_count=sum(
                            unit.status == WorkUnitStatus.QUARANTINED for unit in stage_units
                        ),
                        repair_eligible_unit_ids=[
                            unit.work_unit_id for unit in stage_units if unit.repair_eligible
                        ],
                    )
                )
            status = RunStatus(run.status)
            has_repair = any(unit.repair_eligible for unit in progress_units)
            project_is_active = (
                ProjectLifecycleStatus(self._project_row(session, run.project_id).lifecycle_status)
                == ProjectLifecycleStatus.ACTIVE
            )
            return RunProgress(
                run_id=run.id,
                status=status,
                failure_code=run.failure_code,
                failed_stage=StageName(run.failed_stage) if run.failed_stage else None,
                stage_progress=stage_progress,
                work_units=progress_units,
                actions=RunProgressActions(
                    can_resume=project_is_active and status in {RunStatus.QUEUED, RunStatus.RUNNING},
                    can_cancel=status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.CANCEL_REQUESTED},
                    can_rebuild_stage=project_is_active and status == RunStatus.QUARANTINED,
                    repair_eligible=has_repair,
                ),
            )

    @staticmethod
    def _fragment_from_artifact(stage: StageName, artifact: ArtifactRow) -> Any:
        fragment_type = {
            StageName.STORY_BIBLE: StoryBibleFragment,
            StageName.STORY_GRAPH: StoryGraphFragment,
            StageName.SCENE_BEATS: SceneBeatsFragment,
            StageName.STORYBOARD: StoryboardFragment,
        }[stage]
        return fragment_type.model_validate(artifact.content)

    def _required_unit_evidence_in_session(
        self,
        session: Session,
        *,
        run_id: str,
        stage: StageName,
        unit: GenerationWorkUnitRow,
        candidate_id: str,
    ) -> tuple[ArtifactRow, GenerationAttemptRow, list[ArtifactRow]]:
        candidate = session.get(ArtifactRow, candidate_id)
        if candidate is None:
            raise NotFoundError(f"candidate artifact not found: {candidate_id}")
        if (
            candidate.run_id != run_id
            or candidate.stage != stage.value
            or candidate.kind != ArtifactKind.CANDIDATE.value
            or candidate.work_unit_id != unit.id
            or candidate.attempt_id is None
        ):
            raise InvalidTransitionError("candidate artifact does not belong to the declared run/stage/work unit")
        if candidate.content_hash != stable_hash(candidate.content):
            raise InvalidTransitionError("candidate artifact content hash does not match immutable content")
        attempt = session.get(GenerationAttemptRow, candidate.attempt_id)
        if (
            attempt is None
            or attempt.run_id != run_id
            or attempt.stage != stage.value
            or attempt.work_unit_id != unit.id
            or AttemptStatus(attempt.status) != AttemptStatus.SUCCEEDED
            or attempt.outcome_unknown
        ):
            raise InvalidTransitionError(
                "candidate artifact must be produced by a succeeded, known-outcome work-unit attempt"
            )
        evidence = session.scalars(
            select(ArtifactRow)
            .where(ArtifactRow.attempt_id == attempt.id)
            .order_by(ArtifactRow.created_at, ArtifactRow.id)
        ).all()
        required = {
            ArtifactKind.PROMPT.value,
            ArtifactKind.RESPONSE.value,
            ArtifactKind.VALIDATION.value,
            ArtifactKind.CANDIDATE.value,
        }
        evidence_by_kind: dict[str, list[ArtifactRow]] = {}
        for row in evidence:
            evidence_by_kind.setdefault(row.kind, []).append(row)
        if set(evidence_by_kind) != required or any(
            len(rows) != 1 for rows in evidence_by_kind.values()
        ):
            raise InvalidTransitionError(
                "sealed work-unit producer attempts require exactly one prompt, response, validation, and candidate artifact"
            )
        if evidence_by_kind[ArtifactKind.CANDIDATE.value][0].id != candidate.id:
            raise InvalidTransitionError("candidate artifact must be the producer attempt's unique candidate")
        if attempt.response_persisted_at is None:
            raise InvalidTransitionError(
                "sealed candidates require a durable provider response marker"
            )
        if any(
            row.run_id != run_id
            or row.stage != stage.value
            or row.work_unit_id != unit.id
            or row.content_hash != stable_hash(row.content)
            for row in evidence
        ):
            raise InvalidTransitionError("attempt evidence fails run/stage/work-unit ownership or content-hash checks")
        validation = evidence_by_kind[ArtifactKind.VALIDATION.value][0]
        if not isinstance(validation.content, dict) or validation.content.get("accepted") is not True:
            raise InvalidTransitionError(
                "sealed work-unit candidates require an object validation artifact with accepted: true"
            )
        return candidate, attempt, evidence

    def seal_stage_aggregate(
        self,
        run_id: str,
        stage: StageName,
        *,
        candidate_artifact_ids: list[str],
    ) -> SealedStageAggregateTrace:
        """Seal exactly one ordered fragment per StagePlan unit.

        This repository command owns the aggregate boundary: callers may name
        candidate artifact IDs but cannot provide an arbitrary aggregate JSON
        document, omit evidence, or install a partial stage.
        """

        with self._write() as session:
            run = self._run_row(session, run_id)
            if run.legacy_unsealed:
                raise InvalidTransitionError("legacy/unsealed runs cannot seal stage aggregates")
            if RunStatus(run.status) != RunStatus.RUNNING:
                raise InvalidTransitionError(
                    f"cannot seal a stage aggregate while run is {run.status}"
                )
            plan_row = self._stage_plan_row(session, run_id, stage)
            if plan_row is None:
                raise InvalidTransitionError(f"cannot seal {stage.value} without a StagePlan")
            stage_plan = StagePlan.model_validate(plan_row.plan)
            existing = session.scalar(
                select(SealedStageAggregateRow).where(
                    SealedStageAggregateRow.stage_plan_id == plan_row.id
                )
            )
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.stage_plan_id == plan_row.id)
                .order_by(GenerationWorkUnitRow.sequence)
            ).all()
            if [unit.id for unit in units] != [unit.unit_id for unit in stage_plan.work_units]:
                raise InvalidTransitionError("persisted work units do not match the immutable StagePlan")
            if len(candidate_artifact_ids) != len(units) or len(set(candidate_artifact_ids)) != len(units):
                raise InvalidTransitionError("seal requires exactly one distinct candidate artifact per work unit")

            fragments: list[Any] = []
            manifest_units: list[dict[str, Any]] = []
            for unit, candidate_id in zip(units, candidate_artifact_ids, strict=True):
                candidate, attempt, evidence = self._required_unit_evidence_in_session(
                    session,
                    run_id=run_id,
                    stage=stage,
                    unit=unit,
                    candidate_id=candidate_id,
                )
                fragment = self._fragment_from_artifact(stage, candidate)
                if (
                    fragment.work_unit_id != unit.id
                    or fragment.stage_plan_hash != stage_plan.stage_plan_hash
                ):
                    raise InvalidTransitionError("candidate fragment is not bound to this immutable StagePlan unit")
                fragments.append(fragment)
                manifest_units.append(
                    {
                        "workUnitId": unit.id,
                        "attemptId": attempt.id,
                        "candidateArtifactId": candidate.id,
                        "candidateContentHash": candidate.content_hash,
                        "evidence": [
                            {"artifactId": row.id, "kind": row.kind, "contentHash": row.content_hash}
                            for row in evidence
                        ],
                    }
                )

            dependencies = self._expected_stage_dependencies_in_session(session, run, stage)
            snapshot = CanonicalSnapshot.model_validate(run.canonical_snapshot)
            # Storyboard consumes only its own frozen timing provenance.
            # Reading it while sealing an upstream Story Bible/Graph would
            # incorrectly require a future StagePlan that cannot exist yet.
            dialogue_timing_profile = (
                self._frozen_dialogue_timing_profile_from_stage_plan(stage_plan)
                if stage == StageName.STORYBOARD
                else None
            )
            payload = aggregate_stage_fragments(
                stage_plan,
                fragments,
                brief=snapshot.brief,
                bible=dependencies.get(StageName.STORY_BIBLE),  # type: ignore[arg-type]
                graph=dependencies.get(StageName.STORY_GRAPH),  # type: ignore[arg-type]
                scene_beats=dependencies.get(StageName.SCENE_BEATS),  # type: ignore[arg-type]
                dialogue_timing_profile=dialogue_timing_profile,
            )
            payload_data = payload.model_dump(mode="json", by_alias=False)
            manifest = {
                "stagePlanHash": stage_plan.stage_plan_hash,
                "generationPlanHash": stage_plan.generation_plan_hash,
                "dependencyHash": stage_plan.dependency_hash,
                "units": manifest_units,
                "aggregatePayloadHash": stable_hash(payload_data),
            }
            manifest_hash = stable_hash(manifest)
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise InvalidTransitionError("sealed stage aggregates are immutable")
                return self._sealed_aggregate_trace(existing)
            aggregate = SealedStageAggregateRow(
                id=new_id(),
                run_id=run_id,
                stage_plan_id=plan_row.id,
                stage=stage.value,
                manifest_hash=manifest_hash,
                manifest=manifest,
                payload=payload_data,
                schema_version=CURRENT_STAGE_SCHEMA_VERSION,
                created_at=utc_now(),
            )
            session.add(aggregate)
            for unit in units:
                unit.status = WorkUnitStatus.SUCCEEDED.value
            return self._sealed_aggregate_trace(aggregate)

    def _required_repair_unit_evidence_in_session(
        self,
        session: Session,
        *,
        child_run_id: str,
        scope: WorkUnitRepairScope,
        stage: StageName,
        unit: GenerationWorkUnitRow,
        candidate_id: str,
    ) -> tuple[ArtifactRow, str, list[ArtifactRow], FragmentReuseBinding | None]:
        candidate = session.get(ArtifactRow, candidate_id)
        if candidate is None:
            raise NotFoundError(f"candidate artifact not found: {candidate_id}")
        if candidate.source_artifact_id is None:
            normal_candidate, attempt, evidence = self._required_unit_evidence_in_session(
                session,
                run_id=child_run_id,
                stage=stage,
                unit=unit,
                candidate_id=candidate_id,
            )
            return normal_candidate, attempt.id, evidence, None
        if (
            candidate.run_id != child_run_id
            or candidate.stage != stage.value
            or candidate.kind != ArtifactKind.CANDIDATE.value
            or candidate.work_unit_id != unit.id
            or candidate.attempt_id is not None
            or candidate.content_hash != stable_hash(candidate.content)
        ):
            raise InvalidTransitionError("reused candidate does not belong to the declared child run/stage/work unit")
        binding_row = session.scalar(
            select(FragmentReuseBindingRow).where(
                FragmentReuseBindingRow.child_run_id == child_run_id,
                FragmentReuseBindingRow.child_work_unit_id == unit.id,
            )
        )
        if binding_row is None:
            raise RepairEligibilityError("repair.scope_hash_mismatch", "reused candidate has no exact child binding")
        binding = self._fragment_reuse_binding(binding_row)
        if binding.stage != stage or binding.source_candidate_artifact_id != candidate.source_artifact_id:
            raise RepairEligibilityError("repair.scope_hash_mismatch", "reused candidate does not match its binding")
        frozen = next(
            (
                item
                for item in scope.reuse_sources
                if item.source_candidate_artifact_id == binding.source_candidate_artifact_id
                and item.source_work_unit_id == binding.source_work_unit_id
            ),
            None,
        )
        if frozen is None:
            raise RepairEligibilityError("repair.scope_hash_mismatch", "binding is absent from immutable repair scope")
        _, source_candidate, source_attempt, evidence = self._validate_frozen_reuse_source_in_session(
            session, scope=scope, frozen=frozen
        )
        if source_candidate.id != candidate.source_artifact_id:
            raise RepairEligibilityError("repair.parent_evidence_invalid", "reused source candidate identity changed")
        return candidate, source_attempt.id, evidence, binding

    def seal_repair_stage_aggregate(
        self,
        child_run_id: str,
        stage: StageName,
        *,
        candidate_artifact_ids: list[str],
    ) -> SealedStageAggregateTrace:
        """Seal a child stage with verified child evidence and explicit reuses.

        This is intentionally separate from :meth:`seal_stage_aggregate`.
        The normal method still requires every candidate to be produced by a
        succeeded attempt in that same run and work unit.
        """

        with self._write() as session:
            child = self._run_row(session, child_run_id)
            scope = self._validate_repair_scope_in_session(
                session, child, require_source_current=True
            )
            if RunStatus(child.status) != RunStatus.RUNNING:
                raise InvalidTransitionError(
                    f"cannot seal a repair stage aggregate while run is {child.status}"
                )
            plan_row = self._stage_plan_row(session, child_run_id, stage)
            if plan_row is None:
                raise InvalidTransitionError(f"cannot seal {stage.value} without a child StagePlan")
            stage_plan = StagePlan.model_validate(plan_row.plan)
            existing = session.scalar(
                select(SealedStageAggregateRow).where(
                    SealedStageAggregateRow.stage_plan_id == plan_row.id
                )
            )
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.stage_plan_id == plan_row.id)
                .order_by(GenerationWorkUnitRow.sequence)
            ).all()
            if [unit.id for unit in units] != [unit.unit_id for unit in stage_plan.work_units]:
                raise InvalidTransitionError("persisted child work units do not match the immutable StagePlan")
            if len(candidate_artifact_ids) != len(units) or len(set(candidate_artifact_ids)) != len(units):
                raise InvalidTransitionError("repair seal requires one distinct candidate per child work unit")

            bindings = session.scalars(
                select(FragmentReuseBindingRow).where(
                    FragmentReuseBindingRow.child_run_id == child_run_id,
                    FragmentReuseBindingRow.child_stage_plan_id == plan_row.id,
                )
            ).all()
            binding_units = {row.child_work_unit_id for row in bindings}
            expected_reuse = {
                stable_hash(item.source_selector)
                for item in scope.reuse_sources
                if item.stage == stage
            }
            actual_reuse = {
                stable_hash(unit.selector)
                for unit in units
                if unit.id in binding_units
            }
            if actual_reuse != expected_reuse:
                raise RepairEligibilityError(
                    "repair.scope_hash_mismatch", "child StagePlan has not bound every frozen reusable source"
                )

            fragments: list[Any] = []
            manifest_units: list[dict[str, Any]] = []
            for unit, candidate_id in zip(units, candidate_artifact_ids, strict=True):
                candidate, attempt_id, evidence, binding = self._required_repair_unit_evidence_in_session(
                    session,
                    child_run_id=child_run_id,
                    scope=scope,
                    stage=stage,
                    unit=unit,
                    candidate_id=candidate_id,
                )
                fragment = self._fragment_from_artifact(stage, candidate)
                if fragment.work_unit_id != unit.id or fragment.stage_plan_hash != stage_plan.stage_plan_hash:
                    raise InvalidTransitionError("repair candidate fragment is not bound to this child StagePlan unit")
                fragments.append(fragment)
                unit_manifest: dict[str, Any] = {
                    "workUnitId": unit.id,
                    "attemptId": attempt_id,
                    "candidateArtifactId": candidate.id,
                    "candidateContentHash": candidate.content_hash,
                    "evidence": [
                        {"artifactId": row.id, "kind": row.kind, "contentHash": row.content_hash}
                        for row in evidence
                    ],
                }
                if binding is not None:
                    unit_manifest["reuseBindingId"] = binding.id
                    unit_manifest["reuseBindingHash"] = binding.binding_hash
                    unit_manifest["sourceRunId"] = binding.source_run_id
                    unit_manifest["sourceCandidateArtifactId"] = binding.source_candidate_artifact_id
                manifest_units.append(unit_manifest)

            dependencies = self._repair_stage_dependencies_in_session(session, child, stage)
            snapshot = CanonicalSnapshot.model_validate(child.canonical_snapshot)
            dialogue_timing_profile = (
                self._frozen_dialogue_timing_profile_from_stage_plan(stage_plan)
                if stage == StageName.STORYBOARD
                else None
            )
            payload = aggregate_stage_fragments(
                stage_plan,
                fragments,
                brief=snapshot.brief,
                bible=dependencies.get(StageName.STORY_BIBLE),  # type: ignore[arg-type]
                graph=dependencies.get(StageName.STORY_GRAPH),  # type: ignore[arg-type]
                scene_beats=dependencies.get(StageName.SCENE_BEATS),  # type: ignore[arg-type]
                dialogue_timing_profile=dialogue_timing_profile,
            )
            payload_data = payload.model_dump(mode="json", by_alias=False)
            manifest = {
                "stagePlanHash": stage_plan.stage_plan_hash,
                "generationPlanHash": stage_plan.generation_plan_hash,
                "dependencyHash": stage_plan.dependency_hash,
                "units": manifest_units,
                "aggregatePayloadHash": stable_hash(payload_data),
            }
            manifest_hash = stable_hash(manifest)
            if existing is not None:
                if existing.manifest_hash != manifest_hash:
                    raise InvalidTransitionError("sealed repair stage aggregates are immutable")
                return self._sealed_aggregate_trace(existing)
            aggregate = SealedStageAggregateRow(
                id=new_id(),
                run_id=child_run_id,
                stage_plan_id=plan_row.id,
                stage=stage.value,
                manifest_hash=manifest_hash,
                manifest=manifest,
                payload=payload_data,
                schema_version=CURRENT_STAGE_SCHEMA_VERSION,
                created_at=utc_now(),
            )
            session.add(aggregate)
            for unit in units:
                unit.status = WorkUnitStatus.SUCCEEDED.value
            return self._sealed_aggregate_trace(aggregate)

    def list_project_runs(self, project_id: str, *, limit: int = 50) -> list[GenerationRun]:
        if not 1 <= limit <= 200:
            raise ValueError("run list limit must be between 1 and 200")
        with self._read() as session:
            self._project_row(session, project_id)
            rows = session.scalars(
                select(GenerationRunRow)
                .where(GenerationRunRow.project_id == project_id)
                .order_by(GenerationRunRow.created_at.desc())
                .limit(limit)
            ).all()
            return [self._run(row) for row in rows]

    def reconcile_startup_jobs(self) -> StartupRecoveryPlan:
        """Reconcile jobs left nonterminal by the previous local process.

        Legacy runs remain conservative.  New work-unit runs are resumed only
        when no provider boundary was crossed (or every requested stage is
        already sealed and only the atomic commit remains).  A dispatch marker
        without a durable response is an ambiguous provider outcome and is
        never resubmitted.
        """

        interrupted_run_error = (
            "Generation run was interrupted by a process restart and was not "
            "retried automatically"
        )
        legacy_media_error = (
            "production_pipeline_not_ready: legacy media tasks have no immutable "
            "ProductionSnapshot and cannot be resumed after restart"
        )
        obsolete_scene_timing_error = (
            "This run uses an obsolete Scene Beats timing contract and cannot be "
            "resumed safely. Submit a new run to regenerate Scene Beats under "
            "the current trusted timing and dialogue-capacity contract."
        )
        obsolete_join_state_error = (
            "This run uses an obsolete Scene Beats join-state contract and cannot "
            "be resumed safely. Submit a new run to regenerate Scene Beats under "
            "the current trusted join-entry value contract."
        )
        obsolete_generation_planning_error = (
            "This run uses an obsolete generation planning policy and cannot be "
            "resumed safely. Submit a new run under the current executable "
            "planning contract."
        )
        obsolete_storyboard_timing_provenance_error = (
            "This run has no valid frozen Storyboard dialogue timing profile and cannot "
            "be resumed safely. Submit a new Storyboard run under the current "
            "provenance contract."
        )
        now = utc_now()
        resubmit_run_ids: list[str] = []
        resubmit_media_task_ids: list[str] = []
        resume_media_poll_task_ids: list[str] = []
        terminated_run_ids: list[str] = []
        terminated_media_task_ids: list[str] = []

        with self._write() as session:
            run_rows = session.scalars(
                select(GenerationRunRow)
                .where(
                    GenerationRunRow.status.in_(
                        [
                            RunStatus.QUEUED.value,
                            RunStatus.RUNNING.value,
                            RunStatus.CANCEL_REQUESTED.value,
                        ]
                    )
                )
                .order_by(GenerationRunRow.created_at)
            ).all()
            for row in run_rows:
                attempts = session.scalars(
                    select(GenerationAttemptRow).where(
                        GenerationAttemptRow.run_id == row.id
                    )
                ).all()
                units = session.scalars(
                    select(GenerationWorkUnitRow).where(
                        GenerationWorkUnitRow.run_id == row.id
                    )
                ).all()
                running_attempts = [
                    attempt
                    for attempt in attempts
                    if AttemptStatus(attempt.status) == AttemptStatus.RUNNING
                ]
                status = RunStatus(row.status)
                # Existing attempt-only execution has no work-unit lifecycle,
                # even if it was created after the migration for compatibility.
                # Preserve the old no-replay policy for that shape.
                legacy_execution = row.legacy_unsealed or any(
                    attempt.work_unit_id is None for attempt in attempts
                )
                if status == RunStatus.CANCEL_REQUESTED:
                    row.status = RunStatus.CANCELLED.value
                    row.error = None
                    row.failure_code = None
                    row.failed_stage = None
                    row.finished_at = now
                    self._cancel_run_work_units_in_session(
                        session,
                        row.id,
                        now=now,
                        attempt_error="Generation attempt cancelled during startup recovery",
                    )
                    terminated_run_ids.append(row.id)
                    continue

                obsolete_contract_code = (
                    self._obsolete_generation_planning_policy_recovery_code_in_session(
                        session, row
                    )
                    if not legacy_execution
                    else None
                )
                if obsolete_contract_code is not None:
                    # A plan created before its complete executable contract
                    # was frozen has different dependency, unit, prompt, or
                    # binder rules. Replanning it would rewrite immutable
                    # historical evidence; replaying it would silently execute
                    # a different request. Terminalize only nonterminal state.
                    error = (
                        obsolete_scene_timing_error
                        if obsolete_contract_code
                        == "recovery.scene_timing_contract_obsolete"
                        else (
                            obsolete_join_state_error
                            if obsolete_contract_code
                            == "recovery.join_state_value_contract_obsolete"
                            else (
                                obsolete_storyboard_timing_provenance_error
                                if obsolete_contract_code
                                == "recovery.storyboard_timing_provenance_missing"
                                else obsolete_generation_planning_error
                            )
                        )
                    )
                    row.status = RunStatus.FAILED.value
                    row.error = error
                    row.failure_code = obsolete_contract_code
                    row.failed_stage = self._recovery_obsolete_contract_stage(
                        session, row, obsolete_contract_code
                    ).value
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    for attempt in running_attempts:
                        attempt.status = AttemptStatus.FAILED.value
                        attempt.error = error
                        attempt.outcome_code = row.failure_code
                        attempt.finished_at = now
                    for unit in units:
                        if WorkUnitStatus(unit.status) in {
                            WorkUnitStatus.QUEUED,
                            WorkUnitStatus.RUNNING,
                        }:
                            unit.status = WorkUnitStatus.FAILED.value
                    terminated_run_ids.append(row.id)
                    continue

                pristine_queue = (
                    status == RunStatus.QUEUED
                    and row.started_at is None
                    and not row.result_revision_ids
                    and not attempts
                )
                if pristine_queue and not legacy_execution:
                    row.failure_code = None
                    row.failed_stage = None
                    resubmit_run_ids.append(row.id)
                    continue

                if legacy_execution:
                    row.status = RunStatus.FAILED.value
                    row.error = interrupted_run_error
                    row.failure_code = "recovery.legacy_interrupted"
                    row.failed_stage = min(
                        (attempt.stage for attempt in attempts),
                        key=lambda stage: STAGE_ORDER.index(StageName(stage)),
                        default=None,
                    )
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    for attempt in running_attempts:
                        attempt.status = AttemptStatus.FAILED.value
                        attempt.error = interrupted_run_error
                        attempt.outcome_code = "recovery.legacy_interrupted"
                        attempt.finished_at = now
                    terminated_run_ids.append(row.id)
                    continue

                if self._all_requested_stage_aggregates_are_sealed_in_session(session, row):
                    # The runner will see the complete immutable seals and run
                    # only commit_sealed_run; no provider request is eligible.
                    row.status = RunStatus.QUEUED.value
                    row.started_at = None
                    row.finished_at = None
                    row.error = None
                    row.failure_code = None
                    row.failed_stage = None
                    resubmit_run_ids.append(row.id)
                    continue

                dispatched_without_response = [
                    attempt
                    for attempt in running_attempts
                    if attempt.dispatched_at is not None and attempt.response_persisted_at is None
                ]
                if dispatched_without_response:
                    for attempt in dispatched_without_response:
                        attempt.status = AttemptStatus.FAILED.value
                        attempt.error = (
                            "Provider dispatch completed before startup recovery but no durable response "
                            "was recorded; outcome is unknown and replay is forbidden"
                        )
                        attempt.outcome_unknown = True
                        attempt.outcome_code = "provider.outcome_unknown"
                        attempt.finished_at = now
                        unit = session.get(GenerationWorkUnitRow, attempt.work_unit_id)
                        if unit is not None:
                            unit.status = WorkUnitStatus.OUTCOME_UNKNOWN.value
                    row.status = RunStatus.FAILED.value
                    row.error = (
                        "Generation run has a provider dispatch without a durable response; "
                        "its outcome is unknown and automatic replay is forbidden"
                    )
                    row.failure_code = "provider.outcome_unknown"
                    row.failed_stage = min(
                        (attempt.stage for attempt in dispatched_without_response),
                        key=lambda stage: STAGE_ORDER.index(StageName(stage)),
                    )
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    terminated_run_ids.append(row.id)
                    continue

                nonrecoverable_units = [
                    unit
                    for unit in units
                    if WorkUnitStatus(unit.status)
                    in {
                        WorkUnitStatus.FAILED,
                        WorkUnitStatus.QUARANTINED,
                        WorkUnitStatus.OUTCOME_UNKNOWN,
                        WorkUnitStatus.CANCELLED,
                    }
                ]
                if nonrecoverable_units:
                    statuses = {
                        WorkUnitStatus(unit.status) for unit in nonrecoverable_units
                    }
                    terminal_unit_ids = {unit.id for unit in nonrecoverable_units}
                    failed_attempts = [
                        attempt
                        for attempt in session.scalars(
                            select(GenerationAttemptRow).where(
                                GenerationAttemptRow.run_id == row.id,
                                GenerationAttemptRow.status
                                == AttemptStatus.FAILED.value,
                                GenerationAttemptRow.outcome_code.is_not(None),
                            )
                        ).all()
                        if attempt.work_unit_id in terminal_unit_ids
                    ]
                    latest = max(
                        failed_attempts,
                        key=lambda attempt: (
                            attempt.attempt_number,
                            attempt.finished_at or attempt.started_at,
                        ),
                        default=None,
                    )
                    only_quarantined = statuses == {WorkUnitStatus.QUARANTINED}
                    row.status = (
                        RunStatus.QUARANTINED.value
                        if only_quarantined
                        else RunStatus.FAILED.value
                    )
                    row.error = (
                        "Generation run contains a durably rejected model response"
                        if only_quarantined
                        else "Generation run has terminal work-unit evidence that cannot be replayed automatically"
                    )
                    if WorkUnitStatus.OUTCOME_UNKNOWN in statuses:
                        row.failure_code = "provider.outcome_unknown"
                    elif only_quarantined:
                        row.failure_code = (
                            latest.outcome_code
                            if latest is not None
                            else "recovery.quarantined_work_unit"
                        )
                    elif WorkUnitStatus.FAILED in statuses and latest is not None:
                        row.failure_code = latest.outcome_code
                    else:
                        row.failure_code = "recovery.nonrecoverable_work_unit"
                    row.failed_stage = min(
                        (unit.stage for unit in nonrecoverable_units),
                        key=lambda stage: STAGE_ORDER.index(StageName(stage)),
                    )
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    terminated_run_ids.append(row.id)
                    continue

                # Keep safe in-flight identities intact. A pre-dispatch
                # attempt may continue to the provider boundary; an attempt
                # with a durable response may continue local parsing,
                # validation, and sealing. Neither path spends another
                # correction slot or replays a provider call.
                running_unit_ids = {
                    attempt.work_unit_id for attempt in running_attempts
                }
                orphan_running_units = [
                    unit
                    for unit in units
                    if WorkUnitStatus(unit.status) == WorkUnitStatus.RUNNING
                    and unit.id not in running_unit_ids
                ]
                if orphan_running_units:
                    row.status = RunStatus.FAILED.value
                    row.error = (
                        "Generation run has a running work unit without an active attempt; "
                        "automatic recovery cannot prove a safe continuation"
                    )
                    row.failure_code = "recovery.orphan_running_work_unit"
                    row.failed_stage = min(
                        (unit.stage for unit in orphan_running_units),
                        key=lambda stage: STAGE_ORDER.index(StageName(stage)),
                    )
                    row.started_at = row.started_at or now
                    row.finished_at = now
                    for unit in orphan_running_units:
                        unit.status = WorkUnitStatus.FAILED.value
                    terminated_run_ids.append(row.id)
                    continue
                row.status = RunStatus.QUEUED.value
                row.started_at = None
                row.finished_at = None
                row.error = None
                row.failure_code = None
                row.failed_stage = None
                resubmit_run_ids.append(row.id)

            media_rows = session.scalars(
                select(MediaTaskRow)
                .where(
                    MediaTaskRow.status.in_(
                        [MediaTaskStatus.QUEUED.value, MediaTaskStatus.RUNNING.value]
                    )
                )
                .order_by(MediaTaskRow.created_at)
            ).all()
            for row in media_rows:
                # M1-12A introduces Approval/ProductionSnapshot as the only
                # valid media boundary.  Every existing task predates that
                # immutable input contract, including a queued task that never
                # reached a provider.  Preserve terminal history untouched,
                # but never resume or poll these nonterminal legacy rows.
                row.status = MediaTaskStatus.FAILED.value
                row.started_at = row.started_at or now
                row.finished_at = now
                row.updated_at = now
                row.output_uri = None
                row.error = legacy_media_error
                terminated_media_task_ids.append(row.id)

        return StartupRecoveryPlan(
            resubmit_run_ids=resubmit_run_ids,
            resubmit_media_task_ids=resubmit_media_task_ids,
            resume_media_poll_task_ids=resume_media_poll_task_ids,
            terminated_run_ids=terminated_run_ids,
            terminated_media_task_ids=terminated_media_task_ids,
        )

    def start_run(self, run_id: str) -> GenerationRun:
        with self._write() as session:
            row = self._run_row(session, run_id)
            status = RunStatus(row.status)
            if status == RunStatus.CANCEL_REQUESTED:
                row.status = RunStatus.CANCELLED.value
                row.finished_at = utc_now()
                return self._run(row)
            if status != RunStatus.QUEUED:
                raise InvalidTransitionError(f"cannot start run from {status.value}")
            row.status = RunStatus.RUNNING.value
            row.started_at = utc_now()
            return self._run(row)

    def install_generated_stage(
        self,
        run_id: str,
        stage: StageName,
        payload: StagePayload | dict[str, Any],
    ) -> StageHead:
        _, heads = self._commit_run_outputs(run_id, {stage: payload})
        return heads[0]

    def install_generated_stages(
        self,
        run_id: str,
        payloads: dict[StageName, StagePayload | dict[str, Any]],
    ) -> list[StageHead]:
        _, heads = self._commit_run_outputs(run_id, payloads)
        return heads

    def commit_run_outputs(
        self,
        run_id: str,
        payloads: dict[StageName, StagePayload | dict[str, Any]],
    ) -> GenerationRun:
        run, _ = self._commit_run_outputs(run_id, payloads)
        return run

    def commit_sealed_run(
        self,
        run_id: str,
        *,
        sealed_aggregate_ids: list[str],
    ) -> GenerationRun:
        """Atomically install a complete requested range from verified seals only.

        Unlike the legacy compatibility method ``commit_run_outputs``, this
        command accepts no caller-owned stage payload dictionary.  Each payload
        is read from its immutable exact-manifest aggregate inside the same
        transaction that performs canonical installation.
        """

        with self._lifecycle_write() as session:
            run_row = self._run_row(session, run_id)
            if run_row.legacy_unsealed:
                raise InvalidTransitionError("legacy/unsealed runs cannot commit sealed aggregates")
            requested = [StageName(value) for value in run_row.requested_stages]
            if len(sealed_aggregate_ids) != len(requested) or len(set(sealed_aggregate_ids)) != len(requested):
                raise InvalidTransitionError(
                    "commit_sealed_run requires exactly one distinct aggregate ID per requested stage"
                )
            rows = [session.get(SealedStageAggregateRow, aggregate_id) for aggregate_id in sealed_aggregate_ids]
            if any(row is None for row in rows):
                raise NotFoundError("one or more sealed stage aggregates were not found")
            aggregates = [row for row in rows if row is not None]
            if [StageName(row.stage) for row in aggregates] != requested:
                raise InvalidTransitionError(
                    "sealed aggregates must be supplied in the run's exact requested stage order"
                )
            if any(row.run_id != run_id for row in aggregates):
                raise InvalidTransitionError("sealed aggregates must belong to the declared run")
            for aggregate in aggregates:
                if aggregate.manifest_hash != stable_hash(aggregate.manifest):
                    raise InvalidTransitionError("sealed aggregate manifest hash does not match immutable content")
                if aggregate.manifest.get("aggregatePayloadHash") != stable_hash(aggregate.payload):
                    raise InvalidTransitionError("sealed aggregate payload hash does not match immutable content")
                plan = session.get(StagePlanRow, aggregate.stage_plan_id)
                if (
                    plan is None
                    or plan.run_id != run_id
                    or plan.stage != aggregate.stage
                    or aggregate.manifest.get("stagePlanHash") != plan.stage_plan_hash
                ):
                    raise InvalidTransitionError("sealed aggregate is not bound to the declared immutable StagePlan")
            dialogue_timing_profile = self._frozen_dialogue_timing_profile_for_sealed_commit_in_session(
                session,
                run_row,
            )
            payloads = {
                StageName(aggregate.stage): self._decode_current_stage_payload(
                    StageName(aggregate.stage), aggregate.payload, aggregate.schema_version
                )
                for aggregate in aggregates
            }
            run, _ = self._commit_parsed_run_outputs_in_session(
                session,
                run_row,
                payloads,
                dialogue_timing_profile=dialogue_timing_profile,
            )
            return run

    @staticmethod
    def _frozen_dialogue_timing_profile_from_stage_plan(
        stage_plan: StagePlan,
    ) -> DialogueTimingProfile:
        """Read a stage-owned timing profile without any runtime fallback."""

        if stage_plan.stage == StageName.SCENE_BEATS:
            profile = stage_plan.dialogue_timing_profile
            description = "Scene Beats"
        elif stage_plan.stage == StageName.STORYBOARD:
            profile = stage_plan.storyboard_dialogue_timing_profile
            description = "Storyboard"
        else:
            raise InvalidTransitionError(
                f"{stage_plan.stage.value} has no dialogue timing provenance"
            )
        if profile is None:
            raise InvalidTransitionError(
                f"sealed commit requires a frozen {description} dialogue timing profile"
            )
        return profile

    def _frozen_dialogue_timing_profile_for_sealed_commit_in_session(
        self,
        session: Session,
        run_row: GenerationRunRow,
    ) -> DialogueTimingProfile | None:
        """Load the timing policy that bound this run's sealed V2 output.

        Each stage owns its own immutable provenance.  In particular, a
        Storyboard-only run cannot assume that a READY Scene Beats revision
        came from this run: canonical revisions deliberately store authored
        content, not generator-policy metadata.  Reconstructing either policy
        from a process default would let a deployment change alter acceptance
        of immutable evidence, so missing or malformed frozen evidence is an
        install failure rather than a fallback opportunity.
        """

        requested = {StageName(value) for value in run_row.requested_stages}
        if not requested & {StageName.SCENE_BEATS, StageName.STORYBOARD}:
            return None
        profiles: list[DialogueTimingProfile] = []
        for stage in (StageName.SCENE_BEATS, StageName.STORYBOARD):
            if stage not in requested:
                continue
            description = "Scene Beats" if stage == StageName.SCENE_BEATS else "Storyboard"
            row = self._stage_plan_row(session, run_row.id, stage)
            if row is None:
                raise InvalidTransitionError(
                    f"sealed commit requires a frozen {description} dialogue timing profile"
                )
            try:
                plan = StagePlan.model_validate(row.plan)
            except ValueError as exc:
                raise InvalidTransitionError(
                    f"sealed commit requires a valid frozen {description} dialogue timing profile"
                ) from exc
            profiles.append(self._frozen_dialogue_timing_profile_from_stage_plan(plan))
        if len({profile.model_dump_json() for profile in profiles}) != 1:
            raise InvalidTransitionError(
                "sealed commit requires matching frozen Scene Beats and Storyboard dialogue timing profiles"
            )
        return profiles[0]

    def _commit_run_outputs(
        self,
        run_id: str,
        payloads: dict[StageName, StagePayload | dict[str, Any]],
    ) -> tuple[GenerationRun, list[StageHead]]:
        """Validate inputs, install every requested revision, and succeed atomically."""

        parsed_payloads = {
            stage: stage_payload_model(stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION).model_validate(payload)
            for stage, payload in payloads.items()
        }
        with self._lifecycle_write() as session:
            run_row = self._run_row(session, run_id)
            return self._commit_parsed_run_outputs_in_session(session, run_row, parsed_payloads)

    def _commit_parsed_run_outputs_in_session(
        self,
        session: Session,
        run_row: GenerationRunRow,
        parsed_payloads: dict[StageName, StagePayload],
        *,
        dialogue_timing_profile: DialogueTimingProfile | None = None,
    ) -> tuple[GenerationRun, list[StageHead]]:
        if RunStatus(run_row.status) != RunStatus.RUNNING:
            raise InvalidTransitionError(f"cannot install generated output while run is {run_row.status}")
        requested = [StageName(value) for value in run_row.requested_stages]
        if set(parsed_payloads) != set(requested):
            raise InvalidTransitionError(
                "commit requires exactly one candidate for every requested stage"
            )
        if run_row.result_revision_ids:
            raise InvalidTransitionError("run outputs have already been committed")
        snapshot = self._assert_run_inputs_current_in_session(session, run_row)
        project_row = self._project_row(session, run_row.project_id)
        self._assert_active_project(project_row)
        results: list[StageHead] = []
        for stage in requested:
            current_head = self._stage_row(session, run_row.project_id, stage)
            snapshot_head = snapshot.stage_heads[stage]
            if current_head.revision != snapshot_head.revision:
                raise RevisionConflictError(f"stage:{stage.value}", snapshot_head.revision, current_head.revision)
            now = utc_now()
            head, revision_row = self._install_stage_in_session(
                session,
                project_row,
                stage,
                parsed_payloads[stage],
                expected_revision=snapshot_head.revision,
                now=now,
                allow_noop=False,
                dialogue_timing_profile=dialogue_timing_profile,
            )
            if revision_row is None:
                raise InvalidTransitionError("generated stage installation must create a canonical revision")
            run_row.result_revision_ids = [*run_row.result_revision_ids, revision_row.id]
            canonical_trace = {
                "entityRevisionId": revision_row.id,
                "revision": revision_row.revision,
                "contentHash": revision_row.content_hash,
                "inputRevisions": dict(revision_row.input_revisions),
            }
            canonical_artifact = Artifact(
                run_id=run_row.id,
                stage=stage,
                kind=ArtifactKind.CANONICAL,
                content=canonical_trace,
                content_hash=stable_hash(canonical_trace),
                created_at=now,
            )
            session.add(
                ArtifactRow(
                    id=canonical_artifact.id,
                    run_id=canonical_artifact.run_id,
                    attempt_id=None,
                    work_unit_id=None,
                    source_artifact_id=None,
                    stage=stage.value,
                    kind=ArtifactKind.CANONICAL.value,
                    media_type=canonical_artifact.media_type,
                    content=canonical_trace,
                    content_hash=canonical_artifact.content_hash,
                    created_at=now,
                )
            )
            results.append(head)
        run_row.status = RunStatus.SUCCEEDED.value
        run_row.error = None
        run_row.finished_at = utc_now()
        return self._run(run_row), results

    def _run_outputs_are_current(self, session: Session, row: GenerationRunRow) -> bool:
        snapshot = CanonicalSnapshot.model_validate(row.canonical_snapshot)
        project = self._project_row(session, row.project_id)
        if project.revision != snapshot.project_revision:
            return False
        requested = {StageName(value) for value in row.requested_stages}
        result_rows = session.scalars(
            select(EntityRevisionRow).where(EntityRevisionRow.id.in_(row.result_revision_ids or [""]))
        ).all()
        result_by_stage = {StageName(result.stage): result for result in result_rows}
        if set(result_by_stage) != requested:
            return False
        required_inputs = {
            upstream
            for requested_stage in requested
            for upstream in upstream_stages(requested_stage)
            if upstream not in requested
        }
        for stage in requested:
            current = self._stage_row(session, row.project_id, stage)
            if current.entity_revision_id != result_by_stage[stage].id:
                return False
        for stage in required_inputs:
            current = self._stage_row(session, row.project_id, stage)
            if current.revision != snapshot.stage_heads[stage].revision:
                return False
        return True

    def finish_run(
        self,
        run_id: str,
        *,
        result_revision_ids: Sequence[str] | None = None,
        error: str | None = None,
        quarantine_reason: str | None = None,
        failure_code: str | None = None,
        failed_stage: StageName | None = None,
    ) -> GenerationRun:
        with self._write() as session:
            row = self._run_row(session, run_id)
            if RunStatus(row.status) in TERMINAL_RUN_STATUSES:
                return self._run(row)
            if result_revision_ids is not None:
                row.result_revision_ids = list(result_revision_ids)
            status = RunStatus(row.status)
            if status == RunStatus.CANCEL_REQUESTED:
                row.status = RunStatus.CANCELLED.value
                self._cancel_run_work_units_in_session(
                    session,
                    row.id,
                    now=utc_now(),
                    attempt_error="Generation attempt cancelled before run completion",
                )
            elif status != RunStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish run from {status.value}")
            elif error is not None:
                row.status = RunStatus.FAILED.value
                row.error = error
                row.failure_code = failure_code
                row.failed_stage = failed_stage.value if failed_stage else None
            elif quarantine_reason is not None:
                row.status = RunStatus.QUARANTINED.value
                row.error = quarantine_reason
                row.failure_code = failure_code
                row.failed_stage = failed_stage.value if failed_stage else None
            else:
                row.status = (
                    RunStatus.SUCCEEDED.value
                    if self._run_outputs_are_current(session, row)
                    else RunStatus.QUARANTINED.value
                )
                if row.status == RunStatus.QUARANTINED.value:
                    row.error = "canonical inputs changed or requested outputs were not installed"
                    row.failure_code = "commit.snapshot_changed"
                else:
                    row.error = None
                    row.failure_code = None
                    row.failed_stage = None
            row.finished_at = utc_now()
            return self._run(row)

    def cancel_run(self, run_id: str) -> GenerationRun:
        with self._write() as session:
            row = self._run_row(session, run_id)
            status = RunStatus(row.status)
            if status == RunStatus.QUEUED:
                row.status = RunStatus.CANCELLED.value
                now = utc_now()
                row.finished_at = now
                self._cancel_run_work_units_in_session(
                    session,
                    row.id,
                    now=now,
                    attempt_error="Generation attempt cancelled before dispatch",
                )
            elif status == RunStatus.RUNNING:
                if row.result_revision_ids and self._run_outputs_are_current(session, row):
                    # Canonical installation is the commit point. A cancellation that
                    # arrives after it must not label installed output as cancelled.
                    row.status = RunStatus.SUCCEEDED.value
                    row.finished_at = utc_now()
                else:
                    row.status = RunStatus.CANCEL_REQUESTED.value
            elif status == RunStatus.CANCEL_REQUESTED:
                pass
            elif status in TERMINAL_RUN_STATUSES:
                return self._run(row)
            return self._run(row)

    def create_repair_run(
        self,
        source_run_id: str,
        *,
        stage: StageName | None = None,
        instructions: str | None = None,
        provider_snapshot: dict[str, Any] | None = None,
    ) -> GenerationRun:
        source = self.get_run(source_run_id)
        if source.status != RunStatus.QUARANTINED:
            raise InvalidTransitionError("repairs may only be created from a quarantined run")
        source_trace = self.get_run_trace(source_run_id)
        if not source_trace.snapshot_is_current:
            raise InvalidTransitionError(
                "repair source inputs changed after quarantine; start a fresh rebuild from current canonical heads"
            )
        if stage is not None and stage not in source.requested_stages:
            raise InvalidTransitionError("repair stage must belong to the source run's requestedStages")
        failed_attempts = [
            attempt
            for attempt in source_trace.attempts
            if attempt.status == AttemptStatus.FAILED
        ]
        if not failed_attempts:
            raise InvalidTransitionError(
                "repair requires a failed model attempt with rejected response evidence; start a rebuild instead"
            )
        failed_attempt = failed_attempts[-1]
        if failed_attempt.work_unit_id is not None:
            raise InvalidTransitionError(
                "exact work-unit repair is not implemented; start a rebuild from the failed stage instead"
            )
        failed_stage = failed_attempt.stage
        attempt_artifacts = [
            artifact
            for artifact in source_trace.artifacts
            if artifact.attempt_id == failed_attempt.id and artifact.stage == failed_stage
        ]
        response = next(
            (artifact for artifact in attempt_artifacts if artifact.kind == ArtifactKind.RESPONSE),
            None,
        )
        validation = next(
            (artifact for artifact in attempt_artifacts if artifact.kind == ArtifactKind.VALIDATION),
            None,
        )
        rejected = (
            validation is not None
            and isinstance(validation.content, dict)
            and validation.content.get("accepted") is False
        )
        if response is None or not rejected:
            raise InvalidTransitionError(
                "repair requires the failed attempt's response and rejected validation artifacts"
            )
        if stage is not None and stage != failed_stage:
            raise InvalidTransitionError(
                f"repair stage must match the quarantined attempt stage {failed_stage.value}"
            )
        target = failed_stage
        requested = source.requested_stages
        reused_candidate_artifact_ids: dict[StageName, str] = {}
        repair_index = requested.index(target)
        for reused_stage in requested[:repair_index]:
            candidate = next(
                (
                    artifact
                    for artifact in reversed(source_trace.artifacts)
                    if artifact.stage == reused_stage and artifact.kind == ArtifactKind.CANDIDATE
                ),
                None,
            )
            if candidate is None:
                raise InvalidTransitionError(
                    f"repair source has no accepted candidate for {reused_stage.value}"
                )
            reused_candidate_artifact_ids[reused_stage] = candidate.id
        repair_source = RepairSource(
            failed_attempt_id=failed_attempt.id,
            response_artifact_id=response.id,
            validation_artifact_id=validation.id,
            reused_candidate_artifact_ids=reused_candidate_artifact_ids,
        )
        return self.create_run(
            source.project_id,
            RunKind.REPAIR,
            requested,
            instructions=instructions,
            parent_run_id=source.id,
            repair_stage=target,
            repair_source=repair_source,
            provider_snapshot=provider_snapshot,
        )

    @staticmethod
    def _scope_hash_payload(scope_data: dict[str, Any]) -> dict[str, Any]:
        """Return the exact public repair contract, excluding only its digest."""

        return {key: value for key, value in scope_data.items() if key != "scopeHash"}

    def _source_snapshot_is_current_in_session(
        self,
        session: Session,
        source: GenerationRunRow,
    ) -> bool:
        snapshot = CanonicalSnapshot.model_validate(source.canonical_snapshot)
        return self._snapshot_in_session(session, source.project_id).snapshot_hash == snapshot.snapshot_hash

    def _latest_rejected_evidence_in_session(
        self,
        session: Session,
        *,
        source: GenerationRunRow,
        unit: GenerationWorkUnitRow,
    ) -> tuple[GenerationAttemptRow, ArtifactRow, ArtifactRow] | None:
        attempts = session.scalars(
            select(GenerationAttemptRow)
            .where(GenerationAttemptRow.work_unit_id == unit.id)
            .order_by(GenerationAttemptRow.attempt_number.desc())
        ).all()
        for attempt in attempts:
            if (
                attempt.run_id != source.id
                or attempt.stage != unit.stage
                or AttemptStatus(attempt.status) != AttemptStatus.FAILED
                or attempt.outcome_unknown
                or attempt.response_persisted_at is None
                or not attempt.outcome_code
            ):
                continue
            evidence = session.scalars(
                select(ArtifactRow)
                .where(ArtifactRow.attempt_id == attempt.id)
                .order_by(ArtifactRow.created_at, ArtifactRow.id)
            ).all()
            response = next((row for row in evidence if row.kind == ArtifactKind.RESPONSE.value), None)
            validation = next((row for row in evidence if row.kind == ArtifactKind.VALIDATION.value), None)
            if (
                response is not None
                and validation is not None
                and response.run_id == source.id
                and validation.run_id == source.id
                and response.work_unit_id == unit.id
                and validation.work_unit_id == unit.id
                and isinstance(validation.content, dict)
                and validation.content.get("accepted") is False
                and response.content_hash == stable_hash(response.content)
                and validation.content_hash == stable_hash(validation.content)
            ):
                return attempt, response, validation
        return None

    def _exact_repair_parent_contract_code_in_session(
        self,
        session: Session,
        *,
        source: GenerationRunRow,
        target: GenerationWorkUnitRow,
    ) -> str | None:
        """Reject a parent that cannot be replayed under the current repair contract.

        Exact repair may rebind successful sibling fragments into child-local
        plans, but it may not treat a historical planner or a pre-join Scene
        Beats plan as if it had current provenance.  This check is deliberately
        before child creation and never reconstructs missing fields.
        """

        generation_plan_row = session.get(GenerationPlanRow, source.id)
        if generation_plan_row is None:
            return "repair.parent_plan_obsolete"
        try:
            generation_plan = GenerationPlan.model_validate(generation_plan_row.plan)
        except ValueError:
            return "repair.parent_plan_obsolete"
        if generation_plan.planning_policy_version != PLANNING_POLICY_VERSION:
            return "repair.parent_plan_obsolete"

        requested = [StageName(value) for value in source.requested_stages]
        target_stage = StageName(target.stage)
        if (
            StageName.SCENE_BEATS in requested
            and STAGE_ORDER.index(StageName.SCENE_BEATS)
            <= STAGE_ORDER.index(target_stage)
        ):
            scene_beats_plan = self._stage_plan_row(
                session, source.id, StageName.SCENE_BEATS
            )
            if scene_beats_plan is None:
                return "repair.parent_stage_plan_obsolete"
            if self._scene_beats_stage_plan_contract_code(scene_beats_plan) is not None:
                return "repair.parent_stage_plan_obsolete"
        if (
            StageName.STORYBOARD in requested
            and STAGE_ORDER.index(StageName.STORYBOARD)
            <= STAGE_ORDER.index(target_stage)
        ):
            storyboard_plan = self._stage_plan_row(
                session, source.id, StageName.STORYBOARD
            )
            if storyboard_plan is None:
                return "repair.parent_stage_plan_obsolete"
            if self._storyboard_stage_plan_contract_code(storyboard_plan) is not None:
                return "repair.parent_stage_plan_obsolete"
        return None

    def _work_unit_repair_eligibility_in_session(
        self,
        session: Session,
        *,
        source: GenerationRunRow,
        unit: GenerationWorkUnitRow,
        check_existing_scope: bool = True,
    ) -> WorkUnitRepairEligibility:
        stage = StageName(unit.stage)
        if RunStatus(source.status) != RunStatus.QUARANTINED:
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code="repair.source_not_quarantined"
            )
        if source.legacy_unsealed or session.get(GenerationPlanRow, source.id) is None:
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code="repair.source_legacy_unsealed"
            )
        if unit.run_id != source.id or stage.value not in source.requested_stages:
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code="repair.target_not_in_source_run"
            )
        parent_contract_code = self._exact_repair_parent_contract_code_in_session(
            session,
            source=source,
            target=unit,
        )
        if parent_contract_code is not None:
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id,
                stage=stage,
                eligible=False,
                reason_code=parent_contract_code,
            )
        if (
            ProjectLifecycleStatus(self._project_row(session, source.project_id).lifecycle_status)
            != ProjectLifecycleStatus.ACTIVE
        ):
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code="repair.project_archived"
            )
        if not self._source_snapshot_is_current_in_session(session, source):
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code="repair.snapshot_stale"
            )
        if self._work_unit_is_sealed_in_session(session, unit):
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code="repair.target_sealed"
            )
        if WorkUnitStatus(unit.status) == WorkUnitStatus.OUTCOME_UNKNOWN:
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code="repair.target_outcome_unknown"
            )
        if WorkUnitStatus(unit.status) != WorkUnitStatus.QUARANTINED:
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code="repair.target_not_quarantined"
            )
        if self._latest_rejected_evidence_in_session(session, source=source, unit=unit) is None:
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id,
                stage=stage,
                eligible=False,
                reason_code="repair.target_not_rejected_model_output",
            )
        if check_existing_scope and session.scalar(
            select(WorkUnitRepairScopeRow.child_run_id).where(
                WorkUnitRepairScopeRow.target_work_unit_id == unit.id
            )
        ) is not None:
            return WorkUnitRepairEligibility(
                work_unit_id=unit.id, stage=stage, eligible=False, reason_code="repair.already_exists"
            )
        return WorkUnitRepairEligibility(work_unit_id=unit.id, stage=stage, eligible=True)

    @staticmethod
    def _raise_repair_ineligible(eligibility: WorkUnitRepairEligibility) -> None:
        assert eligibility.reason_code is not None
        raise RepairEligibilityError(
            eligibility.reason_code,
            f"work unit {eligibility.work_unit_id} is not eligible for exact repair: {eligibility.reason_code}",
        )

    def get_repair_eligible_work_units(self, run_id: str) -> list[WorkUnitRepairEligibility]:
        """Return server-owned exact-repair decisions for one source run."""

        with self._read() as session:
            source = self._run_row(session, run_id)
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.run_id == run_id)
                .order_by(GenerationWorkUnitRow.stage, GenerationWorkUnitRow.sequence)
            ).all()
            return [
                self._work_unit_repair_eligibility_in_session(session, source=source, unit=unit)
                for unit in units
            ]

    def _frozen_reuse_source_in_session(
        self,
        session: Session,
        *,
        source: GenerationRunRow,
        unit: GenerationWorkUnitRow,
        kind: FragmentReuseKind,
    ) -> FrozenFragmentReuseSource:
        plan_row = session.get(StagePlanRow, unit.stage_plan_id)
        if plan_row is None or plan_row.run_id != source.id:
            raise RepairEligibilityError("repair.parent_evidence_invalid", "source work unit has no matching StagePlan")
        candidate_rows = session.scalars(
            select(ArtifactRow)
            .where(
                ArtifactRow.run_id == source.id,
                ArtifactRow.work_unit_id == unit.id,
                ArtifactRow.kind == ArtifactKind.CANDIDATE.value,
            )
            .order_by(ArtifactRow.created_at.desc())
        ).all()
        if len(candidate_rows) != 1:
            raise RepairEligibilityError(
                "repair.parent_evidence_invalid", "source reusable unit requires one immutable candidate"
            )
        candidate, attempt, evidence = self._required_unit_evidence_in_session(
            session,
            run_id=source.id,
            stage=StageName(unit.stage),
            unit=unit,
            candidate_id=candidate_rows[0].id,
        )
        evidence_by_kind = {row.kind: row for row in evidence}
        return FrozenFragmentReuseSource(
            kind=kind,
            stage=StageName(unit.stage),
            source_work_unit_id=unit.id,
            source_stage_plan_id=plan_row.id,
            source_stage_plan_hash=plan_row.stage_plan_hash,
            source_generation_plan_hash=unit.generation_plan_hash,
            source_selector=dict(unit.selector),
            source_dependency_hash=unit.dependency_hash,
            source_unit_dependency_hash=unit.unit_dependency_hash,
            source_input_hash=unit.input_hash,
            source_producer_attempt_id=attempt.id,
            source_response_artifact_id=evidence_by_kind[ArtifactKind.RESPONSE.value].id,
            source_validation_artifact_id=evidence_by_kind[ArtifactKind.VALIDATION.value].id,
            source_candidate_artifact_id=candidate.id,
            source_candidate_content_hash=candidate.content_hash,
        )

    def _frozen_reuse_sources_in_session(
        self,
        session: Session,
        *,
        source: GenerationRunRow,
        target: GenerationWorkUnitRow,
    ) -> list[FrozenFragmentReuseSource]:
        requested = [StageName(value) for value in source.requested_stages]
        target_index = requested.index(StageName(target.stage))
        reusable: list[FrozenFragmentReuseSource] = []
        for stage in requested[:target_index]:
            source_plan = self._stage_plan_row(session, source.id, stage)
            if source_plan is None or session.scalar(
                select(SealedStageAggregateRow.id).where(
                    SealedStageAggregateRow.stage_plan_id == source_plan.id
                )
            ) is None:
                raise RepairEligibilityError(
                    "repair.parent_evidence_invalid",
                    f"source upstream stage {stage.value} is not sealed",
                )
            units = session.scalars(
                select(GenerationWorkUnitRow)
                .where(GenerationWorkUnitRow.stage_plan_id == source_plan.id)
                .order_by(GenerationWorkUnitRow.sequence)
            ).all()
            reusable.extend(
                self._frozen_reuse_source_in_session(session, source=source, unit=unit, kind=FragmentReuseKind.UPSTREAM)
                for unit in units
            )
        target_plan = self._stage_plan_row(session, source.id, StageName(target.stage))
        if target_plan is None or target_plan.id != target.stage_plan_id:
            raise RepairEligibilityError("repair.parent_evidence_invalid", "target source StagePlan is inconsistent")
        siblings = session.scalars(
            select(GenerationWorkUnitRow)
            .where(GenerationWorkUnitRow.stage_plan_id == target_plan.id)
            .order_by(GenerationWorkUnitRow.sequence)
        ).all()
        reusable.extend(
            self._frozen_reuse_source_in_session(session, source=source, unit=unit, kind=FragmentReuseKind.SIBLING)
            for unit in siblings
            if unit.id != target.id
        )
        return reusable

    def create_work_unit_repair_run(
        self,
        source_run_id: str,
        work_unit_id: str,
        *,
        idempotency_key: str,
        instructions: str | None = None,
    ) -> WorkUnitRepairRunCreation:
        """Create one immutable exact-repair child without changing model contract.

        The source run's frozen provider snapshot, canonical snapshot,
        requested range, and instructions are copied verbatim.  An exact
        repair therefore cannot quietly turn into a model switch or a new
        prompt request.  Callers may only supply ``None`` for instructions;
        the parameter exists so the HTTP boundary can reject accidental UI
        additions explicitly rather than silently dropping them.
        """

        key = idempotency_key.strip()
        if not 1 <= len(key) <= 255:
            raise ValueError("idempotency key must contain between 1 and 255 characters")
        if instructions is not None:
            raise RepairEligibilityError(
                "repair.instructions_override_forbidden",
                "exact work-unit repairs inherit frozen instructions and cannot override them",
            )
        fingerprint = stable_hash(
            {"parentRunId": source_run_id, "targetWorkUnitId": work_unit_id}
        )
        with self._lifecycle_write() as session:
            prior = session.get(WorkUnitRepairIdempotencyRow, key)
            if prior is not None:
                if prior.request_fingerprint != fingerprint:
                    raise RepairEligibilityError(
                        "repair.idempotency_conflict",
                        "Idempotency-Key has already been used for a different exact repair",
                    )
                return WorkUnitRepairRunCreation(
                    run=self._run(self._run_row(session, prior.child_run_id)), created=False
                )

            source = self._run_row(session, source_run_id)
            self._assert_new_run_profile_enabled(session, source.provider_snapshot)
            target = session.get(GenerationWorkUnitRow, work_unit_id)
            if target is None:
                raise NotFoundError(f"generation work unit not found: {work_unit_id}")
            eligibility = self._work_unit_repair_eligibility_in_session(
                session, source=source, unit=target
            )
            if not eligibility.eligible:
                self._raise_repair_ineligible(eligibility)
            rejected = self._latest_rejected_evidence_in_session(
                session, source=source, unit=target
            )
            assert rejected is not None
            failed_attempt, response, validation = rejected
            source_plan_row = session.get(GenerationPlanRow, source.id)
            source_stage_plan = session.get(StagePlanRow, target.stage_plan_id)
            if source_plan_row is None or source_stage_plan is None:
                raise RepairEligibilityError("repair.parent_evidence_invalid", "source plan evidence is missing")
            parent_contract_code = self._exact_repair_parent_contract_code_in_session(
                session,
                source=source,
                target=target,
            )
            if parent_contract_code is not None:
                raise RepairEligibilityError(
                    parent_contract_code,
                    "exact repair parent no longer satisfies the current frozen planning contract",
                )
            source_plan = GenerationPlan.model_validate(source_plan_row.plan)
            project = self._project_row(session, source.project_id)
            self._assert_active_project(project)
            requested = [StageName(value) for value in source.requested_stages]
            snapshot = CanonicalSnapshot.model_validate(source.canonical_snapshot)
            child = GenerationRun(
                project_id=source.project_id,
                kind=RunKind.REPAIR,
                parent_run_id=source.id,
                repair_stage=StageName(target.stage),
                repair_source=None,
                work_unit_repair_scope_id="pending",  # replaced by child ID before persistence
                provider_snapshot=dict(source.provider_snapshot),
                requested_stages=requested,
                canonical_snapshot=snapshot,
                instructions=source.instructions,
                legacy_unsealed=False,
            )
            # The scope ID is intentionally the child run ID.  It is a stable
            # one-to-one foreign identity, not an inferred JSON convention.
            child = child.model_copy(update={"work_unit_repair_scope_id": child.id})
            session.add(
                GenerationRunRow(
                    id=child.id,
                    project_id=child.project_id,
                    kind=child.kind.value,
                    parent_run_id=child.parent_run_id,
                    repair_stage=child.repair_stage.value if child.repair_stage else None,
                    repair_source=None,
                    work_unit_repair_scope_id=child.work_unit_repair_scope_id,
                    provider_snapshot=child.provider_snapshot,
                    requested_stages=[stage.value for stage in child.requested_stages],
                    status=child.status.value,
                    canonical_snapshot=child.canonical_snapshot.model_dump(mode="json", by_alias=False),
                    instructions=child.instructions,
                    legacy_unsealed=False,
                    result_revision_ids=[],
                    error=None,
                    failure_code=None,
                    failed_stage=None,
                    created_at=child.created_at,
                    started_at=None,
                    finished_at=None,
                )
            )
            session.flush()

            # A child run intentionally has a distinct plan hash and work-unit
            # identities.  It keeps the parent profile/topology values as
            # immutable inputs while making new aggregate seals unambiguous.
            topology: StoryGraphTopology | None = None
            if StageName.STORY_GRAPH in requested:
                topology = plan_story_graph_topology(
                    project_id=child.project_id,
                    brief=snapshot.brief,
                    max_downstream_work_units=128,
                )
                source_topology = session.get(StoryGraphTopologyRow, source.id)
                if source_topology is not None and source_topology.topology_hash != topology.topology_hash:
                    raise RepairEligibilityError(
                        "repair.parent_evidence_invalid",
                        "source Story Graph topology no longer matches the deterministic planner",
                    )
            profile_hash = str(child.provider_snapshot.get("profileHash") or stable_hash(child.provider_snapshot))
            stage_budgets: dict[StageName, StageBudget] | None = None
            if is_v2_snapshot(child.provider_snapshot) or is_v3_snapshot(child.provider_snapshot):
                v2_profile = (
                    TextProviderProfileSnapshotV3.model_validate(child.provider_snapshot)
                    if is_v3_snapshot(child.provider_snapshot)
                    else TextProviderProfileSnapshot.model_validate(child.provider_snapshot)
                )
                stage_budgets = {
                    stage: StageBudget(
                        **{
                            **DEFAULT_STAGE_BUDGETS[stage].model_dump(mode="python"),
                            "max_output_tokens": v2_profile.stage_max_output_tokens.for_stage(stage.value),
                        }
                    )
                    for stage in requested
                }
            plan = create_generation_plan(
                run_id=child.id,
                requested_stages=requested,
                provider_profile_hash=profile_hash,
                story_graph_topology_hash=topology.topology_hash if topology is not None else None,
                canonical_inputs=self._run_plan_inputs_in_session(session, snapshot, requested),
                stage_budgets=stage_budgets,
                max_concurrency=int(child.provider_snapshot.get("textMaxConcurrency") or 1),
                canonical_snapshot_hash=snapshot.snapshot_hash,
                canonical_snapshot_bytes=len(
                    canonical_json(snapshot.model_dump(mode="json", by_alias=True)).encode("utf-8")
                ),
                instructions=child.instructions,
                context_window_tokens=int(child.provider_snapshot.get("textContextWindowTokens") or 32_768),
                provider_output_token_ceiling=int(child.provider_snapshot.get("textMaxOutputTokens") or 8_192),
            )
            session.add(
                GenerationPlanRow(
                    run_id=child.id,
                    plan_hash=plan.plan_hash,
                    plan=plan.model_dump(mode="json", by_alias=False),
                    created_at=child.created_at,
                )
            )
            if topology is not None:
                session.add(
                    StoryGraphTopologyRow(
                        run_id=child.id,
                        generation_plan_hash=plan.plan_hash,
                        topology_hash=topology.topology_hash,
                        topology=topology.model_dump(mode="json", by_alias=True),
                        created_at=child.created_at,
                    )
                )

            reuse_sources = self._frozen_reuse_sources_in_session(
                session, source=source, target=target
            )
            source_topology_row = session.get(StoryGraphTopologyRow, source.id)
            unsigned_scope: dict[str, Any] = {
                "childRunId": child.id,
                "parentRunId": source.id,
                "targetWorkUnitId": target.id,
                "stage": target.stage,
                "sourceGenerationPlanHash": source_plan_row.plan_hash,
                "sourceProviderProfileHash": source_plan.provider_profile_hash,
                "sourceStoryGraphTopologyHash": (
                    source_topology_row.topology_hash if source_topology_row is not None else None
                ),
                "sourceStagePlanId": source_stage_plan.id,
                "sourceStagePlanHash": source_stage_plan.stage_plan_hash,
                "sourceCanonicalSnapshotHash": snapshot.snapshot_hash,
                "targetSelector": dict(target.selector),
                "targetDependencyHash": target.dependency_hash,
                "targetUnitDependencyHash": target.unit_dependency_hash,
                "targetInputHash": target.input_hash,
                "failedAttemptId": failed_attempt.id,
                "responseArtifactId": response.id,
                "validationArtifactId": validation.id,
                "reuseSources": [item.model_dump(mode="json", by_alias=True) for item in reuse_sources],
                "createdAt": child.created_at.isoformat(),
            }
            unsigned_scope["scopeHash"] = "pending"
            provisional_scope = WorkUnitRepairScope(
                **unsigned_scope,
            )
            scope_hash = stable_hash(
                self._scope_hash_payload(
                    provisional_scope.model_dump(mode="json", by_alias=True)
                )
            )
            scope = provisional_scope.model_copy(update={"scope_hash": scope_hash})
            session.add(
                WorkUnitRepairScopeRow(
                    child_run_id=child.id,
                    parent_run_id=source.id,
                    target_work_unit_id=target.id,
                    stage=target.stage,
                    scope_hash=scope.scope_hash,
                    scope=scope.model_dump(mode="json", by_alias=True),
                    created_at=scope.created_at,
                )
            )
            session.add(
                WorkUnitRepairIdempotencyRow(
                    idempotency_key=key,
                    request_fingerprint=fingerprint,
                    parent_run_id=source.id,
                    target_work_unit_id=target.id,
                    child_run_id=child.id,
                    created_at=child.created_at,
                )
            )
            return WorkUnitRepairRunCreation(run=child, created=True)

    def get_work_unit_repair_scope(self, child_run_id: str) -> WorkUnitRepairScope:
        with self._read() as session:
            row = session.get(WorkUnitRepairScopeRow, child_run_id)
            if row is None:
                raise NotFoundError(f"exact work-unit repair scope not found for run: {child_run_id}")
            return self._repair_scope(row)

    def create_attempt(
        self,
        run_id: str,
        stage: StageName,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> GenerationAttempt:
        with self._write() as session:
            run = self._run_row(session, run_id)
            if RunStatus(run.status) != RunStatus.RUNNING:
                raise InvalidTransitionError(
                    f"cannot create generation attempt while run is {run.status}"
                )
            prior_count = len(
                session.scalars(
                    select(GenerationAttemptRow).where(
                        GenerationAttemptRow.run_id == run_id,
                        GenerationAttemptRow.stage == stage.value,
                    )
                ).all()
            )
            attempt = GenerationAttempt(
                run_id=run_id,
                stage=stage,
                attempt_number=prior_count + 1,
                status=AttemptStatus.RUNNING,
                provider=provider,
                model=model,
            )
            session.add(
                GenerationAttemptRow(
                    id=attempt.id,
                    run_id=run_id,
                    stage=stage.value,
                    attempt_number=attempt.attempt_number,
                    attempt_kind=GenerationAttemptKind.PRIMARY.value,
                    source_attempt_id=None,
                    status=attempt.status.value,
                    provider=provider,
                    model=model,
                    error=None,
                    outcome_code=None,
                    started_at=attempt.started_at,
                    finished_at=None,
                )
            )
            return attempt

    def finish_attempt(
        self,
        attempt_id: str,
        status: AttemptStatus,
        *,
        error: str | None = None,
        outcome_code: str | None = None,
        allow_correction: bool = False,
        failure_disposition: WorkUnitFailureDisposition | None = None,
    ) -> GenerationAttempt:
        if status == AttemptStatus.RUNNING:
            raise InvalidTransitionError("finish_attempt requires a terminal attempt status")
        with self._write() as session:
            row = session.get(GenerationAttemptRow, attempt_id)
            if row is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            unit = self._attempt_work_unit_unsealed_in_session(session, row)
            if AttemptStatus(row.status) != AttemptStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish attempt from {row.status}")
            row.status = status.value
            row.error = error
            row.outcome_code = outcome_code
            row.finished_at = utc_now()
            if failure_disposition is not None and status != AttemptStatus.FAILED:
                raise InvalidTransitionError(
                    "only a failed attempt may declare a work-unit failure disposition"
                )
            if unit is not None:
                if status == AttemptStatus.SUCCEEDED:
                    unit.status = WorkUnitStatus.SUCCEEDED.value
                elif status == AttemptStatus.CANCELLED:
                    unit.status = WorkUnitStatus.CANCELLED.value
                elif allow_correction and not row.outcome_unknown:
                    if row.response_persisted_at is None or not outcome_code:
                        raise InvalidTransitionError(
                            "only a durably recorded rejected response may authorize correction"
                        )
                    unit.status = WorkUnitStatus.QUEUED.value
                elif not row.outcome_unknown:
                    if failure_disposition is None:
                        raise InvalidTransitionError(
                            "known work-unit failures require an explicit failed or quarantined disposition"
                        )
                    unit.status = WorkUnitStatus(failure_disposition.value).value
            return self._attempt(row)

    @staticmethod
    def _assert_secret_free_artifact_content(content: Any) -> None:
        """Reject recognizable credential values before immutable evidence lands.

        Provider adapters normally redact response envelopes before this layer.
        This second boundary protects direct callers and alternate adapters.
        Redacted field names (for example ``apiKey: [redacted]``) remain useful
        diagnostics; only a value that matches the established secret policy is
        rejected here.
        """

        if contains_secret_value(content) or (
            contains_secret_setting(content) and _contains_unredacted_secret_setting(content)
        ):
            raise InvalidTransitionError("artifact evidence must not contain secret-shaped values")

    def add_artifact(self, artifact: Artifact) -> Artifact:
        self._assert_secret_free_artifact_content(artifact.content)
        with self._write() as session:
            self._run_row(session, artifact.run_id)
            attempt: GenerationAttemptRow | None = None
            if artifact.attempt_id is not None:
                attempt = session.get(GenerationAttemptRow, artifact.attempt_id)
                if attempt is None:
                    raise NotFoundError(f"generation attempt not found: {artifact.attempt_id}")
                if attempt.run_id != artifact.run_id:
                    raise InvalidTransitionError("artifact attempt must belong to its declared run")
                if artifact.stage is not None and attempt.stage != artifact.stage.value:
                    raise InvalidTransitionError("artifact stage must match its declared attempt")
                if artifact.work_unit_id is not None and attempt.work_unit_id != artifact.work_unit_id:
                    raise InvalidTransitionError("artifact work unit must match its declared attempt")
                if attempt.work_unit_id is not None and artifact.work_unit_id is None:
                    raise InvalidTransitionError("work-unit attempt artifacts must retain their workUnitId")
            if artifact.work_unit_id is not None:
                unit = session.get(GenerationWorkUnitRow, artifact.work_unit_id)
                if unit is None:
                    raise NotFoundError(f"generation work unit not found: {artifact.work_unit_id}")
                if unit.run_id != artifact.run_id:
                    raise InvalidTransitionError("artifact work unit must belong to its declared run")
                if artifact.stage is None or unit.stage != artifact.stage.value:
                    raise InvalidTransitionError("artifact work unit must match its declared stage")
                self._assert_work_unit_unsealed_in_session(session, unit)
                if artifact.kind == ArtifactKind.RESPONSE:
                    raise InvalidTransitionError(
                        "work-unit responses must be persisted through persist_attempt_response"
                    )
                if attempt is None:
                    raise InvalidTransitionError("work-unit artifacts require a producer attempt")
                existing = session.scalar(
                    select(ArtifactRow).where(
                        ArtifactRow.attempt_id == attempt.id,
                        ArtifactRow.kind == artifact.kind.value,
                    )
                )
                if existing is not None:
                    if (
                        existing.run_id == artifact.run_id
                        and existing.work_unit_id == artifact.work_unit_id
                        and existing.stage == (artifact.stage.value if artifact.stage else None)
                        and existing.content_hash == artifact.content_hash
                    ):
                        return self._artifact(existing)
                    raise InvalidTransitionError(
                        f"work-unit producer attempt already has immutable {artifact.kind.value} evidence"
                    )
            if artifact.source_artifact_id is not None:
                source = session.get(ArtifactRow, artifact.source_artifact_id)
                if source is None:
                    raise NotFoundError(
                        f"source artifact not found: {artifact.source_artifact_id}"
                    )
            session.add(
                ArtifactRow(
                    id=artifact.id,
                    run_id=artifact.run_id,
                    attempt_id=artifact.attempt_id,
                    work_unit_id=artifact.work_unit_id,
                    source_artifact_id=artifact.source_artifact_id,
                    stage=artifact.stage.value if artifact.stage else None,
                    kind=artifact.kind.value,
                    media_type=artifact.media_type,
                    content=_json_data(artifact.content),
                    content_hash=artifact.content_hash,
                    created_at=artifact.created_at,
                )
            )
        return artifact

    def get_artifact(self, artifact_id: str) -> Artifact:
        with self._read() as session:
            row = session.get(ArtifactRow, artifact_id)
            if row is None:
                raise NotFoundError(f"artifact not found: {artifact_id}")
            return self._artifact(row)

    def get_run_trace(self, run_id: str) -> RunTrace:
        with self._read() as session:
            run = self._run(self._run_row(session, run_id))
            attempts = [
                self._attempt(row)
                for row in session.scalars(
                    select(GenerationAttemptRow)
                    .where(GenerationAttemptRow.run_id == run_id)
                    .order_by(GenerationAttemptRow.started_at, GenerationAttemptRow.attempt_number)
                ).all()
            ]
            artifacts = [
                self._artifact(row)
                for row in session.scalars(
                    select(ArtifactRow).where(ArtifactRow.run_id == run_id).order_by(ArtifactRow.created_at)
                ).all()
            ]
            if run.result_revision_ids:
                snapshot_is_current = self._run_outputs_are_current(session, self._run_row(session, run_id))
            else:
                current = self._snapshot_in_session(session, run.project_id)
                snapshot_is_current = current.snapshot_hash == run.canonical_snapshot.snapshot_hash
            return RunTrace(
                run=run,
                attempts=attempts,
                artifacts=artifacts,
                snapshot_is_current=snapshot_is_current,
            )

    def get_media_prompt_context(self, project_id: str, shot_id: str) -> MediaPromptContext:
        """Freeze canonical facts consumed by an application-layer prompt compiler."""

        with self._read() as session:
            project = self._project(self._project_row(session, project_id))
            bible_head = self._stage_row(session, project_id, StageName.STORY_BIBLE)
            if bible_head.status != StageStatus.READY.value:
                raise StagePrerequisiteError(StageName.STORYBOARD, StageName.STORY_BIBLE, bible_head.status)
            head = self._stage_row(session, project_id, StageName.STORYBOARD)
            if head.status != StageStatus.READY.value:
                raise StagePrerequisiteError(StageName.STORYBOARD, StageName.STORYBOARD, head.status)
            storyboard = self._load_stage_payload(session, project_id, StageName.STORYBOARD)
            assert isinstance(storyboard, Storyboard)
            shot = next((candidate for candidate in storyboard.shots if candidate.id == shot_id), None)
            if shot is None:
                raise NotFoundError(f"shot not found in current storyboard: {shot_id}")
            bible = self._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            assert isinstance(bible, StoryBible)
            return MediaPromptContext(
                brief=project.brief,
                story_bible=bible,
                shot=shot,
                storyboard_revision=head.revision,
            )

    def create_media_task(
        self,
        project_id: str,
        shot_id: str,
        kind: MediaKind,
        *,
        expected_storyboard_revision: int,
        derived_prompt: str,
        prompt_components: dict[str, Any],
        provider: str | None = None,
        public_settings: dict[str, Any] | None = None,
    ) -> MediaTask:
        """Reject the pre-M2 Shot-to-provider path before any data access.

        Approval alone is deliberately not a production input.  M2 will
        replace this compatibility-shaped entry point with one that accepts an
        immutable ProductionSnapshot; keeping the method callable today would
        let an in-process caller bypass the API's hard stop.
        """

        _ = (
            project_id,
            shot_id,
            kind,
            expected_storyboard_revision,
            derived_prompt,
            prompt_components,
            provider,
            public_settings,
        )
        raise ProductionPipelineNotReadyError()

    def get_media_task(self, task_id: str) -> MediaTask:
        with self._read() as session:
            return self._media_task(self._media_task_row(session, task_id))

    def list_project_media_tasks(self, project_id: str, *, limit: int = 200) -> list[MediaTask]:
        if not 1 <= limit <= 500:
            raise ValueError("media task list limit must be between 1 and 500")
        with self._read() as session:
            self._project_row(session, project_id)
            rows = session.scalars(
                select(MediaTaskRow)
                .where(MediaTaskRow.project_id == project_id)
                .order_by(MediaTaskRow.created_at.desc())
                .limit(limit)
            ).all()
            return [self._media_task(row) for row in rows]

    def start_media_task(self, task_id: str, *, provider: str | None = None) -> MediaTask:
        # Every task stored before M2 lacks a ProductionSnapshot.  Do not even
        # read it here: callers must not turn a queued historical row into a
        # provider-bound execution by bypassing the HTTP hard stop.
        _ = (task_id, provider)
        raise ProductionPipelineNotReadyError()

    def record_media_submission(
        self,
        task_id: str,
        *,
        provider: str,
        provider_task_id: str | None,
    ) -> MediaTask:
        # A persisted provider task ID would make subsequent polling a new
        # production operation.  Historical rows can only be read or safely
        # terminalized until M2 owns that immutable boundary.
        _ = (task_id, provider, provider_task_id)
        raise ProductionPipelineNotReadyError()

    def finish_media_task(
        self,
        task_id: str,
        status: MediaTaskStatus,
        *,
        output_uri: str | None = None,
        error: str | None = None,
    ) -> MediaTask:
        if status not in TERMINAL_MEDIA_TASK_STATUSES:
            raise InvalidTransitionError("finish_media_task requires a terminal status")
        if status == MediaTaskStatus.SUCCEEDED:
            # Success would attach a new provider-derived URI to a legacy row.
            # Preserve only failure/cancellation for upgrade recovery.
            raise ProductionPipelineNotReadyError()
        normalized_error = error.strip() if error else None
        if status == MediaTaskStatus.FAILED and not normalized_error:
            raise ValueError("failed media tasks require an error")
        with self._write() as session:
            row = self._media_task_row(session, task_id)
            if MediaTaskStatus(row.status) != MediaTaskStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish media task from {row.status}")
            now = utc_now()
            row.status = status.value
            row.output_uri = None
            row.error = normalized_error if status == MediaTaskStatus.FAILED else None
            row.finished_at = now
            row.updated_at = now
            return self._media_task(row)

    def get_provider_settings(self) -> ProviderSettings:
        with self._read() as session:
            row = session.get(ProviderSettingsRow, 1)
            if row is None:
                return ProviderSettings()
            data = dict(row.settings)
            data.update(
                profile_version=row.revision,
                revision=row.revision,
                updated_at=row.updated_at,
            )
            return ProviderSettings.model_validate(data)

    def bootstrap_default_text_provider_profile(
        self,
        environment_default: TextProviderProfileSnapshot,
    ) -> TextProviderProfile:
        """Materialize the effective legacy/environment text config exactly once.

        Migration 0006 deliberately stores the old singleton payload without
        inventing V2 execution fields.  Runtime startup is the first layer that
        can see the trusted repo-root ``.env`` and host environment.  Once this
        method writes a V2 snapshot, later environment edits cannot silently
        change the saved profile or runs that reference it.
        """

        if environment_default.profile_id != DEFAULT_PROVIDER_PROFILE_ID:
            raise ValueError("the environment bootstrap snapshot must be for default")
        with self._write() as session:
            row = session.get(TextProviderProfileRow, DEFAULT_PROVIDER_PROFILE_ID)
            now = utc_now()
            if row is not None and is_v2_snapshot(row.settings):
                return self._text_provider_profile(row)

            legacy = dict(row.settings) if row is not None else {}
            if contains_secret_setting(legacy) or contains_secret_value(legacy):
                # Do not carry a credential forward from a legacy settings bag.
                legacy = {
                    key: value
                    for key, value in legacy.items()
                    if not contains_secret_setting({key: value})
                    and not contains_secret_value(value)
                }
            revision = row.revision if row is not None else 0
            values = environment_default.model_dump(
                mode="python",
                by_alias=False,
                exclude={"profile_hash"},
            )
            if revision > 0:
                aliases = {
                    "textProvider": "text_provider",
                    "textBaseUrl": "text_base_url",
                    "textModel": "text_model",
                    "textAuthMode": "text_auth_mode",
                    "textCapabilities": "text_capabilities",
                    "textContextWindowTokens": "text_context_window_tokens",
                    "textMaxOutputTokens": "text_max_output_tokens",
                    "textTemperature": "text_temperature",
                    "textMaxConcurrency": "text_max_concurrency",
                    "textConnectTimeoutSeconds": "text_connect_timeout_seconds",
                    "textAttemptTimeoutSeconds": "text_attempt_timeout_seconds",
                }
                for source, target in aliases.items():
                    legacy_value = legacy.get(source, legacy.get(target))
                    if legacy_value is not None:
                        if target == "text_capabilities" and isinstance(legacy_value, dict):
                            current = dict(values[target])
                            current.update(legacy_value)
                            values[target] = current
                        else:
                            values[target] = legacy_value
            values.update(
                profile_schema_version=2,
                profile_id=DEFAULT_PROVIDER_PROFILE_ID,
                profile_version=revision,
                profile_hash="",
            )
            try:
                configuration = TextProviderProfileSnapshot.model_validate(values)
            except ValueError:
                # A legacy public setting may legitimately differ from a named
                # published preset. Preserve it, but state that it is custom.
                values["preset_id"] = PresetId.CUSTOM
                configuration = TextProviderProfileSnapshot.model_validate(values)
            stored = configuration.model_dump(mode="json", by_alias=True)
            if row is None:
                row = TextProviderProfileRow(
                    id=DEFAULT_PROVIDER_PROFILE_ID,
                    display_name="Default",
                    settings=stored,
                    revision=revision,
                    enabled=True,
                    availability_revision=0,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                session.flush()
            else:
                row.settings = stored
                row.updated_at = now

            selection = session.get(ProviderProfileSelectionRow, 1)
            if selection is None:
                session.add(
                    ProviderProfileSelectionRow(
                        id=1,
                        active_profile_id=DEFAULT_PROVIDER_PROFILE_ID,
                        revision=0,
                        updated_at=now,
                    )
                )
            return self._text_provider_profile(row)

    def get_text_provider_profile(self, profile_id: str) -> TextProviderProfile:
        with self._read() as session:
            row = session.get(TextProviderProfileRow, profile_id)
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            return self._text_provider_profile(row)

    def list_text_provider_profiles(self) -> list[TextProviderProfile]:
        with self._read() as session:
            rows = session.scalars(
                select(TextProviderProfileRow).order_by(TextProviderProfileRow.id)
            ).all()
            return [self._text_provider_profile(row) for row in rows]

    def get_provider_profile_selection(self) -> ProviderProfileSelection:
        with self._read() as session:
            row = session.get(ProviderProfileSelectionRow, 1)
            if row is None:
                raise NotFoundError("text provider profile selection has not been initialized")
            return self._provider_profile_selection(row)

    @staticmethod
    def _profile_configuration_for_revision(
        profile_id: str,
        revision: int,
        value: TextProviderProfileSnapshot | dict[str, Any],
    ) -> TextProviderProfileSnapshot:
        raw = (
            value.model_dump(mode="python", by_alias=False)
            if isinstance(value, TextProviderProfileSnapshot)
            else dict(value)
        )
        if contains_secret_setting(raw) or contains_secret_value(raw):
            raise ValueError("text provider profile configuration must not contain secrets")
        for key in (
            "profileHash",
            "profile_hash",
            "profileId",
            "profile_id",
            "profileVersion",
            "profile_version",
            "profileSchemaVersion",
            "profile_schema_version",
        ):
            raw.pop(key, None)
        raw.update(
            profile_schema_version=2,
            profile_id=profile_id,
            profile_version=revision,
            profile_hash="",
        )
        return TextProviderProfileSnapshot.model_validate(raw)

    def create_text_provider_profile(
        self,
        profile_id: str,
        display_name: str,
        *,
        configuration: TextProviderProfileSnapshot | dict[str, Any] | None = None,
        copy_from_profile_id: str | None = None,
        adapter_id: str | None = None,
        adapter_version: str | None = None,
    ) -> TextProviderProfile:
        if (configuration is None) == (copy_from_profile_id is None):
            raise ValueError("provide exactly one of configuration or copy_from_profile_id")
        if (adapter_id is None) != (adapter_version is None):
            raise ValueError("adapter_id and adapter_version must be provided together")
        if re.fullmatch(PROFILE_ID_PATTERN, profile_id) is None:
            raise ValueError("profile_id must match [a-z][a-z0-9_]{0,62}")
        normalized_name = display_name.strip()
        if not normalized_name:
            raise ValueError("display_name must not be blank")
        with self._write() as session:
            if session.get(TextProviderProfileRow, profile_id) is not None:
                raise InvalidTransitionError(f"text provider profile already exists: {profile_id}")
            if copy_from_profile_id is not None:
                source = session.get(TextProviderProfileRow, copy_from_profile_id)
                if source is None:
                    raise NotFoundError(
                        f"text provider profile not found: {copy_from_profile_id}"
                    )
                configuration = dict(source.settings)
            assert configuration is not None
            parsed = self._profile_configuration_for_revision(profile_id, 1, configuration)
            now = utc_now()
            row = TextProviderProfileRow(
                id=profile_id,
                display_name=normalized_name,
                settings=parsed.model_dump(mode="json", by_alias=True),
                revision=1,
                enabled=True,
                availability_revision=0,
                adapter_id=(
                    adapter_id
                    or (source.adapter_id if copy_from_profile_id is not None else "openai_compatible")
                ),
                adapter_version=(
                    adapter_version
                    or (source.adapter_version if copy_from_profile_id is not None else "1")
                ),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            return self._text_provider_profile(row)

    def update_text_provider_profile(
        self,
        profile_id: str,
        expected_revision: int,
        *,
        display_name: str,
        configuration: TextProviderProfileSnapshot | dict[str, Any],
        adapter_id: str | None = None,
        adapter_version: str | None = None,
    ) -> TextProviderProfile:
        if (adapter_id is None) != (adapter_version is None):
            raise ValueError("adapter_id and adapter_version must be provided together")
        with self._write() as session:
            row = session.get(TextProviderProfileRow, profile_id)
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            if row.revision != expected_revision:
                raise RevisionConflictError(
                    f"text-provider-profile:{profile_id}", expected_revision, row.revision
                )
            normalized_name = display_name.strip()
            if not normalized_name:
                raise ValueError("display_name must not be blank")
            proposed = self._profile_configuration_for_revision(
                profile_id, row.revision + 1, configuration
            )
            current_without_version = dict(row.settings)
            proposed_without_version = proposed.model_dump(mode="json", by_alias=True)
            for key in ("profileVersion", "profileHash"):
                current_without_version.pop(key, None)
                proposed_without_version.pop(key, None)
            next_adapter_id = adapter_id or row.adapter_id
            next_adapter_version = adapter_version or row.adapter_version
            if (
                row.display_name == normalized_name
                and current_without_version == proposed_without_version
                and row.adapter_id == next_adapter_id
                and row.adapter_version == next_adapter_version
            ):
                return self._text_provider_profile(row)
            row.revision += 1
            row.display_name = normalized_name
            row.settings = proposed.model_dump(mode="json", by_alias=True)
            row.adapter_id = next_adapter_id
            row.adapter_version = next_adapter_version
            row.updated_at = utc_now()
            return self._text_provider_profile(row)

    def activate_text_provider_profile(
        self,
        profile_id: str,
        expected_selection_revision: int,
    ) -> ProviderProfileSelection:
        with self._write() as session:
            profile = session.get(TextProviderProfileRow, profile_id)
            if profile is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            if not profile.enabled:
                raise InvalidTransitionError(
                    "a disabled text provider profile cannot be activated; enable it first"
                )
            row = session.get(ProviderProfileSelectionRow, 1)
            if row is None:
                raise NotFoundError("text provider profile selection has not been initialized")
            if row.revision != expected_selection_revision:
                raise RevisionConflictError(
                    "text-provider-profile-selection",
                    expected_selection_revision,
                    row.revision,
                )
            if row.active_profile_id != profile_id:
                row.active_profile_id = profile_id
                row.revision += 1
                row.updated_at = utc_now()
            return self._provider_profile_selection(row)

    def set_text_provider_profile_enabled(
        self,
        profile_id: str,
        expected_availability_revision: int,
        *,
        enabled: bool,
    ) -> TextProviderProfile:
        """Toggle future-admission availability without rewriting profile config."""

        with self._write() as session:
            row = session.get(TextProviderProfileRow, profile_id)
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            if row.availability_revision != expected_availability_revision:
                raise RevisionConflictError(
                    f"text-provider-profile-availability:{profile_id}",
                    expected_availability_revision,
                    row.availability_revision,
                )
            if row.enabled != enabled:
                row.enabled = enabled
                row.availability_revision += 1
                row.updated_at = utc_now()
            return self._text_provider_profile(row)

    @staticmethod
    def _profile_id_from_snapshot(snapshot: Mapping[str, Any]) -> str | None:
        value = snapshot.get("profileId") or snapshot.get("profile_id")
        return value if isinstance(value, str) and value else None

    def _assert_new_run_profile_enabled(
        self, session: Session, provider_snapshot: Mapping[str, Any]
    ) -> None:
        """Guard fresh V2 admission without rewriting historical snapshot semantics.

        A V1 snapshot can contain the old singleton ``profileId`` field, but
        its JSON and hash deliberately remain on the pre-profile path and need
        not have a mutable profile row. Reading it must not synthesize a V2
        control-plane dependency. If that legacy name *does* resolve to an
        existing row, however, it is still a current request for a disabled
        backend and must not bypass its availability state.
        """

        profile_id = self._profile_id_from_snapshot(provider_snapshot)
        if profile_id is None:
            # ``validate_public_provider_snapshot`` has already validated V2
            # snapshots, so this protects direct repository callers if that
            # boundary changes rather than treating an anonymous V2 run as
            # available.
            if is_v3_snapshot(provider_snapshot):
                raise InvalidTransitionError(
                    "a managed V3 provider snapshot must name a registered profile before admitting a new run"
                )
            return
        profile = session.get(TextProviderProfileRow, profile_id)
        if profile is None:
            # The historic direct test/runtime path used an unmaterialized
            # default V2 profile. Preserve that exact compatibility path;
            # named V2 and every V3 admission remain control-plane bound.
            if profile_id == DEFAULT_PROVIDER_PROFILE_ID and not is_v3_snapshot(provider_snapshot):
                return
            if not is_v3_snapshot(provider_snapshot):
                raise InvalidTransitionError(
                    f"text provider profile {profile_id} is not registered; register it before admitting a new run"
                )
            raise InvalidTransitionError(
                f"text provider profile {profile_id} is not registered; register it before admitting a new run"
            )
        if not profile.enabled:
            raise InvalidTransitionError(
                f"text provider profile {profile_id} is disabled; enable it before admitting a new run"
            )

    def delete_text_provider_profile(
        self,
        profile_id: str,
        expected_revision: int,
    ) -> None:
        if profile_id == DEFAULT_PROVIDER_PROFILE_ID:
            raise InvalidTransitionError("the default text provider profile cannot be deleted")
        with self._write() as session:
            row = session.get(TextProviderProfileRow, profile_id)
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            if row.revision != expected_revision:
                raise RevisionConflictError(
                    f"text-provider-profile:{profile_id}", expected_revision, row.revision
                )
            selection = session.get(ProviderProfileSelectionRow, 1)
            if selection is not None and selection.active_profile_id == profile_id:
                raise InvalidTransitionError("the active text provider profile cannot be deleted")
            live_runs = session.scalars(
                select(GenerationRunRow).where(
                    GenerationRunRow.status.not_in(
                        [status.value for status in TERMINAL_RUN_STATUSES]
                    )
                )
            ).all()
            if any(
                candidate.provider_snapshot.get("profileId") == profile_id
                for candidate in live_runs
            ):
                raise InvalidTransitionError(
                    "a text provider profile referenced by a non-terminal run cannot be deleted"
                )
            session.delete(row)

    def put_provider_settings(self, settings: ProviderSettings) -> ProviderSettings:
        # ProviderSettings.extra=forbid is the security boundary: secret-shaped fields cannot enter storage.
        now = utc_now()
        data = settings.model_dump(
            mode="json",
            by_alias=False,
            exclude={
                "revision",
                "updated_at",
                "profile_version",
                "profile_hash",
                "text_key_available",
                "image_key_available",
                "video_key_available",
            },
        )
        with self._write() as session:
            row = session.get(ProviderSettingsRow, 1)
            if row is None:
                row = ProviderSettingsRow(id=1, settings=data, revision=1, updated_at=now)
                session.add(row)
            elif row.settings != data:
                row.settings = data
                row.revision += 1
                row.updated_at = now
            result = dict(row.settings)
            result.update(
                profile_version=row.revision,
                revision=row.revision,
                updated_at=row.updated_at,
            )
            return ProviderSettings.model_validate(result)

    def update_provider_settings_projection(
        self,
        *,
        expected_profile_id: str,
        expected_profile_revision: int,
        updates: dict[str, Any],
        defaults: ProviderSettings,
    ) -> tuple[TextProviderProfile, ProviderSettings]:
        """Atomically update the legacy active-profile/media projection.

        The compatibility endpoint spans two durable records: the selected
        named text profile and the singleton media settings.  Reading either
        outside this transaction would allow an activation or named-profile
        edit to interleave and make a stale form overwrite unrelated state.
        """

        if contains_secret_setting(updates) or contains_secret_value(updates):
            raise ValueError("public provider configuration must not contain secrets")
        with self._write() as session:
            selection = session.get(ProviderProfileSelectionRow, 1)
            if selection is None:
                raise NotFoundError("text provider profile selection has not been initialized")
            if selection.active_profile_id != expected_profile_id:
                raise InvalidTransitionError(
                    "active text provider profile changed; reload settings"
                )

            profile_row = session.get(TextProviderProfileRow, expected_profile_id)
            if profile_row is None:
                raise NotFoundError(
                    f"text provider profile not found: {expected_profile_id}"
                )
            if profile_row.revision != expected_profile_revision:
                raise RevisionConflictError(
                    f"text-provider-profile:{expected_profile_id}",
                    expected_profile_revision,
                    profile_row.revision,
                )

            media_row = session.get(ProviderSettingsRow, 1)
            if media_row is None:
                persisted = ProviderSettings()
            else:
                persisted_data = dict(media_row.settings)
                persisted_data.update(
                    profile_version=media_row.revision,
                    revision=media_row.revision,
                    updated_at=media_row.updated_at,
                )
                persisted = ProviderSettings.model_validate(persisted_data)

            effective_values = {
                field: (
                    getattr(defaults, field)
                    if persisted.revision == 0
                    else (
                        getattr(persisted, field)
                        if getattr(persisted, field) is not None
                        else getattr(defaults, field)
                    )
                )
                for field in PUBLIC_PROVIDER_SETTING_FIELDS
            }
            profile_configuration = TextProviderProfileSnapshot.model_validate(
                profile_row.settings
            )
            effective_values.update(
                profile_id=expected_profile_id,
                text_provider=profile_configuration.text_provider,
                text_base_url=profile_configuration.text_base_url,
                text_model=profile_configuration.text_model,
                text_auth_mode=profile_configuration.text_auth_mode,
                text_capabilities={
                    "chat_completions": profile_configuration.text_capabilities.chat_completions,
                    "json_object": profile_configuration.text_capabilities.json_object,
                    "json_schema": profile_configuration.text_capabilities.json_schema,
                },
                text_context_window_tokens=profile_configuration.text_context_window_tokens,
                text_max_output_tokens=profile_configuration.text_max_output_tokens,
                text_temperature=profile_configuration.text_temperature,
                text_max_concurrency=profile_configuration.text_max_concurrency,
                text_connect_timeout_seconds=profile_configuration.text_connect_timeout_seconds,
                text_attempt_timeout_seconds=profile_configuration.text_attempt_timeout_seconds,
            )
            effective_values.update(updates)
            settings = ProviderSettings.model_validate(effective_values)

            profile_values = profile_configuration.model_dump(
                mode="python", by_alias=False, exclude={"profile_hash"}
            )
            profile_values.update(
                text_provider=settings.text_provider,
                text_base_url=settings.text_base_url,
                text_model=settings.text_model,
                text_auth_mode=settings.text_auth_mode.value,
                text_capabilities={
                    **profile_configuration.text_capabilities.model_dump(mode="python"),
                    "chat_completions": settings.text_capabilities.chat_completions,
                    "json_object": settings.text_capabilities.json_object,
                    "json_schema": settings.text_capabilities.json_schema,
                },
                text_context_window_tokens=settings.text_context_window_tokens,
                text_max_output_tokens=settings.text_max_output_tokens,
                text_temperature=settings.text_temperature,
                text_max_concurrency=settings.text_max_concurrency,
                text_connect_timeout_seconds=settings.text_connect_timeout_seconds,
                text_attempt_timeout_seconds=settings.text_attempt_timeout_seconds,
            )
            if {
                "text_context_window_tokens",
                "text_max_output_tokens",
                "text_attempt_timeout_seconds",
            } & updates.keys():
                profile_values["preset_id"] = PresetId.CUSTOM
            proposed = self._profile_configuration_for_revision(
                expected_profile_id,
                profile_row.revision + 1,
                profile_values,
            )
            current_without_version = dict(profile_row.settings)
            proposed_without_version = proposed.model_dump(mode="json", by_alias=True)
            for key in ("profileVersion", "profileHash"):
                current_without_version.pop(key, None)
                proposed_without_version.pop(key, None)
            if current_without_version != proposed_without_version:
                profile_row.revision += 1
                profile_row.settings = proposed.model_dump(mode="json", by_alias=True)
                profile_row.updated_at = utc_now()

            now = utc_now()
            stored_settings = settings.model_dump(
                mode="json",
                by_alias=False,
                exclude={
                    "revision",
                    "updated_at",
                    "profile_version",
                    "profile_hash",
                    "text_key_available",
                    "image_key_available",
                    "video_key_available",
                },
            )
            if media_row is None:
                media_row = ProviderSettingsRow(
                    id=1,
                    settings=stored_settings,
                    revision=1,
                    updated_at=now,
                )
                session.add(media_row)
            elif media_row.settings != stored_settings:
                media_row.settings = stored_settings
                media_row.revision += 1
                media_row.updated_at = now

            session.flush()
            persisted_result = dict(media_row.settings)
            persisted_result.update(
                profile_version=media_row.revision,
                revision=media_row.revision,
                updated_at=media_row.updated_at,
            )
            return (
                self._text_provider_profile(profile_row),
                ProviderSettings.model_validate(persisted_result),
            )


class ProjectSQLiteRepository(SQLiteRepository):
    """A one-project canonical repository with no application control tables.

    The pipeline and lifecycle runner keep their normal repository contract.
    This adapter supplies the missing ownership boundary: its schema excludes
    installation profiles/accounting and every project route is bound to the
    immutable project-home identity.
    """

    def __init__(
        self,
        database_url: str,
        *,
        project_id: str,
        create_schema: bool = True,
        sqlite_busy_timeout_ms: int = 1_000,
    ) -> None:
        if not project_id:
            raise ValueError("project_id is required for a project repository")
        self.project_id = project_id
        self._admitted_provider_snapshot_hash: str | None = None
        super().__init__(
            database_url,
            create_schema=create_schema,
            sqlite_busy_timeout_ms=sqlite_busy_timeout_ms,
            schema_scope="project",
        )

    @contextmanager
    def admit_provider_snapshot(self, provider_snapshot: dict[str, Any]) -> Iterator[None]:
        """Authorize one application-selected public profile for fresh work.

        The authorization is process-local and short lived.  The immutable
        public snapshot still belongs on each run; selection and credentials do
        not belong in the project database.
        """

        snapshot_hash = stable_hash(provider_snapshot)
        previous = self._admitted_provider_snapshot_hash
        self._admitted_provider_snapshot_hash = snapshot_hash
        try:
            yield
        finally:
            self._admitted_provider_snapshot_hash = previous

    def initialize_project(self, project: Project) -> Project:
        """Create the one project row selected by the immutable folder manifest."""

        if project.id != self.project_id:
            raise InvalidTransitionError("project repository identity does not match project initialization")
        with self._bootstrap_write() as session:
            existing = session.scalar(select(ProjectRow.id).limit(1))
            if existing is not None:
                raise InvalidTransitionError("project repository has already been initialized")
            row = ProjectRow(
                id=project.id,
                revision=project.revision,
                lifecycle_revision=project.lifecycle_revision,
                lifecycle_status=project.lifecycle_status.value,
                archived_at=project.archived_at,
                brief=project.brief.model_dump(mode="json", by_alias=False),
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            session.add(row)
            for stage in STAGE_ORDER:
                session.add(
                    StageHeadRow(
                        id=f"{project.id}:{stage.value}",
                        project_id=project.id,
                        stage=stage.value,
                        status=StageStatus.MISSING.value,
                        revision=0,
                        entity_revision_id=None,
                        content_hash=None,
                        schema_version=CURRENT_STAGE_SCHEMA_VERSION,
                        input_revisions={},
                        stale_reasons=[],
                        updated_at=project.updated_at,
                    )
                )
        return self.get_project(project.id)

    def create_project(self, *args: Any, **kwargs: Any) -> ProjectCreation:
        raise InvalidTransitionError(
            "project repositories are initialized only by their project-home manifest"
        )

    def duplicate_project(self, *args: Any, **kwargs: Any) -> ProjectDuplicateResult:
        raise InvalidTransitionError("a project repository cannot create a second project")

    def _project_row(self, session: Session, project_id: str) -> ProjectRow:
        if project_id != self.project_id:
            raise NotFoundError("project does not belong to this project repository")
        return SQLiteRepository._project_row(session, project_id)

    def _run_row(self, session: Session, run_id: str) -> GenerationRunRow:
        row = SQLiteRepository._run_row(session, run_id)
        if row.project_id != self.project_id:
            raise NotFoundError("generation run does not belong to this project repository")
        return row

    def _assert_new_run_profile_enabled(
        self,
        _session: Session,
        provider_snapshot: Mapping[str, Any],
    ) -> None:
        if self._admitted_provider_snapshot_hash != stable_hash(dict(provider_snapshot)):
            raise InvalidTransitionError(
                "project generation requires an application-admitted provider snapshot"
            )
