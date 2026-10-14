"""Image event, output receipt and byte-inventory contract tests."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecImageEvidence,
    CodexExecOutputEvidence,
    CodexExecReceipt,
    CodexExecReferenceViewEvidence,
    assert_receipt_matches_attempt,
    image_arguments_hash,
    output_manifest_hash,
)

HASH = "a" * 64


def output_evidence(path="delivery/outputs/frame.png", digest="b" * 64):
    return CodexExecOutputEvidence(outputHash=digest, outputRelativePath=path, sizeBytes=128)


def reference_view_evidence():
    return CodexExecReferenceViewEvidence(
        role="parent_output",
        packageRelativePath="references/reference.png",
        referenceHash="d" * 64,
        contentSha256="e" * 64,
        contentSizeBytes=64,
        callId="view_call_1",
        eventId="view_event_1",
        callOrdinal=1,
        eventOrdinal=2,
        outputOrdinal=3,
    )


def image_args_hash(*, prompt_hash="c" * 64, reference_hashes=("d" * 64,), transparent=False, prior=0):
    return image_arguments_hash(
        prompt_hash=prompt_hash,
        reference_hashes=reference_hashes,
        transparent_background=transparent,
        num_last_images_to_include=prior,
    )


def test_image_event_and_receipt_bind_exact_attempt_session_and_bytes():
    attempt_id, session_id = uuid4(), uuid4()
    output = output_evidence()
    manifest_hash = output_manifest_hash([output])
    event = CodexExecImageEvidence(
        attemptId=attempt_id,
        sessionId=session_id,
        callId="call_1",
        callOrdinal=4,
        eventId="event_1",
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
        plotloomCodeRevision="1" * 40,
        processId=321,
        processGroupId=321,
        processBirthIdentity="pid-start-321",
        processExitCode=0,
        expectedImageOutputs=1,
        evidenceHash=HASH,
        outputHash=manifest_hash,
        outputs=[output],
        imageEvidence=[event],
        referenceViews=[reference_view_evidence()],
        remoteOutputHash=output.output_hash,
        remoteToolState="completed",
    )
    assert receipt.image_evidence[0].session_id == session_id
    with pytest.raises(ValidationError, match="serial image receipt must bind"):
        CodexExecReceipt.model_validate(
            receipt.model_dump(mode="python") | {"remote_output_hash": "e" * 64}
        )
    with pytest.raises(ValidationError, match="exact host-recorded view order"):
        CodexExecReceipt.model_validate(
            receipt.model_dump(by_alias=True) | {"referenceViews": []}
        )
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
        plotloomCodeRevision="1" * 40,
        reservedImageOutputs=1,
        imageBudgetState="consumed",
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
        remoteOutputHash=output.output_hash,
    )
    assert_receipt_matches_attempt(attempt, receipt)
    with pytest.raises(ValueError, match="exact project attempt"):
        assert_receipt_matches_attempt(
            attempt.model_copy(update={"profile_hash": "c" * 64}), receipt
        )
    with pytest.raises(ValueError, match="exact project attempt"):
        assert_receipt_matches_attempt(
            attempt.model_copy(update={"plotloom_code_revision": "2" * 40}), receipt
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
            referenceViews=[reference_view_evidence()],
            remoteOutputHash=output.output_hash,
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
            referenceViews=[reference_view_evidence()],
            remoteOutputHash=event.output_hash,
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
            referenceViews=[reference_view_evidence()],
            remoteOutputHash=output.output_hash,
            remoteToolState="completed",
        )

    overlapped_second_view = reference_view_evidence().model_copy(update={
        "package_relative_path": "references/other.png",
        "reference_hash": "f" * 64,
        "call_id": "view_call_2",
        "event_id": "view_event_2",
        "call_ordinal": 3,
        "event_ordinal": 4,
        "output_ordinal": 5,
    })
    later_image_event = event.model_copy(update={
        "call_ordinal": 6,
        "reference_hashes": ("d" * 64, "f" * 64),
        "arguments_hash": image_args_hash(reference_hashes=("d" * 64, "f" * 64)),
    })
    invalid_timeline = receipt.model_dump(mode="python") | {
        "image_evidence": (later_image_event,),
        "reference_views": (reference_view_evidence(), overlapped_second_view),
    }
    with pytest.raises(ValidationError, match="unique and ordered"):
        CodexExecReceipt.model_validate(invalid_timeline)


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
            callOrdinal=1,
            eventId="event_1",
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
            callOrdinal=1,
            eventId="event_1",
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
            callOrdinal=1,
            eventId="event_1",
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


@pytest.mark.parametrize("path", ["delivery/outline.json", "delivery/report.html", "delivery/completion.json"])
def test_text_receipt_output_inventory_accepts_the_existing_creative_delivery_layout(path):
    assert output_evidence(path).output_relative_path == path


@pytest.mark.parametrize("path", ["delivery", "delivery/../outside", "delivery\\outline.json", "../delivery/file.json"])
def test_receipt_output_inventory_rejects_paths_outside_delivery_files(path):
    with pytest.raises(ValidationError):
        output_evidence(path)
