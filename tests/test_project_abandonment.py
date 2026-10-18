"""Explicit exact-home deletion and retry on real disposable material records."""
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.project_abandonment_contracts import AbandonmentPreview
from tests.autopilot_compact_text_fixtures import compact_safety_image_environment
from tests.autopilot_continuation_layout_fixtures import retain_pre_continuation_layout
from tests.test_autopilot_image_safety import reach


@pytest.mark.parametrize("prior", [False, True])
def test_abandonment_deletes_only_exact_stuck_project_without_requiring_upgrade(tmp_path, monkeypatch, compact_two_cut_text_prefix, prior):
    storage, _registry, service, view, _calls, _text = compact_safety_image_environment(tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        sent, _checkpoint = reach(storage, service, view, "character-reference", "sent")
        service.control(view.project_id, RunControlRequest(expected_revision=sent.revision, action="cancel"))
        with closing(storage.projects.open(view.project_id)) as store:
            home, brief = store.home, store.project().brief
        with closing(storage.projects.create(brief.model_copy(update={"title": "保留邻居"}))) as neighbor:
            neighbor_id, neighbor_home = neighbor.manifest.project_id, neighbor.home
        if prior:
            retain_pre_continuation_layout(home)
        app = create_project_folder_authoring_app(storage)
        requests = []
        def host(packet, *, revoke=False):
            requests.append((packet, revoke))
            return AbandonmentPreview(project_id=view.project_id, preview_hash="a" * 64,
                eligible=True, blockers=[], unknown_attempt_ids=[str(item.attempt_id) for item in packet.attempts if item.state not in {"completed", "failed", "settled"}], revoked=revoke)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", host)
        client = TestClient(app)
        path = f"/api/v2/projects/{view.project_id}"
        preview = client.get(path + "/abandonment-preview")
        assert preview.status_code == 200, preview.text
        context = preview.json()
        consent = {key: context[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "previewHash")}
        denied = client.post(path + "/abandon-and-delete", json=consent)
        assert denied.status_code == 409 and home.exists() and not any(revoke for _, revoke in requests)
        response = client.post(path + "/abandon-and-delete", json=consent | {"acknowledgeUnknownRemote": True})
        assert response.status_code == 204, response.text
        assert not home.exists() and neighbor_home.exists()
        assert requests[-1][1] is True
        assert all(packet.project_id == view.project_id for packet, _ in requests)
        assert client.get("/api/v2/project-deletions").json() == []
        with closing(storage.projects.open(neighbor_id)):
            pass
    finally:
        service.close()


def test_partial_erasure_retry_survives_lost_manifest_and_application_reopen(tmp_path, monkeypatch, compact_two_cut_text_prefix):
    storage, _registry, service, view, _calls, _text = compact_safety_image_environment(tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        sent, _checkpoint = reach(storage, service, view, "character-reference", "sent")
        service.control(view.project_id, RunControlRequest(expected_revision=sent.revision, action="cancel"))
        with closing(storage.projects.open(view.project_id)) as store:
            home = store.home
        app = create_project_folder_authoring_app(storage)
        host_calls = []
        def host(packet, *, revoke=False):
            host_calls.append(revoke)
            return AbandonmentPreview(project_id=view.project_id, preview_hash="b" * 64, eligible=True,
                blockers=[], unknown_attempt_ids=[], revoked=revoke)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", host)
        client = TestClient(app)
        path = f"/api/v2/projects/{view.project_id}"
        context = client.get(path + "/abandonment-preview").json()
        consent = {key: context[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "previewHash")}
        consent["acknowledgeUnknownRemote"] = True
        import shutil
        original = shutil.rmtree
        def interrupted(*_args, **_kwargs):
            raise OSError("injected after manifest withdrawal")
        interrupted.avoids_symlink_attacks = original.avoids_symlink_attacks
        monkeypatch.setattr(shutil, "rmtree", interrupted)
        response = client.post(path + "/abandon-and-delete", json=consent)
        assert response.status_code == 409 and "尚未完成" in response.text
        assert home.exists() and not (home / "project.json").exists()
        monkeypatch.setattr(shutil, "rmtree", original)
        from plotloom.project_storage import ProjectFolderStorage
        reopened = ProjectFolderStorage(outputs_root=storage.projects.outputs_root, application_data_root=storage.application.root)
        other_app = create_project_folder_authoring_app(reopened)
        monkeypatch.setattr(other_app.state.autopilot_service.registry, "codex_exec_abandonment", lambda *_args, **_kwargs: pytest.fail("durable acknowledged retry must not redispatch or re-revoke"))
        retry_client = TestClient(other_app)
        pending = retry_client.get("/api/v2/project-deletions").json()
        assert len(pending) == 1 and pending[0]["revoked"] and pending[0]["confirmationTitle"] == consent["confirmationTitle"]
        assert retry_client.post(path + "/abandon-and-delete", json=consent | {"previewHash": "0" * 64}).status_code == 409
        assert home.exists() and reopened.application.abandonment.current(view.project_id)["revocation_json"] is not None
        assert retry_client.post(path + "/abandon-and-delete", json=consent).status_code == 204
        assert not home.exists() and retry_client.get("/api/v2/project-deletions").json() == []
        assert host_calls.count(True) == 1
    finally:
        service.close()


@pytest.mark.parametrize("failure", ["failed_revoke", "lost_ack"])
def test_unacknowledged_deletion_can_reinspect_and_refresh_explicit_consent(tmp_path, monkeypatch, compact_two_cut_text_prefix, failure):
    from plotloom.image_job_contracts import ImageJobError
    storage, _registry, service, view, _calls, _text = compact_safety_image_environment(tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        sent, _checkpoint = reach(storage, service, view, "character-reference", "sent")
        service.control(view.project_id, RunControlRequest(expected_revision=sent.revision, action="cancel"))
        app = create_project_folder_authoring_app(storage)
        attempts, revoked = [], False
        host_hash = "a" * 64
        def host(packet, *, revoke=False):
            nonlocal revoked
            if revoke:
                attempts.append(packet)
                if len(attempts) == 1:
                    revoked = failure == "lost_ack"
                    raise ImageJobError("project_abandonment_unconfirmed", "synthetic revoke failure or lost acknowledgement")
                revoked = True
            return AbandonmentPreview(project_id=view.project_id, preview_hash=host_hash,
                eligible=True, blockers=[], unknown_attempt_ids=["retained-exact-attempt"], revoked=revoked)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", host)
        client = TestClient(app)
        path = f"/api/v2/projects/{view.project_id}"
        def consent_from(context):
            return {key: context[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "previewHash")} | {"acknowledgeUnknownRemote": True}
        original = consent_from(client.get(path + "/abandonment-preview").json())
        failed = client.post(path + "/abandon-and-delete", json=original)
        assert failed.status_code == 422 and failed.json()["code"] == "project_abandonment_unconfirmed"
        assert len(attempts) == 1
        retained = storage.application.abandonment.current(view.project_id)
        assert retained["revocation_json"] is None
        if failure == "failed_revoke":
            host_hash = "b" * 64
        else:
            # The host retains its original tombstone hash after a lost ACK;
            # a later project save changes the public consent preview instead.
            with closing(storage.projects.open(view.project_id)) as store, store.repository.manual_command() as session:
                project = store.repository._project_access.rows.project(session, view.project_id)
                project.brief = project.brief | {"title": "重新核对后的片名"}
                project.revision += 1
        refreshed = consent_from(client.get(path + "/abandonment-preview").json())
        assert refreshed["previewHash"] != original["previewHash"]
        assert client.post(path + "/abandon-and-delete", json=original).status_code == 409
        assert len(attempts) == 1
        response = client.post(path + "/abandon-and-delete", json=refreshed)
        assert response.status_code == 204, response.text
        assert len(attempts) == 2 and storage.application.abandonment.current(view.project_id) is None
    finally:
        service.close()


@pytest.mark.parametrize("substitution", ["home", "lock"])
def test_revoked_erasure_revalidates_directory_and_held_lock_after_acquire(tmp_path, monkeypatch, substitution):
    from plotloom.conformance import FIXED_CHINESE_BRIEF
    from plotloom.exceptions import InvalidTransitionError
    from plotloom.project_storage.abandonment_ledger import resume_revoked_erasure
    from plotloom.project_storage.operational_state import ProjectAccessLease
    from plotloom.project_storage.project_home import ProjectHome
    from tests.test_autopilot_recovery import storage_at
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home, manifest = store.manifest.project_id, store.home, store.manifest
    consent = {"expectedProjectRevision": 1, "expectedLifecycleRevision": 1,
        "confirmationTitle": FIXED_CHINESE_BRIEF.title, "previewHash": "a" * 64, "acknowledgeUnknownRemote": True}
    ledger = storage.application.abandonment
    ledger.prepare(ProjectHome(home, manifest), project_id, consent)
    ledger.acknowledge(project_id, AbandonmentPreview(project_id=project_id, preview_hash="b" * 64,
        eligible=True, blockers=[], unknown_attempt_ids=[], revoked=True))
    (home / "project.json").unlink()
    (home / "retained.txt").write_text("approved original content", encoding="utf-8")
    original_intent = ledger.current(project_id)
    acquire = ProjectAccessLease.acquire
    moved = home.with_name(home.name + "-original")
    def substituted(path, **kwargs):
        if substitution == "home":
            path.rename(moved)
            path.mkdir()
            (path / "unrelated.txt").write_text("unrelated replacement", encoding="utf-8")
            return acquire(path, **kwargs)
        lease = acquire(path, **kwargs)
        (path / ".project-operation.lock").unlink()
        (path / ".project-operation.lock").write_text("replacement lock", encoding="utf-8")
        return lease
    monkeypatch.setattr(ProjectAccessLease, "acquire", staticmethod(substituted))
    import shutil
    monkeypatch.setattr(shutil, "rmtree", lambda *_args, **_kwargs: pytest.fail("substituted directory must never be erased"))
    shutil.rmtree.avoids_symlink_attacks = True
    with pytest.raises(InvalidTransitionError, match="身份已变化|目录锁已变化"):
        resume_revoked_erasure(storage.projects, ledger, original_intent, consent)
    assert ledger.current(project_id) == original_intent
    if substitution == "home":
        assert (moved / "retained.txt").read_text(encoding="utf-8") == "approved original content"
        assert (home / "unrelated.txt").read_text(encoding="utf-8") == "unrelated replacement"
    else:
        assert (home / "retained.txt").read_text(encoding="utf-8") == "approved original content"
