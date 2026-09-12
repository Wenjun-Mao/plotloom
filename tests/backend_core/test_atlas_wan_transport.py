from __future__ import annotations

import pytest

from plotloom.atlas_wan_transport import AtlasCloudWanTransport
from plotloom.video_ingestion import VideoIngestionError


class _Response:
    status = 200
    headers = {"Content-Length": "0"}
    released = False
    def read(self, _size: int) -> bytes: return b""
    def release_conn(self) -> None: self.released = True


def test_download_pins_validated_ip_uses_sni_and_has_no_ambient_credentials(monkeypatch) -> None:
    captured: dict[str, object] = {}
    response = _Response()
    class Pool:
        def __init__(self, host, **kwargs): captured.update(host=host, **kwargs)
        def urlopen(self, method, path, **kwargs): captured.update(method=method, path=path, headers=kwargs["headers"]); return response
        def close(self): captured["closed"] = True
    monkeypatch.setattr("plotloom.atlas_wan_transport.socket.getaddrinfo", lambda *_args, **_kwargs: [(None, None, None, None, ("8.8.8.8", 443))])
    monkeypatch.setattr("plotloom.atlas_wan_transport.HTTPSConnectionPool", Pool)
    transport = AtlasCloudWanTransport("secret", timeout_seconds=2)
    assert transport._session.trust_env is False  # noqa: SLF001 - transport security contract
    assert transport.download("https://cdn.example/clip.mp4?token=unpersisted") == b""
    assert captured["host"] == "8.8.8.8"
    assert captured["assert_hostname"] == "cdn.example" and captured["server_hostname"] == "cdn.example"
    assert captured["headers"] == {"Host": "cdn.example"}
    assert response.released and captured["closed"]


def test_download_enforces_total_deadline_and_closes_response(monkeypatch) -> None:
    response = _Response()
    response.headers = {"Content-Length": "1"}
    class Pool:
        def __init__(self, *_args, **_kwargs): pass
        def urlopen(self, *_args, **_kwargs): return response
        def close(self): pass
    clock = iter((0.0, 3.0))
    monkeypatch.setattr("plotloom.atlas_wan_transport.socket.getaddrinfo", lambda *_args, **_kwargs: [(None, None, None, None, ("8.8.8.8", 443))])
    monkeypatch.setattr("plotloom.atlas_wan_transport.HTTPSConnectionPool", Pool)
    monkeypatch.setattr("plotloom.atlas_wan_transport.monotonic", lambda: next(clock))
    with pytest.raises(VideoIngestionError, match="deadline"):
        AtlasCloudWanTransport("secret", timeout_seconds=1).download("https://cdn.example/clip.mp4")
    assert response.released
