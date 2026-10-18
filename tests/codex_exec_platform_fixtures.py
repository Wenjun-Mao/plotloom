"""Explicit provider-free host configuration, including owned worker children."""
from __future__ import annotations

from pathlib import Path

import pytest


def provider_free_host_runtime(root: Path, source_root: Path) -> tuple[Path, Path]:
    """Create configuration and startup code under one explicit fixture owner."""
    root.mkdir(mode=0o700)
    config = root / "openssl.cnf"
    config.write_text("# Provider-free fixture; no external provider configuration.\n")
    config.chmod(0o600)
    bootstrap = root / "python-startup"
    bootstrap.mkdir(mode=0o700)
    (bootstrap / "sitecustomize.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(source_root / 'src')!r})\n"
        "from plotloom import codex_exec_profile\n"
        f"codex_exec_profile.NODE_OPENSSL_CONFIG = Path({str(config)!r})\n"
    )
    return config, bootstrap


@pytest.fixture(autouse=True)
def codex_exec_test_platform(request):
    """Supply test configuration only to cases using the synthetic host source."""
    if "codex_exec_test_source" not in request.fixturenames:
        return

    from plotloom import codex_exec_profile

    monkeypatch = request.getfixturevalue("monkeypatch")
    root = request.getfixturevalue("tmp_path") / "provider-free-host"
    source = request.getfixturevalue("codex_exec_test_source")
    config, bootstrap = provider_free_host_runtime(root, source)
    monkeypatch.setattr(codex_exec_profile, "NODE_OPENSSL_CONFIG", config)
    # The existing worker environment carries sys.path to the new interpreter.
    # A parent-only monkeypatch would disappear there. This test path changes
    # only explicit fixture config, preserving copied source and its validators.
    monkeypatch.syspath_prepend(str(bootstrap))
