"""Durable work-unit attempt and provider-response persistence."""

from __future__ import annotations

from typing import Any
from ...domain import Artifact, ArtifactKind, AttemptStatus, GenerationAttempt, GenerationAttemptKind, RunStatus, StageName, WorkUnitStatus, utc_now
from ..schema import ArtifactRow, GenerationAttemptRow, GenerationWorkUnitRow
from sqlalchemy.exc import IntegrityError
from ...exceptions import InvalidTransitionError, NotFoundError
from ..codec import _json_data, stable_hash
from sqlalchemy import select

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..legacy_repository import SQLiteRepository


class ProjectGenerationAttemptPersistence:
    """Own claim, dispatch, raw-response, and unknown-outcome evidence."""

    def __init__(self, repository: SQLiteRepository) -> None:
        self._repository = repository

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
        repository = self._repository

        try:
            with repository._work_unit_claim_write() as session:
                unit = session.get(GenerationWorkUnitRow, work_unit_id)
                if unit is None:
                    raise NotFoundError(f"generation work unit not found: {work_unit_id}")
                run = repository._run_row(session, unit.run_id)
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
        repository = self._repository

        with repository._read() as session:
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
            return repository._attempt(row)
    def mark_attempt_dispatched(self, attempt_id: str) -> GenerationAttempt:
        """Commit the non-idempotent provider-boundary marker before an HTTP call."""
        repository = self._repository

        with repository._write() as session:
            row = session.get(GenerationAttemptRow, attempt_id)
            if row is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            if row.work_unit_id is None:
                raise InvalidTransitionError("only work-unit attempts have dispatch markers")
            repository._attempt_work_unit_unsealed_in_session(session, row)
            if AttemptStatus(row.status) != AttemptStatus.RUNNING:
                raise InvalidTransitionError(f"cannot dispatch attempt from {row.status}")
            run = repository._run_row(session, row.run_id)
            if RunStatus(run.status) != RunStatus.RUNNING:
                raise InvalidTransitionError(
                    f"cannot dispatch attempt while run is {run.status}"
                )
            if row.dispatched_at is None:
                row.dispatched_at = utc_now()
            return repository._attempt(row)
    def persist_attempt_response(
        self,
        attempt_id: str,
        content: Any,
        *,
        provider_request_id: str | None = None,
    ) -> Artifact:
        """Atomically retain raw response evidence before parsing or validation."""
        repository = self._repository

        repository._assert_secret_free_artifact_content(content)
        with repository._write() as session:
            attempt = session.get(GenerationAttemptRow, attempt_id)
            if attempt is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            if attempt.work_unit_id is None or attempt.dispatched_at is None:
                raise InvalidTransitionError("a provider response requires a durable dispatch marker")
            repository._attempt_work_unit_unsealed_in_session(session, attempt)
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
                return repository._artifact(existing)
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
        repository = self._repository

        with repository._write() as session:
            row = session.get(GenerationAttemptRow, attempt_id)
            if row is None:
                raise NotFoundError(f"generation attempt not found: {attempt_id}")
            if row.work_unit_id is None or row.dispatched_at is None:
                raise InvalidTransitionError("only dispatched work-unit attempts can become outcome_unknown")
            repository._attempt_work_unit_unsealed_in_session(session, row)
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
            return repository._attempt(row)
