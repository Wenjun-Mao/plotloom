"""Frozen character render direction and its single deterministic rule owner."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

from .domain import CamelModel
from .style_contract_cache import derive_style_contract

CastRenderStyle = Literal["live-action", "realistic", "ghibli"]
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


def freeze_cast_style(style: CastRenderStyle, direction: str | None) -> dict[str, Any]:
    return derive_style_contract(
        owner="cast",
        script=STYLE_OWNER,
        dependencies=STYLE_RULE_DEPENDENCIES,
        style=style,
        direction=direction,
        error_context="character render validation failed",
    )


def cast_style_current(contract: dict[str, Any] | None, direction: str | None) -> bool:
    return bool(contract) and contract == freeze_cast_style(contract["style"], direction)


def validate_cast_style(cast: dict[str, Any], contract: dict[str, Any] | None) -> None:
    if not contract:
        raise ValueError("character render contract is missing; prepare a new task")
    with tempfile.TemporaryDirectory(prefix="plotloom-cast-style-") as directory:
        root = Path(directory)
        for name, value in (("cast", cast), ("contract", contract)):
            (root / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        _run("check-style", str(root / "cast.json"), "--contract", str(root / "contract.json"))
