from __future__ import annotations

import pytest

from plotloom.domain import (
    AttemptStatus,
    GenerationAttemptKind,
    ProjectBrief,
    RunKind,
    StageName,
    WorkUnitFailureDisposition,
    WorkUnitStatus,
)
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence import SQLiteRepository


def _running_bible_unit(repository: SQLiteRepository):
    project = repository.create_project(
        ProjectBrief(title="纠错谱系", synopsis="模型必须修正一份不合格的故事圣经。")
    )
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(run.id)
    repository.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    return run, repository.list_generation_work_units(run.id)[0]


def _known_rejection(repository: SQLiteRepository, attempt_id: str, *, correction_allowed: bool) -> None:
    repository.mark_attempt_dispatched(attempt_id)
    repository.persist_attempt_response(attempt_id, {"choices": [{"message": {"content": "{}"}}]})
    repository.finish_attempt(
        attempt_id,
        AttemptStatus.FAILED,
        error="schema rejected",
        outcome_code="schema.invalid",
        allow_correction=correction_allowed,
        failure_disposition=WorkUnitFailureDisposition.QUARANTINED,
    )


def test_two_visible_corrections_form_a_bounded_durable_lineage_then_quarantine() -> None:
    repository = SQLiteRepository("sqlite://")
    try:
        run, unit = _running_bible_unit(repository)
        first = repository.allocate_attempt_for_work_unit(
            unit.id, max_attempts=3, attempt_kind=GenerationAttemptKind.PRIMARY
        )
        _known_rejection(repository, first.id, correction_allowed=True)

        second = repository.allocate_attempt_for_work_unit(
            unit.id,
            max_attempts=3,
            attempt_kind=GenerationAttemptKind.CORRECTION,
            source_attempt_id=first.id,
        )
        assert second.attempt_number == 2
        assert second.attempt_kind == GenerationAttemptKind.CORRECTION
        assert second.source_attempt_id == first.id
        _known_rejection(repository, second.id, correction_allowed=True)

        third = repository.allocate_attempt_for_work_unit(
            unit.id,
            max_attempts=3,
            attempt_kind=GenerationAttemptKind.CORRECTION,
            source_attempt_id=second.id,
        )
        assert third.attempt_number == 3
        _known_rejection(repository, third.id, correction_allowed=False)

        trace = repository.get_run_trace(run.id)
        attempts = [item for item in trace.attempts if item.work_unit_id == unit.id]
        assert [(item.attempt_number, item.attempt_kind, item.source_attempt_id) for item in attempts] == [
            (1, GenerationAttemptKind.PRIMARY, None),
            (2, GenerationAttemptKind.CORRECTION, first.id),
            (3, GenerationAttemptKind.CORRECTION, second.id),
        ]
        assert all(item.outcome_code == "schema.invalid" for item in attempts)
        assert repository.list_generation_work_units(run.id)[0].status == WorkUnitStatus.QUARANTINED
        with pytest.raises(InvalidTransitionError):
            repository.allocate_attempt_for_work_unit(
                unit.id,
                max_attempts=3,
                attempt_kind=GenerationAttemptKind.CORRECTION,
                source_attempt_id=third.id,
            )
    finally:
        repository.close()


def test_outcome_unknown_is_never_a_correction_source_or_blind_replay_target() -> None:
    repository = SQLiteRepository("sqlite://")
    try:
        _run, unit = _running_bible_unit(repository)
        attempt = repository.allocate_attempt_for_work_unit(unit.id, max_attempts=3)
        repository.mark_attempt_dispatched(attempt.id)
        unknown = repository.mark_attempt_outcome_unknown(attempt.id, error="socket lost after send")
        assert unknown.outcome_code == "provider.outcome_unknown"
        assert unknown.outcome_unknown is True
        assert repository.list_generation_work_units(_run.id)[0].status == WorkUnitStatus.OUTCOME_UNKNOWN
        with pytest.raises(InvalidTransitionError):
            repository.allocate_attempt_for_work_unit(
                unit.id,
                max_attempts=3,
                attempt_kind=GenerationAttemptKind.CORRECTION,
                source_attempt_id=attempt.id,
            )
    finally:
        repository.close()
