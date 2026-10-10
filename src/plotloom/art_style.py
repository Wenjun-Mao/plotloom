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


def freeze_art_style(style: ArtRenderStyle, author_direction: str | None) -> dict[str, Any]:
    return derive_style_contract(
        owner="art",
        script=ADAPTER,
        dependencies=STYLE_RULE_DEPENDENCIES,
        style=style,
        direction=author_direction,
        error_context="art style/upstream novel-art validation failed",
    )


def art_style_current(contract: dict[str, Any] | None, author_direction: str | None) -> bool:
    return bool(contract) and contract == freeze_art_style(contract["style"], author_direction)


def validate_art_style(art: dict[str, Any], cast: dict[str, Any], contract: dict[str, Any] | None) -> None:
    if not contract:
        raise ValueError("art render style was not frozen; prepare a replacement task")
    with tempfile.TemporaryDirectory(prefix="plotloom-art-validate-") as directory:
        root = Path(directory)
        for name, value in (("art", art), ("cast", cast), ("contract", contract)):
            (root / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        _run("validate", str(root / "art.json"), "--cast", str(root / "cast.json"), "--contract", str(root / "contract.json"))
