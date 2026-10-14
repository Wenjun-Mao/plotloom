from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from plotloom.autopilot_brief_style import brief_stage_instructions, freeze_brief_style
from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecOutputEvidence,
    CodexExecProfile,
    CodexExecReceipt,
    output_manifest_hash,
)
from plotloom.codex_exec_validation import (
    CodexExecTextValidationEvidence,
    CodexExecValidationStepEvidence,
    validation_plan_from_package,
)
from plotloom.codex_exec_delivery import publish_creative_completion
from plotloom.creative_handoff_contracts import (
    CreativeHandoffError,
    CreativeHandoffRequest,
)
from plotloom.creative_handoff_exchange import (
    CreativeHandoffExchange,
    canonical_json,
    request_hash,
)
from plotloom.storyboard_brief_style import (
    freeze_storyboard_brief_style,
    storyboard_brief_instructions,
)

PLOTLOOM_CODE_REVISION = "e" * 40


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


def _request_for_stage(stage: str) -> CreativeHandoffRequest:
    artifacts = {
        "characters": {"cast-style-contract.json": {"style": "live-action"}},
        "art": {"cast.json": {"characters": []}, "art-style-contract.json": {"style": "live-action"}},
        "script": {
            "outline.json": {"episodes": []},
            "art.json": {"scenes": []},
            "cast.json": {"characters": []},
        },
        "storyboard": {
            "script.json": {"episodes": []},
            "outline.json": {"episodes": []},
            "cast.json": {"characters": []},
            "art.json": {"scenes": []},
        },
    }.get(stage, {})
    return _request().model_copy(update={"stage": stage, "input_artifacts": artifacts})


def _profile() -> CodexExecProfile:
    return CodexExecProfile(
        contractVersion="plotloom.codex-exec.v7",
        executableSha256="a" * 64,
        cliVersion="codex-cli 0.162.0-alpha.17.2",
        model="gpt-6.1-sol",
        reasoningEffort="medium",
        capabilities=(
            "exec_json_events_v1", "session_rollout_v1", "image_gen_event_v1",
            "image_reference_view_v1", "delivery_directory_write_v1",
        ),
        instructionHash="b" * 64,
        validatorHash="c" * 64,
        authenticationStore="file",
        permissionProfile="plotloom_autopilot_delivery_v5",
        toolProfile="plotloom_autopilot_tools_v4",
        textValidatorRuntimeProfile="node_openssl_private_zsh_tmp_and_checked_python_v3",
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
    package_request = json.loads((job_root / "package" / "request.json").read_bytes())
    plan = validation_plan_from_package(package_request)
    validation = CodexExecTextValidationEvidence(
        planHash=plan.plan_hash,
        profileHash=profile.profile_hash,
        validatorHash=profile.validator_hash,
        requestHash=request_hash(request),
        packageHash="d" * 64,
        sourceRevision=PLOTLOOM_CODE_REVISION,
        candidateFilename="outline.json",
        candidateHash=sha256(candidate).hexdigest(),
        candidateSizeBytes=len(candidate),
        reportFilename="report.html",
        reportHash=sha256(report).hexdigest(),
        reportSizeBytes=len(report),
        steps=(
            CodexExecValidationStepEvidence(
                stepId="validate", argvHash="1" * 64, exitCode=0,
                stdoutHash="2" * 64, stdoutSizeBytes=0,
                stderrHash="3" * 64, stderrSizeBytes=0, durationMs=1,
            ),
            CodexExecValidationStepEvidence(
                stepId="render", argvHash="4" * 64, exitCode=0,
                stdoutHash=sha256(report).hexdigest(), stdoutSizeBytes=len(report),
                stderrHash="5" * 64, stderrSizeBytes=0, durationMs=1,
            ),
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
        plotloomCodeRevision=PLOTLOOM_CODE_REVISION,
        validationPlanHash=plan.plan_hash,
        processId=123,
        processGroupId=123,
        processBirthIdentity="pid-start-123",
        processExitCode=0,
        expectedImageOutputs=0,
        evidenceHash="e" * 64,
        outputHash=output_manifest_hash(outputs),
        outputs=outputs,
        textValidation=validation,
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
        plotloomCodeRevision=PLOTLOOM_CODE_REVISION,
        validationPlanHash=plan.plan_hash,
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
    paths = exchange.write_package(
        request, pin, executor_backend="codex_exec",
        plotloom_code_revision=PLOTLOOM_CODE_REVISION,
    )
    package = Path(paths["packagePath"])
    package_request = json.loads((package / "request.json").read_text())
    assert package_request["executorBackend"] == "codex_exec"
    assert package_request["plotloomCodeRevision"] == PLOTLOOM_CODE_REVISION
    assert package_request["executionPin"]["upstreamRevision"] != PLOTLOOM_CODE_REVISION
    assert not (package / "completion-manifest.example.json").exists()

    attempt, receipt = _text_receipt(package.parent, request, profile)
    manifest = publish_creative_completion(
        request=request,
        execution_pin=pin,
        code_revision=PLOTLOOM_CODE_REVISION,
        job_root=package.parent,
        attempt=attempt,
        profile=profile,
        receipt=receipt,
    )
    assert manifest.schema_version == 3
    assert manifest.validation_plan_hash == attempt.validation_plan_hash
    assert manifest.validation_evidence_hash == receipt.text_validation.evidence_hash
    assert manifest.executor_attempt_id == attempt.attempt_id
    delivery = exchange.read_delivery(
        request,
        pin,
        executor_backend="codex_exec",
        executor_attempt=attempt,
        executor_profile=profile,
        executor_receipt=receipt,
        plotloom_code_revision=PLOTLOOM_CODE_REVISION,
    )
    assert delivery is not None
    assert delivery.manifest == manifest
    assert delivery.manifest.executor_provenance.code_revision == PLOTLOOM_CODE_REVISION
    assert delivery.manifest.executor_provenance.upstream_revision == pin["upstreamRevision"]
    assert delivery.manifest.executor_provenance.code_revision != delivery.manifest.executor_provenance.upstream_revision
    with pytest.raises(ValueError, match="frozen creative request or profile"):
        publish_creative_completion(
            request=request,
            execution_pin=pin,
            code_revision="f" * 40,
            job_root=package.parent,
            attempt=attempt,
            profile=profile,
            receipt=receipt,
            publish_marker=False,
        )
    with pytest.raises(CreativeHandoffError, match="existing package differs"):
        exchange.read_delivery(
            request, pin, executor_backend="codex_exec", executor_attempt=attempt,
            executor_profile=profile, executor_receipt=receipt,
            plotloom_code_revision="f" * 40,
        )


def test_cli_branch_assignment_uses_pinned_read_only_source_paths(tmp_path: Path):
    request = _request_for_stage("branches")
    exchange = CreativeHandoffExchange(tmp_path / "project" / "outputs" / "creative-handoff")
    pin = exchange.current_execution_pin(request.stage)
    paths = exchange.write_package(request, pin, executor_backend="codex_exec",
        plotloom_code_revision=PLOTLOOM_CODE_REVISION)
    package = Path(paths["packagePath"])
    instructions = (package / "COPY_ASSIGNMENT.txt").read_text(encoding="utf-8")
    package_request = json.loads((package / "request.json").read_bytes())
    plan = validation_plan_from_package(package_request)

    assert plan.steps[0].program == "uv"
    assert plan.steps[0].argv[:7] == (
        "run", "--project", "{source}", "--locked", "--no-sync", "python",
        "{source}/scripts/branch_suggestion.py",
    )
    assert plan.steps[1].argv[7] == "render"
    assert '`"$PLOTLOOM_SOURCE_ROOT/third_party/shuohao-skills/skills/novel-outline"`' in instructions
    assert "Output strictly inputs/branch-schema.json" in instructions
    assert "Preserve every planned node, choice-option and join ID" in instructions
    assert "Disclose ambiguous proposals in clarifications" in instructions
    assert "From the repository root" not in instructions
    assert "do not run validators or renderers" in instructions
    assert "branch_suggestion.py validate" not in instructions


@pytest.mark.parametrize(
    ("stage", "skill_directory"),
    [
        ("outline", "novel-outline"),
        ("characters", "novel-characters"),
        ("art", "novel-art"),
        ("script", "novel-script"),
        ("storyboard", "novel-storyboard"),
    ],
)
def test_cli_assignment_maps_base_dir_to_the_pinned_skill_directory(
    tmp_path: Path, stage: str, skill_directory: str
):
    request = _request_for_stage(stage)
    exchange = CreativeHandoffExchange(tmp_path / "project" / "outputs" / "creative-handoff")
    pin = exchange.current_execution_pin(request.stage)
    paths = exchange.write_package(request, pin, executor_backend="codex_exec",
        plotloom_code_revision=PLOTLOOM_CODE_REVISION)
    instructions = (Path(paths["packagePath"]) / "COPY_ASSIGNMENT.txt").read_text(encoding="utf-8")

    expected = f'`"$PLOTLOOM_SOURCE_ROOT/third_party/shuohao-skills/skills/{skill_directory}"`'
    assert expected in instructions
    assert "substitute the checkout root for `{baseDir}`" not in instructions


def _saved_brief_request(stage: str) -> CreativeHandoffRequest:
    parent = freeze_brief_style("hand-cut paper collage")
    if stage == "characters":
        input_artifacts = {"cast-style-contract.json": parent}
        creative_brief = brief_stage_instructions("cast")
    elif stage == "art":
        input_artifacts = {"cast.json": {}, "art-style-contract.json": parent}
        creative_brief = brief_stage_instructions("art")
    else:
        input_artifacts = {
            "storyboard-style-contract.json": freeze_storyboard_brief_style(parent),
        }
        creative_brief = storyboard_brief_instructions()
    source = (
        {"acceptedScriptRevision": 1, "acceptedScriptContentHash": "a" * 64}
        if stage == "storyboard"
        else {"kind": "synopsis", "text": "A ferryman faces one irreversible choice."}
    )
    value = _request().model_dump(mode="json", by_alias=True) | {
        "stage": stage,
        "source": source,
        "inputArtifacts": input_artifacts,
        "creativeBrief": creative_brief,
    }
    return CreativeHandoffRequest.model_validate(value)


@pytest.mark.parametrize(
    ("stage", "contract_filename", "adapter"),
    [
        (
            "characters", "cast-style-contract.json", "brief-cast-style.mjs",
        ),
        (
            "art", "art-style-contract.json", "brief-art-style.mjs",
        ),
        (
            "storyboard", "storyboard-style-contract.json", "brief-storyboard-style.mjs",
        ),
    ],
)
def test_cli_saved_brief_package_routes_neutral_validator_from_delivery(
    tmp_path: Path, stage: str, contract_filename: str, adapter: str,
):
    request = _saved_brief_request(stage)
    exchange = CreativeHandoffExchange(tmp_path / "project" / "outputs" / "creative-handoff")
    pin = exchange.current_execution_pin(request.stage)
    paths = exchange.write_package(request, pin, executor_backend="codex_exec",
        plotloom_code_revision=PLOTLOOM_CODE_REVISION)
    package = Path(paths["packagePath"])
    instructions = (package / "COPY_ASSIGNMENT.txt").read_text(encoding="utf-8")
    package_request = json.loads((package / "request.json").read_text(encoding="utf-8"))
    plan = validation_plan_from_package(package_request)

    assert package_request["inputArtifacts"][contract_filename] == request.input_artifacts[contract_filename]
    assert (package / "inputs" / contract_filename).is_file()
    assert plan.route == "saved_brief"
    assert plan.steps[0].program == "node"
    assert plan.steps[0].argv[0] == f"{{source}}/scripts/{adapter}"
    assert "neutral Plotloom adapter" in instructions
    assert "do not invoke the adapter or write the report yourself" in instructions
    assert "request.creativeBrief supplies creative, style, source and candidate requirements" in instructions
    assert "manual specialist-chat workflow only" in instructions
    assert "host follows only the exact frozen validation plan" in instructions
    assert "run exactly:" in request.creative_brief
    assert "render " + stage + ".json" not in instructions
    if stage == "characters":
        assert "/scripts/cast-style.mjs" not in instructions
    elif stage == "art":
        assert "/scripts/art-style.mjs" not in instructions


@pytest.mark.parametrize(
    ("stage", "required_instructions"),
    [
        (
            "bridge-intent",
            (
                "the local native intent contract replaces upstream stage authoring",
                "every frozen target exactly once",
                "only id and suggestedText",
            ),
        ),
        (
            "bridge-presentation",
            (
                "exhaustive ordered Unicode-codepoint ownership spans",
                "faithful rendering and required reasons",
                "Suggestions do not approve presentation or production",
            ),
        ),
    ],
)
def test_codex_assignments_preserve_native_bridge_stage_contracts(
    tmp_path: Path, stage: str, required_instructions: tuple[str, ...]
):
    request = _request().model_copy(update={"stage": stage})
    exchange = CreativeHandoffExchange(tmp_path / "project" / "outputs" / "creative-handoff")
    # This covers package text only; current_execution_pin correctly rejects
    # uncommitted native bridge sources in a developer worktree.
    pin = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}
    paths = exchange.write_package(request, pin, executor_backend="codex_exec",
        plotloom_code_revision=PLOTLOOM_CODE_REVISION)
    instructions = (Path(paths["packagePath"]) / "COPY_ASSIGNMENT.txt").read_text(encoding="utf-8")

    for required in required_instructions:
        assert required in instructions


def test_cli_creative_delivery_requires_exact_project_receipt_and_inventory(tmp_path: Path):
    request = _request()
    profile = _profile()
    exchange = CreativeHandoffExchange(tmp_path / "project" / "outputs" / "creative-handoff")
    pin = exchange.current_execution_pin(request.stage)
    paths = exchange.write_package(request, pin, executor_backend="codex_exec",
        plotloom_code_revision=PLOTLOOM_CODE_REVISION)
    attempt, receipt = _text_receipt(Path(paths["packagePath"]).parent, request, profile)
    publish_creative_completion(
        request=request,
        execution_pin=pin,
        code_revision=PLOTLOOM_CODE_REVISION,
        job_root=Path(paths["packagePath"]).parent,
        attempt=attempt,
        profile=profile,
        receipt=receipt,
    )
    with pytest.raises(CreativeHandoffError, match="exact project attempt"):
        exchange.read_delivery(request, pin, executor_backend="codex_exec",
            plotloom_code_revision=PLOTLOOM_CODE_REVISION)

    altered_receipt = receipt.model_copy(update={"profile_hash": "f" * 64})
    with pytest.raises(CreativeHandoffError, match="receipt is invalid"):
        exchange.read_delivery(
            request, pin, executor_backend="codex_exec", executor_attempt=attempt,
            executor_profile=profile, executor_receipt=altered_receipt,
            plotloom_code_revision=PLOTLOOM_CODE_REVISION,
        )
