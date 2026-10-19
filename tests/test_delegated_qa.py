"""Closed defaults, explicit actors and nonportable authority for disposable QA."""
# ruff: noqa: F811 -- Imported pytest fixtures are injected by argument name.
import json
import shutil
import sqlite3
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest
from sqlalchemy import select

from plotloom.delegated_qa import REVIEWER_PREFIX, SCOPES
from plotloom.domain import new_id
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import ProjectVideoDispatchRow, VideoJobRow
from plotloom.project_storage.delegated_qa_grants import (
    qa_command,
    require_runtime_grant,
)
from plotloom.project_storage.format import ProjectStorageCorruptionError
from plotloom.project_storage.project_handle import ProjectStore
from plotloom.video_batch_contracts import BatchConfirmation, BatchStart
from plotloom.video_ingestion import probe_video
from tests.delegated_qa_fixtures import INSPECTION, qa_environment, qa_start
from tests.test_storyboard_creator_confirmation import board  # noqa: F401
from tests.test_video_batch_review import native_batch_take  # noqa: F401


def test_real_scope_has_only_the_authorized_two_ten_second_envelope():
    scope, = SCOPES
    assert scope.project_id == "326a5137-1851-4b5c-8ab2-b600ec7bda23"
    assert [item.shot_id for item in scope.materials] == ["SH01", "SH02"]
    assert (scope.max_submissions, scope.max_requested_seconds) == (2, 10)


@pytest.mark.parametrize("snapshot", [None, [], {}, {"reviewedDirections": None}, {"reviewedDirections": []},
    {"reviewedDirections": {}}, {"reviewedDirections": {"reviewBasis": None}}, {"reviewedDirections": {"reviewBasis": []}}])
def test_optional_directions_observation_does_not_invent_qa(snapshot):
    from plotloom.delegated_qa import direction_attribution
    assert direction_attribution(snapshot) is None


@pytest.mark.parametrize("snapshot", [None, [], {}, {"keyframe": None}, {"keyframe": []},
    {"keyframe": {"intent": None}}, {"keyframe": {"intent": []}}])
def test_optional_keyframe_observation_does_not_own_ordinary_shape(snapshot):
    from plotloom.delegated_qa import keyframe_attribution
    assert keyframe_attribution(snapshot) is None


@pytest.mark.parametrize("marker", [None, [], {}, {"kind": "agent_operated_qa"},
    {"kind": "unnamed_creator"}, {"kind": "agent_operated_qa", "scope_id": "noncanonical"}])
def test_present_qa_marker_is_strict_even_when_malformed(marker):
    from plotloom.delegated_qa import direction_attribution, keyframe_attribution
    with pytest.raises(ValueError):
        direction_attribution({"reviewedDirections": {"reviewBasis": {"attribution": marker}}})
    with pytest.raises(ValueError):
        keyframe_attribution({"keyframe": {"intent": {"attribution": marker}}})


def test_ordinary_project_cannot_claim_qa_or_reserved_name(board):
    storage, client, project, body = board
    response = client.post(f"/api/v2/projects/{project}/storyboard-approval", json=body | {
        "attribution": {"kind": "agent_operated_qa", "scopeId": SCOPES[0].id}})
    assert response.status_code == 409, response.text
    with closing(storage.projects.open(project)) as store:
        with pytest.raises(InvalidTransitionError, match="reserved QA"):
            store.authoring.decide_storyboard_approval(project, expected_revision=body["expectedRevision"],
                expected_content_hash=body["contentHash"], decision="approve", gate_set_version="storyboard.v2",
                reviewer=REVIEWER_PREFIX+SCOPES[0].id)
        assert not store.authoring.list_approval_decisions(project)


def test_qa_readback_and_start_require_the_actual_actor(tmp_path, monkeypatch):
    storage, client, service, provider, project, view, actor = qa_environment(tmp_path, monkeypatch)
    expected = actor.model_dump(mode="json", by_alias=True)
    review = client.get(f"/api/v2/projects/{project}/storyboard-review").json()
    assert review["activeApproval"]["attribution"] == expected
    workbench = client.get(f"/api/v2/projects/{project}/visual-workbench").json()
    assert all(item["attribution"] == expected for item in workbench["reviewedKeyframes"])
    with pytest.raises(InvalidTransitionError, match="actual attribution"):
        service.start(project, BatchStart(expectedRevision=view["revision"], manifestHash=view["manifestHash"], basis="whole-batch-english.v1"))
    started = qa_start(service, project, view, actor)
    assert started["execution"]["reviewAttribution"] == expected and not provider.submits
    service.step(project)
    with closing(storage.projects.open(project)) as store:
        job, = service.video.jobs(store)
        assert job["snapshot"]["reviewedDirections"]["reviewBasis"]["attribution"] == expected


def test_qa_copy_keeps_truth_but_has_no_runtime_grant(tmp_path, monkeypatch):
    storage, client, _service, _provider, project, _view, actor = qa_environment(tmp_path, monkeypatch)
    with closing(storage.projects.open(project)) as store:
        copied_home = tmp_path / "copied-project"
        shutil.copytree(store.home, copied_home)
        manifest = store.manifest
    with closing(ProjectStore(copied_home, manifest, create_schema=False)) as copied:
        from plotloom.project_storage.delegated_qa_grants import bind_original_qa_scope
        assert copied.media.list_current_reviewed_keyframes(project)[0]["attribution"]["kind"] == "agent_operated_qa"
        with pytest.raises(InvalidTransitionError, match="execution grant"):
            require_runtime_grant(copied, storage.application, actor)
        with pytest.raises(InvalidTransitionError), qa_command(copied, storage.application, actor):
            pytest.fail("copied QA command became authorized")
        with pytest.raises(InvalidTransitionError, match="different store incarnation"):
            bind_original_qa_scope(copied, storage.application)
    assert client.get(f"/api/v2/projects/{project}/storyboard-review").status_code == 200


def test_qa_persistence_cannot_use_a_typed_actor_without_runtime_context(tmp_path, monkeypatch):
    storage, _client, _service, _provider, project, view, _actor = qa_environment(tmp_path, monkeypatch)
    target = view["manifest"]["targets"][0]
    with closing(storage.projects.open(project)) as store, pytest.raises(InvalidTransitionError, match="runtime incarnation"):
        store.media.create_visual_intent(project, target["snapshot"]["keyframe"]["assetId"],
            target["snapshot"]["keyframe"]["intent"], target_shot_id=target["shotId"])


def test_manual_per_shot_prepare_cannot_save_misattributed_qa_material(tmp_path, monkeypatch):
    _storage, client, _service, provider, project, view, _actor = qa_environment(tmp_path, monkeypatch)
    target = view["manifest"]["targets"][0]
    args = target["args"]
    body = {"approvalId": args["approval_id"], "shotId": args["shot_id"], "storyboardRevision": args["storyboard_revision"],
        "expectedSelectionRevision": args["expected_selection_revision"], "idempotencyKey": "human-path-on-qa",
        "requestedDurationSeconds": args["requested_seconds"], "seed": args["seed"], "profileId": args["profile_id"],
        "aspectPolicy": "cover_center_crop", "allowCenterCrop": True, "playbackIntent": args["playback_intent"]}
    base = f"/api/v2/projects/{project}/video-jobs"
    directions = target["directions"] | {"reviewedEnglish": True}
    preview = client.post(base+"/prompt-preview", json=body | {"reviewedDirections": directions})
    assert preview.status_code == 200, preview.text
    directions["promptSha256"] = preview.json()["compiledPromptSha256"]
    response = client.post(base, json=body | {"reviewedDirections": directions})
    assert response.status_code == 409 and "QA batch English endorsement" in response.text
    assert client.get(base).json()["jobs"] == []
    assert not provider.submits


@pytest.mark.parametrize("change", ["profile", "budget", "asset"])
def test_qa_start_cannot_expand_granted_scope(tmp_path, monkeypatch, change):
    storage, _client, service, provider, project, view, actor = qa_environment(tmp_path, monkeypatch)
    with closing(storage.projects.open(project)) as store:
        def mutate(row):
            manifest = deepcopy(row.manifest)
            if change == "profile": manifest["setup"]["profileId"] = "another-profile"
            if change == "budget": manifest["setup"]["maxRequestedSeconds"] += 5
            if change == "asset": manifest["targets"][0]["snapshot"]["keyframe"]["assetId"] = new_id()
            row.manifest = manifest
        view = store.repository.video_batches.change(project, view["id"], mutate=mutate)
    with pytest.raises(ProjectStorageCorruptionError if change == "asset" else InvalidTransitionError):
        qa_start(service, project, view, actor)
    assert not provider.submits


def test_qa_unknown_claim_blocks_another_submission_before_reservation(tmp_path, monkeypatch):
    storage, _client, service, provider, project, view, actor = qa_environment(tmp_path, monkeypatch)
    qa_start(service, project, view, actor)
    service.step(project)
    service.step(project)
    with closing(storage.projects.open(project)) as store:
        job, = service.video.jobs(store)
        with store.repository._write() as session:
            original = session.get(VideoJobRow, job["id"])
            original.state = "outcome_unknown"
            # A second prepared request cannot cross the application reservation
            # boundary while the existing claim is UNKNOWN, even outside a batch.
            fields = {column.name: deepcopy(getattr(original, column.name)) for column in VideoJobRow.__table__.columns}
            fields |= {"id": new_id(), "idempotency_key": "qa-unsettled-negative", "state": "prepared",
                "provider_prediction_id": None, "dispatched_at": None}
            candidate = VideoJobRow(**fields)
            session.add(candidate)
            candidate_id = candidate.id
        reservations = []
        monkeypatch.setattr(storage.application, "reserve_video_dispatch", lambda **kwargs: reservations.append(kwargs))
        from plotloom.project_storage.project_video import ProjectVideoRepository
        with pytest.raises(InvalidTransitionError, match="unsettled QA"):
            ProjectVideoRepository(store, storage.application).claim_video_dispatch(project, candidate_id)
        assert not reservations
    assert len(provider.submits) == 1


def complete_qa(tmp_path, monkeypatch, take):
    values = qa_environment(tmp_path, monkeypatch)
    storage, client, service, provider, project, view, actor = values
    provider._outputs = [take]
    service.video._probe = probe_video
    qa_start(service, project, view, actor)
    for _ in range(40):
        service.step(project)
        view = service.current(project)
        if view["state"] in {"awaiting_review", "blocked"}: break
    assert view["state"] == "awaiting_review", view["execution"].get("error")
    return storage, client, service, provider, project, view, actor


def test_qa_native_av_receipt_selection_readback_and_copy(tmp_path, monkeypatch, native_batch_take):
    storage, client, service, provider, project, view, actor = complete_qa(tmp_path, monkeypatch, native_batch_take)
    review = service.review(project)
    body = {"expectedRevision": view["revision"], "reviewHash": review["reviewHash"], "basis": "whole-pack-video-native-audio.v1"}
    for extra in ({}, {"attribution": actor}):
        with pytest.raises((InvalidTransitionError, ValueError)):
            service.confirm(project, BatchConfirmation(**body, **extra))
    receipt = service.confirm(project, BatchConfirmation(**body, attribution=actor, inspection=INSPECTION))
    assert receipt["attribution"] == actor.model_dump(mode="json", by_alias=True)
    assert receipt["inspection"] == INSPECTION
    assert service.confirm(project, BatchConfirmation(**body, attribution=actor, inspection=INSPECTION)) == receipt
    with closing(storage.projects.open(project)) as store:
        jobs = service.video.jobs(store)
        assert all(job["selected"] and job["playbackSegment"]["attribution"] == receipt["attribution"] for job in jobs)
        assert all(job["reviews"][-1]["attribution"] == receipt["attribution"] for job in jobs)
        for job in jobs:
            assert client.get(f"/api/v2/projects/{project}/video-jobs/{job['id']}/playback").status_code == 200
        home, manifest = store.home, store.manifest
    copy = tmp_path / "confirmed-copy"
    shutil.copytree(home, copy)
    with closing(ProjectStore(copy, manifest, create_schema=False)) as store:
        from plotloom.project_storage.current_schema import (
            assert_current_project_database,
        )
        assert_current_project_database(store.database_path, project)
        assert all(job["playbackSegment"]["attribution"] == receipt["attribution"] for job in service.video.jobs(store))
    exported = storage.recovery.create_snapshot(project)
    assert exported.status == "complete"
    assert_current_project_database(Path(exported.location) / "project.sqlite3", project)
    assert len(provider.submits) == 6  # Six-shot synthetic scope; production grant remains two.


def test_qa_cumulative_caps_include_prior_claims_outside_this_batch(tmp_path, monkeypatch, native_batch_take):
    storage, _client, _service, _provider, project, _view, _actor = complete_qa(tmp_path, monkeypatch, native_batch_take)
    from plotloom.delegated_qa_video import assert_dispatch
    with closing(storage.projects.open(project)) as store, store.repository._read() as session:
        jobs = session.scalars(select(VideoJobRow)).all()
        assert len(session.scalars(select(ProjectVideoDispatchRow)).all()) == 6
        candidate = deepcopy(jobs[0])
        candidate.id = new_id()
        with pytest.raises(InvalidTransitionError, match="cumulative QA"):
            assert_dispatch(session, project, candidate)


def test_qa_actual_rejection_is_attributed_and_blocks_final_selection(tmp_path, monkeypatch, native_batch_take):
    storage, client, service, _provider, project, view, actor = complete_qa(tmp_path, monkeypatch, native_batch_take)
    review = service.review(project)
    job = review["proposals"][-1]["jobId"]
    base = f"/api/v2/projects/{project}/video-jobs/{job}/review"
    response = client.post(base, json={"attribution": actor.model_dump(mode="json", by_alias=True),
        "decision": "reject", "note": "Synthetic tone rejected for this QA test.", "expectedSelectionRevision": 0})
    assert response.status_code == 201, response.text
    before = next(item for item in client.get(f"/api/v2/projects/{project}/video-jobs").json()["jobs"] if item["id"] == job)
    reopened = client.post(base+"/reopen", json={"reviewer": "Human label", "reason": "Attempt to reopen QA", "expectedSelectionRevision": 0})
    assert reopened.status_code == 409, reopened.text
    assert client.get(f"/api/v2/projects/{project}/video-jobs").status_code == 200
    after = next(item for item in client.get(f"/api/v2/projects/{project}/video-jobs").json()["jobs"] if item["id"] == job)
    assert (after["reviews"], after["selectionRevision"]) == (before["reviews"], before["selectionRevision"])
    assert not service.review(project)["ready"]
    with pytest.raises(InvalidTransitionError):
        service.confirm(project, BatchConfirmation(expectedRevision=view["revision"], reviewHash=review["reviewHash"],
            basis="whole-pack-video-native-audio.v1", attribution=actor, inspection=INSPECTION))
    with closing(storage.projects.open(project)) as store:
        assert not any(job["selected"] for job in service.video.jobs(store))
        home, manifest = store.home, store.manifest
    copied_home = tmp_path / "rejected-qa-copy"
    shutil.copytree(home, copied_home)
    with closing(ProjectStore(copied_home, manifest, create_schema=False)) as copied:
        from plotloom.project_storage.project_video import ProjectVideoRepository
        repository = ProjectVideoRepository(copied, storage.application)
        with pytest.raises(InvalidTransitionError, match="human review path"):
            repository.reopen_video_job_review(project, job, reviewer="Human label", reason="Copied rejection",
                expected_selection_revision=before["selectionRevision"])
        saved = next(item for item in repository.list_video_jobs(project) if item["id"] == job)
        assert (saved["reviews"], saved["selectionRevision"]) == (before["reviews"], before["selectionRevision"])


def test_qa_api_consumes_exact_material_draft_and_rejects_stale_draft(tmp_path, monkeypatch):
    storage, client, _service, _provider, project, view, actor = qa_environment(tmp_path, monkeypatch)
    target = view["manifest"]["targets"][0]
    snapshot = target["snapshot"]
    frame = snapshot["keyframe"]
    payload = frame["intent"] | {"assetId": frame["assetId"], "shotId": target["shotId"]}
    entity = f"{target['shotId']}:{frame['assetId']}"
    base = f"/api/v2/projects/{project}"
    response = client.put(base+"/authoring-drafts", json={"editorScope": "visual_intent", "entityId": entity,
        "baseCanonicalRevision": snapshot["storyboardRevision"], "expectedDraftRevision": 0, "payload": payload})
    assert response.status_code == 200, response.text
    body = {key: value for key, value in payload.items() if key != "assetId"} | {
        "consumedDraft": {"editorScope": "visual_intent", "entityId": entity, "draftRevision": 99}}
    endpoint = base+f"/managed-assets/{frame['assetId']}/visual-intents"
    assert client.post(endpoint, json=body).status_code == 409
    body["consumedDraft"]["draftRevision"] = response.json()["draftRevision"]
    saved = client.post(endpoint, json=body)
    assert saved.status_code == 201, saved.text
    with closing(storage.projects.open(project)) as store:
        revision = store.media.visual_selection_revision(project)
    selected = client.post(base+"/reviewed-keyframes", json={"assetId": frame["assetId"],
        "shotId": target["shotId"], "sceneId": snapshot["shot"]["sceneId"], "expectedSelectionRevision": revision,
        "storyboardRevision": snapshot["storyboardRevision"], "approvalId": snapshot["approvalId"],
        "compatibilityNote": "Synthetic QA API inspection observation.", "visualIntentId": saved.json()["id"],
        "visualIntentRevision": saved.json()["revision"], "attribution": actor.model_dump(mode="json", by_alias=True)})
    assert selected.status_code == 201, selected.text
    assert selected.json()["attribution"]["kind"] == "agent_operated_qa"


@pytest.mark.parametrize("corruption", ["null", "list", "frame", "intent", "provider", "strip_actors", "wrong_scope"])
def test_retained_qa_links_cannot_hide_missing_or_forged_snapshot_attribution(tmp_path, monkeypatch, corruption):
    storage, _client, service, _provider, project, view, actor = qa_environment(tmp_path, monkeypatch)
    qa_start(service, project, view, actor)
    service.step(project)  # Prepare and link only; no provider call.
    with closing(storage.projects.open(project)) as store:
        job, = service.video.jobs(store)
        path = store.database_path
    snapshot = deepcopy(job["snapshot"])
    if corruption == "null": snapshot = None
    elif corruption == "list": snapshot = []
    elif corruption == "frame": snapshot["keyframe"] = None
    elif corruption == "intent": snapshot["keyframe"]["intent"] = []
    elif corruption == "provider": snapshot["provider"] = None
    elif corruption == "strip_actors":
        snapshot["keyframe"]["intent"].pop("attribution")
        snapshot["reviewedDirections"]["reviewBasis"].pop("attribution")
    else:
        snapshot["keyframe"]["intent"]["attribution"]["scopeId"] = "forged-scope"
    from plotloom.persistence.codec import stable_hash
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE v2_video_jobs SET snapshot=?,snapshot_hash=? WHERE id=?",
            (json.dumps(snapshot), stable_hash(snapshot), job["id"]))
    with pytest.raises(ProjectStorageCorruptionError):
        storage.projects.open(project)
