"""Stable checker API anchor with separately bound physical retry jobs."""
from uuid import uuid4

import pytest

from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.content_language_service import ContentLanguageService
from plotloom.generation_retry_policy import ManualExecutionRetry
from tests.test_content_language_service import check_environment as _check_environment, _ready

check_environment = _check_environment


@pytest.mark.parametrize("limit",[0,1,3])
def test_checker_retries_retain_anchor_and_manual_does_not_reset_allowance(check_environment,monkeypatch,limit):
    _storage,store,registry=check_environment
    original,candidate=_ready(store,monkeypatch)
    statuses,calls={},[]
    def admit(attempt):
        calls.append(attempt)
        value=transition_exec_attempt(attempt,state="running",process_id=123,process_group_id=123,process_birth_identity="fake")
        value=transition_exec_attempt(value,state="failed",process_exit_code=1,terminal_result="failure",
            remote_tool_state="not_applicable",evidence_hash="d"*64,execution_failure="transient")
        statuses[str(attempt.attempt_id)]=CodexExecHostStatus(state="failed",attempt=value,localExecutionStopped=True)
        return statuses[str(attempt.attempt_id)]
    registry.codex_exec_admit=admit
    registry.codex_exec_status=lambda identifier:statuses.get(str(identifier),CodexExecHostStatus(state="not_found"))
    service=ContentLanguageService(registry)
    anchor=service.prepare(store,original,candidate,automatic_retry_limit=limit)
    first=service.advance(store,anchor)
    assert len(calls)==1  # First explicit action really admitted the initial checker.
    assert first["checkJobId"]==anchor
    for _ in range(limit+3):
        state=service.ensure(store,original,candidate)
    assert len(calls)==len({c.attempt_id for c in calls})==limit+1
    assert len({c.job_id for c in calls})==limit+1
    state=service.status(store,anchor)
    assert state["checkJobId"]==anchor and state["retry"]["automaticRetriesUsed"]==limit
    assert state["retry"]["state"]=="exhausted"
    assert service.advance(store,anchor,allow_admission=False)["retry"]==state["retry"]
    assert len(calls)==limit+1
    command=ManualExecutionRetry(commandId=uuid4(),failedJobId=state["retry"]["currentJobId"],
        failedAttemptId=state["retry"]["currentAttemptId"])
    manual=service.retry(store,anchor,command)
    assert manual["checkJobId"]==anchor and manual["retry"]["automaticRetriesUsed"]==limit
    assert len(calls)==limit+2
    again=service.retry(store,anchor,command)
    assert again["retry"]==manual["retry"] and len(calls)==limit+2


def test_checker_crash_after_durable_admission_intent_never_resends(check_environment,monkeypatch):
    _storage,store,registry=check_environment
    original,candidate=_ready(store,monkeypatch)
    registry.codex_exec_status=lambda _id:CodexExecHostStatus(state="not_found")
    calls=[]
    registry.codex_exec_admit=lambda attempt:calls.append(attempt)
    service=ContentLanguageService(registry)
    anchor=service.prepare(store,original,candidate)
    store.repository.content_language.mark_admission(store.manifest.project_id,anchor)
    state=service.advance(store,anchor)
    assert state["retry"]["state"]!="exhausted"
    request,data=store.repository.content_language.load(store.manifest.project_id,anchor)
    assert data["attempt"]["state"]=="spawn_intent" and state["state"]=="outcome_unknown" and not calls
    service.advance(store,anchor,allow_admission=False)
    assert not calls and request.job_id==anchor
