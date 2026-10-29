"""Passive planned-dialogue Script plan identity, independent of current timing rules."""
import re
from hashlib import sha256

from .codex_exec_validation import CodexExecTextValidationPlan
from .creative_execution_pin import execution_pin_for_request
from .creative_handoff_identity import canonical_json, request_hash
from .script_dialogue_compatibility import planned_dialogue_from_admission


def retained_script_package_projection(request, execution_pin, *, source_revision):
    """Read the fixed original uv plan; this cannot admit or replay old timing policy."""
    if request.stage != "script" or not isinstance(source_revision, str) or re.fullmatch(r"[a-f0-9]{7,64}", source_revision) is None:
        raise ValueError("retained Script requires its original stage and source revision")
    if planned_dialogue_from_admission(request.input_artifacts.get("script-admission.json")) is None:
        raise ValueError("retained planned Script requires its original bound profile")
    pin = execution_pin_for_request(request, execution_pin)
    digest = lambda value: sha256(canonical_json(value)).hexdigest()
    runner = ["run", "--project", "{source}", "--locked", "--no-sync", "python", "{source}/scripts/script_receiving.py"]
    plan = CodexExecTextValidationPlan.model_validate({
        "schemaVersion": 1, "stage": "script", "route": "plotloom_native",
        "requestHash": request_hash(request), "sourceRevision": source_revision,
        "executionPinHash": digest(pin), "candidateFilename": "script.json", "reportFilename": "report.html",
        "inputs": [{"filename": name, "sha256": digest(value), "sizeBytes": len(canonical_json(value))}
                   for name, value in sorted(request.input_artifacts.items())],
        "steps": [{"stepId": step, "program": "uv", "argv": [*runner, step, "{candidate}", "--request", "{package}/request.json"],
                   "stdoutIsReport": step == "render"} for step in ("validate", "render")],
    })
    return request.model_dump(mode="json", by_alias=True) | {
        "packageVersion": 4, "requestHash": request_hash(request), "candidateFilename": "script.json", "reportFilename": "report.html",
        "upstreamSkillPath": "third_party/shuohao-skills/skills/novel-script/SKILL.md", "executionPin": pin,
        "executorBackend": "codex_exec", "plotloomCodeRevision": source_revision,
        "validationPlan": plan.model_dump(mode="json", by_alias=True), "validationPlanHash": plan.plan_hash,
    }
