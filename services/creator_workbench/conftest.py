"""Shared creator-workbench service test fixtures."""
import pytest
from codex_exec_supervisor import CodexExecSupervisor

from tests.codex_exec_runtime_fixtures import (
    codex_exec_test_source as _codex_exec_test_source,  # noqa: F401
)


@pytest.fixture
def supervisor(tmp_path, monkeypatch, codex_exec_test_source):
    executable = tmp_path / "codex"
    executable.write_text("unused in cancellation tests")
    executable.chmod(0o700)
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir(mode=0o700)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    source_root = codex_exec_test_source
    return CodexExecSupervisor(
        executable,
        source_root=source_root,
        outputs_root=outputs_root,
        private_root=tmp_path / "private",
    )
