"""Assertions and hostile ambient-Python control for the paid CLI fixture."""
import json
import os
import shlex
import sys
from pathlib import Path

from tests.cli_handoff_fixtures import ROOT, exclusive
from tests.paid_outline_cli_runtime import assert_qa_runtime


def without_ambient_python(case):
    """Prove the shadow Python is dependency-free, then reset its selection log."""
    directory = case["root"] / "ambient-python"
    directory.mkdir(mode=0o700)
    marker = directory / "selected"
    launcher = directory / "python3"
    exclusive(launcher, ("#!/bin/sh\n"
        + "printf 'selected\\n' >> " + shlex.quote(str(marker)) + "\n"
        + "exec " + shlex.quote(sys.executable) + ' -I -S "$@"\n').encode())
    launcher.chmod(0o700)
    case["environment"]["PATH"] = str(directory) + os.pathsep + case["environment"]["PATH"]
    result = case["processes"].run(["python3", "-c",
        ("import importlib.util,json,sys; print(json.dumps({'executable':sys.executable,"
        "'isolated':sys.flags.isolated,'noSite':sys.flags.no_site,"
        "'dotenvAbsent':importlib.util.find_spec('dotenv') is None}))")],
        env=case["environment"], capture_output=True, text=True, timeout=10, check=True)
    facts = json.loads(result.stdout)
    assert marker.read_text() == "selected\n"
    assert facts == {"executable": sys.executable, "isolated": 1, "noSite": 1, "dotenvAbsent": True}
    exclusive(directory / "control.json", json.dumps(facts, sort_keys=True).encode())
    marker.unlink()
    return marker


def assert_cli_observations(case, *, sandbox_count):
    startup = [json.loads(path.read_bytes()) for path in
        (case["root"] / "receipts").glob("cli-startup-runtime-*.json")]
    sandbox = [json.loads(path.read_bytes()) for path in
        (case["root"] / "receipts").glob("cli-sandbox-runtime-*.json")]
    assert startup
    by_pid = {item["pid"]: item for item in startup}
    assert len(by_pid) == len(startup)
    for facts in startup:
        assert_qa_runtime(case["qa"], facts)
        assert Path(facts["wrapper"]) == case["executable"]
        assert Path(facts["runtimeSupportImport"]) == ROOT / "tests/paid_outline_cli_runtime.py"
    sandbox_pids = {item["pid"] for item in sandbox}
    assert sandbox_pids == {item["pid"] for item in startup if item["invocation"] == "sandbox"}
    assert len(sandbox_pids) == len(sandbox) == sandbox_count
    expected = {
        "plotloom.config": case["source"] / "src/plotloom/config.py",
        "plotloom.codex_exec_profile": case["source"] / "src/plotloom/codex_exec_profile.py",
        "codex_exec_supervisor_environment": case["source"] / "services/creator_workbench/codex_exec_supervisor_environment.py",
        "codex_exec_supervisor_validation": case["source"] / "services/creator_workbench/codex_exec_supervisor_validation.py",
    }
    for facts in sandbox:
        assert_qa_runtime(case["qa"], facts)
        assert all(facts[field] == value for field, value in by_pid[facts["pid"]].items()
            if field not in {"invocation", "wrapper", "runtimeSupportImport"})
        assert Path(facts["cliSupportImport"]) == ROOT / "tests/paid_outline_cli_fixture.py"
        for name, path in expected.items():
            assert Path(facts["imports"][name]) == path
        assert Path(facts["imports"]["dotenv"]).resolve().is_relative_to(Path(case["qa"]["prefix"]))
