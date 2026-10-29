"""Fresh draft/checker attempts retain candidate authority and admission safety."""
from uuid import uuid4

import pytest

from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.generation_retry_policy import ManualExecutionRetry
from tests.autopilot_controller_fixtures import PIN
from tests.codex_exec_fixtures import install_profile
from tests.test_h3_execution_retry import setup_retry
from tests.video_batch_fixtures import draft_for


def direction_environment(tmp_path,monkeypatch,limit,checking):
    storage,_client,service,_provider,project,view=setup_retry(tmp_path,limit)
    install_profile(service.registry)
    monkeypatch.setattr(CreativeHandoffExchange,"current_execution_pin",lambda *_args:PIN)
    view=service.edit_directions(project,view["revision"],draft_for(view)) if checking else service.draft(project,view["revision"])
    return storage,service,project,view


@pytest.mark.parametrize("checking",[False,True])
@pytest.mark.parametrize("limit",[0,1,3])
def test_direction_retries_are_finite_distinct_and_manual_does_not_replenish(tmp_path,monkeypatch,limit,checking):
    _storage,service,project,_view=direction_environment(tmp_path,monkeypatch,limit,checking)
    registry=service.registry
    statuses,calls={},[]
    def fail(attempt):
        calls.append(attempt)
        running=transition_exec_attempt(attempt,state="running",process_id=123,process_group_id=123,process_birth_identity="stopped-fake")
        failed=transition_exec_attempt(running,state="failed",process_exit_code=1,terminal_result="failure",remote_tool_state="not_applicable",evidence_hash="a"*64,execution_failure="transient")
        value=CodexExecHostStatus(state="failed",attempt=failed,localExecutionStopped=True)
        statuses[str(attempt.attempt_id)]=value
        return value
    registry.codex_exec_admit=fail
    registry.codex_exec_status=lambda identifier:statuses.get(str(identifier),CodexExecHostStatus(state="not_found"))
    for _ in range(limit+4):service.step(project)
    view=service.current(project)
    key="fidelity" if checking else "draft"
    data=view["execution"][key]
    assert view["state"]=="blocked" and len(calls)==limit+1
    assert len({call.job_id for call in calls})==len({call.attempt_id for call in calls})==limit+1
    assert data["retry"]["state"]=="exhausted" and data["retry"]["automaticRetriesUsed"]==limit
    command=ManualExecutionRetry(commandId=uuid4(),failedJobId=data["request"]["jobId"],failedAttemptId=data["attempt"]["attemptId"],expectedRevision=view["revision"])
    changed=service.retry_execution(project,command)
    duplicate=service.retry_execution(project,command)
    assert duplicate["revision"]==changed["revision"] and duplicate["execution"]==changed["execution"]
    for _ in range(3):service.step(project)
    assert len(calls)==limit+2
    assert service.current(project)["execution"][key]["retry"]["automaticRetriesUsed"]==limit


def test_lost_direction_admission_ack_is_not_resent_or_retried(tmp_path,monkeypatch):
    _storage,service,project,_view=direction_environment(tmp_path,monkeypatch,3,False)
    calls=[]
    service.registry.codex_exec_status=lambda _id:CodexExecHostStatus(state="not_found")
    def lost(attempt):
        calls.append(attempt)
        return CodexExecHostStatus(state="not_found")
    service.registry.codex_exec_admit=lost
    for _ in range(5):service.step(project)
    view=service.current(project)
    assert len(calls)==1
    assert view["execution"]["draft"]["attempt"]["state"]=="outcome_unknown"
    assert not view["execution"]["draft"]["localExecutionStopped"]
    assert not view["execution"]["draftHistory"]
