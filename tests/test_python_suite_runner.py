from __future__ import annotations

import json
import os
import signal
import subprocess
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts.testing import python_suite_timing_plugin
from scripts.testing.python_suite_completion import RUN_MARKER, validate_worker_completion
from tests.python_suite_runner_support import RUNNER, completion_proof


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


def test_partition_assigns_whole_files_once_and_balances_case_counts(tmp_path):
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
    rows = {
        "tests/test_a.py": (1.0, 89.0, 0.0),
        "tests/test_b.py": (1.0, 79.0, 0.0),
        "tests/test_c.py": (0.5, 9.5, 0.0),
        "tests/test_d.py": (0.5, 9.5, 0.0),
    }
    manifest = json.dumps(_timing_manifest(tmp_path, cases, rows))
    schedule = RUNNER.python_suite_schedule.schedule_from_timing_text(
        manifest, cases=cases, root=tmp_path
    )
    assert schedule.basis == "duration"
    assert schedule.fallback_reason is None
    assert schedule.assignments == (
        ("tests/test_a.py", "tests/test_d.py"),
        ("tests/test_b.py", "tests/test_c.py"),
    )


def test_partition_refuses_duplicate_or_empty_collections(tmp_path):
    with pytest.raises(RUNNER.SuiteError, match="empty"):
        RUNNER.partition_test_files([])
    with pytest.raises(RUNNER.SuiteError, match="duplicate"):
        RUNNER.partition_test_files(["tests/test_a.py::test_one"] * 2)
    cases = [
        "tests/test_a.py::test_1",
        "tests/test_a.py::test_2",
        "tests/test_b.py::test_1",
        "tests/test_c.py::test_1",
    ]
    rows = {
        "tests/test_a.py": (1.0, 89.0, 0.0),
        "tests/test_b.py": (1.0, 79.0, 0.0),
    }
    incomplete = json.dumps(_timing_manifest(tmp_path, cases, rows))
    schedule = RUNNER.python_suite_schedule.schedule_from_timing_text(
        incomplete, cases=cases, root=tmp_path
    )
    assert schedule.basis == "case-count"
    assert schedule.fallback_reason == "timing-file-coverage-changed"
    assert schedule.assignments == RUNNER.partition_test_files(cases)

    complete_rows = {**rows, "tests/test_c.py": (0.5, 0.5, 0.0)}
    stale = _timing_manifest(tmp_path, cases, complete_rows)
    stale["host_fingerprint"] = "f" * 64
    schedule = RUNNER.python_suite_schedule.schedule_from_timing_text(
        json.dumps(stale), cases=cases, root=tmp_path
    )
    assert schedule.fallback_reason == "host-or-python-changed"

    stale = _timing_manifest(tmp_path, cases, complete_rows)
    stale["input_fingerprint"] = "e" * 64
    schedule = RUNNER.python_suite_schedule.schedule_from_timing_text(
        json.dumps(stale), cases=cases, root=tmp_path
    )
    assert schedule.fallback_reason == "executable-inputs-changed"

    wrong_count = _timing_manifest(tmp_path, cases, complete_rows)
    wrong_count["files"][0]["case_count"] += 1
    schedule = RUNNER.python_suite_schedule.schedule_from_timing_text(
        json.dumps(wrong_count), cases=cases, root=tmp_path
    )
    assert schedule.fallback_reason == "timing-case-counts-changed"

    valid_rows = {path: (1.0, 1.0, 0.0) for path in ("tests/test_a.py", "tests/test_b.py")}
    valid = _timing_manifest(tmp_path, ["tests/test_a.py::test_1", "tests/test_b.py::test_1"], valid_rows)
    malformed = []
    unsafe = json.loads(json.dumps(valid))
    unsafe["files"][0]["path"] = "tests/../outside.py"
    malformed.append(unsafe)
    duplicate = json.loads(json.dumps(valid))
    duplicate["files"].append(dict(duplicate["files"][0]))
    malformed.append(duplicate)
    nonfinite = json.loads(json.dumps(valid))
    nonfinite["files"][0]["call_seconds"] = float("inf")
    malformed.append(nonfinite)
    aggregate = json.loads(json.dumps(valid))
    aggregate["files"][0]["setup_seconds"] = 1e308
    aggregate["files"][0]["call_seconds"] = 1e308
    malformed.append(aggregate)
    huge_integer = json.loads(json.dumps(valid))
    huge_integer["files"][0]["setup_seconds"] = 10**1000
    malformed.append(huge_integer)
    for value in malformed:
        with pytest.raises(RUNNER.python_suite_schedule.TimingManifestError):
            RUNNER.python_suite_schedule.schedule_from_timing_text(
                json.dumps(value, allow_nan=True),
                cases=["tests/test_a.py::test_1", "tests/test_b.py::test_1"],
                root=tmp_path,
            )


def test_worker_command_keeps_results_isolated_and_durations_visible(capsys):
    with TemporaryDirectory() as directory:
        basetemp = Path(directory) / "worker-1"
        command = RUNNER._command(["tests/test_a.py"], basetemp)
    assert "--durations=20" in command
    assert "-p" in command and "no:cacheprovider" in command
    assert f"--basetemp={basetemp}" in command
    assert command[-1] == "tests/test_a.py"
    assert "scripts.testing.python_suite_timing_plugin" in command

    plugin = python_suite_timing_plugin.FilePhaseTotals()
    item = SimpleNamespace(nodeid="tests/test_a.py::test_one")
    plugin.pytest_collection_finish(SimpleNamespace(items=[item]))
    plugin.pytest_runtest_logreport(
        SimpleNamespace(nodeid=item.nodeid, when="call", duration=0.25)
    )
    plugin.pytest_sessionfinish(SimpleNamespace(), 0)
    output = capsys.readouterr().out
    assert validate_worker_completion(output, [item.nodeid])
    assert '"case_count":1' in output

    failed = python_suite_timing_plugin.FilePhaseTotals()
    failed.pytest_collection_finish(SimpleNamespace(items=[item]))
    failed.pytest_runtest_logreport(
        SimpleNamespace(nodeid=item.nodeid, when="call", duration=0.25)
    )
    failed.pytest_sessionfinish(SimpleNamespace(), 1)
    output = capsys.readouterr().out
    marker = next(line[len(RUN_MARKER):] for line in output.splitlines() if line.startswith(RUN_MARKER))
    assert json.loads(marker)["complete"] is False
    assert "PYTHON_SUITE_FILE_TIMING" not in output


def _timing_manifest(root, cases, weights):
    schedule = RUNNER.python_suite_schedule
    case_counts = Counter(case.split("::", 1)[0] for case in cases)
    return {
        "schema_version": 1,
        "native_case_ids_sha256": schedule.native_case_fingerprint(cases),
        "input_fingerprint": schedule.input_fingerprint(root),
        "host_fingerprint": schedule.host_fingerprint(),
        "files": [
            {
                "path": path,
                "case_count": case_counts[path],
                "setup_seconds": values[0],
                "call_seconds": values[1],
                "teardown_seconds": values[2],
            }
            for path, values in weights.items()
        ],
    }


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
            stdout.write(completion_proof((f"{command[-1]}::{Path(command[-1]).stem}",)) + "\n")
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
    assert "schedule=case-count fallback=timing-manifest-missing" in output
    assert len(commands) == 2
    assert commands[0][-1] == "tests/test_a.py"
    assert commands[1][-1] == "tests/test_b.py"


@pytest.mark.parametrize("worker_count", [2, 4])
def test_sigterm_stops_running_worker_groups(tmp_path, monkeypatch, capsys, worker_count):
    tests = tmp_path / "tests"
    tests.mkdir()
    for name in (f"test_{index}.py" for index in range(worker_count)):
        (tests / name).touch()
    collection = "\n".join(f"tests/test_{index}.py::test_case" for index in range(worker_count))
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
            if len(processes) == worker_count:
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
        RUNNER.run_python_suite(root=tmp_path, environment={}, worker_count=worker_count) == 128 + signal.SIGTERM
    )
    output = capsys.readouterr().out
    assert "TERMINATED signal=15" in output
    assert len(processes) == worker_count
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
