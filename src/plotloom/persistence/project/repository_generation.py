"""Typed generation-runtime surface for a single bound project."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from ...domain import (
    Artifact, AttemptStatus, GenerationAttemptKind, MediaKind, MediaTaskStatus,
    RepairSource, RunKind, StageName, StartupRecoveryPlan, WorkUnitFailureDisposition,
)
from ...exceptions import InvalidTransitionError


class ProjectGenerationRepository:
    """Only the lifecycle/pipeline operations required by project execution."""

    def __init__(self, root: Any) -> None:
        self._root = root

    @contextmanager
    def admit_provider_snapshot(self, provider_snapshot: dict[str, Any]) -> Iterator[None]:
        previous = self._root._admitted_provider_snapshot_hash
        self._root._admitted_provider_snapshot_hash = self._stable_hash(provider_snapshot)
        try:
            yield
        finally:
            self._root._admitted_provider_snapshot_hash = previous

    def create_run(
        self, project_id: str, kind: RunKind, requested_stages: Sequence[StageName],
        *, instructions: str | None = None, parent_run_id: str | None = None,
        repair_stage: StageName | None = None, repair_source: RepairSource | None = None,
        provider_snapshot: dict[str, Any] | None = None,
    ):
        return self._root._generation_snapshots.create_run(
            project_id, kind, requested_stages, instructions=instructions,
            parent_run_id=parent_run_id, repair_stage=repair_stage,
            repair_source=repair_source, provider_snapshot=provider_snapshot,
        )

    def get_run(self, run_id: str):
        return self._root._generation_snapshots.get_run(run_id)

    def get_generation_plan(self, run_id: str):
        return self._root._generation_snapshots.get_generation_plan(run_id)

    def get_story_graph_topology(self, run_id: str):
        return self._root._generation_snapshots.get_story_graph_topology(run_id)

    def get_snapshot_stage_payload(self, run_id: str, stage: StageName):
        return self._root._generation_snapshots.get_snapshot_stage_payload(run_id, stage)

    def assert_run_inputs_current(self, run_id: str):
        return self._root._generation_snapshots.assert_run_inputs_current(run_id)

    def get_or_create_stage_plan(self, run_id: str, stage: StageName, *, dependencies: dict[StageName, Any] | None = None):
        return self._root._generation_plans.get_or_create_stage_plan(run_id, stage, dependencies=dependencies)

    def get_or_create_repair_stage_plan(self, child_run_id: str, stage: StageName, *, dependencies: dict[StageName, Any] | None = None):
        return self._root._generation_plans.get_or_create_repair_stage_plan(child_run_id, stage, dependencies=dependencies)

    def list_generation_work_units(self, run_id: str):
        return self._root._generation_plans.list_generation_work_units(run_id)

    def get_recoverable_attempt_for_work_unit(self, work_unit_id: str):
        return self._root._generation_attempts.get_recoverable_attempt_for_work_unit(work_unit_id)

    def allocate_attempt_for_work_unit(self, work_unit_id: str, *, provider: str | None = None, model: str | None = None, attempt_kind: GenerationAttemptKind = GenerationAttemptKind.PRIMARY, source_attempt_id: str | None = None, max_attempts: int | None = None):
        return self._root._generation_attempts.allocate_attempt_for_work_unit(work_unit_id, provider=provider, model=model, attempt_kind=attempt_kind, source_attempt_id=source_attempt_id, max_attempts=max_attempts)

    def mark_attempt_dispatched(self, attempt_id: str):
        return self._root._generation_attempts.mark_attempt_dispatched(attempt_id)

    def persist_attempt_response(self, attempt_id: str, content: Any, *, provider_request_id: str | None = None):
        return self._root._generation_attempts.persist_attempt_response(attempt_id, content, provider_request_id=provider_request_id)

    def mark_attempt_outcome_unknown(self, attempt_id: str, *, error: str):
        return self._root._generation_attempts.mark_attempt_outcome_unknown(attempt_id, error=error)

    def get_run_execution_trace(self, run_id: str):
        return self._root._generation_progress.get_run_execution_trace(run_id)

    def seal_stage_aggregate(self, run_id: str, stage: StageName, *, candidate_artifact_ids: list[str]):
        return self._root._generation_aggregates.seal_stage_aggregate(run_id, stage, candidate_artifact_ids=candidate_artifact_ids)

    def seal_repair_stage_aggregate(self, child_run_id: str, stage: StageName, *, candidate_artifact_ids: list[str]):
        return self._root._generation_aggregates.seal_repair_stage_aggregate(child_run_id, stage, candidate_artifact_ids=candidate_artifact_ids)

    def get_repair_stage_dependencies(self, child_run_id: str, stage: StageName):
        return self._root._generation_repairs.get_repair_stage_dependencies(child_run_id, stage)

    def prepare_repair_stage_reuse(self, child_run_id: str, stage: StageName):
        return self._root._generation_reuse.prepare_repair_stage_reuse(child_run_id, stage)

    def materialize_fragment_reuse_binding(self, child_run_id: str, binding_id: str):
        return self._root._generation_reuse.materialize_fragment_reuse_binding(child_run_id, binding_id)

    def commit_sealed_run(self, run_id: str, *, sealed_aggregate_ids: list[str]):
        return self._root._generation_lifecycle.commit_sealed_run(run_id, sealed_aggregate_ids=sealed_aggregate_ids)

    def commit_run_outputs(self, run_id: str, payloads: dict[StageName, Any]):
        return self._root._generation_lifecycle.commit_run_outputs(run_id, payloads)

    def start_run(self, run_id: str):
        if run_id in self._root._recovered_run_ids():
            raise InvalidTransitionError("recovery_required: restored unfinished work cannot be resumed")
        return self._root._generation_lifecycle.start_run(run_id)

    def finish_run(self, run_id: str, *, result_revision_ids: Sequence[str] | None = None, error: str | None = None, quarantine_reason: str | None = None, failure_code: str | None = None, failed_stage: StageName | None = None):
        return self._root._generation_lifecycle.finish_run(run_id, result_revision_ids=result_revision_ids, error=error, quarantine_reason=quarantine_reason, failure_code=failure_code, failed_stage=failed_stage)

    def cancel_run(self, run_id: str):
        return self._root._generation_lifecycle.cancel_run(run_id)

    def get_run_trace(self, run_id: str):
        return self._root._generation_evidence.get_run_trace(run_id)

    def add_artifact(self, artifact: Artifact):
        return self._root._generation_evidence.add_artifact(artifact)

    def get_artifact(self, artifact_id: str):
        return self._root._generation_evidence.get_artifact(artifact_id)

    def create_attempt(self, run_id: str, stage: StageName, *, provider: str | None = None, model: str | None = None):
        return self._root._generation_evidence.create_attempt(run_id, stage, provider=provider, model=model)

    def finish_attempt(self, attempt_id: str, status: AttemptStatus, *, error: str | None = None, outcome_code: str | None = None, allow_correction: bool = False, failure_disposition: WorkUnitFailureDisposition | None = None):
        return self._root._generation_evidence.finish_attempt(attempt_id, status, error=error, outcome_code=outcome_code, allow_correction=allow_correction, failure_disposition=failure_disposition)

    def create_work_unit_repair_run(self, source_run_id: str, work_unit_id: str, *, idempotency_key: str, instructions: str | None = None):
        return self._root._generation_repairs.create_work_unit_repair_run(source_run_id, work_unit_id, idempotency_key=idempotency_key, instructions=instructions)

    def get_work_unit_repair_scope(self, child_run_id: str):
        return self._root._generation_repairs.get_work_unit_repair_scope(child_run_id)

    def get_fragment_reuse_bindings(self, child_run_id: str):
        return self._root._generation_reuse.get_fragment_reuse_bindings(child_run_id)

    def list_project_runs(self, project_id: str, *, limit: int = 50):
        return self._root._generation_lifecycle.list_project_runs(project_id, limit=limit)

    def reconcile_startup_jobs(self) -> StartupRecoveryPlan:
        if self._root._recovery_operations_present():
            return StartupRecoveryPlan()
        return self._root._generation_recovery.reconcile_startup_jobs()

    @staticmethod
    def _stable_hash(value: dict[str, Any]) -> str:
        from ..codec import stable_hash
        return stable_hash(value)
