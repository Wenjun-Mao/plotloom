"""Finite namespace owner regressions; no native generation or acceptance."""
from contextlib import closing
from uuid import uuid4

import pytest
from codex_exec_supervisor import CodexExecSupervisor
from codex_exec_supervisor_errors import CodexExecSupervisorError
from plotloom.codex_exec_contracts import transition_exec_attempt
from tests.services.creator_workbench.qualification_fixtures import finite  # noqa: F401


def test_actual_owner_reservation_freezes_before_original_admission(finite):
    host = finite.host
    with pytest.raises(CodexExecSupervisorError, match='unfrozen'):
        host.admit(transition_exec_attempt(finite.attempt, state='spawn_intent'))
    host.freeze_qualification_attempt(finite.attempt)
    result = host.admit(transition_exec_attempt(finite.attempt, state='spawn_intent'))
    assert result.attempt.attempt_id == finite.attempt.attempt_id
    assert finite.starts == [finite.attempt.attempt_id]


def test_restart_keeps_binding_and_does_not_renew_activation(finite):
    restarted = CodexExecSupervisor(finite.host.executable, **finite.kwargs)
    with pytest.raises(CodexExecSupervisorError, match='one-shot'):
        restarted.activate_qualification(prior_serial_receipt_sha256='c'*64)
    with pytest.raises(CodexExecSupervisorError, match='pin is required'):
        CodexExecSupervisor(finite.host.executable, **(finite.kwargs | {'namespace_binding_sha256': None}))


def test_registered_role_and_run_cannot_be_replaced(finite):
    with pytest.raises(CodexExecSupervisorError):
        finite.host.register_qualification_project(finite.registration.model_copy(update={'run_id':uuid4()}))
    with pytest.raises(CodexExecSupervisorError, match='run/profile/source'):
        finite.host.freeze_qualification_attempt(finite.attempt.model_copy(update={'run_id':uuid4()}))


def test_halt_blocks_new_work_but_not_exact_disabled_parking_or_status(finite):
    host = finite.host
    host.freeze_qualification_attempt(finite.attempt)
    host.halt_qualification('synthetic_stop')
    attempt = transition_exec_attempt(finite.attempt, state='spawn_intent')
    with pytest.raises(CodexExecSupervisorError, match='held'):
        host.admit(attempt)
    parked = host.suspend(attempt)
    assert parked.dispatch_enabled is False
    assert host.status(attempt.attempt_id).attempt.attempt_id == attempt.attempt_id
    assert finite.starts == []


def test_expiry_is_durable_and_does_not_block_settlement(finite, monkeypatch):
    import codex_exec_supervisor_qualification_admission as owner
    host = finite.host
    host.freeze_qualification_attempt(finite.attempt)
    monkeypatch.setattr(owner.time, 'time_ns', lambda:finite.activation.started_wall_ns+5401*10**9)
    monkeypatch.setattr(owner.time, 'monotonic_ns', lambda:finite.activation.started_monotonic_ns+5401*10**9)
    with closing(host._connect()) as connection:
        connection.execute('BEGIN IMMEDIATE')
        assert host._grant_one_in_transaction(connection) is None
        connection.commit()
        assert connection.execute('SELECT halt_reason FROM exec_qualification_arm').fetchone()[0]
    assert host.suspend(transition_exec_attempt(finite.attempt,state='spawn_intent')).dispatch_enabled is False
    assert host.status(finite.attempt.attempt_id).attempt is not None
