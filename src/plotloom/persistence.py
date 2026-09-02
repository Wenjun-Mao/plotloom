from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    select,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from .domain import (
    STAGE_ORDER,
    TERMINAL_MEDIA_TASK_STATUSES,
    TERMINAL_RUN_STATUSES,
    Artifact,
    ArtifactKind,
    AttemptStatus,
    CanonicalSnapshot,
    EntityRevision,
    GenerationAttempt,
    GenerationRun,
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
    downstream_stages,
    stage_payload_model,
    upstream_stages,
    validate_initial_stage_prefix,
    utc_now,
    validate_public_provider_snapshot,
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
    result_revision_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GenerationAttemptRow(Base):
    __tablename__ = "v2_generation_attempts"
    __table_args__ = (UniqueConstraint("run_id", "stage", "attempt_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArtifactRow(Base):
    __tablename__ = "v2_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[Any] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
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
                if file_database:
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.fetchone()
                cursor.close()

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
            result_revision_ids=list(row.result_revision_ids),
            error=row.error,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )

    @staticmethod
    def _attempt(row: GenerationAttemptRow) -> GenerationAttempt:
        return GenerationAttempt(
            id=row.id,
            run_id=row.run_id,
            stage=StageName(row.stage),
            attempt_number=row.attempt_number,
            status=AttemptStatus(row.status),
            provider=row.provider,
            model=row.model,
            error=row.error,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )

    @staticmethod
    def _artifact(row: ArtifactRow) -> Artifact:
        return Artifact(
            id=row.id,
            run_id=row.run_id,
            attempt_id=row.attempt_id,
            source_artifact_id=row.source_artifact_id,
            stage=StageName(row.stage) if row.stage else None,
            kind=ArtifactKind(row.kind),
            media_type=row.media_type,
            content=row.content,
            content_hash=row.content_hash,
            created_at=row.created_at,
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
                    result_revision_ids=[],
                    error=None,
                    created_at=run.created_at,
                    started_at=None,
                    finished_at=None,
                )
            )
            return run

    def get_run(self, run_id: str) -> GenerationRun:
        with self._read() as session:
            return self._run(self._run_row(session, run_id))

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

        Generation provider calls are not assumed idempotent, so only pristine
        queued runs are resubmitted. Running generation is terminated and its
        open attempts are closed. Media polling is safe to resume only after a
        provider task ID was durably recorded.
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
                running_attempts = [
                    attempt
                    for attempt in attempts
                    if AttemptStatus(attempt.status) == AttemptStatus.RUNNING
                ]
                status = RunStatus(row.status)
                pristine_queue = (
                    status == RunStatus.QUEUED
                    and row.started_at is None
                    and not row.result_revision_ids
                    and not attempts
                )
                if pristine_queue:
                    resubmit_run_ids.append(row.id)
                    continue

                if status == RunStatus.CANCEL_REQUESTED:
                    row.status = RunStatus.CANCELLED.value
                    row.error = None
                    attempt_status = AttemptStatus.CANCELLED
                    attempt_error = "Generation attempt cancelled during startup recovery"
                else:
                    row.status = RunStatus.FAILED.value
                    row.error = interrupted_run_error
                    row.started_at = row.started_at or now
                    attempt_status = AttemptStatus.FAILED
                    attempt_error = interrupted_run_error
                row.finished_at = now
                for attempt in running_attempts:
                    attempt.status = attempt_status.value
                    attempt.error = attempt_error
                    attempt.finished_at = now
                terminated_run_ids.append(row.id)

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
            if RunStatus(run_row.status) != RunStatus.RUNNING:
                raise InvalidTransitionError(f"cannot install generated output while run is {run_row.status}")
            requested = [StageName(value) for value in run_row.requested_stages]
            if set(parsed_payloads) != set(requested):
                raise InvalidTransitionError(
                    "commit_run_outputs requires exactly one candidate for every requested stage"
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
                    run_id=run_id,
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
            elif status != RunStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish run from {status.value}")
            elif error is not None:
                row.status = RunStatus.FAILED.value
                row.error = error
            elif quarantine_reason is not None:
                row.status = RunStatus.QUARANTINED.value
                row.error = quarantine_reason
            else:
                row.status = (
                    RunStatus.SUCCEEDED.value
                    if self._run_outputs_are_current(session, row)
                    else RunStatus.QUARANTINED.value
                )
                if row.status == RunStatus.QUARANTINED.value:
                    row.error = "canonical inputs changed or requested outputs were not installed"
            row.finished_at = utc_now()
            return self._run(row)

    def cancel_run(self, run_id: str) -> GenerationRun:
        with self._write() as session:
            row = self._run_row(session, run_id)
            status = RunStatus(row.status)
            if status == RunStatus.QUEUED:
                row.status = RunStatus.CANCELLED.value
                row.finished_at = utc_now()
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
                    status=attempt.status.value,
                    provider=provider,
                    model=model,
                    error=None,
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
    ) -> GenerationAttempt:
        if status == AttemptStatus.RUNNING:
            raise InvalidTransitionError("finish_attempt requires a terminal attempt status")
        with self._write() as session:
            row = session.get(GenerationAttemptRow, attempt_id)
            if row is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            if AttemptStatus(row.status) != AttemptStatus.RUNNING:
                raise InvalidTransitionError(f"cannot finish attempt from {row.status}")
            row.status = status.value
            row.error = error
            row.finished_at = utc_now()
            return self._attempt(row)

    def add_artifact(self, artifact: Artifact) -> Artifact:
        with self._write() as session:
            self._run_row(session, artifact.run_id)
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
            data.update(revision=row.revision, updated_at=row.updated_at)
            return ProviderSettings.model_validate(data)

    def put_provider_settings(self, settings: ProviderSettings) -> ProviderSettings:
        # ProviderSettings.extra=forbid is the security boundary: secret-shaped fields cannot enter storage.
        now = utc_now()
        data = settings.model_dump(
            mode="json",
            by_alias=False,
            exclude={
                "revision",
                "updated_at",
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
            result.update(revision=row.revision, updated_at=row.updated_at)
            return ProviderSettings.model_validate(result)
