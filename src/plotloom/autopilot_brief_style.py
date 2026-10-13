"""Exact saved-Brief style authority for autopilot Cast and Art candidates."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

BRIEF_STYLE = "saved-brief"
BRIEF_STYLE_LABEL = "Saved Brief direction"
EMPTY_DIRECTION = "尊重故事设定，由专业助手结合内容判断视觉表达；不默认真人实拍或其他预设。"


def freeze_brief_style(direction: str | None) -> dict[str, Any]:
    payload = {"version": 1, "authority": "saved_brief", "direction": direction,
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
