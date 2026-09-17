"""Shared row projections and guards for project-owned persistence.

These functions deliberately contain no repository composition or application
control imports.  Both the retained compatibility facade and the bound project
repository use the same durable row interpretation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import (
    Artifact,
    ArtifactKind,
    AttemptStatus,
    CanonicalSnapshot,
    EntityRevision,
    FragmentReuseBinding,
    GateEvidence,
    GateResult,
    GenerationAttempt,
    GenerationAttemptKind,
    GenerationPlanTrace,
    GenerationRun,
    GenerationWorkUnitTrace,
    LatestRunSummary,
    MediaTask,
    Project,
    ProjectBrief,
    ProjectLifecycleStatus,
    RepairSource,
    RunKind,
    RunStatus,
    SealedStageAggregateTrace,
    StageHead,
    StageName,
    StagePayload,
    StageStatus,
    StagePlanTrace,
    StoryGraphTopologyTrace,
    WorkUnitRepairScope,
    WorkUnitStatus,
    TERMINAL_MEDIA_TASK_STATUSES,
    TERMINAL_RUN_STATUSES,
    TERMINAL_WORK_UNIT_STATUSES,
    stage_payload_model,
)
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError, SchemaResetRequiredError
from ..codec import _stored_utc, stable_hash
from ..schema import (
    ApprovalDecisionRow,
    ArtifactRow,
    EntityRevisionRow,
    FragmentReuseBindingRow,
    GateResultRow,
    GenerationAttemptRow,
    GenerationPlanRow,
    GenerationRunRow,
    GenerationWorkUnitRow,
    MediaTaskRow,
    ProjectRow,
    SourceOutlineCandidateRow,
    SealedStageAggregateRow,
    StageHeadRow,
    StagePlanRow,
    StoryGraphTopologyRow,
    WorkUnitRepairScopeRow,
)
from .approvals import ApprovalDecision
from .constants import CURRENT_STAGE_SCHEMA_VERSION, LEGACY_STAGE_SCHEMA_VERSION
from .media_tasks import GenericMediaTaskPersistence


def project_from_row(row: ProjectRow) -> Project:
    return Project(
        id=row.id, revision=row.revision, lifecycle_revision=row.lifecycle_revision,
        lifecycle_status=ProjectLifecycleStatus(row.lifecycle_status),
        archived_at=_stored_utc(row.archived_at) if row.archived_at else None,
        brief=ProjectBrief.model_validate(row.brief), created_at=_stored_utc(row.created_at),
        updated_at=_stored_utc(row.updated_at),
    )


def latest_run_summary_from_row(row: GenerationRunRow) -> LatestRunSummary:
    return LatestRunSummary(
        id=row.id, kind=RunKind(row.kind), status=RunStatus(row.status),
        requested_stages=[StageName(stage) for stage in row.requested_stages],
        created_at=_stored_utc(row.created_at),
        finished_at=_stored_utc(row.finished_at) if row.finished_at else None,
    )


def stage_head_from_row(row: StageHeadRow) -> StageHead:
    return StageHead(
        stage=StageName(row.stage), status=StageStatus(row.status), revision=row.revision,
        entity_revision_id=row.entity_revision_id, content_hash=row.content_hash,
        schema_version=row.schema_version,
        input_revisions={StageName(key): value for key, value in row.input_revisions.items()},
        stale_reasons=list(row.stale_reasons), updated_at=row.updated_at,
    )


def entity_revision_from_row(row: EntityRevisionRow) -> EntityRevision:
    return EntityRevision(
        id=row.id, project_id=row.project_id, stage=StageName(row.stage), revision=row.revision,
        parent_revision_id=row.parent_revision_id, content_hash=row.content_hash,
        schema_version=row.schema_version,
        input_revisions={StageName(key): value for key, value in row.input_revisions.items()},
        payload=row.payload, created_at=row.created_at,
    )


def decode_stage_payload(
    stage: StageName, payload: dict[str, Any], schema_version: int | None
) -> StagePayload:
    """Decode according to stored evidence, never a live default."""

    if schema_version not in {LEGACY_STAGE_SCHEMA_VERSION, CURRENT_STAGE_SCHEMA_VERSION}:
        raise SchemaResetRequiredError(stage=stage, schema_version=schema_version)
    return stage_payload_model(stage, schema_version=schema_version).model_validate(payload)


def decode_current_stage_payload(
    stage: StageName, payload: dict[str, Any], schema_version: int | None
) -> StagePayload:
    if schema_version != CURRENT_STAGE_SCHEMA_VERSION:
        raise SchemaResetRequiredError(stage=stage, schema_version=schema_version)
    return decode_stage_payload(stage, payload, schema_version)


def gate_result_from_row(row: GateResultRow) -> GateResult:
    return GateResult(
        id=row.id, gate_id=row.gate_id, gate_set_version=row.gate_version,
        evaluated_input_hash=row.evaluation_input_hash, required=row.required,
        status=row.status, severity=row.severity, entity_path=tuple(row.entity_path),
        evidence=tuple(GateEvidence.model_validate(item) for item in row.evidence),
        reason=row.reason,
    )


def approval_decision_from_row(row: ApprovalDecisionRow) -> ApprovalDecision:
    return ApprovalDecision(
        id=row.id, project_id=row.project_id, entity_revision_id=row.entity_revision_id,
        subject_type=row.subject_type, subject_id=row.subject_id,
        subject_revision=row.subject_revision, content_hash=row.content_hash,
        canonical_input_revisions=tuple(
            (StageName(stage), revision)
            for stage, revision in sorted(row.canonical_input_revisions.items())
        ),
        gate_set_version=row.gate_set_version, decision=row.decision, reviewer=row.reviewer,
        note=row.note, created_at=_stored_utc(row.created_at),
    )


def run_from_row(row: GenerationRunRow) -> GenerationRun:
    return GenerationRun(
        id=row.id, project_id=row.project_id, kind=RunKind(row.kind),
        parent_run_id=row.parent_run_id,
        repair_stage=StageName(row.repair_stage) if row.repair_stage else None,
        repair_source=RepairSource.model_validate(row.repair_source) if row.repair_source else None,
        work_unit_repair_scope_id=row.work_unit_repair_scope_id,
        provider_snapshot=dict(row.provider_snapshot),
        requested_stages=[StageName(stage) for stage in row.requested_stages],
        status=RunStatus(row.status), canonical_snapshot=CanonicalSnapshot.model_validate(row.canonical_snapshot),
        instructions=row.instructions, legacy_unsealed=row.legacy_unsealed,
        result_revision_ids=list(row.result_revision_ids), error=row.error,
        failure_code=row.failure_code,
        failed_stage=StageName(row.failed_stage) if row.failed_stage else None,
        created_at=row.created_at, started_at=row.started_at, finished_at=row.finished_at,
    )


def attempt_from_row(row: GenerationAttemptRow) -> GenerationAttempt:
    return GenerationAttempt(
        id=row.id, run_id=row.run_id, work_unit_id=row.work_unit_id, stage=StageName(row.stage),
        attempt_number=row.attempt_number, attempt_kind=GenerationAttemptKind(row.attempt_kind),
        source_attempt_id=row.source_attempt_id, status=AttemptStatus(row.status),
        provider=row.provider, model=row.model, error=row.error, dispatched_at=row.dispatched_at,
        response_persisted_at=row.response_persisted_at, provider_request_id=row.provider_request_id,
        outcome_unknown=row.outcome_unknown, outcome_code=row.outcome_code,
        started_at=row.started_at, finished_at=row.finished_at,
    )


def artifact_from_row(row: ArtifactRow) -> Artifact:
    return Artifact(
        id=row.id, run_id=row.run_id, attempt_id=row.attempt_id, work_unit_id=row.work_unit_id,
        source_artifact_id=row.source_artifact_id, stage=StageName(row.stage) if row.stage else None,
        kind=ArtifactKind(row.kind), media_type=row.media_type, content=row.content,
        content_hash=row.content_hash, created_at=row.created_at,
    )


def generation_plan_trace_from_row(row: GenerationPlanRow) -> GenerationPlanTrace:
    return GenerationPlanTrace(run_id=row.run_id, plan_hash=row.plan_hash, plan=dict(row.plan))


def stage_plan_trace_from_row(row: StagePlanRow) -> StagePlanTrace:
    return StagePlanTrace(
        id=row.id, run_id=row.run_id, stage=StageName(row.stage),
        stage_plan_hash=row.stage_plan_hash, dependency_hash=row.dependency_hash, plan=dict(row.plan),
    )


def work_unit_trace_from_row(row: GenerationWorkUnitRow) -> GenerationWorkUnitTrace:
    return GenerationWorkUnitTrace(
        id=row.id, run_id=row.run_id, stage_plan_id=row.stage_plan_id, stage=StageName(row.stage),
        sequence=row.sequence, selector=dict(row.selector), input_hash=row.input_hash,
        dependency_hash=row.dependency_hash, unit_dependency_hash=row.unit_dependency_hash,
        budget=dict(row.budget), estimated_input_tokens=row.estimated_input_tokens,
        context_window_tokens=row.context_window_tokens, status=WorkUnitStatus(row.status),
    )


def sealed_aggregate_trace_from_row(row: SealedStageAggregateRow) -> SealedStageAggregateTrace:
    return SealedStageAggregateTrace(
        id=row.id, run_id=row.run_id, stage_plan_id=row.stage_plan_id, stage=StageName(row.stage),
        manifest_hash=row.manifest_hash, manifest=dict(row.manifest), payload=dict(row.payload),
        created_at=_stored_utc(row.created_at),
    )


def repair_scope_from_row(row: WorkUnitRepairScopeRow) -> WorkUnitRepairScope:
    scope = WorkUnitRepairScope.model_validate(row.scope)
    if (
        scope.child_run_id != row.child_run_id
        or scope.scope_hash != row.scope_hash
        or stable_hash({key: value for key, value in row.scope.items() if key != "scopeHash"})
        != row.scope_hash
    ):
        raise InvalidTransitionError("stored exact repair scope identity is inconsistent")
    return scope


def fragment_reuse_binding_from_row(row: FragmentReuseBindingRow) -> FragmentReuseBinding:
    binding = FragmentReuseBinding.model_validate(row.binding)
    if (
        binding.id != row.id
        or binding.child_run_id != row.child_run_id
        or binding.child_stage_plan_id != row.child_stage_plan_id
        or binding.child_work_unit_id != row.child_work_unit_id
        or binding.binding_hash != row.binding_hash
        or stable_hash({key: value for key, value in row.binding.items() if key not in {"id", "bindingHash"}})
        != row.binding_hash
    ):
        raise InvalidTransitionError("stored fragment reuse binding identity is inconsistent")
    return binding


def story_graph_topology_trace_from_row(row: StoryGraphTopologyRow) -> StoryGraphTopologyTrace:
    return StoryGraphTopologyTrace(
        run_id=row.run_id, generation_plan_hash=row.generation_plan_hash,
        topology_hash=row.topology_hash, topology=dict(row.topology),
        created_at=_stored_utc(row.created_at),
    )


def media_task_from_row(row: MediaTaskRow) -> MediaTask:
    return GenericMediaTaskPersistence.media_task(row)


def project_row(session: Session, project_id: str) -> ProjectRow:
    row = session.get(ProjectRow, project_id)
    if row is None:
        raise NotFoundError(f"project not found: {project_id}")
    return row


def stage_row(session: Session, project_id: str, stage: StageName) -> StageHeadRow:
    row = session.scalar(
        select(StageHeadRow).where(
            StageHeadRow.project_id == project_id, StageHeadRow.stage == stage.value
        )
    )
    if row is None:
        raise NotFoundError(f"stage head not found: {project_id}/{stage.value}")
    return row


def run_row(session: Session, run_id: str) -> GenerationRunRow:
    row = session.get(GenerationRunRow, run_id)
    if row is None:
        raise NotFoundError(f"run not found: {run_id}")
    return row


def media_task_row(session: Session, task_id: str) -> MediaTaskRow:
    row = session.get(MediaTaskRow, task_id)
    if row is None:
        raise NotFoundError(f"media task not found: {task_id}")
    return row


def assert_active_project(row: ProjectRow) -> None:
    if ProjectLifecycleStatus(row.lifecycle_status) != ProjectLifecycleStatus.ACTIVE:
        raise InvalidTransitionError("archived projects are read-only")


def assert_lifecycle_revision(row: ProjectRow, expected_revision: int) -> None:
    if row.lifecycle_revision != expected_revision:
        raise RevisionConflictError("project-lifecycle", expected_revision, row.lifecycle_revision)


def project_is_busy_in_session(session: Session, project_id: str) -> bool:
    """Preserve lifecycle admission across durable and external work."""

    nonterminal_run = session.scalar(
        select(GenerationRunRow.id).where(
            GenerationRunRow.project_id == project_id,
            GenerationRunRow.status.not_in([status.value for status in TERMINAL_RUN_STATUSES]),
        ).limit(1)
    )
    nonterminal_media = session.scalar(
        select(MediaTaskRow.id).where(
            MediaTaskRow.project_id == project_id,
            MediaTaskRow.status.not_in([status.value for status in TERMINAL_MEDIA_TASK_STATUSES]),
        ).limit(1)
    )
    nonterminal_work_unit = session.scalar(
        select(GenerationWorkUnitRow.id).join(
            GenerationRunRow, GenerationWorkUnitRow.run_id == GenerationRunRow.id
        ).where(
            GenerationRunRow.project_id == project_id,
            GenerationWorkUnitRow.status.not_in(
                [status.value for status in TERMINAL_WORK_UNIT_STATUSES]
            ),
        ).limit(1)
    )
    prepared_outline_publication = session.scalar(
        select(SourceOutlineCandidateRow.job_id).where(
            SourceOutlineCandidateRow.project_id == project_id,
            SourceOutlineCandidateRow.status == "prepared",
        ).limit(1)
    )
    return any(
        item is not None
        for item in (
            nonterminal_run, nonterminal_media, nonterminal_work_unit,
            prepared_outline_publication,
        )
    )
