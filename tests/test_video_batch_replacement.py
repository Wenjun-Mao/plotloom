"""Explicit rejected succession preserves exact history and normal batch owners."""
# ruff: noqa: F811 -- Imported pytest fixture is injected by argument name.
from contextlib import closing
from copy import deepcopy

import pytest
from pydantic import ValidationError

from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import (
    VideoCandidateSelectionRow,
    VideoJobRow,
    VideoReviewRow,
    VideoSegmentRow,
)
from plotloom.project_storage.format import ProjectStorageCorruptionError
from plotloom.video_batch_contracts import (
    BatchControl,
    BatchRejectedReplacement,
    BatchSetup,
)
from tests.test_video_batch_review import (  # noqa: F401
    complete_batch,
    confirmation,
    native_batch_take,
)
from tests.video_batch_fixtures import ready_batch, start_batch


def reject_and_cancel(storage, service, project_id, view, job_id):
    with closing(storage.projects.open(project_id)) as store:
        job = next(job for job in service.video.jobs(store) if job["id"] == job_id)
        service.video.review(store, job_id, reviewer="Fixture creator", decision="reject",
            note="Observed camera pullback and oversized steam.", expected_selection_revision=job["selectionRevision"])
    view = service.current(project_id)
    return service.control(project_id, BatchControl(batchId=view["id"], expectedControlRevision=view["controlRevision"], action="cancel"))


def replacement_request(view, job_id):
    return BatchRejectedReplacement(batchId=view["id"], expectedRevision=view["revision"], rejectedJobIds=[job_id],
        setup=BatchSetup.model_validate(view["manifest"]["setup"]))


def rejected_environment(tmp_path, native_batch_take):
    storage, client, service, project_id, view = complete_batch(tmp_path, native_batch_take)
    job_id = view["execution"]["jobs"][view["manifest"]["targets"][0]["shotId"]]
    cancelled = reject_and_cancel(storage, service, project_id, view, job_id)
    return storage, client, service, project_id, cancelled, job_id


def finish(service, project_id):
    for _ in range(12):
        service.step(project_id)
        view = service.current(project_id)
        if view["state"] in {"awaiting_review", "blocked"}:
            break
    assert view["state"] == "awaiting_review", view["execution"].get("error")
    return view


def test_explicit_api_replacement_preserves_rejection_proposal_and_reuses_other_takes(tmp_path, native_batch_take):
    storage, client, service, project_id, original, rejected_id = rejected_environment(tmp_path, native_batch_take)
    with closing(storage.projects.open(project_id)) as store:
        retained = deepcopy(next(job for job in service.video.jobs(store) if job["id"] == rejected_id))
    response = client.post(f"/api/v2/projects/{project_id}/video-batch/replace-rejected",
        json=replacement_request(original, rejected_id).model_dump(mode="json", by_alias=True))
    assert response.status_code == 200, response.text
    successor = response.json()
    assert successor["id"] != original["id"] and successor["state"] == "setup"
    assert successor["manifest"]["newJobs"] == 1
    targets = successor["manifest"]["targets"]
    fresh = next(target for target in targets if target["mode"] == "generate")
    assert fresh["jobId"] is None and fresh["directions"] is None and fresh["compiledPrompt"] is None
    assert len([target for target in targets if target["mode"] == "reuse"]) == 5
    with pytest.raises(InvalidTransitionError):
        start_batch(service, project_id, successor)
    ready = ready_batch(service, project_id, successor)
    started = start_batch(service, project_id, ready)
    assert service.current(project_id)["execution"]["jobs"] == {key: value for key, value in original["execution"]["jobs"].items() if value != rejected_id}
    service.step(project_id)
    with closing(storage.projects.open(project_id)) as store:
        jobs = service.video.jobs(store)
        new = next(job for job in jobs if job["snapshot"]["shot"]["id"] == fresh["shotId"] and job["id"] != rejected_id)
        assert new["state"] == "prepared"
        assert new["snapshot"]["reviewedDirections"]["reviewBasis"]["batchId"] == started["id"]
        assert next(job for job in jobs if job["id"] == rejected_id) == retained
    completed = finish(service, project_id)
    review = service.review(project_id)
    receipt = service.confirm(project_id, confirmation(completed, review))
    assert len(receipt["selections"]) == 6
    assert rejected_id not in {fact["jobId"] for fact in receipt["selections"]}
    with closing(storage.projects.open(project_id)) as store:
        jobs = service.video.jobs(store)
        assert sum(job["selected"] for job in jobs) == 6
        assert next(job for job in jobs if job["id"] == rejected_id)["reviews"] == retained["reviews"]
        assert next(job for job in jobs if job["id"] == rejected_id)["segments"] == retained["segments"]


def test_repeat_explicit_replacement_carries_exact_rejected_history(tmp_path, native_batch_take):
    storage, _client, service, project_id, cancelled, first = rejected_environment(tmp_path, native_batch_take)
    successor = service.replace_rejected(project_id, replacement_request(cancelled, first))
    first_history = deepcopy(successor["manifest"]["rejectedHistory"])
    start_batch(service, project_id, ready_batch(service, project_id, successor))
    completed = finish(service, project_id)
    shot_id = first_history[0]["shotId"]
    second = completed["execution"]["jobs"][shot_id]
    cancelled = reject_and_cancel(storage, service, project_id, completed, second)
    final = service.replace_rejected(project_id, replacement_request(cancelled, second))
    assert len(final["manifest"]["rejectedHistory"]) == 2
    assert first_history[0] in final["manifest"]["rejectedHistory"]
    start_batch(service, project_id, ready_batch(service, project_id, final))
    completed = finish(service, project_id)
    assert service.review(project_id)["ready"]
    assert completed["execution"]["jobs"][shot_id] not in {first, second}


@pytest.mark.parametrize("case", ["not_cancelled", "stale_revision", "wrong_batch", "not_rejected", "unknown_id", "duplicate", "selected", "prepared", "submitted", "outcome_unknown", "stale_source"])
def test_replacement_refuses_invalid_or_unsettled_predecessor(tmp_path, native_batch_take, case):
    storage, _client, service, project_id, cancelled, identifier = rejected_environment(tmp_path, native_batch_take)
    request = replacement_request(cancelled, identifier)
    if case == "duplicate":
        with pytest.raises(ValidationError):
            BatchRejectedReplacement.model_validate(request.model_dump() | {"rejected_job_ids": [identifier, identifier]})
        return
    if case in {"stale_revision", "wrong_batch", "unknown_id", "not_rejected"}:
        request = request.model_copy(update={
            "stale_revision": {"expected_revision": 1}, "wrong_batch": {"batch_id": "0" * 36},
            "unknown_id": {"rejected_job_ids": ["unknown"]},
            "not_rejected": {"rejected_job_ids": [next(value for value in cancelled["execution"]["jobs"].values() if value != identifier)]},
        }[case])
    with closing(storage.projects.open(project_id)) as store:
        with store.repository.manual_command() as session:
            if case in {"prepared", "submitted", "outcome_unknown"}:
                session.get(VideoJobRow, identifier).state = case
            elif case == "selected":
                from plotloom.contract_identity import utc_now
                shot_id = session.get(VideoJobRow, identifier).snapshot["shot"]["id"]
                session.add(VideoCandidateSelectionRow(project_id=project_id, shot_id=shot_id,
                    selected_video_job_id=identifier, revision=1, updated_at=utc_now()))
        if case == "stale_source":
            from plotloom.stage_contracts import StageName
            board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
            changed = board.shots[0].model_copy(update={"action": board.shots[0].action + " Changed."})
            store.update_stage(StageName.STORYBOARD, board.model_copy(update={"shots": [changed, *board.shots[1:]]}),
                expected_revision=store.authoring.get_stage_head(project_id, StageName.STORYBOARD).revision)
    if case == "not_cancelled":
        service.control(project_id, BatchControl(batchId=cancelled["id"], expectedControlRevision=cancelled["controlRevision"], action="resume"))
    with pytest.raises((InvalidTransitionError, ProjectStorageCorruptionError)):
        service.replace_rejected(project_id, request)


@pytest.mark.parametrize("mutation", ["review", "proposal", "job"])
def test_frozen_history_mutation_blocks_start_and_portable_admission(tmp_path, native_batch_take, mutation):
    storage, _client, service, project_id, cancelled, identifier = rejected_environment(tmp_path, native_batch_take)
    view = ready_batch(service, project_id, service.replace_rejected(project_id, replacement_request(cancelled, identifier)))
    with closing(storage.projects.open(project_id)) as store:
        with store.repository.manual_command() as session:
            from sqlalchemy import select
            if mutation == "review":
                session.scalar(select(VideoReviewRow).where(VideoReviewRow.video_job_id == identifier)).note = "rewritten"
            elif mutation == "proposal":
                session.scalar(select(VideoSegmentRow).where(VideoSegmentRow.video_job_id == identifier)).derivative_hash = "0" * 64
            else:
                session.get(VideoJobRow, identifier).error = "changed retained job"
        from plotloom.video_batch_inventory import validate_manifest
        with pytest.raises(InvalidTransitionError, match="history changed"):
            validate_manifest(store, service.video, view["manifest"])
        import sqlite3

        from plotloom.project_storage.video_batch_validation import (
            assert_video_batch_contracts,
        )
        with sqlite3.connect(store.database_path) as connection:
            with pytest.raises(ProjectStorageCorruptionError):
                assert_video_batch_contracts(connection)
    with pytest.raises((InvalidTransitionError, ProjectStorageCorruptionError)):
        start_batch(service, project_id, view)


def test_lost_replacement_request_cannot_create_duplicate_successor(tmp_path, native_batch_take):
    _storage, _client, service, project_id, cancelled, identifier = rejected_environment(tmp_path, native_batch_take)
    request = replacement_request(cancelled, identifier)
    successor = service.replace_rejected(project_id, request)
    with pytest.raises(InvalidTransitionError, match="exact current predecessor"):
        service.replace_rejected(project_id, request)
    assert service.current(project_id)["id"] == successor["id"]


def test_ordinary_setup_cannot_implicitly_replace_rejection(tmp_path, native_batch_take):
    _storage, _client, service, project_id, cancelled, _identifier = rejected_environment(tmp_path, native_batch_take)
    view = service.setup(project_id, BatchSetup.model_validate(cancelled["manifest"]["setup"]))
    assert view["manifest"]["blockers"] and "replacement" not in view["manifest"]


def test_public_writers_refuse_frozen_take_before_commit_and_successor_stays_usable(tmp_path, native_batch_take):
    storage, client, service, project_id, cancelled, identifier = rejected_environment(tmp_path, native_batch_take)
    successor = service.replace_rejected(project_id, replacement_request(cancelled, identifier))
    with closing(storage.projects.open(project_id)) as store:
        original = next(job for job in service.video.jobs(store) if job["id"] == identifier)
    base = f"/api/v2/projects/{project_id}"
    for selected_revision in (0, 1):
        writes = [
            (f"/video-jobs/{identifier}/review", {"reviewer": "Creator", "decision": "reject", "note": "Another observation"}),
            (f"/video-jobs/{identifier}/review/reopen", {"reviewer": "Creator", "reason": "Reconsider old take"}),
            (f"/video-jobs/{identifier}/segments", {"inFrame": 0, "outFrame": 120}),
            (f"/video-segments/{original['segments'][0]['id']}/select", {}),
            (f"/video-jobs/{identifier}/cancel", {}),
            (f"/video-jobs/{identifier}/discard", {}),
            ("/video-jobs/discard-unselected", {"shotId": original["snapshot"]["shot"]["id"], "videoJobIds": [identifier]}),
        ]
        for path, body in writes:
            response = client.post(base + path, json=body | {"expectedSelectionRevision": selected_revision})
            assert response.status_code == 409, (path, response.text)
            assert "frozen batch history" in response.text, (path, response.text)
            assert client.get(base + "/video-batch").status_code == 200
            assert client.get(base + "/video-jobs").status_code == 200
        with closing(storage.projects.open(project_id)) as store:
            from plotloom.video_batch_replacement import evidence_reader, rejected_fact
            with store.repository._read() as session:
                assert rejected_fact(evidence_reader(session), project_id, identifier) == successor["manifest"]["rejectedHistory"][0]
        if selected_revision == 0:
            start_batch(service, project_id, ready_batch(service, project_id, successor))
            completed = finish(service, project_id)
            review = service.review(project_id)
            receipt = service.confirm(project_id, confirmation(completed, review))
            assert identifier not in {fact["jobId"] for fact in receipt["selections"]}


@pytest.mark.parametrize("change", ["history", "extra_job"])
def test_dispatch_rechecks_exact_history_and_only_one_successor(tmp_path, native_batch_take, change):
    storage, _client, service, project_id, cancelled, identifier = rejected_environment(tmp_path, native_batch_take)
    view = service.replace_rejected(project_id, replacement_request(cancelled, identifier))
    start_batch(service, project_id, ready_batch(service, project_id, view))
    service.step(project_id)
    current = service.current(project_id)
    target = next(target for target in current["manifest"]["targets"] if target["mode"] == "generate")
    new_id = current["execution"]["jobs"][target["shotId"]]
    with closing(storage.projects.open(project_id)) as store:
        if change == "history":
            with store.repository.manual_command() as session:
                session.get(VideoJobRow, identifier).error = "changed after fresh Start"
        else:
            new = next(job for job in service.video.jobs(store) if job["id"] == new_id)
            service.video.prepare(store, **(target["args"] | {"idempotency_key": "late-duplicate-successor"}),
                reviewed_directions=new["snapshot"]["reviewedDirections"])
        from plotloom.video_batch_basis import assert_batch_dispatch_scope
        with store.repository._read() as session, pytest.raises(InvalidTransitionError):
            assert_batch_dispatch_scope(session, project_id, new_id)
        with pytest.raises(InvalidTransitionError):
            service.video.submit(store, new_id)


@pytest.mark.parametrize("finite", [False, True])
def test_qa_replacement_requires_exact_actor_and_preserves_cumulative_claims(tmp_path, monkeypatch, native_batch_take, finite):
    from plotloom.project_storage.delegated_qa_grants import qa_command
    from plotloom.video_batch_contracts import BatchConfirmation
    from plotloom.video_ingestion import probe_video
    from tests.delegated_qa_fixtures import INSPECTION, qa_environment, qa_start
    storage, _client, service, provider, project, view, actor = qa_environment(tmp_path, monkeypatch,
        limits="finite" if finite else (None, None))
    provider._outputs = [native_batch_take]
    service.video._probe = probe_video
    qa_start(service, project, view, actor)
    for _ in range(40):
        service.step(project)
        view = service.current(project)
        if view["state"] == "awaiting_review":
            break
    assert view["state"] == "awaiting_review" and len(provider.submits) == 6
    identifier = next(iter(view["execution"]["jobs"].values()))
    with closing(storage.projects.open(project)) as store, qa_command(store, storage.application, actor):
        service.video.review(store, identifier, reviewer=actor, decision="reject", note="Synthetic fixture take rejected.", expected_selection_revision=0)
    cancelled = service.control(project, BatchControl(batchId=view["id"], expectedControlRevision=view["controlRevision"], action="cancel"))
    request = replacement_request(cancelled, identifier)
    with pytest.raises(InvalidTransitionError, match="actual attribution"):
        service.replace_rejected(project, request)
    request = request.model_copy(update={"attribution": actor})
    successor = service.replace_rejected(project, request)
    ready = ready_batch(service, project, successor)
    qa_start(service, project, ready, actor)
    for _ in range(12):
        service.step(project)
        completed = service.current(project)
        if completed["state"] in {"awaiting_review", "blocked"}:
            break
    with closing(storage.projects.open(project)) as store, store.repository._read() as session:
        from sqlalchemy import select

        from plotloom.persistence.schema import ProjectVideoDispatchRow
        claims = session.scalars(select(ProjectVideoDispatchRow)).all()
        assert len(claims) == (6 if finite else 7)
        assert any(claim.video_job_id == identifier for claim in claims)
    if finite:
        assert completed["state"] == "blocked" and len(provider.submits) == 6
        assert "cumulative QA" in completed["execution"]["error"]
    else:
        assert completed["state"] == "awaiting_review" and len(provider.submits) == 7
        review = service.review(project)
        receipt = service.confirm(project, BatchConfirmation(expectedRevision=completed["revision"],
            reviewHash=review["reviewHash"], basis="whole-pack-video-native-audio.v1", attribution=actor, inspection=INSPECTION))
        assert receipt["attribution"] == actor.model_dump(mode="json", by_alias=True)
        assert receipt["inspection"] == INSPECTION
        assert identifier not in {fact["jobId"] for fact in receipt["selections"]}
