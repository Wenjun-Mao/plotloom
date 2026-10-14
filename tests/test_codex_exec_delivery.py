from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

import pytest

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecOutputEvidence,
    CodexExecProfile,
    CodexExecReceipt,
    output_manifest_hash,
)
from plotloom.codex_exec_delivery import publish_creative_completion
from plotloom.creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json, request_hash


def _request() -> CreativeHandoffRequest:
    return CreativeHandoffRequest.model_validate({
        "jobId": "ch_" + "a" * 20,
        "projectId": "project-demo",
        "sectionId": "section-opening",
        "stage": "outline",
        "expectedStageRevision": 3,
        "source": {"kind": "synopsis", "text": "A ferryman faces one irreversible choice."},
        "inputArtifacts": {},
        "creativeBrief": "Create a one-episode outline candidate; do not claim approval.",
    })


def _profile() -> CodexExecProfile:
    return CodexExecProfile(
        executableSha256="a" * 64,
        cliVersion="codex-cli 0.162.0-alpha.17.2",
        model="gpt-6.1-sol",
        reasoningEffort="medium",
        capabilities=("exec_json_events_v1", "session_rollout_v1", "image_gen_event_v1", "delivery_directory_write_v1"),
        instructionHash="b" * 64,
        validatorHash="c" * 64,
        sandboxProfile="read_only_with_delivery_write",
        maxRuntimeSeconds=1800,
        maxEventBytes=50_000_000,
        maxOutputBytes=20_000_000,
        maxImageOutputs=4,
    )


def _text_receipt(job_root: Path, request: CreativeHandoffRequest, profile: CodexExecProfile):
    delivery = job_root / "delivery"
    delivery.mkdir()
    candidate = canonical_json({"source": "Ferry", "params": {"episodes": 1}})
    report = b"<!doctype html><html><body>derived report</body></html>"
    (delivery / "outline.json").write_bytes(candidate)
    (delivery / "report.html").write_bytes(report)
    outputs = (
        CodexExecOutputEvidence(
            outputHash=sha256(candidate).hexdigest(), outputRelativePath="delivery/outline.json", sizeBytes=len(candidate),
        ),
        CodexExecOutputEvidence(
            outputHash=sha256(report).hexdigest(), outputRelativePath="delivery/report.html", sizeBytes=len(report),
        ),
    )
    session_id = uuid4()
    attempt_id = uuid4()
    receipt = CodexExecReceipt(
        attemptId=attempt_id,
        sessionId=session_id,
        profileHash=profile.profile_hash,
        requestHash=request_hash(request),
        packageHash="d" * 64,
        processId=123,
        processGroupId=123,
        processBirthIdentity="pid-start-123",
        processExitCode=0,
        expectedImageOutputs=0,
        evidenceHash="e" * 64,
        outputHash=output_manifest_hash(outputs),
        outputs=outputs,
        remoteToolState="not_applicable",
    )
    attempt = CodexExecAttempt(
        attemptId=attempt_id,
        runId=uuid4(),
        projectId=uuid4(),
        jobId=request.job_id,
        operationKey=request.stage,
        domain="text",
        requestHash=request_hash(request),
        packageHash="d" * 64,
        profileHash=profile.profile_hash,
        reservedImageOutputs=0,
        imageBudgetState="none",
        state="completed",
        sessionId=session_id,
        processId=123,
        processGroupId=123,
        processBirthIdentity="pid-start-123",
        processExitCode=0,
        terminalResult="success",
        remoteToolState="not_applicable",
        evidenceHash="e" * 64,
        outputHash=output_manifest_hash(outputs),
    )
    return attempt, receipt


def test_cli_creative_package_is_separate_and_host_publishes_completion(tmp_path: Path):
    request = _request()
    profile = _profile()
    exchange = CreativeHandoffExchange(tmp_path / "project" / "outputs" / "creative-handoff")
    pin = exchange.current_execution_pin(request.stage)
    paths = exchange.write_package(request, pin, executor_backend="codex_exec")
    package = Path(paths["packagePath"])
    assert json.loads((package / "request.json").read_text())["executorBackend"] == "codex_exec"
    assert not (package / "completion-manifest.example.json").exists()

    attempt, receipt = _text_receipt(package.parent, request, profile)
    manifest = publish_creative_completion(
        request=request,
        execution_pin=pin,
        code_revision="5add328ff8423f0e4ab31cce1459e208712ff20f",
        job_root=package.parent,
        attempt=attempt,
        profile=profile,
        receipt=receipt,
    )
    assert manifest.schema_version == 2
    assert manifest.executor_attempt_id == attempt.attempt_id
    delivery = exchange.read_delivery(
        request,
        pin,
        executor_backend="codex_exec",
        executor_attempt=attempt,
        executor_profile=profile,
        executor_receipt=receipt,
    )
    assert delivery is not None
    assert delivery.manifest == manifest


def test_cli_creative_delivery_requires_exact_project_receipt_and_inventory(tmp_path: Path):
    request = _request()
    profile = _profile()
    exchange = CreativeHandoffExchange(tmp_path / "project" / "outputs" / "creative-handoff")
    pin = exchange.current_execution_pin(request.stage)
    paths = exchange.write_package(request, pin, executor_backend="codex_exec")
    attempt, receipt = _text_receipt(Path(paths["packagePath"]).parent, request, profile)
    publish_creative_completion(
        request=request,
        execution_pin=pin,
        code_revision="5add328ff8423f0e4ab31cce1459e208712ff20f",
        job_root=Path(paths["packagePath"]).parent,
        attempt=attempt,
        profile=profile,
        receipt=receipt,
    )
    with pytest.raises(CreativeHandoffError, match="exact project attempt"):
        exchange.read_delivery(request, pin, executor_backend="codex_exec")

    altered_receipt = receipt.model_copy(update={"profile_hash": "f" * 64})
    with pytest.raises(CreativeHandoffError, match="receipt is invalid"):
        exchange.read_delivery(
            request, pin, executor_backend="codex_exec", executor_attempt=attempt,
            executor_profile=profile, executor_receipt=altered_receipt,
        )
