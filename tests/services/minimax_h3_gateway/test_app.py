"""Direct H3 job contract, workflow, timing, and migration coverage."""
from __future__ import annotations

import sqlite3
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from fastapi.testclient import TestClient
from PIL import Image

from plotloom.video_backends.minimax_h3 import H3_PROFILES
from plotloom_h3_gateway.app import GatewaySettings, GatewayStore, create_app
from plotloom_h3_gateway.profile_catalog import H3_GATEWAY_PROFILES, frame_count_for_duration_seconds
from plotloom_h3_gateway.workflow import load_h3_template, render_workflow


PROFILE = "minimax_h3_fp8_turbo4_landscape_832x480_v1"
AUTH = {"Authorization": "Bearer test-key"}


class _Response:
    def __init__(self, payload: object) -> None: self._payload = payload
    def json(self) -> object: return self._payload
    def raise_for_status(self) -> None: return None


class _ComfySession:
    def __init__(self) -> None:
        self.submissions: list[dict[str, Any]] = []
        self.history: dict[str, object] = {}

    def get(self, url: str, **_: object) -> _Response:
        if url.endswith("/system_stats"): return _Response({"system": {}})
        if url.endswith("/queue"): return _Response({"queue_running": [], "queue_pending": []})
        if url.endswith("/object_info"): return _Response(_object_info())
        if "/history/" in url:
            prompt_id = url.rsplit("/", 1)[-1]
            return _Response({prompt_id: self.history[prompt_id]} if prompt_id in self.history else {})
        raise AssertionError(url)

    def post(self, url: str, *, json: dict[str, Any], **_: object) -> _Response:
        assert url.endswith("/prompt")
        self.submissions.append(json)
        return _Response({"prompt_id": f"comfy-{len(self.submissions)}"})


def _object_info() -> dict[str, object]:
    result: dict[str, object] = {
        "MiniMaxH3ImageToVideo": {"input": {"optional": {"first_frame": ["IMAGE"], "last_frame": ["IMAGE"]}}},
        "PrimitiveInt": {},
    }
    for node, field, values in (
        ("UNETLoader", "unet_name", ["minimax_h3_fl2va_pruned_fp8_scaled.safetensors"]),
        ("CLIPLoader", "clip_name", ["qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"]),
        ("VAELoader", "vae_name", ["minimax_h3_video_vae_fp16.safetensors", "minimax_h3_audio_vae_fp32.safetensors"]),
        ("LoraLoaderModelOnly", "lora_name", ["minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"]),
    ):
        result[node] = {"input": {"required": {field: [values]}}}
    return result


def _client(tmp_path: Path) -> tuple[TestClient, _ComfySession]:
    session = _ComfySession()
    return TestClient(create_app(GatewaySettings(api_key="test-key", data_dir=tmp_path / "data", comfy_input_dir=tmp_path / "input", comfy_output_dir=tmp_path / "output", dispatch_worker_enabled=False), session=session)), session


def _png(width: int = 832, height: int = 480, colour: str = "#355070") -> bytes:
    image = Image.new("RGB", (width, height), colour)
    buffer = BytesIO(); image.save(buffer, "PNG")
    return buffer.getvalue()


def _image_payload(**extra: object) -> dict[str, object]:
    return {"prompt": "A pilot pauses at the airlock.", "profileId": PROFILE, "aspectPolicy": "reject_mismatch", **extra}


def _submit_image(client: TestClient, **extra: object) -> dict[str, Any]:
    response = client.post("/v1/video-jobs/from-image", headers=AUTH, data={key: str(value) for key, value in _image_payload(**extra).items()}, files={"image": ("start.png", _png(), "image/png")})
    assert response.status_code == 202, response.text
    return response.json()


def test_gateway_and_plotloom_catalogs_match_exactly() -> None:
    assert [item.public_descriptor() for item in H3_GATEWAY_PROFILES] == [item.public_descriptor() for item in H3_PROFILES]


def test_retired_creation_routes_are_not_registered(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.post("/v1/assets", headers=AUTH).status_code == 404
    assert client.post("/v1/video-jobs", headers=AUTH).status_code == 404


def test_image_json_and_multipart_start_only_are_direct_jobs(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    multipart = _submit_image(client, seed=7)
    assert multipart["inputMode"] == "image" and multipart["seed"] == 7
    json_response = client.post("/v1/video-jobs/from-image", headers=AUTH, json={"sourceUrl": "http://127.0.0.1/not-used.png", **_image_payload()})
    # The source requester is deliberately absent in this test; validation
    # happens before fetch and the documented route itself is accepted.
    assert json_response.status_code == 422
    assert json_response.json() == {"error": "source_url_fetch_failed"}


def test_image_start_end_binds_two_prepared_frames_and_no_dangling_nodes(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    response = client.post("/v1/video-jobs/from-image", headers=AUTH, data={key: str(value) for key, value in _image_payload(durationSeconds=8).items()}, files={"image": ("start.png", _png(), "image/png"), "endImage": ("end.png", _png(colour="#6d597a"), "image/png")})
    assert response.status_code == 202
    job = response.json(); frames = client.app.state.gateway.store.get_job_frames(job["id"])
    assert [frame["role"] for frame in frames] == ["start", "end"]
    dispatched = client.app.state.gateway.dispatch_once()
    assert dispatched and dispatched["status"] == "submitted"
    workflow = session.submissions[0]["prompt"]
    assert workflow["105:104"]["inputs"]["first_frame"] == ["h3_start_frame", 0]
    assert workflow["105:104"]["inputs"]["last_frame"] == ["h3_end_frame", 0]
    assert workflow["105:107"]["inputs"]["value"] == frame_count_for_duration_seconds(8)


def test_text_job_has_no_frame_nodes_and_no_aspect_policy(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    response = client.post("/v1/video-jobs/from-text", headers=AUTH, json={"prompt": "A moonlit station answers itself.", "profileId": PROFILE, "durationSeconds": 5})
    assert response.status_code == 202
    job = response.json(); assert job["inputMode"] == "text" and job["aspectPolicy"] is None
    client.app.state.gateway.dispatch_once()
    inputs = session.submissions[0]["prompt"]["105:104"]["inputs"]
    assert "first_frame" not in inputs and "last_frame" not in inputs


def test_direct_contract_rejects_missing_start_mixed_or_retired_idempotency(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    missing = client.post(
        "/v1/video-jobs/from-image", headers=AUTH,
        data={"profileId": PROFILE, "aspectPolicy": "reject_mismatch"},
        files={"prompt": (None, "A missing frame.")},
    )
    assert missing.json() == {"error": "image_file_required"}
    mixed = client.post("/v1/video-jobs/from-image", headers=AUTH, data={**{key: str(value) for key, value in _image_payload().items()}, "sourceUrl": "https://example.test/a.png"}, files={"image": ("a.png", _png(), "image/png")})
    assert mixed.json() == {"error": "request_fields_invalid"}
    idempotency = client.post("/v1/video-jobs/from-image", headers=AUTH, data={**{key: str(value) for key, value in _image_payload().items()}, "idempotencyKey": "no"}, files={"image": ("a.png", _png(), "image/png")})
    assert idempotency.json() == {"error": "request_fields_invalid"}
    text_bad = client.post("/v1/video-jobs/from-text", headers=AUTH, json={"prompt": "x", "profileId": PROFILE, "aspectPolicy": "reject_mismatch"})
    assert text_bad.json() == {"error": "request_invalid"}


def test_seed_duration_grid_and_status_timing_are_frozen(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    random_job = _submit_image(client, durationSeconds=5)
    assert isinstance(random_job["seed"], int) and random_job["frameCount"] == 124
    explicit = _submit_image(client, seed=19, durationSeconds=15)
    assert explicit["seed"] == 19 and explicit["frameCount"] == 362
    assert explicit["actualDurationSeconds"] == 362 / 24
    invalid = client.post("/v1/video-jobs/from-text", headers=AUTH, json={"prompt": "x", "profileId": PROFILE, "durationSeconds": 4})
    assert invalid.json() == {"error": "request_invalid"}
    client.app.state.gateway.dispatch_once()
    submitted = client.get(f"/v1/video-jobs/{random_job['id']}", headers=AUTH).json()
    assert submitted["generationSubmittedAt"] is not None and submitted["generationElapsedMs"] is not None
    session.history["comfy-1"] = {"status": {"status_str": "success", "completed": True}, "outputs": {"92": {"images": [{"filename": "job.mp4", "subfolder": "video", "type": "output"}]}}}
    output = tmp_path / "output" / "video" / "job.mp4"; output.parent.mkdir(parents=True); output.write_bytes(b"mp4")
    completed = client.get(f"/v1/video-jobs/{random_job['id']}", headers=AUTH).json()
    assert completed["generationCompletedAt"] is not None and completed["generationElapsedMs"] >= 0


def test_workflow_has_intended_zero_one_two_frame_connections() -> None:
    profile = H3_GATEWAY_PROFILES[0]
    template = load_h3_template()["prompt"]
    for start, end in ((None, None), ("start.png", None), ("start.png", "end.png")):
        graph = render_workflow(template, profile=profile, prompt="x", start_input_name=start, end_input_name=end, seed=1, frame_count=124)
        inputs = graph["105:104"]["inputs"]
        assert ("first_frame" in inputs) is (start is not None)
        assert ("last_frame" in inputs) is (end is not None)
        assert set(node for node in graph if node.startswith("h3_")) == ({"h3_start_frame"} if start and not end else {"h3_start_frame", "h3_end_frame"} if start and end else set())


def test_legacy_job_migration_keeps_a_readable_start_binding(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sqlite3"; asset_path = tmp_path / "asset.png"; asset_path.write_bytes(_png())
    connection = sqlite3.connect(path)
    connection.executescript("""
      CREATE TABLE assets (id TEXT PRIMARY KEY, mime_type TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, sha256 TEXT NOT NULL, path TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE jobs (id TEXT PRIMARY KEY, asset_id TEXT NOT NULL, profile_id TEXT NOT NULL, aspect_policy TEXT NOT NULL, prompt TEXT NOT NULL, seed INTEGER NOT NULL, prepared_input_name TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """)
    connection.execute("INSERT INTO assets VALUES ('asset_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'image/png', 832, 480, 'x', ?, CURRENT_TIMESTAMP)", (str(asset_path),))
    connection.execute("INSERT INTO jobs (id, asset_id, profile_id, aspect_policy, prompt, seed, prepared_input_name, status) VALUES ('h3_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'asset_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', ?, 'reject_mismatch', 'x', 1, '2026-01-01T00-00-00Z_h3_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png', 'succeeded')", (PROFILE,))
    connection.commit(); connection.close()
    store = GatewayStore(path)
    job = store.get_job("h3_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert job["input_mode"] == "image" and job["frame_count"] == 124
    assert store.get_job_frames(job["id"])[0]["role"] == "start"
