"""Authenticated one-shot operator transport; no real slot or provider changes."""
import json
import subprocess
from http.server import ThreadingHTTPServer
from io import BytesIO
from threading import Thread
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import codex_client
import pytest
from host_bridge import QueueBridge, handler_for

from plotloom.codex_exec_capacity_contracts import (
    CapacityRetirementPreview,
    CapacityRetirementRequest,
)


@pytest.mark.parametrize("auth_home", ["missing", "symlink", "forbidden", "runtime_unavailable"])
def test_unavailable_readiness_preserves_typed_diagnostic_without_constructing_supervisor(
    tmp_path, monkeypatch, codex_exec_test_source, auth_home,
):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    selected = tmp_path / "auth"
    if auth_home == "symlink":
        target = tmp_path / "auth-target"
        target.mkdir()
        selected.symlink_to(target, target_is_directory=True)
    elif auth_home == "forbidden":
        selected = outputs / "auth"
        selected.mkdir()
    elif auth_home == "runtime_unavailable":
        selected.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(selected))
    def unavailable(*_args, **_kwargs):
        raise OSError("private runtime details")
    monkeypatch.setattr(subprocess, "run", unavailable)
    bridge = QueueBridge(tmp_path / "codex", tmp_path / "settings.json", "private-token",
        source_root=codex_exec_test_source, outputs_root=outputs, private_root=tmp_path / "private")
    def forbidden_supervisor():
        pytest.fail("unavailable authentication/runtime must not construct a supervisor")
    monkeypatch.setattr(bridge, "exec_supervisor", forbidden_supervisor)
    assert bridge.exec_readiness() == {"state": "unavailable"}


def packet():
    return CapacityRetirementRequest(project_id=uuid4(), attempt_id=uuid4(),
        expected_preview_hash="a" * 64, reason="Explicit local-only capacity retirement")


def preview(request):
    return CapacityRetirementPreview(project_id=request.project_id, attempt_id=request.attempt_id,
        preview_hash="a" * 64, eligible=True, blockers=[], local_capacity_state="held",
        image_budget_state="reserved", reserved_image_outputs=1)


@pytest.mark.parametrize("command", ["exec-capacity-retirement-preview", "exec-capacity-retire"])
def test_authenticated_bridge_routes_one_exact_typed_packet_and_refuses_missing_auth(tmp_path, monkeypatch, command):
    bridge = QueueBridge(tmp_path / "codex", tmp_path / "settings.json", "private-token")
    request = packet()
    observed = []
    def invoke(name, raw):
        parsed = CapacityRetirementRequest.model_validate(raw)
        observed.append((name, parsed))
        return preview(parsed)
    monkeypatch.setattr(bridge, "exec_supervisor", lambda: SimpleNamespace(
        capacity_retirement_preview=lambda raw: invoke("preview", raw),
        retire_local_capacity=lambda raw: invoke("retire", raw)))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(bridge))
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    url = f"http://127.0.0.1:{server.server_port}/{command}"
    body = request.model_dump_json(by_alias=True).encode()
    try:
        with pytest.raises(HTTPError) as denied:
            urlopen(Request(url, data=body, method="POST"), timeout=3)
        assert denied.value.code == 401 and not observed
        call = Request(url, data=body, method="POST", headers={"Authorization": "Bearer private-token", "Content-Type": "application/json"})
        with urlopen(call, timeout=3) as response:
            result = CapacityRetirementPreview.model_validate_json(response.read())
        assert result == preview(request)
        assert observed == [("preview" if command.endswith("preview") else "retire", request)]
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


@pytest.mark.parametrize("command", ["exec-capacity-retirement-preview", "exec-capacity-retire"])
def test_operator_cli_validates_local_and_remote_states_and_never_retries_lost_ack(tmp_path, monkeypatch, capsys, command):
    request = packet()
    token = tmp_path / "token"; token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://bridge")
    calls = []
    def respond(call, **_kwargs):
        calls.append(call)
        assert call.full_url.endswith("/" + command) and call.get_method() == "POST"
        assert json.loads(call.data) == request.model_dump(mode="json", by_alias=True)
        return BytesIO(preview(request).model_dump_json(by_alias=True).encode())
    monkeypatch.setattr(codex_client, "urlopen", respond)
    assert codex_client.main([command, "--packet-json", request.model_dump_json(by_alias=True)]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["remoteOutcome"] == "preserved_unknown"
    assert json.loads(output.out)["localCapacityState"] == "held" and "private-token" not in output.out
    def lost_ack(call, **_kwargs):
        calls.append(call)
        raise TimeoutError("response lost after possible commit")
    monkeypatch.setattr(codex_client, "urlopen", lost_ack)
    assert codex_client.main([command, "--packet-json", request.model_dump_json(by_alias=True)]) == 1
    assert len(calls) == 2  # One call per explicit invocation, no hidden retry.
