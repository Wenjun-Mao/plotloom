"""Guard manual release-gate evidence, acceptance and bounded runner budgets."""

import re
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).parents[1] / ".github/workflows/ci.yml"


def _workflow():
    # BaseLoader preserves GitHub's `on` key rather than YAML1.1's boolean alias.
    return yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)


def test_filtered_browser_runs_remain_opt_in_diagnostics():
    workflow = _workflow()
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["on"]["workflow_dispatch"]["inputs"]["browser_grep"]["default"] == ".*"
    browser = workflow["jobs"]["browser"]
    assert browser["needs"] == "verify"
    step = next(item for item in browser["steps"] if item.get("name") == "Browser regression contracts")
    assert step["env"]["BROWSER_GREP"] == "${{ inputs.browser_grep }}"
    assert '--grep="${BROWSER_GREP}"' in step["run"]
    assert "inputs.browser_grep" not in step["run"]


def test_browser_shards_preserve_all_results_without_runner_contention():
    browser = _workflow()["jobs"]["browser"]
    assert browser["strategy"]["fail-fast"] == "false"
    assert browser["strategy"]["matrix"]["shard"] == ["1", "2"]
    step = next(item for item in browser["steps"] if item.get("name") == "Browser regression contracts")
    assert "--workers=1" in step["run"]
    assert '--shard="${BROWSER_SHARD}/2"' in step["run"]
    uploads = [item for item in browser["steps"] if item.get("uses") == "actions/upload-artifact@v4"]
    assert len(uploads) == 2
    assert all(item["if"] == "${{ !cancelled() }}" for item in uploads)
    assert all("${{ matrix.shard }}" in item["with"]["name"] for item in uploads)


def test_playwright_deadline_leaves_time_to_finalize_and_upload_evidence():
    browser = _workflow()["jobs"]["browser"]
    step = next(item for item in browser["steps"] if item.get("name") == "Browser regression contracts")
    global_timeout = int(re.search(r"--global-timeout=(\d+)", step["run"])[1])
    assert global_timeout < int(step["timeout-minutes"]) * 60_000
    assert int(step["timeout-minutes"]) < int(browser["timeout-minutes"])


def test_full_python_gate_has_measured_runner_budget_and_cleanup_margin():
    verify = _workflow()["jobs"]["verify"]
    step = next(item for item in verify["steps"] if item.get("name") == "Python and distribution contracts")
    # The growing serial suite reached 83% before the former 30-minute job ended.
    # Preserve the full selection and leave wheel/smoke time outside its budget.
    assert 45 <= int(step["timeout-minutes"]) < int(verify["timeout-minutes"]) <= 60
    assert int(verify["timeout-minutes"]) - int(step["timeout-minutes"]) >= 10
    command = step["run"].split()
    assert command[:4] == ["uv", "run", "pytest", "-q"]
    assert command[4:] == ["--durations=20"]
