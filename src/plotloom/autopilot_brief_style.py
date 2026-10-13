"""Exact saved-Brief style authority for autopilot Cast and Art candidates."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

BRIEF_STYLE = "saved-brief"
BRIEF_STYLE_LABEL = "Saved Brief direction"
EMPTY_DIRECTION = "尊重故事设定，由专业助手结合内容判断视觉表达；不默认真人实拍或其他预设。"
BRIEF_STAGE_INSTRUCTION_CONTRACT = "plotloom.autopilot.saved-brief-receiving-contract.v2"


def brief_stage_instructions(stage: Literal["cast", "art"]) -> str:
    """Build the frozen receiving contract for one saved-Brief specialist task.

    The pinned skills remain unchanged for manual callers. This task-scoped
    contract explicitly supersedes only their preset-specific routing, while
    preserving their unrelated stage and quality guidance.
    """
    if stage == "cast":
        validate = (
            'node scripts/brief-cast-style.mjs validate "$DELIVERY_ROOT/cast.json" '
            '--request "$PACKAGE_ROOT/request.json"'
        )
        render = (
            'node scripts/brief-cast-style.mjs render "$DELIVERY_ROOT/cast.json" '
            '--request "$PACKAGE_ROOT/request.json" > "$DELIVERY_ROOT/report.html"'
        )
        skill_route = "novel-characters"
        contract_file = "inputs/cast-style-contract.json"
        fields = "image.prompt, image.sheet, image.negativePrompt, and image.tags"
        marker = "cast.style"
        ownership = (
            "The supplied request.json and all package inputs are read-only. "
            "The assigned DELIVERY_ROOT/cast.json is the candidate you author; "
            "preserve source facts while proposing the shared character designs."
        )
    elif stage == "art":
        validate = (
            'node scripts/brief-art-style.mjs validate "$DELIVERY_ROOT/art.json" '
            '--cast "$PACKAGE_ROOT/inputs/cast.json"'
        )
        render = (
            'node scripts/brief-art-style.mjs render "$DELIVERY_ROOT/art.json" '
            '--cast "$PACKAGE_ROOT/inputs/cast.json" > "$DELIVERY_ROOT/report.html"'
        )
        skill_route = "novel-art"
        contract_file = "inputs/art-style-contract.json"
        fields = "scene and prop image prompts, sheets, lighting/state prompts, negative prompts and tags"
        marker = "art.style"
        ownership = (
            "The supplied request.json, package inputs, and especially the accepted cast at "
            "PACKAGE_ROOT/inputs/cast.json are read-only. The assigned DELIVERY_ROOT/art.json "
            "is the candidate you author; preserve source facts and accepted character descriptions. "
            "Do not edit the supplied cast."
        )
    else:  # pragma: no cover - Literal callers are statically constrained.
        raise ValueError(f"unknown saved-Brief specialist stage: {stage}")

    commands = [validate, render]
    return (
        f" EXPLICIT SAVED-BRIEF RECEIVING-CONTRACT OVERRIDE ({BRIEF_STAGE_INSTRUCTION_CONTRACT}): "
        f"The frozen {contract_file} and this request identify `saved_brief` and take precedence over conflicting "
        f"preset-specific requirements in the pinned {skill_route} skill for this task. This override replaces only "
        "preset selection/defaults, preset bundles and cross-stage preset matching, style-specific negative-prompt "
        "rules, and the preset-specific validate/render entrypoints. Do not route this Brief-authoritative task "
        "through a preset; do not add preset fields. All other pinned skill instructions still apply, including "
        "upstream stage guidance, schema/structure, source/evidence, language, reporting, and non-style quality gates. "
        f"Preserve the exact original direction in {contract_file} as authoritative metadata, then interpret it "
        f"faithfully in English in {fields}. Set {marker} to `saved-brief` and each image.style to the English "
        "marker `Saved Brief direction`. Do not copy non-English direction text into machine fields or add unrelated "
        "photographic/Ghibli defaults. For an empty direction, use story-informed discretion without a preset and "
        "do not copy emptyDirectionRule into machine fields. "
        f"{ownership} Semantic visual fidelity remains subject to human review. "
        "Resolve PACKAGE_ROOT as the absolute task-package directory containing request.json and inputs/, and "
        "DELIVERY_ROOT as the absolute assigned delivery directory. From the Plotloom repository root, run exactly:\n"
        + "\n".join(commands)
        + "\n"
    )


def freeze_brief_style(direction: str | None) -> dict[str, Any]:
    payload = {"version": 1, "authority": "saved_brief", "stageInstructionContract": BRIEF_STAGE_INSTRUCTION_CONTRACT, "direction": direction,
        "emptyDirectionRule": EMPTY_DIRECTION if not direction else None}
    project_root = Path(__file__).resolve().parents[2]
    validator_paths = {
        "policy": Path(__file__),
        "artAdapter": project_root / "scripts" / "brief-art-style.mjs",
        "artUpstream": project_root / "third_party/shuohao-skills/skills/novel-art/scripts/novel-art.mjs",
        "artGateSummary": project_root / "third_party/shuohao-skills/skills/novel-art/scripts/gate-summary.mjs",
        "castAdapter": project_root / "scripts" / "brief-cast-style.mjs",
        "castUpstream": project_root / "third_party/shuohao-skills/skills/novel-characters/scripts/novel-characters.mjs",
    }
    payload["validatorHashes"] = {
        name: sha256(path.read_bytes()).hexdigest() for name, path in validator_paths.items()
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return payload | {"contentHash": sha256(canonical).hexdigest()}


def brief_style_current(contract: dict[str, Any] | None, direction: str | None) -> bool:
    return bool(contract) and contract == freeze_brief_style(direction)


def image_style_guidance(direction: str | None, *, follows_brief: bool) -> str:
    if direction:
        return direction
    return EMPTY_DIRECTION if follows_brief else ""


def validate_brief_style(payload: dict[str, Any], contract: dict[str, Any], *, subjects: tuple[str, ...], stage: str) -> None:
    direction = contract.get("direction")
    if contract != freeze_brief_style(direction if isinstance(direction, str) else None):
        raise ValueError(f"{stage} Brief visual authority is stale or malformed")
    if payload.get("style") != BRIEF_STYLE:
        raise ValueError(f"{stage}.style must identify saved Brief authority")
    for subject_id in subjects:
        subject = next((item for collection in (payload.get("characters"), payload.get("scenes"), payload.get("props"))
                        if isinstance(collection, list) for item in collection
                        if isinstance(item, dict) and item.get("id") == subject_id), None)
        if subject is None:
            continue
        image = subject.get("image") if isinstance(subject.get("image"), dict) else {}
        if image.get("style") != BRIEF_STYLE_LABEL:
            raise ValueError(f"{stage} {subject_id}: image.style must use the English saved-Brief marker")
