"""Qwen-Image jobs share the durable H3 gateway control plane."""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from plotloom_h3_gateway.app import GatewaySettings, create_app


AUTH = {"Authorization": "Bearer test-key"}


class _Response:
    def __init__(self, payload: object | None = None) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _ComfySession:
    def get(self, url: str, **_: object) -> _Response:
        if url.endswith("/queue"):
            return _Response({"queue_running": [], "queue_pending": []})
        if url.endswith("/system_stats"):
            return _Response({"system": {}})
        if url.endswith("/object_info"):
            return _Response({})
        raise AssertionError(url)

    def post(self, url: str, **_: object) -> _Response:
        raise AssertionError(url)


class _QwenSession:
    def __init__(self, image: bytes) -> None:
        self.image = image
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **_: object) -> _Response:
        assert url.endswith("/health")
        return _Response({"status": "ok"})

    def post(self, url: str, **kwargs: Any) -> _Response:
        self.calls.append((url, kwargs))
        return _Response({"created": 1, "data": [{"b64_json": base64.b64encode(self.image).decode("ascii")} ]})


class _SourceResponse:
    headers: dict[str, str] = {}

    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, **_: object):
        yield self.content

    def close(self) -> None:
        return None


class _SourceSession:
    max_redirects = 3

    def __init__(self, content: bytes) -> None:
        self.content = content

    def get(self, url: str, **_: object) -> _SourceResponse:
        assert url == "https://images.internal/reference.png"
        return _SourceResponse(self.content)


def _png(*, transparent: bool = False, width: int = 1024, height: int = 1024) -> bytes:
    image = Image.new("RGBA" if transparent else "RGB", (width, height), (30, 80, 120, 0) if transparent else "#1e5078")
    if transparent:
        image.paste((255, 120, 20, 255), (128, 128, 896, 896))
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _client(
    tmp_path: Path, *, output: bytes | None = None, source: bytes | None = None
) -> tuple[TestClient, _QwenSession]:
    qwen = _QwenSession(output or _png())
    client = TestClient(create_app(
        GatewaySettings(
            api_key="test-key", data_dir=tmp_path / "data", comfy_input_dir=tmp_path / "input",
            comfy_output_dir=tmp_path / "output", dispatch_worker_enabled=False,
        ),
        session=_ComfySession(), qwen_session=qwen,
        source_session=_SourceSession(source) if source is not None else None,
    ))
    return client, qwen


def test_text_image_contract_is_strict_and_freezes_random_seed(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    response = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "A brass moth on dark velvet.", "resolution": "1024x1024"},
    )
    assert response.status_code == 202
    job = response.json()
    assert job["id"].startswith("img_")
    assert job["inputMode"] == "text"
    assert job["backgroundMode"] == "opaque"
    assert isinstance(job["seed"], int)
    assert "quality" not in job and "requestedDurationSeconds" not in job
    unsupported = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "x", "resolution": "576x1024"},
    )
    assert unsupported.status_code == 422
    assert unsupported.json() == {"error": "request_invalid"}
    profile = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "x", "resolution": "1024x1024", "profileId": "never"},
    )
    assert profile.json() == {"error": "request_invalid"}


def test_qwen_text_job_uses_documented_generation_shape_and_managed_png(tmp_path: Path) -> None:
    client, qwen = _client(tmp_path)
    accepted = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "An observatory at dusk.", "resolution": "1024x1024", "seed": 7},
    ).json()
    result = client.app.state.gateway.dispatch_once()
    assert result is not None and result["status"] == "succeeded"
    status = client.get(f"/v1/image-jobs/{accepted['id']}", headers=AUTH).json()
    assert status["outputReady"] is True
    assert status["outputContentType"] == "image/png"
    assert status["outputWidth"] == 1024 and status["outputHeight"] == 1024
    assert status["generationElapsedMs"] is not None
    url, kwargs = qwen.calls[0]
    assert url.endswith("/v1/images/generations")
    assert kwargs["json"] == {
        "model": "Qwen/Qwen-Image-2.1", "prompt": "An observatory at dusk.", "n": 1,
        "size": "1024x1024", "num_inference_steps": 40, "guidance_scale": 1.0,
        "seed": 7, "generator_device": "cpu", "output_format": "png",
        "response_format": "b64_json", "background": "auto", "enable_cache_dit": False,
    }
    output = client.get(f"/v1/image-jobs/{accepted['id']}/output", headers=AUTH)
    assert output.headers["content-type"] == "image/png"
    assert output.content.startswith(b"\x89PNG")


def test_single_reference_edit_accepts_one_file_and_preserves_transparent_png(tmp_path: Path) -> None:
    client, qwen = _client(tmp_path, output=_png(transparent=True))
    accepted = client.post(
        "/v1/image-jobs/from-image", headers=AUTH,
        data={"prompt": "Keep the orange subject, with no background.", "resolution": "1024x1024", "seed": "8", "backgroundMode": "transparent"},
        files={"image": ("reference.png", _png(transparent=True), "image/png")},
    )
    assert accepted.status_code == 202
    result = client.app.state.gateway.dispatch_once()
    assert result is not None and result["status"] == "succeeded"
    status = client.get(f"/v1/image-jobs/{accepted.json()['id']}", headers=AUTH).json()
    assert status["backgroundMode"] == "transparent"
    url, kwargs = qwen.calls[0]
    assert url.endswith("/v1/images/edits")
    assert kwargs["data"]["background"] == "transparent"
    assert "image[]" in kwargs["files"]
    missing = client.post(
        "/v1/image-jobs/from-image", headers=AUTH,
        data={"prompt": "x", "resolution": "1024x1024"},
        files={"image": (None, "")},
    )
    assert missing.json() == {"error": "image_file_required"}


def test_single_reference_edit_accepts_downloadable_url_without_storing_url(tmp_path: Path) -> None:
    client, qwen = _client(tmp_path, source=_png())
    accepted = client.post(
        "/v1/image-jobs/from-image", headers=AUTH,
        json={
            "sourceUrl": "https://images.internal/reference.png",
            "prompt": "Turn the station lights blue.", "resolution": "1024x1024", "seed": 15,
        },
    )
    assert accepted.status_code == 202
    client.app.state.gateway.dispatch_once()
    assert qwen.calls[0][0].endswith("/v1/images/edits")
    stored = client.app.state.gateway.store.get_job(accepted.json()["id"])
    assert "images.internal" not in str(stored)


def test_transparent_request_rejects_non_alpha_model_output(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, output=_png())
    accepted = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "A clean cutout.", "resolution": "1024x1024", "backgroundMode": "transparent"},
    ).json()
    result = client.app.state.gateway.dispatch_once()
    assert result is not None and result["status"] == "failed"
    status = client.get(f"/v1/image-jobs/{accepted['id']}", headers=AUTH).json()
    assert status["error"] == "qwen_image_alpha_missing"


def test_qwen_and_h3_share_one_fifo_lane(tmp_path: Path) -> None:
    client, qwen = _client(tmp_path)
    image = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "First image.", "resolution": "1024x1024"},
    ).json()
    video = client.post(
        "/v1/video-jobs/from-text", headers=AUTH,
        json={"prompt": "Second video.", "resolution": "832x480"},
    ).json()
    first = client.app.state.gateway.dispatch_once()
    assert first is not None and first["id"] == image["id"] and len(qwen.calls) == 1
    second = client.app.state.gateway.dispatch_once()
    assert second is not None and second["id"] == video["id"]
