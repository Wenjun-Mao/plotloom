"""Finite FIFO capacity, exact pause identity and durable unknown reservations."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from uuid import uuid4

import pytest
from codex_exec_supervisor import CodexExecSupervisor
from codex_exec_supervisor_test_support import (
    _attempt,
    _insert_attempt_row,
    _prepared_text_job,
)

from plotloom.codex_exec_contracts import CodexExecAttempt, transition_exec_attempt
from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits


def _job(supervisor, *, domain="text", state="queued", enabled=True):
    attempt = CodexExecAttempt.model_validate(_attempt().model_dump(mode="python") | {
        "domain": domain, "reserved_image_outputs": int(domain == "image"),
        "image_budget_state": "reserved" if domain == "image" else "none",
        "job_id": ("ij_" if domain == "image" else "ch_") + uuid4().hex[:24],
    })
    current = transition_exec_attempt(attempt, state=state)
    _insert_attempt_row(supervisor, attempt, current)
    with closing(supervisor._connect()) as connection:
        if state == "queued":
            connection.execute("INSERT INTO exec_queue(attempt_id,enabled) VALUES (?,?)", (str(attempt.attempt_id), int(enabled)))
        else:
            connection.execute("INSERT INTO exec_slot(attempt_id,domain) VALUES (?,?)", (str(attempt.attempt_id), domain))
    return current


@pytest.mark.parametrize("drift", [{"maxProcesses": 5}, {"maxTextProcesses": 3},
    {"maxImageProcesses": 3}, {"maxQueuedJobs": 5}, {"maxProcesses": True},
    {"maxProcesses": 1}, {"maxQueuedJobs": 0}])
def test_pool_limits_are_strict_and_finite(drift):
    with pytest.raises(ValueError):
        CodexExecPoolLimits.model_validate(drift)


def test_fifo_skips_full_domain_and_retains_older_job_order(supervisor, monkeypatch):
    _job(supervisor, state="outcome_unknown")
    _job(supervisor, state="outcome_unknown")
    older_text = _job(supervisor)
    image = _job(supervisor, domain="image")
    launched = []
    monkeypatch.setattr(supervisor, "_start_worker", launched.append)

    assert supervisor._drain_queue() == image.attempt_id
    assert launched == [image.attempt_id]
    assert supervisor._load(supervisor._row(older_text.attempt_id)).state == "queued"
    with closing(supervisor._connect()) as connection:
        assert supervisor._capacity_counts(connection) == {"text": 2, "image": 1}
        ordered = connection.execute("SELECT attempt_id FROM exec_queue ORDER BY ordinal").fetchall()
        assert [row[0] for row in ordered] == [str(older_text.attempt_id), str(image.attempt_id)]


def test_two_host_instances_cannot_exceed_global_or_domain_caps(supervisor, monkeypatch):
    jobs = [_job(supervisor, domain=domain) for domain in ("text", "image", "text", "image")]
    other = CodexExecSupervisor(supervisor.executable, source_root=supervisor.source_root,
        outputs_root=supervisor.outputs_root, private_root=supervisor.private_root)
    launched = []
    for host in (supervisor, other):
        monkeypatch.setattr(host, "_start_worker", launched.append)
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda host: host._drain_queue(), [supervisor, other] * 4))
    assert set(item for item in results if item is not None) == {job.attempt_id for job in jobs}
    assert len(launched) == len(set(launched)) == 4
    with closing(supervisor._connect()) as connection:
        assert supervisor._capacity_counts(connection) == {"text": 2, "image": 2}


def test_full_queue_deferral_leaves_exact_attempt_admissible(supervisor, tmp_path, monkeypatch):
    for domain in ("text", "text", "image", "image"):
        _job(supervisor, domain=domain, state="outcome_unknown")
    waiting = [_job(supervisor) for _ in range(4)]
    _exchange, _request, _pin, job_root, attempt, _profile = _prepared_text_job(supervisor, tmp_path)
    launched = []
    monkeypatch.setattr(supervisor, "_start_worker", launched.append)
    status = supervisor.admit(attempt)
    assert status.state == "not_found" and status.capacity_deferred
    assert supervisor._row(attempt.attempt_id) is None
    assert not (supervisor.private_root / "attempts" / str(attempt.attempt_id)).exists()
    assert not any((job_root / "delivery").iterdir())
    assert not launched
    supervisor.cancel(waiting[0])
    admitted = supervisor.admit(attempt)
    assert admitted.state == "queued" and admitted.attempt.attempt_id == attempt.attempt_id
    assert not admitted.capacity_deferred


def test_pause_queued_resume_preserves_identity_and_order(supervisor, monkeypatch):
    job = _job(supervisor)
    with closing(supervisor._connect()) as connection:
        ordinal = connection.execute("SELECT ordinal FROM exec_queue WHERE attempt_id=?", (str(job.attempt_id),)).fetchone()[0]
    launched = []
    monkeypatch.setattr(supervisor, "_start_worker", launched.append)
    paused = supervisor.suspend(job)
    assert paused.state == "queued" and paused.dispatch_enabled is False
    assert supervisor._drain_queue() is None
    resumed = supervisor.resume(job)
    assert resumed.state == "spawn_intent" and resumed.dispatch_enabled is True
    assert launched == [job.attempt_id]
    with closing(supervisor._connect()) as connection:
        assert connection.execute("SELECT ordinal FROM exec_queue WHERE attempt_id=?", (str(job.attempt_id),)).fetchone()[0] == ordinal


def test_pause_fences_delayed_initial_admission(supervisor, tmp_path, monkeypatch):
    _exchange, _request, _pin, _root, attempt, _profile = _prepared_text_job(supervisor, tmp_path)
    monkeypatch.setattr(supervisor, "_start_worker", lambda _id: pytest.fail("pause cannot launch"))
    paused = supervisor.suspend(attempt)
    assert paused.state == "queued" and paused.dispatch_enabled is False
    assert supervisor.admit(attempt) == paused


def test_unregistered_grant_parks_without_releasing_job_budget(supervisor, monkeypatch):
    job = _job(supervisor, domain="image")
    monkeypatch.setattr(supervisor, "_start_worker", lambda _id: None)
    supervisor._drain_queue()
    paused = supervisor.suspend(job)
    assert paused.state == "queued" and paused.attempt.image_budget_state == "reserved"
    with closing(supervisor._connect()) as connection:
        assert supervisor._capacity_counts(connection) == {"text": 0, "image": 0}


def test_registered_spawn_intent_without_worker_proof_stays_unknown(supervisor, monkeypatch):
    job = _job(supervisor)
    monkeypatch.setattr(supervisor, "_start_worker", lambda _id: None)
    supervisor._drain_queue()
    with closing(supervisor._connect()) as connection:
        connection.execute("UPDATE exec_attempts SET worker_pid=98765434,worker_group_id=98765434,worker_birth_identity='missing' WHERE attempt_id=?", (str(job.attempt_id),))
    assert supervisor.suspend(job).state == "spawn_intent"
    monkeypatch.setattr(supervisor, "_owns_worker", lambda _row: False)
    assert supervisor.status(job.attempt_id).state == "outcome_unknown"
    with closing(supervisor._connect()) as connection:
        assert supervisor._capacity_counts(connection) == {"text": 1, "image": 0}


def test_original_worker_can_prove_pre_spawn_parking(supervisor, monkeypatch):
    job = _job(supervisor)
    monkeypatch.setattr(supervisor, "_start_worker", lambda _id: None)
    supervisor._drain_queue()
    identity = (98765435, 98765435, "original-worker")
    with closing(supervisor._connect()) as connection:
        connection.execute("UPDATE exec_attempts SET worker_pid=?,worker_group_id=?,worker_birth_identity=? WHERE attempt_id=?", (*identity, str(job.attempt_id)))
    assert supervisor.suspend(job).state == "spawn_intent"
    with closing(supervisor._connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM exec_attempts WHERE attempt_id=?", (str(job.attempt_id),)).fetchone()
        current = CodexExecAttempt.model_validate_json(row["status_json"])
        assert supervisor._park_before_spawn_in_transaction(connection, row, current, worker_identity=identity)
        connection.commit()
    assert supervisor._load(supervisor._row(job.attempt_id)).state == "queued"
    assert supervisor._row(job.attempt_id)["worker_pid"] is None


def test_full_enabled_queue_resume_defers_original_suspended_identity(supervisor, monkeypatch):
    for _ in range(2):
        _job(supervisor, state="outcome_unknown")
    paused = _job(supervisor, enabled=False)
    for _ in range(4):
        _job(supervisor)
    monkeypatch.setattr(supervisor, "_start_worker", lambda _id: pytest.fail("no text capacity"))
    status = supervisor.resume(paused)
    assert status.capacity_deferred and status.attempt.attempt_id == paused.attempt_id
    assert status.dispatch_enabled is False


def test_cancel_queued_image_releases_budget_and_exact_queue_record(supervisor):
    job = _job(supervisor, domain="image")
    result = supervisor.cancel(job)
    assert result.state == "settled" and result.attempt.terminal_result == "not_started"
    assert result.attempt.image_budget_state == "released"
    with closing(supervisor._connect()) as connection:
        assert connection.execute("SELECT * FROM exec_queue WHERE attempt_id=?", (str(job.attempt_id),)).fetchone() is None


def test_legacy_unknown_capacity_conversion_preserves_exact_json(supervisor, monkeypatch):
    job = _job(supervisor, state="outcome_unknown")
    before = supervisor._row(job.attempt_id)
    with closing(supervisor._connect()) as connection:
        connection.execute("DROP TABLE exec_slot")
        connection.execute("CREATE TABLE exec_slot(slot_id INTEGER PRIMARY KEY CHECK(slot_id=1),attempt_id TEXT NOT NULL)")
        connection.execute("INSERT INTO exec_slot VALUES(1,?)", (str(job.attempt_id),))
    monkeypatch.setattr(supervisor, "_process_group_exists", lambda _id: False)
    supervisor._initialize()
    after = supervisor._row(job.attempt_id)
    assert (after["attempt_json"], after["status_json"], after["receipt_json"]) == (before["attempt_json"], before["status_json"], before["receipt_json"])
    with closing(supervisor._connect()) as connection:
        assert supervisor._capacity_counts(connection) == {"text": 1, "image": 0}


@pytest.mark.parametrize("spawn_state", ["spawn_intent", "running"])
def test_legacy_conversion_refuses_unresolved_or_live_orphan_validator(supervisor, monkeypatch, spawn_state):
    job = _job(supervisor, state="outcome_unknown")
    before = tuple(supervisor._row(job.attempt_id))
    group = 98765436 if spawn_state == "running" else None
    with closing(supervisor._connect()) as connection:
        connection.execute("DROP TABLE exec_slot")
        connection.execute("CREATE TABLE exec_slot(slot_id INTEGER PRIMARY KEY CHECK(slot_id=1),attempt_id TEXT NOT NULL)")
        connection.execute("INSERT INTO exec_slot VALUES(1,?)", (str(job.attempt_id),))
        connection.execute("INSERT INTO exec_validation_process VALUES (?,?,?,?,?,?,0)",
            (str(job.attempt_id), "validate", spawn_state, group, group, "validator-owner" if group else None))
        validator_before = tuple(connection.execute("SELECT * FROM exec_validation_process").fetchone())
    monkeypatch.setattr(supervisor, "_process_group_exists", lambda candidate: candidate == group)
    with pytest.raises(ValueError, match="resolved validator quiescence"):
        supervisor._initialize()
    assert tuple(supervisor._row(job.attempt_id)) == before
    with closing(supervisor._connect()) as connection:
        assert "slot_id" in connection.execute("SELECT sql FROM sqlite_master WHERE name='exec_slot'").fetchone()[0]
        assert tuple(connection.execute("SELECT * FROM exec_validation_process").fetchone()) == validator_before
