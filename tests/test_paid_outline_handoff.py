"""Actual paid entry and owner composition; external native/provider IO is fake."""
import json
import os
import sqlite3
import subprocess
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.cli_handoff_fixtures import ROOT
from tests.codex_exec_runtime_fixtures import (
    codex_exec_test_source as _codex_exec_test_source,  # noqa: F401
)
from tests.paid_outline_fixtures import (
    _commit_fixture,
    allocation_model,
    rebind_allocation,
    run_capsule,
)
from tests.paid_outline_fixtures import (
    paid_case as _paid_case,  # noqa: F401 -- explicit named pytest fixture registration
)
from tests.paid_outline_fixtures import (
    paid_schema_case as _paid_schema_case,  # noqa: F401
)
from tests.paid_outline_fixtures import (
    paid_source as _paid_source,  # noqa: F401
)
from tests.paid_outline_processes import owned_processes


def _copied_snapshot_source(root, processes):
    original, copied = root / "original", root / "copied"
    original.mkdir(mode=0o700)
    environment = os.environ | {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    processes.run(["git", "-c", "init.defaultBranch=main", "init", "--quiet", str(original)],
        env=environment, check=True, capture_output=True)
    for name in ("src/plotloom", "services", "scripts", ".agents"):
        directory = original / name
        directory.mkdir(parents=True)
        (directory / "fixture.txt").write_text("original fixture bytes\n")
    for name in ("pyproject.toml", "uv.lock"):
        (original / name).write_text("synthetic snapshot fixture\n")
    _commit_fixture(original, processes)
    processes.run(["git", "clone", "--quiet", "--no-hardlinks", str(original), str(copied)],
        env=environment, check=True, capture_output=True)
    return copied


@pytest.mark.parametrize("changed", [False, True], ids=["clean-copy", "controlled-delta"])
def test_fixture_snapshot_creates_distinct_commit_for_copied_source(tmp_path, changed):
    tmp_path.chmod(0o700)
    with owned_processes(tmp_path) as processes:
        source = _copied_snapshot_source(tmp_path, processes)
        def git(*arguments):
            return processes.run(["git", "-C", str(source), *arguments],
                check=True, capture_output=True, text=True).stdout.strip()
        original_head, original_tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        assert git("status", "--porcelain") == ""
        if changed:
            (source / "services/fixture.txt").write_text("controlled copied-source delta\n")
            (source / "outside-owner.txt").write_text("must remain outside the snapshot\n")
        _commit_fixture(source, processes)
        snapshot_head, snapshot_tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        assert snapshot_head != original_head
        assert git("rev-list", "--parents", "-n", "1", "HEAD").split() == [snapshot_head, original_head]
        if changed:
            assert snapshot_tree != original_tree
            assert git("diff", "--name-only", original_head, snapshot_head) == "services/fixture.txt"
            assert git("show", "HEAD:services/fixture.txt") == "controlled copied-source delta"
            assert "outside-owner.txt" not in git("ls-files").splitlines()
        else:
            assert snapshot_tree == original_tree
            assert git("status", "--porcelain") == ""


@pytest.mark.parametrize("operation", ["add", "commit"])
def test_fixture_snapshot_propagates_actual_git_failure(tmp_path, operation):
    tmp_path.chmod(0o700)
    with owned_processes(tmp_path) as processes:
        source = _copied_snapshot_source(tmp_path, processes)
        reference = source / ".git/refs/heads/main"
        original_reference = reference.read_bytes()
        if operation == "add":
            (source / ".git/index.lock").write_text("explicit test-owned lock\n")
        else:
            processes.run(["git", "-C", str(source), "config", "core.hooksPath", ".git/hooks"],
                check=True, capture_output=True)
            hook = source / ".git/hooks/pre-commit"
            hook.write_text("#!/bin/sh\nprintf 'fixture commit refused\\n' >&2\nexit 73\n")
            hook.chmod(0o700)
            (source / "services/fixture.txt").write_text("rejected copied-source delta\n")
        with pytest.raises(subprocess.CalledProcessError) as failure:
            _commit_fixture(source, processes)
        assert failure.value.returncode != 0 and operation in failure.value.cmd
        expected = b"index.lock" if operation == "add" else b"fixture commit refused"
        assert expected in failure.value.stderr
        assert reference.read_bytes() == original_reference
    settlement = json.loads((tmp_path / "process-settlement.json").read_bytes())
    assert not settlement["remaining"] and not settlement["errors"]


def test_paid_source_is_independent_and_generic_metadata_semantics_survive(tmp_path,
        codex_exec_test_source, paid_source):
    from plotloom.codex_exec_python_environment import (
        RECEIPT_PATH,
        inspect_checked_python_environment,
    )

    generic = codex_exec_test_source
    assert generic != paid_source
    generic_raw, paid_raw = [(source / RECEIPT_PATH).read_bytes() for source in (generic, paid_source)]
    generic_receipt, paid_receipt = map(json.loads, (generic_raw, paid_raw))
    assert generic_receipt["sourceRoot"] == str(generic)
    assert paid_receipt["sourceRoot"] == str(paid_source)
    assert generic_receipt["environmentRoot"] != paid_receipt["environmentRoot"]
    assert generic_receipt["runtimeRoot"] != paid_receipt["runtimeRoot"]
    generic_runtime = inspect_checked_python_environment(generic)
    paid_runtime = inspect_checked_python_environment(paid_source)
    assert generic_runtime.root != paid_runtime.root
    tmp_path.chmod(0o700)
    with owned_processes(tmp_path) as processes:
        def head(source):
            return processes.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True).stdout.strip()
        assert head(generic) == head(ROOT)
        assert head(paid_source) != head(generic)
        for runtime in (generic_runtime, paid_runtime):
            result = processes.run([str(runtime.interpreter), "unsupported-fixture-operation"], capture_output=True)
            assert result.returncode == 78
    assert (generic / RECEIPT_PATH).read_bytes() == generic_raw
    assert (paid_source / RECEIPT_PATH).read_bytes() == paid_raw


def test_registered_paid_entry_reaches_one_receipt_and_validated_delivery_then_hold(paid_case):
    case = paid_case
    result = run_capsule(case)
    assert result["syntheticEvidence"] is True and result["qualification"] is False
    assert result["outcome"]["status"] == "RECEIVER_ACCEPTED", json.dumps(result, indent=2)
    assert result["actualFixtureChildTerminal"]["code"] == 0, json.dumps(result, indent=2)
    paid = json.loads((case["root"] / "phase/paid-result.json").read_bytes())
    assert paid["outcome"] == "RECEIPT_AND_VALIDATED_DELIVERY" and paid["held"] is True, paid
    assert paid["canonicalAdoption"] is False and paid["imageAdmissions"] == 0 and paid["retryAuthorized"] is False
    allocation = case["allocation"]
    with closing(sqlite3.connect(allocation["projectDatabase"]["path"])) as connection:
        attempt = connection.execute("SELECT snapshot FROM v2_autopilot_exec_attempts").fetchall()
        assert len(attempt) == 1
        assert json.loads(attempt[0][0])["attemptId"] == allocation["namespace"]["attempt"]["attemptId"]
        assert connection.execute("SELECT state FROM v2_autopilot_runs").fetchone()[0] == "paused"
        checkpoints = connection.execute("SELECT operation_key,state FROM v2_autopilot_checkpoints").fetchall()
        assert dict(checkpoints) == {"source": "adopted", "outline": "sent"}
    with closing(sqlite3.connect(allocation["namespace"]["database"]["path"])) as connection:
        assert connection.execute("SELECT count(*) FROM exec_attempts").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM exec_queue").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM exec_slot").fetchone()[0] == 0
        receipt = json.loads(connection.execute("SELECT receipt_json FROM exec_attempts").fetchone()[0])
    validation = receipt["textValidation"]
    assert [item["stepId"] for item in validation["steps"]] == ["validate", "render"]
    assert all(item["exitCode"] == 0 for item in validation["steps"])
    private = Path(allocation["namespace"]["privateRoot"]["path"]) / "attempts" / allocation["namespace"]["attempt"]["attemptId"]
    validated = (private / "validation/validate.stdout").read_bytes()
    assert "✓ 通过校验" in validated.decode()
    assert sha256(validated).hexdigest() == validation["steps"][0]["stdoutHash"]
    job = Path(allocation["projectHome"]["path"]) / "outputs/creative-handoff/jobs" / allocation["namespace"]["attempt"]["jobId"]
    report = (job / "delivery/report.html").read_bytes()
    assert len(report) > 1000 and b"<!doctype html" in report.lower()
    assert sha256(report).hexdigest() == validation["reportHash"] == validation["steps"][1]["stdoutHash"]


def test_late_readiness_deadline_refuses_actual_consume_and_keeps_original_reservation(paid_case):
    case = paid_case
    result = run_capsule(case, mode="deadline")
    assert result["outcome"]["status"] == "RECEIVER_ACCEPTED", json.dumps(result, indent=2)
    assert result["actualFixtureChildTerminal"]["code"] == 0, json.dumps(result, indent=2)
    paid = json.loads((case["root"] / "phase/paid-result.json").read_bytes())
    assert paid["held"] is True and paid["outcome"] == "NOT_ADMITTED" and paid["initialAdmissionSpent"] is False, paid
    allocation = case["allocation"]
    with closing(sqlite3.connect(allocation["projectDatabase"]["path"])) as connection:
        snapshots = connection.execute("SELECT snapshot FROM v2_autopilot_exec_attempts").fetchall()
        assert [json.loads(row[0]) for row in snapshots] == [allocation["namespace"]["attempt"]]
        assert connection.execute("SELECT state FROM v2_autopilot_runs").fetchone()[0] == "paused"
        assert connection.execute("SELECT state FROM v2_autopilot_checkpoints WHERE operation_key='outline'").fetchone()[0] == "prepared"
    with closing(sqlite3.connect(allocation["namespace"]["database"]["path"])) as connection:
        assert all(connection.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
            for table in ("exec_attempts", "exec_queue", "exec_slot", "exec_validation_process"))


def test_invalid_candidate_fails_real_node_validation_without_receipt_or_retry(paid_case):
    case = paid_case
    output = case["root"] / "provider-output.json"
    candidate = json.loads(output.read_bytes())
    del candidate["params"]
    output.write_text(json.dumps(candidate, ensure_ascii=False))
    result = run_capsule(case, mode="invalid-candidate")
    assert result["outcome"]["status"] == "RECEIVER_ACCEPTED", json.dumps(result, indent=2)
    assert result["actualFixtureChildTerminal"]["code"] == 0, json.dumps(result, indent=2)
    paid = json.loads((case["root"] / "phase/paid-result.json").read_bytes())
    assert paid["held"] is True and paid["outcome"] == "FAILED", paid
    assert "receiptSha256" not in paid and "deliverySha256" not in paid
    allocation = case["allocation"]
    attempt_id = allocation["namespace"]["attempt"]["attemptId"]
    with closing(sqlite3.connect(allocation["namespace"]["database"]["path"])) as connection:
        rows = connection.execute("SELECT attempt_id,status_json,receipt_json FROM exec_attempts").fetchall()
        assert len(rows) == 1 and rows[0][0] == attempt_id and rows[0][2] is None
        assert json.loads(rows[0][1])["state"] == "failed"
        assert all(connection.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
            for table in ("exec_queue", "exec_slot", "exec_validation_process"))
    private = Path(allocation["namespace"]["privateRoot"]["path"]) / "attempts" / attempt_id
    failures = list((private / "validation").glob("*.stderr"))
    assert failures and "缺少 params" in "\n".join(item.read_text() for item in failures)
    with closing(sqlite3.connect(allocation["projectDatabase"]["path"])) as connection:
        attempts = connection.execute("SELECT snapshot FROM v2_autopilot_exec_attempts").fetchall()
        assert len(attempts) == 1 and json.loads(attempts[0][0])["attemptId"] == attempt_id
        assert connection.execute("SELECT state FROM v2_autopilot_runs").fetchone()[0] == "paused"
        assert dict(connection.execute("SELECT operation_key,state FROM v2_autopilot_checkpoints")) == {"source": "adopted", "outline": "failed"}


def test_lost_launch_ack_holds_original_spent_attempt_and_fences_unstarted_host(paid_case):
    case = paid_case
    result = run_capsule(case, mode="lost-ack")
    assert result["outcome"]["status"] == "RECEIVER_ACCEPTED", json.dumps(result, indent=2)
    assert result["actualFixtureChildTerminal"]["code"] == 0, json.dumps(result, indent=2)
    paid = json.loads((case["root"] / "phase/paid-result.json").read_bytes())
    assert paid["held"] is True and paid["outcome"] == "UNKNOWN" and paid["initialAdmissionSpent"] is True, paid
    allocation = case["allocation"]
    attempt_id = allocation["namespace"]["attempt"]["attemptId"]
    with closing(sqlite3.connect(allocation["projectDatabase"]["path"])) as connection:
        attempts = connection.execute("SELECT snapshot FROM v2_autopilot_exec_attempts").fetchall()
        assert len(attempts) == 1
        observed = json.loads(attempts[0][0])
        assert observed["attemptId"] == attempt_id and observed["state"] == "outcome_unknown"
        assert connection.execute("SELECT state FROM v2_autopilot_runs").fetchone()[0] == "paused"
    # Observe SQL only: status must never be used to redispatch this failure.
    with closing(sqlite3.connect(allocation["namespace"]["database"]["path"])) as connection:
        rows = connection.execute("SELECT attempt_id,status_json,worker_pid,receipt_json FROM exec_attempts").fetchall()
        assert len(rows) == 1 and rows[0][0] == attempt_id and rows[0][2:] == (None, None)
        assert json.loads(rows[0][1])["state"] == "queued"
        assert connection.execute("SELECT enabled FROM exec_queue WHERE attempt_id=?", (attempt_id,)).fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM exec_slot").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM exec_validation_process").fetchone()[0] == 0


def test_duplicate_capsule_does_not_admit_another_attempt(paid_case):
    case = paid_case
    first = run_capsule(case)
    assert first["actualFixtureChildTerminal"]["code"] == 0, json.dumps(first, indent=2)
    before = (case["root"] / "phase/paid-result.json").read_bytes()
    duplicate = run_capsule(case, mode="duplicate")
    assert duplicate["outcome"]["status"] == "HELD", json.dumps(duplicate, indent=2)
    assert duplicate["actualFixtureChildTerminal"] is None
    assert "SYNTHETIC_registered_paid_launch" not in duplicate["calls"]
    assert (case["root"] / "phase/paid-result.json").read_bytes() == before
    with closing(sqlite3.connect(case["allocation"]["namespace"]["database"]["path"])) as connection:
        assert connection.execute("SELECT count(*) FROM exec_attempts").fetchone()[0] == 1


@pytest.mark.parametrize("field,value", [("initialAdmissions", True), ("imageAdmissions", False),
    ("retries", False), ("initialAdmissions", 2), ("imageAdmissions", 1), ("retries", 1),
    ("canonicalAdoption", True), ("laterStages", True), ("settlementAuthority", "adopt"),
    ("authority", "provider_free_handoff"), ("version", "unknown"), ("unknown", 1)])
def test_allocation_schema_refuses_permission_laundering(paid_schema_case, field, value):
    model = allocation_model(paid_schema_case)
    value_dict = deepcopy(paid_schema_case["allocation"])
    value_dict[field] = value
    with pytest.raises(ValidationError):
        model.model_validate(value_dict)


@pytest.mark.parametrize("field,value", [("initialAdmissions", True), ("imageAdmissions", 1),
    ("retries", 1), ("canonicalAdoption", True), ("laterStages", True), ("authority", "provider_free_handoff")])
def test_actual_js_contract_refuses_fully_rebound_bad_allocation_before_intent(paid_case, field, value):
    case = paid_case
    rebind_allocation(case, lambda allocation: allocation.update({field: value}))
    result = run_capsule(case)
    assert result["outcome"]["status"] == "HELD" and result["calls"] == ["prepare"], json.dumps(result, indent=2)
    assert result["actualFixtureChildTerminal"] is None
    assert not (case["root"] / "phase/invocation-intent.json").exists()


@pytest.mark.parametrize("drift", ["source-revision", "qa-as-validator"])
def test_js_refuses_rebound_source_or_runtime_role_substitution(paid_case, drift):
    case = paid_case
    def substitute(allocation):
        if drift == "source-revision":
            allocation["source"]["revision"] = "0" * 40
        else:
            allocation["validatorRuntime"].update(root=case["qa"]["prefix"], interpreter=case["qa"]["entrypoint"])
    rebind_allocation(case, substitute)
    result = run_capsule(case, mode=drift)
    assert result["outcome"]["status"] == "HELD" and result["calls"] == ["prepare"], json.dumps(result, indent=2)
    assert result["actualFixtureChildTerminal"] is None
    assert not (case["root"] / "phase/invocation-intent.json").exists()


@pytest.mark.parametrize("drift", ["run-revision", "claim", "policy", "checkpoint", "catalog",
    "binding", "home-inode", "validator-identity", "profile"])
def test_actual_paid_receiver_refuses_frozen_drift_without_consume_or_foreign_control(paid_case, drift):
    case, allocation = paid_case, paid_case["allocation"]
    database = allocation["projectDatabase"]["path"]
    with closing(sqlite3.connect(database)) as connection:
        if drift == "run-revision":
            connection.execute("UPDATE v2_autopilot_runs SET revision=revision+1")
        elif drift == "claim":
            foreign = "f" * 32 if allocation["claimEdges"]["pausedClaim"] != "f" * 32 else "e" * 32
            connection.execute("UPDATE v2_autopilot_runs SET claim=?", (foreign,))
        elif drift == "policy":
            connection.execute("UPDATE v2_autopilot_runs SET policy_hash=?", ("0" * 64,))
        elif drift == "checkpoint":
            connection.execute("UPDATE v2_autopilot_checkpoints SET revision=revision+1 WHERE operation_key='outline'")
        connection.commit()
        before_run = connection.execute("SELECT * FROM v2_autopilot_runs").fetchall()
        before_checkpoints = connection.execute("SELECT * FROM v2_autopilot_checkpoints ORDER BY operation_key").fetchall()
    if drift == "catalog":
        (Path(allocation["namespace"]["outputsRoot"]["path"]) / "foreign-project").mkdir(mode=0o700)
    elif drift == "binding":
        binding = Path(allocation["namespace"]["privateRoot"]["path"]) / "namespace-binding.json"
        binding.rename(binding.with_name("retained-binding.json"))
    elif drift == "home-inode":
        rebind_allocation(case, lambda value: value["projectHome"].update(inode=value["projectHome"]["inode"] + 1))
    elif drift == "validator-identity":
        rebind_allocation(case, lambda value: value["validatorRuntime"].update(identityHash="0" * 64))
    elif drift == "profile":
        with case["executable"].open("a") as stream:
            stream.write("\n# explicit synthetic executable identity drift\n")
    result = run_capsule(case, mode=drift)
    assert result["outcome"]["status"] == "RECEIVER_ACCEPTED", json.dumps(result, indent=2)
    assert result["actualFixtureChildTerminal"]["code"] == 1, json.dumps(result, indent=2)
    paid_path = case["root"] / "phase/paid-result.json"
    if paid_path.exists():
        assert json.loads(paid_path.read_bytes())["held"] is False
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT * FROM v2_autopilot_runs").fetchall() == before_run
        assert connection.execute("SELECT * FROM v2_autopilot_checkpoints ORDER BY operation_key").fetchall() == before_checkpoints
        attempts = connection.execute("SELECT snapshot FROM v2_autopilot_exec_attempts").fetchall()
        assert [json.loads(row[0]) for row in attempts] == [allocation["namespace"]["attempt"]]
    with closing(sqlite3.connect(allocation["namespace"]["database"]["path"])) as connection:
        assert all(connection.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
            for table in ("exec_attempts", "exec_queue", "exec_slot", "exec_validation_process"))
