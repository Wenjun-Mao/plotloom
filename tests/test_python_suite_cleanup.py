"""Owned shutdown admission, bounded child reaping and strict group observation."""
import os
import signal
import subprocess
import sys
import time

import pytest
from tests.python_suite_runner_support import RUNNER


class OwnedWorker:
    def __init__(self, pid=123, on_wait=None):
        self.pid = pid
        self.returncode = None
        self.waits = []
        self.polls = 0
        self.on_wait = on_wait

    def poll(self):
        self.polls += 1
        return self.returncode

    def wait(self, timeout=None):
        if timeout is not None:
            self.waits.append(timeout)
            if self.on_wait:
                self.on_wait(timeout)
        self.returncode = -signal.SIGTERM
        return self.returncode


def shutdown_clock(monkeypatch, budget=5):
    clock = [0.0]
    monkeypatch.setattr(RUNNER, "WORKER_SHUTDOWN_GRACE_SECONDS", budget)
    monkeypatch.setattr(RUNNER.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(RUNNER.time, "sleep", lambda delay: clock.__setitem__(0, clock[0] + delay))
    return clock


@pytest.mark.parametrize("exited", [False, True])
def test_standalone_group_probe_does_not_recover_denied_permission(monkeypatch, exited):
    worker = OwnedWorker()
    worker.returncode = -signal.SIGTERM if exited else None
    calls = []
    def denied(pid, sig):
        calls.append((pid, sig))
        raise PermissionError(1, "signal authority denied")
    monkeypatch.setattr(RUNNER.os, "killpg", denied)
    with pytest.raises(PermissionError, match="signal authority denied"):
        RUNNER._process_group_exists(worker)
    assert calls == [(worker.pid, 0)]
    assert worker.polls == 0 and not worker.waits


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX shutdown")
def test_denied_probe_waits_for_owned_exit_after_poll_still_reports_running(monkeypatch):
    shutdown_clock(monkeypatch)
    worker = OwnedWorker()
    calls = []
    def signal_group(pid, sig):
        calls.append((pid, sig))
        if sig == 0:
            if worker.returncode is None:
                raise PermissionError(1, "exit not yet reapable")
            raise ProcessLookupError(3, "group gone after wait")
    monkeypatch.setattr(RUNNER.os, "killpg", signal_group)
    RUNNER._stop_processes([worker])
    assert worker.polls == 1
    assert worker.waits == [5]
    assert worker.returncode == -signal.SIGTERM
    assert calls == [(worker.pid, signal.SIGTERM), (worker.pid, 0), (worker.pid, 0)]


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX shutdown")
def test_reaped_leader_does_not_hide_surviving_descendants(monkeypatch):
    clock = shutdown_clock(monkeypatch, budget=0.1)
    worker = OwnedWorker()
    calls = []
    def signal_group(pid, sig):
        calls.append((pid, sig))
        if sig == 0 and worker.returncode is None:
            raise PermissionError(1, "owned leader exiting")
    monkeypatch.setattr(RUNNER.os, "killpg", signal_group)
    RUNNER._stop_processes([worker])
    assert worker.waits == [0.1]
    assert clock[0] == pytest.approx(0.1)
    assert calls[0] == (worker.pid, signal.SIGTERM)
    assert calls[-1] == (worker.pid, signal.SIGKILL)
    assert sum(sig == 0 for _, sig in calls) >= 2


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX shutdown")
def test_owned_child_timeout_preserves_denial_and_does_not_escalate(monkeypatch):
    shutdown_clock(monkeypatch)
    def timeout(budget):
        raise subprocess.TimeoutExpired("owned worker", budget)
    worker = OwnedWorker(on_wait=timeout)
    calls = []
    def signal_group(pid, sig):
        calls.append((pid, sig))
        if sig == 0:
            raise PermissionError(1, "still denied")
    monkeypatch.setattr(RUNNER.os, "killpg", signal_group)
    with pytest.raises(PermissionError, match="still denied") as failure:
        RUNNER._stop_processes([worker])
    assert isinstance(failure.value.__cause__, subprocess.TimeoutExpired)
    assert worker.waits == [5] and worker.returncode is None
    assert all(sig != signal.SIGKILL for _, sig in calls)


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX shutdown")
def test_persistent_probe_denial_after_reaping_does_not_escalate(monkeypatch):
    shutdown_clock(monkeypatch)
    worker = OwnedWorker()
    calls = []
    def signal_group(pid, sig):
        calls.append((pid, sig))
        if sig == 0:
            raise PermissionError(1, "persistent denial")
    monkeypatch.setattr(RUNNER.os, "killpg", signal_group)
    with pytest.raises(PermissionError, match="persistent denial"):
        RUNNER._stop_processes([worker])
    assert worker.returncode == -signal.SIGTERM and worker.waits == [5]
    assert calls == [(worker.pid, signal.SIGTERM), (worker.pid, 0), (worker.pid, 0)]


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX shutdown")
def test_initial_term_denial_cannot_authorize_wait_or_later_signals(monkeypatch):
    worker = OwnedWorker()
    calls = []
    def denied(pid, sig):
        calls.append((pid, sig))
        raise PermissionError(1, "TERM denied")
    monkeypatch.setattr(RUNNER.os, "killpg", denied)
    with pytest.raises(PermissionError, match="TERM denied"):
        RUNNER._stop_processes([worker])
    assert calls == [(worker.pid, signal.SIGTERM)] and not worker.waits


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX shutdown")
def test_missing_term_group_cannot_authorize_recovery_of_a_denied_probe(monkeypatch):
    shutdown_clock(monkeypatch)
    worker = OwnedWorker()
    def missing_then_denied(_pid, sig):
        if sig == signal.SIGTERM:
            raise ProcessLookupError(3, "original group gone")
        raise PermissionError(1, "unknown group")
    monkeypatch.setattr(RUNNER.os, "killpg", missing_then_denied)
    with pytest.raises(PermissionError, match="unknown group"):
        RUNNER._stop_processes([worker])
    assert not worker.waits


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX shutdown")
@pytest.mark.parametrize("first_elapsed", [3, 5])
def test_two_owned_groups_share_the_original_shutdown_deadline(monkeypatch, first_elapsed):
    clock = shutdown_clock(monkeypatch)
    first = OwnedWorker(123, lambda _budget: clock.__setitem__(0, clock[0] + first_elapsed))
    def second_exit(budget):
        if budget == 0:
            raise subprocess.TimeoutExpired("second owned worker", budget)
        clock[0] += 1
    second = OwnedWorker(456, second_exit)
    workers = {worker.pid: worker for worker in (first, second)}
    calls = []
    def signal_group(pid, sig):
        calls.append((pid, sig))
        if sig == 0:
            if workers[pid].returncode is None:
                raise PermissionError(1, "owned worker exiting")
            raise ProcessLookupError(3, "group gone")
    monkeypatch.setattr(RUNNER.os, "killpg", signal_group)
    if first_elapsed == 5:
        with pytest.raises(PermissionError, match="owned worker exiting"):
            RUNNER._stop_processes([first, second])
    else:
        RUNNER._stop_processes([first, second])
    assert first.waits == [5] and second.waits == [5 - first_elapsed]
    assert clock[0] == (5 if first_elapsed == 5 else 4)
    assert all(sig != signal.SIGKILL for _, sig in calls)


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX process groups")
def test_stop_processes_reaps_two_running_owned_groups():
    workers = []
    try:
        for _ in range(2):
            process = subprocess.Popen([sys.executable, "-c", "import time; print('ready', flush=True); time.sleep(30)"],
                stdout=subprocess.PIPE, text=True, start_new_session=True)
            workers.append(process)
            assert process.stdout is not None
            assert process.stdout.readline().strip() == "ready"
            assert process.poll() is None
        RUNNER._stop_processes(workers)
        assert all(process.returncode is not None for process in workers)
        assert all(not RUNNER._process_group_exists(process) for process in workers)
    finally:
        for process in workers:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            if process.stdout is not None:
                process.stdout.close()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX process groups")
def test_stop_processes_kills_descendant_after_worker_leader_exits(
    tmp_path, monkeypatch
):
    ready_path = tmp_path / "child-ready"
    child_script = (
        "import pathlib, signal, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "pathlib.Path(sys.argv[1]).write_text('ready', encoding='utf-8')\n"
        "time.sleep(30)\n"
    )
    leader_script = (
        "import pathlib, subprocess, sys, time\n"
        "ready = pathlib.Path(sys.argv[1])\n"
        "child = subprocess.Popen(\n"
        "    [sys.executable, '-c', sys.argv[2], str(ready)],\n"
        "    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,\n"
        ")\n"
        "deadline = time.monotonic() + 5\n"
        "while not ready.exists() and time.monotonic() < deadline:\n"
        "    time.sleep(0.01)\n"
        "if not ready.exists():\n"
        "    raise SystemExit('child did not become ready')\n"
        "print(child.pid, flush=True)\n"
        "time.sleep(30)\n"
    )
    monkeypatch.setattr(RUNNER, "WORKER_SHUTDOWN_GRACE_SECONDS", 0.15)
    leader = subprocess.Popen(
        [sys.executable, "-c", leader_script, str(ready_path), child_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    child_pid: int | None = None

    def process_state(pid: int) -> str:
        result = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            capture_output=True,
            check=False,
            text=True,
        )
        return result.stdout.strip()

    try:
        assert leader.stdout is not None
        child_pid_text = leader.stdout.readline().strip()
        assert child_pid_text.isdecimal()
        child_pid = int(child_pid_text)
        assert ready_path.read_text(encoding="utf-8") == "ready"
        state = process_state(child_pid)
        assert state and not state.startswith("Z")
        RUNNER._stop_processes([leader])
        assert leader.poll() is not None

        deadline = time.monotonic() + 3
        state = process_state(child_pid)
        while state and not state.startswith("Z") and time.monotonic() < deadline:
            time.sleep(0.05)
            state = process_state(child_pid)
        assert not state or state.startswith("Z")
    finally:
        try:
            os.killpg(leader.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if leader.poll() is None:
            leader.wait(timeout=3)
        if leader.stdout is not None:
            leader.stdout.close()
