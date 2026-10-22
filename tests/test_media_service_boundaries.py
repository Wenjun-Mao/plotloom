"""The monorepo shares source review, not product or inference dependencies."""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OWNERS = {
    "plotloom": ROOT / "src/plotloom",
    "plotloom_h3_gateway": ROOT / "services/minimax_h3_gateway/src/plotloom_h3_gateway",
    "plotloom_voice_lab": ROOT / "services/qwen3_tts_voice_lab/src/plotloom_voice_lab",
}


def imported_roots(source: str) -> set[str]:
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            imports.add(node.module.split(".")[0])
    return imports


@pytest.mark.parametrize("owner", OWNERS)
def test_runtime_owners_do_not_import_each_other(owner):
    violations = []
    for source in OWNERS[owner].rglob("*.py"):
        foreign = imported_roots(source.read_text()) & (OWNERS.keys() - {owner})
        if foreign:
            violations.append((str(source.relative_to(ROOT)), sorted(foreign)))
    assert not violations, violations


def test_guard_allows_internal_dashboard_imports_but_detects_foreign_runtime():
    assert imported_roots("from ..contracts import GatewaySettings") == set()
    assert imported_roots("from plotloom.runtime import main") == {"plotloom"}
    assert imported_roots("import plotloom_voice_lab.api as api") == {"plotloom_voice_lab"}
