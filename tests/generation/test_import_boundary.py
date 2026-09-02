from __future__ import annotations

import ast
from pathlib import Path


GENERATION_ROOT = Path(__file__).resolve().parents[2] / "src" / "plotloom" / "generation"
FORBIDDEN_TOP_LEVEL_IMPORTS = {"app", "backend", "narrative_forge", "static"}


def test_generation_package_has_no_legacy_runtime_imports() -> None:
    violations: list[str] = []
    for path in sorted(GENERATION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.append(node.module)
            for module in modules:
                if module.split(".", 1)[0] in FORBIDDEN_TOP_LEVEL_IMPORTS:
                    violations.append(
                        f"{path.relative_to(GENERATION_ROOT)}:{node.lineno}: {module}"
                    )
    assert not violations, "generation imports legacy runtime modules:\n" + "\n".join(violations)
