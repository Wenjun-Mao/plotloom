import subprocess

import pytest

from plotloom.codex_exec_auth import (
    AUTHENTICATION_STORE,
    check_codex_exec_readiness,
    resolve_codex_home,
)


def test_readiness_uses_existing_file_store_and_discards_cli_text(tmp_path, monkeypatch):
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir(mode=0o700)
    executable = tmp_path / "codex"
    executable.touch()
    observed = []

    def login_status(command, **options):
        observed.append((command, options))
        return subprocess.CompletedProcess(command, 0, b"private login details", b"")

    monkeypatch.setattr(subprocess, "run", login_status)
    readiness = check_codex_exec_readiness(
        executable,
        environment={"CODEX_HOME": str(codex_home), "OPENAI_API_KEY": "not-forwarded"},
        timeout_seconds=2,
    )

    assert readiness.state == "ready"
    assert observed[0][0] == [
        str(executable), "--config", f'cli_auth_credentials_store="{AUTHENTICATION_STORE}"',
        "login", "status",
    ]
    assert observed[0][1]["env"]["CODEX_HOME"] == str(codex_home)
    assert "OPENAI_API_KEY" not in observed[0][1]["env"]
    assert "private login details" not in repr(readiness.model_dump())


def test_readiness_distinguishes_missing_login_from_invalid_auth_home(tmp_path, monkeypatch):
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir(mode=0o700)
    executable = tmp_path / "codex"
    executable.touch()
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_options: subprocess.CompletedProcess(command, 1, b"private", b""),
    )

    assert check_codex_exec_readiness(
        executable, environment={"CODEX_HOME": str(codex_home)}
    ).state == "not_authenticated"
    assert check_codex_exec_readiness(
        executable, environment={"CODEX_HOME": str(tmp_path / "missing")}
    ).state == "unavailable"


def test_auth_home_must_not_live_inside_project_or_output_state(tmp_path):
    outputs = tmp_path / "outputs"
    auth_home = outputs / "codex-home"
    auth_home.mkdir(parents=True)

    with pytest.raises(ValueError, match="project or supervisor state"):
        resolve_codex_home({"CODEX_HOME": str(auth_home)}, forbidden_roots=(outputs,))
