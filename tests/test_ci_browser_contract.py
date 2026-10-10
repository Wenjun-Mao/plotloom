"""Guard manual release-gate evidence, acceptance and bounded runner budgets."""

import json
import re
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).parents[1] / ".github/workflows/ci.yml"
FRONTEND = WORKFLOW.parents[2] / "frontend"
PLAYWRIGHT_CONFIG = FRONTEND / "playwright.config.ts"
SHARD_MANIFEST = FRONTEND / "e2e/browser-shard-manifest.json"
SHARD_GUARD = FRONTEND / "scripts/check_browser_shard_manifest.mjs"


def _workflow():
    # BaseLoader preserves GitHub's `on` key rather than YAML1.1's boolean alias.
    return yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)


def test_filtered_browser_runs_remain_opt_in_diagnostics():
    workflow = _workflow()
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert (
        workflow["on"]["workflow_dispatch"]["inputs"]["browser_grep"]["default"] == ".*"
    )
    browser = workflow["jobs"]["browser"]
    assert "needs" not in browser
    step = next(
        item
        for item in browser["steps"]
        if item.get("name") == "Browser regression contracts"
    )
    assert step["env"]["BROWSER_GREP"] == "${{ inputs.browser_grep }}"
    assert '--grep="${BROWSER_GREP}"' in step["run"]
    assert "--pass-with-no-tests" in step["run"]
    assert "inputs.browser_grep" not in step["run"]


def test_full_release_jobs_are_independent_and_must_all_succeed_on_the_same_sha():
    jobs = _workflow()["jobs"]
    assert set(jobs) == {"verify", "browser"}
    conditional_steps = []
    for job in jobs.values():
        assert "needs" not in job
        assert "if" not in job
        assert "continue-on-error" not in job
        for step in job["steps"]:
            assert "continue-on-error" not in step
            if "if" in step:
                conditional_steps.append(step)
        checkouts = [
            step
            for step in job["steps"]
            if step.get("uses", "").startswith("actions/checkout@")
        ]
        assert checkouts
        assert all(step["with"]["ref"] == "${{ github.sha }}" for step in checkouts)
    assert {step.get("name") for step in conditional_steps} == {
        "Upload Playwright test results",
        "Upload Playwright report",
    }
    assert all(
        step.get("uses") == "actions/upload-artifact@v4" for step in conditional_steps
    )
    assert all(step["if"] == "${{ !cancelled() }}" for step in conditional_steps)
    browser = jobs["browser"]
    assert browser["strategy"]["fail-fast"] == "false"
    assert browser["strategy"]["matrix"]["shard"] == ["1", "2"]


def test_browser_shards_preserve_all_results_without_runner_contention():
    browser = _workflow()["jobs"]["browser"]
    assert browser["strategy"]["fail-fast"] == "false"
    assert browser["strategy"]["matrix"]["shard"] == ["1", "2"]
    steps = browser["steps"]
    guard_index = next(
        index
        for index, item in enumerate(steps)
        if item.get("name")
        == "Verify browser shard allocation and selected case coverage"
    )
    step_index = next(
        index
        for index, item in enumerate(steps)
        if item.get("name") == "Browser regression contracts"
    )
    guard = steps[guard_index]
    step = steps[step_index]
    assert guard_index < step_index
    assert guard["working-directory"] == "frontend"
    assert guard["env"]["BROWSER_GREP"] == "${{ inputs.browser_grep }}"
    assert guard["run"] == "node scripts/check_browser_shard_manifest.mjs"
    assert "--workers=1" in step["run"]
    assert "--shard" not in step["run"]
    assert step["env"]["BROWSER_SHARD"] == "${{ matrix.shard }}"
    assert '--grep="${BROWSER_GREP}"' in step["run"]
    config = PLAYWRIGHT_CONFIG.read_text()
    assert "process.env.BROWSER_SHARD" in config
    assert "testMatch:" in config
    assert "fullyParallel: false" in config

    manifest = json.loads(SHARD_MANIFEST.read_text())
    assert set(manifest) == {"1", "2"}
    assigned = manifest["1"] + manifest["2"]
    expected = {
        path.relative_to(FRONTEND / "e2e").as_posix()
        for path in (FRONTEND / "e2e").rglob("*")
        if path.is_file()
        and re.search(r"\.(?:spec|test)\.(?:[cm]?[jt]sx?)$", path.name)
    }
    assert len(assigned) == len(set(assigned))
    assert set(assigned) == expected
    guard_source = SHARD_GUARD.read_text()
    assert "assignmentCounts" in guard_source
    assert "unexpectedCases" in guard_source
    assert "missingCases" in guard_source
    assert "overlap" in guard_source
    assert "BROWSER_GREP" in guard_source
    assert '"--list"' in guard_source
    assert 'browserGrep === ".*"' in guard_source
    assert "shardOne.size === 0 || shardTwo.size === 0" in guard_source
    uploads = [
        item
        for item in browser["steps"]
        if item.get("uses") == "actions/upload-artifact@v4"
    ]
    assert len(uploads) == 2
    assert all(item["if"] == "${{ !cancelled() }}" for item in uploads)
    assert all("${{ matrix.shard }}" in item["with"]["name"] for item in uploads)


def test_playwright_deadline_leaves_time_to_finalize_and_upload_evidence():
    browser = _workflow()["jobs"]["browser"]
    step = next(
        item
        for item in browser["steps"]
        if item.get("name") == "Browser regression contracts"
    )
    global_timeout = int(re.search(r"--global-timeout=(\d+)", step["run"])[1])
    assert global_timeout < int(step["timeout-minutes"]) * 60_000
    assert int(step["timeout-minutes"]) < int(browser["timeout-minutes"])


def test_full_python_gate_has_measured_runner_budget_and_cleanup_margin():
    verify = _workflow()["jobs"]["verify"]
    step = next(
        item
        for item in verify["steps"]
        if item.get("name") == "Python and distribution contracts"
    )
    # The growing serial suite reached 83% before the former 30-minute job ended.
    # Preserve the full selection and leave wheel/smoke time outside its budget.
    assert 45 <= int(step["timeout-minutes"]) < int(verify["timeout-minutes"]) <= 60
    assert int(verify["timeout-minutes"]) - int(step["timeout-minutes"]) >= 10
    command = step["run"].split()
    assert command[:4] == ["uv", "run", "pytest", "-q"]
    assert command[4:] == ["--durations=20"]
