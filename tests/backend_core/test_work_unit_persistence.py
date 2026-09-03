from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from alembic import command
from sqlalchemy import create_engine, text

from plotloom.domain import (
    Artifact,
    ArtifactKind,
    AttemptStatus,
    RunKind,
    RunStatus,
    StageName,
    WorkUnitStatus,
)
from plotloom.exceptions import InvalidTransitionError
from plotloom.generation.fragments import StoryBibleFragment, StoryGraphFragment
from plotloom.persistence import SQLiteRepository, stable_hash
from plotloom.schema import SchemaMigrator

from .conftest import all_stage_payloads


def _running_bible_unit(repository: SQLiteRepository, brief):
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(run.id)
    repository.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    return run, repository.list_generation_work_units(run.id)[0]


def _persist_bible_unit_evidence(
    repository: SQLiteRepository,
    run_id: str,
    payload,
    *,
    validation_content: object | None = None,
):
    return _persist_stage_unit_evidence(
        repository,
        run_id,
        StageName.STORY_BIBLE,
        payload,
        validation_content=validation_content,
    )


def _persist_stage_unit_evidence(
    repository: SQLiteRepository,
    run_id: str,
    stage: StageName,
    payload,
    *,
    validation_content: object | None = None,
):
    stage_plan = repository.get_or_create_stage_plan(run_id, stage)
    unit = repository.list_generation_work_units(run_id)[0]
    if stage != StageName.STORY_BIBLE:
        unit = next(
            work_unit
            for work_unit in repository.list_generation_work_units(run_id)
            if work_unit.stage == stage
        )
    attempt = repository.allocate_attempt_for_work_unit(unit.id, provider="local", model="qwen")
    repository.mark_attempt_dispatched(attempt.id)
    prompt = {"messages": [{"role": "user", "content": "make a bible"}]}
    repository.add_artifact(
        Artifact(
            run_id=run_id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=stage,
            kind=ArtifactKind.PROMPT,
            content=prompt,
            content_hash=stable_hash(prompt),
        )
    )
    repository.persist_attempt_response(attempt.id, {"rawResponse": "{}"}, provider_request_id="req-1")
    validation = validation_content if validation_content is not None else {"accepted": True, "issues": []}
    repository.add_artifact(
        Artifact(
            run_id=run_id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=stage,
            kind=ArtifactKind.VALIDATION,
            content=validation,
            content_hash=stable_hash(validation),
        )
    )
    fragment_type = {
        StageName.STORY_BIBLE: StoryBibleFragment,
        StageName.STORY_GRAPH: StoryGraphFragment,
    }[stage]
    fragment = fragment_type(
        stage_plan_hash=stage_plan.stage_plan_hash,
        work_unit_id=unit.id,
        payload=payload,
    )
    fragment_data = fragment.model_dump(mode="json", by_alias=False)
    candidate = repository.add_artifact(
        Artifact(
            run_id=run_id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=stage,
            kind=ArtifactKind.CANDIDATE,
            content=fragment_data,
            content_hash=stable_hash(fragment_data),
        )
    )
    return stage_plan, unit, attempt, candidate


def _seal_bible_unit(repository: SQLiteRepository, run_id: str, payload) -> str:
    _, _, attempt, candidate = _persist_bible_unit_evidence(repository, run_id, payload)
    repository.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    aggregate = repository.seal_stage_aggregate(
        run_id,
        StageName.STORY_BIBLE,
        candidate_artifact_ids=[candidate.id],
    )
    return aggregate.id


def test_run_plan_is_persisted_before_child_rows_and_trace_is_additive(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])

    plan = repository.get_generation_plan(run.id)
    trace = repository.get_run_execution_trace(run.id)

    assert plan.run_id == run.id
    assert plan.canonical_snapshot_hash == run.canonical_snapshot.snapshot_hash
    assert trace.generation_plan is not None
    assert trace.generation_plan.plan_hash == plan.plan_hash
    assert trace.stage_plans == []
    assert trace.work_units == []


def test_run_plan_persists_effective_provider_output_ceiling(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={
            "textContextWindowTokens": 32_768,
            "textMaxOutputTokens": 1_024,
        },
    )

    plan = repository.get_generation_plan(run.id)
    assert plan.stage_budgets[StageName.STORY_BIBLE].max_output_tokens == 1_024

    repository.start_run(run.id)
    stage_plan = repository.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    assert stage_plan.work_units[0].budget.max_output_tokens == 1_024


def test_stage_plan_waits_for_requested_upstream_seal_and_is_idempotent(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH],
    )
    repository.start_run(run.id)

    with pytest.raises(InvalidTransitionError, match="StagePlan exists|aggregate is sealed"):
        repository.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)

    _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    first = repository.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)
    replay = repository.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)

    assert replay == first
    assert [plan.stage for plan in repository.list_stage_plans(run.id)] == [
        StageName.STORY_BIBLE,
        StageName.STORY_GRAPH,
    ]


def test_sealed_aggregate_is_exact_and_commit_reads_only_sealed_payloads(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(run.id)
    aggregate_id = _seal_bible_unit(repository, run.id, all_stage_payloads()[0])

    completed = repository.commit_sealed_run(run.id, sealed_aggregate_ids=[aggregate_id])
    trace = repository.get_run_execution_trace(run.id)

    assert completed.result_revision_ids
    assert trace.sealed_aggregates[0].id == aggregate_id
    assert trace.work_units[0].status == WorkUnitStatus.SUCCEEDED
    with pytest.raises(InvalidTransitionError, match="already been committed|run is succeeded"):
        repository.commit_sealed_run(run.id, sealed_aggregate_ids=[aggregate_id])


def test_work_unit_attempt_requires_dispatch_and_marks_unknown_outcomes(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(run.id)
    repository.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    unit = repository.list_generation_work_units(run.id)[0]
    attempt = repository.allocate_attempt_for_work_unit(unit.id)

    with pytest.raises(InvalidTransitionError, match="dispatch marker"):
        repository.persist_attempt_response(attempt.id, {"rawResponse": "not yet"})
    repository.mark_attempt_dispatched(attempt.id)
    unknown = repository.mark_attempt_outcome_unknown(attempt.id, error="deadline after submission")

    assert unknown.outcome_unknown is True
    assert repository.list_generation_work_units(run.id)[0].status == WorkUnitStatus.OUTCOME_UNKNOWN


def test_work_unit_validation_failure_requires_rebuild_until_exact_repair_exists(
    repository,
    brief,
) -> None:
    run, unit = _running_bible_unit(repository, brief)
    attempt = repository.allocate_attempt_for_work_unit(unit.id)
    repository.mark_attempt_dispatched(attempt.id)
    repository.persist_attempt_response(attempt.id, {"rawResponse": "{}"})
    rejected = {"accepted": False, "issues": [{"code": "schema", "message": "invalid"}]}
    repository.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.VALIDATION,
            content=rejected,
            content_hash=stable_hash(rejected),
        )
    )
    repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error="invalid candidate")
    repository.finish_run(run.id, quarantine_reason="invalid candidate")

    with pytest.raises(InvalidTransitionError, match="exact work-unit repair"):
        repository.create_repair_run(run.id)

    assert len(repository.list_project_runs(run.project_id)) == 1


def test_artifacts_cannot_cross_run_or_escape_work_unit_ownership(repository, brief) -> None:
    project = repository.create_project(brief)
    first = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    second = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(first.id)
    repository.get_or_create_stage_plan(first.id, StageName.STORY_BIBLE)
    unit = repository.list_generation_work_units(first.id)[0]
    attempt = repository.allocate_attempt_for_work_unit(unit.id)
    content = {"messages": []}

    with pytest.raises(InvalidTransitionError, match="declared run"):
        repository.add_artifact(
            Artifact(
                run_id=second.id,
                attempt_id=attempt.id,
                work_unit_id=unit.id,
                stage=StageName.STORY_BIBLE,
                kind=ArtifactKind.PROMPT,
                content=content,
                content_hash=stable_hash(content),
            )
        )


def test_work_unit_claim_is_single_use_except_safe_startup_recovery(repository, brief) -> None:
    run, unit = _running_bible_unit(repository, brief)
    first = repository.allocate_attempt_for_work_unit(unit.id)

    with pytest.raises(InvalidTransitionError, match="work unit is running"):
        repository.allocate_attempt_for_work_unit(unit.id)

    recovery = repository.reconcile_startup_jobs()

    assert recovery.resubmit_run_ids == [run.id]
    assert repository.get_run(run.id).status == RunStatus.QUEUED
    assert repository.list_generation_work_units(run.id)[0].status == WorkUnitStatus.QUEUED
    recovered = repository.get_run_trace(run.id).attempts[0]
    assert recovered.id == first.id
    assert recovered.status == AttemptStatus.FAILED
    assert recovered.dispatched_at is None

    repository.start_run(run.id)
    second = repository.allocate_attempt_for_work_unit(unit.id)

    assert second.attempt_number == 2
    with pytest.raises(InvalidTransitionError, match="work unit is running"):
        repository.allocate_attempt_for_work_unit(unit.id)


def test_attempt_numbers_are_local_to_each_work_unit(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS],
    )
    repository.start_run(run.id)
    bible_id = _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    assert bible_id
    _, _, graph_attempt, graph_candidate = _persist_stage_unit_evidence(
        repository,
        run.id,
        StageName.STORY_GRAPH,
        all_stage_payloads()[1],
    )
    repository.finish_attempt(graph_attempt.id, AttemptStatus.SUCCEEDED)
    repository.seal_stage_aggregate(
        run.id,
        StageName.STORY_GRAPH,
        candidate_artifact_ids=[graph_candidate.id],
    )
    repository.get_or_create_stage_plan(run.id, StageName.SCENE_BEATS)
    units = [
        unit
        for unit in repository.list_generation_work_units(run.id)
        if unit.stage == StageName.SCENE_BEATS
    ]
    assert len(units) > 1

    first = repository.allocate_attempt_for_work_unit(units[0].id)
    second = repository.allocate_attempt_for_work_unit(units[1].id)

    assert (first.attempt_number, second.attempt_number) == (1, 1)


def test_work_unit_claim_is_atomic_across_repository_instances(tmp_path, brief) -> None:
    database_url = f"sqlite:///{tmp_path / 'work-unit-claim.sqlite3'}"
    first_repository = SQLiteRepository(database_url)
    second_repository = SQLiteRepository(database_url)
    try:
        run, unit = _running_bible_unit(first_repository, brief)
        barrier = Barrier(2)

        def claim(repository: SQLiteRepository) -> tuple[str, object]:
            barrier.wait()
            try:
                return "claimed", repository.allocate_attempt_for_work_unit(unit.id)
            except InvalidTransitionError as error:
                return "rejected", error

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(claim, (first_repository, second_repository)))

        claimed = [outcome for outcome in outcomes if outcome[0] == "claimed"]
        rejected = [outcome for outcome in outcomes if outcome[0] == "rejected"]
        assert len(claimed) == 1
        assert len(rejected) == 1
        assert "work unit is running" in str(rejected[0][1])
        attempts = first_repository.get_run_trace(run.id).attempts
        assert [(attempt.work_unit_id, attempt.attempt_number) for attempt in attempts] == [
            (unit.id, 1)
        ]
    finally:
        second_repository.close()
        first_repository.close()


def test_seal_requires_succeeded_producer_and_accepted_object_validation(repository, brief) -> None:
    running, _ = _running_bible_unit(repository, brief)
    _, _, running_attempt, running_candidate = _persist_bible_unit_evidence(
        repository,
        running.id,
        all_stage_payloads()[0],
    )
    with pytest.raises(InvalidTransitionError, match="succeeded"):
        repository.seal_stage_aggregate(
            running.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[running_candidate.id],
        )

    failed, _ = _running_bible_unit(repository, brief)
    _, _, failed_attempt, failed_candidate = _persist_bible_unit_evidence(
        repository,
        failed.id,
        all_stage_payloads()[0],
    )
    repository.finish_attempt(failed_attempt.id, AttemptStatus.FAILED, error="invalid")
    with pytest.raises(InvalidTransitionError, match="succeeded"):
        repository.seal_stage_aggregate(
            failed.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[failed_candidate.id],
        )

    rejected, _ = _running_bible_unit(repository, brief)
    _, _, rejected_attempt, rejected_candidate = _persist_bible_unit_evidence(
        repository,
        rejected.id,
        all_stage_payloads()[0],
        validation_content={"accepted": False, "issues": ["bad"]},
    )
    repository.finish_attempt(rejected_attempt.id, AttemptStatus.SUCCEEDED)
    with pytest.raises(InvalidTransitionError, match="accepted: true"):
        repository.seal_stage_aggregate(
            rejected.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[rejected_candidate.id],
        )

    malformed, _ = _running_bible_unit(repository, brief)
    _, _, malformed_attempt, malformed_candidate = _persist_bible_unit_evidence(
        repository,
        malformed.id,
        all_stage_payloads()[0],
        validation_content=["accepted", True],
    )
    repository.finish_attempt(malformed_attempt.id, AttemptStatus.SUCCEEDED)
    with pytest.raises(InvalidTransitionError, match="object validation"):
        repository.seal_stage_aggregate(
            malformed.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[malformed_candidate.id],
        )

    assert running_attempt.status == AttemptStatus.RUNNING


def test_duplicate_producer_artifacts_are_rejected_before_they_can_be_sealed(repository, brief) -> None:
    run, _ = _running_bible_unit(repository, brief)
    _, unit, attempt, candidate = _persist_bible_unit_evidence(
        repository,
        run.id,
        all_stage_payloads()[0],
    )
    duplicate_prompt = {"messages": [{"role": "user", "content": "different prompt"}]}

    with pytest.raises(InvalidTransitionError, match="immutable prompt evidence"):
        repository.add_artifact(
            Artifact(
                run_id=run.id,
                attempt_id=attempt.id,
                work_unit_id=unit.id,
                stage=StageName.STORY_BIBLE,
                kind=ArtifactKind.PROMPT,
                content=duplicate_prompt,
                content_hash=stable_hash(duplicate_prompt),
            )
        )

    repository.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    sealed = repository.seal_stage_aggregate(
        run.id,
        StageName.STORY_BIBLE,
        candidate_artifact_ids=[candidate.id],
    )
    assert sealed.manifest["units"][0]["candidateArtifactId"] == candidate.id


def test_seal_freezes_attempt_and_artifact_mutation(repository, brief) -> None:
    run, _ = _running_bible_unit(repository, brief)
    _, unit, attempt, candidate = _persist_bible_unit_evidence(
        repository,
        run.id,
        all_stage_payloads()[0],
    )
    repository.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    repository.seal_stage_aggregate(
        run.id,
        StageName.STORY_BIBLE,
        candidate_artifact_ids=[candidate.id],
    )
    media_trace = {"uri": "local://sealed-trace"}

    with pytest.raises(InvalidTransitionError, match="after its work-unit stage aggregate is sealed"):
        repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error="late change")
    with pytest.raises(InvalidTransitionError, match="after its work-unit stage aggregate is sealed"):
        repository.add_artifact(
            Artifact(
                run_id=run.id,
                attempt_id=attempt.id,
                work_unit_id=unit.id,
                stage=StageName.STORY_BIBLE,
                kind=ArtifactKind.MEDIA,
                content=media_trace,
                content_hash=stable_hash(media_trace),
            )
        )


def test_cancel_wins_before_dispatch_and_before_seal(repository, brief) -> None:
    dispatch_run, dispatch_unit = _running_bible_unit(repository, brief)
    dispatch_attempt = repository.allocate_attempt_for_work_unit(dispatch_unit.id)
    assert repository.cancel_run(dispatch_run.id).status == RunStatus.CANCEL_REQUESTED
    with pytest.raises(InvalidTransitionError, match="run is cancel_requested"):
        repository.mark_attempt_dispatched(dispatch_attempt.id)
    cancelled = repository.finish_run(dispatch_run.id)
    assert cancelled.status == RunStatus.CANCELLED
    assert repository.list_generation_work_units(dispatch_run.id)[0].status == WorkUnitStatus.CANCELLED

    seal_run, _ = _running_bible_unit(repository, brief)
    _, seal_unit, seal_attempt, seal_candidate = _persist_bible_unit_evidence(
        repository,
        seal_run.id,
        all_stage_payloads()[0],
    )
    repository.finish_attempt(seal_attempt.id, AttemptStatus.SUCCEEDED)
    repository.cancel_run(seal_run.id)
    with pytest.raises(InvalidTransitionError, match="run is cancel_requested"):
        repository.seal_stage_aggregate(
            seal_run.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[seal_candidate.id],
        )
    repository.finish_run(seal_run.id)
    assert repository.list_generation_work_units(seal_run.id)[0].status == WorkUnitStatus.SUCCEEDED
    assert seal_unit.id


def test_cancel_preserves_sealed_units_and_cancels_unfinished_units(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH],
    )
    repository.start_run(run.id)
    _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    repository.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)

    repository.cancel_run(run.id)
    repository.finish_run(run.id)

    units = repository.list_generation_work_units(run.id)
    assert [unit.status for unit in units] == [
        WorkUnitStatus.SUCCEEDED,
        WorkUnitStatus.CANCELLED,
    ]


def test_startup_recovery_classifies_work_unit_runs_without_provider_replay(repository, brief) -> None:
    pre_dispatch_run, pre_dispatch_unit = _running_bible_unit(repository, brief)
    pre_dispatch = repository.allocate_attempt_for_work_unit(pre_dispatch_unit.id)

    ambiguous_run, ambiguous_unit = _running_bible_unit(repository, brief)
    ambiguous = repository.allocate_attempt_for_work_unit(ambiguous_unit.id)
    repository.mark_attempt_dispatched(ambiguous.id)

    sealed_run, _ = _running_bible_unit(repository, brief)
    sealed_id = _seal_bible_unit(repository, sealed_run.id, all_stage_payloads()[0])

    recovery = repository.reconcile_startup_jobs()

    assert set(recovery.resubmit_run_ids) == {pre_dispatch_run.id, sealed_run.id}
    assert recovery.terminated_run_ids == [ambiguous_run.id]
    assert repository.get_run(pre_dispatch_run.id).status == RunStatus.QUEUED
    assert repository.list_generation_work_units(pre_dispatch_run.id)[0].status == WorkUnitStatus.QUEUED
    assert repository.get_run_trace(pre_dispatch_run.id).attempts[0].status == AttemptStatus.FAILED
    assert repository.get_run(ambiguous_run.id).status == RunStatus.FAILED
    ambiguous_trace = repository.get_run_trace(ambiguous_run.id).attempts[0]
    assert ambiguous_trace.status == AttemptStatus.FAILED
    assert ambiguous_trace.outcome_unknown is True
    assert repository.list_generation_work_units(ambiguous_run.id)[0].status == WorkUnitStatus.OUTCOME_UNKNOWN
    assert repository.get_run(sealed_run.id).status == RunStatus.QUEUED
    assert sealed_id
    assert pre_dispatch.id


def test_work_unit_migration_terminates_open_legacy_attempts(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy-work-units.sqlite3'}"
    migrator = SchemaMigrator(database_url)
    configuration = migrator._config()
    command.upgrade(configuration, "0004_v2_project_creation_idempotency")
    engine = create_engine(database_url)
    now = "2026-09-02 12:00:00"
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO v2_projects (id, revision, brief, created_at, updated_at)
                    VALUES ('project-open', 0, '{}', :now, :now),
                           ('project-cancel', 0, '{}', :now, :now)
                    """
                ),
                {"now": now},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_generation_runs
                    (id, project_id, kind, parent_run_id, repair_stage, provider_snapshot,
                     requested_stages, status, canonical_snapshot, instructions,
                     result_revision_ids, error, created_at, started_at, finished_at)
                    VALUES
                    ('run-open', 'project-open', 'pipeline', NULL, NULL, '{}', '["story_bible"]',
                     'running', '{}', NULL, '[]', NULL, :now, :now, NULL),
                    ('run-cancel', 'project-cancel', 'pipeline', NULL, NULL, '{}', '["story_bible"]',
                     'cancel_requested', '{}', NULL, '[]', NULL, :now, :now, NULL)
                    """
                ),
                {"now": now},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_generation_attempts
                    (id, run_id, stage, attempt_number, status, provider, model, error, started_at, finished_at)
                    VALUES
                    ('attempt-open', 'run-open', 'story_bible', 1, 'running', NULL, NULL, NULL, :now, NULL),
                    ('attempt-cancel', 'run-cancel', 'story_bible', 1, 'running', NULL, NULL, NULL, :now, NULL)
                    """
                ),
                {"now": now},
            )

        command.upgrade(configuration, "head")

        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT runs.id, runs.status, runs.finished_at, attempts.status, attempts.error,
                           attempts.finished_at, attempts.dispatched_at, attempts.response_persisted_at,
                           attempts.outcome_unknown
                    FROM v2_generation_runs AS runs
                    JOIN v2_generation_attempts AS attempts ON attempts.run_id = runs.id
                    ORDER BY runs.id
                    """
                )
            ).all()
        assert rows[0] == (
            "run-cancel",
            "cancelled",
            rows[0][2],
            "cancelled",
            "Legacy generation attempt cancelled during work-unit migration",
            rows[0][5],
            None,
            None,
            0,
        )
        assert rows[0][2] is not None and rows[0][5] is not None
        assert rows[1][0] == "run-open"
        assert rows[1][1] == "failed"
        assert rows[1][3] == "failed"
        assert "dispatch state is unknown" in rows[1][4]
        assert rows[1][2] is not None and rows[1][5] is not None
        assert rows[1][6:] == (None, None, 0)
    finally:
        engine.dispose()
