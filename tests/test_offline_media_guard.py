"""Even a swallowed dispatch failure invalidates offline validation."""
import pytest
import requests

from plotloom.codex_exec_host_client import CodexExecHostClient
from tests.offline_media_fixtures import block_live_media


@pytest.mark.parametrize("boundary", ["HTTP", "native Codex host"])
def test_live_dispatch_fails_immediately_and_remains_a_failure_if_caught(monkeypatch, boundary):
    guard = block_live_media(monkeypatch)
    with pytest.raises(AssertionError, match="attempted live"):
        if boundary == "HTTP":
            requests.post("http://127.0.0.1:9/never-sent", json={"prompt": "private"})
        else:
            CodexExecHostClient._codex_exec_request(None, "admit", "private")
    assert guard.attempts == [boundary]
    with pytest.raises(AssertionError, match="attempted live dispatch"):
        guard.assert_clean()
