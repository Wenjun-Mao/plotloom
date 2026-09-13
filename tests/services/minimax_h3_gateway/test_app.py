from __future__ import annotations

import threading
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image
import requests

from plotloom.video_backends.minimax_h3 import H3_PROFILES
from plotloom_h3_gateway.app import GatewaySettings, create_app
from plotloom_h3_gateway.profile_catalog import H3_GATEWAY_PROFILES


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
        self.submitted = threading.Event()
        self.queue_running: list[object] = []
        self.queue_pending: list[object] = []
        self.available = True

    def get(self, url: str, **_: object) -> _Response:
        if not self.available:
            raise requests.ConnectionError("synthetic ComfyUI outage")
        if url.endswith("/system_stats"):
            return _Response({"system": {}})
        if url.endswith("/queue"):
            return _Response({"queue_running": self.queue_running, "queue_pending": self.queue_pending})
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
        self.submitted.set()
        return _Response({"prompt_id": f"comfy-{len(self.submissions)}"})


def _object_info() -> dict[str, object]:
    required = {
        "UNETLoader": ("unet_name", "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"),
        "CLIPLoader": ("clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
        "VAELoader": ("vae_name", ["minimax_h3_video_vae_fp16.safetensors", "minimax_h3_audio_vae_fp32.safetensors"]),
        "LoraLoaderModelOnly": ("lora_name", "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"),
    }
    result: dict[str, object] = {"MiniMaxH3ImageToVideo": {}, "PrimitiveInt": {}}
    for node_type, (name, options) in required.items():
        values = options if isinstance(options, list) else [options]
        result[node_type] = {"input": {"required": {name: [values]}}}
    return result


def _client(tmp_path: Path) -> tuple[TestClient, _ComfySession]:
    session = _ComfySession()
    app = create_app(
        GatewaySettings(
            api_key="test-key", data_dir=tmp_path / "data", comfy_input_dir=tmp_path / "comfy-input",
            dispatch_worker_enabled=False,
        ),
        session=session,
    )
    return TestClient(app), session


def _dispatch_once(client: TestClient) -> dict[str, Any] | None:
    return client.app.state.gateway.dispatch_once()


def _png(width: int = 1371, height: int = 1148) -> bytes:
    image = Image.new("RGB", (width, height), "#355070")
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_gateway_and_plotloom_catalogs_match_exactly() -> None:
    """Independent packages must agree before a profile can enter production."""

    assert [item.public_descriptor() for item in H3_GATEWAY_PROFILES] == [
        item.public_descriptor() for item in H3_PROFILES
    ]


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
    assert response.json()["status"] == "queued"
    assert session.submissions == []
    assert _dispatch_once(client)["status"] == "submitted"
    assert len(session.submissions) == 1
    submitted = session.submissions[0]["prompt"]
    assert submitted["105:6"]["inputs"]["unet_name"] == "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"
    assert submitted["105:104"]["inputs"]["prompt"] == "A calm glance."
    prepared = next((tmp_path / "comfy-input").glob("*.png"))
    with Image.open(prepared) as image:
        assert image.size == (864, 480)


def test_catalog_profile_uses_exact_portrait_dimensions_and_health_is_secret_free(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["profileContractVersion"] == 2
    assert health.json()["queuedJobs"] == 0
    assert health.json()["activeDispatches"] == 0
    assert health.json()["dispatchConcurrency"] == 1
    assert "maxQueueDepth" not in health.json()
    profiles = health.json()["profiles"]
    assert len(profiles) == 7
    assert all("lora" not in item and "path" not in item for item in profiles)
    profile_id = "minimax_h3_fp8_turbo4_portrait_704x1280_v1"
    headers = {"Authorization": "Bearer test-key"}
    asset = client.post(
        "/v1/assets", headers=headers, files={"image": ("portrait.png", _png(), "image/png")},
    ).json()
    response = client.post(
        "/v1/video-jobs", headers=headers,
        json={"assetId": asset["assetId"], "prompt": "A calm glance.", "profileId": profile_id,
              "aspectPolicy": "contain_pad", "seed": 12},
    )
    assert response.status_code == 202
    assert response.json()["profileId"] == profile_id
    assert _dispatch_once(client)["status"] == "submitted"
    workflow = session.submissions[0]["prompt"]
    assert workflow["115"] == {"class_type": "PrimitiveInt", "inputs": {"value": 704}}
    assert workflow["116"] == {"class_type": "PrimitiveInt", "inputs": {"value": 1280}}
    prepared = next((tmp_path / "comfy-input").glob("*.png"))
    with Image.open(prepared) as image:
        assert image.size == (704, 1280)


def test_gateway_rejects_unknown_profile_before_creating_a_job(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    headers = {"Authorization": "Bearer test-key"}
    asset = client.post(
        "/v1/assets", headers=headers, files={"image": ("portrait.png", _png(), "image/png")},
    ).json()
    response = client.post(
        "/v1/video-jobs", headers=headers,
        json={"assetId": asset["assetId"], "prompt": "A calm glance.", "profileId": "minimax_h3_unreviewed_1",
              "aspectPolicy": "contain_pad"},
    )
    assert response.status_code == 422
    assert response.json() == {"error": "profile_not_supported"}


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
    assert _dispatch_once(client)["status"] == "submitted"
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


def _queue_job(client: TestClient, headers: dict[str, str], asset_id: str, *, prompt: str, key: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "assetId": asset_id,
        "prompt": prompt,
        "aspectPolicy": "reject_mismatch",
        "seed": 7,
    }
    if key is not None:
        payload["idempotencyKey"] = key
    response = client.post("/v1/video-jobs", headers=headers, json=payload)
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"
    return response.json()


def test_fifo_queue_dispatches_only_one_h3_job_at_a_time(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    headers = {"Authorization": "Bearer test-key"}
    asset = client.post(
        "/v1/assets", headers=headers,
        files={"image": ("landscape.png", _png(864, 480), "image/png")},
    ).json()
    first = _queue_job(client, headers, asset["assetId"], prompt="First action")
    second = _queue_job(client, headers, asset["assetId"], prompt="Second action")

    assert _dispatch_once(client)["id"] == first["id"]
    assert len(session.submissions) == 1
    # The first known H3 request has no completed history yet, so the second
    # cannot reach ComfyUI merely because the gateway itself has a backlog.
    assert _dispatch_once(client) is None
    assert len(session.submissions) == 1

    session.history["comfy-1"] = {
        "comfy-1": {
            "status": {"status_str": "success", "completed": True},
            "outputs": {"92": {"images": [{"filename": "first.mp4", "subfolder": "video", "type": "output"}]}},
        }
    }
    assert _dispatch_once(client)["id"] == second["id"]
    assert len(session.submissions) == 2


def test_gateway_allows_a_large_fifo_backlog_but_waits_for_external_comfy_work(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    headers = {"Authorization": "Bearer test-key"}
    asset = client.post(
        "/v1/assets", headers=headers,
        files={"image": ("landscape.png", _png(864, 480), "image/png")},
    ).json()
    queued = [
        _queue_job(client, headers, asset["assetId"], prompt=f"Queued action {index}")
        for index in range(10)
    ]
    assert client.get("/health").json()["queuedJobs"] == 10

    session.queue_pending = [{"external": "trusted-comfy-work"}]
    assert _dispatch_once(client) is None
    assert session.submissions == []
    session.queue_pending = []
    assert _dispatch_once(client)["id"] == queued[0]["id"]
    assert len(session.submissions) == 1


def test_queued_job_is_idempotent_and_can_be_cancelled_before_dispatch(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    headers = {"Authorization": "Bearer test-key"}
    asset = client.post(
        "/v1/assets", headers=headers,
        files={"image": ("landscape.png", _png(864, 480), "image/png")},
    ).json()
    key = "gateway-idempotency-key"
    first = _queue_job(client, headers, asset["assetId"], prompt="Wait here", key=key)
    replay = _queue_job(client, headers, asset["assetId"], prompt="Wait here", key=key)
    assert replay["id"] == first["id"]
    conflict = client.post("/v1/video-jobs", headers=headers, json={
        "assetId": asset["assetId"], "prompt": "Changed request", "aspectPolicy": "reject_mismatch",
        "seed": 7, "idempotencyKey": key,
    })
    assert conflict.status_code == 409
    assert conflict.json() == {"error": "idempotency_conflict"}

    cancelled = client.post(f"/v1/video-jobs/{first['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert _dispatch_once(client) is None
    assert session.submissions == []


def test_restart_preserves_queued_order_and_never_replays_an_interrupted_dispatch(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer test-key"}
    settings = GatewaySettings(
        api_key="test-key", data_dir=tmp_path / "data", comfy_input_dir=tmp_path / "comfy-input",
        dispatch_worker_enabled=False,
    )
    first_session = _ComfySession()
    first_app = create_app(settings, session=first_session)
    first_client = TestClient(first_app)
    asset = first_client.post(
        "/v1/assets", headers=headers,
        files={"image": ("landscape.png", _png(864, 480), "image/png")},
    ).json()
    interrupted = _queue_job(first_client, headers, asset["assetId"], prompt="Never replay me")
    first = _queue_job(first_client, headers, asset["assetId"], prompt="Preserve first")
    second = _queue_job(first_client, headers, asset["assetId"], prompt="Preserve second")
    # Claiming is persisted before an outbound call. Simulate a process loss at
    # that conservative boundary: restart must not retry it.
    assert first_app.state.gateway.store.claim_next_queued()["id"] == interrupted["id"]

    restarted_session = _ComfySession()
    restarted_app = create_app(settings, session=restarted_session)
    restarted_client = TestClient(restarted_app)
    recovered = restarted_client.get(f"/v1/video-jobs/{interrupted['id']}", headers=headers)
    assert recovered.status_code == 200
    assert recovered.json()["status"] == "outcome_unknown"
    dispatched = _dispatch_once(restarted_client)
    assert dispatched is not None and dispatched["id"] == first["id"]
    assert len(restarted_session.submissions) == 1
    # The second item remains queued behind the known first ComfyUI job.
    assert _dispatch_once(restarted_client) is None
    assert restarted_client.get(f"/v1/video-jobs/{second['id']}", headers=headers).json()["status"] == "queued"


def test_gateway_accepts_durable_work_while_comfyui_is_temporarily_unavailable(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    headers = {"Authorization": "Bearer test-key"}
    asset = client.post(
        "/v1/assets", headers=headers,
        files={"image": ("landscape.png", _png(864, 480), "image/png")},
    ).json()
    session.available = False
    queued = _queue_job(client, headers, asset["assetId"], prompt="Wait for H3")
    assert _dispatch_once(client) is None
    assert session.submissions == []

    session.available = True
    assert _dispatch_once(client)["id"] == queued["id"]
    assert len(session.submissions) == 1


def test_runtime_worker_dispatches_a_queued_job_without_a_polling_browser(tmp_path: Path) -> None:
    session = _ComfySession()
    app = create_app(
        GatewaySettings(
            api_key="test-key", data_dir=tmp_path / "data", comfy_input_dir=tmp_path / "comfy-input",
            worker_poll_seconds=0.01,
        ),
        session=session,
    )
    headers = {"Authorization": "Bearer test-key"}
    with TestClient(app) as client:
        asset = client.post(
            "/v1/assets", headers=headers,
            files={"image": ("landscape.png", _png(864, 480), "image/png")},
        ).json()
        job = _queue_job(client, headers, asset["assetId"], prompt="Worker takes this")
        assert session.submitted.wait(timeout=1.0)
        status = client.get(f"/v1/video-jobs/{job['id']}", headers=headers)
        assert status.json()["status"] in {"submitted", "running"}
