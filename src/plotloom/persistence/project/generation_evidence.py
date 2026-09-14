"""Legacy-compatible attempt, artifact, and compact trace persistence."""

from __future__ import annotations

from ...domain import Artifact, ArtifactKind, AttemptStatus, GenerationAttempt, GenerationAttemptKind, RunStatus, RunTrace, StageName, WorkUnitFailureDisposition, WorkUnitStatus, utc_now
from ..schema import ArtifactRow, GenerationAttemptRow, GenerationWorkUnitRow
from ...exceptions import InvalidTransitionError, NotFoundError
from ..codec import _json_data
from sqlalchemy import select

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..legacy_repository import SQLiteRepository


class ProjectGenerationEvidencePersistence:
    """Legacy-compatible attempt, artifact, and compact trace persistence."""

    def __init__(self, repository: SQLiteRepository) -> None:
        self._repository = repository

    def create_attempt(
        self,
        run_id: str,
        stage: StageName,
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> GenerationAttempt:
        repository = self._repository
        with repository._write() as session:
            run = repository._run_row(session, run_id)
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
        repository = self._repository
        if status == AttemptStatus.RUNNING:
            raise InvalidTransitionError("finish_attempt requires a terminal attempt status")
        with repository._write() as session:
            row = session.get(GenerationAttemptRow, attempt_id)
            if row is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            unit = repository._attempt_work_unit_unsealed_in_session(session, row)
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
            return repository._attempt(row)
    def add_artifact(self, artifact: Artifact) -> Artifact:
        repository = self._repository
        repository._assert_secret_free_artifact_content(artifact.content)
        with repository._write() as session:
            repository._run_row(session, artifact.run_id)
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
                repository._assert_work_unit_unsealed_in_session(session, unit)
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
                        return repository._artifact(existing)
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
        repository = self._repository
        with repository._read() as session:
            row = session.get(ArtifactRow, artifact_id)
            if row is None:
                raise NotFoundError(f"artifact not found: {artifact_id}")
            return repository._artifact(row)
    def get_run_trace(self, run_id: str) -> RunTrace:
        repository = self._repository
        with repository._read() as session:
            run = repository._run(repository._run_row(session, run_id))
            attempts = [
                repository._attempt(row)
                for row in session.scalars(
                    select(GenerationAttemptRow)
                    .where(GenerationAttemptRow.run_id == run_id)
                    .order_by(GenerationAttemptRow.started_at, GenerationAttemptRow.attempt_number)
                ).all()
            ]
            artifacts = [
                repository._artifact(row)
                for row in session.scalars(
                    select(ArtifactRow).where(ArtifactRow.run_id == run_id).order_by(ArtifactRow.created_at)
                ).all()
            ]
            if run.result_revision_ids:
                snapshot_is_current = repository._run_outputs_are_current(session, repository._run_row(session, run_id))
            else:
                current = repository._snapshot_in_session(session, run.project_id)
                snapshot_is_current = current.snapshot_hash == run.canonical_snapshot.snapshot_hash
            return RunTrace(
                run=run,
                attempts=attempts,
                artifacts=artifacts,
                snapshot_is_current=snapshot_is_current,
            )
