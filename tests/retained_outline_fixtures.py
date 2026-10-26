"""Fresh synthetic stopped native evidence; never reads historical proof or dispatches."""
import json
import sqlite3
from contextlib import closing
from hashlib import sha256
from uuid import uuid4

from plotloom.autopilot_contracts import MachineDecision, OperationScope
from plotloom.codex_exec_contracts import (
    CodexExecAttempt, CodexExecProfile, CodexExecReceipt, output_manifest_hash,
)
from plotloom.codex_exec_files import output_evidence_for_tree
from plotloom.codex_exec_runtime import package_tree_hash
from plotloom.codex_exec_validation import (
    CodexExecTextValidationEvidence, CodexExecValidationStepEvidence,
)
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeDeliveryManifest
from plotloom.creative_handoff_identity import canonical_json, request_hash
from plotloom.outline_report_metadata import OUTLINE_REPORT_SCHEMA_FILENAME
from plotloom.project_storage import ProjectFolderStorage
from tests.autopilot_fixtures import policy_for
from tests.codex_exec_fixtures import PROFILE
from tests.source_outline_fixtures import _material, _request

REVISION = "a" * 40


def digest(value):
    return sha256(canonical_json(value)).hexdigest()


def historical_profile(version):
    value = PROFILE.model_dump(mode="json", by_alias=True)
    value["contractVersion"] = f"plotloom.codex-exec.v{version}"
    if version != 8:
        value.update(maxProcesses=1, maxTextProcesses=None, maxImageProcesses=None, maxQueuedJobs=None)
    if version == 6:
        value.update(permissionProfile="plotloom_autopilot_delivery_v4",
            textValidatorRuntimeProfile="node_openssl_private_zsh_tmp_and_validator_aliases_v2")
    return CodexExecProfile.model_validate(value)


def historical_request(request, schema):
    artifacts = dict(request.input_artifacts)
    if schema == "missing":
        del artifacts[OUTLINE_REPORT_SCHEMA_FILENAME]
    elif schema == "different":
        artifacts[OUTLINE_REPORT_SCHEMA_FILENAME] = {"type": "object", "description": "original historical schema"}
    return request.model_copy(update={"input_artifacts": artifacts})


def historical_package(request, pin):
    """Test-owned original wire representation, independent of live/recovery projectors."""
    script = "{source}/third_party/shuohao-skills/skills/novel-outline/scripts/novel-outline.mjs"
    plan = {
        "schemaVersion": 1, "stage": "outline", "route": "upstream",
        "requestHash": request_hash(request), "sourceRevision": REVISION,
        "executionPinHash": digest(pin), "candidateFilename": "outline.json",
        "reportFilename": "report.html",
        "inputs": [{"filename": name, "sha256": digest(value), "sizeBytes": len(canonical_json(value))}
            for name, value in sorted(request.input_artifacts.items())],
        "steps": [
            {"stepId": "validate", "program": "node", "argv": [script, "validate", "{candidate}"], "stdoutIsReport": False},
            {"stepId": "render", "program": "node", "argv": [script, "render", "{candidate}", "--html"], "stdoutIsReport": True},
        ],
    }
    return request.model_dump(mode="json", by_alias=True) | {
        "packageVersion": 4, "requestHash": request_hash(request),
        "candidateFilename": "outline.json", "reportFilename": "report.html",
        "upstreamSkillPath": "third_party/shuohao-skills/skills/novel-outline/SKILL.md",
        "executionPin": pin, "executorBackend": "codex_exec", "plotloomCodeRevision": REVISION,
        "validationPlan": plan, "validationPlanHash": digest(plan),
    }


def storage_at(root):
    return ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")


def stopped_native_outline(root, *, version=8, schema="missing"):
    """Fabricate only disposable test rows and bytes; synthetic receipt is not native acceptance."""
    storage = storage_at(root)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home = str(store.manifest.project_id), store.home
        profile = historical_profile(version)
        policy = policy_for(store).model_copy(update={"executor_binding": profile})
        run = store.repository.autopilot.start(project_id,
            expected_brief_revision=store.project().revision, policy=policy)
        store.repository.autopilot.control(project_id, expected_revision=run.revision, action="cancel")
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        current = _request(project_id, source)
        store.prepare_outline_candidate(current)
        pin = store.creative_handoff_execution_pin(current)
    request = historical_request(current, schema)
    package = historical_package(request, pin)
    job = home / "outputs/creative-handoff/jobs" / request.job_id
    (job / "package/inputs").mkdir(parents=True)
    (job / "package/request.json").write_bytes(canonical_json(package))
    (job / "package/COPY_ASSIGNMENT.txt").write_text("Original synthetic frozen assignment.\n")
    for name, value in request.input_artifacts.items():
        (job / "package/inputs" / name).write_bytes(canonical_json(value))
    delivery = job / "delivery"
    delivery.mkdir()
    (delivery / "outline.json").write_bytes(canonical_json({"source": "渡口的信", "params": {"episodes": 1}, "episodes": []}))
    (delivery / "report.html").write_bytes(b"<!doctype html><html>Original synthetic report.</html>")
    outputs = output_evidence_for_tree(job, "delivery", output_prefix="delivery", max_total_bytes=profile.max_output_bytes)
    package_hash = package_tree_hash(job, max_total_bytes=profile.max_output_bytes)
    common = dict(profileHash=profile.profile_hash, requestHash=request_hash(request), packageHash=package_hash)
    validation = CodexExecTextValidationEvidence(**common,
        planHash=package["validationPlanHash"], validatorHash=profile.validator_hash, sourceRevision=REVISION,
        candidateFilename="outline.json", candidateHash=outputs[0].output_hash, candidateSizeBytes=outputs[0].size_bytes,
        reportHash=outputs[1].output_hash, reportSizeBytes=outputs[1].size_bytes,
        steps=(CodexExecValidationStepEvidence(stepId="validate", argvHash="1" * 64, exitCode=0,
            stdoutHash=sha256(b"").hexdigest(), stdoutSizeBytes=0, stderrHash="2" * 64, stderrSizeBytes=0, durationMs=1),
            CodexExecValidationStepEvidence(stepId="render", argvHash="3" * 64, exitCode=0,
                stdoutHash=outputs[1].output_hash, stdoutSizeBytes=outputs[1].size_bytes,
                stderrHash="2" * 64, stderrSizeBytes=0, durationMs=1)))
    identity = dict(**common, attemptId=uuid4(), sessionId=uuid4(), plotloomCodeRevision=REVISION,
        validationPlanHash=package["validationPlanHash"], processId=123, processGroupId=123,
        processBirthIdentity="synthetic-stopped", processExitCode=0, evidenceHash="e" * 64,
        outputHash=output_manifest_hash(outputs), remoteToolState="not_applicable")
    receipt = CodexExecReceipt(**identity, expectedImageOutputs=0, outputs=outputs, textValidation=validation)
    attempt = CodexExecAttempt(**identity, runId=run.id, projectId=project_id,
        jobId=request.job_id, operationKey="outline", domain="text", reservedImageOutputs=0,
        imageBudgetState="none", state="completed", terminalResult="success")
    manifest = CreativeDeliveryManifest(schemaVersion=3, executorBackend="codex_exec",
        executorAttemptId=attempt.attempt_id, codexSessionId=receipt.session_id, executorProfileHash=profile.profile_hash,
        validationPlanHash=package["validationPlanHash"], validationEvidenceHash=validation.evidence_hash,
        jobId=request.job_id, requestHash=request_hash(request), deliveryId="synthetic-historical-outline", stage="outline",
        candidate={"filename": "outline.json", "sha256": outputs[0].output_hash},
        report={"filename": "report.html", "sha256": outputs[1].output_hash},
        executorProvenance={"codeRevision": REVISION, "skillVersion": "plotloom-shuohao-specialist.v1",
            "skillHash": pin["specialistSkillHash"], "upstreamRevision": pin["upstreamRevision"],
            "upstreamSkillHash": pin["upstreamSkillHash"], "model": profile.model, "reasoningEffort": profile.reasoning_effort})
    (delivery / "completion.json").write_bytes(canonical_json(manifest.model_dump(mode="json", by_alias=True)))
    with sqlite3.connect(home / "project.sqlite3") as connection:
        # This constructs a new synthetic historical fixture, never edits retained real data.
        connection.execute("UPDATE v2_source_outline_candidates SET request=?, manifest_hash=?, status='ready', delivery_id=?, outline=?, report_html=?, delivered_at=? WHERE job_id=?",
            (canonical_json(request.model_dump(mode="json", by_alias=True)).decode(), digest(manifest.model_dump(mode="json", by_alias=True)),
                manifest.delivery_id, (delivery / "outline.json").read_text(), (delivery / "report.html").read_text(), "2026-10-16", request.job_id))
        connection.execute("UPDATE v2_creative_handoff_execution_pins SET request_hash=? WHERE job_id=?", (request_hash(request), request.job_id))
        evidence = {"owner": "outline", "subjectId": request.job_id, "jobId": request.job_id,
            "requestHash": request_hash(request), "executionPin": pin, "executorAttemptId": str(attempt.attempt_id),
            "executorReceiptHash": attempt.evidence_hash, "deliveryHash": digest(manifest.model_dump(mode="json", by_alias=True))}
        checkpoint_id = str(uuid4())
        connection.execute("INSERT INTO v2_autopilot_checkpoints (id,run_id,project_id,operation_key,revision,state,evidence,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (checkpoint_id, str(run.id), project_id, "outline", 1, "delivered", json.dumps(evidence), "2026-10-16", "2026-10-16"))
        connection.execute("INSERT INTO v2_autopilot_exec_attempts (id,run_id,project_id,operation_key,job_id,domain,state,image_budget_state,reserved_image_outputs,revision,snapshot,receipt,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (str(attempt.attempt_id), str(run.id), project_id, "outline", request.job_id, "text", "completed", "none", 0, 1,
                attempt.model_dump_json(by_alias=True), receipt.model_dump_json(by_alias=True), "2026-10-16", "2026-10-16"))
        policy_hash = connection.execute("SELECT policy_hash FROM v2_autopilot_runs").fetchone()[0]
        decision = MachineDecision(scope=OperationScope.TEXT, policyHash=policy_hash,
            subject={"jobId": request.job_id}, upstreamHash=request_hash(request), evidence=evidence,
            rationale="Fresh synthetic retained Outline decision; no creative acceptance.")
        connection.execute("INSERT INTO v2_autopilot_decisions (id,run_id,project_id,scope,checkpoint_id,decision,created_at) VALUES (?,?,?,?,?,?,?)",
            (str(uuid4()), str(run.id), project_id, OperationScope.TEXT.value, checkpoint_id,
                decision.model_dump_json(by_alias=True), "2026-10-16"))
    storage.projects.close_project(project_id)
    return storage, project_id, home, request, pin, profile, attempt, receipt
