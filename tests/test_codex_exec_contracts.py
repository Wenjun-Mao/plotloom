from uuid import uuid4

import pytest
from pydantic import ValidationError

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecImageEvidence,
    CodexExecOutputEvidence,
    CodexExecProfile,
    CodexExecReceipt,
    SpecialistChatExecutor,
    assert_receipt_matches_attempt,
    image_arguments_hash,
    output_manifest_hash,
)

HASH = "a" * 64


def output_evidence(path="delivery/outputs/frame.png", digest="b" * 64):
    return CodexExecOutputEvidence(outputHash=digest, outputRelativePath=path, sizeBytes=128)


def image_args_hash(*, prompt_hash="c" * 64, reference_hashes=("d" * 64,), transparent=False, prior=0):
    return image_arguments_hash(
        prompt_hash=prompt_hash,
        reference_hashes=reference_hashes,
        transparent_background=transparent,
        num_last_images_to_include=prior,
    )


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
        "state": "settled",
    }
    with pytest.raises(ValidationError):
        CodexExecAttempt(**common)
    with pytest.raises(ValidationError):
        CodexExecAttempt(
            **common,
            terminalResult="failure",
            evidenceHash=HASH,
            remoteToolState="failed",
        )

    settled_not_started = CodexExecAttempt(
        **common,
        terminalResult="not_started",
        evidenceHash=HASH,
        remoteToolState="not_applicable",
    )
    assert settled_not_started.state == "settled"

    settled_failure = CodexExecAttempt(
        **(common | {"attemptId": uuid4()}),
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
            state="failed",
            processId=321,
            processGroupId=321,
            processBirthIdentity="pid-start-321",
            processExitCode=1,
            terminalResult="failure",
            remoteToolState="completed",
            evidenceHash=HASH,
            outputHash=HASH,
        )


def test_image_event_and_receipt_bind_exact_attempt_session_and_bytes():
    attempt_id, session_id = uuid4(), uuid4()
    output = output_evidence()
    manifest_hash = output_manifest_hash([output])
    event = CodexExecImageEvidence(
        attemptId=attempt_id,
        sessionId=session_id,
        callId="call_1",
        eventType="image_gen.generation",
        eventStatus="completed",
        argumentsHash=image_args_hash(),
        promptHash="c" * 64,
        referenceHashes=["d" * 64],
        transparentBackground=False,
        numLastImagesToInclude=0,
        outputHash=output.output_hash,
        outputRelativePath="delivery/outputs/frame.png",
    )
    receipt = CodexExecReceipt(
        attemptId=attempt_id,
        sessionId=session_id,
        profileHash=HASH,
        requestHash=HASH,
        packageHash=HASH,
        processId=321,
        processGroupId=321,
        processBirthIdentity="pid-start-321",
        processExitCode=0,
        expectedImageOutputs=1,
        evidenceHash=HASH,
        outputHash=manifest_hash,
        outputs=[output],
        imageEvidence=[event],
        remoteToolState="completed",
    )
    assert receipt.image_evidence[0].session_id == session_id
    attempt = CodexExecAttempt(
        attemptId=attempt_id,
        runId=uuid4(),
        projectId=uuid4(),
        jobId="ij_" + "f" * 24,
        operationKey="frame-1",
        domain="image",
        requestHash=HASH,
        packageHash=HASH,
        profileHash=HASH,
        reservedImageOutputs=1,
        state="completed",
        sessionId=session_id,
        processId=321,
        processGroupId=321,
        processBirthIdentity="pid-start-321",
        processExitCode=0,
        terminalResult="success",
        remoteToolState="completed",
        evidenceHash=HASH,
        outputHash=manifest_hash,
    )
    assert_receipt_matches_attempt(attempt, receipt)
    with pytest.raises(ValueError, match="exact project attempt"):
        assert_receipt_matches_attempt(
            attempt.model_copy(update={"profile_hash": "c" * 64}), receipt
        )
    with pytest.raises(ValidationError, match="process ownership"):
        assert_receipt_matches_attempt(
            attempt.model_copy(update={"process_birth_identity": None}), receipt
        )
    with pytest.raises(ValidationError, match="output hash must bind"):
        CodexExecReceipt(
            attemptId=attempt_id,
            sessionId=session_id,
            profileHash=HASH,
            requestHash=HASH,
            packageHash=HASH,
            processId=321,
            processGroupId=321,
            processBirthIdentity="pid-start-321",
            processExitCode=0,
            expectedImageOutputs=1,
            evidenceHash=HASH,
            outputHash=HASH,
            outputs=[output],
            imageEvidence=[event],
            remoteToolState="completed",
        )
    different_bytes = output_evidence(digest="c" * 64)
    with pytest.raises(ValidationError, match="exact output path and byte hash"):
        CodexExecReceipt(
            attemptId=attempt_id,
            sessionId=session_id,
            profileHash=HASH,
            requestHash=HASH,
            packageHash=HASH,
            processId=321,
            processGroupId=321,
            processBirthIdentity="pid-start-321",
            processExitCode=0,
            expectedImageOutputs=1,
            evidenceHash=HASH,
            outputHash=output_manifest_hash([different_bytes]),
            outputs=[different_bytes],
            imageEvidence=[event],
            remoteToolState="completed",
        )
    with pytest.raises(AttributeError):
        receipt.image_evidence.append(event)
    with pytest.raises(AttributeError):
        event.reference_hashes.append("e" * 64)
    with pytest.raises(ValidationError):
        event.output_hash = "f" * 64
    with pytest.raises(ValidationError):
        event.output_relative_path = "../frame.png"
    with pytest.raises(ValidationError):
        CodexExecReceipt(
            attemptId=attempt_id,
            sessionId=uuid4(),
            profileHash=HASH,
            requestHash=HASH,
            packageHash=HASH,
            processId=321,
            processGroupId=321,
            processBirthIdentity="pid-start-321",
            processExitCode=0,
            expectedImageOutputs=1,
            evidenceHash=HASH,
            outputHash=manifest_hash,
            outputs=[output],
            imageEvidence=[event],
            remoteToolState="completed",
        )


@pytest.mark.parametrize(
    "path",
    [
        "delivery/outputs",
        "delivery\\outputs\\frame.png",
        "delivery/outputs/../frame.png",
    ],
)
def test_image_event_rejects_noncanonical_or_directory_only_output_paths(path):
    with pytest.raises(ValidationError):
        CodexExecImageEvidence(
            attemptId=uuid4(),
            sessionId=uuid4(),
            callId="call_1",
            eventType="image_gen.generation",
            eventStatus="completed",
            argumentsHash=image_args_hash(),
            promptHash="c" * 64,
            referenceHashes=["d" * 64],
            transparentBackground=False,
            outputHash="b" * 64,
            outputRelativePath=path,
        )


@pytest.mark.parametrize("value", ["not-a-hash", "sk-proj-privatecredential"])
def test_image_event_rejects_unhashed_or_credential_shaped_reference_evidence(value):
    with pytest.raises(ValidationError):
        CodexExecImageEvidence(
            attemptId=uuid4(),
            sessionId=uuid4(),
            callId="call_1",
            eventType="image_gen.generation",
            eventStatus="completed",
            argumentsHash=image_args_hash(reference_hashes=(value,)),
            promptHash="c" * 64,
            referenceHashes=[value],
            transparentBackground=False,
            outputHash="b" * 64,
            outputRelativePath="delivery/outputs/frame.png",
        )


def test_image_argument_hash_must_bind_normalized_actual_arguments():
    with pytest.raises(ValidationError, match="argument hash"):
        CodexExecImageEvidence(
            attemptId=uuid4(),
            sessionId=uuid4(),
            callId="call_1",
            eventType="image_gen.generation",
            eventStatus="completed",
            argumentsHash=HASH,
            promptHash="c" * 64,
            referenceHashes=["d" * 64],
            transparentBackground=False,
            numLastImagesToInclude=0,
            outputHash="b" * 64,
            outputRelativePath="delivery/outputs/frame.png",
        )


def test_nonzero_process_exit_cannot_be_success_receipt():
    output = output_evidence()
    with pytest.raises(ValidationError):
        CodexExecReceipt(
            attemptId=uuid4(),
            sessionId=uuid4(),
            profileHash=HASH,
            requestHash=HASH,
            packageHash=HASH,
            processId=321,
            processGroupId=321,
            processBirthIdentity="pid-start-321",
            processExitCode=1,
            expectedImageOutputs=0,
            evidenceHash=HASH,
            outputHash=output_manifest_hash([output]),
            outputs=[output],
            remoteToolState="not_applicable",
        )
