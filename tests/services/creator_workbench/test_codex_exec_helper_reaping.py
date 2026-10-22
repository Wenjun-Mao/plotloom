"""Parent-owned OS waits never depend on another RPC or settle provider work."""
import json
import os
import subprocess
import sys
import time
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import uuid4

import codex_exec_supervisor_worker_ownership as worker_module
import pytest
from codex_exec_supervisor import CodexExecSupervisor
from codex_exec_supervisor_test_support import (
    _attempt,
    _insert_attempt_row,
    _prepared_text_job,
)
from host_bridge import QueueBridge, handler_for

from plotloom.codex_exec_contracts import transition_exec_attempt


def _until(predicate, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    assert predicate(), "owned helper did not reach the required lifecycle boundary"


def _assert_reaped(worker):
    assert worker.returncode is not None
    with pytest.raises(ChildProcessError):
        os.waitpid(worker.pid, os.WNOHANG)


def _capture_spawned_workers(supervisor, monkeypatch):
    captured = []
    real_start = supervisor._start_worker_reaper
    def start(identity):
        reaper = real_start(identity)
        real_spawned = reaper.spawned
        def spawned(worker):
            if worker is not None:
                captured.append(worker)
            real_spawned(worker)
        monkeypatch.setattr(reaper, "spawned", spawned)
        return reaper
    monkeypatch.setattr(supervisor, "_start_worker_reaper", start)
    return captured


def _cleanup(worker):
    # Test failure cleanup runs only after lifecycle assertions. It must not
    # supply the wait that the autonomous-reaping regression is measuring.
    if worker.poll() is None:
        worker.terminate()
    worker.wait(timeout=5)


def test_fast_child_is_reaped_without_status_or_any_followup_rpc(supervisor):
    identity = uuid4()
    reaper = supervisor._start_worker_reaper(identity)
    worker = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    try:
        with supervisor._guard:
            supervisor._workers[str(identity)] = worker
        reaper.spawned(worker)
        _until(lambda: str(identity) not in supervisor._workers)
        _assert_reaped(worker)
    finally:
        _cleanup(worker)


def test_bridge_close_leaves_owned_child_and_autonomous_waiter_running(supervisor, tmp_path):
    identity = uuid4()
    reaper = supervisor._start_worker_reaper(identity)
    worker = subprocess.Popen([sys.executable, "-c", "import sys;sys.stdin.read()"],
        stdin=subprocess.PIPE, start_new_session=True)
    try:
        with supervisor._guard:
            supervisor._workers[str(identity)] = worker
        reaper.spawned(worker)
        bridge = QueueBridge(supervisor.executable, tmp_path / "settings.json", "fixture-token",
            source_root=supervisor.source_root, outputs_root=supervisor.outputs_root, private_root=supervisor.private_root)
        bridge._exec_supervisor = supervisor
        with ThreadingHTTPServer(("127.0.0.1", 0), handler_for(bridge)) as server:
            thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            thread.start()
            server.shutdown()
            thread.join(timeout=2)
            assert not thread.is_alive()
        assert worker.poll() is None
        assert supervisor._workers[str(identity)] is worker
        worker.stdin.close()
        _until(lambda: str(identity) not in supervisor._workers)
        _assert_reaped(worker)
    finally:
        if worker.stdin is not None and not worker.stdin.closed:
            worker.stdin.close()
        _cleanup(worker)


_SUCCESS_CLI = r'''
import json, os, sys, time
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
if len(sys.argv) > 1 and sys.argv[1] == "sandbox":
    if "render" in sys.argv:
        print("<!doctype html><html><body>fixture renderer</body></html>")
    raise SystemExit(0)
sys.stdin.read()
Path("outline.json").write_text(json.dumps({"source":"The Ferryman","params":{"episodes":1},"episodes":[]}))
session = uuid4()
day = date.today()
root = Path(os.environ["CODEX_HOME"]) / "sessions" / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}"
root.mkdir(parents=True, exist_ok=True)
(root / f"rollout-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}-{session}.jsonl").write_text(json.dumps({"type":"session_meta","payload":{"id":str(session)},"ordinal":0}) + "\n")
for event in ({"type":"thread.started","thread_id":str(session)},{"type":"turn.started"},{"type":"turn.completed"}):
    print(json.dumps(event), flush=True)
'''


@pytest.mark.parametrize("outcome", ["completed", "outcome_unknown"])
def test_real_registered_helper_reaps_without_followup_rpc_and_preserves_outcome(supervisor, tmp_path, monkeypatch, outcome):
    source = _SUCCESS_CLI if outcome == "completed" else "import sys\nsys.stdin.read()\nraise SystemExit(9)\n"
    _exchange, _request, _pin, _root, attempt, _profile = _prepared_text_job(supervisor, tmp_path, fake_cli_source=source)
    captured = _capture_spawned_workers(supervisor, monkeypatch)
    supervisor.admit(attempt)
    assert len(captured) == 1
    worker = captured[0]
    original = supervisor._row(attempt.attempt_id)["attempt_json"]
    try:
        # Direct immutable-ledger observations do not call status/admit/cancel
        # and cannot reap a child, grant capacity or reconcile its outcome.
        _until(lambda: json.loads(supervisor._row(attempt.attempt_id)["status_json"])["state"] == outcome)
        _until(lambda: str(attempt.attempt_id) not in supervisor._workers)
        _assert_reaped(worker)
        row = supervisor._row(attempt.attempt_id)
        assert row["attempt_json"] == original
        with closing(supervisor._connect()) as connection:
            assert supervisor._capacity_counts(connection) == {"text": int(outcome == "outcome_unknown"), "image": 0}
        assert bool(row["receipt_json"]) == (outcome == "completed")
    finally:
        _cleanup(worker)


def test_reaper_allocation_failure_precedes_helper_popen_and_retains_reservation(supervisor, tmp_path, monkeypatch):
    _exchange, _request, _pin, _root, attempt, _profile = _prepared_text_job(supervisor, tmp_path)
    def fail_start(_self):
        raise RuntimeError("fixture thread allocation failure")
    monkeypatch.setattr(worker_module._WorkerExitReaper, "start", fail_start)
    real_popen = worker_module.subprocess.Popen
    def forbid_helper(command, *args, **kwargs):
        if len(command) > 1 and Path(command[1]).name == "codex_exec_supervisor_worker.py":
            pytest.fail("helper cannot exist before its waiter")
        return real_popen(command, *args, **kwargs)
    monkeypatch.setattr(worker_module.subprocess, "Popen", forbid_helper)
    with pytest.raises(RuntimeError, match="thread allocation"):
        supervisor.admit(attempt)
    row = supervisor._row(attempt.attempt_id)
    assert row["attempt_json"] == attempt.model_dump_json(by_alias=True)
    assert row["worker_pid"] is None and json.loads(row["status_json"])["state"] == "spawn_intent"
    assert not supervisor._workers
    with closing(supervisor._connect()) as connection:
        assert supervisor._capacity_counts(connection) == {"text": 1, "image": 0}


def test_popen_failure_releases_preallocated_waiter_without_fabricating_absence(supervisor, tmp_path, monkeypatch):
    _exchange, _request, _pin, _root, attempt, _profile = _prepared_text_job(supervisor, tmp_path)
    reapers = []
    real_start = supervisor._start_worker_reaper
    def capture(identity):
        reaper = real_start(identity)
        reapers.append(reaper)
        return reaper
    monkeypatch.setattr(supervisor, "_start_worker_reaper", capture)
    real_popen = worker_module.subprocess.Popen
    def fail_helper(command, *args, **kwargs):
        if len(command) > 1 and Path(command[1]).name == "codex_exec_supervisor_worker.py":
            raise OSError("fixture helper creation failure")
        return real_popen(command, *args, **kwargs)
    monkeypatch.setattr(worker_module.subprocess, "Popen", fail_helper)
    with pytest.raises(OSError, match="creation failure"):
        supervisor.admit(attempt)
    assert len(reapers) == 1
    reapers[0]._thread.join(timeout=2)
    assert not reapers[0]._thread.is_alive() and not supervisor._workers
    row = supervisor._row(attempt.attempt_id)
    assert row["worker_pid"] is None and json.loads(row["status_json"])["state"] == "spawn_intent"
    with closing(supervisor._connect()) as connection:
        assert supervisor._capacity_counts(connection) == {"text": 1, "image": 0}


@pytest.mark.parametrize("state", ["running", "outcome_unknown"])
def test_wait_failure_keeps_exact_handle_and_running_or_unknown_capacity(supervisor, monkeypatch, caplog, state):
    attempt = _attempt("running")
    current = attempt if state == "running" else transition_exec_attempt(attempt, state=state)
    _insert_attempt_row(supervisor, attempt, current)
    with closing(supervisor._connect()) as connection:
        connection.execute("INSERT INTO exec_slot(attempt_id,domain) VALUES (?,?)", (str(attempt.attempt_id), "text"))
    before = dict(supervisor._row(attempt.attempt_id))
    worker = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    real_wait = worker.wait
    def fail_wait(*_args, **_kwargs):
        raise OSError("fixture wait failure")
    monkeypatch.setattr(worker, "wait", fail_wait)
    try:
        with supervisor._guard:
            supervisor._workers[str(attempt.attempt_id)] = worker
        reaper = supervisor._start_worker_reaper(attempt.attempt_id)
        reaper.spawned(worker)
        reaper._thread.join(timeout=2)
        assert not reaper._thread.is_alive()
        assert supervisor._workers[str(attempt.attempt_id)] is worker
        assert dict(supervisor._row(attempt.attempt_id)) == before
        assert "exact child handle retained" in caplog.text
        with closing(supervisor._connect()) as connection:
            assert supervisor._capacity_counts(connection) == {"text": 1, "image": 0}
    finally:
        real_wait(timeout=5)
        supervisor._workers.pop(str(attempt.attempt_id), None)


def test_old_waiter_cannot_forget_replacement_popen_for_same_identity(supervisor):
    identity = uuid4()
    reaper = supervisor._start_worker_reaper(identity)
    old = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(0.1)"], start_new_session=True)
    replacement = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(10)"], start_new_session=True)
    try:
        with supervisor._guard:
            supervisor._workers[str(identity)] = old
            reaper.spawned(old)
            supervisor._workers[str(identity)] = replacement
        reaper._thread.join(timeout=2)
        _assert_reaped(old)
        assert supervisor._workers[str(identity)] is replacement
        assert replacement.poll() is None
    finally:
        _cleanup(old)
        _cleanup(replacement)
        supervisor._workers.pop(str(identity), None)


def test_another_host_reconciles_but_never_waits_for_original_parents_child(supervisor, tmp_path, monkeypatch):
    release = tmp_path / "release-original-helper"
    monkeypatch.setenv("PLOTLOOM_TEST_HELPER_RELEASE", str(release))
    _exchange, _request, _pin, _root, attempt, _profile = _prepared_text_job(supervisor, tmp_path,
        fake_cli_source="import os,sys,time\nfrom pathlib import Path\nsys.stdin.read()\ndeadline=time.monotonic()+15\nwhile not Path(os.environ['PLOTLOOM_TEST_HELPER_RELEASE']).exists() and time.monotonic()<deadline:time.sleep(0.01)\nraise SystemExit(9)\n")
    captured = _capture_spawned_workers(supervisor, monkeypatch)
    supervisor.admit(attempt)
    assert len(captured) == 1
    worker = captured[0]
    other = CodexExecSupervisor(supervisor.executable, source_root=supervisor.source_root,
        outputs_root=supervisor.outputs_root, private_root=supervisor.private_root)
    monkeypatch.setattr(other, "_start_worker_reaper", lambda _id: pytest.fail("non-parent cannot own this child wait"))
    try:
        status = other.status(attempt.attempt_id)
        assert status.state in {"spawn_intent", "running"}
        assert not other._workers
        release.touch()
        _until(lambda: str(attempt.attempt_id) not in supervisor._workers)
        _assert_reaped(worker)
        assert json.loads(other._row(attempt.attempt_id)["status_json"])["state"] == "outcome_unknown"
        with closing(other._connect()) as connection:
            assert other._capacity_counts(connection) == {"text": 1, "image": 0}
    finally:
        release.touch()
        try:
            worker.wait(timeout=5)
        except subprocess.TimeoutExpired:
            supervisor.cancel(attempt)
            _cleanup(worker)
