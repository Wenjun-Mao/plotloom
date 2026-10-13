"""Frozen author style and the shared upstream-preserving art adapter."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

from .domain import CamelModel
from .style_contract_cache import derive_style_contract

ArtRenderStyle = Literal["live-action", "realistic", "ghibli"]
CandidateArtRenderStyle = Literal["live-action", "realistic", "ghibli", "brief"]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADAPTER = PROJECT_ROOT / "scripts" / "art-style.mjs"
STYLE_RULE_DEPENDENCIES = (
    PROJECT_ROOT
    / "third_party"
    / "shuohao-skills"
    / "skills"
    / "novel-art"
    / "scripts"
    / "novel-art.mjs",
    PROJECT_ROOT
    / "third_party"
    / "shuohao-skills"
    / "skills"
    / "novel-art"
    / "scripts"
    / "gate-summary.mjs",
)


def _run(*args: str) -> str:
    result = subprocess.run(["node", str(ADAPTER), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"art style/upstream novel-art validation failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout


class ArtPrepareRequest(CamelModel):
    render_style: ArtRenderStyle


def freeze_art_style(style: CandidateArtRenderStyle, author_direction: str | None) -> dict[str, Any]:
    if style == "brief":
        from .autopilot_brief_style import freeze_brief_style
        return freeze_brief_style(author_direction)
    return derive_style_contract(
        owner="art",
        script=ADAPTER,
        dependencies=STYLE_RULE_DEPENDENCIES,
        style=style,
        direction=author_direction,
        error_context="art style/upstream novel-art validation failed",
    )


def art_style_current(contract: dict[str, Any] | None, author_direction: str | None) -> bool:
    if contract and contract.get("authority") == "saved_brief":
        from .autopilot_brief_style import brief_style_current
        return brief_style_current(contract, author_direction)
    return bool(contract) and contract == freeze_art_style(contract["style"], author_direction)


def validate_art_style(art: dict[str, Any], cast: dict[str, Any], contract: dict[str, Any] | None) -> None:
    if not contract:
        raise ValueError("art render style was not frozen; prepare a replacement task")
    if contract.get("authority") == "saved_brief":
        from .autopilot_brief_style import validate_brief_style
        subjects = tuple(item["id"] for key in ("scenes", "props") for item in art.get(key, []) if isinstance(item, dict) and isinstance(item.get("id"), str))
        validate_brief_style(art, contract, subjects=subjects, stage="art")
        with tempfile.TemporaryDirectory(prefix="plotloom-brief-art-") as directory:
            root = Path(directory)
            art_path, cast_path = root / "art.json", root / "cast.json"
            art_path.write_text(json.dumps(art, ensure_ascii=False), encoding="utf-8")
            cast_path.write_text(json.dumps(cast, ensure_ascii=False), encoding="utf-8")
            script = PROJECT_ROOT / "scripts" / "brief-art-style.mjs"
            result = subprocess.run(["node", str(script), "validate", str(art_path), "--cast", str(cast_path)], capture_output=True, text=True, check=False)
            if result.returncode:
                raise ValueError(f"art Brief style/upstream validation failed: {(result.stderr or result.stdout).strip()}")
        return
    with tempfile.TemporaryDirectory(prefix="plotloom-art-validate-") as directory:
        root = Path(directory)
        for name, value in (("art", art), ("cast", cast), ("contract", contract)):
            (root / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        _run("validate", str(root / "art.json"), "--cast", str(root / "cast.json"), "--contract", str(root / "contract.json"))
