from __future__ import annotations

import pytest

from plotloom.video_backends.minimax_h3 import H3_PROFILES, MiniMaxH3GatewayAdapter, MiniMaxH3GatewayTransport
from plotloom.video_backends.minimax_h3.adapter import H3_PROFILE_CONTRACT_VERSION
from plotloom.video_ingestion import ObservedVideo
from plotloom.video_provider import VideoOutputContractError, VideoProviderError, WanDispatchError


_JOB_ID = "h3_0123456789abcdef0123456789abcdef"
_PROFILE = "minimax_h3_fp8_turbo4_portrait_576x1024_v1"


class _Response:
    def __init__(self, status_code: int, payload: object | None = None, *, content: bytes = b"", headers: dict[str, str] | None = None) -> None:
        self.status_code, self._payload, self._content, self.headers = status_code, payload, content, headers or {}
    def json(self) -> object:
        if isinstance(self._payload, Exception): raise self._payload
        return self._payload
    def iter_content(self, _: int) -> list[bytes]: return [self._content]
    def close(self) -> None: return None


def _job(status: str, output_ready: bool) -> dict[str, object]:
    return {
        "id": _JOB_ID, "status": status, "inputMode": "image", "profileId": _PROFILE,
        "aspectPolicy": "reject_mismatch", "seed": 1, "requestedDurationSeconds": 5,
        "frameCount": 124, "actualDurationSeconds": 124 / 24,
        "generationSubmittedAt": None, "generationCompletedAt": None, "generationElapsedMs": None,
        "error": None, "outputReady": output_ready,
    }


class _GatewaySession:
    def __init__(self) -> None: self.trust_env = True; self.calls: list[tuple[str, str, dict]] = []
    def request(self, method: str, url: str, **kwargs: object) -> _Response:
        self.calls.append((method, url, dict(kwargs)))
        if url.endswith("/health"):
            return _Response(200, {"status": "ok", "profileContractVersion": H3_PROFILE_CONTRACT_VERSION, "profiles": [profile.public_descriptor() for profile in H3_PROFILES], "inputModes": ["image", "text"], "queuedJobs": 0, "activeDispatches": 0, "dispatchConcurrency": 1})
        if url.endswith("/v1/video-jobs/from-image"): return _Response(202, _job("queued", False))
        if url.endswith(f"/v1/video-jobs/{_JOB_ID}"): return _Response(200, _job("succeeded", True))
        raise AssertionError(url)
    def get(self, url: str, **kwargs: object) -> _Response:
        self.calls.append(("GET", url, dict(kwargs)))
        assert url.endswith(f"/v1/video-jobs/{_JOB_ID}/output")
        return _Response(200, content=b"mp4", headers={"Content-Type": "video/mp4", "Content-Length": "3"})


def test_h3_transport_uses_only_the_direct_multipart_gateway_envelope() -> None:
    session = _GatewaySession(); transport = MiniMaxH3GatewayTransport("test-key", base_url="http://100.64.1.2:8090", session=session)
    transport.preflight()
    submitted = transport.submit_image(b"png", mime_type="image/png", payload={"prompt": "one line", "profileId": _PROFILE, "aspectPolicy": "reject_mismatch", "seed": 1, "durationSeconds": 5})
    polled = transport.poll(_JOB_ID); media = transport.download(_JOB_ID)
    assert transport._session.trust_env is False
    assert submitted["id"] == _JOB_ID and polled["outputReady"] is True and media == b"mp4"
    assert MiniMaxH3GatewayAdapter.completed_output(submitted, expected_profile_id=_PROFILE) is None
    assert all(call[2].get("allow_redirects") is False for call in session.calls)
    assert session.calls[1][1].endswith("/v1/video-jobs/from-image")
    assert session.calls[1][2]["data"]["durationSeconds"] == "5"
    assert "idempotencyKey" not in session.calls[1][2]["data"]


def test_h3_transport_rejects_public_or_malformed_gateway_roots() -> None:
    for base_url in ("https://example.com", "http://8.8.8.8", "http://100.64.1.2:8090/not-root", "https://user:pass@100.64.1.2:8090"):
        with pytest.raises(ValueError): MiniMaxH3GatewayTransport("test-key", base_url=base_url)


def test_h3_adapter_direct_image_contract_requires_a_frozen_profile() -> None:
    adapter = MiniMaxH3GatewayAdapter()
    with pytest.raises(VideoProviderError, match="requires an explicit profile"):
        adapter.compile_image(prompt="one line", duration=5, resolution="576x1024", audio=True, aspect_policy="reject_mismatch", seed=1, profile_id=None)
    with pytest.raises(VideoProviderError, match="requires a frozen profile"):
        adapter.prediction_id(_job("queued", False), expected_profile_id=None)


def test_h3_adapter_requires_explicit_and_exclusive_center_crop_consent() -> None:
    adapter = MiniMaxH3GatewayAdapter()
    with pytest.raises(VideoProviderError, match="allowCenterCrop"):
        adapter.production_contract(
            requested_seconds=5, resolution="576x1024", audio=True,
            aspect_policy="cover_center_crop", allow_letterbox=False,
            allow_center_crop=False, seed=7, profile_id=_PROFILE,
        )
    contract = adapter.production_contract(
        requested_seconds=5, resolution="576x1024", audio=True,
        aspect_policy="cover_center_crop", allow_letterbox=False,
        allow_center_crop=True, seed=7, profile_id=_PROFILE,
    )
    assert contract.request_snapshot() == {
        "durationSeconds": 5, "resolution": "576x1024", "audio": True,
        "aspectPolicy": "cover_center_crop", "seed": 7, "profileId": _PROFILE,
        "profileVersion": 1, "width": 576, "height": 1024,
        "allowLetterbox": False, "allowCenterCrop": True,
    }
    with pytest.raises(VideoProviderError, match="mutually exclusive"):
        adapter.production_contract(
            requested_seconds=5, resolution="576x1024", audio=True,
            aspect_policy="cover_center_crop", allow_letterbox=True,
            allow_center_crop=True, seed=7, profile_id=_PROFILE,
        )


def test_h3_adapter_rejects_a_gateway_response_that_changes_the_frozen_crop_mode() -> None:
    with pytest.raises(VideoProviderError, match="aspect policy"):
        MiniMaxH3GatewayAdapter.prediction_id(
            _job("queued", False), expected_profile_id=_PROFILE,
            expected_aspect_policy="cover_center_crop",
        )


def test_h3_adapter_reports_retained_output_expiry() -> None:
    with pytest.raises(VideoOutputContractError, match="h3_gateway_output_expired"):
        MiniMaxH3GatewayAdapter.completed_output(_job("succeeded", False), expected_profile_id=_PROFILE)


def test_h3_adapter_rejects_playable_output_outside_the_frozen_profile() -> None:
    """H.264/AAC alone cannot make a wrong H3 geometry publishable."""

    with pytest.raises(VideoOutputContractError, match="h3_output_profile_mismatch"):
        MiniMaxH3GatewayAdapter().validate_observed_output(
            ObservedVideo(
                duration_seconds=124 / 24,
                width=1280,
                height=720,
                video_codec="h264",
                audio_codec="aac",
                frame_rate=24,
                frame_count=124,
            ),
            profile_id=_PROFILE,
        )


def test_h3_transport_rejects_unrecognised_direct_response_shape() -> None:
    class _Malformed(_GatewaySession):
        def request(self, method: str, url: str, **kwargs: object) -> _Response:
            if url.endswith("/v1/video-jobs/from-image"): return _Response(202, {"id": _JOB_ID, "status": "submitted"})
            return super().request(method, url, **kwargs)
    transport = MiniMaxH3GatewayTransport("test-key", base_url="http://100.64.1.2:8090", session=_Malformed())
    with pytest.raises(WanDispatchError):
        transport.submit_image(b"png", mime_type="image/png", payload={"prompt": "x", "profileId": _PROFILE, "aspectPolicy": "reject_mismatch", "seed": 1, "durationSeconds": 5})
