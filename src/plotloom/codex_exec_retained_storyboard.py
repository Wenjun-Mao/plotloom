"""Passive saved-Brief Storyboard package-v4 / plan-v1 provenance."""
import re
from hashlib import sha256

from .codex_exec_validation import CodexExecTextValidationPlan
from .creative_execution_pin import execution_pin_for_request
from .creative_handoff_identity import canonical_json, request_hash
from .production_dialogue_timing import TIMING_FILENAME, FrozenF5DialogueTiming

_STYLE = "storyboard-style-contract.json"
_HASH = re.compile(r"[a-f0-9]{64}")


def _digest(value):
    return sha256(canonical_json(value)).hexdigest()


def _hash_inventory(value, names):
    if (not isinstance(value, dict) or set(value) != names
            or any(not isinstance(item, str) or _HASH.fullmatch(item) is None for item in value.values())):
        raise ValueError("retained Storyboard validator hash inventory is invalid")


def _assert_frozen_style(contract):
    """Check the existing frozen representation, never today's validator files."""
    if not isinstance(contract, dict):
        raise ValueError("retained Storyboard requires its frozen saved-Brief authority")
    inherited = contract.get("inheritedArtRenderContract")
    if (not isinstance(inherited, dict) or set(inherited) != {
            "version", "authority", "stageInstructionContract", "direction", "emptyDirectionRule",
            "validatorHashes", "contentHash"}
            or type(inherited["version"]) is not int or inherited["version"] != 1
            or inherited["authority"] != "saved_brief"
            or inherited["stageInstructionContract"] != "plotloom.autopilot.saved-brief-receiving-contract.v2"):
        raise ValueError("retained Storyboard inherited Art authority is invalid")
    direction, empty = inherited["direction"], inherited["emptyDirectionRule"]
    if (direction is not None and not isinstance(direction, str)
            or (direction and empty is not None)
            or (not direction and not isinstance(empty, str))):
        raise ValueError("retained Storyboard inherited direction is invalid")
    _hash_inventory(inherited["validatorHashes"], {
        "policy", "artAdapter", "artUpstream", "artGateSummary", "castAdapter", "castUpstream"})
    if inherited["contentHash"] != _digest({k: v for k, v in inherited.items() if k != "contentHash"}):
        raise ValueError("retained Storyboard inherited Art hash differs")
    hashes = contract.get("validatorHashes")
    _hash_inventory(hashes, {"policy", "adapter", "upstream", "upstreamGateSummary", "dialogueTiming"})
    expected = {
        "version": "plotloom.saved-brief.storyboard.v1", "authority": "saved_brief",
        "stageInstructionContract": "plotloom.autopilot.saved-brief-storyboard-receiving-contract.v1",
        "direction": direction, "emptyDirectionRule": empty,
        "inheritedArtRenderContract": inherited, "validatorHashes": hashes,
    }
    if contract != expected | {"contentHash": _digest(expected)}:
        raise ValueError("retained Storyboard frozen authority or hash differs")


def retained_storyboard_package_projection(request, execution_pin, *, source_revision):
    """Reconstruct a known immutable wire shape, without execution authority.

    Callers still bind this projection to their original request, pin, attempt,
    receipt and inherited origin. No recorded argv or package files are inputs.
    """
    if request.stage != "storyboard":
        raise ValueError("retained Storyboard projection requires a Storyboard request")
    if not isinstance(source_revision, str) or re.fullmatch(r"[a-f0-9]{7,64}", source_revision) is None:
        raise ValueError("retained Storyboard requires its frozen source revision")
    if request.content_validation_contract not in {None, "plotloom.typed-content-result.v1"}:
        raise ValueError("retained Storyboard content boundary is unsupported")
    if TIMING_FILENAME not in request.input_artifacts:
        raise ValueError("retained Storyboard requires frozen dialogue timing")
    FrozenF5DialogueTiming.model_validate(request.input_artifacts[TIMING_FILENAME])
    _assert_frozen_style(request.input_artifacts.get(_STYLE))
    pin = execution_pin_for_request(request, execution_pin)
    original_hash = request_hash(request)
    script = "{source}/scripts/brief-storyboard-style.mjs"
    arguments = ["{candidate}", "--request", "{package}/request.json"]
    plan = {
        "schemaVersion": 1, "stage": "storyboard", "route": "saved_brief",
        "requestHash": original_hash, "sourceRevision": source_revision,
        "executionPinHash": _digest(pin), "candidateFilename": "storyboard.json",
        "reportFilename": "report.html",
        "inputs": [{"filename": name, "sha256": _digest(value),
            "sizeBytes": len(canonical_json(value))} for name, value in sorted(request.input_artifacts.items())],
        "steps": [{"stepId": step, "program": "node", "argv": [script, step, *arguments],
            "stdoutIsReport": step == "render"} for step in ("validate", "render")],
    }
    if request.content_validation_contract is not None:
        plan["steps"][0]["argv"] = [
            "{source}/scripts/storyboard-content-validation.mjs", "{candidate}", "{package}/request.json"]
    parsed = CodexExecTextValidationPlan.model_validate(plan)
    return request.model_dump(mode="json", by_alias=True) | {
        "packageVersion": 4, "requestHash": original_hash,
        "candidateFilename": "storyboard.json", "reportFilename": "report.html",
        "upstreamSkillPath": "third_party/shuohao-skills/skills/novel-storyboard/SKILL.md",
        "executionPin": pin, "executorBackend": "codex_exec", "plotloomCodeRevision": source_revision,
        "validationPlan": parsed.model_dump(mode="json", by_alias=True), "validationPlanHash": parsed.plan_hash,
    }
