"""Persistent creator composition must explicitly admit protected H3 settings."""

import importlib.util
import json
import os
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient


SERVICE = Path(__file__).resolve().parents[3] / "services" / "creator_workbench"
FIXTURE_SECRET = "creator-test-secret-not-for-a-live-gateway"


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(SERVICE))
    import h3_configuration

    def load(name):
        spec = importlib.util.spec_from_file_location(f"creator_runtime_{name}", SERVICE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return h3_configuration, load("server"), load("manage")


@pytest.fixture
def configuration(tmp_path):
    path = tmp_path / "owner.env"
    path.write_text(
        "VIDEO_PROVIDER=minimax_h3_gateway\n"
        "VIDEO_MODEL=minimax_h3_gateway_catalog_v7\n"
        "VIDEO_BASE_URL=http://100.64.1.2:8090\n"
        "VIDEO_AUTH_MODE=bearer\n"
        f"VIDEO_MODEL_API_KEY={FIXTURE_SECRET}\n"
        "PLOTLOOM_OUTPUTS_DIR=/must-not-open\n"
        "PLOTLOOM_APPLICATION_DATA_DIR=/must-not-open/application\n"
    )
    path.chmod(0o600)
    return path


def test_default_off_never_reads_parent_credentials_or_a_config_file(modules, monkeypatch):
    configuration, _server, _manager = modules
    monkeypatch.setenv("PLOTLOOM_ENABLE_H3_GATEWAY", "true")
    monkeypatch.setenv("VIDEO_MODEL_API_KEY", FIXTURE_SECRET)
    monkeypatch.setenv("PLOTLOOM_CREATOR_H3_CONFIG_FILE", "/missing/owner.env")
    monkeypatch.delenv("PLOTLOOM_CREATOR_ENABLE_H3", raising=False)
    monkeypatch.setattr(configuration, "read_h3_configuration", lambda _path: pytest.fail("disabled runtime read credentials"))
    assert configuration.creator_h3_backend() == (None, None)


def test_explicit_configuration_has_no_environment_export_or_gateway_contact(modules, configuration, monkeypatch):
    settings_module, _server, _manager = modules
    monkeypatch.setenv("VIDEO_MODEL_API_KEY", "ambient-must-not-be-consumed")
    monkeypatch.setattr(requests.Session, "request", lambda *_args, **_kwargs: pytest.fail("startup contacted a gateway"))
    before = dict(os.environ)
    settings = settings_module.read_h3_configuration(configuration)
    provider, adapter = settings_module.creator_h3_backend({
        "PLOTLOOM_CREATOR_ENABLE_H3": "true",
        "PLOTLOOM_CREATOR_H3_CONFIG_FILE": str(configuration),
    })
    assert settings.video_api_key.get_secret_value() == FIXTURE_SECRET
    assert provider is not None and adapter is not None
    assert provider._session.trust_env is False
    assert not hasattr(settings, "outputs_dir")
    assert dict(os.environ) == before


@pytest.mark.parametrize("failure", ["public-root", "secret-userinfo", "invalid-auth", "old-catalog", "foreign-provider", "missing-key", "missing-model"])
def test_invalid_configuration_fails_closed_without_secret_in_error(modules, configuration, failure):
    settings_module, _server, _manager = modules
    replacements = {
        "public-root": ("http://100.64.1.2:8090", "http://8.8.8.8:8090"),
        "secret-userinfo": ("http://100.64.1.2:8090", f"http://{FIXTURE_SECRET}@100.64.1.2:8090"),
        "invalid-auth": ("VIDEO_AUTH_MODE=bearer", f"VIDEO_AUTH_MODE={FIXTURE_SECRET}"),
        "old-catalog": ("catalog_v7", "catalog_v5"),
        "foreign-provider": ("VIDEO_PROVIDER=minimax_h3_gateway", "VIDEO_PROVIDER=other"),
        "missing-key": (f"VIDEO_MODEL_API_KEY={FIXTURE_SECRET}", "VIDEO_MODEL_API_KEY="),
        "missing-model": ("VIDEO_MODEL=minimax_h3_gateway_catalog_v7", "VIDEO_MODEL="),
    }
    old, new = replacements[failure]
    configuration.write_text(configuration.read_text().replace(old, new))
    with pytest.raises(ValueError, match="owner-only file") as error:
        settings_module.read_h3_configuration(configuration)
    assert FIXTURE_SECRET not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize("failure", ["missing", "directory", "symlink", "readable", "foreign-owner"])
def test_configuration_requires_regular_owned_private_file(modules, configuration, monkeypatch, failure):
    settings_module, _server, _manager = modules
    selected = configuration
    if failure == "missing":
        selected = configuration.with_name("missing.env")
    elif failure == "directory":
        selected = configuration.parent
    elif failure == "symlink":
        selected = configuration.with_name("linked.env")
        selected.symlink_to(configuration)
    elif failure == "readable":
        configuration.chmod(0o644)
    else:
        owner = os.getuid()
        monkeypatch.setattr(settings_module.os, "getuid", lambda: owner + 1)
    with pytest.raises(ValueError, match="owner-only file"):
        settings_module.read_h3_configuration(selected)
    assert configuration.read_text().endswith("PLOTLOOM_APPLICATION_DATA_DIR=/must-not-open/application\n")


@pytest.mark.parametrize("environment", [{"PLOTLOOM_CREATOR_ENABLE_H3": "1"}, {"PLOTLOOM_CREATOR_ENABLE_H3": "true"}])
def test_optin_requires_exact_switch_and_explicit_file(modules, environment):
    configuration, _server, _manager = modules
    with pytest.raises(ValueError):
        configuration.creator_h3_backend(environment)


@pytest.mark.parametrize("enabled", [False, True])
def test_server_keeps_installation_storage_and_redacts_public_capability(modules, configuration, tmp_path, monkeypatch, enabled):
    _settings, server, _manager = modules
    data = tmp_path / "installation"
    for directory in ("outputs", "application"):
        (data / directory).mkdir(parents=True)
    monkeypatch.setenv("PLOTLOOM_CHECKOUT", str(SERVICE.parents[1]))
    monkeypatch.setenv("PLOTLOOM_CREATOR_DATA", str(data))
    monkeypatch.setenv("PLOTLOOM_CREATOR_ENABLE_H3", "true" if enabled else "false")
    monkeypatch.setenv("PLOTLOOM_CREATOR_H3_CONFIG_FILE", str(configuration))
    monkeypatch.setenv("PLOTLOOM_OUTPUTS_DIR", "/must-not-open")
    monkeypatch.setenv("PLOTLOOM_APPLICATION_DATA_DIR", "/must-not-open")
    monkeypatch.setenv("PORT", "invalid-parent-setting")
    monkeypatch.setattr(requests.Session, "request", lambda *_args, **_kwargs: pytest.fail("startup contacted a gateway"))
    with TestClient(server.create_app()) as client:
        payload = client.get("/api/v2/video-backend").json()
        assert payload["enabled"] is enabled
        assert FIXTURE_SECRET not in json.dumps(payload)
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.app.state.specialists.path.is_relative_to(data / "application")


def test_manager_retains_only_config_path_and_disable_preserves_credentials(modules, configuration, tmp_path, monkeypatch):
    _settings, _server, manager = modules
    monkeypatch.setattr(manager, "CONFIG", tmp_path / "deployment.json")
    config = {"data": str(tmp_path / "installation"), "token": "/private/bridge-token"}
    before = configuration.read_bytes()
    manager.configure_h3(config, configuration)
    assert json.loads(manager.CONFIG.read_text())["h3_config"] == str(configuration)
    assert FIXTURE_SECRET not in manager.CONFIG.read_text()
    manager.configure_h3(config)
    assert config["h3_config"] == str(configuration)
    manager.configure_h3(config, disable=True)
    assert config["h3_config"] is None
    assert configuration.read_bytes() == before


@pytest.mark.parametrize("location", ["data", "service"])
def test_manager_rejects_credentials_inside_runtime_or_service_source(modules, tmp_path, monkeypatch, location):
    _settings, _server, manager = modules
    service = tmp_path / "service"
    monkeypatch.setattr(manager, "SERVICE", service)
    config = {"data": str(tmp_path / "installation")}
    root = Path(config["data"]) if location == "data" else service
    root.mkdir()
    with pytest.raises(ValueError, match="outside creator data and service source"):
        manager.configure_h3(config, root / "credentials.env")


def test_manager_validates_before_any_docker_or_bridge_action(modules, monkeypatch):
    _settings, _server, manager = modules
    config = {"data": "/isolated/installation", "h3_config": "/missing/owner.env"}
    monkeypatch.setattr(manager.sys, "platform", "darwin")
    monkeypatch.setattr(manager.sys, "argv", ["manage.py", "start"])
    monkeypatch.setattr(manager, "load_config", lambda _root: config)
    monkeypatch.setattr(manager, "compose", lambda *_args: pytest.fail("Docker ran before validation"))
    monkeypatch.setattr(manager, "install_bridge", lambda *_args: pytest.fail("bridge ran before validation"))
    with pytest.raises(ValueError, match="owner-only file"):
        manager.main()


@pytest.mark.parametrize("enabled", [False, True])
def test_compose_mounts_configuration_without_exporting_credential(modules, configuration, monkeypatch, enabled):
    _settings, _server, manager = modules
    calls = []
    monkeypatch.setattr(manager, "run", lambda command, **kwargs: calls.append((command, kwargs["env"])))
    config = {"data": "/isolated/installation", "token": "/private/bridge-token"}
    if enabled:
        config["h3_config"] = str(configuration)
    manager.compose(config, "ps")
    command, environment = calls[0]
    assert str(SERVICE / "compose.h3.yaml") in command if enabled else str(SERVICE / "compose.h3.yaml") not in command
    assert environment.get("PLOTLOOM_CREATOR_H3_CONFIG") == (str(configuration) if enabled else None)
    assert FIXTURE_SECRET not in json.dumps(environment)
    assert FIXTURE_SECRET not in json.dumps(command)
