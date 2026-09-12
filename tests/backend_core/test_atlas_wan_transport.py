from __future__ import annotations

import pytest
import requests

from plotloom.atlas_wan_transport import AtlasCloudWanTransport
from plotloom.video_ingestion import VideoIngestionError
from plotloom.video_provider import WanDispatchDiagnostic, WanDispatchError


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


@pytest.mark.parametrize(
    ("method", "phase", "status"),
    [("upload", "upload", 401), ("submit", "submit", 429)],
)
def test_dispatch_http_rejections_preserve_only_allowlisted_evidence(monkeypatch, method, phase, status) -> None:
    class Response:
        status_code = status
        text = "credential=do-not-persist"

        def json(self):
            return {"detail": self.text}

    transport = AtlasCloudWanTransport("top-secret-key")
    monkeypatch.setattr(transport._session, "request", lambda *_args, **_kwargs: Response())
    with pytest.raises(WanDispatchError) as raised:
        if method == "upload":
            transport.upload(b"image", mime_type="image/png")
        else:
            transport.submit({"prompt": "never expose this prompt"})
    assert raised.value.diagnostic.phase == phase
    assert raised.value.diagnostic.code == "http_rejected"
    assert raised.value.diagnostic.status_code == status
    assert str(raised.value) == f"dispatch_{phase}_http_rejected_status_{status}"
    assert "secret" not in str(raised.value) and "credential" not in str(raised.value)


def test_dispatch_transport_uncertainty_and_bad_upload_envelope_are_secret_safe(monkeypatch) -> None:
    transport = AtlasCloudWanTransport("top-secret-key")
    monkeypatch.setattr(
        transport._session,
        "request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(requests.ConnectionError("https://signed.example/?token=secret")),
    )
    with pytest.raises(WanDispatchError) as unavailable:
        transport.upload(b"image", mime_type="image/png")
    assert unavailable.value.diagnostic.code == "transport_unavailable"
    assert unavailable.value.diagnostic.status_code is None
    assert "signed" not in str(unavailable.value) and "secret" not in str(unavailable.value)

    class Response:
        status_code = 200

        def json(self):
            return {"url": "http://provider.example/not-https?token=secret"}

    monkeypatch.setattr(transport._session, "request", lambda *_args, **_kwargs: Response())
    with pytest.raises(WanDispatchError) as malformed:
        transport.upload(b"image", mime_type="image/png")
    assert malformed.value.diagnostic.code == "invalid_upload_url"
    assert str(malformed.value) == "dispatch_upload_invalid_upload_url"
    assert "secret" not in str(malformed.value)


def test_upload_uses_documented_multipart_field_and_top_level_url(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"url": "https://uploads.atlas.example/keyframe.png"}

    transport = AtlasCloudWanTransport("top-secret-key")
    monkeypatch.setattr(
        transport._session,
        "request",
        lambda method, url, **kwargs: (captured.update(method=method, url=url, **kwargs) or Response()),
    )

    assert transport.upload(b"approved-image", mime_type="image/png") == "https://uploads.atlas.example/keyframe.png"
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.atlascloud.ai/api/v1/model/uploadMedia"
    assert captured["files"] == {"file": ("approved-keyframe", b"approved-image", "image/png")}
    assert "json" not in captured


@pytest.mark.parametrize(
    "payload",
    [
        {"data": {"url": "https://signed.example/?token=secret"}},
        {"data": {"download_url": "https://signed.example/?token=secret"}},
        {"error": {"message": "upload rejected: token=secret"}},
    ],
)
def test_upload_rejects_undocumented_nested_urls_and_error_envelopes(monkeypatch, payload) -> None:
    class Response:
        status_code = 200

        def json(self):
            return payload

    transport = AtlasCloudWanTransport("top-secret-key")
    monkeypatch.setattr(transport._session, "request", lambda *_args, **_kwargs: Response())
    with pytest.raises(WanDispatchError) as rejected:
        transport.upload(b"image", mime_type="image/png")
    assert rejected.value.diagnostic.code == "invalid_upload_url"
    assert "signed" not in str(rejected.value) and "secret" not in str(rejected.value)


def test_upload_rejects_non_object_json_envelopes(monkeypatch) -> None:
    class Response:
        status_code = 200

        @staticmethod
        def json() -> list[str]:
            return ["https://signed.example/?token=secret"]

    transport = AtlasCloudWanTransport("top-secret-key")
    monkeypatch.setattr(transport._session, "request", lambda *_args, **_kwargs: Response())
    with pytest.raises(WanDispatchError) as rejected:
        transport.upload(b"image", mime_type="image/png")
    assert rejected.value.diagnostic.code == "invalid_envelope"
    assert "signed" not in str(rejected.value) and "secret" not in str(rejected.value)


@pytest.mark.parametrize(
    ("phase", "code", "status"),
    [
        ("https://signed.example/?token=secret", "http_rejected", 401),
        ("upload", "provider detail: secret", 401),
        ("upload", "http_rejected", True),
        ("upload", "http_rejected", 99),
    ],
)
def test_diagnostic_allowlist_rejects_untrusted_runtime_values(phase, code, status) -> None:
    with pytest.raises(ValueError):
        WanDispatchDiagnostic(phase, code, status)  # type: ignore[arg-type]
