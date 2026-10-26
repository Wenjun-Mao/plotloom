"""Immutable output/receipt construction from already validated terminal inputs."""
from __future__ import annotations
from plotloom.codex_exec_contracts import CodexExecOutputEvidence, CodexExecReceipt, output_manifest_hash, transition_exec_attempt
from plotloom.codex_exec_runtime import CodexExecRuntimeError


def build_terminal_receipt(*, attempt, profile, current, stream, session, outputs,
                           image_facts, remote_state, reference_views, text_validation,
                           process_evidence_hash, exit_code):
    output_evidence = tuple(CodexExecOutputEvidence(
        outputHash=item.sha256,
        outputRelativePath=f"delivery/{item.relative_path}",
        sizeBytes=item.size_bytes,
    ) for item in outputs)
    if not output_evidence:
        raise CodexExecRuntimeError("Codex Exec produced no delivery files")
    output_hash = output_manifest_hash(output_evidence)
    evidence_hash = process_evidence_hash
    if text_validation is not None:
        from hashlib import sha256
        evidence_hash = sha256(
            f"{evidence_hash}:{text_validation.evidence_hash}".encode("ascii")
        ).hexdigest()
    completed = transition_exec_attempt(
        current,
        state="completed",
        session_id=stream.session_id,
        process_exit_code=exit_code,
        terminal_result="success",
        remote_tool_state=remote_state,
        evidence_hash=evidence_hash,
        output_hash=output_hash,
        remote_output_hash=image_facts[0].output_hash if image_facts else None,
        image_budget_state="consumed" if attempt.domain == "image" else "none",
    )
    receipt = CodexExecReceipt(
        attemptId=attempt.attempt_id,
        sessionId=stream.session_id,
        profileHash=profile.profile_hash,
        requestHash=attempt.request_hash,
        packageHash=attempt.package_hash,
        plotloomCodeRevision=attempt.plotloom_code_revision,
        processId=current.process_id,
        processGroupId=current.process_group_id,
        processBirthIdentity=current.process_birth_identity,
        processExitCode=exit_code,
        expectedImageOutputs=attempt.reserved_image_outputs,
        evidenceHash=evidence_hash,
        outputHash=output_hash,
        outputs=output_evidence,
        imageEvidence=image_facts,
        referenceViews=reference_views,
        validationPlanHash=attempt.validation_plan_hash,
        textValidation=text_validation,
        remoteOutputHash=completed.remote_output_hash,
        remoteToolState=remote_state,
    )
    from plotloom.codex_exec_contracts import assert_receipt_matches_attempt
    assert_receipt_matches_attempt(completed, receipt)
    return completed, receipt


def evidence_hash_for_process(stdout_path, stderr_path, transcript_hash, exit_code):
    from hashlib import sha256
    digest = sha256()
    for path in (stdout_path, stderr_path):
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    digest.update(transcript_hash.encode("ascii"))
    digest.update(str(exit_code).encode("ascii"))
    return digest.hexdigest()
