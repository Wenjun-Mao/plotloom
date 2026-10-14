"""Make the source-owned creator-workbench service available to focused tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
SERVICE_SOURCE = Path(__file__).resolve().parents[3] / "services" / "creator_workbench"
sys.path.insert(0, str(SERVICE_SOURCE))


@pytest.fixture
def supervisor(tmp_path, monkeypatch):
    from codex_exec_supervisor import CodexExecSupervisor

    executable = tmp_path / "codex"
    executable.write_text("unused in validator lifecycle tests")
    executable.chmod(0o700)
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir(mode=0o700)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    source_root = Path(__file__).resolve().parents[3]
    return CodexExecSupervisor(
        executable,
        source_root=source_root,
        outputs_root=outputs_root,
        private_root=tmp_path / "private",
    )
