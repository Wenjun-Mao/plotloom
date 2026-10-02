"""Qualify the real isolated HTTP/shim/native boundary with test-owned fake tasks."""

import json
import os
import shlex
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import replace
from threading import Thread
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

import isolated
import pytest
import uvicorn
from isolated import RuntimeConfig, compose

from plotloom.art_contracts import ArtAcceptRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from tests.test_project_storage_art import _deliver, _prepare_art_context


@pytest.fixture
def installation(tmp_path, monkeypatch):
    data = tmp_path / "copy"
    for directory in ("outputs", "application"):
        (data / directory).mkdir(parents=True)
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<title>Isolated fixture</title>")
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    token = private / "token"
    token.write_text("fixture-private-token-" * 4)
    token.chmod(0o600)
    calls = tmp_path / "native-calls.jsonl"
    fake = tmp_path / "native.py"
    fake.write_text(
        "import json, sys\n"
        f"with open({str(calls)!r}, 'a') as log:\n"
        "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
    )
    executable = tmp_path / "native"
    executable.write_text(
        f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(fake))} \"$@\"\n"
    )
    executable.chmod(0o700)
    # A contaminated parent configuration must not route the copy elsewhere.
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", "/does-not-exist")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("no_proxy", "")
    original_run = subprocess.run

    def run(command, **options):
        # Keep the complete transport real; stub only desktop navigation so
        # fixture UUIDs can never open or queue an actual user chat.
        if command[0] == "/usr/bin/open":
            return subprocess.CompletedProcess(command, 0)
        return original_run(command, **options)

    monkeypatch.setattr(subprocess, "run", run)
    return RuntimeConfig(data, static, executable, token, 0, 0), calls


def request(url, payload=None, token=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with build_opener(ProxyHandler({})).open(Request(
        url, data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers, method=method,
    ), timeout=5) as response:
        return json.load(response)


def native_calls(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def bytes_under(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


@contextmanager
def serving(runtime):
    server = uvicorn.Server(uvicorn.Config(runtime.app, log_level="error", access_log=False))
    thread = Thread(target=server.run, kwargs={"sockets": [runtime.socket]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            if not thread.is_alive():
                pytest.fail("owned server exited before startup")
            time.sleep(0.01)
        assert server.started
        yield
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive()


def bind_roles(url):
    settings = {role: {"name": f"fixture-{role}", "taskId": str(uuid4())} for role in ("text", "image")}
    assert request(url + "/api/v2/specialists", settings, method="PUT")["busy"] is False
    return settings


def prepare_art(runtime):
    storage = runtime.app.state.project_folder_storage
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        candidate, frozen = store.prepare_art_candidate("ch_" + "r" * 32, render_style="realistic")
        ready = store.admit_art_delivery(_deliver(store, frozen))
        store.accept_art_candidate(ArtAcceptRequest(
            job_id=candidate.job_id, expected_art_revision=0, binding=binding, art=ready.art,
        ))
    finally:
        store.close()
    return project_id


@pytest.mark.parametrize("role", ["text", "image"])
def test_full_http_dispatch_uses_one_settings_owner_and_actual_outbound_shim(installation, role):
    config, calls = installation
    normal = config.data_root.parent / "normal"
    normal.mkdir()
    (normal / "settings.json").write_text('{"unchanged":true}')
    (normal / "inflight.json").write_text('{"state":"outcome_unknown"}')
    before = bytes_under(normal)
    with compose(config) as runtime, serving(runtime):
        assert runtime.bridge.settings == runtime.app.state.specialists.path
        assert runtime.bridge.settings == config.data_root / "application/specialists/settings.json"
        assert runtime.app.state.specialists.executable == str(runtime.shim)
        assert runtime.app.state.specialists.environment["PLOTLOOM_CODEX_BRIDGE_URL"] == runtime.bridge_url
        assert runtime.app.state.specialists.environment["PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE"] == str(config.token_file)
        assert runtime.app.state.specialists.environment["no_proxy"] == "127.0.0.1"
        settings = bind_roles(runtime.url)
        project_id = prepare_art(runtime)
        endpoint = runtime.url + f"/api/v2/projects/{project_id}"
        if role == "text":
            candidate = request(endpoint + "/art/candidates", {"renderStyle": "realistic"}, method="POST")
            job = candidate["jobId"]
            sent = request(endpoint + f"/specialist-tasks/art/{job}/send", {}, method="POST")
            assert sent["state"] == "queued"
        else:
            prepared = request(endpoint + "/art-reference-proposals", {
                "subjectType": "scene", "subjectId": "S01",
                "renderDirection": "Fixture-only photographic empty room.",
            }, method="POST")
            job = prepared["proposal"]["id"]
            request(endpoint + f"/art-reference-proposals/{job}/send", {}, method="POST")
        queued = native_calls(calls)
        assert len(queued) == 1
        assert queued[0][:3] == ["queue", "--thread", settings[role]["taskId"]]
        assert str(config.data_root / "outputs") in queued[0][-1]
        root = config.data_root / "application/specialists/dispatch" / settings[role]["taskId"]
        assert json.loads((root / job / "receipt.json").read_text())["state"] == "queued"
        assert json.loads((root / "inflight.json").read_text())["jobId"] == job
        # Health and a repeated send never add native queues.
        assert request(runtime.url + "/healthz") == {"status": "ok"}
        result = subprocess.run(
            [str(runtime.shim), "bridge-health"],
            env=runtime.app.state.specialists.environment, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0
        with pytest.raises(HTTPError):
            if role == "text":
                request(endpoint + f"/specialist-tasks/art/{job}/send", {}, method="POST")
            else:
                request(endpoint + f"/art-reference-proposals/{job}/send", {}, method="POST")
        assert len(native_calls(calls)) == 1
        assert bytes_under(normal) == before
        token = config.token_file.read_bytes()
        assert all(token not in value for value in bytes_under(config.data_root).values())
        assert token not in runtime.shim.read_bytes()
        bridge_port = runtime.bridge_server.server_port
        shim = runtime.shim
    assert not runtime.bridge_thread.is_alive()
    assert not shim.exists()
    assert runtime.socket.fileno() == -1
    assert runtime.bridge_server.socket.fileno() == -1
    with socket.socket() as released:
        released.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        released.bind(("127.0.0.1", bridge_port))


def test_foreign_installation_tasks_auth_and_health_queue_nothing(installation):
    config, calls = installation
    other = replace(config, data_root=config.data_root.parent / "other")
    for name in ("outputs", "application"):
        (other.data_root / name).mkdir(parents=True)
    with compose(config) as runtime, compose(other) as foreign, serving(runtime), serving(foreign):
        bind_roles(runtime.url)
        foreign_settings = bind_roles(foreign.url)
        foreign_before = bytes_under(other.data_root / "application")
        token = config.token_file.read_text().strip()
        assert request(runtime.bridge_url + "/healthz", token=token) == {"status": "ok"}
        assert request(runtime.url + "/healthz") == {"status": "ok"}
        with pytest.raises(HTTPError) as failure:
            request(runtime.bridge_url + "/queue", {"thread": str(uuid4()), "message": "fixture"}, token="wrong")
        assert failure.value.code == 401
        for role in ("text", "image"):
            with pytest.raises(HTTPError) as failure:
                request(runtime.bridge_url + "/queue", {
                    "thread": foreign_settings[role]["taskId"], "message": "foreign fixture",
                }, token=token)
            assert failure.value.code == 400
        assert native_calls(calls) == []
        assert bytes_under(other.data_root / "application") == foreign_before


def test_unknown_native_exit_retains_exact_attempt_across_runtime_restart(installation):
    config, calls = installation
    fake = config.native_executable.with_name("native.py")
    fake.write_text(fake.read_text() + "raise SystemExit(1)\n")
    with compose(config) as runtime, serving(runtime):
        settings = bind_roles(runtime.url)
        project_id = prepare_art(runtime)
        endpoint = runtime.url + f"/api/v2/projects/{project_id}"
        candidate = request(endpoint + "/art/candidates", {"renderStyle": "realistic"}, method="POST")
        job = candidate["jobId"]
        with pytest.raises(HTTPError) as failure:
            request(endpoint + f"/specialist-tasks/art/{job}/send", {}, method="POST")
        assert failure.value.code == 422
        root = config.data_root / "application/specialists/dispatch" / settings["text"]["taskId"]
        assert json.loads((root / job / "receipt.json").read_text())["state"] == "outcome_unknown"
        before = bytes_under(root)
    with compose(config) as runtime, serving(runtime):
        assert request(runtime.url + "/api/v2/specialists")["busy"]
        with pytest.raises(HTTPError):
            request(runtime.url + f"/api/v2/projects/{project_id}/specialist-tasks/art/{job}/send", {}, method="POST")
        with pytest.raises(HTTPError):
            request(runtime.url + "/api/v2/specialists", settings, method="PUT")
        assert bytes_under(root) == before
        assert len(native_calls(calls)) == 1


@pytest.mark.parametrize("failure", ["permissions", "credential-state", "symlink", "foreign-root", "missing-native", "same-port"])
def test_invalid_runtime_fails_before_creating_bindings_or_queueing(installation, failure):
    config, calls = installation
    if failure == "permissions":
        config.token_file.chmod(0o644)
    elif failure == "credential-state":
        token = config.data_root / "application/token"
        token.write_text(config.token_file.read_text())
        token.chmod(0o600)
        config = replace(config, token_file=token)
    elif failure == "symlink":
        (config.data_root / "application/foreign").symlink_to(config.token_file.parent, target_is_directory=True)
    elif failure == "foreign-root":
        settings = config.data_root / "application/specialists/settings.json"
        settings.parent.mkdir()
        settings.write_text(json.dumps({"roots": {"fixture": str(config.data_root.parent / "normal")}}))
    elif failure == "missing-native":
        config = replace(config, native_executable=config.native_executable.parent / "missing")
    else:
        config = replace(config, port=8859, bridge_port=8859)
    before = bytes_under(config.data_root)
    with pytest.raises((ValueError, FileNotFoundError)), compose(config):
        pytest.fail("invalid runtime must never serve")
    assert bytes_under(config.data_root) == before
    assert native_calls(calls) == []


def test_startup_composition_failure_and_exception_release_owned_resources(installation, monkeypatch):
    config, calls = installation
    sockets = []
    original_socket = socket.socket

    def tracked_socket(*args, **kwargs):
        value = original_socket(*args, **kwargs)
        sockets.append(value)
        return value

    monkeypatch.setattr(isolated.socket, "socket", tracked_socket)

    def fail(*args, **kwargs):
        raise ValueError("fixture composition failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(isolated, "create_project_folder_authoring_app", fail)
        with pytest.raises(ValueError, match="fixture composition"), compose(config):
            pytest.fail("must not serve")
    assert all(value.fileno() == -1 for value in sockets)
    with pytest.raises(RuntimeError, match="fixture exit"), compose(config) as runtime:
        raise RuntimeError("fixture exit")
    assert not runtime.bridge_thread.is_alive()
    assert not runtime.shim.exists()
    assert native_calls(calls) == []


def test_cli_sigterm_cleans_bridge_ports_and_ephemeral_shim(installation):
    config, calls = installation
    temporary = config.data_root.parent / "owned-tmp"
    temporary.mkdir(mode=0o700)
    ports = []
    for _ in range(2):
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            ports.append(reservation.getsockname()[1])
    command = [
        sys.executable, isolated.__file__, "--data-root", str(config.data_root),
        "--static-dir", str(config.static_dir), "--codex", str(config.native_executable),
        "--token-file", str(config.token_file), "--port", str(ports[0]),
        "--bridge-port", str(ports[1]),
    ]
    with subprocess.Popen(command, env=os.environ | {"TMPDIR": str(temporary)},
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as process:
        try:
            deadline = time.monotonic() + 10
            while True:
                assert process.poll() is None
                try:
                    assert request(f"http://127.0.0.1:{ports[0]}/healthz") == {"status": "ok"}
                    break
                except OSError:
                    assert time.monotonic() < deadline
                    time.sleep(0.02)
            assert len(list(temporary.glob("plotloom-isolated-*"))) == 1
        finally:
            process.terminate()
            process.wait(timeout=10)
    assert process.returncode == 0
    assert not list(temporary.iterdir())
    assert native_calls(calls) == []
    for port in ports:
        with socket.socket() as released:
            released.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            released.bind(("127.0.0.1", port))


def test_h3_is_explicit_default_off_even_with_enabled_parent_settings(installation, monkeypatch):
    config, _ = installation
    monkeypatch.setenv("PLOTLOOM_ENABLE_H3_GATEWAY", "true")
    monkeypatch.setenv("VIDEO_PROVIDER", "untrusted")
    monkeypatch.setenv("VIDEO_MODEL_API_KEY", "fixture-secret")
    with compose(config) as runtime:
        assert not config.enable_h3
        # Disabled composition must never consume the parent's provider/credential.
        from fastapi.testclient import TestClient
        with TestClient(runtime.app) as client:
            assert client.get("/api/v2/video-backend").json()["enabled"] is False
    assert monkeypatch is not None


def test_h3_optin_keeps_runtimeconfig_storage_authority(installation, monkeypatch):
    config, _ = installation
    monkeypatch.setenv("VIDEO_PROVIDER", "minimax_h3_gateway")
    monkeypatch.setenv("VIDEO_MODEL", "minimax_h3_gateway_catalog_v7")
    monkeypatch.setenv("VIDEO_BASE_URL", "http://100.64.1.2:8090")
    monkeypatch.setenv("VIDEO_MODEL_API_KEY", "fixture-secret")
    monkeypatch.setenv("PLOTLOOM_OUTPUTS_DIR", "/normal-must-not-open")
    monkeypatch.setenv("PLOTLOOM_APPLICATION_DATA_DIR", "/normal-application-must-not-open")
    with compose(replace(config, enable_h3=True)) as runtime:
        assert runtime.app.state.specialists.path.is_relative_to(config.data_root)
        from fastapi.testclient import TestClient
        with TestClient(runtime.app) as client:
            payload = client.get("/api/v2/video-backend").json()
            assert payload["enabled"] is True
            assert "fixture-secret" not in json.dumps(payload)


def test_trusted_dotenv_provider_precedence_with_unexported_video_settings(installation, tmp_path, monkeypatch):
    config, _ = installation
    for key in ("VIDEO_PROVIDER", "VIDEO_MODEL", "VIDEO_BASE_URL", "VIDEO_MODEL_API_KEY", "PLOTLOOM_OUTPUTS_DIR", "PLOTLOOM_APPLICATION_DATA_DIR"):
        monkeypatch.delenv(key, raising=False)
    checkout = tmp_path / "trusted-checkout"; checkout.mkdir()
    (checkout / ".env").write_text(
        "VIDEO_PROVIDER=minimax_h3_gateway\nVIDEO_MODEL=minimax_h3_gateway_catalog_v7\n"
        "VIDEO_BASE_URL=http://100.64.1.2:8090\nVIDEO_MODEL_API_KEY=fixture-dotenv-key\n"
        "PLOTLOOM_OUTPUTS_DIR=/normal-do-not-open\nPLOTLOOM_APPLICATION_DATA_DIR=/normal-do-not-open-app\n"
    )
    settings = isolated.load_h3_configuration(checkout)
    assert settings.video_api_key.get_secret_value() == "fixture-dotenv-key"
    assert settings.video_base_url == "http://100.64.1.2:8090"
    assert not hasattr(settings, "outputs_dir")
    assert not hasattr(settings, "application_data_dir")
    monkeypatch.setenv("VIDEO_BASE_URL", "http://100.64.1.3:8090")
    assert isolated.load_h3_configuration(checkout).video_base_url == "http://100.64.1.3:8090"


def test_enable_h3_requires_boolean_not_an_extra_port(installation):
    config, _ = installation
    with pytest.raises(ValueError, match="boolean"):
        replace(config, enable_h3=8853).validated()


@pytest.mark.parametrize("ambient", ["equal", "nested", "obsolete-and-malformed"])
def test_h3_provider_only_configuration_does_not_validate_ambient_storage(installation, monkeypatch, ambient):
    config, _ = installation
    monkeypatch.setenv("VIDEO_PROVIDER", "minimax_h3_gateway")
    monkeypatch.setenv("VIDEO_MODEL", "minimax_h3_gateway_catalog_v7")
    monkeypatch.setenv("VIDEO_BASE_URL", "http://100.64.1.2:8090")
    monkeypatch.setenv("VIDEO_MODEL_API_KEY", "fixture-provider-key")
    monkeypatch.setenv("PLOTLOOM_OUTPUTS_DIR", "/normal-do-not-open")
    monkeypatch.setenv("PLOTLOOM_APPLICATION_DATA_DIR", "/normal-do-not-open/application" if ambient == "nested" else "/normal-do-not-open")
    if ambient == "obsolete-and-malformed":
        monkeypatch.setenv("PLOTLOOM_DATA_DIR", "/retired-do-not-open")
        monkeypatch.setenv("PORT", "invalid-port")
        monkeypatch.setenv("TEXT_TEMPERATURE", "not-a-number")
    with compose(replace(config, enable_h3=True)) as runtime:
        assert runtime.app.state.specialists.path.is_relative_to(config.data_root)
        from fastapi.testclient import TestClient
        with TestClient(runtime.app) as client:
            assert client.get("/api/v2/video-backend").json()["enabled"] is True


@pytest.mark.parametrize("failure", ["missing-credential", "invalid-catalog"])
def test_h3_provider_only_configuration_still_fails_closed(installation, monkeypatch, failure):
    config, _ = installation
    monkeypatch.setenv("VIDEO_PROVIDER", "minimax_h3_gateway")
    monkeypatch.setenv("VIDEO_MODEL", "untrusted-catalog" if failure == "invalid-catalog" else "minimax_h3_gateway_catalog_v7")
    monkeypatch.setenv("VIDEO_MODEL_API_KEY", "" if failure == "missing-credential" else "fixture-provider-key")
    monkeypatch.setenv("PLOTLOOM_OUTPUTS_DIR", "/normal-do-not-open")
    monkeypatch.setenv("PLOTLOOM_APPLICATION_DATA_DIR", "/normal-do-not-open")
    with pytest.raises(RuntimeError, match="VIDEO_MODEL_API_KEY|trusted MiniMax"), compose(replace(config, enable_h3=True)):
        pytest.fail("invalid provider configuration must never serve")
