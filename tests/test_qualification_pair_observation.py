"""Migrated campaign capture cases; no CLI, provider, auth or HTTP runtime."""
from contextlib import closing,contextmanager
from dataclasses import asdict
import json
import os
import sqlite3
from pathlib import Path
from time import monotonic_ns
from types import SimpleNamespace as Namespace
import pytest
from plotloom.codex_exec_contracts import CodexExecHostStatus,transition_exec_attempt
from plotloom.image_commands import IMAGE_METHODS
from plotloom.specialist_settings import SpecialistRegistry
from tests.autopilot_controller_fixtures import environment
from tests.autopilot_image_fixtures import handoff_image_environment
from tests.qualification_pair_test_support import pair_controls  # noqa: F401

@pytest.fixture(autouse=True)
def bind_current_controls(pair_controls,monkeypatch):
    for name,value in pair_controls.exports.items():
        monkeypatch.setitem(globals(),name,value)

def runtime_for(registry, storage=None, host=None):
    return Namespace(app=Namespace(state=Namespace(specialists=registry,
        project_folder_storage=storage)), bridge=Namespace(exec_supervisor=lambda: host))


def current(storage, project):
    with closing(storage.projects.open(project)) as store:
        return store.repository.autopilot.current(project)


def capture_for(tmp_path, registry, storage=None, host=None, **options):
    work = tmp_path / "evidence"
    work.mkdir()
    events = []
    capture = CampaignObservation(runtime_for(registry, storage, host), work,
        lambda event, **facts: events.append({"event": event, **facts}),
        prepared_package_snapshot, image_owners=IMAGE_METHODS, **options)
    return capture, events


def records(capture):
    return [json.loads(line) for line in (capture.work / "rpc_observations.jsonl").read_text().splitlines()]


def test_actual_text_owner_freezes_validation_plan_before_its_original_admission(tmp_path, monkeypatch):
    storage, registry, service, run, text_calls = environment(tmp_path / "project", monkeypatch)
    capture, events = capture_for(tmp_path, registry, storage)
    original_admit = registry.codex_exec_admit
    def checked_admit(value):
        assert any(event["jobId"] == value.job_id and len(event["frozenIdentity"]) == 11 for event in events)
        return original_admit(value)
    monkeypatch.setattr(registry, "codex_exec_admit", checked_admit)
    try:
        assert service.acquire_controller()
        with capture.installed():
            for _ in range(12):
                view = current(storage, run.project_id)
                capture.freeze_prepared(run.project_id,
                    {"run": view.model_dump(mode="json", by_alias=True)}, "primary")
                service.step(run.project_id)
                if capture.records_emitted:
                    break
            else:
                pytest.fail("real text owner never issued its original admission")
        rows = records(capture)
        assert len(rows) == 1 and rows[0]["operation"] == "admit"
        proof = events[0]["frozenIdentity"]
        assert len(proof) == 11 and "attempt_id" not in proof
        assert proof["domain"] == "text" and proof["validation_plan_hash"]
        identity = rows[0]["attemptIdentity"]
        assert len(identity) == 12 and all(identity[key] == value for key, value in proof.items())
        assert text_calls == [identity["job_id"]]
        assert capture.require_complete()["recordsEmitted"] == 1
    finally:
        service.close()


def test_actual_image_owner_null_blocker_deferral_then_same_original_admission(tmp_path, monkeypatch):
    storage, registry, service, run, image_calls, _texts = handoff_image_environment(
        tmp_path / "project", monkeypatch, auto_deliver=False, cuts_per_scene=2)
    host = registry._codex_exec_test_host
    original_admit = registry.codex_exec_admit
    admitted = []
    deferred = None
    def defer_once(value):
        nonlocal deferred
        assert any(event["jobId"] == value.job_id and len(event["frozenIdentity"]) == 11 for event in events)
        admitted.append(value)
        if deferred is None:
            deferred = value
            return CodexExecHostStatus(state="not_found", capacityDeferred=True)
        return original_admit(value)
    monkeypatch.setattr(registry, "codex_exec_admit", defer_once)
    capture, events = capture_for(tmp_path, registry, storage)
    try:
        assert service.acquire_controller()
        with capture.installed():
            for _ in range(40):
                view = current(storage, run.project_id)
                capture.freeze_prepared(run.project_id,
                    {"run": view.model_dump(mode="json", by_alias=True)}, "primary")
                service.step(run.project_id)
                if deferred is not None:
                    break
            else:
                pytest.fail("real image owner never issued its original admission")
            waiting = current(storage, run.project_id)
            checkpoint = next(item for item in waiting.checkpoints if item["operationKey"] == deferred.operation_key)
            assert waiting.state == "running" and waiting.blocker is None
            assert not image_calls and len(admitted) == 1
            with closing(storage.projects.open(run.project_id)) as store:
                project, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, deferred.operation_key)
            digest, _request = prepared_package_snapshot(capture.runtime, run.project_id, checkpoint)
            assert capture.classify(project, checkpoint,
                LedgerSample(monotonic_ns(), monotonic_ns(), None), digest) == "known_capacity_wait"
            service.step(run.project_id)  # Only production issues its status + same-ID admit.
            assert admitted == [deferred, deferred] and image_calls == [deferred.job_id]
            status = host.statuses[str(deferred.attempt_id)]
            project = current(storage, run.project_id)
            checkpoint = next(item for item in project.checkpoints if item["operationKey"] == deferred.operation_key)
            with closing(storage.projects.open(run.project_id)) as store:
                project_attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, deferred.operation_key)
            sample = LedgerSample(monotonic_ns(), monotonic_ns(),
                LedgerRow(deferred, status.attempt, receipt=status.receipt))
            assert capture.classify(project_attempt, checkpoint, sample, digest) == "host_running"
        rows = records(capture)
        assert [row["operation"] for row in rows] == ["admit", "status", "admit"]
        assert [row["sequence"] for row in rows] == [1, 2, 3]
        assert rows[0]["status"]["capacityDeferred"] is True
        assert len(rows[0]["attemptIdentity"]) == 12 and len(events[0]["frozenIdentity"]) == 11
    finally:
        service.close()


def test_all_five_real_registry_methods_keep_exact_arguments_and_typed_returns(tmp_path, monkeypatch):
    registry = SpecialistRegistry(tmp_path / "registry", executable="never-called")
    value, calls = attempt(), []
    waiting = transition_exec_attempt(value, state="queued")
    settled = transition_exec_attempt(value, state="settled", terminal_result="not_started",
        remote_tool_state="not_applicable", evidence_hash="f" * 64, image_budget_state="released")
    replies = {"exec-admit": CodexExecHostStatus(state="not_found", capacityDeferred=True),
        "exec-status": CodexExecHostStatus(state="not_found"),
        "exec-suspend": CodexExecHostStatus(state="queued", attempt=waiting, dispatchEnabled=False),
        "exec-resume": CodexExecHostStatus(state="queued", attempt=waiting, dispatchEnabled=True),
        "exec-cancel": CodexExecHostStatus(state="settled", attempt=settled)}
    def request(command, *arguments):
        calls.append((command, arguments))
        return replies[command]
    monkeypatch.setattr(registry, "_codex_exec_request", request)
    capture, _events = capture_for(tmp_path, registry)
    capture.observer.freeze_job(frozen(value))
    with capture.installed():
        for operation in ("admit", "status", "suspend", "resume", "cancel"):
            argument = value.attempt_id if operation == "status" else value
            assert getattr(registry, "codex_exec_" + operation)(argument) is replies["exec-" + operation]
    assert len(calls) == 5
    for command, arguments in calls:
        if command == "exec-status":
            assert arguments == ("--attempt-id", str(value.attempt_id))
        else:
            assert arguments[0] == "--attempt-json"
            assert json.loads(arguments[1]) == value.model_dump(mode="json", by_alias=True)
    assert capture.require_complete()["recordsEmitted"] == 5
    assert "codex_exec_admit" not in registry.__dict__


def test_stream_hook_never_copies_history_and_reports_truncation(tmp_path, monkeypatch):
    registry = SpecialistRegistry(tmp_path / "registry", executable="never-called")
    value = attempt()
    reply = CodexExecHostStatus(state="not_found", capacityDeferred=True)
    monkeypatch.setattr(registry, "_codex_exec_request", lambda *_args: reply)
    def no_history(_self):
        pytest.fail("streaming capture must not request the complete record history")
    monkeypatch.setattr(AdmissionObserver, "records", property(no_history))
    capture, _events = capture_for(tmp_path, registry, max_records=2)
    capture.observer.freeze_job(frozen(value))
    with capture.installed():
        assert registry.codex_exec_admit(value) is reply
        assert registry.codex_exec_status(value.attempt_id) is reply
        assert registry.codex_exec_suspend(value) is reply  # Cleanup delegates beyond the bound.
        with pytest.raises(ObservationError):
            registry.codex_exec_resume(value)
    assert [row["sequence"] for row in records(capture)] == [1, 2, 3]
    assert capture.summary()["discardedRecords"] == 1
    with pytest.raises(ObservationError, match="incomplete"):
        capture.require_complete()


def test_persistence_uncertainty_blocks_new_calls_but_preserves_cleanup_returns(tmp_path, monkeypatch):
    registry = SpecialistRegistry(tmp_path / "registry", executable="never-called")
    value, calls = attempt(), []
    reply = CodexExecHostStatus(state="not_found", capacityDeferred=True)
    def request(*arguments):
        calls.append(arguments)
        return reply
    monkeypatch.setattr(registry, "_codex_exec_request", request)
    capture, _events = capture_for(tmp_path, registry)
    capture.observer.freeze_job(frozen(value))
    def fail_fsync(_descriptor):
        raise OSError("synthetic evidence-write failure")
    monkeypatch.setattr(os, "fsync", fail_fsync)
    with capture.installed():
        assert registry.codex_exec_admit(value) is reply
        assert registry.codex_exec_status(value.attempt_id) is reply
        with pytest.raises(ObservationError, match="persistence failed"):
            registry.codex_exec_admit(value)
    assert len(calls) == 2 and capture.summary()["persistenceFailure"]
    with pytest.raises(ObservationError):
        capture.require_complete()


def test_nested_original_cleanup_streams_each_completion_once_in_completion_order(tmp_path, monkeypatch):
    registry = SpecialistRegistry(tmp_path / "registry", executable="never-called")
    value = attempt()
    status, admit = CodexExecHostStatus(state="not_found"), CodexExecHostStatus(state="not_found", capacityDeferred=True)
    def request(command, *_arguments):
        if command == "exec-admit":
            assert registry.codex_exec_status(value.attempt_id) is status
            return admit
        return status
    monkeypatch.setattr(registry, "_codex_exec_request", request)
    capture, _events = capture_for(tmp_path, registry)
    capture.observer.freeze_job(frozen(value))
    with capture.installed():
        assert registry.codex_exec_admit(value) is admit
    assert [row["sequence"] for row in records(capture)] == [2, 1]
    with pytest.raises(ObservationError, match="no current exact"):
        capture.observer.classify(value, checkpoint_attempt_id=value.attempt_id,
            current_package_hash=value.package_hash,
            sample=LedgerSample(monotonic_ns(), monotonic_ns(), None))


def test_actual_ledger_decoder_and_cleanup_keep_disabled_jobs_parked(tmp_path, monkeypatch):
    complete = successful_text()
    pending = [queued(attempt(project_id=complete.current.project_id, run_id=complete.current.run_id,
        operation_key=f"image:shot-{index}")) for index in range(5)]
    rows = (complete, *pending)
    database = tmp_path / "supervisor.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript("CREATE TABLE exec_attempts(attempt_json,status_json,receipt_json,worker_pid,worker_group_id,worker_birth_identity); CREATE TABLE exec_queue(attempt_id,enabled); CREATE TABLE exec_slot(domain); CREATE TABLE exec_validation_process(process_group_id);")
        for row in rows:
            connection.execute("INSERT INTO exec_attempts VALUES(?,?,?,?,?,?)", (
                row.original.model_dump_json(by_alias=True), row.current.model_dump_json(by_alias=True),
                row.receipt.model_dump_json(by_alias=True) if row.receipt else None,
                row.worker_pid, row.worker_group_id, row.worker_birth_identity))
        connection.executemany("INSERT INTO exec_queue VALUES(?,0)", [(str(row.current.attempt_id),) for row in pending])
    attempts = {row.current.operation_key: row.current if row is complete else row.original for row in rows}
    checkpoints = [{"operationKey": key} for key in attempts]
    view = Namespace(id=complete.current.run_id, state="paused", handoff=None, checkpoints=checkpoints)
    closed = []
    store = Namespace(repository=Namespace(autopilot=Namespace(current=lambda _project: view,
        exec_attempt_evidence_for_operation=lambda _run, operation: (attempts[operation], None))), close=lambda: closed.append(True))
    storage = Namespace(projects=Namespace(inspect=lambda _project, passive: store))
    runtime = runtime_for(None, storage, Namespace(database=database))
    monkeypatch.setattr("campaign_cleanup.group_observation", lambda _group: "absent")
    before = database.read_bytes()
    result, evidence = cleanup_snapshot(runtime, {"primary": str(complete.current.project_id)}, material_qualified=True)
    assert result.outcome == "safe_parked" and result.zero_live_work
    assert not result.all_work_quiescent and not result.complete_success
    assert len(result.parked_attempts) == 5 and all(value is False for value in evidence["queue"].values())
    assert database.read_bytes() == before and closed == [True]


