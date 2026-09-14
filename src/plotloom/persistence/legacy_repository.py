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

from ..domain import (
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
from ..generation.aggregation import aggregate_stage_fragments
from ..generation.dialogue_capacity import DIALOGUE_CAPACITY_POLICY_VERSION
from ..generation.fragments import (
    SceneBeatsFragment,
    StoryBibleFragment,
    StoryGraphFragment,
    StoryboardFragment,
)
from ..generation.planning import (
    DEFAULT_STAGE_BUDGETS,
    GenerationPlan,
    PLANNING_POLICY_VERSION,
    PlanningError,
    StageBudget,
    StagePlan,
    create_generation_plan,
    plan_stage,
)
from ..generation.scene_timing_allocation import (
    SCENE_TIMING_ALLOCATION_VERSION,
    SceneTimingAllocation,
)
from ..join_state_values import JOIN_STATE_VALUE_CONTRACT_VERSION
from ..keyframe_preparation import has_matching_aspect
from ..video_provider import VideoProductionContract
from ..generation.story_graph_topology import (
    StoryGraphTopology,
    plan_story_graph_topology,
)
from ..generation.prompts import canonical_json
from ..provider_profiles import (
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
from ..exceptions import (
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
from ..image_job_contracts import ImageJobError

from .codec import _contains_unredacted_secret_setting, _json_data, _stored_utc, stable_hash
from .project.approvals import ApprovalClosure, ApprovalDecision, ProjectApprovalPersistence
from .project.canonical import ProjectCanonicalPersistence
from .project.catalog import ProjectCatalogPersistence
from .project.constants import CURRENT_STAGE_SCHEMA_VERSION, LEGACY_STAGE_SCHEMA_VERSION
from .project.drafts import ProjectDraftPersistence
from .project.gates import ProjectGatePersistence
from .project.generation_snapshots import ProjectGenerationSnapshots
from .project.generation_plans import ProjectGenerationPlanningPersistence
from .project.generation_attempts import ProjectGenerationAttemptPersistence
from .project.generation_reuse import ProjectGenerationReusePersistence
from .project.generation_aggregates import ProjectGenerationAggregatePersistence
from .project.generation_progress import ProjectGenerationProgressPersistence
from .project.generation_repairs import ProjectGenerationRepairPersistence
from .project.generation_recovery import ProjectGenerationRecoveryPersistence
from .project.generation_lifecycle import ProjectGenerationLifecyclePersistence
from .project.generation_evidence import ProjectGenerationEvidencePersistence
from .project.lifecycle import ProjectLifecyclePersistence
from .project.workflow import ProjectAuthoringWorkflow
from .database import RepositoryDatabase
from .schema import (
    ApprovalDecisionRow, ArtifactRow, AuthoringDraftRow, Base, CharacterReferenceDecisionRow,
    CharacterReferenceProposalCandidateRow, CharacterReferenceProposalDeliveryRow, CharacterReferenceProposalRow,
    CharacterReferenceStateRow, EntityRevisionRow, FragmentReuseBindingRow, GateResultRow, GenerationAttemptRow,
    GenerationPlanRow, GenerationRunRow, GenerationWorkUnitRow, ImageJobCandidateRow, ImageJobDeliveryRow, ImageJobRow,
    ManagedAssetProvenanceRow, ManagedAssetRow, MediaTaskRow, PROJECT_TEXT_PIPELINE_TABLE_NAMES, ProductionUnitRow,
    ProjectCreationIdempotencyRow, ProjectDuplicateIdempotencyRow, ProjectRow, ProviderProfileSelectionRow,
    ProviderSettingsRow, ReviewedShotBindingRow, SamePersonReviewRow, SamePersonReviewStateRow, SealedStageAggregateRow,
    StageHeadRow, StagePlanRow, StillPreviewRow, StoryGraphTopologyRow, TextProviderProfileRow, VideoJobRow,
    VideoPilotLedgerEventRow, VideoPilotLedgerRow, VideoReviewRow, VisualIntentRow, VisualSelectionStateRow,
    WorkUnitRepairIdempotencyRow, WorkUnitRepairScopeRow,
)
from .transactions import bootstrap_lease, lifecycle_lease, read_lease, work_unit_claim_lease, write_lease
from ..validation import STORYBOARD_GATE_SET_VERSION, validate_stage_payload





class SQLiteRepository:
    """Transactional canonical store with immutable entity revisions and mutable heads."""

    def __init__(self, database_url: str = "sqlite://", *, create_schema: bool = True, sqlite_busy_timeout_ms: int = 1_000, schema_scope: Literal["full", "project"] = "full") -> None:
        if sqlite_busy_timeout_ms < 1:
            raise ValueError("sqlite_busy_timeout_ms must be at least 1")
        if schema_scope not in {"full", "project"}:
            raise ValueError("schema_scope must be 'full' or 'project'")
        self._sqlite_busy_timeout_ms = sqlite_busy_timeout_ms
        self._bootstrap_retry_after_seconds = max(1, (sqlite_busy_timeout_ms + 999) // 1_000)
        self._schema_scope = schema_scope
        self._database = RepositoryDatabase(database_url, create_schema=create_schema, schema_tables=self._schema_tables(), schema_scope=schema_scope, sqlite_busy_timeout_ms=sqlite_busy_timeout_ms)
        self.engine = self._database.engine
        self._sessions = self._database.sessions
        self._write_lock = self._database.write_lock
        self._catalog = ProjectCatalogPersistence(self)
        self._lifecycle = ProjectLifecyclePersistence(self)
        self._drafts = ProjectDraftPersistence(self)
        self._gates = ProjectGatePersistence(self)
        self._approvals = ProjectApprovalPersistence(self)
        self._canonical = ProjectCanonicalPersistence(self)
        self._workflow = ProjectAuthoringWorkflow(self)
        self._generation_snapshots = ProjectGenerationSnapshots(self)
        self._generation_plans = ProjectGenerationPlanningPersistence(self)
        self._generation_attempts = ProjectGenerationAttemptPersistence(self)
        self._generation_reuse = ProjectGenerationReusePersistence(self)
        self._generation_aggregates = ProjectGenerationAggregatePersistence(self)
        self._generation_progress = ProjectGenerationProgressPersistence(self)
        self._generation_repairs = ProjectGenerationRepairPersistence(self)
        self._generation_recovery = ProjectGenerationRecoveryPersistence(self)
        self._generation_lifecycle = ProjectGenerationLifecyclePersistence(self)
        self._generation_evidence = ProjectGenerationEvidencePersistence(self)

    def _schema_tables(self) -> list[Any]:
        if self._schema_scope == "full":
            return list(Base.metadata.sorted_tables)
        return [table for table in Base.metadata.sorted_tables if table.name in PROJECT_TEXT_PIPELINE_TABLE_NAMES]

    def close(self) -> None:
        self._database.close()

    @contextmanager
    def _read(self) -> Iterator[Session]:
        with read_lease(self._sessions) as session:
            yield session

    @contextmanager
    def _write(self) -> Iterator[Session]:
        with write_lease(self._sessions, self._write_lock) as session:
            yield session

    @contextmanager
    def _bootstrap_write(self) -> Iterator[Session]:
        with bootstrap_lease(self._sessions, self._write_lock, retry_after_seconds=self._bootstrap_retry_after_seconds, is_contention=self._is_sqlite_lock_contention) as session:
            yield session

    @contextmanager
    def _lifecycle_write(self) -> Iterator[Session]:
        with lifecycle_lease(self._sessions, self._write_lock, dialect_name=self.engine.dialect.name, retry_after_seconds=self._bootstrap_retry_after_seconds, is_contention=self._is_sqlite_lock_contention) as session:
            yield session

    @contextmanager
    def _work_unit_claim_write(self) -> Iterator[Session]:
        with work_unit_claim_lease(self._sessions, self._write_lock, is_contention=self._is_sqlite_lock_contention) as session:
            yield session

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
        return ProjectCatalogPersistence._creation_fingerprint(brief, stages)

    def _create_project_row_in_session(
        self,
        session: Session,
        brief: ProjectBrief,
        now: datetime,
    ) -> ProjectRow:
        return self._catalog._create_project_row_in_session(session, brief, now)

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
        return self._catalog._stage_envelopes_in_session(session, project_id)

    def _project_creation_in_session(self, session: Session, project_row: ProjectRow) -> ProjectCreation:
        return self._catalog._project_creation_in_session(session, project_row)

    def create_project(
        self,
        brief: ProjectBrief,
        *,
        initial_stages: Sequence[InitialStage | dict[str, Any]] = (),
        idempotency_key: str | None = None,
    ) -> ProjectCreation:
        return self._catalog.create_project(brief, initial_stages=initial_stages, idempotency_key=idempotency_key)

    def get_project(self, project_id: str) -> Project:
        return self._catalog.get_project(project_id)

    def list_projects(
        self,
        *,
        lifecycle_status: ProjectLifecycleStatus | None = ProjectLifecycleStatus.ACTIVE,
        limit: int = 50,
        cursor: tuple[datetime, str] | None = None,
    ) -> tuple[list[ProjectSummary], tuple[datetime, str] | None]:
        return self._catalog.list_projects(lifecycle_status=lifecycle_status, limit=limit, cursor=cursor)

    def archive_project(self, project_id: str, expected_lifecycle_revision: int) -> Project:
        return self._lifecycle.archive_project(project_id, expected_lifecycle_revision)

    def restore_project(self, project_id: str, expected_lifecycle_revision: int) -> Project:
        return self._lifecycle.restore_project(project_id, expected_lifecycle_revision)

    @staticmethod
    def _duplicate_fingerprint(
        project_id: str,
        expected_lifecycle_revision: int,
        title: str | None,
    ) -> str:
        return ProjectCatalogPersistence._duplicate_fingerprint(project_id, expected_lifecycle_revision, title)

    def _duplicate_result_in_session(
        self,
        session: Session,
        project_id: str,
        copied_through: str | None,
        omitted_stages: Sequence[str],
    ) -> ProjectDuplicateResult:
        return self._catalog._duplicate_result_in_session(session, project_id, copied_through, omitted_stages)

    def duplicate_project(
        self,
        project_id: str,
        expected_lifecycle_revision: int,
        *,
        title: str | None = None,
        idempotency_key: str | None = None,
    ) -> ProjectDuplicateResult:
        return self._catalog.duplicate_project(project_id, expected_lifecycle_revision, title=title, idempotency_key=idempotency_key)

    def permanent_delete_project(
        self,
        project_id: str,
        expected_lifecycle_revision: int,
        confirmation_title: str,
    ) -> None:
        return self._lifecycle.permanent_delete_project(project_id, expected_lifecycle_revision, confirmation_title)

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
        return self._drafts.update_project(project_id, expected_revision, brief)

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
        return self._drafts._consume_exact_authoring_draft_in_session(session, project, editor_scope=editor_scope, entity_id=entity_id, expected_draft_revision=expected_draft_revision, canonical_base_revision=canonical_base_revision, canonical_payload=canonical_payload)

    def update_project_consuming_authoring_draft(
        self,
        project_id: str,
        expected_revision: int,
        brief: ProjectBrief,
        *,
        entity_id: str,
        expected_draft_revision: int,
    ) -> Project:
        return self._drafts.update_project_consuming_authoring_draft(project_id, expected_revision, brief, entity_id=entity_id, expected_draft_revision=expected_draft_revision)

    @staticmethod
    def _authoring_draft(row: AuthoringDraftRow) -> AuthoringDraft:
        return ProjectDraftPersistence._authoring_draft(row)

    @staticmethod
    def _validate_authoring_draft_payload(
        editor_scope: AuthoringDraftScope,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return ProjectDraftPersistence._validate_authoring_draft_payload(editor_scope, payload)

    def _authoring_draft_base_revision(
        self,
        session: Session,
        project: ProjectRow,
        editor_scope: AuthoringDraftScope,
    ) -> int:
        return self._drafts._authoring_draft_base_revision(session, project, editor_scope)

    def list_authoring_drafts(self, project_id: str) -> list[AuthoringDraft]:
        return self._drafts.list_authoring_drafts(project_id)

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
        return self._drafts.upsert_authoring_draft(project_id, editor_scope=editor_scope, entity_id=entity_id, base_canonical_revision=base_canonical_revision, expected_draft_revision=expected_draft_revision, payload=payload)

    def discard_authoring_draft(
        self,
        project_id: str,
        *,
        editor_scope: AuthoringDraftScope,
        entity_id: str,
        expected_draft_revision: int,
    ) -> bool:
        return self._drafts.discard_authoring_draft(project_id, editor_scope=editor_scope, entity_id=entity_id, expected_draft_revision=expected_draft_revision)

    def list_stage_heads(self, project_id: str) -> list[StageHead]:
        return self._gates.list_stage_heads(project_id)

    def list_stage_envelopes(self, project_id: str) -> list[StageEnvelope]:
        return self._gates.list_stage_envelopes(project_id)

    def get_stage_head(self, project_id: str, stage: StageName) -> StageHead:
        return self._gates.get_stage_head(project_id, stage)

    def get_entity_revision(self, revision_id: str) -> EntityRevision:
        return self._gates.get_entity_revision(revision_id)

    def record_gate_evaluation(
        self,
        project_id: str,
        entity_revision_id: str,
        evaluation: GateEvaluation,
    ) -> GateEvaluation:
        return self._gates.record_gate_evaluation(project_id, entity_revision_id, evaluation)

    def _evaluate_storyboard_revision_in_session(
        self,
        session: Session,
        project: ProjectRow,
        storyboard_revision: EntityRevisionRow,
    ) -> GateEvaluation:
        return self._gates._evaluate_storyboard_revision_in_session(session, project, storyboard_revision)

    def _record_gate_evaluation_in_session(
        self,
        session: Session,
        project_id: str,
        revision: EntityRevisionRow,
        evaluation: GateEvaluation,
        *,
        now: datetime,
    ) -> GateEvaluation:
        return self._gates._record_gate_evaluation_in_session(session, project_id, revision, evaluation, now=now)

    def get_gate_evaluation(
        self,
        entity_revision_id: str,
        gate_set_version: str,
    ) -> GateEvaluation:
        return self._gates.get_gate_evaluation(entity_revision_id, gate_set_version)

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
        return self._approvals.append_approval_decision(project_id, entity_revision_id, decision=decision, reviewer=reviewer, gate_set_version=gate_set_version, note=note, subject_type=subject_type, subject_id=subject_id)

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
        return self._approvals.decide_storyboard_approval(project_id, expected_revision=expected_revision, expected_content_hash=expected_content_hash, decision=decision, reviewer=reviewer, gate_set_version=gate_set_version, note=note)

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
        return self._approvals._append_approval_decision_in_session(session, project_id, revision, decision=decision, reviewer=reviewer, gate_set_version=gate_set_version, note=note, subject_type=subject_type, subject_id=subject_id)

    def approve_storyboard(
        self,
        project_id: str,
        entity_revision_id: str,
        *,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
    ) -> ApprovalDecision:
        return self._approvals.approve_storyboard(project_id, entity_revision_id, reviewer=reviewer, gate_set_version=gate_set_version, note=note)

    def revoke_storyboard_approval(
        self,
        project_id: str,
        entity_revision_id: str,
        *,
        reviewer: str,
        gate_set_version: str,
        note: str | None = None,
    ) -> ApprovalDecision:
        return self._approvals.revoke_storyboard_approval(project_id, entity_revision_id, reviewer=reviewer, gate_set_version=gate_set_version, note=note)

    def list_approval_decisions(self, project_id: str) -> list[ApprovalDecision]:
        return self._approvals.list_approval_decisions(project_id)

    def get_approval_closure(self, decision_id: str) -> ApprovalClosure:
        return self._approvals.get_approval_closure(decision_id)

    def approval_is_revoked(self, decision_id: str) -> bool:
        return self._approvals.approval_is_revoked(decision_id)

    def _load_stage_payload(self, session: Session, project_id: str, stage: StageName) -> StagePayload:
        return self._canonical._load_stage_payload(session, project_id, stage)

    def get_stage_payload(self, project_id: str, stage: StageName) -> StagePayload:
        return self._canonical.get_stage_payload(project_id, stage)

    def _mark_downstream_stale(self, session: Session, project_id: str, stage: StageName, now: datetime) -> None:
        return self._canonical._mark_downstream_stale(session, project_id, stage, now)

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
        return self._canonical._install_stage_in_session(session, project_row, stage, payload, expected_revision=expected_revision, now=now, allow_noop=allow_noop, dialogue_timing_profile=dialogue_timing_profile)

    def update_stage(
        self,
        project_id: str,
        stage: StageName,
        expected_revision: int,
        payload: StagePayload | dict[str, Any],
    ) -> StageHead:
        return self._canonical.update_stage(project_id, stage, expected_revision, payload)

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
        return self._workflow.update_stage_consuming_authoring_draft(project_id, stage, expected_revision, payload, entity_id=entity_id, expected_draft_revision=expected_draft_revision)

    @staticmethod
    def _snapshot_fingerprint(
        project_revision: int,
        brief: ProjectBrief,
        heads: Sequence[StageHead],
    ) -> dict[str, Any]:
        return ProjectGenerationSnapshots.snapshot_fingerprint(project_revision, brief, heads)

    def _snapshot_in_session(self, session: Session, project_id: str) -> CanonicalSnapshot:
        return self._generation_snapshots.snapshot_in_session(session, project_id)

    def capture_snapshot(self, project_id: str) -> CanonicalSnapshot:
        return self._generation_snapshots.capture_snapshot(project_id)

    def snapshot_is_current(self, snapshot: CanonicalSnapshot) -> bool:
        return self._generation_snapshots.snapshot_is_current(snapshot)

    @staticmethod
    def _relevant_input_stages(requested: Sequence[StageName]) -> set[StageName]:
        return ProjectGenerationSnapshots.relevant_input_stages(requested)

    def _assert_run_inputs_current_in_session(
        self,
        session: Session,
        row: GenerationRunRow,
    ) -> CanonicalSnapshot:
        return self._generation_snapshots.assert_run_inputs_current_in_session(session, row)

    def assert_run_inputs_current(self, run_id: str) -> CanonicalSnapshot:
        return self._generation_snapshots.assert_run_inputs_current(run_id)

    def get_snapshot_stage_payload(self, run_id: str, stage: StageName) -> StagePayload:
        """Read immutable upstream facts by the run snapshot, never a mutable head.

        Snapshot reads are historical evidence, rather than live authoring
        inputs.  A pre-0010 snapshot has no embedded schemaVersion and the
        ``StageHead`` compatibility default intentionally classifies it as V1.
        Decode it with that frozen version; using the live-only decoder here
        would both make historical runs unreadable and invite callers to infer
        V2 semantics from absent V1 fields.
        """

        return self._generation_snapshots.get_snapshot_stage_payload(run_id, stage)

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

        return self._generation_snapshots.run_plan_inputs_in_session(session, snapshot, requested_stages)

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
        return self._generation_snapshots.create_run(
            project_id, kind, requested_stages, instructions=instructions,
            parent_run_id=parent_run_id, repair_stage=repair_stage,
            repair_source=repair_source, provider_snapshot=provider_snapshot,
        )

    def get_run(self, run_id: str) -> GenerationRun:
        return self._generation_snapshots.get_run(run_id)

    def get_generation_plan(self, run_id: str) -> GenerationPlan:
        """Return the immutable enqueue-time plan for a non-legacy run."""

        return self._generation_snapshots.get_generation_plan(run_id)

    def get_story_graph_topology(self, run_id: str) -> StoryGraphTopology | None:
        """Return the immutable topology for a run that generates Story Graph."""

        return self._generation_snapshots.get_story_graph_topology(run_id)

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
        return self._generation_repairs.get_repair_stage_dependencies(child_run_id, stage)

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
        return self._generation_plans.get_or_create_stage_plan(run_id, stage, dependencies=dependencies)

    def get_or_create_repair_stage_plan(
        self,
        child_run_id: str,
        stage: StageName,
        *,
        dependencies: dict[StageName, StagePayload] | None = None,
    ) -> StagePlan:
        return self._generation_plans.get_or_create_repair_stage_plan(child_run_id, stage, dependencies=dependencies)

    def list_stage_plans(self, run_id: str) -> list[StagePlan]:
        return self._generation_plans.list_stage_plans(run_id)

    def list_generation_work_units(self, run_id: str) -> list[GenerationWorkUnitTrace]:
        return self._generation_plans.list_generation_work_units(run_id)

    def get_fragment_reuse_bindings(self, child_run_id: str) -> list[FragmentReuseBinding]:
        return self._generation_reuse.get_fragment_reuse_bindings(child_run_id)

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
        return self._generation_reuse.prepare_repair_stage_reuse(child_run_id, stage)

    def materialize_fragment_reuse_binding(
        self,
        child_run_id: str,
        binding_id: str,
    ) -> Artifact:
        return self._generation_reuse.materialize_fragment_reuse_binding(child_run_id, binding_id)

    def materialize_reused_fragment(self, child_run_id: str, binding_id: str) -> Artifact:
        return self._generation_reuse.materialize_reused_fragment(child_run_id, binding_id)

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
        return self._generation_attempts.allocate_attempt_for_work_unit(work_unit_id, provider=provider, model=model, attempt_kind=attempt_kind, source_attempt_id=source_attempt_id, max_attempts=max_attempts)

    def get_recoverable_attempt_for_work_unit(
        self,
        work_unit_id: str,
    ) -> GenerationAttempt | None:
        return self._generation_attempts.get_recoverable_attempt_for_work_unit(work_unit_id)

    def mark_attempt_dispatched(self, attempt_id: str) -> GenerationAttempt:
        return self._generation_attempts.mark_attempt_dispatched(attempt_id)

    def persist_attempt_response(
        self,
        attempt_id: str,
        content: Any,
        *,
        provider_request_id: str | None = None,
    ) -> Artifact:
        return self._generation_attempts.persist_attempt_response(attempt_id, content, provider_request_id=provider_request_id)

    def mark_attempt_outcome_unknown(self, attempt_id: str, *, error: str) -> GenerationAttempt:
        return self._generation_attempts.mark_attempt_outcome_unknown(attempt_id, error=error)

    def get_run_execution_trace(self, run_id: str) -> RunExecutionTrace:
        return self._generation_progress.get_run_execution_trace(run_id)

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
        return self._generation_progress.get_run_progress(run_id)

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
        return self._generation_aggregates.seal_stage_aggregate(run_id, stage, candidate_artifact_ids=candidate_artifact_ids)

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
        return self._generation_aggregates.seal_repair_stage_aggregate(child_run_id, stage, candidate_artifact_ids=candidate_artifact_ids)

    def list_project_runs(self, project_id: str, *, limit: int = 50) -> list[GenerationRun]:
        return self._generation_lifecycle.list_project_runs(project_id, limit=limit)

    def reconcile_startup_jobs(self) -> StartupRecoveryPlan:
        return self._generation_recovery.reconcile_startup_jobs()

    def start_run(self, run_id: str) -> GenerationRun:
        return self._generation_lifecycle.start_run(run_id)

    def install_generated_stage(
        self,
        run_id: str,
        stage: StageName,
        payload: StagePayload | dict[str, Any],
    ) -> StageHead:
        return self._generation_lifecycle.install_generated_stage(run_id, stage, payload)

    def install_generated_stages(
        self,
        run_id: str,
        payloads: dict[StageName, StagePayload | dict[str, Any]],
    ) -> list[StageHead]:
        return self._generation_lifecycle.install_generated_stages(run_id, payloads)

    def commit_run_outputs(
        self,
        run_id: str,
        payloads: dict[StageName, StagePayload | dict[str, Any]],
    ) -> GenerationRun:
        return self._generation_lifecycle.commit_run_outputs(run_id, payloads)

    def commit_sealed_run(
        self,
        run_id: str,
        *,
        sealed_aggregate_ids: list[str],
    ) -> GenerationRun:
        return self._generation_lifecycle.commit_sealed_run(run_id, sealed_aggregate_ids=sealed_aggregate_ids)

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
        return self._generation_lifecycle.finish_run(run_id, result_revision_ids=result_revision_ids, error=error, quarantine_reason=quarantine_reason, failure_code=failure_code, failed_stage=failed_stage)

    def cancel_run(self, run_id: str) -> GenerationRun:
        return self._generation_lifecycle.cancel_run(run_id)

    def create_repair_run(
        self,
        source_run_id: str,
        *,
        stage: StageName | None = None,
        instructions: str | None = None,
        provider_snapshot: dict[str, Any] | None = None,
    ) -> GenerationRun:
        return self._generation_repairs.create_repair_run(source_run_id, stage=stage, instructions=instructions, provider_snapshot=provider_snapshot)

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
        return self._generation_repairs.get_repair_eligible_work_units(run_id)

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
        return self._generation_repairs.create_work_unit_repair_run(source_run_id, work_unit_id, idempotency_key=idempotency_key, instructions=instructions)

    def get_work_unit_repair_scope(self, child_run_id: str) -> WorkUnitRepairScope:
        return self._generation_repairs.get_work_unit_repair_scope(child_run_id)

    def create_attempt(
        self,
        run_id: str,
        stage: StageName,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> GenerationAttempt:
        return self._generation_evidence.create_attempt(run_id, stage, provider=provider, model=model)

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
        return self._generation_evidence.finish_attempt(attempt_id, status, error=error, outcome_code=outcome_code, allow_correction=allow_correction, failure_disposition=failure_disposition)

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
        return self._generation_evidence.add_artifact(artifact)

    def get_artifact(self, artifact_id: str) -> Artifact:
        return self._generation_evidence.get_artifact(artifact_id)

    def get_run_trace(self, run_id: str) -> RunTrace:
        return self._generation_evidence.get_run_trace(run_id)

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
