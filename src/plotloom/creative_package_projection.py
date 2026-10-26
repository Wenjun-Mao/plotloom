"""Deterministic creative package bytes from an explicit frozen request and pin."""
from __future__ import annotations
import re
import shlex
from pathlib import Path
from typing import Any
from .creative_handoff_contracts import CREATIVE_CANDIDATE_FILENAMES, CreativeHandoffError, CreativeHandoffRequest
from .creative_handoff_identity import PACKAGE_VERSION, TEMPLATE_FILENAME, canonical_json, request_hash
from .creative_execution_pin import execution_pin_for_request
from .codex_exec_resources import upstream_skill_path_for_stage
from .codex_exec_stage_routing import codex_exec_stage_validator_instructions


def project_creative_package(
    job_root: Path, request: CreativeHandoffRequest, execution_pin: dict[str, str], *,
    executor_backend: str = "specialist_chat", plotloom_code_revision: str | None = None,
) -> tuple[dict[str, Any], bytes, bytes, set[str]]:
    if executor_backend not in {"specialist_chat", "codex_exec"}:
        raise CreativeHandoffError("execution_backend_invalid", "creative package execution backend is unsupported")
    if executor_backend == "codex_exec" and (
        not isinstance(plotloom_code_revision, str)
        or re.fullmatch(r"[a-f0-9]{7,64}", plotloom_code_revision) is None
    ):
        raise CreativeHandoffError("executor_revision_missing", "Codex Exec packages require the frozen Plotloom source revision")
    frozen_hash = request_hash(request)
    candidate_filename = CREATIVE_CANDIDATE_FILENAMES[request.stage]
    projected = request.model_dump(mode="json", by_alias=True) | {
        "packageVersion": 4 if executor_backend == "codex_exec" else PACKAGE_VERSION,
        "requestHash": frozen_hash,
        "candidateFilename": candidate_filename,
        "reportFilename": "report.html",
        "upstreamSkillPath": upstream_skill_path_for_stage(request.stage),
        "executionPin": execution_pin_for_request(request, execution_pin),
    }
    if executor_backend == "codex_exec":
        from .codex_exec_validation import build_text_validation_plan

        projected["executorBackend"] = "codex_exec"
        projected["plotloomCodeRevision"] = plotloom_code_revision
        validation_plan = build_text_validation_plan(
            request,
            execution_pin=projected["executionPin"],
            source_revision=plotloom_code_revision,
        )
        projected["validationPlan"] = validation_plan.model_dump(mode="json", by_alias=True)
        projected["validationPlanHash"] = validation_plan.plan_hash
    character_id_instruction = (
        "For characters, preserve established characters[].id values; every "
        "characters[].id must be unique and nonblank. "
        if request.stage == "characters"
        else ""
    )
    branch_candidate = shlex.quote(str(job_root / "delivery" / "branches.json"))
    branch_request = shlex.quote(str(job_root / "package" / "request.json"))
    branch_report = shlex.quote(str(job_root / "delivery" / "report.html"))
    branch_instruction = (
        "For branches, upstream outline is narrative guidance only. Output strictly inputs/branch-schema.json; "
        "Preserve every planned node, choice-option and join ID and order from source.topology. Do not emit an upstream outline or invent topology. "
        f"From the repository root, run uv run --locked python scripts/branch_suggestion.py validate {branch_candidate} --request {branch_request}, then "
        f"uv run --locked python scripts/branch_suggestion.py render {branch_candidate} --request {branch_request} > {branch_report}. Disclose ambiguous proposals in clarifications. "
        if request.stage == "branches" else ""
    )
    intent_instruction = (
        "For bridge-intent, the local native intent contract replaces upstream stage authoring. "
        "Output exactly inputs/intent-schema.json: every frozen target exactly once, only id and suggestedText. "
        "From the repository root run uv run --locked python scripts/native_bridge_intent.py validate <absolute-delivery/intent.json> --request <absolute-package/request.json>, "
        "then render with the same arguments to derive report.html. "
        if request.stage == "bridge-intent" else ""
    )
    presentation_instruction = (
        "For bridge-presentation, use the local presentation contract and inputs/presentation-schema.json. "
        "Return every frozen source ID with exhaustive ordered Unicode-codepoint ownership spans, faithful rendering and required reasons. "
        "From the repository root run uv run --locked python scripts/native_bridge_presentation.py validate <absolute-delivery/presentation.json> --request <absolute-package/request.json>, "
        "then render with the same arguments to derive report.html. Suggestions do not approve presentation or production. "
        if request.stage == "bridge-presentation" else ""
    )
    if executor_backend == "codex_exec":
        upstream_base_dir = Path(projected["upstreamSkillPath"]).parent.as_posix()
        codex_validator_instruction = (
            "The CLI remains in the writable delivery directory. Read the exact stage source named by "
            "request.json's upstreamSkillPath under $PLOTLOOM_SOURCE_ROOT, including only its stage-local "
            f"references. For any upstream command using `{{baseDir}}`, substitute "
            f"`\"$PLOTLOOM_SOURCE_ROOT/{upstream_base_dir}\"` "
            "for `{baseDir}`; this is the directory containing the pinned source file, not the checkout root. "
            "Use the frozen validation plan for awareness only. Write only the candidate JSON; do not run "
            "validators or renderers, redirect command output, or create report.html. The trusted host runs "
            "the exact validation plan and creates the HTML report after the CLI exits. "
        )
        if request.stage == "branches":
            codex_validator_instruction += (
                "For branches, upstream outline is narrative guidance only. Output strictly "
                "inputs/branch-schema.json. Preserve every planned node, choice-option and join ID "
                "and order from source.topology. Do not emit an upstream outline or invent topology. "
                "Disclose ambiguous proposals in clarifications. "
            )
            codex_validator_instruction += "This frozen branch contract replaces upstream outline authoring for this task. "
        elif request.stage == "bridge-intent":
            codex_validator_instruction += (
                "For bridge-intent, the local native intent contract replaces upstream stage authoring. "
                "Output exactly inputs/intent-schema.json: every frozen target exactly once, only id and "
                "suggestedText. "
            )
        elif request.stage == "bridge-presentation":
            codex_validator_instruction += (
                "For bridge-presentation, use the local presentation contract and "
                "inputs/presentation-schema.json. Return every frozen source ID with exhaustive ordered "
                "Unicode-codepoint ownership spans, faithful rendering and required reasons. Suggestions "
                "do not approve presentation or production. "
            )
        elif request.stage in {"characters", "art", "storyboard"}:
            codex_validator_instruction += codex_exec_stage_validator_instructions(
                request.stage, projected, job_root
            )
        instructions = (
            "Read request.json, each inputs/*.json file, the frozen validation plan, the pinned upstream source path and its referenced "
            "stage-local resources. "
            f"Write only the stage-shaped candidate JSON to ../delivery/{candidate_filename}. Do not create "
            "report.html, completion.json, or any other output. The trusted Codex Exec host validates the "
            "candidate and creates the report from the frozen plan after the CLI exits. "
            "For this Codex Exec package v4, request.creativeBrief supplies creative, style, source and candidate "
            "requirements. Any validator, renderer, report, or completion-manifest steps stated there, in the "
            "pinned stage skill, or in referenced stage instructions describe the manual specialist-chat workflow "
            "only; they are not executable by this CLI attempt. This precedence does not replace any substantive "
            "candidate requirement. The host follows only the exact frozen validation plan. "
            f"{character_id_instruction}{codex_validator_instruction}"
            "This is a candidate only: do not edit project canon, approvals, selections, or request files.\n"
        ).encode()
        return projected, instructions, b"", {"request.json", "COPY_ASSIGNMENT.txt", "inputs"}
    instructions = (
        "Read request.json, each inputs/*.json file, and the pinned upstream source path. "
        f"Write the stage-shaped candidate JSON to the sibling ../delivery/{candidate_filename}, then derive "
        "../delivery/report.html from that candidate. Never create package/delivery. Finally publish "
        "../delivery/completion.json once. "
        f"{character_id_instruction}{branch_instruction}{intent_instruction}{presentation_instruction}"
        "This is a candidate only: do not edit project canon, approvals, selections, or request files.\n"
    ).encode()
    template = canonical_json({
        "schemaVersion": 1, "jobId": request.job_id, "requestHash": frozen_hash,
        "deliveryId": "replace-with-specialist-delivery-id", "stage": request.stage,
        "candidate": {"filename": candidate_filename, "sha256": "0" * 64},
        "report": {"filename": "report.html", "sha256": "0" * 64},
        "executorProvenance": {
            "codeRevision": "checked-out-commit", "skillVersion": f"plotloom-{request.stage.removeprefix('bridge-')}-specialist.v1" if request.stage in {"bridge-intent", "bridge-presentation", "video-directions"} else "plotloom-shuohao-specialist.v1",
            "skillHash": projected["executionPin"]["specialistSkillHash"],
            "upstreamRevision": projected["executionPin"]["upstreamRevision"],
            "upstreamSkillHash": projected["executionPin"]["upstreamSkillHash"],
            "model": None, "reasoningEffort": None,
        }, "limitations": [],
    })
    return projected, instructions, template, {"request.json", "COPY_ASSIGNMENT.txt", TEMPLATE_FILENAME, "inputs"}
