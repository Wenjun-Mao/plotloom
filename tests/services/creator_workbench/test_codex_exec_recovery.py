"""Native recovery owner preserves UNKNOWN unless all dispatch facts settle."""
import json
from contextlib import closing
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from codex_exec_supervisor_test_support import _insert_attempt_row, _prepared_text_job

from plotloom.codex_exec_contracts import CodexExecAttempt, transition_exec_attempt
from plotloom.codex_exec_runtime import package_tree_hash
from plotloom.project_storage.project_home import find_project_home
from tests.codex_exec_recovery_fixtures import write_readonly_turn


@pytest.fixture
def recoverable(supervisor, tmp_path, monkeypatch):
    import codex_exec_supervisor_recovery as owner
    _exchange, _request, _pin, _text_job, text_attempt, _profile = _prepared_text_job(supervisor, tmp_path)
    home = find_project_home(supervisor.outputs_root, str(text_attempt.project_id)).path
    job_id = "ij_" + uuid4().hex
    job = home / "runs" / ("synthetic__" + job_id) / "jobs" / job_id
    (job / "package").mkdir(parents=True)
    (job / "delivery").mkdir()
    request = {"packageVersion": 8, "executorBackend": "codex_exec", "executionContract": "codex_exec.v1",
        "jobId": job_id, "requestHash": "a" * 64,
        "specialistPreflight": {"codeRevision": text_attempt.plotloom_code_revision}}
    (job / "package/request.json").write_text(json.dumps(request))
    (job / "package/COPY_ASSIGNMENT.txt").write_text("Frozen provider-free test assignment")
    original = CodexExecAttempt.model_validate(text_attempt.model_dump(mode="python") | {
        "attempt_id": uuid4(), "domain": "image", "job_id": job_id, "operation_key": "image:synthetic",
        "reserved_image_outputs": 1, "image_budget_state": "reserved", "validation_plan_hash": None,
        "package_hash": package_tree_hash(job, max_total_bytes=2_000_000), "request_hash": "a" * 64})
    unknown = transition_exec_attempt(original, state="outcome_unknown", process_id=55556,
                                     process_group_id=55556, process_birth_identity="synthetic-cli")
    _insert_attempt_row(supervisor, original, unknown)
    private = supervisor.private_root / "attempts" / str(unknown.attempt_id)
    today = datetime.now(UTC).date()
    session = uuid4()
    rollout = supervisor.codex_home / "sessions" / today.strftime("%Y/%m/%d") / f"rollout-synthetic-{session}.jsonl"
    write_readonly_turn(job, supervisor.source_root, private, rollout, session)
    with closing(supervisor._connect()) as connection:
        connection.execute("UPDATE exec_attempts SET project_home=?,job_root=?,private_dir=?,worker_pid=55555,worker_group_id=55555,worker_birth_identity='synthetic-worker' WHERE attempt_id=?",
            (str(home), str(job), str(private), str(unknown.attempt_id)))
        connection.execute("INSERT INTO exec_slot VALUES (?,?)", (str(unknown.attempt_id), "image"))
    monkeypatch.setattr(supervisor, "_process_group_exists", lambda group: False)
    def absent(pid, signal):
        assert pid in (55555, 55556) and signal == 0
        raise ProcessLookupError(pid)
    monkeypatch.setattr(owner.os, "kill", absent)
    return unknown, private, job, rollout, session


def test_postmortem_settles_only_exact_attempt_and_retains_original_unknown(supervisor, recoverable):
    unknown, private, job, rollout, session = recoverable
    original = supervisor._row(unknown.attempt_id)["status_json"]
    other = CodexExecAttempt.model_validate(unknown.model_dump(mode="python") | {
        "attempt_id": uuid4(), "job_id": "ij_" + uuid4().hex, "operation_key": "image:other"})
    _insert_attempt_row(supervisor, other, other)
    with closing(supervisor._connect()) as connection:
        connection.execute("INSERT INTO exec_slot VALUES (?,?)", (str(other.attempt_id), "image"))
    hashes = {path: path.read_bytes() for path in [private / "stdout.jsonl", private / "stderr.log", rollout]}
    result = supervisor.recover_no_remote_dispatch(unknown)
    assert result.state == "settled" and result.attempt.terminal_result == "no_remote_dispatch"
    assert result.attempt.session_id == session and result.attempt.process_exit_code is None
    assert result.attempt.image_budget_state == "released" and result.receipt is None
    assert supervisor._load(supervisor._row(other.attempt_id)).attempt == other
    assert all(path.read_bytes() == content for path, content in hashes.items())
    assert list((job / "delivery").iterdir()) == []
    with closing(supervisor._connect()) as connection:
        record = connection.execute("SELECT * FROM exec_recovery_evidence WHERE attempt_id=?", (str(unknown.attempt_id),)).fetchone()
        assert record["original_status_json"] == original
        assert json.loads(record["proof_json"])["proof"]["observedCliExitCode"] is None
        assert [row[0] for row in connection.execute("SELECT attempt_id FROM exec_slot")] == [str(other.attempt_id)]
        assert connection.execute("SELECT * FROM exec_process_exits").fetchall() == []
    with pytest.raises(ValueError):
        supervisor.recover_no_remote_dispatch(unknown)


@pytest.mark.parametrize("defect", ["changed-package", "stderr", "delivery", "validator", "live-group", "live-pid",
                                    "stale-snapshot", "ambiguous-session", "missing-session"])
def test_recovery_refuses_ambiguity_without_any_settlement(supervisor, recoverable, monkeypatch, defect):
    import codex_exec_supervisor_recovery as owner
    unknown, private, job, rollout, session = recoverable
    requested = unknown
    if defect == "changed-package": (job / "package/request.json").write_text("{}")
    elif defect == "stderr": (private / "stderr.log").write_text("unaccounted CLI diagnostic")
    elif defect == "delivery": (job / "delivery/completion.json").write_text("{}")
    elif defect == "validator":
        with closing(supervisor._connect()) as connection:
            connection.execute("INSERT INTO exec_validation_process VALUES (?,?,'spawn_intent',NULL,NULL,NULL,0)",
                               (str(unknown.attempt_id), "synthetic"))
    elif defect == "live-group": monkeypatch.setattr(supervisor, "_process_group_exists", lambda _group: True)
    elif defect == "live-pid": monkeypatch.setattr(owner.os, "kill", lambda *_args: None)
    elif defect == "stale-snapshot": requested = transition_exec_attempt(unknown, session_id=uuid4())
    elif defect == "ambiguous-session": (rollout.parent / f"rollout-duplicate-{session}.jsonl").write_bytes(rollout.read_bytes())
    elif defect == "missing-session": rollout.unlink()
    with pytest.raises((ValueError, OSError)):
        supervisor.recover_no_remote_dispatch(requested)
    assert supervisor._load(supervisor._row(unknown.attempt_id)).attempt == unknown
    with closing(supervisor._connect()) as connection:
        assert connection.execute("SELECT * FROM exec_recovery_evidence").fetchall() == []
        assert connection.execute("SELECT * FROM exec_slot WHERE attempt_id=?", (str(unknown.attempt_id),)).fetchone()
