"""Plotloom consumes media-service HTTP; backend source has a separate owner."""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OWNERS = {
    "plotloom": ROOT / "src/plotloom",
    "creator_workbench": ROOT / "services/creator_workbench",
}
BACKEND_PACKAGES = {"plotloom_h3_gateway", "plotloom_voice_lab"}


def imported_roots(source: str) -> set[str]:
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            imports.add(node.module.split(".")[0])
    return imports


@pytest.mark.parametrize("owner", OWNERS)
def test_consumers_do_not_import_backend_runtime(owner):
    sources = list(OWNERS[owner].rglob("*.py"))
    assert OWNERS[owner].is_dir() and sources
    violations = []
    for source in sources:
        foreign = imported_roots(source.read_text()) & BACKEND_PACKAGES
        if foreign:
            violations.append((str(source.relative_to(ROOT)), sorted(foreign)))
    assert not violations, violations


def test_backend_source_is_not_vendored_in_plotloom():
    for name in ("minimax_h3_gateway", "qwen3_tts_voice_lab"):
        assert not (ROOT / "services" / name).exists()


def test_guard_recognizes_backend_and_relative_imports():
    assert imported_roots("from ..contracts import GatewaySettings") == set()
    assert imported_roots("from plotloom.runtime import main") == {"plotloom"}
    assert imported_roots("import plotloom_voice_lab.api as api") == {"plotloom_voice_lab"}
