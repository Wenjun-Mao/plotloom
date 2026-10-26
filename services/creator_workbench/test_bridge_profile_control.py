"""Exercise the deployment boundary without sending any native assignment."""

import json
import subprocess
from http.server import ThreadingHTTPServer
from io import BytesIO
from threading import Thread
from urllib.request import Request, urlopen

import codex_client
import pytest
from host_bridge import QueueBridge, handler_for

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecHostStatus,
    CodexExecProfile,
    transition_exec_attempt,
)

TEXT_TASK = "01a0dfa6-40ae-7cf2-82eb-edcde7a8fcc0"
IMAGE_TASK = "01a0c506-84d5-7161-8ae0-2ae914e5d81a"


from bridge_test_support import _spawn_intent_attempt


def test_exec_profile_is_host_observed_and_never_uses_project_or_user_config(
    tmp_path, monkeypatch, codex_exec_test_source
):
    executable = tmp_path / "codex"
    executable.write_bytes(b"qualified CLI executable")
    executable.chmod(0o700)
    settings = tmp_path / "settings.json"
    source_root = codex_exec_test_source
    (tmp_path / "outputs").mkdir()
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir(mode=0o700)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_options: subprocess.CompletedProcess(
            command, 0, b"codex-cli 0.162.0-alpha.17.2\n", b""
        ),
    )
    bridge = QueueBridge(
        executable,
        settings,
        "test-token" * 8,
        source_root=source_root,
        outputs_root=tmp_path / "outputs",
        private_root=tmp_path / "private",
    )
    profile = bridge.exec_profile()
    assert profile["backend"] == "codex_exec"
    assert profile["cliVersion"] == "codex-cli 0.162.0-alpha.17.2"
    assert profile["model"] == "gpt-6.1-sol"
    assert profile["contractVersion"] == "plotloom.codex-exec.v8"
    assert profile["authenticationStore"] == "file"
    assert profile["permissionProfile"] == "plotloom_autopilot_delivery_v5"
    assert profile["toolProfile"] == "plotloom_autopilot_tools_v4"
    assert "sandboxProfile" not in profile
    assert profile["maxProcesses"] == 4
    assert profile["maxTextProcesses"] == profile["maxImageProcesses"] == 2
    assert profile["maxQueuedJobs"] == 4
    assert profile["apiFallback"] is False
    assert "token" not in json.dumps(profile).casefold()



def test_readiness_uses_existing_file_store_without_exposing_cli_output(tmp_path, monkeypatch, codex_exec_test_source):
    executable = tmp_path / "codex"
    executable.touch()
    source_root = codex_exec_test_source
    outputs_root = tmp_path / "outputs"
    outputs_root.mkdir()
    private_root = tmp_path / "private"
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir(mode=0o700)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    commands = []

    def login_status(command, **options):
        commands.append((command, options))
        return subprocess.CompletedProcess(command, 0, b"private login mode", b"")

    monkeypatch.setattr(subprocess, "run", login_status)
    bridge = QueueBridge(
        executable,
        tmp_path / "settings.json",
        "test-token" * 8,
        source_root=source_root,
        outputs_root=outputs_root,
        private_root=private_root,
    )

    readiness = bridge.exec_readiness()
    assert readiness["state"] == "ready"
    assert readiness["localCapacity"]["limits"]["maxImageProcesses"] == 2
    assert readiness["localCapacity"]["heldImage"] == 0 and not readiness["localCapacity"]["imageLaneBlocked"]
    login_command = next(command for command, _options in commands if command[-2:] == ["login", "status"])
    assert login_command == [
        str(executable), "--config", 'cli_auth_credentials_store="file"', "login", "status",
    ]
    login_options = next(options for command, options in commands if command == login_command)
    assert login_options["env"]["CODEX_HOME"] == str(codex_home)
    assert "private login mode" not in json.dumps(bridge.exec_readiness())



@pytest.mark.parametrize("version", ["codex-cli 0.163.0-alpha.10.2", None])
def test_client_emits_only_a_validated_profile(tmp_path, monkeypatch, capsys, version):
    token = tmp_path / "token"
    token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://bridge")
    profile = CodexExecProfile(
        contractVersion="plotloom.codex-exec.v1",
        executableSha256="a" * 64,
        cliVersion=version,
        model="gpt-6.1-sol",
        reasoningEffort="medium",
        capabilities=("exec_json_events_v1", "session_rollout_v1", "image_gen_event_v1", "delivery_directory_write_v1"),
        instructionHash="b" * 64,
        validatorHash="c" * 64,
        sandboxProfile="read_only_with_delivery_write",
        maxRuntimeSeconds=1800,
        maxEventBytes=50_000_000,
        maxOutputBytes=500_000_000,
        maxImageOutputs=4,
    )
    monkeypatch.setattr(
        codex_client,
        "urlopen",
        lambda *_args, **_kwargs: BytesIO(
            json.dumps(profile.model_dump(mode="json", by_alias=True)).encode()
        ),
    )
    assert codex_client.main(["exec-profile"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == profile.model_dump(mode="json", by_alias=True)
    assert not output.err
    assert "private" not in output.out



@pytest.mark.parametrize("state", ["ready", "not_authenticated", "unavailable"])
def test_client_emits_only_a_validated_readiness_state(tmp_path, monkeypatch, capsys, state):
    token = tmp_path / "token"
    token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://bridge")
    monkeypatch.setattr(
        codex_client,
        "urlopen",
        lambda *_args, **_kwargs: BytesIO(json.dumps({"state": state}).encode()),
    )

    assert codex_client.main(["exec-readiness"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == {"state": state}
    assert not output.err and "private" not in output.out



def test_client_rejects_unrecognized_readiness_fields(tmp_path, monkeypatch, capsys):
    token = tmp_path / "token"
    token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://bridge")
    monkeypatch.setattr(
        codex_client,
        "urlopen",
        lambda *_args, **_kwargs: BytesIO(b'{"state":"ready","secret":"private"}'),
    )

    assert codex_client.main(["exec-readiness"]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "invalid" in output.err and "private" not in output.err



@pytest.mark.parametrize("control", ["cancel", "suspend", "resume", "recover-no-remote-dispatch"])
def test_control_endpoint_passes_the_exact_attempt_snapshot_to_the_supervisor(bridge, monkeypatch, control):
    attempt = _spawn_intent_attempt()
    cancelled = transition_exec_attempt(
        attempt,
        state="settled",
        terminal_result="not_started",
        remote_tool_state="not_applicable",
        evidence_hash="d" * 64,
    )
    observed = []

    class Supervisor:
        def cancel(self, snapshot):
            observed.append(CodexExecAttempt.model_validate(snapshot))
            return CodexExecHostStatus(state="settled", attempt=cancelled)

    setattr(Supervisor, control.replace("-", "_"), Supervisor.cancel)
    bridge.exec_supervisor = lambda: Supervisor()
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(bridge))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = json.dumps({"attempt": attempt.model_dump(mode="json", by_alias=True)}).encode()
        request = Request(
            f"http://127.0.0.1:{server.server_port}/exec-{control}/{attempt.attempt_id}",
            data=payload,
            headers={
                "Authorization": f"Bearer {bridge.token}",
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=3) as response:
            result = CodexExecHostStatus.model_validate_json(response.read())
        assert result.state == "settled"
        assert observed == [attempt]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)



@pytest.mark.parametrize("control", ["cancel", "suspend", "resume"])
def test_client_sends_frozen_attempt_for_control_and_never_retries(tmp_path, monkeypatch, capsys, control):
    attempt = _spawn_intent_attempt()
    cancelled = transition_exec_attempt(
        attempt,
        state="settled",
        terminal_result="not_started",
        remote_tool_state="not_applicable",
        evidence_hash="d" * 64,
    )
    token = tmp_path / "token"
    token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://bridge")
    requests = []

    def response(request, **_kwargs):
        requests.append(request)
        assert request.full_url.endswith(f"/exec-{control}/{attempt.attempt_id}")
        assert request.get_method() == "POST"
        assert json.loads(request.data) == {
            "attempt": attempt.model_dump(mode="json", by_alias=True)
        }
        return BytesIO(json.dumps(CodexExecHostStatus(
            state="settled", attempt=cancelled
        ).model_dump(mode="json", by_alias=True)).encode())

    monkeypatch.setattr(codex_client, "urlopen", response)
    assert codex_client.main([
        f"exec-{control}",
        "--attempt-json",
        attempt.model_dump_json(by_alias=True),
    ]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["state"] == "settled"
    assert len(requests) == 1
