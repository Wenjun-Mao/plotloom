"""Exercise the deployment boundary without sending any native assignment."""

import json
import subprocess
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import codex_client
import pytest
from host_bridge import QueueBridge, handler_for

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
    assert bridge.queue({"thread": task, "message": message}) == {"returncode": 0}
    assert len(commands) == 1
    assert commands[0][0] == [
        str(bridge.executable),
        "queue",
        "--thread",
        task,
        "--message",
        message,
    ]
    assert commands[0][1]["timeout"] < 30


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
