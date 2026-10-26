"""Explicit worker experiments retain the full runner's coverage and isolation."""

import os
from pathlib import Path
from textwrap import dedent

import pytest

from scripts.testing import experiment_python_workers
from tests.python_suite_runner_support import RUNNER, completion_proof


def _fake_runner(tmp_path, monkeypatch, *, workers, mode="pass"):
    tests = tmp_path / "tests"
    tests.mkdir()
    cases = []
    for index in range(workers):
        name = f"test_{index}.py"
        (tests / name).touch()
        cases.append(f"tests/{name}::test_case")
    processes, commands, basetemps = [], [], []
    monkeypatch.setattr(RUNNER, "WORKER_SHUTDOWN_GRACE_SECONDS", 0)

    def absent_group(*_args):
        raise ProcessLookupError

    monkeypatch.setattr(RUNNER.os, "killpg", absent_group)

    class Collector:
        pid, returncode = 900, None

        def communicate(self, timeout=None):
            self.returncode = 0
            return "\n".join(cases), ""

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

    class Worker:
        def __init__(self, command, stdout):
            self.pid = 1000 + len(processes)
            self.returncode = None if mode == "startup-failure" else 0
            self.waited = False
            processes.append(self)
            assigned = tuple(case for case in cases if case.split("::", 1)[0] in command)
            marker = completion_proof(assigned)
            if mode == "wrong-case" and len(processes) == workers:
                marker = completion_proof(tuple(case + "[drift]" for case in assigned))
            elif mode == "missing-proof" and len(processes) == workers:
                marker = "pytest passed without completion proof"
            stdout.write(marker + "\n")
            stdout.flush()

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.waited = True
            self.returncode = 0 if self.returncode is None else self.returncode
            return self.returncode

    def launch(command, **kwargs):
        if "--collect-only" in command:
            return Collector()
        commands.append(command)
        basetemps.append(Path(next(value.split("=", 1)[1] for value in command if value.startswith("--basetemp="))))
        if mode == "startup-failure" and len(commands) == workers:
            raise OSError("synthetic last-worker startup failure")
        return Worker(command, kwargs["stdout"])

    monkeypatch.setattr(RUNNER.subprocess, "Popen", launch)
    return cases, commands, processes, basetemps


@pytest.mark.parametrize("workers", [2, 4, 8])
def test_explicit_count_uses_exact_same_runner_and_complete_case_proofs(tmp_path, monkeypatch, capsys, workers):
    cases, commands, processes, basetemps = _fake_runner(tmp_path, monkeypatch, workers=workers)
    assert RUNNER.run_python_suite(root=tmp_path, environment={}, worker_count=workers) == 0
    output = capsys.readouterr().out
    assert f"workers={workers}" in output
    assert output.count("[python-suite] COMPLETE worker=") == workers
    assert len(commands) == len(processes) == len(set(basetemps)) == workers
    assert all(not path.parent.exists() for path in basetemps)
    assert {case.split("::", 1)[0] for case in cases} == {command[-1] for command in commands}
    assert all(process.waited for process in processes)


@pytest.mark.parametrize("mode", ["wrong-case", "missing-proof"])
def test_zero_exit_worker_cannot_hide_case_drift_or_missing_proof(tmp_path, monkeypatch, capsys, mode):
    _fake_runner(tmp_path, monkeypatch, workers=4, mode=mode)
    assert RUNNER.run_python_suite(root=tmp_path, environment={}, worker_count=4) == 1
    assert "REFUSED worker=4 completion:" in capsys.readouterr().out


def test_partial_four_worker_startup_reaps_started_workers_and_removes_temp_root(tmp_path, monkeypatch):
    _cases, commands, processes, basetemps = _fake_runner(tmp_path, monkeypatch, workers=4, mode="startup-failure")
    assert RUNNER.run_python_suite(root=tmp_path, environment={}, worker_count=4) == 127
    assert len(commands) == 4 and len(processes) == 3
    assert all(process.waited for process in processes)
    assert all(not path.parent.exists() for path in basetemps)


@pytest.mark.parametrize("count", [None, 0, 1, 3, 2.0, True])
def test_invalid_counts_refuse_before_any_collection(monkeypatch, count):
    monkeypatch.setattr(RUNNER.subprocess, "Popen", lambda *_a, **_k: pytest.fail("invalid count spawned collection"))
    assert RUNNER.run_python_suite(environment={}, worker_count=count) == 2


def test_release_main_still_uses_default_and_experiment_is_explicit(monkeypatch):
    counts = []
    monkeypatch.setattr(experiment_python_workers, "run_python_suite", lambda **kwargs: counts.append(kwargs) or 0)
    assert experiment_python_workers.main(["--workers", "4"]) == 0
    assert counts == [{"worker_count": 4}]
    with pytest.raises(SystemExit):
        experiment_python_workers.main([])
    with pytest.raises(SystemExit):
        experiment_python_workers.main(["--workers", "3"])
    calls = []
    monkeypatch.setattr(RUNNER, "run_python_suite", lambda **kwargs: calls.append(kwargs) or 0)
    assert RUNNER.main() == 0 and calls == [{}] and RUNNER.WORKER_COUNT == 2


@pytest.mark.skipif(os.name != "posix", reason="qualified owned process groups are POSIX")
def test_four_real_whole_file_workers_keep_sqlite_storyboard_node_and_image_isolation(tmp_path, capsys):
    bodies = [
        """
        import sqlite3
        def test_case(tmp_path):
            with sqlite3.connect(tmp_path / 'owned.sqlite') as connection:
                connection.execute('CREATE TABLE marker (value TEXT)')
                connection.execute("INSERT INTO marker VALUES ('local')")
                assert connection.execute('SELECT value FROM marker').fetchall() == [('local',)]
        """,
        """
        from plotloom.story_workloads import FIXED_CHINESE_BRIEF
        from plotloom.project_storage.composition import ProjectFolderStorage
        from tests.creative_delivery_fixtures import _accepted_f4_script
        def test_case(tmp_path):
            storage = ProjectFolderStorage(outputs_root=tmp_path / 'outputs', application_data_root=tmp_path / 'application')
            store = storage.projects.create(FIXED_CHINESE_BRIEF)
            try:
                _accepted_f4_script(store)
                store.prepare_storyboard_review_candidate('ch_' + 'r' * 32)
                assert store.storyboard_review_state().stale_reasons == []
            finally:
                store.close()
        """,
        """
        import subprocess
        def test_case(tmp_path):
            result = subprocess.run(['node', '-e', 'console.log(JSON.stringify({ok: true}))'], capture_output=True, text=True, check=True, cwd=tmp_path)
            assert result.stdout.strip() == '{"ok":true}'
        """,
        """
        from PIL import Image
        def test_case(tmp_path):
            path = tmp_path / 'frame.png'
            Image.new('RGB', (16, 9), (4, 5, 6)).save(path)
            with Image.open(path) as image:
                assert image.size == (16, 9) and image.getpixel((3, 4)) == (4, 5, 6)
        """,
    ]
    tests = tmp_path / "tests"
    tests.mkdir()
    # This disposable native collection still imports the real source/plugin
    # and helpers; it does not create a second worker implementation.
    for index, body in enumerate(bodies):
        (tests / f"test_probe_{index}.py").write_text(dedent(body), encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(RUNNER.ROOT), str(RUNNER.ROOT / "src")))
    assert RUNNER.run_python_suite(root=tmp_path, environment=environment, worker_count=4) == 0
    output = capsys.readouterr().out
    assert "native_cases=4 files=4 workers=4" in output
    assert output.count("[python-suite] COMPLETE worker=") == 4
    basetemps = [Path(line.split("basetemp=", 1)[1]) for line in output.splitlines() if line.startswith("[python-suite] START ")]
    assert len(set(basetemps)) == 4 and all(not path.parent.exists() for path in basetemps)
