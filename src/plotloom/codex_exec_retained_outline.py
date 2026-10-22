"""Read-only Outline package-v4 / plan-v1 representation for retained evidence."""
import re
from hashlib import sha256

from .codex_exec_validation import CodexExecTextValidationPlan
from .creative_handoff_exchange import canonical_json, execution_pin_for_request, request_hash


def retained_outline_package_projection(request, execution_pin, *, source_revision):
    """Derive expected original bindings without live admission or recorded-plan input.

    This retained-evidence projection cannot authorize execution. The fixed wire
    representation keeps passive recovery independent of prospective schemas
    and validator plans; original input objects are hashed without modification.
    """
    if request.stage != "outline":
        raise ValueError("retained Outline projection requires an Outline request")
    if not isinstance(source_revision, str) or re.fullmatch(r"[a-f0-9]{7,64}", source_revision) is None:
        raise ValueError("retained Outline projection requires its frozen source revision")
    pin = execution_pin_for_request(request, execution_pin)
    original_request_hash = request_hash(request)
    skill = "third_party/shuohao-skills/skills/novel-outline/SKILL.md"
    script = "{source}/third_party/shuohao-skills/skills/novel-outline/scripts/novel-outline.mjs"
    plan = {
        "schemaVersion": 1,
        "stage": "outline",
        "route": "upstream",
        "requestHash": original_request_hash,
        "sourceRevision": source_revision,
        "executionPinHash": sha256(canonical_json(pin)).hexdigest(),
        "candidateFilename": "outline.json",
        "reportFilename": "report.html",
        "inputs": [{
            "filename": name,
            "sha256": sha256(canonical_json(payload)).hexdigest(),
            "sizeBytes": len(canonical_json(payload)),
        } for name, payload in sorted(request.input_artifacts.items())],
        "steps": [
            {"stepId": "validate", "program": "node", "argv": [script, "validate", "{candidate}"], "stdoutIsReport": False},
            {"stepId": "render", "program": "node", "argv": [script, "render", "{candidate}", "--html"], "stdoutIsReport": True},
        ],
    }
    if request.content_validation_contract is not None:
        plan["steps"][0]["argv"] = ["{source}/scripts/text-content-validation.mjs", "{candidate}", "{package}/request.json"]
    expected_plan = CodexExecTextValidationPlan.model_validate(plan)
    return request.model_dump(mode="json", by_alias=True) | {
        "packageVersion": 4,
        "requestHash": original_request_hash,
        "candidateFilename": "outline.json",
        "reportFilename": "report.html",
        "upstreamSkillPath": skill,
        "executionPin": pin,
        "executorBackend": "codex_exec",
        "plotloomCodeRevision": source_revision,
        "validationPlan": expected_plan.model_dump(mode="json", by_alias=True),
        "validationPlanHash": expected_plan.plan_hash,
    }
