from __future__ import annotations

import importlib.util
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "testing" / "run_python_suite.py"
SPEC = importlib.util.spec_from_file_location("plotloom_python_suite", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def test_collector_accepts_native_rows_and_rejects_duplicate_or_unsafe_cases(tmp_path):
    test_file = tmp_path / "tests" / "test_sample.py"
    test_file.parent.mkdir()
    test_file.touch()
    rows = "tests/test_sample.py::test_one\ntests/test_sample.py::test_two\n"
    assert (
        RUNNER.parse_collected_cases(rows, root=tmp_path) == rows.strip().splitlines()
    )

    with pytest.raises(RUNNER.SuiteError, match="duplicate"):
        RUNNER.parse_collected_cases(
            rows + "tests/test_sample.py::test_one\n", root=tmp_path
        )
    with pytest.raises(RUNNER.SuiteError, match="unsafe"):
        RUNNER.parse_collected_cases("tests/../outside.py::test_one\n", root=tmp_path)


def test_partition_assigns_whole_files_once_and_balances_case_counts():
    cases = [
        "tests/test_a.py::test_1",
        "tests/test_a.py::test_2",
        "tests/test_a.py::test_3",
        "tests/test_b.py::test_1",
        "tests/test_b.py::test_2",
        "tests/test_c.py::test_1",
        "tests/test_d.py::test_1",
    ]
    assignments = RUNNER.partition_test_files(cases)
    flattened = [path for assignment in assignments for path in assignment]
    assert len(flattened) == len(set(flattened))
    assert set(flattened) == {case.split("::", 1)[0] for case in cases}
    assert assignments == RUNNER.partition_test_files(cases)
    case_counts = Counter(case.split("::", 1)[0] for case in cases)
    shard_totals = [
        sum(case_counts[path] for path in assignment) for assignment in assignments
    ]
    assert abs(shard_totals[0] - shard_totals[1]) <= 1


def test_partition_refuses_duplicate_or_empty_collections():
    with pytest.raises(RUNNER.SuiteError, match="empty"):
        RUNNER.partition_test_files([])
    with pytest.raises(RUNNER.SuiteError, match="duplicate"):
        RUNNER.partition_test_files(["tests/test_a.py::test_one"] * 2)


def test_worker_command_keeps_results_isolated_and_durations_visible():
    with TemporaryDirectory() as directory:
        basetemp = Path(directory) / "worker-1"
        command = RUNNER._command(["tests/test_a.py"], basetemp)
    assert "--durations=20" in command
    assert "-p" in command and "no:cacheprovider" in command
    assert f"--basetemp={basetemp}" in command
    assert command[-1] == "tests/test_a.py"


def test_runner_refuses_ambient_pytest_selection_before_collecting(capsys):
    with patch.object(
        RUNNER.subprocess,
        "Popen",
        side_effect=AssertionError("must refuse before collection"),
    ):
        assert (
            RUNNER.run_python_suite(environment={"PYTEST_ADDOPTS": "-k currentness"})
            == 2
        )
    assert "refuses ambient PYTEST_ADDOPTS" in capsys.readouterr().err


def test_runner_reports_each_worker_and_fails_if_either_worker_fails(
    tmp_path, monkeypatch, capsys
):
    tests = tmp_path / "tests"
    tests.mkdir()
    for name in ("test_a.py", "test_b.py"):
        (tests / name).touch()
    collection = "tests/test_a.py::test_a\ntests/test_b.py::test_b\n"
    monkeypatch.setattr(RUNNER, "WORKER_SHUTDOWN_GRACE_SECONDS", 0)
    monkeypatch.setattr(RUNNER.os, "killpg", lambda *_args: None)
    outcomes = iter((0, 7))
    commands = []

    class CompletedWorker:
        def __init__(self, command, *, stdout, **_kwargs):
            commands.append(command)
            stdout.write("captured worker report\n")
            stdout.flush()
            self.returncode = next(outcomes)
            self.pid = len(commands) + 100

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

    class CompletedCollector:
        pid = 900
        returncode = None

        def communicate(self, timeout=None):
            self.returncode = 0
            return collection, ""

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

    def start_process(command, **kwargs):
        if "--collect-only" in command:
            return CompletedCollector()
        return CompletedWorker(command, **kwargs)

    monkeypatch.setattr(RUNNER.subprocess, "Popen", start_process)

    assert RUNNER.run_python_suite(root=tmp_path, environment={}) == 1
    output = capsys.readouterr().out
    assert output.count("captured worker report") == 2
    assert "worker=1" in output and "worker=2" in output
    assert "SUMMARY elapsed_seconds=" in output and "exit_code=1" in output
    assert len(commands) == 2
    assert commands[0][-1] == "tests/test_a.py"
    assert commands[1][-1] == "tests/test_b.py"


def test_sigterm_stops_running_worker_groups(tmp_path, monkeypatch, capsys):
    tests = tmp_path / "tests"
    tests.mkdir()
    for name in ("test_a.py", "test_b.py"):
        (tests / name).touch()
    collection = "tests/test_a.py::test_a\ntests/test_b.py::test_b\n"
    original_signal = RUNNER.signal.signal
    handlers = {}

    def recording_signal(signum, handler):
        previous = original_signal(signum, handler)
        if signum == signal.SIGTERM and callable(handler):
            handlers[signum] = handler
        return previous

    monkeypatch.setattr(RUNNER.signal, "signal", recording_signal)
    monkeypatch.setattr(RUNNER, "WORKER_SHUTDOWN_GRACE_SECONDS", 0)
    killed_groups = []
    terminated_processes = []

    def kill_process_group(pid, received_signal):
        if pid == 900:
            raise ProcessLookupError
        killed_groups.append((pid, received_signal))

    monkeypatch.setattr(RUNNER.os, "killpg", kill_process_group)
    processes = []

    class CompletedCollector:
        pid = 900
        returncode = None

        def communicate(self, timeout=None):
            self.returncode = 0
            return collection, ""

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

    class RunningWorker:
        def __init__(self, _command, **_kwargs):
            self.pid = 100 + len(processes)
            self.returncode = None
            processes.append(self)
            if len(processes) == 2:
                handlers[signal.SIGTERM](signal.SIGTERM, None)

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.returncode = -signal.SIGTERM
            return self.returncode

        def terminate(self):
            terminated_processes.append(self.pid)
            self.returncode = -signal.SIGTERM

    def start_process(command, **kwargs):
        if "--collect-only" in command:
            return CompletedCollector()
        return RunningWorker(command, **kwargs)

    monkeypatch.setattr(RUNNER.subprocess, "Popen", start_process)

    assert (
        RUNNER.run_python_suite(root=tmp_path, environment={}) == 128 + signal.SIGTERM
    )
    output = capsys.readouterr().out
    assert "TERMINATED signal=15" in output
    assert len(processes) == 2
    assert all(process.returncode is not None for process in processes)
    if os.name == "posix":
        assert killed_groups == [
            *((process.pid, signal.SIGTERM) for process in processes),
            *((process.pid, signal.SIGKILL) for process in processes),
        ]
    else:
        assert terminated_processes == [process.pid for process in processes]


def test_sigterm_during_collection_stops_and_reaps_collector(
    tmp_path, monkeypatch, capsys
):
    (tmp_path / "tests").mkdir()
    handlers = {}
    original_signal = RUNNER.signal.signal

    def recording_signal(signum, handler):
        previous = original_signal(signum, handler)
        if signum == signal.SIGTERM and callable(handler):
            handlers[signum] = handler
        return previous

    monkeypatch.setattr(RUNNER.signal, "signal", recording_signal)
    monkeypatch.setattr(RUNNER, "WORKER_SHUTDOWN_GRACE_SECONDS", 0.1)
    process_calls = []
    process_state = {"group_exists": True, "reaped": False, "terminated": False}
    group_signals = []

    class BlockingCollector:
        pid = 901
        returncode = None

        def __init__(self, command, **_kwargs):
            self.command = command
            process_calls.append(command)

        def communicate(self, timeout=None):
            handlers[signal.SIGTERM](signal.SIGTERM, None)
            raise subprocess.TimeoutExpired(self.command, timeout)

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.returncode = -signal.SIGTERM
            process_state["reaped"] = True
            return self.returncode

        def terminate(self):
            process_state["terminated"] = True

    def kill_process_group(pid, received_signal):
        assert pid == BlockingCollector.pid
        group_signals.append(received_signal)
        if received_signal == signal.SIGTERM:
            process_state["group_exists"] = False
        elif received_signal == 0 and not process_state["group_exists"]:
            raise ProcessLookupError

    monkeypatch.setattr(RUNNER.subprocess, "Popen", BlockingCollector)
    monkeypatch.setattr(RUNNER.os, "killpg", kill_process_group)

    assert (
        RUNNER.run_python_suite(root=tmp_path, environment={}) == 128 + signal.SIGTERM
    )
    assert len(process_calls) == 1
    assert "--collect-only" in process_calls[0]
    assert process_state["reaped"]
    if os.name == "posix":
        assert signal.SIGTERM in group_signals
        assert signal.SIGKILL not in group_signals
    else:
        assert process_state["terminated"]
    assert "TERMINATED signal=15" in capsys.readouterr().out


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
