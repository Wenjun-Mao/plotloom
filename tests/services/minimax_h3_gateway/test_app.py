from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from plotloom_h3_gateway.app import GatewaySettings, create_app


class _Response:
    def __init__(self, payload: object, *, content: bytes = b"") -> None:
        self._payload = payload
        self.content = content

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _ComfySession:
    def __init__(self) -> None:
        self.submissions: list[dict[str, Any]] = []
        self.history: dict[str, object] = {}

    def get(self, url: str, **_: object) -> _Response:
        if url.endswith("/system_stats"):
            return _Response({"system": {}})
        if url.endswith("/queue"):
            return _Response({"queue_running": [], "queue_pending": []})
        if url.endswith("/object_info"):
            return _Response(_object_info())
        if "/history/" in url:
            prompt_id = url.rsplit("/", 1)[-1]
            return _Response(self.history.get(prompt_id, {}))
        if url.endswith("/view"):
            return _Response({}, content=b"synthetic-mp4")
        raise AssertionError(url)

    def post(self, url: str, *, json: dict[str, Any], **_: object) -> _Response:
        assert url.endswith("/prompt")
        self.submissions.append(json)
        return _Response({"prompt_id": "comfy-1"})


def _object_info() -> dict[str, object]:
    required = {
        "UNETLoader": ("unet_name", "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"),
        "CLIPLoader": ("clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
        "VAELoader": ("vae_name", ["minimax_h3_video_vae_fp16.safetensors", "minimax_h3_audio_vae_fp32.safetensors"]),
        "LoraLoaderModelOnly": ("lora_name", "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"),
    }
    result: dict[str, object] = {"MiniMaxH3ImageToVideo": {}}
    for node_type, (name, options) in required.items():
        values = options if isinstance(options, list) else [options]
        result[node_type] = {"input": {"required": {name: [values]}}}
    return result


def _client(tmp_path: Path) -> tuple[TestClient, _ComfySession]:
    session = _ComfySession()
    app = create_app(
        GatewaySettings(
            api_key="test-key", data_dir=tmp_path / "data", comfy_input_dir=tmp_path / "comfy-input",
        ),
        session=session,
    )
    return TestClient(app), session


def _png(width: int = 1371, height: int = 1148) -> bytes:
    image = Image.new("RGB", (width, height), "#355070")
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_upload_requires_bearer_key(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    response = client.post("/v1/assets", files={"image": ("frame.png", _png(), "image/png")})
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_job_uses_frozen_profile_and_crop_policy_without_stretching(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    headers = {"Authorization": "Bearer test-key"}
    asset = client.post(
        "/v1/assets", headers=headers, files={"image": ("portrait.png", _png(), "image/png")},
    )
    assert asset.status_code == 200
    response = client.post(
        "/v1/video-jobs", headers=headers,
        json={"assetId": asset.json()["assetId"], "prompt": "A calm glance.", "aspectPolicy": "cover_center_crop", "seed": 12},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "submitted"
    assert len(session.submissions) == 1
    submitted = session.submissions[0]["prompt"]
    assert submitted["105:6"]["inputs"]["unet_name"] == "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"
    assert submitted["105:104"]["inputs"]["prompt"] == "A calm glance."
    prepared = next((tmp_path / "comfy-input").glob("*.png"))
    with Image.open(prepared) as image:
        assert image.size == (864, 480)


def test_reject_policy_refuses_aspect_mismatch_before_comfy_submit(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    headers = {"Authorization": "Bearer test-key"}
    asset = client.post(
        "/v1/assets", headers=headers, files={"image": ("portrait.png", _png(), "image/png")},
    ).json()
    response = client.post(
        "/v1/video-jobs", headers=headers,
        json={"assetId": asset["assetId"], "prompt": "A calm glance.", "aspectPolicy": "reject_mismatch"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "failed"
    assert response.json()["error"] == "input_aspect_mismatch"
    assert session.submissions == []


def test_completed_job_proxies_only_its_single_mp4_output(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    headers = {"Authorization": "Bearer test-key"}
    asset = client.post(
        "/v1/assets", headers=headers, files={"image": ("landscape.png", _png(864, 480), "image/png")},
    ).json()
    job = client.post(
        "/v1/video-jobs", headers=headers,
        json={"assetId": asset["assetId"], "prompt": "A calm glance.", "aspectPolicy": "reject_mismatch"},
    ).json()
    session.history["comfy-1"] = {
        "comfy-1": {
            "status": {"status_str": "success", "completed": True},
            "outputs": {"92": {"images": [{"filename": "result.mp4", "subfolder": "video", "type": "output"}]}},
        }
    }
    status = client.get(f"/v1/video-jobs/{job['id']}", headers=headers)
    assert status.json()["status"] == "succeeded"
    output = client.get(f"/v1/video-jobs/{job['id']}/output", headers=headers)
    assert output.status_code == 200
    assert output.headers["content-type"] == "video/mp4"
    assert output.content == b"synthetic-mp4"
