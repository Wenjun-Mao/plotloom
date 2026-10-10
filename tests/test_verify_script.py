"""Guard explicit local verification tiers and their selection boundaries."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts" / "verify.py"
SPEC = importlib.util.spec_from_file_location("plotloom_verify", VERIFY_PATH)
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFY
SPEC.loader.exec_module(VERIFY)


def test_quick_tier_is_lock_lint_frontend_unit_and_type_only():
    commands = [step.command for step in VERIFY._quick_steps()]
    assert commands == [
        ("uv", "lock", "--check"),
        (
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "ruff",
            "check",
            "src/plotloom/api",
            "--select",
            "F401",
        ),
        ("npm", "--prefix", "frontend", "test"),
        ("npm", "--prefix", "frontend", "run", "typecheck"),
        ("npm", "--prefix", "frontend", "run", "typecheck:e2e"),
    ]


def test_focused_requires_selection_and_rejects_unknown_files(capsys):
    with patch.object(
        VERIFY.subprocess,
        "run",
        side_effect=AssertionError("must reject before execution"),
    ):
        assert VERIFY.main(["focused"]) == 2
        assert VERIFY.main(["focused", "--pytest", "tests/missing_test_file.py"]) == 2
        assert VERIFY.main(["focused", "--vitest", "tests/missing.test.ts"]) == 2
        assert VERIFY.main(["focused", "--playwright", "e2e/missing.spec.ts"]) == 2
    output = capsys.readouterr()
    assert "requires at least one" in output.err
    assert "unknown pytest selector" in output.err
    assert "unknown Vitest selector" in output.err
    assert "unknown Playwright selector" in output.err


def test_focused_preflights_exact_pytest_case_and_prints_commands(capsys):
    calls = []

    def pass_preflight_then_fail(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 0 if "--collect-only" in command else 17
        )

    selector = "tests/test_style_contract_cache.py::test_owner_style_and_none_versus_empty_direction_are_distinct_keys"
    with patch.object(VERIFY.subprocess, "run", side_effect=pass_preflight_then_fail):
        assert VERIFY.main(["focused", "--pytest", selector]) == 17
    assert len(calls) == 2
    assert calls[0][-3:] == ["--collect-only", "-q", selector]
    assert calls[1][-2:] == ["-q", selector]
    output = capsys.readouterr().out
    assert "[focused] COMMAND" in output
    assert selector in output
    assert "VERIFY_SUMMARY tier=focused" in output
    assert "exit_code=17" in output


def test_unknown_pytest_case_is_rejected_by_native_collection():
    code = VERIFY.main(
        ["focused", "--pytest", "tests/test_style_contract_cache.py::not_a_real_case"]
    )
    assert code != 0


@pytest.mark.parametrize(
    "name,value",
    [
        ("PYTEST_ADDOPTS", "-k currentness"),
        ("BROWSER_GREP", "currentness"),
        ("BROWSER_SHARD", "1"),
        ("VITEST_FILTER", "app-state"),
        ("PLAYWRIGHT_SHARD", "1"),
    ],
)
def test_full_refuses_ambient_diagnostic_selection_without_logging_values(
    name, value, monkeypatch, capsys
):
    monkeypatch.setenv(name, value)
    with patch.object(
        VERIFY.subprocess,
        "run",
        side_effect=AssertionError("must refuse before execution"),
    ):
        assert VERIFY.main(["full"]) == 2
    output = capsys.readouterr()
    assert name in output.err
    assert value not in output.err


def test_full_accepts_only_the_full_browser_grep():
    assert VERIFY._validate_full_filters({"BROWSER_GREP": ".*"}) == []
    assert "BROWSER_GREP" in VERIFY._validate_full_filters(
        {"BROWSER_GREP": "currentness"}
    )


def test_full_steps_include_all_release_gates_in_safe_build_order(tmp_path):
    steps = VERIFY._full_steps(tmp_path / "wheel")
    labels = [step.label for step in steps]
    assert labels == [
        "locked dependencies",
        "ffmpeg probe tool",
        "ffprobe probe tool",
        "API unused imports",
        "archived prompt reader",
        "frontend unit tests",
        "frontend type contracts",
        "Python contracts",
        "deterministic production bundle",
        "checked production bundle parity",
        "unfiltered browser shard coverage",
        "unfiltered browser suite",
        "wheel build",
        "installed wheel smoke",
    ]
    assert labels.index("deterministic production bundle") < labels.index("wheel build")
    by_label = {step.label: step for step in steps}
    assert by_label["unfiltered browser shard coverage"].environment == (
        ("BROWSER_GREP", ".*"),
    )
    assert "BROWSER_SHARD" not in dict(by_label["unfiltered browser suite"].environment)


def test_quick_stops_on_first_failure_and_reports_exit_code(monkeypatch, capsys):
    calls = []

    def fail_first(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 9)

    with patch.object(VERIFY.subprocess, "run", side_effect=fail_first):
        assert VERIFY.main(["quick"]) == 9
    assert len(calls) == 1
    assert "VERIFY_SUMMARY tier=quick" in capsys.readouterr().out
