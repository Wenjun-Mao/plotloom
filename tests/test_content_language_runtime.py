"""Existing server owner advances standalone checks; observers never dispatch."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from threading import Barrier, Event, Lock, current_thread
from time import monotonic, sleep

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_autopilot import register_autopilot_runtime
from plotloom.api.project_folder_content_language import (
    register_content_language_routes,
)
from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.content_language_service import ContentLanguageService
from tests.content_language_fixtures import completed_check, result_for
from tests.test_content_language_service import _ready
from tests.test_content_language_service import check_environment as _check_environment

check_environment = _check_environment


def check_app(storage, registry):
    @contextmanager
    def opened(project_id):
        with closing(storage.projects.open(project_id)) as store:
            yield store
    app = FastAPI()
    app.state.project_folder_storage = storage
    register_content_language_routes(app, opened, registry)
    register_autopilot_runtime(app, opened, registry)
    app.state.autopilot_service.interval_seconds = 0.02
    return app


def running(attempt):
    return transition_exec_attempt(attempt, state="running", process_id=123,
        process_group_id=123, process_birth_identity="synthetic-checker-test-process")


def failed(attempt, *, category="transient", stopped=True):
    value = transition_exec_attempt(attempt, state="failed", terminal_result="failure",
        process_exit_code=1, remote_tool_state="not_applicable", evidence_hash="c" * 64,
        execution_failure=category)
    return CodexExecHostStatus(state="failed", attempt=value, localExecutionStopped=stopped)


def test_first_check_then_observers_only_background_owner_retries_and_passes(check_environment, monkeypatch):
    storage, store, registry = check_environment
    original, _candidate = _ready(store, monkeypatch)
    statuses, admissions, admission_threads = {}, [], []
    lock, fail_now = Lock(), Event()
    def admit(attempt):
        with lock:
            admissions.append(attempt)
            admission_threads.append(current_thread())
            value = CodexExecHostStatus(state="running", attempt=running(attempt))
            statuses[str(attempt.attempt_id)] = value
            return value
    def status(identifier):
        with lock:
            value = statuses.get(str(identifier))
            if value is None:
                return CodexExecHostStatus(state="not_found")
            if value.state == "running" and fail_now.is_set():
                if value.attempt.attempt_id == admissions[0].attempt_id:
                    value = failed(value.attempt)
                else:
                    request, _data = store.repository.content_language.load(original.project_id, value.attempt.job_id)
                    done, receipt = completed_check(store, request.job_id, result_for(request))
                    value = CodexExecHostStatus(state="completed", attempt=done, receipt=receipt, localExecutionStopped=True)
                statuses[str(identifier)] = value
            return value
    registry.codex_exec_admit, registry.codex_exec_status = admit, status
    app = check_app(storage, registry)
    route = f"/api/v2/projects/{original.project_id}/content-language/outline/{original.job_id}"
    with TestClient(app) as client:
        first = client.post(route + "/check").json()
        anchor = first["checkJobId"]
        assert first["state"] == "running" and len(admissions) == 1
        fail_now.set()
        deadline = monotonic() + 8
        while monotonic() < deadline:
            # These are the UI's subsequent calls; neither can admit a job.
            observed = client.post(f"/api/v2/projects/{original.project_id}/content-language-checks/{anchor}/reconcile")
            assert observed.status_code == 200, observed.text
            passed = client.get(route).json()
            if passed["verdict"] == "pass":
                break
            sleep(0.02)
        assert passed["verdict"] == "pass", passed
        assert passed["checkJobId"] == anchor and passed["candidateJobId"] == original.job_id
        assert passed["retry"]["automaticRetriesUsed"] == 1
        assert passed["retry"]["currentJobId"] != anchor
        assert len(admissions) == len({item.attempt_id for item in admissions}) == 2
        assert len({item.job_id for item in admissions}) == 2
        assert admission_threads[1] is app.state.autopilot_service._thread
        assert store.source_outline_state().candidate.status == "ready"  # No creative adoption.
    assert app.state.autopilot_service._thread is None


def test_two_check_callers_claim_one_admission_rpc(check_environment, monkeypatch):
    storage, store, registry = check_environment
    original, candidate = _ready(store, monkeypatch)
    service = ContentLanguageService(registry)
    anchor = service.prepare(store, original, candidate)
    barrier, lock = Barrier(2), Lock()
    admissions, polls, statuses = [], [], {}
    def status(identifier):
        with lock:
            polls.append(identifier)
            synchronize = len(polls) <= 2
            value = statuses.get(str(identifier), CodexExecHostStatus(state="not_found"))
        if synchronize:
            barrier.wait(timeout=5)
        return value
    def admit(attempt):
        with lock:
            admissions.append(attempt)
            value = CodexExecHostStatus(state="running", attempt=running(attempt))
            statuses[str(attempt.attempt_id)] = value
            return value
    registry.codex_exec_status, registry.codex_exec_admit = status, admit
    client = TestClient(check_app(storage, registry))
    route = f"/api/v2/projects/{original.project_id}/content-language/outline/{original.job_id}/check"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: client.post(route), range(2)))
    assert all(response.status_code == 200 for response in results)
    assert len(admissions) == 1
    assert all(response.json()["checkJobId"] == anchor for response in results)


def test_known_capacity_deferral_reopens_only_unadmitted_exact_intent(check_environment, monkeypatch):
    _storage, store, registry = check_environment
    original, candidate = _ready(store, monkeypatch)
    service = ContentLanguageService(registry)
    anchor = service.prepare(store, original, candidate)
    calls, statuses = [], {}
    registry.codex_exec_status = lambda identifier: statuses.get(str(identifier), CodexExecHostStatus(state="not_found"))
    def admit(attempt):
        calls.append(attempt)
        if len(calls) == 1:
            return CodexExecHostStatus(state="not_found", capacityDeferred=True)
        value = CodexExecHostStatus(state="running", attempt=running(attempt))
        statuses[str(attempt.attempt_id)] = value
        return value
    registry.codex_exec_admit = admit
    service.advance(store, anchor)
    request, data = store.repository.content_language.load(original.project_id, anchor)
    assert data["admissionDeferred"] and data["attempt"]["state"] == "spawn_intent"
    service.advance(store, anchor)
    assert len(calls) == 2 and calls[0] == calls[1]
    service.advance(store, anchor)
    assert len(calls) == 2 and request.job_id == anchor


@pytest.mark.parametrize("gate", ["permission", "unconfirmed_stop", "changed_profile", "cancel_prepared_child"])
def test_server_owner_preserves_stop_and_frozen_authority_gates(check_environment, monkeypatch, gate):
    storage, store, registry = check_environment
    original, _candidate = _ready(store, monkeypatch)
    admissions, statuses = [], {}
    def admit(attempt):
        admissions.append(attempt)
        current = running(attempt)
        value = (failed(current) if gate == "cancel_prepared_child" else CodexExecHostStatus(state="running", attempt=current))
        statuses[str(attempt.attempt_id)] = value
        return value
    registry.codex_exec_admit = admit
    registry.codex_exec_status = lambda identifier: statuses.get(str(identifier), CodexExecHostStatus(state="not_found"))
    def cancel(attempt):
        value = transition_exec_attempt(attempt, state="settled", terminal_result="not_started",
            remote_tool_state="not_applicable", evidence_hash="f" * 64, execution_failure="cancelled")
        return CodexExecHostStatus(state="settled", attempt=value, localExecutionStopped=True)
    registry.codex_exec_cancel = cancel
    app = check_app(storage, registry)
    client, runtime = TestClient(app), app.state.autopilot_service
    route = f"/api/v2/projects/{original.project_id}/content-language/outline/{original.job_id}"
    first = client.post(route + "/check").json()
    anchor = first["checkJobId"]
    if gate == "cancel_prepared_child":
        assert first["retry"]["currentJobId"] != anchor and len(admissions) == 1
        cancelled = client.post(f"/api/v2/projects/{original.project_id}/content-language-checks/{anchor}/cancel")
        assert cancelled.status_code == 200 and cancelled.json()["retry"]["state"] == "stopped"
    elif gate == "changed_profile":
        profile = registry.codex_exec_profile()
        registry.codex_exec_profile = lambda: profile.model_copy(update={"instruction_hash": "d" * 64})
    else:
        attempt = admissions[0]
        statuses[str(attempt.attempt_id)] = failed(running(attempt),
            category="permission" if gate == "permission" else "transient", stopped=gate != "unconfirmed_stop")
    try:
        assert runtime.acquire_controller()
        for _ in range(3):
            runtime.step(original.project_id)
        assert len(admissions) == 1
        current = client.get(route).json()
        assert current["retry"]["state"] != "exhausted"
        assert store.source_outline_state().candidate.status == "ready"
    finally:
        runtime.close()
