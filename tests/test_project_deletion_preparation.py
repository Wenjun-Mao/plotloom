"""Deletion preparation is observation; stopping binds exact consent and work."""
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_abandonment_contracts import AbandonmentPreview
from tests.autopilot_compact_text_fixtures import compact_safety_image_environment
from tests.test_autopilot_recovery import storage_at
from tests.test_autopilot_image_safety import reach


def test_cancellation_dispatches_once_per_text_bridge_or_image_attempt_and_never_unknown_owners(monkeypatch):
    from plotloom.autopilot_contracts import POLICY_VERSION
    from plotloom.autopilot_image_controller import AutopilotImageController
    from plotloom.autopilot_text_controller import AutopilotTextController
    text = AutopilotTextController.__new__(AutopilotTextController)
    text.registry = object()
    text.bridge_services = {"bridge-intent": object(), "bridge-presentation": object()}
    store = SimpleNamespace(**{name: Mock() for name in ("cancel_outline_candidate", "cancel_branch_candidate",
        "cancel_cast_candidate", "cancel_art_candidate", "cancel_script_candidate", "cancel_storyboard_review_candidate")},
        repository=SimpleNamespace(production_bridge_intent=SimpleNamespace(cancel=Mock())))
    owners = ["outline", "branches", "characters", "art", "script", "storyboard",
        "bridge-intent", "bridge-presentation", "image", "character-reference", "art-reference", "unrelated-domain"]
    checkpoints = [{"state": "sent", "operationKey": owner, "evidence": {"owner": owner,
        "subjectId": owner, "jobId": f"job-{owner}", "executorAttemptId": str(uuid4())}} for owner in owners]
    view = SimpleNamespace(id="exact-run", project_id="exact-project", policy=SimpleNamespace(version=POLICY_VERSION), checkpoints=checkpoints)
    calls = []
    def cancel(_store, _registry, _run_id, checkpoint):
        calls.append(checkpoint["evidence"]["executorAttemptId"])
    monkeypatch.setattr("plotloom.autopilot_text_controller.cancel_codex_exec", cancel)
    monkeypatch.setattr("plotloom.autopilot_image_controller.cancel_codex_exec", cancel)
    text.cancel_pending(store, view)
    AutopilotImageController(object()).cancel_pending(store, view)
    assert len(calls) == len(owners) - 1 and len(set(calls)) == len(calls)
    assert checkpoints[-1]["evidence"]["executorAttemptId"] not in calls
    assert store.cancel_outline_candidate.call_count == 1
    assert store.repository.production_bridge_intent.cancel.call_count == 2


def test_cancelled_publication_cannot_hide_retained_exec_from_host_guard(tmp_path, monkeypatch, compact_two_cut_text_prefix):
    from plotloom.project_storage.operational_state import close_blockers
    storage, _registry, service, view, _calls, _text = compact_safety_image_environment(
        tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        sent, checkpoint = reach(storage, service, view, "character-reference", "sent")
        service.control(view.project_id, RunControlRequest(expected_revision=sent.revision, action="cancel"))
        with closing(storage.projects.open(view.project_id)) as store:
            store.media.cancel_character_reference_proposal(view.project_id, checkpoint["evidence"]["jobId"], "Exact disposable fixture cancellation")
            assert close_blockers(store) == []
            home = store.home
        app = create_project_folder_authoring_app(storage)
        calls = []
        def host(packet, *, revoke=False):
            calls.append(revoke)
            return AbandonmentPreview(project_id=view.project_id, preview_hash="f" * 64,
                eligible=True, blockers=[], unknown_attempt_ids=[str(packet.attempts[-1].attempt_id)], revoked=revoke)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", host)
        client = TestClient(app)
        path = f"/api/v2/projects/{view.project_id}"
        preview = client.get(path + "/deletion-preview").json()
        assert preview["mode"] == "abandon" and preview["unknownAttemptIds"] and calls == [False]
        consent = {key: preview[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "scopeHash")}
        refused = client.post(path + "/permanent-delete", json=consent)
        assert refused.status_code == 409 and "原主机撤销" in refused.text and home.exists()
        assert calls == [False]
    finally:
        service.close()


def save_unsent_draft(client, path):
    return client.put(path + "/authoring-drafts", json={"editorScope": "brief", "entityId": "root",
        "expectedDraftRevision": 0, "baseCanonicalRevision": 1,
        "payload": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True) | {"title": "后来保存的草稿"}})


def test_idle_preparation_uses_ordinary_delete_without_host_or_project_writes(tmp_path, monkeypatch):
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home = store.manifest.project_id, store.home
    app = create_project_folder_authoring_app(storage)
    monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment",
        lambda *_args, **_kwargs: pytest.fail("idle deletion must not contact execution host"))
    client = TestClient(app)
    path = f"/api/v2/projects/{project_id}"
    before = {str(path.relative_to(home)): path.read_bytes() for path in home.rglob("*") if path.is_file()}
    preview = client.get(path + "/deletion-preview")
    assert preview.status_code == 200, preview.text
    context = preview.json()
    assert context["mode"] == "ordinary" and context["run"] is None
    assert {str(path.relative_to(home)): path.read_bytes() for path in home.rglob("*") if path.is_file()} == before
    consent = {key: context[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle")}
    assert client.post(path + "/permanent-delete", json=consent).status_code == 204
    assert not home.exists()


def test_final_ordinary_erasure_rechecks_material_scope_even_without_project_revision_change(tmp_path):
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home = store.manifest.project_id, store.home
    client = TestClient(create_project_folder_authoring_app(storage))
    path = f"/api/v2/projects/{project_id}"
    preview = client.get(path + "/deletion-preview").json()
    assert save_unsent_draft(client, path).status_code == 200
    assert client.get(path).json()["revision"] == preview["expectedProjectRevision"]
    consent = {key: preview[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "scopeHash")}
    refused = client.post(path + "/permanent-delete", json=consent)
    assert refused.status_code == 409 and "任务范围已改变" in refused.text and home.exists()


@pytest.mark.parametrize("change", [None, "revision", "run_id", "scope", "manual"])
def test_paused_stop_requires_exact_scope_and_actual_run_identity(tmp_path, monkeypatch, compact_two_cut_text_prefix, change):
    storage, _registry, service, view, _calls, _text = compact_safety_image_environment(
        tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        current = service.control(view.project_id, RunControlRequest(expected_revision=view.revision, action="pause"))
        app = create_project_folder_authoring_app(storage)
        def host(packet, *, revoke=False):
            return AbandonmentPreview(project_id=view.project_id, preview_hash="a" * 64,
                eligible=True, blockers=[], unknown_attempt_ids=["unknown-retained"], revoked=revoke)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", host)
        client = TestClient(app)
        path = f"/api/v2/projects/{view.project_id}"
        response = client.get(path + "/deletion-preview")
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview["mode"] == "stop" and preview["run"]["state"] == "paused"
        ordinary = {key: preview[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle")}
        assert client.post(path + "/permanent-delete", json=ordinary).status_code == 409
        assert service.storage.projects.outputs_root.exists()
        consent = {key: preview[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "scopeHash")}
        consent |= {"expectedRunId": current.id, "expectedRunRevision": current.revision}
        if change == "revision":
            consent["expectedRunRevision"] += 1
        if change == "run_id":
            consent["expectedRunId"] = "replacement-run-with-same-revision"
        if change == "scope":
            consent["scopeHash"] = "f" * 64
        if change == "manual":
            with closing(storage.projects.open(view.project_id)) as store:
                with store.repository.manual_command():
                    store.repository.autopilot.control(view.project_id, expected_revision=current.revision, action="cancel")
            assert client.post(path + "/stop-for-deletion", json=consent).status_code == 409
            return
        stopped = client.post(path + "/stop-for-deletion", json=consent)
        if change:
            assert stopped.status_code == 409, stopped.text
            with closing(storage.projects.open(view.project_id)) as store:
                assert store.repository.autopilot.current(view.project_id).state == "paused"
            return
        assert stopped.status_code == 200 and stopped.json()["runId"] == current.id and stopped.json()["state"] == "cancelled", stopped.text
        fresh = client.get(path + "/deletion-preview").json()
        assert fresh["scopeHash"] == preview["scopeHash"]
        assert fresh["mode"] in {"ordinary", "abandon"} and fresh["run"] is None
    finally:
        service.close()


@pytest.mark.parametrize("still_running", [False, True])
def test_running_owned_task_can_request_exact_stop_before_host_erasure_quiescence(tmp_path, monkeypatch, compact_two_cut_text_prefix, still_running):
    storage, registry, service, view, _calls, _text = compact_safety_image_environment(
        tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        sent, _checkpoint = reach(storage, service, view, "character-reference", "sent")
        assert sent.state in {"running", "waiting"}
        app = create_project_folder_authoring_app(storage)
        cancelled, revocations = [], []
        def host(packet, *, revoke=False):
            blocked = not cancelled or still_running
            revocations.append(revoke)
            return AbandonmentPreview(project_id=view.project_id, preview_hash="e" * 64,
                eligible=not blocked, blockers=[f"{packet.attempts[-1].job_id}: local process group is not proven absent"] if blocked else [],
                unknown_attempt_ids=[str(packet.attempts[-1].attempt_id)], revoked=revoke)
        def cancel(attempt):
            cancelled.append(attempt.attempt_id)
            return registry.codex_exec_cancel(attempt)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", host)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_cancel", cancel)
        client = TestClient(app)
        path = f"/api/v2/projects/{view.project_id}"
        preview = client.get(path + "/deletion-preview").json()
        assert preview["mode"] == "stop" and preview["stopWarnings"] and not cancelled
        consent = {key: preview[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "scopeHash")}
        stopped = client.post(path + "/stop-for-deletion", json=consent | {
            "expectedRunId": preview["run"]["id"], "expectedRunRevision": preview["run"]["revision"]})
        assert stopped.status_code == 200, stopped.text
        assert len(cancelled) == 1 and not any(revocations)
        fresh = stopped.json()["deletionPreview"]
        assert stopped.json()["state"] == "cancelled" and fresh["scopeHash"] == preview["scopeHash"]
        assert fresh["mode"] == ("blocked" if still_running else "abandon")
        if still_running:
            assert "本地任务进程仍存在" in fresh["blockers"][0]
            assert client.get(path).status_code == 200
        else:
            final = {key: fresh[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "scopeHash", "previewHash")}
            assert client.post(path + "/abandon-and-delete", json=final | {"acknowledgeUnknownRemote": True}).status_code == 204
            assert revocations.count(True) == 1
    finally:
        service.close()


def test_recorded_unknown_work_stops_then_abandons_only_confirmed_scope(tmp_path, monkeypatch, compact_two_cut_text_prefix):
    storage, registry, service, view, _calls, _text = compact_safety_image_environment(
        tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        sent, _checkpoint = reach(storage, service, view, "character-reference", "sent")
        service.control(view.project_id, RunControlRequest(expected_revision=sent.revision, action="pause"))
        app = create_project_folder_authoring_app(storage)
        calls = []
        def host(packet, *, revoke=False):
            calls.append((packet.model_dump(mode="json", by_alias=True), revoke))
            return AbandonmentPreview(project_id=view.project_id, preview_hash="d" * 64,
                eligible=True, blockers=[], unknown_attempt_ids=["exact-unknown"], revoked=revoke)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", host)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_cancel", registry.codex_exec_cancel)
        client = TestClient(app)
        path = f"/api/v2/projects/{view.project_id}"
        preview = client.get(path + "/deletion-preview").json()
        assert preview["mode"] == "stop" and preview["unknownAttemptIds"] == ["exact-unknown"]
        consent = {key: preview[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "scopeHash")}
        stopped = client.post(path + "/stop-for-deletion", json=consent | {
            "expectedRunId": preview["run"]["id"], "expectedRunRevision": preview["run"]["revision"]})
        assert stopped.status_code == 200, stopped.text
        fresh = stopped.json()["deletionPreview"]
        assert fresh["mode"] == "abandon" and fresh["scopeHash"] == preview["scopeHash"]
        assert not any(revoke for _, revoke in calls)
        # A later draft changes material without creating a new canonical Brief.
        assert save_unsent_draft(client, path).status_code == 200
        refused = client.post(path + "/abandon-and-delete", json=consent | {
            "previewHash": fresh["previewHash"], "acknowledgeUnknownRemote": True})
        assert refused.status_code == 409 and "任务范围已改变" in refused.text
        assert not any(revoke for _, revoke in calls)
        latest = client.get(path + "/deletion-preview").json()
        final = {key: latest[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "scopeHash", "previewHash")}
        assert client.post(path + "/abandon-and-delete", json=final | {"acknowledgeUnknownRemote": True}).status_code == 204
        assert calls[-1][1] is True and calls[-1][0]["attempts"]
        assert all(call[0]["projectId"] == view.project_id for call in calls)
    finally:
        service.close()
