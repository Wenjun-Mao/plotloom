"""Small real API/SQLite/exchange journey with an explicitly fake native host."""
from contextlib import closing, contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_content_language import (
    register_content_language_routes,
)
from plotloom.codex_exec_contracts import (
    CodexExecHostStatus,
    transition_exec_attempt,
)
from plotloom.content_language_service import ContentLanguageService
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.exceptions import InvalidTransitionError
from plotloom.source_outline_contracts import OutlineAcceptRequest
from tests.content_language_fixtures import completed_check, result_for
from tests.source_outline_fixtures import _deliver, _material, _request
from tests.test_codex_exec_validation import SOURCE_REVISION
from tests.test_content_language_persistence import (
    check_environment as _check_environment,
)

check_environment = _check_environment


def _ready(store, monkeypatch):
    import tests.content_language_fixtures as fixtures
    # This test exercises actual checking advancement rather than installing
    # the shared helper's explicit synthetic already-completed check.
    monkeypatch.setattr(fixtures, "install_synthetic_language_check", lambda *_args: None)
    source = _material()
    store.save_source_material(expected_source_revision=0, material=source)
    request = _request(store.manifest.project_id, source)
    store.prepare_outline_candidate(request)
    delivery = _deliver(store, request)
    store.admit_outline_delivery(delivery)
    return request, delivery.candidate


def test_actual_api_check_advances_once_preserves_ready_then_allows_exact_adoption(check_environment, monkeypatch):
    storage, store, registry = check_environment
    original, candidate = _ready(store, monkeypatch)
    statuses, admissions = {}, []

    def admit(attempt):
        admissions.append(attempt.attempt_id)
        running = transition_exec_attempt(attempt, state="running", process_id=123,
            process_group_id=123, process_birth_identity="explicit-fake-check-host")
        status = CodexExecHostStatus(state="running", attempt=running)
        statuses[str(attempt.attempt_id)] = status
        return status

    def status(identifier):
        previous = statuses.get(str(identifier))
        if previous is None:
            return CodexExecHostStatus(state="not_found")
        if previous.state == "running":
            request, _data = store.repository.content_language.load(original.project_id, previous.attempt.job_id)
            done, receipt = completed_check(store, request.job_id, result_for(request))
            statuses[str(identifier)] = CodexExecHostStatus(state="completed", attempt=done, receipt=receipt)
        return statuses[str(identifier)]

    registry.codex_exec_admit, registry.codex_exec_status = admit, status

    @contextmanager
    def opened(project_id):
        assert project_id == store.manifest.project_id
        yield store

    app = FastAPI()
    register_content_language_routes(app, opened, registry)
    route = f"/api/v2/projects/{original.project_id}/content-language/outline/{original.job_id}"
    client = TestClient(app)
    assert client.get(route).json()["state"] == "required"
    with pytest.raises(InvalidTransitionError, match="独立原生"):
        store.accept_outline_candidate(OutlineAcceptRequest(job_id=original.job_id, expected_source_revision=1, expected_outline_revision=0))
    pending = client.post(route + "/check").json()
    assert pending["state"] == "running" and pending["verdict"] is None
    assert store.source_outline_state().candidate.status == "ready"
    passed = client.post(route + "/check").json()
    assert passed["verdict"] == "pass" and passed["checkJobId"] == pending["checkJobId"]
    assert client.post(route + "/check").json()["checkJobId"] == passed["checkJobId"]
    assert len(admissions) == 1
    accepted = store.accept_outline_candidate(OutlineAcceptRequest(job_id=original.job_id, expected_source_revision=1, expected_outline_revision=0))
    assert accepted.accepted_outline.outline == candidate
    assert passed["checkJobId"] != original.job_id
    store.close()
    snapshot = storage.recovery.create_snapshot(original.project_id)
    from pathlib import Path

    from plotloom.project_storage import ProjectFolderStorage
    restored = ProjectFolderStorage(outputs_root=storage.projects.outputs_root.parent / "restored-outputs",
        application_data_root=storage.projects.outputs_root.parent / "restored-application")
    restored.recovery.restore(Path(snapshot.location))
    with closing(restored.projects.open(original.project_id)) as copied:
        retained = copied.repository.content_language.load(original.project_id, passed["checkJobId"])[1]
        assert retained["result"]["verdict"] == "pass"
        assert copied.source_outline_state().accepted_outline.outline == candidate


def test_lost_native_admission_acknowledgement_holds_exact_unknown_without_resubmission(check_environment, monkeypatch):
    _storage, store, registry = check_environment
    original, candidate = _ready(store, monkeypatch)
    service = ContentLanguageService(registry)
    job = service.prepare(store, original, candidate, code_revision=SOURCE_REVISION)
    calls = []
    registry.codex_exec_status = lambda _attempt: CodexExecHostStatus(state="not_found")

    def lost(attempt):
        calls.append(attempt.attempt_id)
        raise RuntimeError("synthetic lost admission acknowledgement")

    registry.codex_exec_admit = lost
    with pytest.raises(RuntimeError, match="lost admission"):
        service.advance(store, job)
    assert service.status(store, job)["state"] == "outcome_unknown"
    with pytest.raises(InvalidTransitionError, match="不确定"):
        service.advance(store, job)
    assert len(calls) == 1
    assert store.source_outline_state().candidate.status == "ready"


def test_new_publication_cannot_strip_language_contract_and_old_report_remains_readable(check_environment, monkeypatch):
    _storage, store, _registry = check_environment
    original, _candidate = _ready(store, monkeypatch)
    stripped = original.model_copy(deep=True)
    stripped.job_id = "ch_" + "z" * 32
    del stripped.input_artifacts["language-contract.json"]
    pin = store.creative_handoff_execution_pin(original)
    with pytest.raises(CreativeHandoffError, match="冻结项目内容语言"):
        store.creative_handoff_exchange().write_package(stripped, pin)
    # Prospective guards do not relabel or regenerate already-stored HTML.
    before = store.outline_candidate_report(original.job_id)
    assert before == "<!doctype html><html><body>derived outline</body></html>"
    assert store.outline_candidate_report(original.job_id) == before
