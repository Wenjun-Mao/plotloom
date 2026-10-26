"""No-resend, missing-only race and portable-grant regressions."""
from contextlib import closing
from copy import deepcopy
import shutil
import pytest
from plotloom.stage_contracts import StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage.project_handle import ProjectStore
from plotloom.video_batch_contracts import BatchControl
from plotloom.video_batch_runtime import VideoBatchRuntime
from tests.video_batch_fixtures import batch_environment, ready_batch, start_batch
from tests.video_prompt_fixtures import reviewed_h3_body
from plotloom.video_provider import RemoteOutcomeUnknown


def test_unknown_submission_is_retained_across_restart_and_resume(tmp_path):
    storage, _client, service, provider, project_id, view = batch_environment(tmp_path)
    ready = ready_batch(service, project_id, view)
    start_batch(service, project_id, ready)
    provider.submit_error = RemoteOutcomeUnknown("fixture acknowledgment lost")
    service.step(project_id); service.step(project_id)
    assert len(provider.submits) == 1
    service.step(project_id)
    current = service.current(project_id)
    assert current["state"] == "blocked"
    service.control(project_id, BatchControl(batchId=current["id"], expectedControlRevision=current["controlRevision"], action="resume"))
    from plotloom.video_batch_service import VideoBatchService
    restarted = VideoBatchService(storage, service.registry, service.video)
    for _ in range(3): restarted.step(project_id)
    assert len(provider.submits) == 1
    assert restarted.current(project_id)["state"] == "blocked"


def test_late_manual_job_blocks_frozen_missing_only_start(tmp_path):
    storage, client, service, provider, project_id, view = batch_environment(tmp_path)
    ready = ready_batch(service, project_id, view)
    target = ready["manifest"]["targets"][0]
    args = target["args"]
    body = {"approvalId": args["approval_id"], "shotId": args["shot_id"], "storyboardRevision": args["storyboard_revision"],
        "expectedSelectionRevision": args["expected_selection_revision"], "idempotencyKey": "late-manual-work", "seed": 9,
        "requestedDurationSeconds": args["requested_seconds"], "aspectPolicy": "reject_mismatch"}
    response = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=reviewed_h3_body(client, project_id, body))
    assert response.status_code == 201, response.text
    with pytest.raises(InvalidTransitionError, match="existing video work changed"):
        start_batch(service, project_id, ready)
    assert not provider.submits


def test_copy_cannot_inherit_dispatch_grant(tmp_path):
    storage, _client, service, provider, project_id, view = batch_environment(tmp_path)
    started = start_batch(service, project_id, ready_batch(service, project_id, view))
    service.step(project_id)
    with closing(storage.projects.open(project_id)) as original:
        copied_home = tmp_path / "isolated-project-copy"
        shutil.copytree(original.home, copied_home)
        # SQLite backup gives a consistent copy, rather than copying live WAL blindly.
        import sqlite3
        with sqlite3.connect(copied_home / original.manifest.database_path) as destination:
            with sqlite3.connect(f"{original.database_path.as_uri()}?mode=ro", uri=True) as source:
                source.backup(destination)
    with closing(ProjectStore.open(copied_home)) as copied:
        with pytest.raises(InvalidTransitionError, match="no execution grant"):
            service.grants.require(copied, started["id"], started["manifestHash"])
    assert not provider.submits


def test_one_controller_process_lease_prevents_competing_execution(tmp_path):
    _storage, _client, service, _provider, project_id, _view = batch_environment(tmp_path)
    first, second = VideoBatchRuntime(service), VideoBatchRuntime(service)
    assert first.acquire()
    try:
        assert not second.acquire()
        with pytest.raises(InvalidTransitionError, match="another video batch controller"):
            second.step(project_id)
    finally:
        import os
        os.close(first.descriptor); first.descriptor = None


def test_adopted_prepared_job_obeys_pause_and_its_original_prompt(tmp_path):
    from plotloom.video_batch_contracts import BatchSetup
    storage, client, service, provider, project_id, view = batch_environment(tmp_path)
    service.control(project_id, BatchControl(batchId=view["id"], expectedControlRevision=view["controlRevision"], action="cancel"))
    target = view["manifest"]["targets"][0]
    args = target["args"]
    body = {"approvalId": args["approval_id"], "shotId": args["shot_id"], "storyboardRevision": args["storyboard_revision"],
        "expectedSelectionRevision": args["expected_selection_revision"], "idempotencyKey": "adopt-prepared-manual", "seed": 9,
        "requestedDurationSeconds": args["requested_seconds"], "aspectPolicy": "reject_mismatch"}
    response = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=reviewed_h3_body(client, project_id, body))
    assert response.status_code == 201, response.text
    existing = response.json()
    adopted = service.setup(project_id, BatchSetup(profileId="minimax_h3_quality8_portrait_576x1024_v2"))
    target = next(item for item in adopted["manifest"]["targets"] if item["shotId"] == args["shot_id"])
    assert target["mode"] == "prepared" and target["compiledPrompt"] == existing["snapshot"]["compiledPrompt"]
    ready = ready_batch(service, project_id, adopted)
    started = start_batch(service, project_id, ready)
    service.control(project_id, BatchControl(batchId=started["id"], expectedControlRevision=started["controlRevision"], action="pause"))
    with closing(storage.projects.open(project_id)) as store:
        with pytest.raises(InvalidTransitionError): service.video.submit(store, existing["id"])
    assert not provider.submits


def test_frozen_caps_block_entire_manifest_before_any_provider_call(tmp_path):
    from plotloom.video_batch_contracts import BatchSetup
    _storage, _client, service, provider, project_id, view = batch_environment(tmp_path)
    service.control(project_id, BatchControl(batchId=view["id"], expectedControlRevision=view["controlRevision"], action="cancel"))
    bounded = service.setup(project_id, BatchSetup(profileId="minimax_h3_quality8_portrait_576x1024_v2", maxJobs=1, maxRequestedSeconds=5))
    assert bounded["manifest"]["blockers"] and bounded["manifest"]["newJobs"] == 6
    with pytest.raises(InvalidTransitionError): service.draft(project_id, bounded["revision"])
    assert not provider.submits and provider.preflight_calls == 0


def test_cancelled_predecessor_keeps_observing_after_new_setup(tmp_path, monkeypatch):
    from plotloom.video_batch_contracts import BatchSetup
    storage, _client, service, provider, project_id, view = batch_environment(tmp_path)
    started = start_batch(service, project_id, ready_batch(service, project_id, view))
    service.step(project_id); service.step(project_id)
    with closing(storage.projects.open(project_id)) as store:
        original = service.video.jobs(store)[0]
    assert original["state"] == "submitted"
    with closing(storage.projects.open(project_id)) as store:
        assert store.repository.video_batches.needs_step(project_id)
    service.control(project_id, BatchControl(batchId=started["id"], expectedControlRevision=started["controlRevision"], action="cancel"))
    successor = service.setup(project_id, BatchSetup(profileId="minimax_h3_quality8_portrait_576x1024_v2"))
    assert successor["id"] != started["id"]
    with closing(storage.projects.open(project_id)) as store:
        assert store.repository.video_batches.needs_step(project_id)
    observed = []
    monkeypatch.setattr(service.video, "reconcile", lambda store, identifier: observed.append(identifier))
    service.step(project_id)
    assert observed == [original["id"]] and len(provider.submits) == 1
