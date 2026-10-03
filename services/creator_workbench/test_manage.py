"""Guard login-service reinstallation and source updates using isolated paths."""

import subprocess
from pathlib import Path

import manage
import pytest


@pytest.fixture
def installation(tmp_path, monkeypatch):
    repository = tmp_path / "checkout"
    service = repository / "services" / "creator_workbench"
    service.mkdir(parents=True)
    (service / "host_bridge.py").write_text("first bridge version")
    private = repository / ".local" / "creator-workbench"
    private.mkdir(parents=True)
    monkeypatch.setattr(manage, "REPOSITORY", repository)
    monkeypatch.setattr(manage, "SERVICE", service)
    monkeypatch.setattr(manage, "CONFIG", private / "deployment.json")
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    commands = []
    monkeypatch.setattr(
        manage, "run", lambda command, **_kwargs: commands.append(command)
    )
    config = {
        "data": str(tmp_path / "data"),
        "codex": "/native/codex",
        "token": "/private/token",
    }
    return config, commands, service


def test_start_reloads_an_unloaded_bridge_and_skips_an_unchanged_running_bridge(
    installation, monkeypatch
):
    config, commands, _service = installation
    manage.install_bridge(config)
    assert commands[-1][1] == "bootstrap"
    commands.clear()
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 1),
    )
    manage.install_bridge(config)
    assert len(commands) == 1 and commands[0][1] == "bootstrap"
    commands.clear()
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0),
    )
    manage.install_bridge(config)
    assert not commands


def test_start_reloads_changed_bridge_code_at_the_same_source_path(installation):
    config, commands, service = installation
    manage.install_bridge(config)
    commands.clear()
    (service / "host_bridge.py").write_text("updated bridge version")
    manage.install_bridge(config)
    assert [command[1] for command in commands] == ["bootout", "bootstrap"]


def test_start_recreates_backend_when_only_mounted_python_source_changes(monkeypatch):
    config = {"data": "/isolated/data", "token": "/private/token", "codex": "/native/codex"}
    calls = []
    monkeypatch.setattr(manage.sys, "platform", "darwin")
    monkeypatch.setattr(manage.sys, "argv", ["manage.py", "start"])
    monkeypatch.setattr(manage, "load_config", lambda _root: config)
    monkeypatch.setattr(manage, "install_bridge", lambda value: calls.append(("bridge", value)))
    monkeypatch.setattr(manage, "compose", lambda value, *args: calls.append(("compose", value, args)))
    manage.main()
    assert calls == [
        ("compose", config, ("build",)),
        ("bridge", config),
        ("compose", config, ("up", "-d", "--force-recreate", "--wait", "--wait-timeout", "90")),
        ("compose", config, ("exec", "-T", "workbench", "codex", "bridge-health")),
    ]


def test_existing_credentials_are_secured_without_changing_the_token(tmp_path):
    private = tmp_path / "private"
    private.mkdir(mode=0o755)
    token = private / "bridge-token"
    token.write_text("preserved-token" * 4)
    token.chmod(0o644)
    assert manage.secure_token(private, create=False) == token
    assert private.stat().st_mode & 0o777 == 0o700
    assert token.stat().st_mode & 0o777 == 0o600
    assert token.read_text() == "preserved-token" * 4


def test_symlink_credentials_are_rejected_without_changing_the_target(tmp_path):
    private = tmp_path / "private"
    private.mkdir()
    target = tmp_path / "other-token"
    target.write_text("not-the-bridge-token" * 4)
    target.chmod(0o644)
    (private / "bridge-token").symlink_to(target)
    with pytest.raises(ValueError, match="regular file"):
        manage.secure_token(private, create=False)
    assert target.stat().st_mode & 0o777 == 0o644
