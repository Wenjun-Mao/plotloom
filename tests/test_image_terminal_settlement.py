"""No idle/cancel shortcut: a validated no-output block has its own outcome."""
import json
from uuid import uuid4

import pytest

from plotloom.specialist_settings import SpecialistRegistry
from tests.image_terminal_support import ImageTerminalRuntime


@pytest.mark.parametrize("target", ["image_job", "character_reference_proposal", "art_reference_proposal"])
@pytest.mark.parametrize("unknown", [False, True])
def test_cancelled_before_generation_block_settles_without_publication(tmp_path, monkeypatch, target, unknown):
    runtime = ImageTerminalRuntime(tmp_path, monkeypatch, target, unknown=unknown)
    assert runtime.registry.view()["busy"]
    assert runtime.client.get(runtime.url).status_code == 200
    response = runtime.settle()
    assert response.status_code == 200, response.text
    assert response.json() == {"state": "completed", "outcome": "blocked", "candidates": []}
    restored = SpecialistRegistry(runtime.storage.application.root)
    assert not restored.view()["busy"]
    receipt = json.loads((runtime.dispatch_root() / runtime.job["id"] / "receipt.json").read_text())
    assert receipt["state"] == "completed"
    assert receipt["terminalSettlement"]["operatorReview"] == runtime.review
    assert runtime.settle().status_code == 200
    runtime.assert_unpublished()


@pytest.mark.parametrize("fault", ["missing", "malformed", "foreign_job", "foreign_hash", "foreign_task", "pin", "generation", "active", "outputs_declared", "outputs_file", "completion", "extra", "numeric_false", "symlink", "package"])
def test_invalid_or_uncertain_marker_keeps_reservation(tmp_path, monkeypatch, fault):
    runtime = ImageTerminalRuntime(tmp_path, monkeypatch)
    marker_path = runtime.delivery / "terminal.json"
    if fault == "missing": marker_path.unlink()
    elif fault == "malformed": marker_path.write_text("{")
    elif fault in {"foreign_job", "foreign_hash", "foreign_task", "pin", "generation", "active", "outputs_declared", "numeric_false"}:
        if fault == "foreign_job": runtime.marker["jobId"] = "ij_" + "c" * 32
        if fault == "foreign_hash": runtime.marker["requestHash"] = "c" * 64
        if fault == "foreign_task": runtime.marker["taskId"] = str(uuid4())
        if fault == "pin": runtime.marker["executorProvenance"]["skillHash"] = "c" * 64
        if fault == "generation": runtime.marker["generationStarted"] = True
        if fault == "active": runtime.marker["activeTools"] = True
        if fault == "outputs_declared": runtime.marker["outputsProduced"] = True
        if fault == "numeric_false": runtime.marker["generationStarted"] = 0
        runtime.write_marker()
    elif fault == "outputs_file":
        (runtime.delivery / "outputs").mkdir(exist_ok=True)
        (runtime.delivery / "outputs" / "partial.png").write_bytes(b"staged")
    elif fault == "completion": (runtime.delivery / "completion.json").write_text("{}")
    elif fault == "extra": (runtime.delivery / "unexpected").write_text("staged")
    elif fault == "symlink":
        marker_path.rename(runtime.delivery / "saved.json")
        marker_path.symlink_to(runtime.delivery / "saved.json")
    elif fault == "package": (runtime.delivery.parent / "package" / "COPY_ASSIGNMENT.txt").write_text("tampered")
    response = runtime.settle()
    assert response.status_code in {409, 422}, response.text
    assert runtime.registry.view()["busy"]
    assert runtime.registry.status(runtime.job["id"])["state"] == "queued"
    assert len(runtime.calls) == 1


@pytest.mark.parametrize("field,value", [("observedIdle", False), ("reviewedBlockedVerdict", False), ("observedIdle", 1), ("markerHash", "c" * 64), ("taskId", str(uuid4())), ("terminalTurnId", "not-a-turn"), ("terminalRevision", 0)])
def test_explicit_review_is_required_and_bound(tmp_path, monkeypatch, field, value):
    runtime = ImageTerminalRuntime(tmp_path, monkeypatch)
    runtime.review[field] = value
    assert runtime.settle().status_code in {409, 422}
    assert runtime.registry.view()["busy"]


def test_competing_lease_retained_and_repeat_does_not_remove_new_owner(tmp_path, monkeypatch):
    runtime = ImageTerminalRuntime(tmp_path, monkeypatch)
    active = runtime.dispatch_root() / "inflight.json"
    competing = {"jobId": "ij_" + "d" * 32, "taskId": runtime.task_id}
    active.write_text(json.dumps(competing))
    assert runtime.settle().status_code in {409, 422}
    assert json.loads(active.read_text()) == competing
    active.write_text(json.dumps({"jobId": runtime.job["id"], "taskId": runtime.task_id}))
    assert runtime.settle().status_code == 200
    active.write_text(json.dumps(competing))
    assert runtime.settle().status_code == 200
    assert json.loads(active.read_text()) == competing
    runtime.review["terminalRevision"] += 1
    assert runtime.settle().status_code in {409, 422}
    assert json.loads(active.read_text()) == competing


def test_crash_after_exact_release_recovers_retained_proof(tmp_path, monkeypatch):
    runtime = ImageTerminalRuntime(tmp_path, monkeypatch)
    receipt = runtime.dispatch_root() / runtime.job["id"] / "receipt.json"
    assert runtime.settle().status_code == 200
    value = json.loads(receipt.read_text())
    value["state"] = "queued"  # Simulate unlink before final tombstone write.
    receipt.write_text(json.dumps(value))
    assert runtime.settle().status_code == 200
    assert json.loads(receipt.read_text())["state"] == "completed"
    runtime.assert_unpublished()


def test_crash_tombstone_finishes_without_touching_successor(tmp_path, monkeypatch):
    runtime = ImageTerminalRuntime(tmp_path, monkeypatch)
    receipt = runtime.dispatch_root() / runtime.job["id"] / "receipt.json"
    assert runtime.settle().status_code == 200
    value = json.loads(receipt.read_text())
    value["state"] = "queued"
    receipt.write_text(json.dumps(value))
    active = runtime.dispatch_root() / "inflight.json"
    successor = {"jobId": "ij_" + "e" * 32, "taskId": runtime.task_id}
    active.write_text(json.dumps(successor))
    assert runtime.settle().status_code == 200
    assert json.loads(receipt.read_text())["state"] == "completed"
    assert json.loads(active.read_text()) == successor


def test_role_mapped_identity_reference_remains_verified(tmp_path, monkeypatch):
    runtime = ImageTerminalRuntime(tmp_path, monkeypatch, reference=True)
    assert runtime.client.get(runtime.url).status_code == 200
    assert runtime.settle().status_code == 200
    runtime.assert_unpublished()


def test_non_cancelled_request_cannot_settle(tmp_path, monkeypatch):
    runtime = ImageTerminalRuntime(tmp_path, monkeypatch)
    # Real repository state transition seeded only in a disposable test DB.
    import sqlite3
    store = runtime.storage.projects.open(runtime.project_id)
    database = store.database_path
    store.close()
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE v2_image_jobs SET state='exported' WHERE id=?", (runtime.job["id"],))
    assert runtime.settle().status_code in {409, 422}
    assert runtime.registry.view()["busy"]
