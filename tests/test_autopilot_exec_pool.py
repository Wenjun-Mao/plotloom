"""Project-owned queue, known capacity waits and original-identity pause/resume."""
from contextlib import closing

from plotloom.autopilot_contracts import RunControlRequest
from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from tests.autopilot_controller_fixtures import environment, run_text


def _current(storage, project_id):
    with closing(storage.projects.open(project_id)) as store:
        return store.repository.autopilot.current(project_id)


def _attempt(storage, run):
    with closing(storage.projects.open(run.project_id)) as store:
        return store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, "outline")[0]


def test_known_capacity_deferral_keeps_one_original_attempt_then_clears_when_admitted(tmp_path, monkeypatch):
    storage, registry, service, run, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    received = []
    host = registry._codex_exec_test_host
    original_admit = host.admit
    def admit(attempt):
        received.append(attempt.attempt_id)
        if len(received) == 1:
            return CodexExecHostStatus(state="not_found", capacityDeferred=True)
        return original_admit(attempt)
    monkeypatch.setattr(registry, "codex_exec_admit", admit)
    try:
        assert service.acquire_controller()
        for _ in range(3):
            service.step(run.project_id)
        waiting = _current(storage, run.project_id)
        original = _attempt(storage, run)
        assert waiting.state == "waiting" and waiting.blocker["code"] == "codex_exec_capacity_deferred"
        assert original.state == "spawn_intent" and not calls
        service.step(run.project_id)
        admitted = _current(storage, run.project_id)
        current_attempt = _attempt(storage, run)
        assert admitted.state == "running" and admitted.blocker is None
        assert current_attempt.state == "running" and current_attempt.attempt_id == original.attempt_id
        assert received == [original.attempt_id, original.attempt_id]
        assert len(calls) == 1
    finally:
        service.close()


def test_queued_pause_resume_uses_original_frozen_job_without_dispatch_while_paused(tmp_path, monkeypatch):
    storage, registry, service, run, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    host = registry._codex_exec_test_host
    original_admit = host.admit
    queue_requests, resume_requests, suspend_requests = [], [], []
    def enqueue(attempt):
        queue_requests.append(attempt.attempt_id)
        queued = transition_exec_attempt(attempt, state="queued")
        status = CodexExecHostStatus(state="queued", attempt=queued, dispatchEnabled=True)
        host.statuses[str(attempt.attempt_id)] = status
        return status
    def suspend(attempt):
        suspend_requests.append(attempt.attempt_id)
        current = host.statuses[str(attempt.attempt_id)].attempt
        status = CodexExecHostStatus(state="queued", attempt=current, dispatchEnabled=False)
        host.statuses[str(attempt.attempt_id)] = status
        return status
    def resume(attempt):
        resume_requests.append(attempt.attempt_id)
        queued = host.statuses.pop(str(attempt.attempt_id)).attempt
        return original_admit(queued)
    monkeypatch.setattr(registry, "codex_exec_admit", enqueue)
    monkeypatch.setattr(registry, "codex_exec_suspend", suspend)
    monkeypatch.setattr(registry, "codex_exec_resume", resume)
    try:
        assert service.acquire_controller()
        for _ in range(3):
            service.step(run.project_id)
        original = _attempt(storage, run)
        assert original.state == "queued" and not calls
        current = _current(storage, run.project_id)
        service.control(run.project_id, RunControlRequest(expected_revision=current.revision, action="pause"))
        service.step(run.project_id)
        paused = _current(storage, run.project_id)
        assert paused.state == "paused" and not calls and not resume_requests
        assert suspend_requests and set(suspend_requests) == {original.attempt_id}
        service.control(run.project_id, RunControlRequest(expected_revision=paused.revision, action="resume"))
        service.step(run.project_id)
        resumed = _attempt(storage, run)
        assert resumed.state == "running" and resumed.attempt_id == original.attempt_id
        assert queue_requests == resume_requests == [original.attempt_id]
        assert calls == [original.job_id]
    finally:
        service.close()


def test_known_queued_image_cancel_releases_proposal_and_project_lifecycle(tmp_path, monkeypatch):
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch)
    host = registry._codex_exec_test_host
    original_admit, original_cancel = host.admit, host.cancel
    def enqueue(attempt):
        if attempt.domain != "image":
            return original_admit(attempt)
        queued = transition_exec_attempt(attempt, state="queued")
        status = CodexExecHostStatus(state="queued", attempt=queued, dispatchEnabled=True)
        host.statuses[str(attempt.attempt_id)] = status
        return status
    def cancel(attempt):
        if attempt.domain != "image":
            return original_cancel(attempt)
        settled = transition_exec_attempt(attempt, state="settled", terminal_result="not_started",
            remote_tool_state="not_applicable", evidence_hash="f" * 64, image_budget_state="released")
        status = CodexExecHostStatus(state="settled", attempt=settled)
        host.statuses[str(attempt.attempt_id)] = status
        return status
    suspended = []
    def reconcile_suspended(attempt):
        suspended.append(attempt.attempt_id)
        return host.statuses[str(attempt.attempt_id)]
    monkeypatch.setattr(registry, "codex_exec_admit", enqueue)
    monkeypatch.setattr(registry, "codex_exec_cancel", cancel)
    monkeypatch.setattr(registry, "codex_exec_suspend", reconcile_suspended)
    try:
        current = run_text(service, run)
        for _ in range(3):
            service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            current = store.repository.autopilot.current(run.project_id)
            checkpoint = next(item for item in current.checkpoints if item["evidence"]["owner"] == "character-reference")
            attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, checkpoint["operationKey"])
            assert attempt.state == "queued" and not host.image_calls
        service.control(run.project_id, RunControlRequest(expected_revision=current.revision, action="cancel"))
        service.step(run.project_id)
        assert suspended == [attempt.attempt_id]
        with closing(storage.projects.open(run.project_id)) as store:
            context = store.media.character_reference_proposal_delivery_context(run.project_id, attempt.job_id)
            assert context["state"] == "cancelled"
            settled, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, checkpoint["operationKey"])
            assert settled.state == "settled" and settled.image_budget_state == "released"
            assert store.repository.autopilot.current(run.project_id).state == "cancelled"
        assert not host.image_calls
        storage.projects.close_project(run.project_id)
    finally:
        service.close()
