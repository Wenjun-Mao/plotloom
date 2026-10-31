"""Normal Codex authorization stays truthful without inheriting QA authority."""
# ruff: noqa: F811 -- pytest supplies the imported FFmpeg fixture by argument.
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.codec import stable_hash
from plotloom.project_storage import ProjectFolderStorage, ProjectStorageCorruptionError
from plotloom.video_batch_contracts import BatchControl, BatchStart
from plotloom.video_fidelity_contracts import IntentAuthorization
from tests.delegated_qa_fixtures import qa_environment, qa_start
from tests.video_batch_fixtures import batch_environment, ready_batch, start_batch
from tests.test_video_batch_review import native_batch_take  # noqa: F401

OPERATOR = {"kind": "codex_task", "taskId": "00000000-0000-4000-8000-000000000001"}
OTHER = {"kind": "codex_task", "taskId": "00000000-0000-4000-8000-000000000002"}


def command(view, **extra):
    return {"expectedRevision": view["revision"], "manifestHash": view["manifestHash"],
        "basis": "production-intent.v2", **extra}


def test_api_operator_start_readback_exact_replay_prepare_and_fake_dispatch(tmp_path):
    storage, client, service, provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    body = command(ready, operator=OPERATOR)
    url = f"/api/v2/projects/{project}/video-batch"
    response = client.post(url + "/start", json=body)
    assert response.status_code == 200, response.text
    started = response.json()
    assert started["execution"]["intentReviewActor"] == OPERATOR
    assert "reviewAttribution" not in started["execution"]
    read = client.get(url).json()
    assert all(value["intentAuthorization"]["operator"] == OPERATOR
        and "attribution" not in value["reviewBasis"] for value in read["authorizedDirections"].values())
    replay = client.post(url + "/start", json=body)
    assert replay.status_code == 200, replay.text
    assert {key: replay.json()[key] for key in ("id", "revision", "execution")} == {key: started[key] for key in ("id", "revision", "execution")}
    assert not provider.submits
    for changed in [command(ready), command(ready, operator=OTHER)]:
        refused = client.post(url + "/start", json=changed)
        assert refused.status_code == 409, refused.text
    service.step(project)  # Exact original preparation only.
    with closing(storage.projects.open(project)) as store:
        job, = service.video.jobs(store)
        assert job["snapshot"]["reviewedDirections"]["intentAuthorization"]["operator"] == OPERATOR
        assert "attribution" not in job["snapshot"]["reviewedDirections"]["reviewBasis"]
    service.step(project)  # Explicit fake provider, never a live gateway.
    assert len(provider.submits) == 1
    assert client.post(url + "/start", json=body).status_code == 200
    assert len(provider.submits) == 1


def test_operator_cannot_replace_qa_grant_or_material_attribution(tmp_path, monkeypatch):
    _storage, client, service, provider, project, ready, qa = qa_environment(tmp_path, monkeypatch)
    url = f"/api/v2/projects/{project}/video-batch/start"
    response = client.post(url, json=command(ready, operator=OPERATOR))
    assert response.status_code == 409, response.text
    response = client.post(url, json=command(ready, operator=OPERATOR,
        attribution=qa.model_dump(mode="json", by_alias=True)))
    assert response.status_code == 422, response.text
    assert not provider.submits
    started = qa_start(service, project, ready, qa)
    assert started["execution"]["intentReviewActor"] == qa.model_dump(mode="json", by_alias=True)
    assert "operator" not in next(iter(service.current(project)["authorizedDirections"].values()))["intentAuthorization"]


def test_unchanged_creator_serialization_has_no_operator_or_fabricated_qa(tmp_path):
    _storage, _client, service, provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    assert "operator" not in BatchStart(**command(ready)).model_dump(mode="json", by_alias=True)
    assert IntentAuthorization(briefHash="a" * 64).model_dump(mode="json", by_alias=True) == {
        "version": "production-intent.v2", "briefHash": "a" * 64}
    started = start_batch(service, project, ready)
    assert started["execution"]["intentReviewActor"] == {"kind": "unnamed_creator"}
    assert not provider.submits


@pytest.mark.parametrize("change", ["missing", "different", "null", "extra"])
def test_preparation_refuses_changed_operator_without_dispatch(tmp_path, change):
    storage, _client, service, provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    service.start(project, BatchStart(**command(ready, operator=OPERATOR)))
    target = service.current(project)["manifest"]["targets"][0]
    from plotloom.video_batch_basis import authorized_directions
    directions = deepcopy(authorized_directions(service.current(project), target))
    authorization = directions["intentAuthorization"]
    if change == "missing": authorization.pop("operator")
    elif change == "different": authorization["operator"] = OTHER
    elif change == "null": authorization["operator"] = None
    else: authorization["operator"]["scopeId"] = "not-a-qa-grant"
    with closing(storage.projects.open(project)) as store:
        with pytest.raises((ValueError, InvalidTransitionError)):
            service.video.prepare(store, **target["args"], reviewed_directions=directions)
        assert service.video.jobs(store) == []
    assert not provider.submits


@pytest.mark.parametrize("change", ["missing_snapshot", "changed_snapshot", "changed_actor", "malformed_actor"])
def test_portable_reopening_rejects_operator_tampering(tmp_path, change):
    storage, _client, service, provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    service.start(project, BatchStart(**command(ready, operator=OPERATOR)))
    service.step(project)
    with closing(storage.projects.open(project)) as store:
        job, = service.video.jobs(store)
        database = store.database_path
    with sqlite3.connect(database) as connection:
        if change.endswith("snapshot"):
            snapshot = deepcopy(job["snapshot"])
            if change == "missing_snapshot": snapshot["reviewedDirections"]["intentAuthorization"].pop("operator")
            else: snapshot["reviewedDirections"]["intentAuthorization"]["operator"] = OTHER
            connection.execute("UPDATE v2_video_jobs SET snapshot=?,snapshot_hash=? WHERE id=?",
                (json.dumps(snapshot), stable_hash(snapshot), job["id"]))
        else:
            raw, = connection.execute("SELECT execution FROM v2_video_batches WHERE id=?", (ready["id"],)).fetchone()
            execution = json.loads(raw)
            execution["intentReviewActor"] = OTHER if change == "changed_actor" else OPERATOR | {"scopeId": "forged"}
            connection.execute("UPDATE v2_video_batches SET execution=? WHERE id=?", (json.dumps(execution), ready["id"]))
    with pytest.raises(ProjectStorageCorruptionError):
        storage.projects.open(project)
    assert not provider.submits


def test_operator_survives_snapshot_restore_without_portable_dispatch_permission(tmp_path):
    storage, _client, service, provider, project, view = batch_environment(tmp_path)
    ready = ready_batch(service, project, view)
    service.start(project, BatchStart(**command(ready, operator=OPERATOR)))
    service.step(project)
    current = service.current(project)
    service.control(project, BatchControl(batchId=current["id"],
        expectedControlRevision=current["controlRevision"], action="cancel"))
    snapshot = storage.recovery.create_snapshot(project)
    restored = ProjectFolderStorage(outputs_root=tmp_path / "restored-output", application_data_root=tmp_path / "restored-app")
    restored.recovery.restore(Path(snapshot.location))
    with closing(restored.projects.open(project)) as store:
        batch = store.repository.video_batches.current(project)
        assert batch["execution"]["intentReviewActor"] == OPERATOR
        from plotloom.project_storage.project_video import ProjectVideoRepository
        job, = ProjectVideoRepository(store, restored.application).list_video_jobs(project)
        assert job["snapshot"]["reviewedDirections"]["intentAuthorization"]["operator"] == OPERATOR
        from plotloom.project_storage.video_batch_grants import VideoBatchGrants
        with pytest.raises(InvalidTransitionError, match="execution grant"):
            VideoBatchGrants(restored.application).require(store, batch["id"], batch["manifestHash"])
    assert not provider.submits


def test_codex_generation_to_selected_native_window_and_restored_playback(tmp_path, native_batch_take):
    from plotloom.video_batch_contracts import BatchConfirmation
    from plotloom.video_ingestion import probe_video
    from plotloom.project_storage.project_video import ProjectVideoRepository
    storage, client, service, provider, project, view = batch_environment(tmp_path)
    provider._outputs = [native_batch_take]
    service.video._probe = probe_video
    ready = ready_batch(service, project, view)
    service.start(project, BatchStart(**command(ready, operator=OPERATOR)))
    for _ in range(40):
        service.step(project)
        current = service.current(project)
        if current["state"] in {"awaiting_review", "blocked"}:
            break
    assert current["state"] == "awaiting_review", current["execution"].get("error")
    review = service.review(project)
    receipt = service.confirm(project, BatchConfirmation(expectedRevision=current["revision"],
        reviewHash=review["reviewHash"], basis="source-bound-selections.v1", attribution=OPERATOR))
    assert receipt["attribution"] == OPERATOR and "inspection" not in receipt and "confirmation" not in receipt
    with closing(storage.projects.open(project)) as store:
        jobs = service.video.jobs(store)
        assert len(jobs) == len(provider.submits) == 6
        assert all(job["selected"] and job["playbackSegment"]["current"]
            and job["snapshot"]["reviewedDirections"]["intentAuthorization"]["operator"] == OPERATOR for job in jobs)
        playback = client.get(f"/api/v2/projects/{project}/video-jobs/{jobs[0]['id']}/playback")
        assert playback.status_code == 200 and playback.content
    snapshot = storage.recovery.create_snapshot(project)
    restored = ProjectFolderStorage(outputs_root=tmp_path / "selected-output", application_data_root=tmp_path / "selected-app")
    restored.recovery.restore(Path(snapshot.location))
    with closing(restored.projects.open(project)) as store:
        restored_jobs = ProjectVideoRepository(store, restored.application).list_video_jobs(project)
        assert [job["playbackSegment"]["derivativeHash"] for job in restored_jobs] == [job["playbackSegment"]["derivativeHash"] for job in jobs]
        assert all(job["selected"] and job["playbackSegment"]["current"] for job in restored_jobs)

