"""Independent composition root for one manifest-bound project database."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, ContextManager, Sequence

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ...domain import (
    InitialStage,
    Project,
    StageName,
    StageStatus,
    STAGE_ORDER,
    stage_payload_model,
    utc_now,
    validate_initial_stage_prefix,
)
from ...exceptions import InvalidTransitionError, NotFoundError
from ..database import RepositoryDatabase
from ..schema import (
    PROJECT_TEXT_PIPELINE_TABLE_NAMES, GenerationRunRow, ProjectOperationalStateRow,
    ProjectRow, SourceOutlineCandidateRow, SourceOutlineHeadRow,
    SourceOutlineGraphAdmissionRow,
    SourceOutlineRevisionRow, SourceOutlineSectionMapHeadRow,
    SourceOutlineSectionMapRevisionRow, SourceOutlineSourceRevisionRow, StageHeadRow,
    CastCandidateRow, CastHeadRow, CastRevisionRow, ArtCandidateRow, ArtHeadRow, ArtRevisionRow,
    ScriptCandidateRow, ScriptHeadRow, ScriptRevisionRow,
)
from ..transactions import bootstrap_lease, lifecycle_lease, read_lease, work_unit_claim_lease, write_lease
from .access import ProjectCodecs, ProjectGuards, ProjectLeases, ProjectPersistenceAccess, ProjectRows
from .approvals import ProjectApprovalPersistence
from .canonical import ProjectCanonicalPersistence
from .catalog import ProjectCatalogPersistence
from .constants import CURRENT_STAGE_SCHEMA_VERSION
from .drafts import ProjectDraftPersistence
from .gates import ProjectGatePersistence
from .generation_access import GenerationAdmission, GenerationCodecs, GenerationLeases, GenerationPersistenceAccess, GenerationRows
from .generation_admission import ProjectGenerationAdmission
from .generation_aggregates import ProjectGenerationAggregatePersistence
from .generation_attempts import ProjectGenerationAttemptPersistence
from .generation_evidence import ProjectGenerationEvidencePersistence
from .generation_integrity import GenerationWorkUnitIntegrity
from .generation_lifecycle import ProjectGenerationLifecyclePersistence
from .generation_plans import ProjectGenerationPlanningPersistence
from .generation_progress import ProjectGenerationProgressPersistence
from .generation_recovery import ProjectGenerationRecoveryPersistence
from .generation_repair_eligibility import GenerationRepairEligibility
from .generation_repair_scope import GenerationRepairScopePolicy
from .generation_repairs import ProjectGenerationRepairPersistence
from .generation_runtime_artifacts import ProjectGenerationRuntimeArtifactPersistence
from .generation_reuse import ProjectGenerationReusePersistence
from .generation_snapshots import ProjectGenerationSnapshots
from .lifecycle import ProjectLifecyclePersistence
from .media import ProjectMediaPersistence
from .source_outline import ProjectSourceOutlinePersistence
from .cast import ProjectCastPersistence
from .art import ProjectArtPersistence
from .script import ProjectScriptPersistence
from .repository_codecs import (
    approval_decision_from_row, artifact_from_row, assert_active_project,
    assert_lifecycle_revision, attempt_from_row, decode_current_stage_payload,
    decode_stage_payload, entity_revision_from_row, fragment_reuse_binding_from_row,
    gate_result_from_row, generation_plan_trace_from_row, latest_run_summary_from_row,
    media_task_from_row, media_task_row, project_from_row, project_is_busy_in_session,
    project_row, repair_scope_from_row, run_from_row, run_row,
    sealed_aggregate_trace_from_row, stage_head_from_row, stage_row,
    stage_plan_trace_from_row, story_graph_topology_trace_from_row,
    work_unit_trace_from_row,
)
from .workflow import ProjectAuthoringWorkflow


@dataclass(frozen=True)
class ProjectVideoDispatchAccess:
    """The only project-database primitives the cross-file video bridge needs."""

    read: Callable[[], ContextManager[Session]]
    lifecycle_write: Callable[[], ContextManager[Session]]


class ProjectSQLiteRepository:
    """Project-only composition with no legacy or application-control dependency."""

    def __init__(
        self,
        database_url: str,
        *,
        project_id: str,
        create_schema: bool = True,
        sqlite_busy_timeout_ms: int = 1_000,
        read_only: bool = False,
        normalize_sqlite_wal: bool = True,
    ) -> None:
        if not project_id:
            raise ValueError("project_id is required for a project repository")
        if sqlite_busy_timeout_ms < 1:
            raise ValueError("sqlite_busy_timeout_ms must be at least 1")
        self.project_id = project_id
        self._bootstrap_retry_after_seconds = max(1, (sqlite_busy_timeout_ms + 999) // 1_000)
        self._database = RepositoryDatabase(
            database_url,
            create_schema=create_schema,
            schema_tables=self._schema_tables(),
            schema_scope="project",
            sqlite_busy_timeout_ms=sqlite_busy_timeout_ms,
            read_only=read_only,
            normalize_sqlite_wal=normalize_sqlite_wal,
        )
        self.engine, self._sessions, self._write_lock = (
            self._database.engine, self._database.sessions, self._database.write_lock
        )
        if not read_only:
            # Project folders predate F1A. This is a narrow additive migration:
            # it creates only the independent review tables and never rewrites
            # a source, canonical stage, media record, or project manifest.
            from ..schema import Base

            Base.metadata.create_all(
                self.engine,
                tables=[
                    SourceOutlineHeadRow.__table__,
                    SourceOutlineSourceRevisionRow.__table__,
                    SourceOutlineCandidateRow.__table__,
                    SourceOutlineRevisionRow.__table__,
                    SourceOutlineSectionMapHeadRow.__table__,
                    SourceOutlineSectionMapRevisionRow.__table__,
                    SourceOutlineGraphAdmissionRow.__table__,
                    CastHeadRow.__table__, CastCandidateRow.__table__, CastRevisionRow.__table__,
                    ArtHeadRow.__table__, ArtCandidateRow.__table__, ArtRevisionRow.__table__,
                    ScriptHeadRow.__table__, ScriptCandidateRow.__table__, ScriptRevisionRow.__table__,
                ],
            )
        self._generation_admission = ProjectGenerationAdmission()

        self._project_access = ProjectPersistenceAccess(
            leases=ProjectLeases(
                read=self._read, write=self._write, bootstrap_write=self._bootstrap_write,
                lifecycle_write=self._lifecycle_write,
                work_unit_claim_write=self._work_unit_claim_write,
            ),
            rows=ProjectRows(
                project=self._project_row, stage=self._stage_row, run=self._run_row,
                media_task=media_task_row,
            ),
            codecs=ProjectCodecs(
                project=project_from_row, latest_run_summary=latest_run_summary_from_row,
                stage_head=stage_head_from_row, entity_revision=entity_revision_from_row,
                decode_current_stage_payload=decode_current_stage_payload,
                gate_result=gate_result_from_row, approval_decision=approval_decision_from_row,
            ),
            guards=ProjectGuards(
                active=assert_active_project, lifecycle_revision=assert_lifecycle_revision,
                busy=project_is_busy_in_session,
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
        self.source_outline = ProjectSourceOutlinePersistence(self._project_access, self._canonical)
        self.cast = ProjectCastPersistence(self._project_access)
        self.art = ProjectArtPersistence(self._project_access, self.cast)
        self.script = ProjectScriptPersistence(self._project_access, self.art)
        self._media = ProjectMediaPersistence(
            self._project_access, self._canonical, self._drafts, self.cast, self.art, accounting=None
        )
        self._generation_access = GenerationPersistenceAccess(
            leases=GenerationLeases(
                read=self._read, write=self._write, lifecycle_write=self._lifecycle_write,
                work_unit_claim_write=self._work_unit_claim_write,
            ),
            rows=GenerationRows(project=self._project_row, run=self._run_row, stage=self._stage_row),
            codecs=GenerationCodecs(
                project=project_from_row, run=run_from_row, attempt=attempt_from_row,
                artifact=artifact_from_row, stage_head=stage_head_from_row,
                stage_plan_trace=stage_plan_trace_from_row, work_unit_trace=work_unit_trace_from_row,
                generation_plan_trace=generation_plan_trace_from_row,
                topology_trace=story_graph_topology_trace_from_row,
                sealed_aggregate_trace=sealed_aggregate_trace_from_row,
                repair_scope=repair_scope_from_row, reuse_binding=fragment_reuse_binding_from_row,
                decode_stage_payload=decode_stage_payload,
                decode_current_stage_payload=decode_current_stage_payload,
            ),
            admission=GenerationAdmission(
                assert_active_project=assert_active_project,
                assert_new_run_profile_enabled=self._generation_admission.assert_new_run_profile_enabled,
            ),
        )
        self._generation_snapshots = ProjectGenerationSnapshots(self._generation_access)
        self._generation_plans = ProjectGenerationPlanningPersistence(self._generation_access)
        integrity = GenerationWorkUnitIntegrity()
        eligibility = GenerationRepairEligibility(
            self._generation_access, self._generation_plans, integrity, self._generation_snapshots
        )
        repair_scope = GenerationRepairScopePolicy(
            self._generation_access, self._generation_plans, integrity, eligibility
        )
        self._generation_plans.bind_repair_scope(repair_scope)
        self._generation_attempts = ProjectGenerationAttemptPersistence(self._generation_access, integrity)
        self._generation_reuse = ProjectGenerationReusePersistence(
            self._generation_access, self._generation_plans, integrity, repair_scope
        )
        self._generation_aggregates = ProjectGenerationAggregatePersistence(
            self._generation_access, self._generation_plans, integrity, repair_scope
        )
        self._generation_evidence = ProjectGenerationEvidencePersistence(
            self._generation_access, integrity, self._generation_snapshots
        )
        self._generation_repairs = ProjectGenerationRepairPersistence(
            self._generation_access, self._generation_plans, repair_scope, eligibility,
            self._generation_snapshots, self._generation_evidence,
        )
        self._generation_progress = ProjectGenerationProgressPersistence(
            self._generation_access, eligibility, integrity
        )
        self._generation_recovery = ProjectGenerationRecoveryPersistence(
            self._generation_access, self._generation_plans
        )
        self._generation_runtime_artifacts = (
            ProjectGenerationRuntimeArtifactPersistence(self._generation_access)
        )
        self._generation_lifecycle = ProjectGenerationLifecyclePersistence(
            self._generation_access, self._generation_snapshots, self._canonical
        )
        from .repository_authoring import ProjectAuthoringRepository
        from .repository_generation import ProjectGenerationRepository
        from .repository_lifecycle import ProjectLifecycleRepository
        from .repository_media import ProjectMediaRepository

        self.authoring = ProjectAuthoringRepository(
            catalog=self._catalog,
            gates=self._gates,
            drafts=self._drafts,
            canonical=self._canonical,
            workflow=self._workflow,
            approvals=self._approvals,
        )
        self.lifecycle = ProjectLifecycleRepository(self._lifecycle)
        self.generation = ProjectGenerationRepository(
            admission=self._generation_admission,
            snapshots=self._generation_snapshots,
            plans=self._generation_plans,
            attempts=self._generation_attempts,
            aggregates=self._generation_aggregates,
            repairs=self._generation_repairs,
            reuse=self._generation_reuse,
            lifecycle=self._generation_lifecycle,
            evidence=self._generation_evidence,
            progress=self._generation_progress,
            recovery=self._generation_recovery,
            runtime_artifacts=self._generation_runtime_artifacts,
        )
        self.media = ProjectMediaRepository(
            assets=self._media.assets,
            intents=self._media.intents,
            admission=self._media.admission,
            keyframes=self._media.keyframes,
            references=self._media.references,
            proposals=self._media.proposals,
            art_references=self._media.art_references,
            same_person=self._media.same_person,
            image_preparation=self._media.image_preparation,
            image_delivery=self._media.image_delivery,
            direct_video=self._media.direct_video,
            video_currentness=self._media.video_currentness,
        )
        self.video_dispatch = ProjectVideoDispatchAccess(self._read, self._lifecycle_write)

    def _schema_tables(self) -> list[Any]:
        from ..schema import Base
        return [table for table in Base.metadata.sorted_tables if table.name in PROJECT_TEXT_PIPELINE_TABLE_NAMES]

    def close(self) -> None:
        self._database.close()

    def enable_sqlite_wal(self) -> None:
        self._database.enable_sqlite_wal()

    def _set_recovery_admission(self, *, recovered_run_ids: Callable[[], set[str]], recovery_operations_present: Callable[[], bool]) -> None:
        self._generation_admission.set_recovery_admission(
            recovered_run_ids=recovered_run_ids,
            recovery_operations_present=recovery_operations_present,
        )

    def initialize_project(
        self, project: Project, *, initial_stages: Sequence[InitialStage] = ()
    ) -> Project:
        if project.id != self.project_id:
            raise InvalidTransitionError("project repository identity does not match project initialization")
        normalized_stages = [InitialStage.model_validate(stage) for stage in initial_stages]
        validate_initial_stage_prefix(normalized_stages)
        with self._bootstrap_write() as session:
            if session.scalar(select(ProjectRow.id).limit(1)) is not None:
                raise InvalidTransitionError("project repository has already been initialized")
            project_row = ProjectRow(
                id=project.id, revision=project.revision, lifecycle_revision=project.lifecycle_revision,
                lifecycle_status=project.lifecycle_status.value, archived_at=project.archived_at,
                brief=project.brief.model_dump(mode="json", by_alias=False),
                created_at=project.created_at, updated_at=project.updated_at,
            )
            session.add(project_row)
            session.flush()
            session.add(ProjectOperationalStateRow(project_id=project.id, state="open", revision=1, changed_at=project.created_at))
            for stage in STAGE_ORDER:
                session.add(StageHeadRow(
                    id=f"{project.id}:{stage.value}", project_id=project.id, stage=stage.value,
                    status=StageStatus.MISSING.value, revision=0, entity_revision_id=None,
                    content_hash=None, schema_version=CURRENT_STAGE_SCHEMA_VERSION,
                    input_revisions={}, stale_reasons=[], updated_at=project.updated_at,
                ))
            self.source_outline.initialize(session, project.id, created_at=project.created_at)
            self.cast.initialize(session, project.id, created_at=project.created_at)
            self.art.initialize(session, project.id, created_at=project.created_at)
            self.script.initialize(session, project.id, created_at=project.created_at)
            session.flush()
            for initial_stage in normalized_stages:
                payload = stage_payload_model(
                    initial_stage.stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION
                ).model_validate(initial_stage.payload)
                self._canonical._install_stage_in_session(
                    session,
                    project_row,
                    initial_stage.stage,
                    payload,
                    expected_revision=0,
                    now=project.created_at,
                    allow_noop=False,
                )
        return self.authoring.get_project(project.id)

    def get_project(self, project_id: str) -> Project:
        """Compatibility read retained for manifest/open validation only."""

        return self.authoring.get_project(project_id)

    def operational_state(self) -> tuple[str, int]:
        with self._read() as session:
            row = session.get(ProjectOperationalStateRow, self.project_id)
            if row is None:
                raise InvalidTransitionError("project has no operational state")
            return row.state, row.revision

    def set_operational_state(self, *, expected_revision: int, state: str) -> tuple[str, int]:
        if state not in {"open", "closed"}:
            raise ValueError("project operational state must be open or closed")
        with self._write() as session:
            row = session.get(ProjectOperationalStateRow, self.project_id)
            if row is None:
                raise InvalidTransitionError("project has no operational state")
            if row.revision != expected_revision:
                raise InvalidTransitionError("project operational state is stale")
            if row.state != state:
                row.state, row.revision, row.changed_at = state, row.revision + 1, utc_now()
            return row.state, row.revision

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

    def _project_row(self, session: Session, project_id: str) -> ProjectRow:
        if project_id != self.project_id:
            raise NotFoundError("project does not belong to this project repository")
        return project_row(session, project_id)

    def _stage_row(self, session: Session, project_id: str, stage: StageName) -> StageHeadRow:
        if project_id != self.project_id:
            raise NotFoundError("stage does not belong to this project repository")
        return stage_row(session, project_id, stage)

    def _run_row(self, session: Session, run_id: str) -> GenerationRunRow:
        row = run_row(session, run_id)
        if row.project_id != self.project_id:
            raise NotFoundError("generation run does not belong to this project repository")
        return row
