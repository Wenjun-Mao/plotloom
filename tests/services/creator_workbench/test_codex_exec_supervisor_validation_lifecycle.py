"""Durable spawn, cancellation and crash-window guards for trusted validators."""
import os
from contextlib import closing

import pytest
from codex_exec_supervisor_test_support import _attempt, _insert_attempt_row

from plotloom.codex_exec_contracts import CodexExecAttempt, transition_exec_attempt


def _owned_running_attempt(supervisor):
    reserved = CodexExecAttempt.model_validate(_attempt().model_dump(mode="python") | {"plotloom_code_revision": "a" * 40, "validation_plan_hash": "b" * 64})
    running = transition_exec_attempt(
        reserved,
        state="running",
        process_id=43210,
        process_group_id=43210,
        process_birth_identity="fixture-cli-process",
    )
    from uuid import uuid4
    running = transition_exec_attempt(running, state="validating", session_id=uuid4())
    _insert_attempt_row(supervisor, reserved, running)
    worker_group, worker_birth = supervisor._process_identity(os.getpid())
    with closing(supervisor._connect()) as connection:
        connection.execute(
            "UPDATE exec_attempts SET worker_pid=?,worker_group_id=?,worker_birth_identity=? WHERE attempt_id=?",
            (os.getpid(), worker_group, worker_birth, str(running.attempt_id)),
        )
    return reserved, running


def test_validator_spawn_intent_is_committed_before_popen_and_process_runs_outside_transaction(
    monkeypatch, supervisor,
):
    import codex_exec_supervisor_validation_process as validation_module
    real_popen = validation_module.subprocess.Popen

    _reserved, running = _owned_running_attempt(supervisor)
    fake_pid = 98765431
    real_identity = supervisor._process_identity
    monkeypatch.setattr(
        supervisor,
        "_process_identity",
        lambda pid: (fake_pid, "fixture-validator") if pid == fake_pid else real_identity(pid),
    )

    class FakeProcess:
        pid = fake_pid

    def fake_popen(command, *args, **kwargs):
        if command != ["validator"]:
            return real_popen(command, *args, **kwargs)
        row = supervisor._active_validation_process(running.attempt_id)
        assert row is not None
        assert row["spawn_state"] == "spawn_intent"
        with closing(supervisor._connect()) as connection:
            assert not connection.in_transaction
        return FakeProcess()

    monkeypatch.setattr(validation_module.subprocess, "Popen", fake_popen)
    process, identity = supervisor._spawn_validation_process(
        running, "validate", ["validator"], {}, supervisor.private_root, None, None,
    )

    row = supervisor._active_validation_process(running.attempt_id)
    assert process.pid == fake_pid
    assert row["spawn_state"] == "running"
    assert (row["process_id"], row["process_group_id"], row["process_birth_identity"]) == identity
    with closing(supervisor._connect()) as connection:
        connection.execute("DELETE FROM exec_validation_process WHERE attempt_id=?", (str(running.attempt_id),))


def test_cancel_between_spawn_intent_and_launch_clears_only_the_unlaunched_intent(supervisor):
    _reserved, running = _owned_running_attempt(supervisor)
    supervisor._record_validation_spawn_intent(running, "validate")

    cancelled = supervisor.cancel(running)

    assert cancelled.state == "cancel_requested"
    assert not supervisor._validation_launch_is_allowed(running, "validate")
    assert supervisor._active_validation_process(running.attempt_id) is None
    assert supervisor._load(supervisor._row(running.attempt_id)).state == "cancel_requested"


def test_cancel_after_launch_fence_preserves_exact_owner_registration(supervisor, monkeypatch):
    _reserved, running = _owned_running_attempt(supervisor)
    supervisor._record_validation_spawn_intent(running, "render")
    assert supervisor._validation_launch_is_allowed(running, "render")

    cancelled = supervisor.cancel(running)
    fake_pid = 98765432
    real_identity = supervisor._process_identity
    monkeypatch.setattr(
        supervisor,
        "_process_identity",
        lambda pid: (fake_pid, "fixture-validator") if pid == fake_pid else real_identity(pid),
    )
    state = supervisor._register_validation_process(
        running, "render", (fake_pid, fake_pid, "fixture-validator"),
    )

    owner = supervisor._active_validation_process(running.attempt_id)
    assert cancelled.state == "cancel_requested"
    assert state == "cancel_requested"
    assert owner["spawn_state"] == "running"
    assert owner["process_group_id"] == fake_pid
    with closing(supervisor._connect()) as connection:
        connection.execute("DELETE FROM exec_validation_process WHERE attempt_id=?", (str(running.attempt_id),))


def test_worker_loss_with_unresolved_spawn_intent_stays_unknown_and_is_never_restarted(
    monkeypatch, supervisor,
):
    _reserved, running = _owned_running_attempt(supervisor)
    supervisor._record_validation_spawn_intent(running, "validate")
    with closing(supervisor._connect()) as connection:
        connection.execute(
            "UPDATE exec_attempts SET worker_pid=?,worker_group_id=?,worker_birth_identity=? WHERE attempt_id=?",
            (98765433, 98765433, "dead-worker", str(running.attempt_id)),
        )
    monkeypatch.setattr(supervisor, "_start_worker", lambda _attempt_id: pytest.fail("must not restart"))

    status = supervisor.status(running.attempt_id)

    assert status.state == "outcome_unknown"
    assert supervisor._active_validation_process(running.attempt_id)["spawn_state"] == "spawn_intent"


def test_not_started_settlement_cannot_consume_a_validator_spawn_intent(supervisor):
    reserved = _attempt()
    cancelled = transition_exec_attempt(reserved, state="cancel_requested")
    _insert_attempt_row(supervisor, reserved, cancelled)
    with closing(supervisor._connect()) as connection:
        connection.execute(
            "INSERT INTO exec_validation_process "
            "(attempt_id,step_id,spawn_state,process_id,process_group_id,process_birth_identity,updated_at) "
            "VALUES (?, 'validate', 'spawn_intent', NULL,NULL,NULL,0)",
            (str(reserved.attempt_id),),
        )
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM exec_attempts WHERE attempt_id=?", (str(reserved.attempt_id),),
        ).fetchone()
        settled = supervisor._settle_not_started_in_transaction(connection, row, cancelled)
        connection.commit()

    assert settled.state == "cancel_requested"
    assert settled.process_id is None
    assert supervisor._active_validation_process(reserved.attempt_id)["spawn_state"] == "spawn_intent"
