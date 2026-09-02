import ast
from pathlib import Path


PLOTLOOM_ROOT = Path(__file__).resolve().parents[1] / "src" / "plotloom"
FORBIDDEN_TOP_LEVEL_IMPORTS = {"app", "backend", "narrative_forge"}


def test_plotloom_python_package_has_no_legacy_runtime_imports():
    assert PLOTLOOM_ROOT.is_dir(), "the Plotloom Python package is missing"
    violations: list[str] = []
    for path in sorted(PLOTLOOM_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.append(node.module)
            for module in modules:
                if module.split(".", 1)[0] in FORBIDDEN_TOP_LEVEL_IMPORTS:
                    violations.append(f"{path.relative_to(PLOTLOOM_ROOT)}:{node.lineno}: {module}")
    assert not violations, "Plotloom imports legacy runtime modules:\n" + "\n".join(violations)
