"""Run lifecycle and atomic canonical output installation persistence."""

from __future__ import annotations

from typing import Any
from ...domain import (
    Artifact, ArtifactKind, AttemptStatus, CanonicalSnapshot, DialogueTimingProfile,
    TERMINAL_RUN_STATUSES, GenerationRun, RunStatus, StageHead, StageName,
    StagePayload, WorkUnitStatus, upstream_stages, utc_now,
)
from ..schema import ArtifactRow, EntityRevisionRow, GenerationAttemptRow, GenerationRunRow, GenerationWorkUnitRow, SealedStageAggregateRow, StagePlanRow
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from collections.abc import Sequence
from sqlalchemy import select
from ..codec import stable_hash
from ...domain import stage_payload_model
from ...generation.planning import StagePlan
from .constants import CURRENT_STAGE_SCHEMA_VERSION
from .canonical import ProjectCanonicalPersistence
from .generation_snapshots import ProjectGenerationSnapshots

from .generation_access import GenerationPersistenceAccess


class ProjectGenerationLifecyclePersistence:
    """Run lifecycle and atomic canonical output installation persistence."""

    def __init__(
        self,
        access: GenerationPersistenceAccess,
        snapshots: ProjectGenerationSnapshots,
        canonical: ProjectCanonicalPersistence,
    ) -> None:
        self._access = access
        self._snapshots = snapshots
        self._canonical = canonical

    def list_project_runs(self, project_id: str, *, limit: int = 50) -> list[GenerationRun]:
        access = self._access
        if not 1 <= limit <= 200:
            raise ValueError("run list limit must be between 1 and 200")
        with access.leases.read() as session:
            access.rows.project(session, project_id)
            rows = session.scalars(
                select(GenerationRunRow)
                .where(GenerationRunRow.project_id == project_id)
                .order_by(GenerationRunRow.created_at.desc())
                .limit(limit)
            ).all()
            return [access.codecs.run(row) for row in rows]

    def list_project_run_ids_for_index(self, project_id: str) -> list[str]:
        """Return all durable IDs for startup index rebuild, not an API listing."""

        access = self._access
        with access.leases.read() as session:
            access.rows.project(session, project_id)
            return list(
                session.scalars(
                    select(GenerationRunRow.id)
                    .where(GenerationRunRow.project_id == project_id)
                    .order_by(GenerationRunRow.created_at)
                )
            )

    def list_project_runs_for_index(self, project_id: str) -> list[GenerationRun]:
        """Return the frozen routing fields used only during startup rebuild."""

        access = self._access
        with access.leases.read() as session:
            access.rows.project(session, project_id)
            rows = session.scalars(
                select(GenerationRunRow)
                .where(GenerationRunRow.project_id == project_id)
                .order_by(GenerationRunRow.created_at)
            ).all()
            return [access.codecs.run(row) for row in rows]

    def start_run(self, run_id: str) -> GenerationRun:
        access = self._access
        with access.leases.write() as session:
            row = access.rows.run(session, run_id)
            status = RunStatus(row.status)
            if status == RunStatus.CANCEL_REQUESTED:
                row.status = RunStatus.CANCELLED.value
                row.finished_at = utc_now()
                return access.codecs.run(row)
            if status != RunStatus.QUEUED:
                raise InvalidTransitionError(f"cannot start run from {status.value}")
            row.status = RunStatus.RUNNING.value
            row.started_at = utc_now()
            return access.codecs.run(row)
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
        access = self._access

        with access.leases.lifecycle_write() as session:
            run_row = access.rows.run(session, run_id)
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
                session, run_row
            )
            payloads = {
                StageName(aggregate.stage): access.codecs.decode_current_stage_payload(
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
        access = self._access
        with access.leases.write() as session:
            row = access.rows.run(session, run_id)
            if RunStatus(row.status) in TERMINAL_RUN_STATUSES:
                return access.codecs.run(row)
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
            return access.codecs.run(row)
    def cancel_run(self, run_id: str) -> GenerationRun:
        access = self._access
        with access.leases.write() as session:
            row = access.rows.run(session, run_id)
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
                return access.codecs.run(row)
            return access.codecs.run(row)

    @staticmethod
    def _frozen_dialogue_timing_profile_from_stage_plan(
        stage_plan: Any,
    ) -> DialogueTimingProfile:
        if stage_plan.stage == StageName.SCENE_BEATS:
            profile, description = stage_plan.dialogue_timing_profile, "Scene Beats"
        elif stage_plan.stage == StageName.STORYBOARD:
            profile, description = stage_plan.storyboard_dialogue_timing_profile, "Storyboard"
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
        self, session: Any, run_row: GenerationRunRow
    ) -> DialogueTimingProfile | None:
        requested = {StageName(value) for value in run_row.requested_stages}
        if not requested & {StageName.SCENE_BEATS, StageName.STORYBOARD}:
            return None
        profiles: list[DialogueTimingProfile] = []
        for stage in (StageName.SCENE_BEATS, StageName.STORYBOARD):
            if stage not in requested:
                continue
            description = "Scene Beats" if stage == StageName.SCENE_BEATS else "Storyboard"
            row = session.scalar(
                select(StagePlanRow).where(
                    StagePlanRow.run_id == run_row.id, StagePlanRow.stage == stage.value
                )
            )
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
        parsed_payloads = {
            stage: stage_payload_model(
                stage, schema_version=CURRENT_STAGE_SCHEMA_VERSION
            ).model_validate(payload)
            for stage, payload in payloads.items()
        }
        with self._access.leases.lifecycle_write() as session:
            run_row = self._access.rows.run(session, run_id)
            return self._commit_parsed_run_outputs_in_session(session, run_row, parsed_payloads)

    def _commit_parsed_run_outputs_in_session(
        self,
        session: Any,
        run_row: GenerationRunRow,
        parsed_payloads: dict[StageName, StagePayload],
        *,
        dialogue_timing_profile: DialogueTimingProfile | None = None,
    ) -> tuple[GenerationRun, list[StageHead]]:
        if RunStatus(run_row.status) != RunStatus.RUNNING:
            raise InvalidTransitionError(
                f"cannot install generated output while run is {run_row.status}"
            )
        requested = [StageName(value) for value in run_row.requested_stages]
        if set(parsed_payloads) != set(requested):
            raise InvalidTransitionError("commit requires exactly one candidate for every requested stage")
        if run_row.result_revision_ids:
            raise InvalidTransitionError("run outputs have already been committed")
        snapshot = self._snapshots.assert_run_inputs_current_in_session(session, run_row)
        project_row = self._access.rows.project(session, run_row.project_id)
        self._access.admission.assert_active_project(project_row)
        results: list[StageHead] = []
        for stage in requested:
            current_head = self._access.rows.stage(session, run_row.project_id, stage)
            snapshot_head = snapshot.stage_heads[stage]
            if current_head.revision != snapshot_head.revision:
                raise RevisionConflictError(
                    f"stage:{stage.value}", snapshot_head.revision, current_head.revision
                )
            now = utc_now()
            head, revision_row = self._canonical._install_stage_in_session(
                session, project_row, stage, parsed_payloads[stage],
                expected_revision=snapshot_head.revision, now=now, allow_noop=False,
                dialogue_timing_profile=dialogue_timing_profile,
            )
            if revision_row is None:
                raise InvalidTransitionError(
                    "generated stage installation must create a canonical revision"
                )
            run_row.result_revision_ids = [*run_row.result_revision_ids, revision_row.id]
            canonical_trace = {
                "entityRevisionId": revision_row.id,
                "revision": revision_row.revision,
                "contentHash": revision_row.content_hash,
                "inputRevisions": dict(revision_row.input_revisions),
            }
            artifact = Artifact(
                run_id=run_row.id, stage=stage, kind=ArtifactKind.CANONICAL,
                content=canonical_trace, content_hash=stable_hash(canonical_trace), created_at=now,
            )
            session.add(ArtifactRow(
                id=artifact.id, run_id=artifact.run_id, attempt_id=None, work_unit_id=None,
                source_artifact_id=None, stage=stage.value, kind=ArtifactKind.CANONICAL.value,
                media_type=artifact.media_type, content=canonical_trace,
                content_hash=artifact.content_hash, created_at=now,
            ))
            results.append(head)
        run_row.status = RunStatus.SUCCEEDED.value
        run_row.error = None
        run_row.finished_at = utc_now()
        return self._access.codecs.run(run_row), results

    def _run_outputs_are_current(self, session: Any, row: GenerationRunRow) -> bool:
        snapshot = CanonicalSnapshot.model_validate(row.canonical_snapshot)
        project = self._access.rows.project(session, row.project_id)
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
            upstream for requested_stage in requested for upstream in upstream_stages(requested_stage)
            if upstream not in requested
        }
        for stage in requested:
            if self._access.rows.stage(session, row.project_id, stage).entity_revision_id != result_by_stage[stage].id:
                return False
        return all(
            self._access.rows.stage(session, row.project_id, stage).revision
            == snapshot.stage_heads[stage].revision
            for stage in required_inputs
        )

    @staticmethod
    def _cancel_run_work_units_in_session(
        session: Any, run_id: str, *, now: Any, attempt_error: str
    ) -> None:
        running_attempts = session.scalars(select(GenerationAttemptRow).where(
            GenerationAttemptRow.run_id == run_id,
            GenerationAttemptRow.status == AttemptStatus.RUNNING.value,
        )).all()
        for attempt in running_attempts:
            attempt.status = AttemptStatus.CANCELLED.value
            attempt.error = attempt_error
            attempt.finished_at = now
        units = session.scalars(select(GenerationWorkUnitRow).where(
            GenerationWorkUnitRow.run_id == run_id
        )).all()
        for unit in units:
            if unit.status in {WorkUnitStatus.QUEUED.value, WorkUnitStatus.RUNNING.value}:
                unit.status = WorkUnitStatus.CANCELLED.value
