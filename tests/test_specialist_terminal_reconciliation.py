"""Explicit checks reconcile retained terminal proof across all real stage owners."""

import json
from uuid import uuid4

import pytest

from plotloom.api.project_folder_specialists import METHODS
from plotloom.codex_image_dispatch import NativeCodexImageDispatcher
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.exceptions import NotFoundError
from plotloom.persistence.project.creative_terminal import CANDIDATE_ROWS
from plotloom.persistence.schema.project_creative_handoff import (
    CreativeHandoffExecutionPinRow,
)
from plotloom.specialist_settings import SpecialistRegistry
from tests.specialist_reconciliation_support import (
    ReconciliationRuntime,
    cancel,
    delivery,
    new_job,
    prepare,
    ready_delivery,
    snapshot_database,
    snapshot_files,
)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    value = ReconciliationRuntime(tmp_path, monkeypatch)
    try:
        yield value
    finally:
        value.store.close()


def dispatched(runtime, stage):
    candidate, request = prepare(runtime.store, stage)
    with runtime.client(raise_server_exceptions=True) as client:
        response = client.post(runtime.url(stage, request.job_id) + "/send")
        assert response.status_code == 200, response.text
    return candidate, request


def job_files(runtime, job):
    return runtime.store.home / "outputs" / "creative-handoff" / "jobs" / job


@pytest.mark.parametrize("stage", METHODS)
def test_cancelled_terminal_proof_survives_restart_and_never_changes_new_head_or_another_lease(runtime, stage):
    _candidate, request = dispatched(runtime, stage)
    job = request.job_id
    delivery(runtime.store, request)
    cancel(runtime.store, stage, job)
    with pytest.raises((NotFoundError, CreativeHandoffError)):
        getattr(runtime.store, METHODS[stage][1])(job)
    next_candidate, _ = prepare(runtime.store, stage)
    before = snapshot_database(runtime.store)
    frozen = snapshot_files(job_files(runtime, job))
    restarted = SpecialistRegistry(runtime.registry_root)
    with runtime.client(restarted) as client:
        assert client.post(runtime.url(stage, job) + "/send").status_code >= 400
        response = client.post(runtime.url(stage, job) + "/check")
        assert response.status_code == 200, response.text
        assert response.json() == {"state": "completed", "candidateStatus": "discarded"}
        assert snapshot_database(runtime.store) == before
        assert snapshot_files(job_files(runtime, job)) == frozen
        assert not restarted.view()["busy"]
        assert client.post(runtime.url(stage, next_candidate.job_id) + "/send").status_code == 200
        restarted.dispatch("image", job_id="ij_" + uuid4().hex, package_path="/image/package", delivery_path="/image/delivery")
        leases = {role: (runtime.dispatch_root(role) / "inflight.json").read_bytes() for role in ("text", "image")}
        again = client.post(runtime.url(stage, job) + "/check")
        assert again.json() == response.json()
        assert {role: (runtime.dispatch_root(role) / "inflight.json").read_bytes() for role in leases} == leases
        assert snapshot_database(runtime.store) == before
        assert snapshot_files(job_files(runtime, job)) == frozen
    assert restarted.status(job)["state"] == "completed"
    assert len(runtime.calls) == 3  # Initial text, newer text, other-role image only.


@pytest.mark.parametrize("stage", METHODS)
@pytest.mark.parametrize("defect", ["absent", "partial", "tampered"])
def test_missing_or_invalid_terminal_delivery_holds_all_stage_reservations(runtime, stage, defect):
    _candidate, request = dispatched(runtime, stage)
    job = request.job_id
    if defect != "absent":
        delivery(runtime.store, request)
        root = job_files(runtime, job) / "delivery"
        if defect == "partial":
            (root / "completion.json").unlink()
        else:
            filename = json.loads((root / "completion.json").read_text())["candidate"]["filename"]
            (root / filename).write_text('{"tampered":true}')
    cancel(runtime.store, stage, job)
    before = snapshot_database(runtime.store)
    frozen = snapshot_files(job_files(runtime, job))
    dispatch_before = snapshot_files(runtime.dispatch_root())
    with runtime.client() as client:
        response = client.post(runtime.url(stage, job) + "/check")
        if defect == "tampered":
            assert response.status_code >= 400
        else:
            assert response.json()["state"] == "queued"
    assert runtime.registry.view()["busy"]
    assert snapshot_database(runtime.store) == before
    assert snapshot_files(job_files(runtime, job)) == frozen
    assert snapshot_files(runtime.dispatch_root()) == dispatch_before
    assert len(runtime.calls) == 1


@pytest.mark.parametrize("stage", METHODS)
def test_cancelled_unknown_dispatch_resolves_only_from_valid_terminal_proof(runtime, stage):
    _candidate, request = dispatched(runtime, stage)
    job = request.job_id
    receipt = runtime.dispatch_root() / job / "receipt.json"
    value = json.loads(receipt.read_text())
    value["state"] = "outcome_unknown"
    receipt.write_text(json.dumps(value))
    cancel(runtime.store, stage, job)
    with runtime.client() as client:
        assert client.post(runtime.url(stage, job) + "/check").json()["state"] == "outcome_unknown"
        assert runtime.registry.view()["busy"]
        delivery(runtime.store, request)
        assert client.post(runtime.url(stage, job) + "/check").json()["candidateStatus"] == "discarded"
    assert not runtime.registry.view()["busy"]
    assert len(runtime.calls) == 1


@pytest.mark.parametrize("defect", [
    "request-project", "request-stage", "request-job", "missing-pin", "pin-hash",
    "context-project", "context-stage", "context-missing", "receipt-job", "receipt-task",
    "receipt-missing", "receipt-malformed", "lease-job", "lease-task", "duplicate-root",
])
def test_terminal_identity_and_pin_failures_never_release_or_relabel(runtime, defect):
    stage = "script"
    _candidate, request = dispatched(runtime, stage)
    job = request.job_id
    delivery(runtime.store, request)
    cancel(runtime.store, stage, job)
    root = runtime.dispatch_root()
    receipt = root / job / "receipt.json"
    if defect.startswith("request-") or defect in {"missing-pin", "pin-hash"}:
        with runtime.store.repository._lifecycle_write() as session:
            if defect.startswith("request-"):
                row = session.get(CANDIDATE_ROWS[stage], job)
                key = {"request-project": "projectId", "request-stage": "stage", "request-job": "jobId"}[defect]
                row.request = row.request | {key: "art" if key == "stage" else new_job()}
            else:
                pin = session.get(CreativeHandoffExecutionPinRow, job)
                if defect == "missing-pin":
                    session.delete(pin)
                else:
                    pin.request_hash = "0" * 64
    elif defect.startswith("context-") or defect == "duplicate-root":
        data = json.loads(runtime.registry.path.read_text())
        if defect == "duplicate-root":
            data["roots"][str(uuid4())] = str(root)
        elif defect == "context-missing":
            del data["jobs"][job]
        else:
            key = "projectId" if defect == "context-project" else "stage"
            data["jobs"][job][key] = "foreign"
        runtime.registry.path.write_text(json.dumps(data))
    elif defect.startswith("lease-"):
        lease = {"jobId": job, "taskId": runtime.settings.text.task_id}
        lease["jobId" if defect == "lease-job" else "taskId"] = new_job() if defect == "lease-job" else str(uuid4())
        (root / "inflight.json").write_text(json.dumps(lease))
    elif defect == "receipt-missing":
        receipt.unlink()
    elif defect == "receipt-malformed":
        receipt.write_text("[]")
    else:
        value = json.loads(receipt.read_text())
        value["jobId" if defect == "receipt-job" else "taskId"] = new_job() if defect == "receipt-job" else str(uuid4())
        receipt.write_text(json.dumps(value))
    before = snapshot_database(runtime.store)
    frozen = snapshot_files(job_files(runtime, job))
    dispatch_before = snapshot_files(root)
    with runtime.client() as client:
        assert client.post(runtime.url(stage, job) + "/check").status_code >= 400
    assert snapshot_database(runtime.store) == before
    assert snapshot_files(job_files(runtime, job)) == frozen
    assert snapshot_files(root) == dispatch_before
    assert (root / "inflight.json").exists()
    assert len(runtime.calls) == 1


def test_foreign_route_identity_cannot_reconcile_a_valid_receipt(runtime):
    _candidate, request = dispatched(runtime, "script")
    delivery(runtime.store, request)
    cancel(runtime.store, "script", request.job_id)
    other = runtime.storage.projects.create(FIXED_CHINESE_BRIEF)
    other_id = other.manifest.project_id
    other.close()
    before = snapshot_files(runtime.dispatch_root())
    with runtime.client() as client:
        assert client.post(runtime.url("script", request.job_id, other_id) + "/check").status_code >= 400
        assert client.post(runtime.url("art", request.job_id) + "/check").status_code >= 400
    assert snapshot_files(runtime.dispatch_root()) == before
    assert runtime.registry.view()["busy"]


def test_declined_exact_owner_release_does_not_mark_receipt_completed(runtime, monkeypatch):
    _candidate, request = dispatched(runtime, "script")
    delivery(runtime.store, request)
    cancel(runtime.store, "script", request.job_id)
    before = snapshot_files(runtime.dispatch_root())
    monkeypatch.setattr(NativeCodexImageDispatcher, "complete", lambda *_args: None)
    with runtime.client() as client:
        assert client.post(runtime.url("script", request.job_id) + "/check").status_code >= 400
    assert snapshot_files(runtime.dispatch_root()) == before
    assert runtime.registry.status(request.job_id)["state"] == "queued"


def test_current_invalid_script_retains_reservation(runtime):
    _candidate, request = dispatched(runtime, "script")
    delivery(runtime.store, request)
    before = snapshot_files(runtime.dispatch_root())
    frozen = snapshot_files(job_files(runtime, request.job_id))
    with runtime.client() as client:
        assert client.post(runtime.url("script", request.job_id) + "/check").status_code >= 400
    assert runtime.store.script_state().candidate.status == "prepared"
    assert runtime.registry.view()["busy"]
    assert snapshot_files(runtime.dispatch_root()) == before
    assert snapshot_files(job_files(runtime, request.job_id)) == frozen


@pytest.mark.parametrize("defect", ["manifest-job", "manifest-stage", "manifest-request", "provenance", "package"])
def test_terminal_exchange_identity_and_provenance_failures_hold_reservation(runtime, defect):
    _candidate, request = dispatched(runtime, "script")
    delivery(runtime.store, request)
    cancel(runtime.store, "script", request.job_id)
    files = job_files(runtime, request.job_id)
    if defect == "package":
        (files / "package" / "COPY_ASSIGNMENT.txt").write_text("altered frozen instructions")
    else:
        manifest = files / "delivery" / "completion.json"
        value = json.loads(manifest.read_text())
        if defect == "provenance":
            value["executorProvenance"]["skillHash"] = "0" * 64
        else:
            key = {"manifest-job": "jobId", "manifest-stage": "stage", "manifest-request": "requestHash"}[defect]
            value[key] = {"jobId": new_job(), "stage": "art", "requestHash": "0" * 64}[key]
        manifest.write_text(json.dumps(value))
    before = snapshot_database(runtime.store)
    frozen = snapshot_files(files)
    dispatch_before = snapshot_files(runtime.dispatch_root())
    with runtime.client() as client:
        assert client.post(runtime.url("script", request.job_id) + "/check").status_code >= 400
    assert snapshot_database(runtime.store) == before
    assert snapshot_files(files) == frozen
    assert snapshot_files(runtime.dispatch_root()) == dispatch_before
    assert runtime.registry.view()["busy"]
    assert len(runtime.calls) == 1


def test_valid_terminal_proof_finishes_receipt_after_crash_between_unlink_and_tombstone(runtime):
    _candidate, request = dispatched(runtime, "script")
    delivery(runtime.store, request)
    cancel(runtime.store, "script", request.job_id)
    (runtime.dispatch_root() / "inflight.json").unlink()
    before = snapshot_database(runtime.store)
    frozen = snapshot_files(job_files(runtime, request.job_id))
    with runtime.client() as client:
        assert client.post(runtime.url("script", request.job_id) + "/check").json()["candidateStatus"] == "discarded"
    assert runtime.registry.status(request.job_id)["state"] == "completed"
    assert snapshot_database(runtime.store) == before
    assert snapshot_files(job_files(runtime, request.job_id)) == frozen
    assert len(runtime.calls) == 1


@pytest.mark.parametrize("stage", ["outline", "characters", "art", "script"])
@pytest.mark.parametrize("tampered", [False, True])
def test_ready_replacement_reconciles_only_valid_proof_without_changing_new_head(runtime, stage, tampered):
    _candidate, request = dispatched(runtime, stage)
    ready_delivery(runtime.store, request)
    route_stage = {"outline": "source-outline", "characters": "cast", "art": "art", "script": "script"}[stage]
    with runtime.client() as client:
        refresh = client.post(f"/api/v2/projects/{runtime.project_id}/{route_stage}/candidates/{request.job_id}/refresh")
        assert refresh.status_code == 200, refresh.text
        assert refresh.json()["status"] == "ready"
    assert runtime.registry.view()["busy"]
    next_candidate, _ = prepare(runtime.store, stage)
    if tampered:
        (job_files(runtime, request.job_id) / "delivery" / "report.html").write_text("altered report")
    before = snapshot_database(runtime.store)
    frozen = snapshot_files(job_files(runtime, request.job_id))
    dispatch_before = snapshot_files(runtime.dispatch_root())
    with runtime.client() as client:
        result = client.post(runtime.url(stage, request.job_id) + "/check")
        if tampered:
            assert result.status_code >= 400
            assert snapshot_files(runtime.dispatch_root()) == dispatch_before
            assert runtime.registry.view()["busy"]
        else:
            assert result.json() == {"state": "completed", "candidateStatus": "discarded"}
            assert not runtime.registry.view()["busy"]
        assert snapshot_database(runtime.store) == before
        assert snapshot_files(job_files(runtime, request.job_id)) == frozen
        assert len(runtime.calls) == 1
        if not tampered:
            assert client.post(runtime.url(stage, next_candidate.job_id) + "/send").status_code == 200
            lease = (runtime.dispatch_root() / "inflight.json").read_bytes()
            assert client.post(runtime.url(stage, request.job_id) + "/check").json() == result.json()
            assert (runtime.dispatch_root() / "inflight.json").read_bytes() == lease
            assert snapshot_database(runtime.store) == before
            assert len(runtime.calls) == 2
