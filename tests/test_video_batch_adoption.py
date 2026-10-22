"""Immutable English endorsement and current explicit execution ownership differ."""
from contextlib import closing
from copy import deepcopy

import pytest

from plotloom.exceptions import InvalidTransitionError
from plotloom.video_batch_contracts import BatchControl, BatchSetup
from plotloom.video_provider import RemoteOutcomeUnknown
from tests.video_batch_fixtures import batch_environment, ready_batch, start_batch


def cancelled_origin_and_successor(tmp_path, *, start=True):
    storage, client, service, provider, project_id, view = batch_environment(tmp_path)
    original = start_batch(service, project_id, ready_batch(service, project_id, view))
    service.step(project_id)
    with closing(storage.projects.open(project_id)) as store:
        job = service.video.jobs(store)[0]
    assert job["state"] == "prepared" and not provider.submits
    service.control(project_id, BatchControl(batchId=original["id"], expectedControlRevision=original["controlRevision"], action="cancel"))
    successor = service.setup(project_id, BatchSetup(profileId="minimax_h3_quality8_portrait_576x1024_v2"))
    adopted = next(target for target in successor["manifest"]["targets"] if target["jobId"] == job["id"])
    assert adopted["mode"] == "prepared"
    successor = ready_batch(service, project_id, successor)
    if start:
        successor = start_batch(service, project_id, successor)
    return storage, service, provider, project_id, original, successor, job


@pytest.mark.parametrize("path", ["controller", "manual"])
def test_cancelled_origin_prepared_job_dispatches_under_exact_started_adopter(tmp_path, path):
    storage, service, provider, project_id, original, successor, job = cancelled_origin_and_successor(tmp_path)
    snapshot = deepcopy(job["snapshot"])
    assert snapshot["reviewedDirections"]["reviewBasis"]["batchId"] == original["id"]
    if path == "controller":
        service.step(project_id)
        assert service.current(project_id)["state"] == "running"
    else:
        with closing(storage.projects.open(project_id)) as store:
            service.video.submit(store, job["id"])
    assert len(provider.submits) == 1
    with closing(storage.projects.open(project_id)) as store:
        saved = next(item for item in service.video.jobs(store) if item["id"] == job["id"])
        assert saved["state"] == "submitted" and saved["snapshot"] == snapshot
        from plotloom.persistence.schema import VideoBatchRow
        with store.repository._read() as session:
            assert session.get(VideoBatchRow, original["id"]).state == "cancelled"
        with pytest.raises(InvalidTransitionError):
            service.video.submit(store, job["id"])
    assert len(provider.submits) == 1
    assert service.current(project_id)["id"] == successor["id"]


@pytest.mark.parametrize("state", ["not_started", "paused", "cancelled", "stale", "missing_grant"])
def test_adoption_without_current_execution_authority_never_submits(tmp_path, state):
    storage, service, provider, project_id, _original, successor, job = cancelled_origin_and_successor(tmp_path, start=state != "not_started")
    if state in {"paused", "cancelled"}:
        service.control(project_id, BatchControl(batchId=successor["id"], expectedControlRevision=successor["controlRevision"], action="pause" if state == "paused" else "cancel"))
    if state == "stale":
        with closing(storage.projects.open(project_id)) as store:
            from plotloom.domain import StageName
            head = store.authoring.get_stage_head(project_id, StageName.STORYBOARD)
            board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
            shot = board.shots[0].model_copy(update={"action": board.shots[0].action + " Changed current source."})
            store.update_stage(StageName.STORYBOARD, board.model_copy(update={"shots": [shot, *board.shots[1:]]}), expected_revision=head.revision)
    if state == "missing_grant":
        with storage.application._write() as connection:
            connection.execute("DELETE FROM video_batch_grants WHERE batch_id=?", (successor["id"],))
    with closing(storage.projects.open(project_id)) as store:
        with pytest.raises(InvalidTransitionError):
            service.video.submit(store, job["id"])
    service.step(project_id)
    assert not provider.submits


def test_adopted_unknown_submission_keeps_one_attempt(tmp_path):
    storage, service, provider, project_id, _original, _successor, job = cancelled_origin_and_successor(tmp_path)
    provider.submit_error = RemoteOutcomeUnknown("fixture adopted acknowledgment lost")
    service.step(project_id)
    assert len(provider.submits) == 1
    with closing(storage.projects.open(project_id)) as store:
        saved = next(item for item in service.video.jobs(store) if item["id"] == job["id"])
        assert saved["state"] == "outcome_unknown"
        with pytest.raises(InvalidTransitionError):
            service.video.submit(store, job["id"])
    service.step(project_id)
    assert len(provider.submits) == 1
