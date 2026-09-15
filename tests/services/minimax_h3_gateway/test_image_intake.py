"""Contract coverage for raw/URL image ingress and one-step H3 admission."""
from __future__ import annotations

import requests
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from plotloom_h3_gateway.app import GatewaySettings, create_app


class _SourceResponse:
    def __init__(
        self,
        content: bytes,
        *,
        headers: dict[str, str] | None = None,
        error: requests.RequestException | None = None,
        chunks: list[bytes] | None = None,
    ) -> None:
        self._content = content
        self.headers = headers or {}
        self._error = error
        self._chunks = chunks
        self.closed = False

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error

    def iter_content(self, *, chunk_size: int) -> list[bytes]:
        assert chunk_size == 64 * 1024
        return self._chunks if self._chunks is not None else [self._content]

    def close(self) -> None:
        self.closed = True


class _SourceSession:
    def __init__(self, response: _SourceResponse | requests.RequestException) -> None:
        self.response = response
        self.max_redirects: int | None = None
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, url: str, **kwargs: object) -> _SourceResponse:
        self.calls.append((url, kwargs))
        if isinstance(self.response, requests.RequestException):
            raise self.response
        return self.response


def _client(tmp_path: Path, *, source_session: _SourceSession | None = None) -> TestClient:
    return TestClient(create_app(
        GatewaySettings(
            api_key="test-key",
            data_dir=tmp_path / "data",
            comfy_input_dir=tmp_path / "comfy-input",
            comfy_output_dir=tmp_path / "comfy-output",
            dispatch_worker_enabled=False,
        ),
        session=object(),
        source_session=source_session,
    ))


def _png(width: int = 1371, height: int = 1148) -> bytes:
    image = Image.new("RGB", (width, height), "#355070")
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_asset_upload_detects_image_bytes_instead_of_trusting_multipart_mime(tmp_path: Path) -> None:
    response = _client(tmp_path).post(
        "/v1/assets",
        headers={"Authorization": "Bearer test-key"},
        files={"image": ("frame.bin", _png(864, 480), "application/octet-stream")},
    )
    assert response.status_code == 200
    assert response.json()["mimeType"] == "image/png"


def test_asset_url_ingestion_is_bounded_and_does_not_persist_source_url(tmp_path: Path) -> None:
    source_url = "http://100.64.35.71:9000/reviewed-frame?temporary=secret"
    source_response = _SourceResponse(_png(864, 480), headers={"Content-Type": "application/octet-stream"})
    source_session = _SourceSession(source_response)
    client = _client(tmp_path, source_session=source_session)
    response = client.post(
        "/v1/assets",
        headers={"Authorization": "Bearer test-key"},
        json={"sourceUrl": source_url},
    )
    assert response.status_code == 200
    assert response.json()["mimeType"] == "image/png"
    assert source_session.max_redirects == 3
    assert source_session.calls == [
        (source_url, {"allow_redirects": True, "stream": True, "timeout": (5.0, 20.0)})
    ]
    assert source_response.closed is True
    with client.app.state.gateway.store._connect() as connection:
        serialized = " ".join(str(item) for item in connection.execute("SELECT * FROM assets").fetchone())
    assert source_url not in serialized


def test_asset_url_rejects_invalid_fetches_and_declared_or_streamed_oversize(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer test-key"}
    invalid = _client(tmp_path / "invalid").post(
        "/v1/assets", headers=headers, json={"sourceUrl": "file:///tmp/frame.png"}
    )
    assert invalid.status_code == 422
    assert invalid.json() == {"error": "source_url_invalid"}

    declared = _client(
        tmp_path / "declared-oversize",
        source_session=_SourceSession(_SourceResponse(
            b"", headers={"Content-Length": str(20 * 1024 * 1024 + 1)}
        )),
    ).post("/v1/assets", headers=headers, json={"sourceUrl": "https://images.example/frame"})
    assert declared.status_code == 413
    assert declared.json() == {"error": "source_url_too_large"}

    streamed = _client(
        tmp_path / "streamed-oversize",
        source_session=_SourceSession(_SourceResponse(
            b"", chunks=[b"x" * (20 * 1024 * 1024), b"x"]
        )),
    ).post("/v1/assets", headers=headers, json={"sourceUrl": "https://images.example/frame"})
    assert streamed.status_code == 413
    assert streamed.json() == {"error": "source_url_too_large"}

    failed = _client(
        tmp_path / "failed",
        source_session=_SourceSession(requests.ConnectionError("synthetic source outage")),
    ).post("/v1/assets", headers=headers, json={"sourceUrl": "https://images.example/frame"})
    assert failed.status_code == 422
    assert failed.json() == {"error": "source_url_fetch_failed"}


def test_one_step_url_submission_returns_the_normal_queued_job_envelope(tmp_path: Path) -> None:
    client = _client(tmp_path, source_session=_SourceSession(_SourceResponse(_png(864, 480))))
    response = client.post(
        "/v1/video-jobs/from-image",
        headers={"Authorization": "Bearer test-key"},
        json={
            "sourceUrl": "http://100.64.35.71:9000/frame.png",
            "prompt": "She pauses at the airlock and listens.",
            "aspectPolicy": "reject_mismatch",
            "seed": 42,
        },
    )
    assert response.status_code == 202
    assert set(response.json()) == {"id", "status", "profileId", "aspectPolicy", "error", "outputReady"}
    assert response.json()["status"] == "queued"
    assert response.json()["profileId"] == "minimax_h3_fp8_turbo4_480p"


def test_one_step_rejects_an_unknown_profile_before_fetching_the_source_url(tmp_path: Path) -> None:
    source_session = _SourceSession(_SourceResponse(_png(864, 480)))
    response = _client(tmp_path, source_session=source_session).post(
        "/v1/video-jobs/from-image",
        headers={"Authorization": "Bearer test-key"},
        json={
            "sourceUrl": "http://100.64.35.71:9000/frame.png",
            "prompt": "This should not retrieve an image.",
            "profileId": "minimax_h3_unreviewed_1",
            "aspectPolicy": "reject_mismatch",
        },
    )
    assert response.status_code == 422
    assert response.json() == {"error": "profile_not_supported"}
    assert source_session.calls == []


def test_one_step_multipart_submission_never_creates_retry_deduplication_state(tmp_path: Path) -> None:
    client = _client(tmp_path)
    headers = {"Authorization": "Bearer test-key"}
    accepted = client.post(
        "/v1/video-jobs/from-image",
        headers=headers,
        data={"prompt": "A quiet turn.", "aspectPolicy": "reject_mismatch", "seed": "42"},
        files={"image": ("frame.png", _png(864, 480), "image/png")},
    )
    assert accepted.status_code == 202
    assert accepted.json()["status"] == "queued"
    rejected = client.post(
        "/v1/video-jobs/from-image",
        headers=headers,
        data={
            "prompt": "A quiet turn.",
            "aspectPolicy": "reject_mismatch",
            "idempotencyKey": "never-store-this-on-one-step",
        },
        files={"image": ("frame.png", _png(864, 480), "image/png")},
    )
    assert rejected.status_code == 422
    assert rejected.json() == {"error": "one_step_idempotency_not_supported"}


def test_one_step_known_aspect_failure_rolls_back_its_unreferenced_asset(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/v1/video-jobs/from-image",
        headers={"Authorization": "Bearer test-key"},
        data={"prompt": "A quiet turn.", "aspectPolicy": "reject_mismatch"},
        files={"image": ("portrait.png", _png(), "image/png")},
    )
    assert response.status_code == 422
    assert response.json() == {"error": "input_aspect_mismatch"}
    with client.app.state.gateway.store._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
    assert list((tmp_path / "data" / "assets").iterdir()) == []
