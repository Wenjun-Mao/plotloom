"""Exact bridge execution scope and prospective explicit-cancel settlement."""
from contextlib import closing
from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

import pytest

from plotloom.autopilot_contracts import OperationScope, RunControlRequest
from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.project.autopilot_exec_attempts import AutopilotExecPersistence
from tests.autopilot_controller_fixtures import environment, run_text
from tests.test_autopilot_continuation import origin_rows, request_for


def inject_failure(registry, *, kind="failure", classification="transient"):
    host, admit, failed = registry._codex_exec_test_host, registry.codex_exec_admit, []

    def fail(attempt):
        if attempt.operation_key != "bridge-intent" or failed:
            return admit(attempt)
        value = attempt if kind == "not_started" else admit(attempt).attempt
        facts = {"state": "failed", "terminal_result": kind, "remote_tool_state": "not_applicable", "evidence_hash": "f" * 64}
        if kind == "failure":
            facts.update(process_exit_code=1, execution_failure=classification)
        value = transition_exec_attempt(value, **facts)
        failed.append(value)
        host.pending.discard(str(value.attempt_id))
        status = CodexExecHostStatus(state="failed", attempt=value, localExecutionStopped=True)
        host.statuses[str(value.attempt_id)] = status
        return status

    registry.codex_exec_admit = fail
    return failed


def reach_failed(tmp_path, monkeypatch, *, kind="failure", classification="transient"):
    storage, registry, service, run, calls = environment(tmp_path, monkeypatch, limits={"automatic_retry_limit": 0})
    failed = inject_failure(registry, kind=kind, classification=classification)
    assert service.acquire_controller()
    for _ in range(48):
        service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            current = store.repository.autopilot.current(run.project_id)
        failed_checkpoint = next((item for item in current.checkpoints if item["operationKey"] == "bridge-intent"), None)
        if current.state == "blocked" or failed_checkpoint is not None and failed_checkpoint["state"] == "failed":
            assert len(failed) == 1
            return storage, registry, service, current, calls, failed[0]
    service.close()
    pytest.fail("fixture did not reach its known stopped bridge failure")


@pytest.mark.parametrize("kind", ["failure", "not_started"])
def test_explicit_cancel_settles_exact_persisted_failure_without_receipt_or_new_job(tmp_path, monkeypatch, kind):
    storage, registry, service, current, calls, attempt = reach_failed(tmp_path, monkeypatch, kind=kind, classification="permission")
    try:
        with closing(storage.projects.open(current.project_id)) as store:
            before = origin_rows(store, current.id)
            original_calls = list(calls)
        stopped = service.control(current.project_id, RunControlRequest(expected_revision=current.revision, action="cancel"))
        assert stopped.state == "cancelled" and calls == original_calls
        with closing(storage.projects.open(current.project_id)) as store:
            data = store.repository.production_bridge_intent.load_job(current.project_id, attempt.job_id)
            assert data["status"] == "failed" and data["responseEvidence"] is None
            assert origin_rows(store, current.id) == before
            retained, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(current.id, "bridge-intent")
            assert retained == attempt and receipt is None
        assert not registry._codex_exec_test_host.image_calls
    finally:
        service.close()


@pytest.mark.parametrize("reply", ["unknown", "unproven_stop", "unpersisted_failure", "mismatch", "lost_ack", "takeover"])
def test_uncertain_or_unbound_cancel_never_settles_bridge_publication(tmp_path, monkeypatch, reply):
    storage, registry, service, current, calls, attempt = reach_failed(tmp_path, monkeypatch)
    try:
        original_calls = list(calls)
        original = registry.codex_exec_cancel

        def cancel(value):
            if reply == "lost_ack":
                raise OSError("synthetic lost cancellation acknowledgement")
            status = original(value)
            if reply == "unproven_stop":
                return status.model_copy(update={"local_execution_stopped": False})
            if reply == "unpersisted_failure":
                return status.model_copy(update={"attempt": status.attempt.model_copy(update={"process_exit_code": 2})})
            if reply == "mismatch":
                return status.model_copy(update={"attempt": status.attempt.model_copy(update={"attempt_id": uuid4()})})
            if reply == "unknown":
                unknown = status.attempt.model_copy(update={"state": "outcome_unknown", "terminal_result": None,
                    "remote_tool_state": None, "evidence_hash": None, "process_exit_code": None, "execution_failure": None})
                return CodexExecHostStatus(state="outcome_unknown", attempt=unknown)
            return status

        monkeypatch.setattr(registry, "codex_exec_cancel", cancel)
        request = RunControlRequest(expected_revision=current.revision, action="takeover" if reply == "takeover" else "cancel")
        if reply in {"mismatch", "lost_ack"}:
            with pytest.raises((InvalidTransitionError, OSError)):
                service.control(current.project_id, request)
        else:
            service.control(current.project_id, request)
        with closing(storage.projects.open(current.project_id)) as store:
            data = store.repository.production_bridge_intent.load_job(current.project_id, attempt.job_id)
            assert data["status"] == ("dispatched" if reply in {"mismatch", "lost_ack"} else "cancelled")
            assert data["responseEvidence"] is None
            if reply not in {"mismatch", "lost_ack", "takeover"}:
                # A later repeat cancel cannot rewrite an already-cancelled owner.
                monkeypatch.setattr(registry, "codex_exec_cancel", original)
                stopped = store.repository.autopilot.current(current.project_id)
                with pytest.raises(InvalidTransitionError, match="no longer automatically controllable"):
                    service.control(current.project_id, RunControlRequest(expected_revision=stopped.revision, action="cancel"))
                assert store.repository.production_bridge_intent.load_job(current.project_id, attempt.job_id)["status"] == "cancelled"
        assert calls == original_calls
    finally:
        service.close()


def test_transient_limit_zero_requires_explicit_cancel_and_new_continue(tmp_path, monkeypatch):
    storage, registry, service, current, calls, attempt = reach_failed(tmp_path, monkeypatch)
    try:
        assert current.policy.automatic_retry_limit == 0
        stopped = service.control(current.project_id, RunControlRequest(expected_revision=current.revision, action="cancel"))
        with closing(storage.projects.open(current.project_id)) as store:
            before = origin_rows(store, current.id)
            request = request_for(store, stopped)
        # Freeze this disposable text-only fixture's new policy before dispatch.
        from plotloom import autopilot_service
        freeze = autopilot_service.freeze_launch_policy
        with monkeypatch.context() as text_only:
            text_only.setattr(autopilot_service, "freeze_launch_policy", lambda *args:
                freeze(*args).model_copy(update={"early_reference_limit": 0}))
            child = service.continue_material(current.project_id, request)
        original_calls = list(calls)
        complete = run_text(service, child)
        assert len(complete.checkpoints) == 11
        assert calls[:len(original_calls)] == original_calls and len(calls) == len(original_calls) + 4
        assert len(calls) == len(set(calls)) and attempt.job_id not in calls[len(original_calls):]
        with closing(storage.projects.open(current.project_id)) as store:
            assert origin_rows(store, current.id) == before
        assert not registry._codex_exec_test_host.image_calls
    finally:
        service.close()


def test_exact_bridge_execution_retry_uses_install_scope_and_refuses_text_scope(tmp_path, monkeypatch):
    storage, registry, service, run, calls = environment(tmp_path, monkeypatch, limits={"automatic_retry_limit": 1})
    failed = inject_failure(registry)
    original = AutopilotExecPersistence._mark_exec_spawn_intent
    wrong_scope_refusals = []

    def mark(owner, *args, **kwargs):
        authority = owner.access.authority()
        if authority.scope == OperationScope.INSTALL:
            before = list(calls)
            wrong_access = replace(owner.access, authority=lambda: replace(authority, scope=OperationScope.TEXT))
            with patch.object(owner, "access", wrong_access), pytest.raises(InvalidTransitionError, match="scope"):
                original(owner, *args, **kwargs)
            assert calls == before
            wrong_scope_refusals.append(True)
        return original(owner, *args, **kwargs)

    monkeypatch.setattr(AutopilotExecPersistence, "_mark_exec_spawn_intent", mark)
    try:
        complete = run_text(service, run)
        rows = {item["operationKey"]: item for item in complete.checkpoints}
        assert rows["bridge-intent"]["state"] == "failed"
        assert rows["bridge-intent:retry:1"]["state"] == "adopted"
        assert len(failed) == 1 and wrong_scope_refusals and len(calls) == len(set(calls))
    finally:
        service.close()
