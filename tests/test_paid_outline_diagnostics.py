"""Passive synthetic diagnostics; no paid journey, process launch or provider."""
import json
from copy import deepcopy

import pytest

from tests import paid_outline_diagnostics as diagnostics
from tests.cli_handoff_fixtures import ROOT
from tests.paid_outline_cli_checks import assert_cli_observations
from tests.paid_outline_processes import OwnedTestProcesses


def case_for(tmp_path):
    (tmp_path / "receipts").mkdir()
    (tmp_path / "phase").mkdir()
    qa = {"entrypoint": "/synthetic/venv/bin/python", "prefix": "/synthetic/venv",
        "physicalExecutable": "/synthetic/venv/bin/python", "physicalBasePrefix": "/synthetic/base",
        "implementation": "cpython", "majorMinor": [3, 12]}
    row = {key: qa[key] for key in ("physicalExecutable", "physicalBasePrefix", "implementation", "majorMinor")}
    row.update(executable=qa["entrypoint"], physicalPrefix=qa["prefix"], pid=11, invocation="sandbox",
        wrapper=str(tmp_path / "fake-codex"), runtimeSupportImport=str(ROOT / "tests/paid_outline_cli_runtime.py"))
    case = {"root": tmp_path, "qa": qa, "executable": tmp_path / "fake-codex", "source": tmp_path / "source"}
    return case, row


def write_rows(case, startup, sandbox):
    for kind, rows in (("startup", startup), ("sandbox", sandbox)):
        for index, row in enumerate(rows):
            (case["root"] / "receipts" / f"cli-{kind}-runtime-{index}.json").write_text(json.dumps(row))


@pytest.mark.parametrize("startup,sandbox", [(0, 0), (2, 0), (1, 0), (1, 1)])
def test_original_observation_failures_keep_order_and_add_counts(tmp_path, startup, sandbox):
    case, row = case_for(tmp_path)
    # Empty startup, duplicate PID, unequal sets, then original expected-two count.
    write_rows(case, [row] * startup, [row] * sandbox)
    with pytest.raises(AssertionError) as error:
        assert_cli_observations(case, sandbox_count=2)
    value = json.loads(str(error.value))
    assert value["startupCount"] == startup and value["sandboxCount"] == sandbox
    assert value["expectedSandboxCount"] == 2
    assert value["startupPids"]["items"] == ([11] if startup else [])
    assert value["sandboxStartupPids"]["items"] == ([11] if startup else [])


def test_failure_context_selects_existing_outcomes_without_private_output(tmp_path):
    case, row = case_for(tmp_path)
    secret = "DO_NOT_DISCLOSE_TOKEN_OR_COMMAND"
    (tmp_path / "capsule-result-success.json").write_text(json.dumps({
        "outcome": {"status": "HELD", "reason": secret, "environment": secret},
        "actualFixtureChildTerminal": {"code": 7, "output": secret}, "driverLog": secret}))
    (tmp_path / "phase/paid-result.json").write_text(json.dumps({"outcome": "UNKNOWN",
        "reason": "RuntimeError", "attemptState": "outcome_unknown", "auth": secret}))
    value = diagnostics.cli_failure_context(case, [row], [row], 2)
    assert secret not in value
    parsed = json.loads(value)
    assert parsed["capsules"]["success"] == {"file": "read", "status": "HELD", "reason": "<omitted>", "childExitCode": 7}
    assert parsed["paid"] == {"file": "read", "outcome": "UNKNOWN", "reason": "RuntimeError", "attemptState": "outcome_unknown"}
    (tmp_path / "capsule-result-invalid-candidate.json").write_text('{"outcome":{"status":"RECEIVER_ACCEPTED"}}')
    assert json.loads(diagnostics.cli_failure_context(case, [], [], 1))["capsules"]["invalid-candidate"]["status"] == "RECEIVER_ACCEPTED"


@pytest.mark.parametrize("content,state", [(None, "absent"), (b"not-json", "unreadable"),
    (b"\xff", "unreadable"), (b"[]", "not-object"), (b"x" * (diagnostics.MAX_FILE_BYTES + 1), "too-large")],
    ids=["absent", "malformed", "invalid-utf8", "non-object", "oversized"])
def test_absent_malformed_and_large_context_cannot_mask_count_failure(tmp_path, content, state):
    case, row = case_for(tmp_path)
    if content is not None:
        (tmp_path / "capsule-result-success.json").write_bytes(content)
    write_rows(case, [row], [row])
    with pytest.raises(AssertionError) as error:
        assert_cli_observations(case, sandbox_count=2)
    assert json.loads(str(error.value))["capsules"]["success"]["file"] == state


def test_symlink_context_and_read_errors_do_not_replace_original_failure(tmp_path, monkeypatch):
    case, row = case_for(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text('{"outcome":{"status":"HELD"}}')
    (tmp_path / "capsule-result-success.json").symlink_to(outside)
    assert json.loads(diagnostics.cli_failure_context(case, [], [], 2))["capsules"]["success"]["file"] == "unsafe"
    def refused(*args):
        raise OSError("PRIVATE_ERROR_TEXT")
    monkeypatch.setattr(diagnostics, "_read_case_file", refused)
    write_rows(case, [row], [row])
    with pytest.raises(AssertionError) as error:
        assert_cli_observations(case, sandbox_count=2)
    assert "PRIVATE_ERROR_TEXT" not in str(error.value)
    assert json.loads(str(error.value))["paid"]["file"] == "unreadable"


def report_for():
    return {"remaining": [{"pid": 31, "ppid": 30, "pgid": 31, "command": "PRIVATE_COMMAND"}],
        "errors": ["identity: PRIVATE_COMMAND", "PRIVATE_AUTH"], "observerError": "RuntimeError",
        "unresolvedSpawns": [{"pid": 32, "parentPid": 31, "command": "PRIVATE_COMMAND"}],
        "unresolvedGroups": {"31": [31, 32]}, "directExits": [{"pid": 30, "exitCode": 7}]}


def test_cached_settlement_failure_is_passive_and_preserves_report(monkeypatch):
    owner = OwnedTestProcesses.__new__(OwnedTestProcesses)
    owner._report = report_for()
    before = deepcopy(owner._report)
    def forbidden(*args):
        raise AssertionError("diagnostics must not observe or signal")
    monkeypatch.setattr("tests.paid_outline_processes.process_identity", forbidden)
    monkeypatch.setattr("tests.paid_outline_processes.os.kill", forbidden)
    with pytest.raises(RuntimeError, match="owned test process settlement failed; evidence retained:") as error:
        owner.settle()
    message = str(error.value)
    assert "PRIVATE" not in message and owner._report == before
    summary = json.loads(message.split("evidence retained: ", 1)[1])
    assert summary["remaining"] == {"count": 1, "items": [{"pid": 31, "ppid": 30, "pgid": 31}]}
    assert summary["errors"] == {"count": 2, "categories": ["identity:", "<omitted>"]}
    assert summary["observerError"] == "RuntimeError"
    assert summary["unresolvedSpawns"]["items"] == [{"pid": 32, "parentPid": 31}]
    assert summary["unresolvedGroups"]["items"] == [{"pgid": 31, "members": {"count": 2, "items": [31, 32]}}]
    assert summary["directExits"]["items"] == [{"pid": 30, "exitCode": 7}]


def test_bounded_numeric_and_error_output_never_exposes_unknown_strings(tmp_path):
    case, _row = case_for(tmp_path)
    rows = [{"pid": n, "invocation": "PRIVATE"} for n in range(1000)]
    summary = json.loads(diagnostics.cli_failure_context(case, rows, rows, 2))
    assert summary["startupPids"]["count"] == 1000 and len(summary["startupPids"]["items"]) == diagnostics.MAX_ITEMS
    assert summary["invocations"]["other"] == 1000 and "PRIVATE" not in json.dumps(summary)
    report = report_for()
    report.update(remaining=[{"pid": 10**1000, "command": "PRIVATE"}] * 1000,
        errors=["PRIVATE"] * 1000, observerError="PRIVATE",
        unresolvedGroups={"PRIVATE": ["PRIVATE"] * 1000})
    result = diagnostics.settlement_failure_context(report)
    assert len(result) <= diagnostics.MAX_MESSAGE_CHARS and "PRIVATE" not in result
    assert json.loads(result)["remaining"]["count"] == 1000


def test_diagnostic_serialization_failure_preserves_assertion_and_settlement(tmp_path, monkeypatch):
    case, row = case_for(tmp_path)
    write_rows(case, [row], [row])
    def broken(*args, **kwargs):
        raise RuntimeError("PRIVATE_SERIALIZER_FAILURE")
    monkeypatch.setattr(diagnostics.json, "dumps", broken)
    with pytest.raises(AssertionError, match="diagnostics.*unavailable"):
        assert_cli_observations(case, sandbox_count=2)
    owner = OwnedTestProcesses.__new__(OwnedTestProcesses)
    owner._report = report_for()
    with pytest.raises(RuntimeError, match="settlement failed; evidence retained:.*unavailable"):
        owner.settle()
