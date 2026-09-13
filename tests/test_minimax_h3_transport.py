from __future__ import annotations

import pytest

from plotloom.minimax_h3_transport import MiniMaxH3GatewayTransport
from plotloom.video_provider import WanDispatchError


_ASSET_ID = "asset_0123456789abcdef0123456789abcdef"
_JOB_ID = "h3_0123456789abcdef0123456789abcdef"


class _Response:
    def __init__(self, status_code: int, payload: object | None = None, *, content: bytes = b"", headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload
        self._content = content
        self.headers = headers or {}
        self.closed = False

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def iter_content(self, _: int) -> list[bytes]:
        return [self._content]

    def close(self) -> None:
        self.closed = True


class _GatewaySession:
    def __init__(self) -> None:
        self.trust_env = True
        self.calls: list[tuple[str, str, dict]] = []

    def request(self, method: str, url: str, **kwargs: object) -> _Response:
        self.calls.append((method, url, dict(kwargs)))
        if url.endswith("/health"):
            return _Response(200, {"status": "ok", "profiles": ["minimax_h3_fp8_turbo4_480p"], "maxQueueDepth": 2})
        if url.endswith("/v1/assets"):
            return _Response(200, {"assetId": _ASSET_ID, "mimeType": "image/png", "width": 864, "height": 480, "sha256": "a" * 64})
        if url.endswith("/v1/video-jobs"):
            return _Response(202, _job("submitted", False))
        if url.endswith(f"/v1/video-jobs/{_JOB_ID}"):
            return _Response(200, _job("succeeded", True))
        raise AssertionError(url)

    def get(self, url: str, **kwargs: object) -> _Response:
        self.calls.append(("GET", url, dict(kwargs)))
        assert url.endswith(f"/v1/video-jobs/{_JOB_ID}/output")
        return _Response(200, content=b"mp4", headers={"Content-Type": "video/mp4", "Content-Length": "3"})


def _job(status: str, output_ready: bool) -> dict[str, object]:
    return {
        "id": _JOB_ID,
        "status": status,
        "profileId": "minimax_h3_fp8_turbo4_480p",
        "aspectPolicy": "cover_center_crop",
        "error": None,
        "outputReady": output_ready,
    }


def test_h3_transport_uses_only_the_fixed_gateway_envelopes() -> None:
    session = _GatewaySession()
    transport = MiniMaxH3GatewayTransport("test-key", base_url="http://100.64.1.2:8090", session=session)

    transport.preflight()
    asset = transport.upload(b"png", mime_type="image/png")
    submitted = transport.submit({"assetId": asset, "prompt": "one line", "profileId": "minimax_h3_fp8_turbo4_480p", "aspectPolicy": "cover_center_crop", "seed": 1})
    polled = transport.poll(_JOB_ID)
    media = transport.download(_JOB_ID)

    assert transport._session.trust_env is False
    assert submitted["id"] == _JOB_ID and polled["outputReady"] is True
    assert media == b"mp4"
    assert all(call[2].get("allow_redirects") is False for call in session.calls)
    assert session.calls[0][2]["headers"] == {}
    assert session.calls[1][2]["headers"] == {"Authorization": "Bearer test-key"}


def test_h3_transport_rejects_public_and_malformed_gateway_roots() -> None:
    for base_url in ("https://example.com", "http://8.8.8.8", "http://100.64.1.2:8090/not-root", "https://user:pass@100.64.1.2:8090"):
        with pytest.raises(ValueError):
            MiniMaxH3GatewayTransport("test-key", base_url=base_url)


def test_h3_transport_rejects_unrecognised_response_shape_before_job_id_use() -> None:
    class _Malformed(_GatewaySession):
        def request(self, method: str, url: str, **kwargs: object) -> _Response:
            if url.endswith("/v1/video-jobs"):
                return _Response(202, {"id": _JOB_ID, "status": "submitted"})
            return super().request(method, url, **kwargs)

    transport = MiniMaxH3GatewayTransport("test-key", base_url="http://100.64.1.2:8090", session=_Malformed())
    with pytest.raises(WanDispatchError):
        transport.submit({"assetId": _ASSET_ID})
