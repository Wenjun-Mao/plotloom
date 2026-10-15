"""Exercise the deployment boundary without sending any native assignment."""

import json
import subprocess
from http.server import ThreadingHTTPServer
from io import BytesIO
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

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


@pytest.fixture
def bridge(tmp_path):
    executable = tmp_path / "codex"
    executable.touch()
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "settings": {
                    "text": {"taskId": TEXT_TASK},
                    "image": {"taskId": IMAGE_TASK},
                }
            }
        )
    )
    return QueueBridge(executable, settings, "test-token" * 8)


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

    assert bridge.exec_readiness() == {"state": "ready"}
    login_command = next(command for command, _options in commands if command[-2:] == ["login", "status"])
    assert login_command == [
        str(executable), "--config", 'cli_auth_credentials_store="file"', "login", "status",
    ]
    login_options = next(options for command, options in commands if command == login_command)
    assert login_options["env"]["CODEX_HOME"] == str(codex_home)
    assert "private login mode" not in json.dumps(bridge.exec_readiness())


def test_client_emits_only_a_validated_profile(tmp_path, monkeypatch, capsys):
    token = tmp_path / "token"
    token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://bridge")
    profile = CodexExecProfile(
        contractVersion="plotloom.codex-exec.v1",
        executableSha256="a" * 64,
        cliVersion="codex-cli 0.162.0-alpha.17.2",
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


@pytest.mark.parametrize("task", [TEXT_TASK, IMAGE_TASK])
def test_bridge_uses_exact_native_command_once_for_either_configured_role(
    bridge, monkeypatch, task
):
    commands = []

    def queue(command, **options):
        commands.append((command, options))
        return subprocess.CompletedProcess(
            command, 0, b"private stdout", b"private stderr"
        )

    monkeypatch.setattr(subprocess, "run", queue)
    message = "Frozen package at /Users/creator/project/package. 中文要求。"
    assert bridge.queue({"thread": task, "message": message}) == {
        "returncode": 0,
        "wakeState": "open_requested",
    }
    assert len(commands) == 2
    assert commands[0][0] == [
        str(bridge.executable),
        "queue",
        "--thread",
        task,
        "--message",
        message,
    ]
    assert commands[0][1]["timeout"] < 30
    assert commands[1][0] == ["/usr/bin/open", f"codex://threads/{task}"]
    assert sum(options["timeout"] for _, options in commands) < 28


@pytest.mark.parametrize("failure", ["nonzero", "timeout", "missing"])
def test_open_failure_preserves_queue_acknowledgement_without_retry(
    bridge, monkeypatch, failure
):
    commands = []

    def run(command, **_options):
        commands.append(command)
        if len(commands) == 1:
            return subprocess.CompletedProcess(command, 0)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 2)
        if failure == "missing":
            raise OSError("private error detail")
        return subprocess.CompletedProcess(command, 1, b"private", b"private")

    monkeypatch.setattr(subprocess, "run", run)
    assert bridge.queue({"thread": IMAGE_TASK, "message": "request"}) == {
        "returncode": 0,
        "wakeState": "open_unconfirmed",
    }
    assert len(commands) == 2


def test_nonzero_queue_acknowledgement_never_opens_or_retries(bridge, monkeypatch):
    commands = []

    def run(command, **_options):
        commands.append(command)
        return subprocess.CompletedProcess(command, 1, b"private", b"private")

    monkeypatch.setattr(subprocess, "run", run)
    assert bridge.queue({"thread": IMAGE_TASK, "message": "request"}) == {
        "returncode": 1
    }
    assert len(commands) == 1


@pytest.mark.parametrize("wake_state", ["open_requested", "open_unconfirmed"])
def test_client_emits_only_bounded_wake_acknowledgement(
    tmp_path, monkeypatch, capsys, wake_state
):
    token = tmp_path / "token"
    token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://bridge")
    monkeypatch.setattr(
        codex_client,
        "urlopen",
        lambda *_args, **_kwargs: BytesIO(
            json.dumps(
                {
                    "returncode": 0,
                    "wakeState": wake_state,
                    "untrusted": "private-output",
                }
            ).encode()
        ),
    )
    assert (
        codex_client.main(
            ["queue", "--thread", IMAGE_TASK, "--message", "private-assignment"]
        )
        == 0
    )
    output = capsys.readouterr()
    assert json.loads(output.out) == {
        "protocol": "plotloom.native-queue.v1",
        "wakeState": wake_state,
    }
    assert not output.err
    assert "private" not in output.out


@pytest.mark.parametrize(
    "result",
    [
        None,
        {},
        {"returncode": True},
        {"returncode": 0},
        {"returncode": 0, "wakeState": {}},
        {"returncode": 0, "wakeState": "untrusted-private-value"},
    ],
)
def test_client_malformed_acknowledgement_fails_closed_without_output_leak(
    tmp_path, monkeypatch, capsys, result
):
    token = tmp_path / "token"
    token.write_text("private-token")
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://bridge")
    attempts = []

    def response(*_args, **_kwargs):
        attempts.append(True)
        return BytesIO(json.dumps(result).encode())

    monkeypatch.setattr(codex_client, "urlopen", response)
    assert (
        codex_client.main(
            ["queue", "--thread", IMAGE_TASK, "--message", "private-assignment"]
        )
        == 1
    )
    output = capsys.readouterr()
    assert not output.out and "private" not in output.err
    assert len(attempts) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"thread": "not-a-uuid", "message": "request"},
        {"thread": 123, "message": "request"},
        {"thread": "00000000-0000-0000-0000-000000000000", "message": "request"},
        {"thread": IMAGE_TASK, "message": ""},
        {"thread": IMAGE_TASK, "message": "request", "command": "exec"},
    ],
)
def test_bridge_rejects_unbound_or_malformed_requests_before_queueing(
    bridge, monkeypatch, payload
):
    monkeypatch.setattr(
        subprocess, "run", lambda *_args, **_kwargs: pytest.fail("must not queue")
    )
    with pytest.raises((ValueError, TypeError)):
        bridge.queue(payload)


def test_bridge_and_client_never_retry_an_ambiguous_timeout(
    bridge, monkeypatch, tmp_path
):
    attempts = []

    def timeout(command, **_kwargs):
        attempts.append(command)
        raise subprocess.TimeoutExpired(command, 25)

    monkeypatch.setattr(subprocess, "run", timeout)
    assert bridge.queue({"thread": IMAGE_TASK, "message": "request"}) == {
        "returncode": 1
    }
    assert len(attempts) == 1
    token = tmp_path / "token"
    token.write_text(bridge.token)
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE", str(token))
    monkeypatch.setenv("PLOTLOOM_CODEX_BRIDGE_URL", "http://127.0.0.1:1")
    requests = []

    def lost_ack(request, **_kwargs):
        requests.append(request)
        raise URLError("lost acknowledgement")

    monkeypatch.setattr(codex_client, "urlopen", lost_ack)
    assert (
        codex_client.main(["queue", "--thread", IMAGE_TASK, "--message", "request"])
        == 1
    )
    assert len(requests) == 1


def test_http_authentication_and_health_do_not_queue(bridge, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("health/auth must not queue"),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(bridge))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        with pytest.raises(HTTPError) as failure:
            urlopen(Request(url + "/queue", data=b"{}"), timeout=3)
        assert failure.value.code == 401
        with urlopen(
            Request(
                url + "/healthz", headers={"Authorization": f"Bearer {bridge.token}"}
            ),
            timeout=3,
        ) as response:
            assert json.load(response) == {"status": "ok"}
        with pytest.raises(HTTPError) as failure:
            urlopen(
                Request(
                    url + "/queue",
                    data=json.dumps({"thread": 42, "message": "request"}).encode(),
                    headers={"Authorization": f"Bearer {bridge.token}"},
                ),
                timeout=3,
            )
        assert failure.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def _spawn_intent_attempt():
    return CodexExecAttempt(
        attemptId=uuid4(),
        runId=uuid4(),
        projectId=uuid4(),
        jobId="ch_" + "a" * 24,
        operationKey="outline",
        domain="text",
        requestHash="a" * 64,
        packageHash="b" * 64,
        profileHash="c" * 64,
        reservedImageOutputs=0,
        state="spawn_intent",
    )


@pytest.mark.parametrize("control", ["cancel", "suspend", "resume"])
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

    setattr(Supervisor, control, Supervisor.cancel)
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
