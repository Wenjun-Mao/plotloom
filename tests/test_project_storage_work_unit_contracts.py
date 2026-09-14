"""Low-level durable work-unit contracts through a manifest-bound project store."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import Artifact, ArtifactKind, AttemptStatus, RunKind, StageName
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
