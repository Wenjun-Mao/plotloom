"""Test-owned source and runtime metadata for provider-free host contract tests.

This checkout deliberately has no usable validator dependency environment. Tests
exercise real read-only inspection of a small synthetic receipt; native runtime
execution is qualified separately with an explicitly provisioned environment.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from plotloom.codex_exec_python_environment import (
    ENVIRONMENT_PATH,
    RECEIPT_PATH,
    _snapshot,
)


def _clone(source: Path, destination: Path) -> None:
    subprocess.run(
        ["git", "clone", "--shared", "--no-hardlinks", "--quiet", str(source), str(destination)],
        check=True, capture_output=True, timeout=30,
    )
    revision = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, timeout=5,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(destination), "checkout", "--quiet", "--detach", revision],
        check=True, capture_output=True, timeout=30,
    )


@pytest.fixture(scope="session", name="codex_exec_test_source")
def codex_exec_test_source(tmp_path_factory):
    """Use committed source copies and synthetic owned runtime files, never .local."""
    original = Path(__file__).resolve().parents[1]
    fixture_root = tmp_path_factory.mktemp("codex-exec-source").resolve()
    source = fixture_root / "checkout"
    _clone(original, source)
    _clone(original / "third_party/shuohao-skills", source / "third_party/shuohao-skills")
    version = ".".join(str(value) for value in sys.version_info[:3])
    runtime = fixture_root / f"cpython-{version}-fixture"
    (runtime / "bin").mkdir(parents=True)
    base = runtime / f"bin/python{sys.version_info.major}.{sys.version_info.minor}"
    base.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "--version" ]; then echo "Python {version}"; exit 0; fi\n'
        "exit 78\n"
    )
    base.chmod(0o700)
    environment = source / ENVIRONMENT_PATH
    (environment / "bin").mkdir(parents=True)
    copied = environment / "bin/python"
    copied.write_bytes(base.read_bytes())
    copied.chmod(0o700)
    (environment / "lib").mkdir()
    (environment / "lib/fixture_dependency.py").write_text("fixture dependency identity\n")
    (environment / "pyvenv.cfg").write_text(
        f"home = {base.parent}\ninclude-system-site-packages = false\nversion = {version}\n"
        f"executable = {base}\ncommand = explicit test-owned metadata fixture\n"
    )
    (source / RECEIPT_PATH).write_text(json.dumps(_snapshot(source)))
    return source
