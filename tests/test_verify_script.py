"""Guard explicit local verification tiers and their selection boundaries."""

from __future__ import annotations

import importlib.util
import json
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
    assert by_label["Python contracts"].command == (
        "uv",
        "run",
        "--locked",
        "--no-sync",
        "python",
        "scripts/testing/run_python_suite.py",
    )
    assert by_label["unfiltered browser shard coverage"].environment == (
        ("BROWSER_GREP", ".*"),
    )
    assert "BROWSER_SHARD" not in dict(by_label["unfiltered browser suite"].environment)


def _module_manifest():
    return json.loads(
        (ROOT / "scripts" / "testing" / "module-ownership.json").read_text(
            encoding="utf-8"
        )
    )


def test_module_union_deduplicates_modules_and_shared_dependencies():
    selection = VERIFY._load_module_selection()
    plan = selection.build_module_plan(
        _module_manifest(), ["graph", "story-authoring", "graph"], "contract", root=ROOT
    )

    assert plan.names == ("graph", "story-authoring")
    selectors = dict(plan.selectors)
    assert "tests/test_graph_commands.py" in selectors["pytest"]
    assert "tests/test_project_storage_source_outline.py" in selectors["pytest"]
    assert all(
        "::" not in selector for values in selectors.values() for selector in values
    )
    dependency_paths = [dependency["path"] for dependency in plan.dependencies]
    assert dependency_paths.count("frontend/tests/setup-browser-dom.ts") == 1


def test_module_complete_skips_unowned_suite_and_browser_depth_refuses_empty():
    selection = VERIFY._load_module_selection()
    manifest = _module_manifest()

    complete = selection.build_module_plan(
        manifest, ["shared-generation"], "complete", root=ROOT
    )
    assert complete.suites == ("pytest", "vitest")
    with pytest.raises(ValueError, match="no playwright tests"):
        selection.build_module_plan(
            manifest, ["shared-generation"], "browser", root=ROOT
        )


def test_module_complete_expands_owned_shared_build_and_package_gates(capsys):
    with patch.object(
        VERIFY.subprocess,
        "run",
        side_effect=AssertionError("show mode must not execute checks"),
    ):
        assert (
            VERIFY.main(
                [
                    "module",
                    "--module",
                    "verification-tooling",
                    "--depth",
                    "complete",
                    "--show",
                ]
            )
            == 0
        )

    output = capsys.readouterr().out
    labels = [
        "locked dependencies",
        "deterministic production bundle",
        "checked production bundle parity",
        "unfiltered browser shard coverage",
        "wheel build",
        "installed wheel smoke",
        "module pytest",
        "module Vitest",
        "module Playwright",
    ]
    assert (
        "MODULE_PLAN required_complete_gates=locked-dependencies,static-bundle,"
        "browser-allocation,wheel-package"
    ) in output
    positions = [output.index(f"command label={label}") for label in labels]
    assert positions == sorted(positions)


def test_module_selection_rejects_unknown_or_invalid_required_gates():
    selection = VERIFY._load_module_selection()
    manifest = _module_manifest()
    manifest["required_complete_gates"]["unmapped-gate"] = ["verification-tooling"]

    with pytest.raises(ValueError, match="unknown required complete gate"):
        selection.build_module_plan(
            manifest, ["verification-tooling"], "complete", root=ROOT
        )


def test_module_rejects_unknown_and_empty_selection_before_execution(capsys):
    with patch.object(
        VERIFY.subprocess,
        "run",
        side_effect=AssertionError("module suites must not launch"),
    ):
        assert VERIFY.main(["module", "--depth", "contract"]) == 2
        assert (
            VERIFY.main(["module", "--module", "no-such-module", "--depth", "contract"])
            == 2
        )
        assert (
            VERIFY.main(
                [
                    "module",
                    "--module",
                    "shared-generation",
                    "--depth",
                    "browser",
                ]
            )
            == 2
        )
    output = capsys.readouterr()
    assert "requires at least one --module" in output.err
    assert "unknown module(s)" in output.err
    assert "no playwright tests" in output.err


def test_module_show_prints_expanded_selectors_and_commands_without_execution(
    capsys,
):
    with patch.object(
        VERIFY.subprocess,
        "run",
        side_effect=AssertionError("show mode must not execute checks"),
    ):
        assert (
            VERIFY.main(
                ["module", "--module", "graph", "--depth", "contract", "--show"]
            )
            == 0
        )
    output = capsys.readouterr().out
    assert "MODULE_PLAN depth=contract modules=graph gate=module-scoped" in output
    assert "MODULE_PLAN selector=tests/test_graph_commands.py" in output
    assert "shared_dependency=pytest:tests/generation/conftest.py" in output
    assert "omitted_suites=playwright" in output
    assert "MODULE_PLAN command label=module pytest" in output
    assert "VERIFY_SUMMARY tier=module-plan" in output


def test_module_refuses_ambient_filters_before_showing_or_execution(
    monkeypatch, capsys
):
    monkeypatch.setenv("PLAYWRIGHT_GREP", "currentness")
    with patch.object(
        VERIFY.subprocess,
        "run",
        side_effect=AssertionError("ambient filter must be refused first"),
    ):
        assert (
            VERIFY.main(
                ["module", "--module", "graph", "--depth", "contract", "--show"]
            )
            == 2
        )
    output = capsys.readouterr()
    assert "PLAYWRIGHT_GREP" in output.err
    assert "currentness" not in output.err


def test_module_runner_propagates_failure_without_running_later_suites():
    calls = []

    def pass_then_fail(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0 if len(calls) < 4 else 23)

    with patch.object(VERIFY.subprocess, "run", side_effect=pass_then_fail):
        assert VERIFY.main(["module", "--module", "graph", "--depth", "browser"]) == 23

    assert len(calls) == 4
    assert calls[0][-1] == "scripts/testing/check_module_ownership.py"
    assert calls[1][-1] == "typecheck"
    assert calls[2][-1] == "typecheck:e2e"
    playwright_index = calls[3].index("test:e2e")
    assert calls[3][playwright_index + 1] == "--"
    assert any(selector.startswith("e2e/") for selector in calls[3])


def test_module_pytest_failure_stops_before_later_native_suites():
    calls = []

    def fail_pytest(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 19 if len(calls) == 3 else 0)

    with patch.object(VERIFY.subprocess, "run", side_effect=fail_pytest):
        assert (
            VERIFY.main(
                [
                    "module",
                    "--module",
                    "shared-api-security",
                    "--depth",
                    "complete",
                ]
            )
            == 19
        )

    assert len(calls) == 3
    assert calls[0][-1] == "scripts/testing/check_module_ownership.py"
    assert calls[1][-1] == "typecheck"
    assert "pytest" in calls[2]
    assert "test" not in calls[2]


def test_quick_stops_on_first_failure_and_reports_exit_code(monkeypatch, capsys):
    calls = []

    def fail_first(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 9)

    with patch.object(VERIFY.subprocess, "run", side_effect=fail_first):
        assert VERIFY.main(["quick"]) == 9
    assert len(calls) == 1
    assert "VERIFY_SUMMARY tier=quick" in capsys.readouterr().out
