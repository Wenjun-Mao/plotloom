"""Acknowledged deletion is an irreversible, cross-restart admission boundary."""
from contextlib import closing
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.project_abandonment_contracts import AbandonmentPreview
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.operational_state import (
    ProjectAccessLease,
    ProjectBusyError,
)
from plotloom.project_storage.project_home import ProjectHome
from plotloom.project_storage.schema_upgrade import upgrade_project
from plotloom.project_storage.write_admission import ProjectDeletionPendingError
from plotloom.specialist_settings import SpecialistRegistry
from tests.autopilot_compact_text_fixtures import compact_safety_image_environment
from tests.test_autopilot_image_safety import reach
from tests.test_autopilot_recovery import storage_at


def consent_for(project):
    return {"expectedProjectRevision": project.revision, "expectedLifecycleRevision": project.lifecycle_revision,
        "confirmationTitle": project.brief.title, "previewHash": "a" * 64, "acknowledgeUnknownRemote": True}


def acknowledge(storage, project_id, home, manifest, consent):
    storage.application.abandonment.prepare(ProjectHome(home, manifest), project_id, consent)
    storage.application.abandonment.acknowledge(project_id, AbandonmentPreview(project_id=project_id,
        preview_hash="b" * 64, eligible=True, blockers=[], unknown_attempt_ids=[], revoked=True))


@pytest.mark.parametrize("withdrawn", [False, True])
@pytest.mark.parametrize("restart", [False, True])
def test_actual_erase_failure_quarantines_writes_reopen_and_dispatch(tmp_path, monkeypatch,
        compact_two_cut_text_prefix, withdrawn, restart):
    storage, _registry, service, view, images, texts = compact_safety_image_environment(
        tmp_path, monkeypatch, compact_two_cut_text_prefix, auto_deliver=False)
    try:
        sent, _ = reach(storage, service, view, "character-reference", "sent")
        service.control(view.project_id, RunControlRequest(expected_revision=sent.revision, action="cancel"))
        with closing(storage.projects.open(view.project_id)) as store:
            home, project = store.home, store.project()
            with store.repository.engine.connect() as connection:
                original_attempts = connection.exec_driver_sql("SELECT * FROM v2_autopilot_exec_attempts ORDER BY id").all()
        with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as neighbor:
            neighbor_id = neighbor.manifest.project_id
        app = create_project_folder_authoring_app(storage)
        host_calls = []
        def host(packet, *, revoke=False):
            host_calls.append((packet.model_dump(mode="json"), revoke))
            return AbandonmentPreview(project_id=view.project_id, preview_hash="c" * 64,
                eligible=True, blockers=[], unknown_attempt_ids=["exact-unknown"], revoked=revoke)
        monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", host)
        client = TestClient(app)
        path = f"/api/v2/projects/{view.project_id}"
        preview = client.get(path + "/abandonment-preview").json()
        consent = {key: preview[key] for key in ("expectedProjectRevision", "expectedLifecycleRevision", "confirmationTitle", "previewHash")}
        consent["acknowledgeUnknownRemote"] = True
        with monkeypatch.context() as failure:
            if withdrawn:
                import shutil
                original = shutil.rmtree
                def fail_remove(*_args, **_kwargs):
                    raise PermissionError("fault after manifest withdrawal")
                fail_remove.avoids_symlink_attacks = original.avoids_symlink_attacks
                failure.setattr(shutil, "rmtree", fail_remove)
            else:
                unlink = Path.unlink
                def fail_unlink(target, *args, **kwargs):
                    if target == home / "project.json":
                        raise PermissionError("fault before manifest withdrawal")
                    return unlink(target, *args, **kwargs)
                failure.setattr(Path, "unlink", fail_unlink)
            result = client.post(path + "/abandon-and-delete", json=consent)
        assert result.status_code == 409 and "尚未完成" in result.text
        assert (home / "project.json").exists() is not withdrawn
        intent = storage.application.abandonment.current(view.project_id)
        calls_before, images_before, texts_before = list(host_calls), list(images), list(texts)
        if restart:
            storage = ProjectFolderStorage(outputs_root=storage.projects.outputs_root, application_data_root=storage.application.root)
            app = create_project_folder_authoring_app(storage)
            monkeypatch.setattr(app.state.autopilot_service.registry, "codex_exec_abandonment", lambda *_a, **_k: pytest.fail("ACK retry must not repeat host command"))
            client = TestClient(app)
        patch = client.patch(path, json={"expectedRevision": project.revision,
            "brief": project.brief.model_dump(mode="json", by_alias=True) | {"title": "must not be admitted"}})
        assert patch.status_code == (404 if withdrawn else 409), patch.text
        for action, payload in (("unfreeze", {}), ("archive", {"expectedLifecycleRevision": 1}),
                ("restore", {"expectedLifecycleRevision": 1}), ("duplicate", {"expectedLifecycleRevision": 1}), ("snapshots", {})):
            response = client.post(path + "/" + action, json=payload)
            assert response.status_code == (404 if withdrawn else 409), response.text
        assert len(client.get("/api/v2/project-deletions").json()) == 1
        assert client.get("/api/v2/projects").status_code == 200
        if not withdrawn:
            for admission in ("authority", "inspection"):
                with pytest.raises(ProjectDeletionPendingError):
                    storage.projects.read_open(view.project_id, admission=admission)
            with closing(storage.projects.inspect(view.project_id)) as inspection:
                assert inspection.project() == project
                with inspection.repository.engine.connect() as connection:
                    assert connection.exec_driver_sql("SELECT * FROM v2_autopilot_exec_attempts ORDER BY id").all() == original_attempts
            for operation in (lambda: service.continue_material(view.project_id, None),
                    lambda: upgrade_project(home, SpecialistRegistry(storage.application.root))):
                with pytest.raises(ProjectDeletionPendingError):
                    operation()
            from plotloom.project_storage.text_dispatch import ProjectRunDispatcher
            dispatcher = ProjectRunDispatcher(storage, provider_resolver=None, secrets=None, max_workers=1)
            assert not dispatcher.reconcile_startup()[view.project_id].resubmit_run_ids
            with pytest.raises(ProjectDeletionPendingError):
                dispatcher.require_open_project(view.project_id)
        assert host_calls == calls_before and images == images_before and texts == texts_before
        assert storage.application.abandonment.current(view.project_id) == intent
        with closing(storage.projects.open(neighbor_id)) as neighbor:
            neighbor.update_brief(neighbor.project().brief.model_copy(update={"title": "neighbor remains writable"}), expected_revision=1)
        assert client.post(path + "/abandon-and-delete", json=consent | {"previewHash": "0" * 64}).status_code == 409
        assert home.exists()
        assert client.post(path + "/abandon-and-delete", json=consent).status_code == 204
        assert not home.exists() and not client.get("/api/v2/project-deletions").json()
        assert host_calls == calls_before
    finally:
        service.close()


@pytest.mark.parametrize("mode", ["shared", "exclusive"])
def test_ack_committed_during_lease_acquisition_is_seen_before_admission(tmp_path, monkeypatch, mode):
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project, home, manifest = store.project(), store.home, store.manifest
    acquire = ProjectAccessLease.acquire
    leases = []
    def after_acquire(path, **kwargs):
        lease = acquire(path, **kwargs)
        leases.append(lease)
        acknowledge(storage, project.id, home, manifest, consent_for(project))
        return lease
    monkeypatch.setattr(ProjectAccessLease, "acquire", staticmethod(after_acquire))
    with pytest.raises(ProjectDeletionPendingError):
        storage.projects.open(project.id) if mode == "shared" else storage.projects.reopen_project(project.id)
    assert leases[0].descriptor == -1


def test_existing_shared_handle_prevents_ack_and_identity_creation_publishes_nothing(tmp_path):
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project, home, manifest = store.project(), store.home, store.manifest
        with pytest.raises(ProjectBusyError):
            ProjectAccessLease.acquire(home, mode="exclusive")
        assert storage.application.abandonment.current(project.id) is None
    acknowledge(storage, project.id, home, manifest, consent_for(project))
    before = set(storage.projects.outputs_root.iterdir())
    with pytest.raises(ProjectDeletionPendingError):
        storage.projects.create(FIXED_CHINESE_BRIEF, project_id=project.id, created_at=project.created_at + timedelta(days=1))
    with pytest.raises(ProjectDeletionPendingError):
        storage.projects.resume_creation(FIXED_CHINESE_BRIEF, project_id=project.id, created_at=project.created_at)
    assert set(storage.projects.outputs_root.iterdir()) == before


@pytest.mark.parametrize("snapshot", [False, True])
def test_recovery_cannot_copy_or_publish_ack_pending_identity(tmp_path, snapshot):
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project, home, manifest = store.project(), store.home, store.manifest
    storage.projects.close_project(project.id)
    source = storage.recovery.create_snapshot(project.id).location if snapshot else home
    acknowledge(storage, project.id, home, manifest, consent_for(project))
    before = set(storage.projects.outputs_root.iterdir())
    with pytest.raises(ProjectDeletionPendingError):
        storage.recovery.restore(Path(source))
    assert set(storage.projects.outputs_root.iterdir()) == before
