"""Frozen character render direction and its single deterministic rule owner."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

from plotloom.domain_base import CamelModel
from .style_contract_cache import derive_style_contract

CastRenderStyle = Literal["live-action", "realistic", "ghibli"]
CandidateCastRenderStyle = Literal["live-action", "realistic", "ghibli", "brief"]
CONTRACT_FILENAME = "cast-style-contract.json"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STYLE_OWNER = PROJECT_ROOT / "scripts" / "cast-style.mjs"
STYLE_RULE_DEPENDENCIES = (
    PROJECT_ROOT
    / "third_party"
    / "shuohao-skills"
    / "skills"
    / "novel-characters"
    / "scripts"
    / "novel-characters.mjs",
)


class CastPrepareRequest(CamelModel):
    render_style: CastRenderStyle


def _run(*args: str) -> str:
    result = subprocess.run(["node", str(STYLE_OWNER), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"character render validation failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout


def freeze_cast_style(style: CandidateCastRenderStyle, direction: str | None) -> dict[str, Any]:
    if style == "brief":
        from .autopilot_brief_style import freeze_brief_style
        return freeze_brief_style(direction)
    return derive_style_contract(
        owner="cast",
        script=STYLE_OWNER,
        dependencies=STYLE_RULE_DEPENDENCIES,
        style=style,
        direction=direction,
        error_context="character render validation failed",
    )


def cast_style_current(contract: dict[str, Any] | None, direction: str | None) -> bool:
    if contract and contract.get("authority") == "saved_brief":
        from .autopilot_brief_style import brief_style_current
        return brief_style_current(contract, direction)
    return bool(contract) and contract == freeze_cast_style(contract["style"], direction)


def validate_cast_style(cast: dict[str, Any], contract: dict[str, Any] | None, request: dict[str, Any] | None = None) -> None:
    if not contract:
        raise ValueError("character render contract is missing; prepare a new task")
    if contract.get("authority") == "saved_brief":
        from .autopilot_brief_style import validate_brief_style
        validate_brief_style(cast, contract, subjects=tuple(item["id"] for item in cast.get("characters", []) if isinstance(item, dict) and isinstance(item.get("id"), str)), stage="characters")
        with tempfile.TemporaryDirectory(prefix="plotloom-brief-cast-") as directory:
            root = Path(directory)
            cast_path = root / "cast.json"
            cast_path.write_text(json.dumps(cast, ensure_ascii=False), encoding="utf-8")
            script = PROJECT_ROOT / "scripts" / "brief-cast-style.mjs"
            args = ["node", str(script), "validate", str(cast_path)]
            if request is not None:
                request_path = root / "request.json"
                request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
                args.extend(("--request", str(request_path)))
            result = subprocess.run(args, capture_output=True, text=True, check=False)
            if result.returncode:
                raise ValueError(f"character Brief style/upstream validation failed: {(result.stderr or result.stdout).strip()}")
        return
    with tempfile.TemporaryDirectory(prefix="plotloom-cast-style-") as directory:
        root = Path(directory)
        for name, value in (("cast", cast), ("contract", contract)):
            (root / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        _run("check-style", str(root / "cast.json"), "--contract", str(root / "contract.json"))
