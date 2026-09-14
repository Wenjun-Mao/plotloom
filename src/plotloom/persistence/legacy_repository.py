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
from ..generation.planning import (
    GenerationPlan,
    StagePlan,
)
from ..keyframe_preparation import has_matching_aspect
from ..video_provider import VideoProductionContract
from ..generation.story_graph_topology import (
    StoryGraphTopology,
)
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
from .project.generation_integrity import GenerationWorkUnitIntegrity
from .project.generation_repair_eligibility import GenerationRepairEligibility
from .project.generation_repair_scope import GenerationRepairScopePolicy
from .project.generation_access import (
    GenerationAdmission, GenerationCodecs, GenerationLeases,
    GenerationPersistenceAccess, GenerationRows,
)
from .project.lifecycle import ProjectLifecyclePersistence
from .project.workflow import ProjectAuthoringWorkflow
from .project.media import ProjectMediaPersistence
from .project.media_admission import KeyframeAdmission
from .project.media_assets import ManagedAssetPersistence
from .project.media_character_references import CharacterReferencePersistence
from .project.media_image_currentness import ImageJobCurrentness
from .project.media_image_delivery import ImageJobDeliveryPersistence
from .project.media_reference_proposals import CharacterReferenceProposalPersistence
from .project.media_same_person_reviews import SamePersonReviewPersistence
from .project.media_tasks import GenericMediaTaskPersistence
from .project.media_video_currentness import VideoJobCurrentness
from .project.access import (
    ProjectCodecs, ProjectGuards, ProjectLeases, ProjectPersistenceAccess, ProjectRows,
)
from .application.profiles import ApplicationControlAccess, ApplicationProfilePersistence
from .application.accounting import VideoPilotAccounting
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
        self._project_access = ProjectPersistenceAccess(
            leases=ProjectLeases(
                read=self._read, write=self._write, bootstrap_write=self._bootstrap_write,
                lifecycle_write=self._lifecycle_write, work_unit_claim_write=self._work_unit_claim_write,
            ),
            rows=ProjectRows(
                project=self._project_row, stage=self._stage_row, run=self._run_row,
                media_task=self._media_task_row,
            ),
            codecs=ProjectCodecs(
                project=self._project, latest_run_summary=self._latest_run_summary,
                stage_head=self._stage_head, entity_revision=self._entity_revision,
                decode_current_stage_payload=self._decode_current_stage_payload,
                gate_result=self._gate_result, approval_decision=self._approval_decision,
            ),
            guards=ProjectGuards(
                active=self._assert_active_project,
                lifecycle_revision=self._assert_lifecycle_revision,
                busy=self._project_is_busy_in_session,
            ),
        )
        self._catalog = ProjectCatalogPersistence(self._project_access)
        self._lifecycle = ProjectLifecyclePersistence(self._project_access)
        self._gates = ProjectGatePersistence(self._project_access, self._catalog)
        self._approvals = ProjectApprovalPersistence(self._project_access)
        self._canonical = ProjectCanonicalPersistence(self._project_access, self._gates)
        self._catalog.bind_canonical(self._canonical)
        self._drafts = ProjectDraftPersistence(self._project_access, self._canonical)
        self._workflow = ProjectAuthoringWorkflow(self._project_access, self._drafts, self._canonical)
        self._application_control_access = ApplicationControlAccess(read=self._read, write=self._write)
        self._application_profiles = ApplicationProfilePersistence(self._application_control_access)
        self._video_accounting = VideoPilotAccounting(self._application_control_access)
        self._media = ProjectMediaPersistence(
            self._project_access, self._canonical, self._drafts, self._video_accounting
        )
        self._generation_access = GenerationPersistenceAccess(
            leases=GenerationLeases(
                read=self._read,
                write=self._write,
                lifecycle_write=self._lifecycle_write,
                work_unit_claim_write=self._work_unit_claim_write,
            ),
            rows=GenerationRows(project=self._project_row, run=self._run_row, stage=self._stage_row),
            codecs=GenerationCodecs(
                project=self._project,
                run=self._run,
                attempt=self._attempt,
                artifact=self._artifact,
                stage_head=self._stage_head,
                stage_plan_trace=self._stage_plan_trace,
                work_unit_trace=self._work_unit_trace,
                generation_plan_trace=self._generation_plan_trace,
                topology_trace=self._story_graph_topology_trace,
                sealed_aggregate_trace=self._sealed_aggregate_trace,
                repair_scope=self._repair_scope,
                reuse_binding=self._fragment_reuse_binding,
                decode_stage_payload=self._decode_stage_payload,
                decode_current_stage_payload=self._decode_current_stage_payload,
            ),
            admission=GenerationAdmission(
                assert_active_project=self._assert_active_project,
                assert_new_run_profile_enabled=self._assert_new_run_profile_enabled,
            ),
        )
        self._generation_snapshots = ProjectGenerationSnapshots(self._generation_access)
        self._generation_plans = ProjectGenerationPlanningPersistence(self._generation_access)
        self._generation_integrity = GenerationWorkUnitIntegrity()
        self._generation_repair_eligibility = GenerationRepairEligibility(
            self._generation_access, self._generation_plans, self._generation_integrity,
            self._generation_snapshots,
        )
        self._generation_repair_scope = GenerationRepairScopePolicy(
            self._generation_access, self._generation_plans, self._generation_integrity,
            self._generation_repair_eligibility,
        )
        self._generation_plans.bind_repair_scope(self._generation_repair_scope)
        self._generation_attempts = ProjectGenerationAttemptPersistence(
            self._generation_access, self._generation_integrity
        )
        self._generation_reuse = ProjectGenerationReusePersistence(
            self._generation_access, self._generation_plans, self._generation_integrity,
            self._generation_repair_scope
        )
        self._generation_aggregates = ProjectGenerationAggregatePersistence(
            self._generation_access, self._generation_plans, self._generation_integrity,
            self._generation_repair_scope
        )
        self._generation_evidence = ProjectGenerationEvidencePersistence(
            self._generation_access, self._generation_integrity, self._generation_snapshots
        )
        self._generation_repairs = ProjectGenerationRepairPersistence(
            self._generation_access, self._generation_plans, self._generation_repair_scope,
            self._generation_repair_eligibility, self._generation_snapshots,
            self._generation_evidence,
        )
        self._generation_progress = ProjectGenerationProgressPersistence(
            self._generation_access, self._generation_repair_eligibility,
            self._generation_integrity,
        )
        self._generation_recovery = ProjectGenerationRecoveryPersistence(
            self._generation_access, self._generation_plans
        )
        self._generation_lifecycle = ProjectGenerationLifecyclePersistence(
            self._generation_access, self._generation_snapshots, self._canonical
        )

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
            or stable_hash(
                {key: value for key, value in row.scope.items() if key != "scopeHash"}
            ) != row.scope_hash
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
        return ApplicationProfilePersistence._text_provider_profile(row)

    @staticmethod
    def _provider_profile_selection(
        row: ProviderProfileSelectionRow,
    ) -> ProviderProfileSelection:
        return ApplicationProfilePersistence._provider_profile_selection(row)

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
        return GenericMediaTaskPersistence.media_task(row)

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
        return ManagedAssetPersistence.managed_asset_dict(row)
    def record_managed_import(self, project_id: str, *, original_hash: str, display_hash: str, mime_type: str, byte_size: int, width: int, height: int, declaration: dict[str, Any], publish: Callable[[], tuple[str, str]]) -> dict[str, Any]:
        return self._media.assets.record_managed_import(project_id, original_hash=original_hash, display_hash=display_hash, mime_type=mime_type, byte_size=byte_size, width=width, height=height, declaration=declaration, publish=publish)
    def get_managed_asset_storage(self, project_id: str, asset_id: str) -> dict[str, Any]:
        return self._media.assets.get_managed_asset_storage(project_id, asset_id)
    def reviewed_keyframe_crop_source(self, project_id: str, *, binding_id: str, expected_selection_revision: int) -> dict[str, Any]:
        return self._media.assets.reviewed_keyframe_crop_source(project_id, binding_id=binding_id, expected_selection_revision=expected_selection_revision)
    def record_reviewed_keyframe_center_crop(self, project_id: str, *, source: dict[str, Any], target_profile: dict[str, Any], expected_selection_revision: int, original_hash: str, display_hash: str, mime_type: str, byte_size: int, width: int, height: int, publish: Callable[[], tuple[str, str]]) -> dict[str, Any]:
        return self._media.assets.record_reviewed_keyframe_center_crop(project_id, source=source, target_profile=target_profile, expected_selection_revision=expected_selection_revision, original_hash=original_hash, display_hash=display_hash, mime_type=mime_type, byte_size=byte_size, width=width, height=height, publish=publish)
    def list_managed_assets(self, project_id: str) -> list[dict[str, Any]]:
        return self._media.assets.list_managed_assets(project_id)
    def create_visual_intent(self, project_id: str, asset_id: str, intent: dict[str, Any], *, consumed_draft: tuple[str, int, dict[str, Any]] | None=None) -> dict[str, Any]:
        return self._media.intents.create_visual_intent(project_id, asset_id, intent, consumed_draft=consumed_draft)
    def list_visual_intents(self, project_id: str) -> list[dict[str, Any]]:
        return self._media.intents.list_visual_intents(project_id)
    @staticmethod
    def _latest_visual_intent_for_role_in_session(session: Session, project_id: str, asset_id: str, role: str | None) -> VisualIntentRow | None:
        return KeyframeAdmission.latest_visual_intent_for_role_in_session(session, project_id, asset_id, role)
    def _reviewed_binding_admission_eligible_in_session(self, session: Session, project_id: str, binding: ReviewedShotBindingRow, *, approval: ApprovalDecisionRow | None=None) -> bool:
        return self._media.admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding, approval=approval)
    def list_current_reviewed_keyframes(self, project_id: str) -> list[dict[str, Any]]:
        return self._media.admission.list_current_reviewed_keyframes(project_id)
    def _approval_is_active_in_session(self, session: Session, decision_id: str) -> ApprovalDecisionRow:
        return self._media.admission.approval_is_active_in_session(session, decision_id)
    @staticmethod
    def _selection_state_in_session(session: Session, project_id: str, now: datetime) -> VisualSelectionStateRow:
        return KeyframeAdmission.selection_state_in_session(session, project_id, now)
    def select_reviewed_keyframe(self, project_id: str, *, asset_id: str, shot_id: str, scene_id: str, expected_selection_revision: int, storyboard_revision: int, approval_id: str, compatibility_note: str, visual_intent_id: str, visual_intent_revision: int) -> dict[str, Any]:
        return self._media.keyframes.select_reviewed_keyframe(project_id, asset_id=asset_id, shot_id=shot_id, scene_id=scene_id, expected_selection_revision=expected_selection_revision, storyboard_revision=storyboard_revision, approval_id=approval_id, compatibility_note=compatibility_note, visual_intent_id=visual_intent_id, visual_intent_revision=visual_intent_revision)
    def create_still_preview(self, project_id: str, *, scene_id: str, shot_ids: list[str], expected_selection_revision: int, storyboard_revision: int, approval_id: str) -> dict[str, Any]:
        return self._media.keyframes.create_still_preview(project_id, scene_id=scene_id, shot_ids=shot_ids, expected_selection_revision=expected_selection_revision, storyboard_revision=storyboard_revision, approval_id=approval_id)
    def list_still_previews(self, project_id: str) -> list[dict[str, Any]]:
        return self._media.keyframes.list_still_previews(project_id)
    def visual_selection_revision(self, project_id: str) -> int:
        return self._media.keyframes.visual_selection_revision(project_id)
    def reviewed_preview_dependencies_current(self, project_id: str, frame: dict[str, Any]) -> bool:
        return self._media.keyframes.reviewed_preview_dependencies_current(project_id, frame)
    @staticmethod
    def _video_job_id() -> str:
        return VideoJobCurrentness.video_job_id()
    @staticmethod
    def _video_job_dict(row: VideoJobRow, *, current: bool, selected: bool=False) -> dict[str, Any]:
        return VideoJobCurrentness.video_job_dict(row, current=current, selected=selected)
    @staticmethod
    def _video_job_tracks_paid_wan_pilot(row: VideoJobRow) -> bool:
        return VideoJobCurrentness.video_job_tracks_paid_wan_pilot(row)
    def _video_job_current_in_session(self, session: Session, row: VideoJobRow) -> bool:
        return self._media.video_currentness.video_job_current_in_session(session, row)
    def video_budget(self) -> dict[str, Any]:
        return self._media.video.video_budget()
    def prepare_video_job(self, project_id: str, *, approval_id: str, shot_id: str, storyboard_revision: int, expected_selection_revision: int, idempotency_key: str, requested_seconds: int=5, resolution: str='720p', audio: bool=True, production_contract: VideoProductionContract | None=None) -> dict[str, Any]:
        return self._media.video.prepare_video_job(project_id, approval_id=approval_id, shot_id=shot_id, storyboard_revision=storyboard_revision, expected_selection_revision=expected_selection_revision, idempotency_key=idempotency_key, requested_seconds=requested_seconds, resolution=resolution, audio=audio, production_contract=production_contract)
    def claim_video_dispatch(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        return self._media.video.claim_video_dispatch(project_id, video_job_id)
    def record_video_submission(self, project_id: str, video_job_id: str, prediction_id: str) -> dict[str, Any]:
        return self._media.video.record_video_submission(project_id, video_job_id, prediction_id)
    def record_video_outcome_unknown(self, project_id: str, video_job_id: str, message: str) -> dict[str, Any]:
        return self._media.video.record_video_outcome_unknown(project_id, video_job_id, message)
    def record_video_output(self, project_id: str, video_job_id: str, *, uri: str, digest: str, observed: dict[str, Any]) -> dict[str, Any]:
        return self._media.video.record_video_output(project_id, video_job_id, uri=uri, digest=digest, observed=observed)
    def record_video_retrieve_needed(self, project_id: str, video_job_id: str, message: str) -> dict[str, Any]:
        return self._media.video.record_video_retrieve_needed(project_id, video_job_id, message)
    def record_video_remote_failed(self, project_id: str, video_job_id: str, code: str) -> dict[str, Any]:
        return self._media.video.record_video_remote_failed(project_id, video_job_id, code)
    def recover_video_dispatches(self) -> list[str]:
        return self._media.video.recover_video_dispatches()
    def cancel_video_job(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        return self._media.video.cancel_video_job(project_id, video_job_id)
    def list_video_jobs(self, project_id: str) -> list[dict[str, Any]]:
        return self._media.video.list_video_jobs(project_id)
    def get_video_output_storage(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        return self._media.video.get_video_output_storage(project_id, video_job_id)
    def review_video_job(self, project_id: str, video_job_id: str, *, reviewer: str, decision: str, note: str) -> dict[str, Any]:
        return self._media.video.review_video_job(project_id, video_job_id, reviewer=reviewer, decision=decision, note=note)
    @staticmethod
    def _character_reference_context(character: Any) -> dict[str, Any]:
        return CharacterReferencePersistence.character_reference_context(character)
    @staticmethod
    def _character_reference_state_in_session(session: Session, project_id: str, character_id: str, now: datetime) -> CharacterReferenceStateRow:
        return CharacterReferencePersistence._character_reference_state_in_session(session, project_id, character_id, now)
    @staticmethod
    def _reference_decision_dict(row: CharacterReferenceDecisionRow, *, current: bool) -> dict[str, Any]:
        return CharacterReferencePersistence._reference_decision_dict(row, current=current)
    def _current_character_reference_in_session(self, session: Session, project_id: str, character: Any) -> CharacterReferenceDecisionRow | None:
        return self._media.references.current_character_reference_in_session(session, project_id, character)
    def create_character_reference_decision(self, project_id: str, *, character_id: str, primary_asset_id: str, complementary_asset_ids: list[str], expected_reference_revision: int, reviewer: str, notes: str) -> dict[str, Any]:
        return self._media.references.create_character_reference_decision(project_id, character_id=character_id, primary_asset_id=primary_asset_id, complementary_asset_ids=complementary_asset_ids, expected_reference_revision=expected_reference_revision, reviewer=reviewer, notes=notes)
    def revoke_character_reference_decision(self, project_id: str, *, character_id: str, expected_reference_revision: int, reviewer: str, reason: str) -> dict[str, Any]:
        return self._media.references.revoke_character_reference_decision(project_id, character_id=character_id, expected_reference_revision=expected_reference_revision, reviewer=reviewer, reason=reason)
    def list_character_reference_decisions(self, project_id: str) -> dict[str, Any]:
        return self._media.references.list_character_reference_decisions(project_id)
    @staticmethod
    def _proposal_dict(row: CharacterReferenceProposalRow, *, current: bool) -> dict[str, Any]:
        return CharacterReferenceProposalPersistence._proposal_dict(row, current=current)
    def _proposal_is_current_in_session(self, session: Session, proposal: CharacterReferenceProposalRow) -> bool:
        return self._media.proposals._proposal_is_current_in_session(session, proposal)
    def prepare_character_reference_proposal(self, project_id: str, *, character_id: str, story_bible_revision: int, visual_direction: str, parent_candidate_asset_id: str | None) -> dict[str, Any]:
        return self._media.proposals.prepare_character_reference_proposal(project_id, character_id=character_id, story_bible_revision=story_bible_revision, visual_direction=visual_direction, parent_candidate_asset_id=parent_candidate_asset_id)
    def character_reference_proposal_package_sources(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        return self._media.proposals.character_reference_proposal_package_sources(project_id, proposal_id)
    def mark_character_reference_proposal_exported(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        return self._media.proposals.mark_character_reference_proposal_exported(project_id, proposal_id)
    def character_reference_proposal_delivery_context(self, project_id: str, proposal_id: str) -> dict[str, Any]:
        return self._media.proposals.character_reference_proposal_delivery_context(project_id, proposal_id)
    def record_character_reference_proposal_rejection(self, project_id: str, proposal_id: str, code: str) -> None:
        return self._media.proposals.record_character_reference_proposal_rejection(project_id, proposal_id, code)
    def record_character_reference_proposal_delivery(self, project_id: str, proposal_id: str, *, delivery_id: str, manifest: dict[str, Any], manifest_hash: str, outputs: list[dict[str, Any]], publish: Callable[[dict[str, Any]], tuple[str, str]]) -> dict[str, Any]:
        return self._media.proposals.record_character_reference_proposal_delivery(project_id, proposal_id, delivery_id=delivery_id, manifest=manifest, manifest_hash=manifest_hash, outputs=outputs, publish=publish)
    @staticmethod
    def _proposal_candidate_dict(session: Session, row: CharacterReferenceProposalCandidateRow) -> dict[str, Any]:
        return CharacterReferenceProposalPersistence._proposal_candidate_dict(session, row)
    def list_character_reference_proposals(self, project_id: str) -> list[dict[str, Any]]:
        return self._media.proposals.list_character_reference_proposals(project_id)
    @staticmethod
    def _same_person_review_state_in_session(session: Session, project_id: str, now: datetime) -> SamePersonReviewStateRow:
        return SamePersonReviewPersistence._same_person_review_state_in_session(session, project_id, now)
    @staticmethod
    def _same_person_review_dict(row: SamePersonReviewRow, *, current: bool) -> dict[str, Any]:
        return SamePersonReviewPersistence._same_person_review_dict(row, current=current)
    def _identity_mapping_for_binding_in_session(self, session: Session, binding: ReviewedShotBindingRow) -> list[dict[str, Any]] | None:
        return self._media.same_person.identity_mapping_for_binding_in_session(session, binding)
    def _same_person_review_is_current_in_session(self, session: Session, project_id: str, review: SamePersonReviewRow) -> bool:
        return self._media.same_person.same_person_review_is_current_in_session(session, project_id, review)
    def record_same_person_review(self, project_id: str, *, binding_id: str, expected_review_revision: int, reviewer: str, comparisons: list[dict[str, Any]], notes: str) -> dict[str, Any]:
        return self._media.same_person.record_same_person_review(project_id, binding_id=binding_id, expected_review_revision=expected_review_revision, reviewer=reviewer, comparisons=comparisons, notes=notes)
    def list_same_person_reviews(self, project_id: str) -> dict[str, Any]:
        return self._media.same_person.list_same_person_reviews(project_id)
    def current_same_person_review_for_binding(self, session: Session, project_id: str, binding: ReviewedShotBindingRow) -> SamePersonReviewRow | None:
        return self._media.same_person.current_same_person_review_for_binding(session, project_id, binding)
    @staticmethod
    def _image_job_id() -> str:
        return ImageJobCurrentness.image_job_id()
    @staticmethod
    def _image_job_dict(row: ImageJobRow, *, current: bool) -> dict[str, Any]:
        return ImageJobCurrentness.image_job_dict(row, current=current)
    @staticmethod
    def _production_unit_dict(row: ProductionUnitRow) -> dict[str, Any]:
        return ImageJobCurrentness.production_unit_dict(row)
    def _image_job_is_current_in_session(self, session: Session, job: ImageJobRow) -> bool:
        return self._media.image_currentness.image_job_is_current_in_session(session, job)
    @staticmethod
    def _image_job_resolved_context(*, shot: Any, storyboard: Any, story_bible: Any, scene_beats: Any) -> dict[str, Any]:
        return ImageJobCurrentness.image_job_resolved_context(shot=shot, storyboard=storyboard, story_bible=story_bible, scene_beats=scene_beats)
    def prepare_image_job(self, project_id: str, *, approval_id: str, shot_id: str, storyboard_revision: int, parent_candidate_asset_id: str | None=None, keyframe_adaptation: dict[str, Any] | None=None, presentation_change: str, contract_version: int=2, consumed_draft: tuple[str, int, dict[str, Any]] | None=None) -> dict[str, Any]:
        return self._media.image_preparation.prepare_image_job(project_id, approval_id=approval_id, shot_id=shot_id, storyboard_revision=storyboard_revision, parent_candidate_asset_id=parent_candidate_asset_id, keyframe_adaptation=keyframe_adaptation, presentation_change=presentation_change, contract_version=contract_version, consumed_draft=consumed_draft)
    def image_job_package_sources(self, project_id: str, job_id: str) -> dict[str, Any]:
        return self._media.image_delivery.image_job_package_sources(project_id, job_id)
    def mark_image_job_exported(self, project_id: str, job_id: str) -> dict[str, Any]:
        return self._media.image_delivery.mark_image_job_exported(project_id, job_id)
    def cancel_image_job(self, project_id: str, job_id: str, reason: str) -> dict[str, Any]:
        return self._media.image_delivery.cancel_image_job(project_id, job_id, reason)
    def image_job_delivery_context(self, project_id: str, job_id: str) -> dict[str, Any]:
        return self._media.image_delivery.image_job_delivery_context(project_id, job_id)
    def record_image_job_delivery_rejection(self, project_id: str, job_id: str, code: str) -> None:
        return self._media.image_delivery.record_image_job_delivery_rejection(project_id, job_id, code)
    @staticmethod
    def _image_candidate_dict(session: Session, row: ImageJobCandidateRow) -> dict[str, Any]:
        return ImageJobDeliveryPersistence._image_candidate_dict(session, row)
    def record_image_job_delivery(self, project_id: str, job_id: str, *, delivery_id: str, manifest: dict[str, Any], manifest_hash: str, outputs: Sequence[dict[str, Any]], publish: Callable[[dict[str, Any]], tuple[str, str]]) -> dict[str, Any]:
        return self._media.image_delivery.record_image_job_delivery(project_id, job_id, delivery_id=delivery_id, manifest=manifest, manifest_hash=manifest_hash, outputs=outputs, publish=publish)
    def list_image_jobs(self, project_id: str) -> list[dict[str, Any]]:
        return self._media.image_delivery.list_image_jobs(project_id)

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

    def capture_snapshot(self, project_id: str) -> CanonicalSnapshot:
        return self._generation_snapshots.capture_snapshot(project_id)

    def snapshot_is_current(self, snapshot: CanonicalSnapshot) -> bool:
        return self._generation_snapshots.snapshot_is_current(snapshot)

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

    def get_repair_stage_dependencies(
        self,
        child_run_id: str,
        stage: StageName,
    ) -> dict[StageName, StagePayload]:
        return self._generation_repairs.get_repair_stage_dependencies(child_run_id, stage)

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

    def get_run_progress(self, run_id: str) -> RunProgress:
        return self._generation_progress.get_run_progress(run_id)

    def seal_stage_aggregate(
        self,
        run_id: str,
        stage: StageName,
        *,
        candidate_artifact_ids: list[str],
    ) -> SealedStageAggregateTrace:
        return self._generation_aggregates.seal_stage_aggregate(run_id, stage, candidate_artifact_ids=candidate_artifact_ids)

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

    def get_repair_eligible_work_units(self, run_id: str) -> list[WorkUnitRepairEligibility]:
        return self._generation_repairs.get_repair_eligible_work_units(run_id)

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

    def add_artifact(self, artifact: Artifact) -> Artifact:
        return self._generation_evidence.add_artifact(artifact)

    def get_artifact(self, artifact_id: str) -> Artifact:
        return self._generation_evidence.get_artifact(artifact_id)

    def get_run_trace(self, run_id: str) -> RunTrace:
        return self._generation_evidence.get_run_trace(run_id)

    def get_media_prompt_context(self, project_id: str, shot_id: str) -> MediaPromptContext:
        return self._media.tasks.get_media_prompt_context(project_id, shot_id)
    def create_media_task(self, project_id: str, shot_id: str, kind: MediaKind, *, expected_storyboard_revision: int, derived_prompt: str, prompt_components: dict[str, Any], provider: str | None=None, public_settings: dict[str, Any] | None=None) -> MediaTask:
        return self._media.tasks.create_media_task(project_id, shot_id, kind, expected_storyboard_revision=expected_storyboard_revision, derived_prompt=derived_prompt, prompt_components=prompt_components, provider=provider, public_settings=public_settings)
    def get_media_task(self, task_id: str) -> MediaTask:
        return self._media.tasks.get_media_task(task_id)
    def list_project_media_tasks(self, project_id: str, *, limit: int=200) -> list[MediaTask]:
        return self._media.tasks.list_project_media_tasks(project_id, limit=limit)
    def start_media_task(self, task_id: str, *, provider: str | None=None) -> MediaTask:
        return self._media.tasks.start_media_task(task_id, provider=provider)
    def record_media_submission(self, task_id: str, *, provider: str, provider_task_id: str | None) -> MediaTask:
        return self._media.tasks.record_media_submission(task_id, provider=provider, provider_task_id=provider_task_id)
    def finish_media_task(self, task_id: str, status: MediaTaskStatus, *, output_uri: str | None=None, error: str | None=None) -> MediaTask:
        return self._media.tasks.finish_media_task(task_id, status, output_uri=output_uri, error=error)

    def get_provider_settings(self) -> ProviderSettings:
        return self._application_profiles.get_provider_settings()
    def bootstrap_default_text_provider_profile(self, environment_default: TextProviderProfileSnapshot) -> TextProviderProfile:
        return self._application_profiles.bootstrap_default_text_provider_profile(environment_default)
    def get_text_provider_profile(self, profile_id: str) -> TextProviderProfile:
        return self._application_profiles.get_text_provider_profile(profile_id)
    def list_text_provider_profiles(self) -> list[TextProviderProfile]:
        return self._application_profiles.list_text_provider_profiles()
    def get_provider_profile_selection(self) -> ProviderProfileSelection:
        return self._application_profiles.get_provider_profile_selection()
    @staticmethod
    def _profile_configuration_for_revision(profile_id: str, revision: int, value: TextProviderProfileSnapshot | dict[str, Any]) -> TextProviderProfileSnapshot:
        return ApplicationProfilePersistence._profile_configuration_for_revision(profile_id, revision, value)
    def create_text_provider_profile(self, profile_id: str, display_name: str, *, configuration: TextProviderProfileSnapshot | dict[str, Any] | None=None, copy_from_profile_id: str | None=None, adapter_id: str | None=None, adapter_version: str | None=None) -> TextProviderProfile:
        return self._application_profiles.create_text_provider_profile(profile_id, display_name, configuration=configuration, copy_from_profile_id=copy_from_profile_id, adapter_id=adapter_id, adapter_version=adapter_version)
    def update_text_provider_profile(self, profile_id: str, expected_revision: int, *, display_name: str, configuration: TextProviderProfileSnapshot | dict[str, Any], adapter_id: str | None=None, adapter_version: str | None=None) -> TextProviderProfile:
        return self._application_profiles.update_text_provider_profile(profile_id, expected_revision, display_name=display_name, configuration=configuration, adapter_id=adapter_id, adapter_version=adapter_version)
    def activate_text_provider_profile(self, profile_id: str, expected_selection_revision: int) -> ProviderProfileSelection:
        return self._application_profiles.activate_text_provider_profile(profile_id, expected_selection_revision)
    def set_text_provider_profile_enabled(self, profile_id: str, expected_availability_revision: int, *, enabled: bool) -> TextProviderProfile:
        return self._application_profiles.set_text_provider_profile_enabled(profile_id, expected_availability_revision, enabled=enabled)
    @staticmethod
    def _profile_id_from_snapshot(snapshot: Mapping[str, Any]) -> str | None:
        return ApplicationProfilePersistence._profile_id_from_snapshot(snapshot)
    def _assert_new_run_profile_enabled(self, session: Session, provider_snapshot: Mapping[str, Any]) -> None:
        return self._application_profiles._assert_new_run_profile_enabled(session, provider_snapshot)
    def delete_text_provider_profile(self, profile_id: str, expected_revision: int) -> None:
        return self._application_profiles.delete_text_provider_profile(profile_id, expected_revision)
    def put_provider_settings(self, settings: ProviderSettings) -> ProviderSettings:
        return self._application_profiles.put_provider_settings(settings)
    def update_provider_settings_projection(self, *, expected_profile_id: str, expected_profile_revision: int, updates: dict[str, Any], defaults: ProviderSettings) -> tuple[TextProviderProfile, ProviderSettings]:
        return self._application_profiles.update_provider_settings_projection(expected_profile_id=expected_profile_id, expected_profile_revision=expected_profile_revision, updates=updates, defaults=defaults)
