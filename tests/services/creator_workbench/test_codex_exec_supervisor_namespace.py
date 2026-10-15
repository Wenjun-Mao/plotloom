"""Synthetic external execution; real supervisor, source closure and SQLite."""
import sqlite3
import stat
from contextlib import closing
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest
from codex_exec_supervisor import CodexExecSupervisor
from codex_exec_supervisor_errors import CodexExecSupervisorError
from codex_exec_supervisor_test_support import _prepared_text_job

from plotloom.codex_exec_contracts import transition_exec_attempt
from plotloom.codex_exec_namespace_contracts import CodexExecNamespaceBinding
from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits
from plotloom.codex_exec_profile import build_codex_exec_profile


def _path_identity(path):
    path = path.resolve(strict=True)
    metadata = path.stat()
    return {"path": str(path), "device": metadata.st_dev, "inode": metadata.st_ino,
        "uid": metadata.st_uid, "mode": stat.S_IMODE(metadata.st_mode)}


@pytest.fixture
def bounded(supervisor, tmp_path):
    _exchange, _request, _pin, _job_root, original, _profile = _prepared_text_job(supervisor, tmp_path)
    limits = CodexExecPoolLimits(maxProcesses=1, maxTextProcesses=1, maxImageProcesses=1, maxQueuedJobs=1)
    profile = build_codex_exec_profile(supervisor.executable, source_root=supervisor.source_root, pool_limits=limits)
    application = tmp_path / "application"
    application.chmod(0o700)
    supervisor.outputs_root.chmod(0o700)
    private = tmp_path / "bounded-private"
    private.mkdir(mode=0o700)
    empty = CodexExecSupervisor(supervisor.executable, source_root=supervisor.source_root,
        outputs_root=supervisor.outputs_root, private_root=private, pool_limits=limits)
    reserved = original.model_copy(update={"state": "reserved", "profile_hash": profile.profile_hash})
    binding = CodexExecNamespaceBinding(version="plotloom.exec-one-attempt.v1", namespaceId=uuid4(),
        applicationRoot=_path_identity(application), outputsRoot=_path_identity(supervisor.outputs_root),
        privateRoot=_path_identity(private), sourceRoot=_path_identity(supervisor.source_root),
        database=_path_identity(empty.database),
        executable=_path_identity(supervisor.executable) | {"sha256": sha256(supervisor.executable.read_bytes()).hexdigest(),
            "size": supervisor.executable.stat().st_size}, profile=profile, limits=limits, attempt=reserved)
    raw = binding.model_dump_json(by_alias=True).encode()
    binding_file = private / "namespace-binding.json"
    binding_file.write_bytes(raw)
    binding_file.chmod(0o600)
    pin = sha256(raw).hexdigest()
    kwargs = {"source_root": supervisor.source_root, "outputs_root": supervisor.outputs_root,
        "private_root": private, "namespace_binding_sha256": pin}
    host = CodexExecSupervisor(supervisor.executable, **kwargs)
    return SimpleNamespace(host=host, attempt=transition_exec_attempt(reserved, state="spawn_intent"),
        reserved=reserved, kwargs=kwargs, binding_file=binding_file, pin=pin, unbound=empty)


def _admit_without_external_worker(case, monkeypatch):
    starts = []
    monkeypatch.setattr(case.host, "_start_worker", starts.append)
    status = case.host.admit(case.attempt)
    assert status.attempt.attempt_id == case.attempt.attempt_id
    assert starts == [case.attempt.attempt_id]
    return starts


def test_bound_admission_and_restart_preserve_exact_identity(bounded, monkeypatch):
    starts = _admit_without_external_worker(bounded, monkeypatch)
    other = CodexExecSupervisor(bounded.host.executable, **bounded.kwargs)
    monkeypatch.setattr(other, "_start_worker", starts.append)
    assert other.admit(bounded.attempt).attempt.attempt_id == bounded.attempt.attempt_id
    with closing(other._connect()) as connection:
        assert connection.execute("SELECT count(*) FROM exec_attempts").fetchone()[0] == 1
        assert connection.execute("SELECT binding_sha256 FROM exec_namespace_configuration").fetchone()[0] == bounded.pin


@pytest.mark.parametrize("entry", ["admit", "status", "worker", "register"])
def test_foreign_requested_identity_refuses_before_start(bounded, monkeypatch, entry):
    starts = []
    monkeypatch.setattr(bounded.host, "_start_worker_reaper", lambda *_args: pytest.fail("foreign worker started"))
    foreign = bounded.attempt.model_copy(update={"attempt_id": uuid4()})
    with pytest.raises(CodexExecSupervisorError, match="foreign"):
        if entry == "admit":
            bounded.host.admit(foreign)
        elif entry == "status":
            bounded.host.status(foreign.attempt_id)
        elif entry == "worker":
            bounded.host.run_worker(foreign.attempt_id)
        else:
            bounded.host._register_worker(foreign.attempt_id)
    assert not starts


@pytest.mark.parametrize("control", ["cancel", "suspend", "resume"])
@pytest.mark.parametrize("field", ["attempt_id", "project_id"])
def test_foreign_control_cannot_insert_or_change_namespace_rows(bounded, control, field):
    before = bounded.host.database.read_bytes()
    foreign = bounded.attempt.model_copy(update={field: uuid4()})
    with pytest.raises(CodexExecSupervisorError, match="foreign"):
        getattr(bounded.host, control)(foreign)
    assert bounded.host.database.read_bytes() == before


def test_exact_pre_admission_cancel_tombstone_survives_reconstruction(bounded, monkeypatch):
    cancelled = bounded.host.cancel(bounded.reserved)
    assert cancelled.state == "settled" and cancelled.attempt.terminal_result == "not_started"
    other = CodexExecSupervisor(bounded.host.executable, **bounded.kwargs)
    monkeypatch.setattr(other, "_start_worker", lambda _value: pytest.fail("cancelled attempt started"))
    assert other.admit(bounded.attempt) == cancelled
    assert other.status(bounded.attempt.attempt_id) == cancelled


def test_missing_running_cancel_retains_unknown_capacity_through_status_and_restart(bounded, monkeypatch):
    running = transition_exec_attempt(bounded.attempt, state="running", process_id=43210,
        process_group_id=43210, process_birth_identity="synthetic-missing-host")
    unknown = bounded.host.cancel(running)
    assert unknown.state == "outcome_unknown"
    other = CodexExecSupervisor(bounded.host.executable, **bounded.kwargs)
    monkeypatch.setattr(other, "_start_worker", lambda _value: pytest.fail("unknown attempt restarted"))
    assert other.status(running.attempt_id) == unknown
    assert other.admit(bounded.attempt) == unknown
    assert other._drain_queue() is None
    with closing(other._connect()) as connection:
        assert other._capacity_counts(connection) == {"text": 1, "image": 0}


@pytest.mark.parametrize("drift", ["evidence", "paths", "capacity"])
def test_cancel_tombstone_drift_cannot_relax_namespace(bounded, drift):
    bounded.host.cancel(bounded.reserved)
    with closing(sqlite3.connect(bounded.host.database)) as connection:
        if drift == "evidence":
            connection.execute("UPDATE exec_attempts SET status_json=json_set(status_json,'$.evidenceHash',?)", ("a" * 64,))
        elif drift == "paths":
            connection.execute("UPDATE exec_attempts SET private_dir='foreign'")
        else:
            connection.execute("INSERT INTO exec_slot VALUES(?,'text')", (str(bounded.attempt.attempt_id),))
        connection.commit()
    before = bounded.host.database.read_bytes()
    with pytest.raises(CodexExecSupervisorError):
        CodexExecSupervisor(bounded.host.executable, **bounded.kwargs)
    assert bounded.host.database.read_bytes() == before


def test_explicit_suspend_and_resume_only_touch_the_bound_identity(bounded, monkeypatch):
    starts = []
    monkeypatch.setattr(bounded.host, "_start_worker", starts.append)
    parked = bounded.host.suspend(bounded.attempt)
    assert parked.state == "queued" and parked.dispatch_enabled is False
    assert not starts
    assert bounded.host.status(bounded.attempt.attempt_id).state == "queued"
    assert not starts
    resumed = bounded.host.resume(bounded.attempt)
    assert resumed.state == "spawn_intent" and starts == [bounded.attempt.attempt_id]


def test_project_unknown_snapshot_fences_actual_unstarted_host_without_re_admission(bounded, monkeypatch):
    _admit_without_external_worker(bounded, monkeypatch)
    project_unknown = transition_exec_attempt(bounded.attempt, state="outcome_unknown")
    for name in ("admit", "status", "resume", "_start_worker", "_refresh_active_attempt", "_drain_queue"):
        monkeypatch.setattr(bounded.host, name, lambda *_args: pytest.fail("suspend dispatched or polled"))
    status = bounded.host.suspend(project_unknown)
    assert status.state == "queued" and status.dispatch_enabled is False
    assert project_unknown.state == "outcome_unknown"
    with closing(bounded.host._connect()) as connection:
        rows = connection.execute("SELECT attempt_json,worker_pid,receipt_json FROM exec_attempts").fetchall()
        assert len(rows) == 1 and rows[0]["attempt_json"] == bounded.attempt.model_dump_json(by_alias=True)
        assert rows[0]["worker_pid"] is None and rows[0]["receipt_json"] is None
        assert connection.execute("SELECT enabled FROM exec_queue").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM exec_slot").fetchone()[0] == 0


@pytest.mark.parametrize("state", ["running", "validating", "outcome_unknown"])
def test_project_unknown_suspend_preserves_actual_active_host_capacity_and_validation(bounded, monkeypatch, state):
    _admit_without_external_worker(bounded, monkeypatch)
    running = transition_exec_attempt(bounded.attempt, state="running", process_id=54321,
        process_group_id=54321, process_birth_identity="synthetic-process-not-probed", session_id=uuid4())
    bounded.host._store(running)
    active = running if state == "running" else transition_exec_attempt(running, state=state)
    if active != running:
        bounded.host._store(active)
    if state == "validating":
        with closing(bounded.host._connect()) as connection:
            connection.execute("INSERT INTO exec_validation_process "
                "VALUES(?,'validate','running',65432,65432,'synthetic-validator-not-probed',0)",
                (str(active.attempt_id),))
            connection.commit()
    def snapshots():
        with closing(bounded.host._connect()) as connection:
            return {table: [tuple(row) for row in connection.execute("SELECT * FROM " + table)]
                for table in ("exec_attempts", "exec_queue", "exec_slot", "exec_validation_process")}
    before = snapshots()
    for name in ("admit", "status", "resume", "_start_worker", "_refresh_active_attempt", "_drain_queue"):
        monkeypatch.setattr(bounded.host, name, lambda *_args: pytest.fail("suspend dispatched or polled"))
    project_unknown = transition_exec_attempt(bounded.attempt, state="outcome_unknown")
    status = bounded.host.suspend(project_unknown)
    assert status.attempt == active and status.receipt is None
    assert snapshots() == before and len(before["exec_slot"]) == 1


def test_missing_host_for_project_unknown_is_not_found_without_inventing_a_row(bounded):
    project_unknown = transition_exec_attempt(bounded.attempt, state="outcome_unknown")
    status = bounded.host.suspend(project_unknown)
    assert status.state == "not_found" and status.attempt is None
    with closing(bounded.host._connect()) as connection:
        assert all(connection.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
            for table in ("exec_attempts", "exec_queue", "exec_slot", "exec_validation_process"))


@pytest.mark.parametrize("table", ["exec_attempts", "exec_queue", "exec_slot", "exec_validation_process"])
def test_foreign_ledger_rows_refuse_status_drain_and_reconstruction_without_mutation(bounded, monkeypatch, table):
    _admit_without_external_worker(bounded, monkeypatch)
    with closing(sqlite3.connect(bounded.host.database)) as connection:
        foreign = str(uuid4())
        if table == "exec_attempts":
            connection.execute("UPDATE exec_attempts SET project_id=?", (foreign,))
        elif table == "exec_queue":
            connection.execute("INSERT INTO exec_queue(attempt_id,enabled) VALUES(?,1)", (foreign,))
        elif table == "exec_slot":
            connection.execute("INSERT INTO exec_slot VALUES(?,'text')", (foreign,))
        else:
            connection.execute("INSERT INTO exec_validation_process(attempt_id,step_id,spawn_state,updated_at) VALUES(?,'fixture','spawn_intent',0)", (foreign,))
        connection.commit()
    before = bounded.host.database.read_bytes()
    with pytest.raises(CodexExecSupervisorError, match="foreign"):
        bounded.host.status(bounded.attempt.attempt_id)
    with pytest.raises(CodexExecSupervisorError, match="foreign"):
        bounded.host._drain_queue()
    with pytest.raises(CodexExecSupervisorError, match="foreign"):
        CodexExecSupervisor(bounded.host.executable, **bounded.kwargs)
    assert bounded.host.database.read_bytes() == before


@pytest.mark.parametrize("loss", ["argument", "deleted_file", "changed_file", "database_replaced", "root_mode"])
def test_binding_loss_and_physical_drift_refuse_before_reconstruction_or_start(bounded, monkeypatch, loss):
    _admit_without_external_worker(bounded, monkeypatch)
    kwargs = bounded.kwargs.copy()
    if loss == "argument":
        kwargs.pop("namespace_binding_sha256")
    elif loss == "deleted_file":
        bounded.binding_file.unlink()
    elif loss == "changed_file":
        bounded.binding_file.write_bytes(b"{}")
    elif loss == "database_replaced":
        database = bounded.host.database
        database.rename(database.with_suffix(".retained"))
        database.write_bytes(b"")
        database.chmod(0o600)
    else:
        bounded.host.outputs_root.chmod(0o750)
    with pytest.raises((CodexExecSupervisorError, OSError, sqlite3.DatabaseError)):
        CodexExecSupervisor(bounded.host.executable, **kwargs)
    if loss != "argument":
        with pytest.raises((CodexExecSupervisorError, OSError, sqlite3.DatabaseError)):
            bounded.host._drain_queue()


def test_binding_and_pin_cannot_both_be_dropped_after_restart(bounded):
    bounded.binding_file.unlink()
    kwargs = bounded.kwargs | {"namespace_binding_sha256": None}
    before = bounded.host.database.read_bytes()
    with pytest.raises(CodexExecSupervisorError, match="unbound"):
        CodexExecSupervisor(bounded.host.executable, **kwargs)
    with pytest.raises(CodexExecSupervisorError, match="unbound"):
        bounded.unbound.status(bounded.attempt.attempt_id)
    assert bounded.host.database.read_bytes() == before


def test_foreign_queue_inserted_in_grant_transaction_refuses_before_grant(bounded, monkeypatch):
    _admit_without_external_worker(bounded, monkeypatch)
    with closing(bounded.host._connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("PRAGMA defer_foreign_keys=ON")
        connection.execute("INSERT INTO exec_queue(attempt_id,enabled) VALUES(?,1)", (str(uuid4()),))
        with pytest.raises(CodexExecSupervisorError, match="foreign"):
            bounded.host._grant_one_in_transaction(connection)
        connection.rollback()


def test_unknown_exact_attempt_keeps_capacity_and_no_worker_restart(bounded, monkeypatch):
    starts = _admit_without_external_worker(bounded, monkeypatch)
    unknown = transition_exec_attempt(bounded.attempt, state="outcome_unknown")
    bounded.host._store(unknown)
    assert bounded.host.status(unknown.attempt_id).state == "outcome_unknown"
    assert bounded.host._drain_queue() is None
    with closing(bounded.host._connect()) as connection:
        assert bounded.host._capacity_counts(connection) == {"text": 1, "image": 0}
    assert starts == [unknown.attempt_id]


def test_worker_argv_transports_binding_and_real_parser_reconstructs_it(bounded, monkeypatch):
    import codex_exec_supervisor_worker as worker
    import codex_exec_supervisor_worker_ownership as ownership
    _admit_without_external_worker(bounded, monkeypatch)
    captured = []
    real_popen = ownership.subprocess.Popen
    # External helper process creation alone is faked. Execute its real parser
    # and constructor below, stopping before process registration/execution.
    def popen(command, **_kwargs):
        if command[1:] == ["--version"]:
            return real_popen(command, **_kwargs)
        captured.append(command)
        raise OSError("synthetic helper creation failure")
    with monkeypatch.context() as external:
        external.setattr(ownership.subprocess, "Popen", popen)
        external.setattr(bounded.host, "_start_worker", CodexExecSupervisor._start_worker.__get__(bounded.host))
        with pytest.raises(OSError, match="synthetic"):
            bounded.host._start_worker(bounded.attempt.attempt_id)
    command = captured[0]
    assert command[-2:] == ["--namespace-binding-sha256", bounded.pin]
    reconstructed = []
    with monkeypatch.context() as execution:
        execution.setattr(CodexExecSupervisor, "run_worker", lambda host, identity:
            reconstructed.append((host._namespace_sha256, identity)))
        worker.main(command[2:])
    assert reconstructed == [(bounded.pin, bounded.attempt.attempt_id)]
    with pytest.raises(CodexExecSupervisorError, match="pin"):
        worker.main(command[2:-2])


def test_source_profile_drift_refuses_before_mutating_ledger(bounded, monkeypatch):
    _admit_without_external_worker(bounded, monkeypatch)
    # Change an owned file only in the isolated copied test checkout.
    owned = bounded.host.source_root / "src/plotloom/autopilot_exec_staged.py"
    original = owned.read_bytes()
    try:
        owned.write_bytes(original + b"\n# synthetic source drift\n")
        before = bounded.host.database.read_bytes()
        with pytest.raises(CodexExecSupervisorError, match="profile"):
            CodexExecSupervisor(bounded.host.executable, **bounded.kwargs)
        with pytest.raises(CodexExecSupervisorError, match="profile"):
            bounded.host.status(bounded.attempt.attempt_id)
        assert bounded.host.database.read_bytes() == before
    finally:
        owned.write_bytes(original)
