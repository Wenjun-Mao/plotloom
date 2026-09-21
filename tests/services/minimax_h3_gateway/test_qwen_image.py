"""Qwen-Image jobs share the durable H3 gateway control plane."""
from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from plotloom_h3_gateway.app import GatewaySettings, create_app
from plotloom_h3_gateway.image_catalog import (
    QWEN_IMAGE_CANVASES,
    qwen_image_canvas_from_snapshot,
)
from plotloom_h3_gateway.profile_catalog import QUALITY_RECIPES


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
            return _Response(_comfy_object_info())
        raise AssertionError(url)

    def post(self, url: str, **_: object) -> _Response:
        assert url.endswith("/prompt")
        return _Response({"prompt_id": "comfy-test"})


def _comfy_object_info() -> dict[str, object]:
    """Provide the complete H3 readiness shape required by public health."""

    loras = [recipe.lora_file for recipe in QUALITY_RECIPES.values() if recipe.lora_file]

    def required(**values: object) -> dict[str, object]:
        return {"input": {"required": values}}

    return {
        "MiniMaxH3ImageToVideo": {"input": {"optional": {"first_frame": ["IMAGE"], "last_frame": ["IMAGE"]}}},
        "PrimitiveInt": {}, "KSamplerSelect": {}, "BasicScheduler": {}, "BasicGuider": {},
        "SamplerCustomAdvanced": {}, "MiniMaxH3SigmaShift": {},
        "UNETLoader": required(unet_name=[["minimax_h3_fl2va_pruned_fp8_scaled.safetensors"]]),
        "CLIPLoader": required(clip_name=[["qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"]]),
        "VAELoader": required(vae_name=[["minimax_h3_video_vae_fp16.safetensors", "minimax_h3_audio_vae_fp32.safetensors"]]),
        "LoraLoaderModelOnly": required(lora_name=[loras]),
    }

class _QwenSession:
    def __init__(self, image: bytes) -> None:
        self.image = image
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **_: object) -> _Response:
        assert url.endswith("/health")
        return _Response({"status": "ok"})

    def post(self, url: str, **kwargs: Any) -> _Response:
        self.calls.append((url, kwargs))
        return _Response({
            "id": "img-test", "created": 1, "peak_memory_mb": 1.0,
            "inference_time_s": 0.1, "usage": None,
            "data": [{
                "b64_json": base64.b64encode(self.image).decode("ascii"),
                "url": None, "revised_prompt": "test", "file_path": "/private/output.png",
                "resize": None,
            }],
        })


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
        json={"prompt": "x", "resolution": "768x768"},
    )
    assert unsupported.status_code == 422
    assert unsupported.json() == {"error": "image_resolution_not_supported"}
    profile = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "x", "resolution": "1024x1024", "profileId": "never"},
    )
    assert profile.json() == {"error": "request_invalid"}


def test_qwen_catalog_exposes_and_admits_only_reviewed_canvases(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    expected = [canvas.resolution for canvas in QWEN_IMAGE_CANVASES]
    assert client.get("/health").json()["imageResolutions"] == expected

    for canvas in QWEN_IMAGE_CANVASES:
        text = client.post(
            "/v1/image-jobs/from-text", headers=AUTH,
            json={"prompt": "A bounded canvas check.", "resolution": canvas.resolution},
        )
        assert text.status_code == 202, text.text
        assert text.json()["resolution"] == canvas.resolution

        edit = client.post(
            "/v1/image-jobs/from-image", headers=AUTH,
            data={"prompt": "A bounded edit canvas check.", "resolution": canvas.resolution},
            files={"image": ("reference.png", _png(width=canvas.width, height=canvas.height), "image/png")},
        )
        assert edit.status_code == 202, edit.text
        assert edit.json()["resolution"] == canvas.resolution


def test_qwen_text_job_uses_documented_generation_shape_and_managed_png(tmp_path: Path) -> None:
    client, qwen = _client(tmp_path, output=_png(width=576, height=1024))
    accepted = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "An observatory at dusk.", "resolution": "576x1024", "seed": 7},
    ).json()
    result = client.app.state.gateway.dispatch_once()
    assert result is not None and result["status"] == "succeeded"
    status = client.get(f"/v1/image-jobs/{accepted['id']}", headers=AUTH).json()
    assert status["outputReady"] is True
    assert status["outputContentType"] == "image/png"
    assert status["outputWidth"] == 576 and status["outputHeight"] == 1024
    assert status["generationElapsedMs"] is not None
    url, kwargs = qwen.calls[0]
    assert url.endswith("/v1/images/generations")
    assert kwargs["json"] == {
        "model": "Qwen/Qwen-Image-2.1", "prompt": "An observatory at dusk.", "n": 1,
        "size": "576x1024", "num_inference_steps": 40, "guidance_scale": 1.0,
        "seed": 7, "generator_device": "cpu", "output_format": "png",
        "response_format": "b64_json", "background": "opaque", "enable_cache_dit": False,
    }
    output = client.get(f"/v1/image-jobs/{accepted['id']}/output", headers=AUTH)
    assert output.headers["content-type"] == "image/png"
    assert output.content.startswith(b"\x89PNG")


def test_qwen_snapshot_freezes_its_canvas_and_rejects_mismatched_provider_output(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    accepted = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "A frozen portrait.", "resolution": "704x1280", "seed": 17},
    ).json()
    stored = client.app.state.gateway.store.get_job(accepted["id"])
    snapshot = json.loads(stored["execution_snapshot_json"])
    assert snapshot["imageContractVersion"] == 2
    assert snapshot["resolution"] == "704x1280"
    assert (snapshot["width"], snapshot["height"]) == (704, 1280)
    assert qwen_image_canvas_from_snapshot(stored["execution_snapshot_json"]).resolution == "704x1280"

    result = client.app.state.gateway.dispatch_once()
    assert result is not None and result["status"] == "failed"
    assert result["error_code"] == "qwen_image_output_invalid"


def test_qwen_square_snapshot_version_remains_readable() -> None:
    snapshot = json.dumps({
        "imageContractVersion": 1,
        "resolution": "1024x1024",
        "width": 1024,
        "height": 1024,
    })
    assert qwen_image_canvas_from_snapshot(snapshot).resolution == "1024x1024"


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
    assert "Everything outside the subject must be fully transparent" in kwargs["data"]["prompt"]
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


def test_transparent_request_rejects_nearly_opaque_png(tmp_path: Path) -> None:
    output = Image.new("RGBA", (1024, 1024), (20, 40, 60, 250))
    buffer = BytesIO()
    output.save(buffer, "PNG")
    client, _ = _client(tmp_path, output=buffer.getvalue())
    accepted = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "A cutout.", "resolution": "1024x1024", "backgroundMode": "transparent"},
    ).json()
    result = client.app.state.gateway.dispatch_once()
    assert result is not None and result["status"] == "failed"
    status = client.get(f"/v1/image-jobs/{accepted['id']}", headers=AUTH).json()
    assert status["error"] == "qwen_image_alpha_missing"


def test_qwen_transport_rejects_unexpected_provider_response_shape(tmp_path: Path) -> None:
    client, qwen = _client(tmp_path)
    qwen.post = lambda *_args, **_kwargs: _Response({"data": []})  # type: ignore[method-assign]
    accepted = client.post(
        "/v1/image-jobs/from-text", headers=AUTH,
        json={"prompt": "A strict response contract.", "resolution": "1024x1024"},
    ).json()
    result = client.app.state.gateway.dispatch_once()
    assert result is not None and result["status"] == "failed"
    status = client.get(f"/v1/image-jobs/{accepted['id']}", headers=AUTH).json()
    assert status["error"] == "qwen_image_response_invalid"


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
