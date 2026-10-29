"""Explicit new single-shot identities preserve rejected native evidence."""
# ruff: noqa: F811 -- Imported pytest fixture is injected by argument name.
from contextlib import closing
from copy import deepcopy

import pytest

from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import VideoJobRow
from plotloom.project_storage.current_schema import assert_current_project_database
from plotloom.video_batch_contracts import (
    BatchControl,
    BatchRejectedReplacement,
    BatchSetup,
)
from plotloom.video_ingestion import probe_video
from tests.test_video_batch_replacement import finish, reject_and_cancel
from tests.test_video_batch_review import native_batch_take  # noqa: F401
from tests.video_batch_fixtures import batch_environment, ready_batch, start_batch


def cancelled(service, project, view):
    return service.control(project, BatchControl(batchId=view["id"],
        expectedControlRevision=view["controlRevision"], action="cancel"))


def single_setup(target, key):
    args = target["args"]
    return BatchSetup(profileId=args["profile_id"], aspectPolicy=args["aspect_policy"], shotIds=[target["shotId"]],
        singleRequest={"approvalId": args["approval_id"], "shotId": target["shotId"],
            "storyboardRevision": args["storyboard_revision"], "expectedSelectionRevision": args["expected_selection_revision"],
            "idempotencyKey": key, "seed": 17, "requestedDurationSeconds": args["requested_seconds"],
            "aspectPolicy": args["aspect_policy"], "playbackIntent": args["playback_intent"]})


def single_rejected_environment(tmp_path, take):
    storage, client, service, provider, project, all_shots = batch_environment(tmp_path)
    cancelled(service, project, all_shots)
    # A never-dispatched foreign-shot key is already frozen authority, not an
    # available identity a replacement may borrow for a different shot.
    foreign = service.setup(project, single_setup(all_shots["manifest"]["targets"][1], "foreign-shot-frozen-key"))
    cancelled(service, project, foreign)
    original = service.setup(project, single_setup(all_shots["manifest"]["targets"][0], "single-original-key"))
    provider._outputs = [take]
    service.video._probe = probe_video
    start_batch(service, project, ready_batch(service, project, original))
    complete = finish(service, project)
    job_id = complete["execution"]["jobs"][complete["manifest"]["scopeShotIds"][0]]
    predecessor = reject_and_cancel(storage, service, project, complete, job_id)
    return storage, client, service, provider, project, predecessor, job_id, foreign


def explicit_request(predecessor, job_id, key="single-explicit-new-key"):
    setup = deepcopy(predecessor["manifest"]["setup"])
    setup["singleRequest"]["idempotencyKey"] = key
    return BatchRejectedReplacement(batchId=predecessor["id"], expectedRevision=predecessor["revision"],
        rejectedJobIds=[job_id], setup=setup)


def test_single_replacement_uses_explicit_new_key_and_preserves_source_settings_and_history(tmp_path, native_batch_take):
    storage, client, service, provider, project, predecessor, rejected, _foreign = single_rejected_environment(tmp_path, native_batch_take)
    with closing(storage.projects.open(project)) as store:
        retained = deepcopy(next(job for job in service.video.jobs(store) if job["id"] == rejected))
    request = explicit_request(predecessor, rejected)
    response = client.post(f"/api/v2/projects/{project}/video-batch/replace-rejected", json=request.model_dump(mode="json", by_alias=True))
    assert response.status_code == 200, response.text
    successor = response.json()
    assert successor["state"] == "setup" and successor["id"] != predecessor["id"]
    target, = successor["manifest"]["targets"]
    old_target, = predecessor["manifest"]["targets"]
    assert target["sourceHash"] == old_target["sourceHash"] and target["snapshot"] == old_target["snapshot"]
    assert target["args"]["idempotency_key"] == "single-explicit-new-key"
    assert target["args"]["seed"] == old_target["args"]["seed"] == 17
    assert target["directions"] is None and target["compiledPrompt"] is None
    assert len(provider.submits) == 1
    with pytest.raises(InvalidTransitionError): start_batch(service, project, successor)
    # Lost acknowledgments read the exact retained successor, with no writes.
    replay = client.post(f"/api/v2/projects/{project}/video-batch/replace-rejected",
        json=request.model_dump(mode="json", by_alias=True))
    assert replay.status_code == 200 and replay.json()["id"] == successor["id"]
    assert replay.json()["revision"] == successor["revision"]
    changed = request.model_dump(mode="json", by_alias=True)
    changed["setup"]["singleRequest"]["seed"] += 1
    assert client.post(f"/api/v2/projects/{project}/video-batch/replace-rejected", json=changed).status_code == 409
    ready = ready_batch(service, project, successor)
    assert ready["execution"]["fidelity"]["attempt"]["attemptId"] != predecessor["execution"]["fidelity"]["attempt"]["attemptId"]
    start_batch(service, project, ready)
    service.step(project)
    current = service.current(project)
    new_id = current["execution"]["jobs"][target["shotId"]]
    with closing(storage.projects.open(project)) as store:
        with store.repository._read() as session:
            job = session.get(VideoJobRow, new_id)
            assert job.idempotency_key == "single-explicit-new-key"
        assert_current_project_database(store.database_path, project)
        assert next(item for item in service.video.jobs(store) if item["id"] == rejected) == retained
    service.step(project)
    assert len(provider.submits) == 2
    with closing(storage.projects.open(project)) as store:
        assert_current_project_database(store.database_path, project)
        with store.repository.manual_command() as session:
            session.get(VideoJobRow, new_id).state = "outcome_unknown"
    before = service.current(project)
    replay = client.post(f"/api/v2/projects/{project}/video-batch/replace-rejected",
        json=request.model_dump(mode="json", by_alias=True))
    assert replay.status_code == 200 and replay.json()["id"] == successor["id"]
    assert replay.json()["revision"] == before["revision"] and len(provider.submits) == 2
    with closing(storage.projects.open(project)) as store, store.repository._read() as session:
        assert session.get(VideoJobRow, new_id).state == "outcome_unknown"


@pytest.mark.parametrize("change", ["old_key", "foreign_frozen_key", "foreign_shot", "missing_single", "seed", "missing_seed", "copied_check", "duration", "unknown", "stale_source"])
def test_single_replacement_refuses_reused_foreign_changed_or_unsettled_identity(tmp_path, native_batch_take, change):
    storage, client, service, provider, project, predecessor, rejected, foreign = single_rejected_environment(tmp_path, native_batch_take)
    payload = explicit_request(predecessor, rejected).model_dump(mode="json", by_alias=True)
    body = payload["setup"]["singleRequest"]
    if change == "old_key": body["idempotencyKey"] = predecessor["manifest"]["setup"]["singleRequest"]["idempotencyKey"]
    elif change == "foreign_frozen_key": body["idempotencyKey"] = "foreign-shot-frozen-key"
    elif change == "foreign_shot":
        body["shotId"] = foreign["manifest"]["scopeShotIds"][0]
        payload["setup"]["shotIds"] = [body["shotId"]]
    elif change == "missing_single": payload["setup"].pop("singleRequest")
    elif change == "seed": body["seed"] += 1
    elif change == "missing_seed": body["seed"] = None
    elif change == "copied_check": body["reviewedDirections"] = deepcopy(predecessor["manifest"]["targets"][0]["directions"])
    elif change == "duration": body["requestedDurationSeconds"] = 8
    elif change == "unknown":
        with closing(storage.projects.open(project)) as store, store.repository.manual_command() as session:
            session.get(VideoJobRow, rejected).state = "outcome_unknown"
    else:
        from plotloom.stage_contracts import StageName
        with closing(storage.projects.open(project)) as store:
            board = store.authoring.get_stage_payload(project, StageName.STORYBOARD)
            changed = board.shots[0].model_copy(update={"action": board.shots[0].action + " Changed source."})
            store.update_stage(StageName.STORYBOARD, board.model_copy(update={"shots": [changed, *board.shots[1:]]}),
                expected_revision=store.authoring.get_stage_head(project, StageName.STORYBOARD).revision)
    response = client.post(f"/api/v2/projects/{project}/video-batch/replace-rejected", json=payload)
    assert response.status_code == 409, response.text
    assert service.current(project)["id"] == predecessor["id"] and len(provider.submits) == 1
    if change == "unknown":
        with closing(storage.projects.open(project)) as store, store.repository._read() as session:
            assert session.get(VideoJobRow, rejected).state == "outcome_unknown"
