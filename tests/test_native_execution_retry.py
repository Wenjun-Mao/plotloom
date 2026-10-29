"""Real native-owner rows with a fake host: each successor is a fresh attempt."""
from contextlib import closing
from uuid import uuid4

import pytest

from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.autopilot_execution_retry import current_checkpoint
from plotloom.generation_retry_policy import ManualExecutionRetry
from tests.autopilot_controller_fixtures import environment


def current(storage, project_id):
    with closing(storage.projects.open(project_id)) as store:
        return store.repository.autopilot.current(project_id)


@pytest.mark.parametrize("limit", [0, 1, 3])
def test_failed_native_jobs_get_exact_frozen_allowance_and_manual_keeps_auto_count(tmp_path, monkeypatch, limit):
    storage, registry, service, run, calls = environment(tmp_path, monkeypatch, auto_deliver=False,
                                                       limits={"automatic_retry_limit":limit})
    host = registry._codex_exec_test_host
    original_admit = host.admit
    ids = []
    def fail(attempt):
        running = original_admit(attempt).attempt
        ids.append(attempt.attempt_id)
        failed = transition_exec_attempt(running,state="failed",process_exit_code=1,terminal_result="failure",
            remote_tool_state="not_applicable",evidence_hash="f"*64,execution_failure="transient")
        status = CodexExecHostStatus(state="failed",attempt=failed,localExecutionStopped=True)
        host.statuses[str(attempt.attempt_id)] = status
        return status
    registry.codex_exec_admit = fail
    try:
        assert service.acquire_controller()
        for _ in range(4+limit*2):
            service.step(run.project_id)
        view = current(storage,run.project_id)
        checkpoint = current_checkpoint(view,"outline")
        assert checkpoint["evidence"]["result"]["executionRetryExhausted"]
        assert checkpoint["retry"]["state"] == "exhausted"
        assert all(c["retry"]["state"] == "stopped" for c in view.checkpoints
            if c["operationKey"].startswith("outline") and c is not checkpoint)
        assert len(ids) == len(set(ids)) == limit+1
        assert len(calls) == limit+1
        assert checkpoint["retry"]["automaticRetriesUsed"] == limit
        assert view.lifetime_jobs == limit+1
        # Reopening/observing does not replenish the frozen allowance.
        for _ in range(2): service.step(run.project_id)
        assert len(ids) == limit+1
        view = current(storage,run.project_id)
        checkpoint = current_checkpoint(view,"outline")
        command = ManualExecutionRetry(commandId=uuid4(),expectedRunId=view.id,expectedRevision=view.revision,
            failedJobId=checkpoint["evidence"]["jobId"],failedAttemptId=checkpoint["evidence"]["executorAttemptId"])
        successor = service.retry_execution(run.project_id,command)
        assert current_checkpoint(successor,"outline")["retry"]["automaticRetriesUsed"] == limit
        duplicate = service.retry_execution(run.project_id,command)
        assert duplicate.revision == successor.revision and duplicate.checkpoints == successor.checkpoints
        for _ in range(3): service.step(run.project_id)
        assert len(ids) == limit+2 and len(set(ids)) == limit+2
        final = current(storage, run.project_id)
        assert current_checkpoint(final, "outline")["retry"]["state"] == "exhausted"
        assert all(c["retry"]["state"] == "stopped" for c in final.checkpoints
            if c["operationKey"].startswith("outline") and c["operationKey"] != current_checkpoint(final, "outline")["operationKey"])
    finally:
        service.close()


@pytest.mark.parametrize("stopped,failure", [(False,"transient"),(True,"cancelled"),(True,"permission"),(True,"configuration"),(True,"authorization")])
def test_running_local_owner_and_nonretryable_stops_never_create_successor(tmp_path,monkeypatch,stopped,failure):
    storage,registry,service,run,_calls = environment(tmp_path,monkeypatch,auto_deliver=False)
    host=registry._codex_exec_test_host
    admit=host.admit
    ids=[]
    def fail(attempt):
        running=admit(attempt).attempt
        ids.append(attempt.attempt_id)
        value=transition_exec_attempt(running,state="failed",process_exit_code=1,terminal_result="failure",
            remote_tool_state="not_applicable",evidence_hash="e"*64,execution_failure=failure)
        status=CodexExecHostStatus(state="failed",attempt=value,localExecutionStopped=stopped)
        host.statuses[str(attempt.attempt_id)]=status
        return status
    registry.codex_exec_admit=fail
    try:
        assert service.acquire_controller()
        for _ in range(6):service.step(run.project_id)
        assert len(ids)==1
        view = current(storage,run.project_id)
        checkpoint = current_checkpoint(view,"outline:retry:1")
        assert checkpoint["operationKey"]=="outline"
        assert checkpoint["retry"]["state"] == ("retry_pending" if failure == "transient" else "stopped")
        before = (view.revision, view.checkpoints, host.admissions, tuple(host.statuses))
        def no_host(*_args): pytest.fail("retry projection polled or admitted host work")
        with monkeypatch.context() as reads:
            reads.setattr(registry, "codex_exec_status", no_host)
            reads.setattr(registry, "codex_exec_admit", no_host)
            for _ in range(2):
                observed = current(storage, run.project_id)
                assert (observed.revision, observed.checkpoints, host.admissions, tuple(host.statuses)) == before
    finally:service.close()


def test_image_retry_keeps_unknown_cost_and_uses_fresh_reference_job(tmp_path,monkeypatch):
    storage,registry,service,run,_calls=environment(tmp_path,monkeypatch)
    host=registry._codex_exec_test_host
    admit=host.admit
    failed_ids=[]
    def once(attempt):
        if attempt.domain=="image" and not failed_ids:
            failed_ids.append(attempt.attempt_id)
            running=transition_exec_attempt(attempt,state="running",process_id=123456,
                process_group_id=123456,process_birth_identity="stopped-fake-image")
            failed=transition_exec_attempt(running,state="failed",process_exit_code=1,
                terminal_result="failure",remote_tool_state="unknown",image_budget_state="reserved",
                evidence_hash="b"*64,execution_failure="transient")
            result=CodexExecHostStatus(state="failed",attempt=failed,localExecutionStopped=True)
            host.statuses[str(attempt.attempt_id)]=result
            return result
        return admit(attempt)
    registry.codex_exec_admit=once
    try:
        assert service.acquire_controller()
        for _ in range(100):
            service.step(run.project_id)
            view=current(storage,run.project_id)
            if any(c["state"]=="adopted" and c["evidence"]["result"].get("executionRetry") for c in view.checkpoints) or view.state=="blocked":break
        assert any(c["state"]=="adopted" and c["evidence"]["result"].get("executionRetry") for c in view.checkpoints),view.blocker
        retried=[c for c in view.checkpoints if c["evidence"]["result"].get("executionRetry")]
        assert len(retried)==1
        child=retried[0]["evidence"]
        assert child["result"]["executionRetry"]["predecessorAttemptId"]==str(failed_ids[0])
        with closing(storage.projects.open(run.project_id)) as store:
            prior=store.repository.autopilot.exec_attempt_for_operation(run.id,
                child["result"]["executionRetry"]["parentOperationKey"])
            assert prior.remote_tool_state=="unknown" and prior.image_budget_state=="reserved"
            assert prior.job_id!=child["jobId"]
    finally:service.close()


def test_missing_native_admission_ack_never_resends_used_identity(tmp_path,monkeypatch):
    storage,registry,service,run,_calls=environment(tmp_path,monkeypatch,auto_deliver=False)
    calls=[]
    registry.codex_exec_status=lambda _id:CodexExecHostStatus(state="not_found")
    def lost(attempt):
        calls.append(attempt)
        return CodexExecHostStatus(state="not_found")
    registry.codex_exec_admit=lost
    try:
        assert service.acquire_controller()
        for _ in range(7):service.step(run.project_id)
        view=current(storage,run.project_id)
        assert len(calls)==1 and not any(c["evidence"]["result"].get("executionRetry") for c in view.checkpoints)
        assert current_checkpoint(view, "outline")["retry"]["state"] == "retry_pending"
        with closing(storage.projects.open(run.project_id)) as store:
            attempt=store.repository.autopilot.exec_attempt_for_operation(run.id,"outline")
            assert attempt.state=="outcome_unknown"
    finally:service.close()


def test_late_parent_completion_is_retained_without_replacing_adopted_child(tmp_path,monkeypatch):
    from plotloom.autopilot_contracts import CommandAuthority, OperationScope
    from plotloom.codex_exec_attempt_contracts import ATTEMPT_OBSERVED_FIELDS
    storage,registry,service,run,_calls=environment(tmp_path,monkeypatch)
    host=registry._codex_exec_test_host
    admit=host.admit
    late=[]
    def delay_first(attempt):
        admitted=admit(attempt)
        if attempt.operation_key=="outline" and not late:
            completed=host.status(attempt.attempt_id)
            late.append(completed)
            unknown=transition_exec_attempt(admitted.attempt,state="outcome_unknown")
            value=CodexExecHostStatus(state="outcome_unknown",attempt=unknown,localExecutionStopped=True)
            host.statuses[str(attempt.attempt_id)]=value
            return value
        return admitted
    registry.codex_exec_admit=delay_first
    try:
        assert service.acquire_controller()
        for _ in range(15):
            service.step(run.project_id)
            view=current(storage,run.project_id)
            child=current_checkpoint(view,"outline")
            if child and child["operationKey"]!="outline" and child["state"]=="adopted":break
        assert child["state"]=="adopted" and child["operationKey"]=="outline:retry:1"
        retained=late[0]
        with closing(storage.projects.open(run.project_id)) as store:
            with store.repository.autopilot_command(CommandAuthority(view.id,service.claim,OperationScope.EVIDENCE)):
                store.repository.autopilot.update_exec_attempt(retained.attempt.attempt_id,receipt=retained.receipt,
                    **{field:getattr(retained.attempt,field) for field in ATTEMPT_OBSERVED_FIELDS})
        reopened=current(storage,run.project_id)
        assert current_checkpoint(reopened,"outline")["evidence"]["jobId"]==child["evidence"]["jobId"]
        assert current_checkpoint(reopened,"outline")["state"]=="adopted"
        assert next(c for c in reopened.checkpoints if c["operationKey"] == "outline")["retry"]["state"] == "stopped"
        assert current_checkpoint(reopened,"outline")["retry"]["state"] == "ready"
        with closing(storage.projects.open(run.project_id)) as store:
            parent=store.repository.autopilot.exec_attempt_for_operation(run.id,"outline")
            assert parent.state=="completed" and parent.attempt_id==retained.attempt.attempt_id
    finally:service.close()
