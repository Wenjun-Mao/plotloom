"""Shared pause owner must fence exact UNKNOWN admissions without redispatch."""
from contextlib import contextmanager
from uuid import uuid4

import pytest

from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_exec_staged import admit_reserved_codex_exec_once
from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.exceptions import InvalidTransitionError
from tests.test_autopilot_exec_staged import prepared
from tests.autopilot_seed_fixtures import run_facts


@contextmanager
def lost_ack(tmp_path, monkeypatch):
    with prepared(tmp_path, monkeypatch) as (_storage, registry, service, store, view, checkpoint, attempt, kwargs, calls):
        admitted = []
        def lost(value):
            admitted.append(value)
            raise OSError("synthetic acknowledgment lost after host retention")
        monkeypatch.setattr(registry, "codex_exec_admit", lost)
        with pytest.raises(OSError, match="acknowledgment"):
            admit_reserved_codex_exec_once(store, registry, view, service.claim, checkpoint,
                expected_attempt=attempt, expected_run_revision=view.revision, **kwargs)
        unknown, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, "outline")
        assert unknown.state == "outcome_unknown" and receipt is None and len(admitted) == 1
        for method in ("codex_exec_admit", "codex_exec_status", "codex_exec_resume"):
            monkeypatch.setattr(registry, method, lambda *_args: pytest.fail("pause dispatched, polled or resumed"))
        current = store.repository.autopilot.current(view.project_id)
        yield registry, service, store, current, unknown, admitted[0], calls


def test_pause_unknown_project_fences_retained_unstarted_host_without_changing_project_fact(tmp_path, monkeypatch):
    with lost_ack(tmp_path, monkeypatch) as (registry, service, store, view, unknown, intent, calls):
        parked = transition_exec_attempt(intent, state="queued")
        requests = []
        def suspend(value):
            requests.append(value)
            return CodexExecHostStatus(state="queued", attempt=parked, dispatchEnabled=False)
        monkeypatch.setattr(registry, "codex_exec_suspend", suspend)
        result = service.control(view.project_id, RunControlRequest(expected_revision=view.revision, action="pause"))
        assert result.state == "paused" and result.revision == view.revision + 1
        assert requests == [unknown] and not calls
        assert store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, "outline") == (unknown, None)


@pytest.mark.parametrize("state", ["running", "validating", "outcome_unknown"])
def test_pause_unknown_project_preserves_typed_active_host_snapshot(tmp_path, monkeypatch, state):
    with lost_ack(tmp_path, monkeypatch) as (registry, service, store, view, unknown, intent, calls):
        running = transition_exec_attempt(intent, state="running", process_id=54321,
            process_group_id=54321, process_birth_identity="synthetic-owned-process", session_id=uuid4())
        active = running if state == "running" else transition_exec_attempt(running, state=state)
        status = CodexExecHostStatus(state=state, attempt=active)
        received = []
        def suspend(value):
            received.append(value)
            return status
        monkeypatch.setattr(registry, "codex_exec_suspend", suspend)
        result = service.control(view.project_id, RunControlRequest(expected_revision=view.revision, action="pause"))
        assert result.state == "paused" and received == [unknown] and not calls
        assert status.attempt == active and status.receipt is None
        assert store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, "outline") == (unknown, None)


@pytest.mark.parametrize("failure", ["missing", "enabled", "foreign", "exception"])
def test_pause_unknown_unacknowledged_fence_rolls_back_project_control(tmp_path, monkeypatch, failure):
    with lost_ack(tmp_path, monkeypatch) as (registry, service, store, view, unknown, intent, calls):
        requests = []
        def suspend(value):
            requests.append(value)
            if failure == "exception":
                raise OSError("synthetic suspend failed")
            if failure == "missing":
                return CodexExecHostStatus(state="not_found")
            queued = transition_exec_attempt(intent, state="queued")
            if failure == "foreign":
                queued = queued.model_copy(update={"attempt_id": uuid4()})
            return CodexExecHostStatus(state="queued", attempt=queued, dispatchEnabled=failure == "enabled")
        monkeypatch.setattr(registry, "codex_exec_suspend", suspend)
        with pytest.raises((InvalidTransitionError, OSError)):
            service.control(view.project_id, RunControlRequest(expected_revision=view.revision, action="pause"))
        retained = store.repository.autopilot.current(view.project_id)
        assert run_facts(retained) == run_facts(view) and requests == [unknown] and not calls
        assert store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, "outline") == (unknown, None)
