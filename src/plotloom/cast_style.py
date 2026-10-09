"""Frozen character render direction and its single deterministic rule owner."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Literal

from .domain import CamelModel

CastRenderStyle = Literal["live-action", "realistic", "ghibli"]
CONTRACT_FILENAME = "cast-style-contract.json"
STYLE_OWNER = Path(__file__).resolve().parents[2] / "scripts" / "cast-style.mjs"


class CastPrepareRequest(CamelModel):
    render_style: CastRenderStyle


def _run(*args: str) -> str:
    result = subprocess.run(["node", str(STYLE_OWNER), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"character render validation failed: {(result.stderr or result.stdout).strip()}")
    return result.stdout


def freeze_cast_style(style: CastRenderStyle, direction: str | None) -> dict[str, Any]:
    return json.loads(_run("contract", "--style", style, "--author-direction", json.dumps(direction)))


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
