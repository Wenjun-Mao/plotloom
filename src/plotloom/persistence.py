from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
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
    Artifact,
    ArtifactKind,
    AttemptStatus,
    CanonicalSnapshot,
    EntityRevision,
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
    ProviderSettings,
    RepairSource,
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
    WorkUnitStatus,
    downstream_stages,
    stage_payload_model,
    upstream_stages,
    new_id,
    validate_initial_stage_prefix,
    utc_now,
    contains_secret_setting,
    contains_secret_value,
    validate_public_provider_snapshot,
)
from .generation.aggregation import aggregate_stage_fragments
from .generation.fragments import (
    SceneBeatsFragment,
    StoryBibleFragment,
    StoryGraphFragment,
    StoryboardFragment,
)
from .generation.planning import (
    DEFAULT_STAGE_BUDGETS,
    GenerationPlan,
    StageBudget,
    StagePlan,
    create_generation_plan,
    plan_stage,
)
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
    V2ExtractionPolicy,
    execution_preset,
    is_v2_snapshot,
)
from .exceptions import (
    BootstrapContentionError,
    IdempotencyConflictError,
    InvalidTransitionError,
    NotFoundError,
    RevisionConflictError,
    StagePrerequisiteError,
)
from .schema import SchemaMigrator, sqlite_database_path
from .validation import validate_stage_payload


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "v2_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
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


class EntityRevisionRow(Base):
    __tablename__ = "v2_entity_revisions"
    __table_args__ = (UniqueConstraint("project_id", "stage", "revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("v2_projects.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
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
    input_revisions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    stale_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


def _json_data(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=False)
    return value


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
    ) -> None:
        if sqlite_busy_timeout_ms < 1:
            raise ValueError("sqlite_busy_timeout_ms must be at least 1")
        self._sqlite_busy_timeout_ms = sqlite_busy_timeout_ms
        self._bootstrap_retry_after_seconds = max(1, (sqlite_busy_timeout_ms + 999) // 1_000)
        engine_options: dict[str, Any] = {"future": True}
        database_path = sqlite_database_path(database_url)
        if database_url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_options["poolclass"] = StaticPool
        elif database_path is not None:
            database_path.parent.mkdir(parents=True, exist_ok=True)
            if create_schema:
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
        if create_schema and database_path is None:
            Base.metadata.create_all(self.engine)

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
            brief=ProjectBrief.model_validate(row.brief),
            created_at=_stored_utc(row.created_at),
            updated_at=_stored_utc(row.updated_at),
        )

    @staticmethod
    def _stage_head(row: StageHeadRow) -> StageHead:
        return StageHead(
            stage=StageName(row.stage),
            status=StageStatus(row.status),
            revision=row.revision,
            entity_revision_id=row.entity_revision_id,
            content_hash=row.content_hash,
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
            input_revisions={StageName(key): value for key, value in row.input_revisions.items()},
            payload=row.payload,
            created_at=row.created_at,
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
    def _text_provider_profile(row: TextProviderProfileRow) -> TextProviderProfile:
        configuration = TextProviderProfileSnapshot.model_validate(row.settings)
        return TextProviderProfile(
            profile_id=row.id,
            display_name=row.display_name,
            configuration=configuration,
            revision=row.revision,
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
                    input_revisions={},
                    stale_reasons=[],
                    updated_at=now,
                )
            )
        return row

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
                payload = stage_payload_model(stage).model_validate(revision.payload)
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
                payload = stage_payload_model(initial_stage.stage).model_validate(initial_stage.payload)
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

    def update_project(self, project_id: str, expected_revision: int, brief: ProjectBrief) -> Project:
        with self._write() as session:
            row = self._project_row(session, project_id)
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

    def _load_stage_payload(self, session: Session, project_id: str, stage: StageName) -> StagePayload:
        head = self._stage_row(session, project_id, stage)
        if head.entity_revision_id is None:
            raise StagePrerequisiteError(stage, stage, head.status)
        revision = session.get(EntityRevisionRow, head.entity_revision_id)
        if revision is None:
            raise NotFoundError(f"entity revision not found: {head.entity_revision_id}")
        return stage_payload_model(stage).model_validate(revision.payload)

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
        validate_stage_payload(
            stage,
            payload,
            brief=brief,
            bible=upstream_payloads.get(StageName.STORY_BIBLE),  # type: ignore[arg-type]
            graph=upstream_payloads.get(StageName.STORY_GRAPH),  # type: ignore[arg-type]
            scene_beats=upstream_payloads.get(StageName.SCENE_BEATS),  # type: ignore[arg-type]
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
            return self._stage_head(head), None

        revision = EntityRevision(
            project_id=project_row.id,
            stage=stage,
            revision=head.revision + 1,
            parent_revision_id=head.entity_revision_id,
            content_hash=content_hash,
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
            input_revisions=next_inputs,
            payload=payload_data,
            created_at=now,
        )
        session.add(revision_row)
        head.status = StageStatus.READY.value
        head.revision = revision.revision
        head.entity_revision_id = revision.id
        head.content_hash = content_hash
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
        parsed = stage_payload_model(stage).model_validate(payload)
        with self._write() as session:
            project_row = self._project_row(session, project_id)
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
        """Read immutable upstream facts by the run snapshot, never a mutable head."""

        with self._read() as session:
            row = self._run_row(session, run_id)
            snapshot = CanonicalSnapshot.model_validate(row.canonical_snapshot)
            head = snapshot.stage_heads[stage]
            if head.entity_revision_id is None:
                raise StagePrerequisiteError(stage, stage, head.status.value)
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            if revision is None or revision.project_id != row.project_id or revision.stage != stage.value:
                raise NotFoundError(f"snapshot entity revision not found: {head.entity_revision_id}")
            return stage_payload_model(stage).model_validate(revision.payload)

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
            inputs[stage] = stage_payload_model(stage).model_validate(revision.payload)
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
        with self._write() as session:
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
            if is_v2_snapshot(run.provider_snapshot):
                v2_profile = TextProviderProfileSnapshot.model_validate(run.provider_snapshot)
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
        return stage_payload_model(stage).model_validate(aggregate.payload)

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
            dependencies[dependency] = stage_payload_model(dependency).model_validate(revision.payload)
        return dependencies

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
            expected = self._expected_stage_dependencies_in_session(session, run, stage)
            if dependencies is not None:
                if set(dependencies) != set(expected) or any(
                    stable_hash(dependencies[name]) != stable_hash(expected[name]) for name in expected
                ):
                    raise InvalidTransitionError(
                        "StagePlan dependencies must exactly match frozen canonical or sealed inputs"
                    )
            proposed = plan_stage(generation_plan, stage=stage, dependencies=expected)
            existing = self._stage_plan_row(session, run_id, stage)
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
            payload = aggregate_stage_fragments(
                stage_plan,
                fragments,
                brief=snapshot.brief,
                bible=dependencies.get(StageName.STORY_BIBLE),  # type: ignore[arg-type]
                graph=dependencies.get(StageName.STORY_GRAPH),  # type: ignore[arg-type]
                scene_beats=dependencies.get(StageName.SCENE_BEATS),  # type: ignore[arg-type]
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
        ambiguous_media_error = (
            "Media submission was interrupted before a provider task ID was "
            "persisted; the task was not resubmitted to avoid duplicate billing"
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
                status = MediaTaskStatus(row.status)
                pristine_queue = (
                    status == MediaTaskStatus.QUEUED
                    and row.started_at is None
                    and row.finished_at is None
                    and not row.provider_task_id
                )
                if pristine_queue:
                    resubmit_media_task_ids.append(row.id)
                    continue
                if status == MediaTaskStatus.RUNNING and row.provider_task_id:
                    resume_media_poll_task_ids.append(row.id)
                    continue

                row.status = MediaTaskStatus.FAILED.value
                row.started_at = row.started_at or now
                row.finished_at = now
                row.updated_at = now
                row.output_uri = None
                row.error = ambiguous_media_error
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

        with self._write() as session:
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
            payloads = {
                StageName(aggregate.stage): stage_payload_model(StageName(aggregate.stage)).model_validate(
                    aggregate.payload
                )
                for aggregate in aggregates
            }
            run, _ = self._commit_parsed_run_outputs_in_session(session, run_row, payloads)
            return run

    def _commit_run_outputs(
        self,
        run_id: str,
        payloads: dict[StageName, StagePayload | dict[str, Any]],
    ) -> tuple[GenerationRun, list[StageHead]]:
        """Validate inputs, install every requested revision, and succeed atomically."""

        parsed_payloads = {
            stage: stage_payload_model(stage).model_validate(payload) for stage, payload in payloads.items()
        }
        with self._write() as session:
            run_row = self._run_row(session, run_id)
            return self._commit_parsed_run_outputs_in_session(session, run_row, parsed_payloads)

    def _commit_parsed_run_outputs_in_session(
        self,
        session: Session,
        run_row: GenerationRunRow,
        parsed_payloads: dict[StageName, StagePayload],
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

    def add_artifact(self, artifact: Artifact) -> Artifact:
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
        if not derived_prompt.strip():
            raise ValueError("derived media prompt must not be blank")
        with self._write() as session:
            self._project_row(session, project_id)
            head = self._stage_row(session, project_id, StageName.STORYBOARD)
            if head.status != StageStatus.READY.value:
                raise StagePrerequisiteError(StageName.STORYBOARD, StageName.STORYBOARD, head.status)
            if head.revision != expected_storyboard_revision:
                raise RevisionConflictError("stage:storyboard", expected_storyboard_revision, head.revision)
            storyboard = self._load_stage_payload(session, project_id, StageName.STORYBOARD)
            assert isinstance(storyboard, Storyboard)
            if not any(candidate.id == shot_id for candidate in storyboard.shots):
                raise NotFoundError(f"shot not found in current storyboard: {shot_id}")
            task = MediaTask(
                project_id=project_id,
                shot_id=shot_id,
                storyboard_revision=head.revision,
                kind=kind,
                derived_prompt=derived_prompt,
                prompt_components=prompt_components,
                provider=provider,
                public_settings=public_settings or {},
            )
            session.add(
                MediaTaskRow(
                    id=task.id,
                    project_id=project_id,
                    shot_id=shot_id,
                    storyboard_revision=head.revision,
                    kind=kind.value,
                    status=task.status.value,
                    derived_prompt=task.derived_prompt,
                    prompt_components=prompt_components,
                    provider=provider,
                    public_settings=task.public_settings,
                    provider_task_id=None,
                    output_uri=None,
                    error=None,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    started_at=None,
                    finished_at=None,
                )
            )
            return task

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
        normalized_provider = provider.strip() if provider else None
        with self._write() as session:
            row = self._media_task_row(session, task_id)
            if MediaTaskStatus(row.status) != MediaTaskStatus.QUEUED:
                raise InvalidTransitionError(f"cannot start media task from {row.status}")
            now = utc_now()
            row.status = MediaTaskStatus.RUNNING.value
            row.provider = normalized_provider or row.provider
            row.error = None
            row.started_at = now
            row.finished_at = None
            row.updated_at = now
            return self._media_task(row)

    def record_media_submission(
        self,
        task_id: str,
        *,
        provider: str,
        provider_task_id: str | None,
    ) -> MediaTask:
        normalized_provider = provider.strip()
        normalized_task_id = provider_task_id.strip() if provider_task_id else None
        if not normalized_provider:
            raise ValueError("media provider must not be blank")
        with self._write() as session:
            row = self._media_task_row(session, task_id)
            if MediaTaskStatus(row.status) != MediaTaskStatus.RUNNING:
                raise InvalidTransitionError(f"cannot record media submission from {row.status}")
            row.provider = normalized_provider
            row.provider_task_id = normalized_task_id
            row.updated_at = utc_now()
            return self._media_task(row)

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
        normalized_output = output_uri.strip() if output_uri else None
        normalized_error = error.strip() if error else None
        if status == MediaTaskStatus.SUCCEEDED and not normalized_output:
            raise ValueError("succeeded media tasks require an output URI")
        if status == MediaTaskStatus.FAILED and not normalized_error:
            raise ValueError("failed media tasks require an error")
        with self._write() as session:
            row = self._media_task_row(session, task_id)
            if MediaTaskStatus(row.status) != MediaTaskStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish media task from {row.status}")
            now = utc_now()
            row.status = status.value
            row.output_uri = normalized_output if status == MediaTaskStatus.SUCCEEDED else None
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
    ) -> TextProviderProfile:
        if (configuration is None) == (copy_from_profile_id is None):
            raise ValueError("provide exactly one of configuration or copy_from_profile_id")
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
    ) -> TextProviderProfile:
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
            if row.display_name == normalized_name and current_without_version == proposed_without_version:
                return self._text_provider_profile(row)
            row.revision += 1
            row.display_name = normalized_name
            row.settings = proposed.model_dump(mode="json", by_alias=True)
            row.updated_at = utc_now()
            return self._text_provider_profile(row)

    def activate_text_provider_profile(
        self,
        profile_id: str,
        expected_selection_revision: int,
    ) -> ProviderProfileSelection:
        with self._write() as session:
            if session.get(TextProviderProfileRow, profile_id) is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
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
