"""Offline receipt/persistence trust, exact reuse, native failure and row isolation."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.content_language_contract import CHECK_INPUT
from plotloom.content_language_persistence import (
    check_rows,
    require_language_pass,
)
from plotloom.content_language_service import ContentLanguageService
from plotloom.exceptions import InvalidTransitionError, NotFoundError
from plotloom.persistence.project.branches import ProjectBranchPersistence
from plotloom.persistence.project.creative_execution_pins import freeze_execution_pin
from plotloom.persistence.schema import SourceOutlineCandidateRow
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from tests.codex_exec_fixtures import PROFILE
from tests.content_language_fixtures import (
    completed_check,
    original_request,
    result_for,
)
from tests.source_outline_fixtures import _storage
from tests.test_codex_exec_validation import PIN, SOURCE_REVISION
from tests.test_content_language_contract import CANDIDATES


@pytest.fixture
def check_environment(tmp_path, monkeypatch):
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, _stage: PIN)
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    registry = SimpleNamespace(require_codex_exec_readiness=lambda: None, codex_exec_profile=lambda: PROFILE)
    yield storage, store, registry
    store.close()


def prepare(store, registry, stage="outline", candidate=None):
    original = original_request(stage, project_id=store.manifest.project_id)
    with store.repository._write() as session:
        freeze_execution_pin(session, original, PIN)
    candidate = deepcopy(candidate or CANDIDATES[stage])
    service = ContentLanguageService(registry)
    job = service.prepare(store, original, candidate, code_revision=PIN["upstreamRevision"] if stage.startswith("bridge-") else SOURCE_REVISION)
    request, _data = store.repository.content_language.load(original.project_id, job)
    return service, original, candidate, job, request


@pytest.mark.parametrize("stage", tuple(CANDIDATES))
def test_distinct_check_receipt_is_required_then_exact_results_reuse_for_each_stage(check_environment, stage):
    storage, store, registry = check_environment
    service, original, candidate, job, request = prepare(store, registry, stage)
    assert job != original.job_id and request.stage == original.stage
    with pytest.raises(NotFoundError):
        store.cancel_outline_candidate(job)
    with store.repository._read() as session, pytest.raises(InvalidTransitionError, match="未通过|尚未完成"):
        require_language_pass(session, original, candidate)
    original_head = store.source_outline_state().candidate
    done, receipt = completed_check(store, job, result_for(request))
    assert done.attempt_id == receipt.attempt_id
    with store.repository._read() as session:
        assert require_language_pass(session, original, candidate) == job
        assert len(check_rows(session, original.project_id)) == 1
        assert ProjectBranchPersistence._latest(session, original.project_id) is None
    assert service.prepare(store, original, candidate, code_revision=SOURCE_REVISION) == job
    assert store.source_outline_state().candidate == original_head
    assert service.status(store, job)["verdict"] == "pass"
    with pytest.raises(NotFoundError): store.outline_candidate_request(job)
    with pytest.raises(NotFoundError): store.branch_candidate_report(job)
    project_id = store.manifest.project_id
    store.close()
    reopened = storage.projects.open(project_id)
    try:
        assert service.status(reopened, job)["verdict"] == "pass"
        assert reopened.repository.content_language.load(project_id, job)[1]["receipt"] == receipt.model_dump(mode="json", by_alias=True)
    finally:
        reopened.close()


@pytest.mark.parametrize("mutation", ["candidate", "locale", "source", "classifier", "settings", "verdict", "receipt"])
def test_changed_inputs_or_forged_stored_flags_receipt_never_adopt(check_environment, mutation):
    _storage, store, registry = check_environment
    service, original, candidate, job, request = prepare(store, registry)
    completed_check(store, job, result_for(request))
    if mutation in {"verdict", "receipt", "classifier"}:
        with store.repository._write() as session:
            row = session.get(SourceOutlineCandidateRow, job)
            data = deepcopy(row.outline)
            if mutation == "verdict": data["result"]["coverage"][0]["verdict"] = "not_applicable"
            elif mutation == "receipt": data["receipt"]["evidenceHash"] = "1" * 64
            else:
                changed = deepcopy(row.request)
                changed["inputArtifacts"][CHECK_INPUT]["classifierVersion"] = "forged-new-version"
                row.request = changed
            row.outline = data
        with pytest.raises(ValueError): service.status(store, job)
        return
    changed = original.model_copy(deep=True)
    if mutation == "candidate": candidate["adaptation"]["core"] += " Changed."
    elif mutation == "source": changed.source["text"] += " New source fact."
    elif mutation == "settings": changed.input_artifacts["settings.json"] = {"choice": "different"}
    else:
        from plotloom.language_policy import freeze_request_language
        freeze_request_language(changed, "en-US")
        candidate["lang"] = "en"
    with store.repository._read() as session, pytest.raises(InvalidTransitionError, match="独立原生"):
        require_language_pass(session, changed, candidate)


@pytest.mark.parametrize("state", ["failed", "outcome_unknown"])
def test_failed_and_unknown_checks_retain_identity_without_duplicate_submission(check_environment, monkeypatch, state):
    _storage, store, registry = check_environment
    service, original, candidate, job, _request = prepare(store, registry)
    _request, data = store.repository.content_language.load(original.project_id, job)
    from plotloom.codex_exec_contracts import CodexExecAttempt
    attempt = CodexExecAttempt.model_validate(data["attempt"])
    running = transition_exec_attempt(attempt, state="running", session_id=uuid4(), process_id=123,
        process_group_id=123, process_birth_identity="test-process")
    changes = {"state": state}
    if state == "failed":
        changes |= {"terminal_result": "failure", "process_exit_code": 1, "evidence_hash": "1"*64,
                    "remote_tool_state": "not_applicable"}
    observed = transition_exec_attempt(running, **changes)
    store.repository.content_language.observe(original.project_id, job, attempt=observed)
    registry.codex_exec_status = lambda _attempt: CodexExecHostStatus(state=state, attempt=observed)
    registry.codex_exec_admit = lambda *_args: pytest.fail("an old failed/UNKNOWN check must not be resent")
    assert service.prepare(store, original, candidate, code_revision=SOURCE_REVISION) == job
    assert service.advance(store, job, allow_admission=False)["state"] == state
    assert service.status(store, job)["verdict"] is None
    with store.repository._read() as session:
        row = session.get(SourceOutlineCandidateRow, job)
        assert row.status == ("cancelled" if state == "failed" else "prepared")
        with pytest.raises(InvalidTransitionError): require_language_pass(session, original, candidate)


def test_native_result_requires_complete_coverage_and_uncertainty_is_never_a_content_rejection(check_environment):
    _storage, store, registry = check_environment
    service, original, candidate, job, request = prepare(store, registry)
    completed_check(store, job, result_for(request, uncertain_path="$.adaptation.core"))
    status = service.status(store, job)
    assert status["verdict"] == "uncertain" and status["issues"] == []
    with store.repository._read() as session, pytest.raises(InvalidTransitionError):
        require_language_pass(session, original, candidate)
    data = store.repository.content_language.load(original.project_id, job)[1]
    assert data["attempt"]["state"] == "completed"
    assert data["receipt"] and "contentRejection" not in data["attempt"]
