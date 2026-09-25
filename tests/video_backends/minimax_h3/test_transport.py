from __future__ import annotations

import pytest
from pydantic import ValidationError

from plotloom.video_backends.minimax_h3 import H3_PROFILES, MiniMaxH3GatewayAdapter, MiniMaxH3GatewayTransport
from plotloom.video_backends.minimax_h3.adapter import H3_PROFILE_CONTRACT_VERSION, H3_QUALIFIED_DURATION_FRAMES
from plotloom.video_ingestion import ObservedVideo
from plotloom.video_contracts import VideoJobRequest
from plotloom.video_provider import VideoOutputContractError, VideoProviderError, WanDispatchError


_JOB_ID = "h3_0123456789abcdef0123456789abcdef"
_PROFILE = next(profile.profile_id for profile in H3_PROFILES if profile.quality == 1)
_QUALITY_8_PROFILE = next(profile.profile_id for profile in H3_PROFILES if profile.quality == 8)


class _Response:
    def __init__(self, status_code: int, payload: object | None = None, *, content: bytes = b"", headers: dict[str, str] | None = None) -> None:
        self.status_code, self._payload, self._content, self.headers = status_code, payload, content, headers or {}
    def json(self) -> object:
        if isinstance(self._payload, Exception): raise self._payload
        return self._payload
    def iter_content(self, _: int) -> list[bytes]: return [self._content]
    def close(self) -> None: return None


def _job(status: str, output_ready: bool, *, duration: int = 5, frame_count: int = 124) -> dict[str, object]:
    return {
        "id": _JOB_ID, "status": status, "inputMode": "image", "quality": 1,
        "resolution": "576x1024",
        "aspectPolicy": "reject_mismatch", "seed": 1, "requestedDurationSeconds": duration,
        "frameCount": frame_count, "actualDurationSeconds": frame_count / 24,
        "generationSubmittedAt": None, "generationCompletedAt": None, "generationElapsedMs": None,
        "error": None, "outputReady": output_ready,
    }


class _GatewaySession:
    def __init__(self) -> None: self.trust_env = True; self.calls: list[tuple[str, str, dict]] = []
    def request(self, method: str, url: str, **kwargs: object) -> _Response:
        self.calls.append((method, url, dict(kwargs)))
        if url.endswith("/health"):
            return _Response(200, {"status": "ok", "generationContractVersion": H3_PROFILE_CONTRACT_VERSION, "defaultQuality": 1, "qualities": [1, 2, 3, 8], "resolutions": ["832x480", "960x544", "1280x704", "576x1024", "608x1088", "704x1280"], "inputModes": ["image", "text"], "queuedJobs": 0, "activeDispatches": 0, "dispatchConcurrency": 1})
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
    submitted = transport.submit_image(b"png", mime_type="image/png", payload={"prompt": "one line", "quality": 1, "resolution": "576x1024", "aspectPolicy": "reject_mismatch", "seed": 1, "durationSeconds": 5})
    polled = transport.poll(_JOB_ID); media = transport.download(_JOB_ID)
    assert transport._session.trust_env is False
    assert submitted["id"] == _JOB_ID and polled["outputReady"] is True and media == b"mp4"
    assert MiniMaxH3GatewayAdapter.completed_output(submitted, expected_profile_id=_PROFILE) is None
    assert all(call[2].get("allow_redirects") is False for call in session.calls)
    assert session.calls[1][1].endswith("/v1/video-jobs/from-image")
    assert session.calls[1][2]["data"]["durationSeconds"] == "5"
    assert session.calls[1][2]["data"]["quality"] == "1"
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
        "profileVersion": 2, "width": 576, "height": 1024,
        "fps": 24, "frameCount": 124,
        "allowLetterbox": False, "allowCenterCrop": True,
        "quality": 1,
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
            requested_seconds=5,
            expected_frame_count=124,
            expected_fps=24,
        )


def test_h3_eight_second_contract_freezes_grid_and_rejects_mismatched_envelopes() -> None:
    adapter = MiniMaxH3GatewayAdapter()
    contract = adapter.production_contract(
        requested_seconds=8, resolution="576x1024", audio=True,
        aspect_policy="reject_mismatch", allow_letterbox=False,
        allow_center_crop=False, seed=8, profile_id=_PROFILE,
    )
    assert contract.request_snapshot()["frameCount"] == 192
    assert adapter.compile_image(
        prompt="one line", duration=8, resolution="576x1024", audio=True,
        aspect_policy="reject_mismatch", seed=8, profile_id=_PROFILE, quality=1,
    )["durationSeconds"] == 8
    with pytest.raises(VideoProviderError, match="duration"):
        adapter.prediction_id(
            _job("queued", False), expected_profile_id=_PROFILE,
            expected_aspect_policy="reject_mismatch", expected_duration_seconds=8,
            expected_frame_count=192,
        )
    with pytest.raises(VideoProviderError, match="frame count"):
        adapter.completed_output(
            _job("succeeded", True, duration=8, frame_count=124), expected_profile_id=_PROFILE,
            expected_aspect_policy="reject_mismatch", expected_duration_seconds=8,
            expected_frame_count=192,
        )
    with pytest.raises(VideoOutputContractError, match="h3_output_profile_mismatch"):
        adapter.validate_observed_output(
            ObservedVideo(124 / 24, 576, 1024, "h264", "aac", frame_rate=24, frame_count=124),
            profile_id=_PROFILE, requested_seconds=8, expected_frame_count=192, expected_fps=24,
        )


def test_h3_public_profiles_advertise_reviewed_quality_and_duration_choices() -> None:
    capability = MiniMaxH3GatewayAdapter().public_capability()
    assert capability["qualifiedDurationSeconds"] == list(range(5, 16))
    assert capability["qualities"] == [1, 8]
    assert capability["defaultQuality"] == 8
    assert capability["defaultProfileId"] == _QUALITY_8_PROFILE
    assert all(
        "minDurationSeconds" not in profile and "maxDurationSeconds" not in profile
        for profile in capability["profiles"]
    )


def test_h3_frozen_profile_geometry_must_match_the_current_catalog() -> None:
    with pytest.raises(VideoProviderError, match="frozen profile contract"):
        MiniMaxH3GatewayAdapter().compile_image(
            prompt="one line", duration=8, resolution="576x1024", audio=True,
            aspect_policy="reject_mismatch", seed=8, profile_id=_PROFILE,
            profile_version=1, width=832, height=480, fps=24, frame_count=192,
        )


def test_h3_transport_rejects_submit_duration_or_frame_drift() -> None:
    class _Drifted(_GatewaySession):
        def request(self, method: str, url: str, **kwargs: object) -> _Response:
            if url.endswith("/v1/video-jobs/from-image"):
                return _Response(202, _job("queued", False, duration=8, frame_count=192))
            return super().request(method, url, **kwargs)

    transport = MiniMaxH3GatewayTransport("test-key", base_url="http://100.64.1.2:8090", session=_Drifted())
    with pytest.raises(WanDispatchError):
        transport.submit_image(b"png", mime_type="image/png", payload={"prompt": "x", "quality": 1, "resolution": "576x1024", "aspectPolicy": "reject_mismatch", "seed": 1, "durationSeconds": 5})


def test_h3_transport_rejects_unrecognised_direct_response_shape() -> None:
    class _Malformed(_GatewaySession):
        def request(self, method: str, url: str, **kwargs: object) -> _Response:
            if url.endswith("/v1/video-jobs/from-image"): return _Response(202, {"id": _JOB_ID, "status": "submitted"})
            return super().request(method, url, **kwargs)
    transport = MiniMaxH3GatewayTransport("test-key", base_url="http://100.64.1.2:8090", session=_Malformed())
    with pytest.raises(WanDispatchError):
        transport.submit_image(b"png", mime_type="image/png", payload={"prompt": "x", "quality": 1, "resolution": "576x1024", "aspectPolicy": "reject_mismatch", "seed": 1, "durationSeconds": 5})


def test_h3_quality_eight_freezes_base_recipe_and_exact_grid() -> None:
    adapter = MiniMaxH3GatewayAdapter()
    # Gateway profile_catalog.py is separately packaged; bind all eleven
    # gateway results here without making the product import that service.
    assert H3_QUALIFIED_DURATION_FRAMES == {
        5: 124, 6: 158, 7: 175, 8: 192, 9: 226, 10: 243,
        11: 277, 12: 294, 13: 328, 14: 345, 15: 362,
    }
    assert [H3_QUALIFIED_DURATION_FRAMES[seconds] for seconds in (5, 8, 15)] == [124, 192, 362]
    profile = next(profile for profile in H3_PROFILES if profile.profile_id == _QUALITY_8_PROFILE)
    assert profile.sampling_recipe is not None
    assert profile.sampling_recipe.public_descriptor() == {
        "id": "minimax_h3_base20", "version": 1, "topology": "base", "loraFile": None,
        "loraStrength": None, "inferenceSteps": 20, "videoSigmaShift": None,
        "audioSigmaShift": None, "sampler": "res_multistep", "scheduler": "simple", "denoise": 1.0,
    }
    contract = adapter.production_contract(
        requested_seconds=15, resolution="576x1024", audio=True,
        aspect_policy="reject_mismatch", allow_letterbox=False,
        allow_center_crop=False, seed=15, profile_id=_QUALITY_8_PROFILE,
    )
    assert contract.request_snapshot()["quality"] == 8
    assert contract.request_snapshot()["frameCount"] == 362
    assert adapter.compile_image(
        prompt="reviewed", duration=15, resolution="576x1024", audio=True,
        aspect_policy="reject_mismatch", seed=15, profile_id=_QUALITY_8_PROFILE,
        profile_version=2, width=576, height=1024, fps=24, frame_count=362, quality=8,
    )["quality"] == 8
    with pytest.raises(VideoProviderError, match="quality"):
        adapter.prediction_id(_job("queued", False, duration=15, frame_count=362), expected_profile_id=_QUALITY_8_PROFILE)
    with pytest.raises(VideoProviderError, match="duration"):
        adapter.production_contract(
            requested_seconds=16, resolution="576x1024", audio=True,
            aspect_policy="reject_mismatch", allow_letterbox=False,
            allow_center_crop=False, seed=15, profile_id=_QUALITY_8_PROFILE,
        )


def test_h3_api_duration_is_an_integer_within_gateway_range() -> None:
    body = {
        "approvalId": "approval", "shotId": "shot", "storyboardRevision": 1,
        "expectedSelectionRevision": 1, "idempotencyKey": "duration-validation",
    }
    for seconds in range(5, 16):
        assert VideoJobRequest.model_validate({**body, "requestedDurationSeconds": seconds}).requested_duration_seconds == seconds
    for invalid in (4, 16, True, 5.0, "8"):
        with pytest.raises(ValidationError):
            VideoJobRequest.model_validate({**body, "requestedDurationSeconds": invalid})


def test_h3_transport_rejects_non_integer_or_wrong_grid_response() -> None:
    for frame_count in (192.0, 175, True):
        with pytest.raises(WanDispatchError):
            MiniMaxH3GatewayTransport._validate_job_envelope(
                _job("queued", False, duration=8, frame_count=frame_count), phase="submit_response_parse",
                expected_quality=1, expected_duration_seconds=8, expected_frame_count=192,
            )


def test_h3_transport_sends_quality_eight_and_fifteen_seconds() -> None:
    class _QualityEightSession(_GatewaySession):
        def request(self, method: str, url: str, **kwargs: object) -> _Response:
            if url.endswith("/v1/video-jobs/from-image"):
                self.calls.append((method, url, dict(kwargs)))
                return _Response(202, {**_job("queued", False, duration=15, frame_count=362), "quality": 8, "seed": 15})
            return super().request(method, url, **kwargs)

    session = _QualityEightSession()
    transport = MiniMaxH3GatewayTransport("test-key", base_url="http://100.64.1.2:8090", session=session)
    result = transport.submit_image(b"png", mime_type="image/png", payload={
        "prompt": "reviewed", "quality": 8, "resolution": "576x1024",
        "aspectPolicy": "reject_mismatch", "seed": 15, "durationSeconds": 15,
    })
    assert result["quality"] == 8 and result["frameCount"] == 362
    assert session.calls[0][2]["data"]["quality"] == "8"
    assert session.calls[0][2]["data"]["durationSeconds"] == "15"


def test_legacy_quality_one_profile_keeps_its_frozen_meaning() -> None:
    legacy_id = "minimax_h3_quality1_portrait_576x1024_v1"
    adapter = MiniMaxH3GatewayAdapter()
    assert adapter.compile_image(
        prompt="legacy reviewed", duration=5, resolution="576x1024", audio=True,
        aspect_policy="reject_mismatch", seed=1, profile_id=legacy_id,
        profile_version=1, width=576, height=1024, fps=24, frame_count=124,
    )["quality"] == 1
    assert adapter.prediction_id(_job("queued", False), expected_profile_id=legacy_id) == _JOB_ID
    with pytest.raises(VideoProviderError, match="allowlisted"):
        adapter.production_contract(
            requested_seconds=5, resolution="576x1024", audio=True,
            aspect_policy="reject_mismatch", allow_letterbox=False,
            allow_center_crop=False, seed=1, profile_id=legacy_id,
        )
