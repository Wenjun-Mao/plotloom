from uuid import uuid4

import pytest
from pydantic import ValidationError

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecProfile,
    SpecialistChatExecutor,
    transition_exec_attempt,
)

HASH = "a" * 64


def profile(**changes):
    value = {
        "executableSha256": HASH,
        "cliVersion": "0.162.0-alpha.17.2",
        "model": "test-model",
        "reasoningEffort": "high",
        "capabilities": [
            "exec_json_events_v1",
            "session_rollout_v1",
            "delivery_directory_write_v1",
            "image_gen_event_v1",
        ],
        "instructionHash": HASH,
        "validatorHash": HASH,
        "sandboxProfile": "read_only_with_delivery_write",
        "maxRuntimeSeconds": 1800,
        "maxEventBytes": 2_000_000,
        "maxOutputBytes": 20_000_000,
        "maxImageOutputs": 4,
    }
    return CodexExecProfile.model_validate(value | changes)


def test_profile_hash_is_stable_and_profile_is_immutable():
    one = profile()
    two = profile()
    assert one.profile_hash == two.profile_hash
    with pytest.raises(AttributeError):
        one.capabilities.append("exec_json_events_v1")
    with pytest.raises(ValidationError):
        one.model = "changed"
    assert one.profile_hash == two.profile_hash


@pytest.mark.parametrize(
    "changes",
    [
        {"maxProcesses": 2},
        {"apiFallback": True},
        {"nestedDispatch": True},
        {"externalMcpServers": True},
        {"capabilities": ["exec_json_events_v1", "session_rollout_v1", "delivery_directory_write_v1"]},
        {"sandboxProfile": "danger_full_access"},
    ],
)
def test_profile_rejects_unbounded_or_unqualified_capabilities(changes):
    with pytest.raises(ValidationError):
        profile(**changes)


def test_profile_rejects_credential_shaped_identity():
    with pytest.raises(ValidationError):
        profile(model="sk-proj-privatecredential")


def test_specialist_binding_remains_a_chat_identity():
    with pytest.raises(ValidationError):
        SpecialistChatExecutor(
            backend="specialist_chat",
            textTaskId=uuid4(),
            imageTaskId=uuid4(),
            unexpectedSessionId=uuid4(),
        )


def test_attempt_reserves_exact_domain_budget_and_process_group():
    attempt = CodexExecAttempt(
        attemptId=uuid4(),
        runId=uuid4(),
        projectId=uuid4(),
        jobId="ch_" + "b" * 24,
        operationKey="outline",
        domain="text",
        requestHash=HASH,
        packageHash=HASH,
        profileHash=HASH,
        reservedImageOutputs=0,
        state="running",
        processId=123,
        processGroupId=123,
        processBirthIdentity="Mon Oct 13 12:00:00 2026",
    )
    assert attempt.process_id == attempt.process_group_id
    with pytest.raises(ValidationError):
        attempt.process_group_id = 124
    assert attempt.process_group_id == 123


def test_attempt_lifecycle_uses_validated_immutable_snapshots():
    attempt = CodexExecAttempt(
        attemptId=uuid4(),
        runId=uuid4(),
        projectId=uuid4(),
        jobId="ch_" + "b" * 24,
        operationKey="outline",
        domain="text",
        requestHash=HASH,
        packageHash=HASH,
        profileHash=HASH,
        reservedImageOutputs=0,
        state="reserved",
    )
    intent = transition_exec_attempt(attempt, state="spawn_intent")
    running = transition_exec_attempt(
        intent,
        state="running",
        process_id=123,
        process_group_id=123,
        process_birth_identity="pid-start-123",
    )
    uncertain = transition_exec_attempt(running, state="outcome_unknown")
    assert attempt.state == "reserved"
    assert intent.state == "spawn_intent"
    assert running.state == "running"
    assert uncertain.state == "outcome_unknown"
    assert uncertain.process_birth_identity == "pid-start-123"
    with pytest.raises(ValueError, match="lifecycle transition"):
        transition_exec_attempt(attempt, state="running")
    with pytest.raises(ValueError, match="only lifecycle and terminal facts"):
        transition_exec_attempt(attempt, run_id=uuid4())
    with pytest.raises(ValidationError):
        transition_exec_attempt(running.model_copy(update={"process_id": -1}), state="running")


def test_terminal_attempt_cannot_rewrite_its_evidence_while_settling():
    attempt = CodexExecAttempt(
        attemptId=uuid4(), runId=uuid4(), projectId=uuid4(), jobId="ch_" + "a" * 24,
        operationKey="outline", domain="text", requestHash=HASH, packageHash=HASH,
        profileHash=HASH, reservedImageOutputs=0, state="failed", sessionId=uuid4(),
        processId=321, processGroupId=321, processBirthIdentity="pid-start-321",
        processExitCode=1, terminalResult="failure", remoteToolState="not_applicable", evidenceHash=HASH,
    )
    settled = transition_exec_attempt(attempt, state="settled")
    assert settled.state == "settled"
    with pytest.raises(ValueError, match="terminal attempt evidence"):
        transition_exec_attempt(attempt, state="settled", evidence_hash="f" * 64)


@pytest.mark.parametrize(
    "domain,outputs",
    [("text", 1), ("image", 0), ("image", 5)],
)
def test_attempt_rejects_budget_domain_mismatch(domain, outputs):
    with pytest.raises(ValidationError):
        CodexExecAttempt(
            attemptId=uuid4(),
            runId=uuid4(),
            projectId=uuid4(),
            jobId="ij_" + "c" * 24,
            operationKey="frame-1",
            domain=domain,
            requestHash=HASH,
            packageHash=HASH,
            profileHash=HASH,
            reservedImageOutputs=outputs,
            state="reserved",
        )


def test_completed_attempt_requires_terminal_evidence_and_output_identity():
    with pytest.raises(ValidationError):
        CodexExecAttempt(
            attemptId=uuid4(),
            runId=uuid4(),
            projectId=uuid4(),
            jobId="ch_" + "d" * 24,
            operationKey="outline",
            domain="text",
            requestHash=HASH,
            packageHash=HASH,
            profileHash=HASH,
            reservedImageOutputs=0,
            state="completed",
        )


def test_settled_attempt_requires_truthful_terminal_process_and_remote_facts():
    common = {
        "attemptId": uuid4(),
        "runId": uuid4(),
        "projectId": uuid4(),
        "jobId": "ij_" + "e" * 24,
        "operationKey": "frame-1",
        "domain": "image",
        "requestHash": HASH,
        "packageHash": HASH,
        "profileHash": HASH,
        "reservedImageOutputs": 1,
        "imageBudgetState": "reserved",
        "state": "settled",
    }
    with pytest.raises(ValidationError):
        CodexExecAttempt(**common)
    with pytest.raises(ValidationError):
        CodexExecAttempt(
            **(common | {"imageBudgetState": "released"}),
            terminalResult="failure",
            evidenceHash=HASH,
            remoteToolState="failed",
        )

    settled_not_started = CodexExecAttempt(
        **(common | {"imageBudgetState": "released"}),
        terminalResult="not_started",
        evidenceHash=HASH,
        remoteToolState="not_applicable",
    )
    assert settled_not_started.state == "settled"

    settled_failure = CodexExecAttempt(
        **(common | {"attemptId": uuid4(), "imageBudgetState": "released"}),
        terminalResult="failure",
        evidenceHash=HASH,
        remoteToolState="failed",
        sessionId=uuid4(),
        processId=321,
        processGroupId=321,
        processBirthIdentity="pid-start-321",
        processExitCode=1,
    )
    assert settled_failure.process_exit_code == 1


def test_confirmed_remote_completion_requires_the_exact_session_id():
    with pytest.raises(ValidationError, match="exact Codex session identity"):
        CodexExecAttempt(
            attemptId=uuid4(),
            runId=uuid4(),
            projectId=uuid4(),
            jobId="ij_" + "e" * 24,
            operationKey="frame-1",
            domain="image",
            requestHash=HASH,
            packageHash=HASH,
            profileHash=HASH,
            reservedImageOutputs=1,
            imageBudgetState="consumed",
            state="failed",
            processId=321,
            processGroupId=321,
            processBirthIdentity="pid-start-321",
            processExitCode=1,
            terminalResult="failure",
            remoteToolState="completed",
            evidenceHash=HASH,
            outputHash=HASH,
            remoteOutputHash=HASH,
        )


def test_failed_cli_after_remote_completion_requires_retained_output_hash():
    with pytest.raises(ValidationError, match="retain confirmed remote ImageGen byte provenance"):
        CodexExecAttempt(
            attemptId=uuid4(),
            runId=uuid4(),
            projectId=uuid4(),
            jobId="ij_" + "g" * 24,
            operationKey="frame-1",
            domain="image",
            requestHash=HASH,
            packageHash=HASH,
            profileHash=HASH,
            reservedImageOutputs=1,
            imageBudgetState="consumed",
            state="failed",
            sessionId=uuid4(),
            processId=321,
            processGroupId=321,
            processBirthIdentity="pid-start-321",
            processExitCode=1,
            terminalResult="failure",
            remoteToolState="completed",
            evidenceHash=HASH,
            outputHash=HASH,
        )
