"""Shared creator-workbench service test fixtures."""
from pathlib import Path

import pytest

from codex_exec_supervisor import CodexExecSupervisor


@pytest.fixture
def supervisor(tmp_path, monkeypatch):
    executable = tmp_path / "codex"
    executable.write_text("unused in cancellation tests")
    executable.chmod(0o700)
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir(mode=0o700)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    source_root = Path(__file__).resolve().parents[2]
    return CodexExecSupervisor(
        executable,
        source_root=source_root,
        outputs_root=outputs_root,
        private_root=tmp_path / "private",
    )
