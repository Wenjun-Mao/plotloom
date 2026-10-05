"""Lifecycle admission retains unresolved execution independent of publication."""
import json
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.operational_state import ProjectBusyError
from tests.image_terminal_support import ImageTerminalRuntime
from tests.specialist_reconciliation_support import ReconciliationRuntime, prepare, cancel, delivery


def refuse_lifecycle(storage, project_id):
    with closing(storage.projects.inspect(project_id)) as store:
        project = store.project()
    actions = [lambda: storage.projects.close_project(project_id),
               lambda: storage.lifecycle.archive(project_id, expected_lifecycle_revision=project.lifecycle_revision),
               lambda: storage.lifecycle.permanently_delete(project_id, expected_project_revision=project.revision,
                         expected_lifecycle_revision=project.lifecycle_revision, confirmation_title=project.brief.title),
               lambda: storage.recovery.create_snapshot(project_id)]
    for action in actions:
        with pytest.raises(ProjectBusyError, match="native_specialist_execution_unresolved"):
            action()


@pytest.mark.parametrize("stage", ["outline", "characters", "art", "script", "storyboard"])
@pytest.mark.parametrize("receipt_state", ["queued", "outcome_unknown"])
def test_cancelled_text_blocks_only_owner_until_exact_proof(tmp_path, monkeypatch, stage, receipt_state):
    rt = ReconciliationRuntime(tmp_path, monkeypatch)
    _, request = prepare(rt.store, stage)
    client = rt.client(raise_server_exceptions=True)
    assert client.post(rt.url(stage, request.job_id) + "/send").status_code == 200
    receipt = rt.dispatch_root() / request.job_id / "receipt.json"
    record = json.loads(receipt.read_text()) | {"state": receipt_state}
    receipt.write_text(json.dumps(record))
    cancel(rt.store, stage, request.job_id)
    rt.store.close()
    # Restart composition with the same installation ownership, without a server.
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    refuse_lifecycle(storage, rt.project_id)
    other = storage.projects.create(FIXED_CHINESE_BRIEF)
    other_id = other.manifest.project_id
    other.close()
    storage.projects.close_project(other_id)
    storage.recovery.create_snapshot(other_id)
    assert client.post(rt.url(stage, request.job_id) + "/check").json()["state"] == receipt_state
    refuse_lifecycle(storage, rt.project_id)
    with closing(storage.projects.open(rt.project_id)) as store:
        delivery(store, request)
    assert client.post(rt.url(stage, request.job_id) + "/check").json()["state"] == "completed"
    storage.projects.close_project(rt.project_id)
    storage.recovery.create_snapshot(rt.project_id)
    assert len(rt.calls) == 1


@pytest.mark.parametrize("target", ["image_job", "character_reference_proposal", "art_reference_proposal"])
@pytest.mark.parametrize("unknown", [False, True])
def test_cancelled_images_are_project_owned_until_reviewed_terminal(tmp_path, monkeypatch, target, unknown):
    rt = ImageTerminalRuntime(tmp_path, monkeypatch, target, unknown=unknown)
    data = json.loads(rt.registry.path.read_text())
    assert data["jobs"][rt.job["id"]]["projectId"] == rt.project_id
    refuse_lifecycle(rt.storage, rt.project_id)
    assert rt.settle().status_code == 200
    rt.assert_unpublished()
    rt.storage.projects.close_project(rt.project_id)
    rt.storage.recovery.create_snapshot(rt.project_id)


@pytest.mark.parametrize("defect", ["missing-receipt", "lease-unlinked", "reservation-only", "missing-context"])
def test_crash_windows_retain_owner_without_guessing_from_publication(tmp_path, monkeypatch, defect):
    rt = ReconciliationRuntime(tmp_path, monkeypatch)
    _, request = prepare(rt.store, "outline")
    assert rt.client().post(rt.url("outline", request.job_id) + "/send").status_code == 200
    cancel(rt.store, "outline", request.job_id)
    rt.store.close()
    root = rt.dispatch_root()
    if defect == "missing-receipt":
        (root / request.job_id / "receipt.json").unlink()
    elif defect == "reservation-only":
        (root / request.job_id / "receipt.json").unlink()
        (root / request.job_id).rmdir()
    elif defect == "lease-unlinked":
        (root / "inflight.json").unlink()
    else:
        data = json.loads(rt.registry.path.read_text())
        data["jobs"].pop(request.job_id)
        rt.registry.path.write_text(json.dumps(data))
    refuse_lifecycle(rt.storage, rt.project_id)


def test_unsent_cancel_does_not_invent_ownership(tmp_path, monkeypatch):
    rt = ReconciliationRuntime(tmp_path, monkeypatch)
    _, request = prepare(rt.store, "outline")
    cancel(rt.store, "outline", request.job_id)
    rt.store.close()
    rt.storage.projects.close_project(rt.project_id)
    rt.storage.recovery.create_snapshot(rt.project_id)
    assert not rt.calls


def test_dispatch_and_lifecycle_use_project_before_registry_lock(tmp_path, monkeypatch):
    rt = ReconciliationRuntime(tmp_path, monkeypatch)
    _, request = prepare(rt.store, "outline")
    rt.store.close()
    started, finish = Event(), Event()
    import subprocess
    def queue(command, **kwargs):
        started.set()
        assert finish.wait(10)
        return subprocess.CompletedProcess(command, 0, "offline")
    monkeypatch.setattr(subprocess, "run", queue)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(lambda: rt.client().post(rt.url("outline", request.job_id) + "/send"))
        assert started.wait(10)
        with pytest.raises(ProjectBusyError, match="another local writer"):
            rt.storage.projects.close_project(rt.project_id)
        finish.set()
        assert future.result(timeout=10).status_code == 200
    with closing(rt.storage.projects.open(rt.project_id)) as store:
        cancel(store, "outline", request.job_id)
    refuse_lifecycle(rt.storage, rt.project_id)
