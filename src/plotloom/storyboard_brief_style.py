"""F5A's frozen receiving authority inherited from accepted saved-Brief Art."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .autopilot_brief_style import BRIEF_STYLE, BRIEF_STYLE_LABEL

CONTRACT_VERSION = "plotloom.saved-brief.storyboard.v1"
INSTRUCTION_VERSION = "plotloom.autopilot.saved-brief-storyboard-receiving-contract.v1"
CONTRACT_FILENAME = "storyboard-style-contract.json"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADAPTER = PROJECT_ROOT / "scripts/brief-storyboard-style.mjs"
UPSTREAM = PROJECT_ROOT / "third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs"


def _digest(value: dict[str, Any]) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def freeze_storyboard_brief_style(inherited: dict[str, Any] | None) -> dict[str, Any]:
    """Use accepted Art metadata, never ambient Brief or model-authored direction."""
    if not inherited or inherited.get("authority") != "saved_brief":
        raise ValueError("storyboard saved-Brief authority requires the inherited Art contract")
    parent = {key: value for key, value in inherited.items() if key != "contentHash"}
    if inherited.get("contentHash") != _digest(parent):
        raise ValueError("inherited Art visual authority is malformed")
    direction = inherited.get("direction")
    if direction is not None and not isinstance(direction, str):
        raise ValueError("inherited Art direction must be text or empty")
    payload = {
        "version": CONTRACT_VERSION, "authority": "saved_brief",
        "stageInstructionContract": INSTRUCTION_VERSION,
        "direction": direction, "emptyDirectionRule": inherited.get("emptyDirectionRule"),
        "inheritedArtRenderContract": inherited,
        "validatorHashes": {
            name: sha256(path.read_bytes()).hexdigest()
            for name, path in {
                "policy": Path(__file__), "adapter": ADAPTER, "upstream": UPSTREAM,
                "upstreamGateSummary": UPSTREAM.with_name("gate-summary.mjs"),
            }.items()
        },
    }
    return payload | {"contentHash": _digest(payload)}


def storyboard_brief_style_current(contract: dict[str, Any], inherited: dict[str, Any] | None) -> bool:
    try:
        return contract == freeze_storyboard_brief_style(inherited)
    except (ValueError, OSError):
        return False


def validate_storyboard_brief_authority(
    storyboard: dict[str, Any], contract: dict[str, Any], inherited: dict[str, Any] | None,
) -> None:
    if not storyboard_brief_style_current(contract, inherited):
        raise ValueError("storyboard saved-Brief authority is stale or malformed")
    if storyboard.get("style") != BRIEF_STYLE:
        raise ValueError("storyboard.style must identify saved Brief authority")
    if storyboard.get("promptLang") != "en":
        raise ValueError("saved-Brief storyboard promptLang must be en")


def storyboard_brief_instructions() -> str:
    validate = 'node scripts/brief-storyboard-style.mjs validate "$DELIVERY_ROOT/storyboard.json" --request "$PACKAGE_ROOT/request.json"'
    render = 'node scripts/brief-storyboard-style.mjs render "$DELIVERY_ROOT/storyboard.json" --request "$PACKAGE_ROOT/request.json" > "$DELIVERY_ROOT/report.html"'
    return (
        f" EXPLICIT SAVED-BRIEF RECEIVING-CONTRACT OVERRIDE ({INSTRUCTION_VERSION}): "
        f"The frozen inputs/{CONTRACT_FILENAME} inherits the exact accepted Art visual authority and takes "
        "precedence over conflicting preset-specific instructions in pinned novel-storyboard. This replaces "
        "only preset selection/defaults, preset matching/phrases and preset-specific validate/render commands. "
        "Every other upstream structural, script coverage, timing, source/name, language, shot-recipe and H3 "
        "gate remains in force. The author owns the exact direction in the frozen contract; interpret it "
        "faithfully in English in every cut.frame and H3 visual description. Do not copy non-English direction "
        "into machine prompts. Empty direction permits story-informed discretion with no preset default. "
        f"Set storyboard.style to `{BRIEF_STYLE}`, promptLang to `en`, and include the neutral authority marker "
        f"`{BRIEF_STYLE_LABEL}` in every cut.frame. The marker proves authority membership, not creative fidelity; "
        "semantic fidelity remains human-reviewed. Do not inject photographic/Ghibli phrases or model-authored "
        "style authority. request.json and all package inputs are read-only; author only storyboard.json and "
        "derive report.html. No Markdown, H3 export pack, media or other delivery outputs are permitted. "
        "Resolve PACKAGE_ROOT as the absolute task-package directory containing request.json and inputs/, and "
        "DELIVERY_ROOT as the absolute assigned delivery directory. From the Plotloom repository root, run exactly:\n"
        f"{validate}\n{render}\n"
    )
