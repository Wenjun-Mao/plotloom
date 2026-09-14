"""Low-level durable work-unit contracts through a manifest-bound project store."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import Artifact, ArtifactKind, AttemptStatus, GenerationAttemptKind, RunKind, RunStatus, StageName, WorkUnitStatus
from plotloom.exceptions import InvalidTransitionError
from plotloom.generation.fragments import StoryBibleFragment
from plotloom.persistence import stable_hash
from plotloom.project_storage import ProjectFolderStorage, ProjectStore
from tests.backend_core.conftest import all_stage_payloads
from tests.project_storage_fixtures import fixture_profile


def _storage(tmp_path) -> ProjectFolderStorage:
    return ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )


def _running_bible_unit(store: ProjectStore):
    snapshot = fixture_profile().model_dump(mode="json", by_alias=True)
    with store.generation.admit_provider_snapshot(snapshot):
        run = store.generation.create_run(
            store.project().id,
            RunKind.PIPELINE,
            [StageName.STORY_BIBLE],
            provider_snapshot=snapshot,
        )
    store.generation.start_run(run.id)
    plan = store.generation.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    return run, plan, store.generation.list_generation_work_units(run.id)[0]


def _accepted_bible_evidence(store: ProjectStore, run, plan, unit):
    repository = store.generation
    attempt = repository.allocate_attempt_for_work_unit(unit.id, provider="fixture", model="fixture")
    repository.mark_attempt_dispatched(attempt.id)
    prompt = {"messages": [{"role": "user", "content": "fixture bible"}]}
    repository.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.PROMPT,
            content=prompt,
            content_hash=stable_hash(prompt),
        )
    )
    repository.persist_attempt_response(attempt.id, {"rawResponse": {"choices": []}})
    validation = {"accepted": True, "issues": []}
    repository.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.VALIDATION,
            content=validation,
            content_hash=stable_hash(validation),
        )
    )
    fragment = StoryBibleFragment(
        stage_plan_hash=plan.stage_plan_hash,
        work_unit_id=unit.id,
        payload=all_stage_payloads()[0],
    ).model_dump(mode="json", by_alias=False)
    candidate = repository.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.CANDIDATE,
            content=fragment,
            content_hash=stable_hash(fragment),
        )
    )
    return attempt, candidate


def test_project_work_unit_claim_is_atomic_across_independent_project_handles(tmp_path) -> None:
    storage = _storage(tmp_path)
    first = storage.projects.create(FIXED_CHINESE_BRIEF)
    run, _plan, unit = _running_bible_unit(first)
    second = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    ).projects.open(first.project().id)
    barrier = Barrier(2)

    def claim(store: ProjectStore):
        barrier.wait()
        try:
            return "claimed", store.generation.allocate_attempt_for_work_unit(unit.id)
        except InvalidTransitionError as error:
            return "rejected", error

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(claim, (first, second)))
    finally:
        second.close()

    claimed = [outcome for outcome in outcomes if outcome[0] == "claimed"]
    rejected = [outcome for outcome in outcomes if outcome[0] == "rejected"]
    assert len(claimed) == len(rejected) == 1
    assert "work unit is running" in str(rejected[0][1])
    attempts = first.run_trace(run.id).attempts
    assert [(attempt.work_unit_id, attempt.attempt_number) for attempt in attempts] == [(unit.id, 1)]


def test_project_work_unit_seal_requires_accepted_producer_and_freezes_evidence(tmp_path) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    run, plan, unit = _running_bible_unit(store)
    attempt, candidate = _accepted_bible_evidence(store, run, plan, unit)

    with pytest.raises(InvalidTransitionError, match="succeeded"):
        store.generation.seal_stage_aggregate(
            run.id, StageName.STORY_BIBLE, candidate_artifact_ids=[candidate.id]
        )
    store.generation.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    sealed = store.generation.seal_stage_aggregate(
        run.id, StageName.STORY_BIBLE, candidate_artifact_ids=[candidate.id]
    )
    assert sealed.manifest["units"][0]["candidateArtifactId"] == candidate.id

    late_media = {"uri": "project://late-media"}
    with pytest.raises(InvalidTransitionError, match="aggregate is sealed"):
        store.generation.add_artifact(
            Artifact(
                run_id=run.id,
                attempt_id=attempt.id,
                work_unit_id=unit.id,
                stage=StageName.STORY_BIBLE,
                kind=ArtifactKind.MEDIA,
                content=late_media,
                content_hash=stable_hash(late_media),
            )
        )


def test_project_work_unit_requires_dispatch_then_marks_ambiguous_outcome_unknown(tmp_path) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    run, _plan, unit = _running_bible_unit(store)
    attempt = store.generation.allocate_attempt_for_work_unit(unit.id)

    with pytest.raises(InvalidTransitionError, match="dispatch marker"):
        store.generation.persist_attempt_response(attempt.id, {"rawResponse": "not yet"})
    unknown = store.generation.mark_attempt_dispatched(attempt.id)
    unknown = store.generation.mark_attempt_outcome_unknown(
        unknown.id, error="provider outcome is unknown"
    )

    assert unknown.outcome_unknown is True
    assert unknown.outcome_code == "provider.outcome_unknown"
    assert store.generation.list_generation_work_units(run.id)[0].status == WorkUnitStatus.OUTCOME_UNKNOWN


def test_project_work_unit_claim_recovery_keeps_the_original_predispatch_attempt(tmp_path) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    run, _plan, unit = _running_bible_unit(store)
    first = store.generation.allocate_attempt_for_work_unit(unit.id)

    with pytest.raises(InvalidTransitionError, match="work unit is running"):
        store.generation.allocate_attempt_for_work_unit(unit.id)
    recovery = store.generation.reconcile_startup_jobs()
    assert recovery.resubmit_run_ids == [run.id]
    assert store.generation.get_run(run.id).status == RunStatus.QUEUED
    assert store.generation.list_generation_work_units(run.id)[0].status == WorkUnitStatus.RUNNING
    assert store.generation.start_run(run.id).status == RunStatus.RUNNING
    resumed = store.generation.get_recoverable_attempt_for_work_unit(unit.id)
    assert resumed is not None
    assert (resumed.id, resumed.attempt_number, resumed.dispatched_at) == (first.id, 1, None)
    with pytest.raises(InvalidTransitionError, match="work unit is running"):
        store.generation.allocate_attempt_for_work_unit(unit.id)


def test_project_work_unit_cancellation_blocks_dispatch_and_sealing_without_rewriting_evidence(tmp_path) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    dispatch_run, _plan, dispatch_unit = _running_bible_unit(store)
    dispatch_attempt = store.generation.allocate_attempt_for_work_unit(dispatch_unit.id)
    assert store.generation.cancel_run(dispatch_run.id).status == RunStatus.CANCEL_REQUESTED
    with pytest.raises(InvalidTransitionError, match="cancel_requested"):
        store.generation.mark_attempt_dispatched(dispatch_attempt.id)
    assert store.generation.finish_run(dispatch_run.id).status == RunStatus.CANCELLED
    assert store.generation.list_generation_work_units(dispatch_run.id)[0].status == WorkUnitStatus.CANCELLED

    seal_run, plan, seal_unit = _running_bible_unit(store)
    attempt, candidate = _accepted_bible_evidence(store, seal_run, plan, seal_unit)
    store.generation.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    store.generation.cancel_run(seal_run.id)
    with pytest.raises(InvalidTransitionError, match="cancel_requested"):
        store.generation.seal_stage_aggregate(
            seal_run.id, StageName.STORY_BIBLE, candidate_artifact_ids=[candidate.id]
        )
    assert store.generation.finish_run(seal_run.id).status == RunStatus.CANCELLED
    assert store.generation.list_generation_work_units(seal_run.id)[0].status == WorkUnitStatus.SUCCEEDED


def test_project_work_unit_cancellation_preserves_a_sealed_stage_and_cancels_the_next_stage(tmp_path) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    snapshot = fixture_profile().model_dump(mode="json", by_alias=True)
    with store.generation.admit_provider_snapshot(snapshot):
        run = store.generation.create_run(
            store.project().id,
            RunKind.PIPELINE,
            [StageName.STORY_BIBLE, StageName.STORY_GRAPH],
            provider_snapshot=snapshot,
        )
    store.generation.start_run(run.id)
    bible_plan = store.generation.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    bible_unit = store.generation.list_generation_work_units(run.id)[0]
    attempt, candidate = _accepted_bible_evidence(store, run, bible_plan, bible_unit)
    store.generation.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    store.generation.seal_stage_aggregate(
        run.id, StageName.STORY_BIBLE, candidate_artifact_ids=[candidate.id]
    )
    store.generation.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)

    store.generation.cancel_run(run.id)
    assert store.generation.finish_run(run.id).status == RunStatus.CANCELLED
    assert [unit.status for unit in store.generation.list_generation_work_units(run.id)] == [
        WorkUnitStatus.SUCCEEDED,
        WorkUnitStatus.CANCELLED,
    ]


def test_project_work_unit_unknown_attempt_is_never_a_correction_source_or_replay_target(tmp_path) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    run, _plan, unit = _running_bible_unit(store)
    attempt = store.generation.allocate_attempt_for_work_unit(unit.id, max_attempts=3)
    store.generation.mark_attempt_dispatched(attempt.id)
    unknown = store.generation.mark_attempt_outcome_unknown(
        attempt.id, error="socket lost after provider submission"
    )

    assert unknown.outcome_code == "provider.outcome_unknown"
    assert unknown.outcome_unknown is True
    assert store.generation.list_generation_work_units(run.id)[0].status == WorkUnitStatus.OUTCOME_UNKNOWN
    with pytest.raises(InvalidTransitionError, match="work unit is outcome_unknown"):
        store.generation.allocate_attempt_for_work_unit(
            unit.id,
            max_attempts=3,
            attempt_kind=GenerationAttemptKind.CORRECTION,
            source_attempt_id=attempt.id,
        )
