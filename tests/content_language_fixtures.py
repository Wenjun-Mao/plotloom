"""Explicit synthetic checking evidence for offline contract tests, never live proof."""
from hashlib import sha256
from uuid import uuid4

from plotloom.codex_exec_contracts import (
    CodexExecOutputEvidence,
    CodexExecReceipt,
    output_manifest_hash,
    transition_exec_attempt,
)
from plotloom.codex_exec_delivery import publish_creative_completion
from plotloom.codex_exec_validation import (
    CodexExecTextValidationEvidence,
    CodexExecValidationStepEvidence,
)
from plotloom.content_language_contract import (
    CHECK_INPUT,
    CHECK_OPERATION,
    ContentLanguageResult,
    freeze_language_candidate,
    render_language_report,
)
from plotloom.creative_handoff_contracts import (
    CREATIVE_CANDIDATE_FILENAMES,
    CreativeHandoffRequest,
)
from plotloom.creative_handoff_identity import canonical_json
from plotloom.language_policy import LANGUAGE_CONTRACT_FILENAME, freeze_request_language


def original_request(stage="outline", *, locale="zh-CN", project_id=None):
    request = CreativeHandoffRequest(job_id="ch_" + uuid4().hex, project_id=project_id or str(uuid4()),
        section_id="story", stage=stage, expected_stage_revision=0,
        source={"title": "The Ferry", "text": 'Mara says "Keep the light on." 这是来源。',
                "adaptationIntent": "Preserve Mara as a proper name and the exact quoted English words."},
        creative_brief="Write the requested stage from the complete sources.")
    freeze_request_language(request, locale)
    return request


def checking_request(original, candidate):
    frozen = freeze_language_candidate(original, candidate)
    return CreativeHandoffRequest(job_id="ch_" + uuid4().hex, project_id=original.project_id,
        section_id=original.section_id, stage=original.stage, expected_stage_revision=0,
        source={"operation": CHECK_OPERATION, "candidateJobId": original.job_id, "bindingHash": frozen["bindingHash"]},
        input_artifacts={CHECK_INPUT: frozen, LANGUAGE_CONTRACT_FILENAME: frozen["languageContract"],
                         "content-language-schema.json": ContentLanguageResult.model_json_schema(by_alias=True)},
        creative_brief="Independently review the complete candidate.")


def result_for(request, *, rejected_path=None, uncertain_path=None):
    inventory = request.input_artifacts[CHECK_INPUT]["inventory"]
    from plotloom.content_language_classifier import string_leaves
    leaves = dict(string_leaves(request.input_artifacts[CHECK_INPUT]["candidate"]))
    coverage = [{key: item[key] for key in ("path", "sha256", "role")} | {
        "verdict": ("reject" if item["path"] == rejected_path else "uncertain" if item["path"] == uncertain_path else
                    "pass" if item["role"] == "authored_prose" and leaves[item["path"]].strip() else "not_applicable"),
        "exceptions": []} for item in inventory]
    findings = []
    for path, code in ((rejected_path, "wrong_language"), (uncertain_path, "uncertain_language")):
        if path:
            findings.append({"code": code, "span": {"path": path, "start": 0, "end": len(leaves[path]), "text": leaves[path]},
                             "explanation": "Synthetic test finding; not an actual model judgment."})
    return {"contract": "plotloom.content-language-check.v1", "bindingHash": request.source["bindingHash"],
            "verdict": "reject" if rejected_path else "uncertain" if uncertain_path else "pass",
            "coverage": coverage, "findings": findings}


def synthetic_text_receipt(attempt, profile, filename, raw, report):
    """A test fixture's explicit successful native receipt, with exact output bytes."""
    outputs = tuple(CodexExecOutputEvidence(output_relative_path="delivery/" + name,
        output_hash=sha256(content).hexdigest(), size_bytes=len(content))
        for name, content in sorted(((filename, raw), ("report.html", report))))
    proof = CodexExecTextValidationEvidence(plan_hash=attempt.validation_plan_hash,
        profile_hash=profile.profile_hash, validator_hash=profile.validator_hash, request_hash=attempt.request_hash,
        package_hash=attempt.package_hash, source_revision=attempt.plotloom_code_revision,
        candidate_filename=filename, candidate_hash=sha256(raw).hexdigest(), candidate_size_bytes=len(raw),
        report_hash=sha256(report).hexdigest(), report_size_bytes=len(report), steps=(
            CodexExecValidationStepEvidence(step_id="validate", argv_hash="1"*64, exit_code=0,
                stdout_hash=sha256(b"").hexdigest(), stdout_size_bytes=0, stderr_hash="2"*64, stderr_size_bytes=0, duration_ms=1),
            CodexExecValidationStepEvidence(step_id="render", argv_hash="3"*64, exit_code=0,
                stdout_hash=sha256(report).hexdigest(), stdout_size_bytes=len(report), stderr_hash="2"*64,
                stderr_size_bytes=0, duration_ms=1)))
    done = transition_exec_attempt(attempt, state="completed", session_id=uuid4(), process_id=123,
        process_group_id=123, process_birth_identity="synthetic-checker-test-process", process_exit_code=0,
        terminal_result="success", remote_tool_state="not_applicable", evidence_hash="f"*64,
        output_hash=output_manifest_hash(outputs))
    receipt = CodexExecReceipt(**{name: getattr(done, name) for name in (
        "attempt_id", "session_id", "profile_hash", "request_hash", "package_hash", "plotloom_code_revision",
        "validation_plan_hash", "process_id", "process_group_id", "process_birth_identity", "process_exit_code",
        "evidence_hash", "output_hash", "remote_tool_state")}, expected_image_outputs=0, outputs=outputs, text_validation=proof)
    return done, receipt


def completed_check(store, job_id, result):
    """Publish a byte-bound fake host receipt through the real offline exchange."""
    request, data = store.repository.content_language.load(store.manifest.project_id, job_id)
    from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecProfile
    attempt, profile = CodexExecAttempt.model_validate(data["attempt"]), CodexExecProfile.model_validate(data["profile"])
    exchange, pin = store.creative_handoff_exchange(), store.creative_handoff_execution_pin(request)
    paths = exchange.write_package(request, pin, executor_backend="codex_exec", plotloom_code_revision=attempt.plotloom_code_revision)
    from pathlib import Path
    root = Path(paths["packagePath"]).parent
    delivery = root / "delivery"
    delivery.mkdir(exist_ok=True)
    filename = CREATIVE_CANDIDATE_FILENAMES[request.stage]
    raw, report = canonical_json(result), render_language_report(request, result)
    (delivery / filename).write_bytes(raw)
    (delivery / "report.html").write_bytes(report)
    done, receipt = synthetic_text_receipt(attempt, profile, filename, raw, report)
    publish_creative_completion(request=request, execution_pin=pin, code_revision=attempt.plotloom_code_revision,
        job_root=root, attempt=done, profile=profile, receipt=receipt)
    delivery = exchange.read_delivery(request, pin, executor_backend="codex_exec", executor_attempt=done,
        executor_profile=profile, executor_receipt=receipt, plotloom_code_revision=attempt.plotloom_code_revision)
    store.repository.content_language.observe(request.project_id, job_id, attempt=done, receipt=receipt,
                                              delivery=delivery, result_json=raw.decode())
    return done, receipt


def install_synthetic_language_check(store, original, candidate):
    """Explicit test-only pass: host proof is synthetic, never product evidence."""
    from types import SimpleNamespace

    from plotloom.content_language_service import ContentLanguageService
    from tests.codex_exec_fixtures import PROFILE
    registry = SimpleNamespace(codex_exec_profile=lambda: PROFILE, require_codex_exec_readiness=lambda: None)
    revision = (store.creative_handoff_execution_pin(original)["upstreamRevision"]
                if original.stage.startswith("bridge-") else "a" * 40)
    service = ContentLanguageService(registry)
    job = service.prepare(store, original, candidate, code_revision=revision)
    request, data = store.repository.content_language.load(original.project_id, job)
    if data.get("result") is None:
        completed_check(store, job, result_for(request))
    return job
