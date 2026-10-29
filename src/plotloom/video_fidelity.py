"""Exact persisted assistant-check evidence at prepare, dispatch and readback."""
from hashlib import sha256

from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
)
from .contract_hash import stable_hash
from .creative_handoff_contracts import CreativeHandoffRequest
from .creative_handoff_identity import canonical_json, request_hash
from .exceptions import InvalidTransitionError
from .persistence.schema import VideoBatchRow
from .video_directions_contract import bind_fidelity
from .video_fidelity_contracts import FidelityReference


def fidelity_reference(batch_id, data, result):
    return {"version": "assistant-fidelity.v1", "batchId": batch_id,
        "attemptId": data["attempt"]["attemptId"], "resultHash": stable_hash(result)}


def assert_target_fidelity(session, project_id, target):
    """Caller-supplied verdicts never replace a native attempt and delivery."""
    try:
        reference = FidelityReference.model_validate(target["directions"].get("fidelityCheck"))
        row = session.get(VideoBatchRow, reference.batch_id)
        if row is None or row.project_id != project_id or stable_hash(row.manifest) != row.manifest_hash:
            raise ValueError("missing retained check")
        return validate_retained_fidelity(row.execution.get("fidelity"), project_id, row.id, target, reference)
    except (ValueError, TypeError, KeyError, StopIteration) as error:
        raise InvalidTransitionError("助手保真检查缺失、未通过或来源已变化；请检查当前完整候选。") from error


def validate_retained_fidelity(data, project_id, batch_id, target, reference, *, require_pass=True):
    """Pure shared validator for portable admission and runtime authority."""
    if not data or not data.get("result"):
        raise ValueError("missing fidelity result")
    attempt = CodexExecAttempt.model_validate(data["attempt"])
    receipt = CodexExecReceipt.model_validate(data["receipt"])
    assert_receipt_matches_attempt(attempt, receipt)
    request = CreativeHandoffRequest.model_validate(data["request"])
    if (attempt.state != "completed" or str(attempt.attempt_id) != reference.attempt_id
            or request.source.get("operation") != "fidelity-check"
            or request.project_id != project_id or request.section_id != batch_id
            or attempt.request_hash != request_hash(request)
            or attempt.job_id != request.job_id or str(attempt.run_id) != batch_id
            or request.source.get("candidateBinding") != data.get("candidateBinding")
            or stable_hash(data["result"]) != reference.result_hash
            or data.get("responseHash") != sha256(canonical_json(data["result"])).hexdigest()):
        raise ValueError("fidelity identity changed")
    if (receipt.text_validation is None or receipt.text_validation.candidate_hash != data.get("deliveryCandidateHash")):
        raise ValueError("fidelity result lacks exact validated native output")
    bound = bind_fidelity(request, data["result"])
    check = bound[target["shotId"]]
    frozen = next(item for item in request.input_artifacts["video-targets.json"]["targets"] if item["shotId"] == target["shotId"])
    if ((require_pass and check["verdict"] != "pass") or frozen["snapshot"] != target["snapshot"]
            or frozen["compiledPrompt"] != target["compiledPrompt"]
            or frozen["directions"] != {key: target["directions"][key] for key in ("sourceHash", "fields")}):
        raise ValueError("fidelity check is rejected or stale")
    # Draft provenance is required for native drafts, and must use another
    # invocation. Manually edited candidates are honestly labelled as such.
    draft_id = request.source.get("draftAttemptId")
    if draft_id is not None and draft_id == str(attempt.attempt_id):
        raise ValueError("drafter cannot be its own checking invocation")
    return check
