"""Fixed passive Cast/Art package plans, never current execution authority."""
import re
from hashlib import sha256

from .codex_exec_validation import CodexExecTextValidationPlan
from .creative_execution_pin import execution_pin_for_request
from .creative_handoff_identity import canonical_json, request_hash

_V1_ART_SHAPES = {
    "saved_brief": "5b06e011f8909cdc4e2483f7aa81dcb1bfa56e8144a774e5ad2f92bb77f77b96",
    "preset_style": "446624511b462a4ee99c398cc71c81f0ba23dbcc4459f05ff6fe5889c55d2bc2",
}


def _digest(value):
    return sha256(canonical_json(value)).hexdigest()


def _assert_frozen_brief(contract):
    """Integrity of the original frozen representation, without today's file hashes."""
    if (not isinstance(contract, dict) or set(contract) != {"version", "authority", "stageInstructionContract",
            "direction", "emptyDirectionRule", "validatorHashes", "contentHash"}
            or type(contract["version"]) is not int or contract["version"] != 1
            or contract["authority"] != "saved_brief"
            or contract["stageInstructionContract"] != "plotloom.autopilot.saved-brief-receiving-contract.v2"):
        raise ValueError("retained saved-Brief authority shape is invalid")
    direction, empty, hashes = contract["direction"], contract["emptyDirectionRule"], contract["validatorHashes"]
    if (direction is not None and not isinstance(direction, str) or direction and empty is not None
            or not direction and not isinstance(empty, str)
            or not isinstance(hashes, dict) or set(hashes) != {"policy", "artAdapter", "artUpstream", "artGateSummary", "castAdapter", "castUpstream"}
            or any(not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None for value in hashes.values())
            or contract["contentHash"] != _digest({key: value for key, value in contract.items() if key != "contentHash"})):
        raise ValueError("retained saved-Brief authority integrity differs")


def retained_visual_package_projection(request, execution_pin, *, source_revision):
    """Reconstruct known original wire steps, never execute package-supplied argv."""
    stage = request.stage
    if stage not in {"characters", "art"} or not isinstance(source_revision, str) or re.fullmatch(r"[a-f0-9]{7,64}", source_revision) is None:
        raise ValueError("retained visual package requires its original stage and source revision")
    stem = "cast" if stage == "characters" else "art"
    contract = request.input_artifacts.get(f"{stem}-style-contract.json", {})
    route = "saved_brief" if contract.get("authority") == "saved_brief" else "preset_style"
    if route == "saved_brief":
        _assert_frozen_brief(contract)
    elif "authority" in contract:
        raise ValueError("unsupported retained visual authority")
    shape = request.input_artifacts.get("art-structure-schema.json") if stage == "art" else None
    if shape is not None:
        if shape.get("contract") == "plotloom.art-structural-result.v1":
            if _digest(shape) != _V1_ART_SHAPES[route]:
                raise ValueError("original Art shape differs")
        elif shape.get("contract") != "plotloom.art-structural-result.v2":
            raise ValueError("unsupported retained Art shape")
    pin = execution_pin_for_request(request, execution_pin)
    filename = stem + ".json"
    adapter = f"{{source}}/scripts/{'brief-' if route == 'saved_brief' else ''}{stem}-style.mjs"
    extra = (["--cast", "{input:cast.json}"] if stage == "art" else ["--request", "{package}/request.json"])
    if route == "preset_style":
        extra += ["--contract", f"{{input:{stem}-style-contract.json}}"]
    validate = {"stepId": "validate", "program": "node", "argv": [adapter, "validate", "{candidate}", *extra], "stdoutIsReport": False}
    typed = request.content_validation_contract
    if typed is not None:
        if typed != "plotloom.typed-content-result.v1":
            raise ValueError("unsupported retained visual content boundary")
        validate["argv"] = ["{source}/scripts/text-content-validation.mjs", "{candidate}", "{package}/request.json"]
    marked_cast = stage == "characters" and "creative-field-ownership.json" in request.input_artifacts
    if shape is not None or marked_cast:
        if typed is None:
            raise ValueError("retained marked visual request requires typed content boundary")
        wrapper = "art_content_validation.py" if stage == "art" else "creative_field_validation.py"
        validate |= {"program": "uv", "argv": ["run", "--project", "{source}", "--locked", "--no-sync", "python",
            "{source}/scripts/" + wrapper, "{candidate}", "--request", "{package}/request.json", "--node", "{tool:node}"]}
    render = [adapter, "render", "{candidate}"]
    if route == "preset_style":
        render.append("--html")
    render += extra
    if stage == "art" and "provider-literal-contract.json" in request.input_artifacts:
        render += ["--request", "{package}/request.json"]
    plan = CodexExecTextValidationPlan.model_validate({
        "schemaVersion": 1, "stage": stage, "route": route, "requestHash": request_hash(request), "sourceRevision": source_revision,
        "executionPinHash": _digest(pin), "candidateFilename": filename, "reportFilename": "report.html",
        "inputs": [{"filename": name, "sha256": _digest(value), "sizeBytes": len(canonical_json(value))}
                   for name, value in sorted(request.input_artifacts.items())],
        "steps": [validate, {"stepId": "render", "program": "node", "argv": render, "stdoutIsReport": True}],
    })
    return request.model_dump(mode="json", by_alias=True) | {
        "packageVersion": 4, "requestHash": request_hash(request), "candidateFilename": filename, "reportFilename": "report.html",
        "upstreamSkillPath": f"third_party/shuohao-skills/skills/novel-{stage}/SKILL.md", "executionPin": pin,
        "executorBackend": "codex_exec", "plotloomCodeRevision": source_revision,
        "validationPlan": plan.model_dump(mode="json", by_alias=True), "validationPlanHash": plan.plan_hash,
    }
