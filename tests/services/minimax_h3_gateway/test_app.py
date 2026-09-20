"""Direct H3 job contract, workflow, timing, and migration coverage."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import requests
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from plotloom_h3_gateway.app import GatewaySettings, GatewayStore, create_app
from plotloom_h3_gateway.profile_catalog import (
    QUALITY_RECIPES,
    RESOLUTIONS,
    admitted_execution,
    frame_count_for_duration_seconds,
)
from plotloom_h3_gateway.workflow import load_h3_template, render_workflow


RESOLUTION = "832x480"
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


class _UncertainSubmitSession(_ComfySession):
    """Model a transport loss after an outbound Comfy submission attempt."""

    def __init__(self) -> None:
        super().__init__()
        self.submit_attempts = 0

    def post(self, url: str, *, json: dict[str, Any], **_: object) -> _Response:
        assert url.endswith("/prompt")
        self.submit_attempts += 1
        raise requests.RequestException("offline fixture lost the submission response")


def _object_info() -> dict[str, object]:
    result: dict[str, object] = {
        "MiniMaxH3ImageToVideo": {"input": {"optional": {"first_frame": ["IMAGE"], "last_frame": ["IMAGE"]}}},
        "PrimitiveInt": {},
    }
    for node, field, values in (
        ("UNETLoader", "unet_name", ["minimax_h3_fl2va_pruned_fp8_scaled.safetensors"]),
        ("CLIPLoader", "clip_name", ["qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"]),
        ("VAELoader", "vae_name", ["minimax_h3_video_vae_fp16.safetensors", "minimax_h3_audio_vae_fp32.safetensors"]),
        ("LoraLoaderModelOnly", "lora_name", [
            "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
            "minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors",
            "minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors",
        ]),
    ):
        result[node] = {"input": {"required": {field: [values]}}}
    for node in (
        "MiniMaxH3SigmaShift", "KSamplerSelect", "BasicScheduler",
        "BasicGuider", "SamplerCustomAdvanced",
    ):
        result[node] = {"input": {"required": {}}}
    return result


def _client(tmp_path: Path) -> tuple[TestClient, _ComfySession]:
    session = _ComfySession()
    return TestClient(create_app(GatewaySettings(api_key="test-key", data_dir=tmp_path / "data", comfy_input_dir=tmp_path / "input", comfy_output_dir=tmp_path / "output", dispatch_worker_enabled=False), session=session)), session


def _png(width: int = 832, height: int = 480, colour: str = "#355070") -> bytes:
    image = Image.new("RGB", (width, height), colour)
    buffer = BytesIO(); image.save(buffer, "PNG")
    return buffer.getvalue()


def _image_payload(**extra: object) -> dict[str, object]:
    return {"prompt": "A pilot pauses at the airlock.", "resolution": RESOLUTION, "aspectPolicy": "reject_mismatch", **extra}


def _submit_image(client: TestClient, **extra: object) -> dict[str, Any]:
    response = client.post("/v1/video-jobs/from-image", headers=AUTH, data={key: str(value) for key, value in _image_payload(**extra).items()}, files={"image": ("start.png", _png(), "image/png")})
    assert response.status_code == 202, response.text
    return response.json()


def test_gateway_catalog_exposes_only_reviewed_quality_and_resolution_choices() -> None:
    assert sorted(QUALITY_RECIPES) == [1, 2, 3, 8]
    assert [item.value for item in RESOLUTIONS] == ["832x480", "960x544", "1280x704", "576x1024", "608x1088", "704x1280"]


def test_retired_creation_routes_are_not_registered(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    assert client.post("/v1/assets", headers=AUTH).status_code == 404
    assert client.post("/v1/video-jobs", headers=AUTH).status_code == 404


def test_retired_profile_id_is_not_part_of_the_new_contract(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    response = client.post(
        "/v1/video-jobs/from-text", headers=AUTH,
        json={"prompt": "No old selection field.", "profileId": "retired_profile", "resolution": RESOLUTION},
    )
    assert response.status_code == 422
    assert response.json() == {"error": "request_invalid"}


def test_image_json_and_multipart_start_only_are_direct_jobs(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    multipart = _submit_image(client, seed=7)
    assert multipart["inputMode"] == "image" and multipart["seed"] == 7
    json_response = client.post("/v1/video-jobs/from-image", headers=AUTH, json={"sourceUrl": "http://127.0.0.1/not-used.png", **_image_payload()})
    # The source requester is deliberately absent in this test; validation
    # happens before fetch and the documented route itself is accepted.
    assert json_response.status_code == 422
    assert json_response.json() == {"error": "source_url_fetch_failed"}


def test_quality_defaults_to_one_and_status_never_returns_profile_id(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    job = _submit_image(client)
    assert job["quality"] == 1 and job["resolution"] == RESOLUTION
    assert "profileId" not in job


def test_every_quality_and_resolution_is_admitted_on_both_routes(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    for quality in sorted(QUALITY_RECIPES):
        for resolution in RESOLUTIONS:
            text = client.post(
                "/v1/video-jobs/from-text", headers=AUTH,
                json={"prompt": "A bounded quality check.", "quality": quality, "resolution": resolution.value},
            )
            assert text.status_code == 202, text.text
            width, height = resolution.width, resolution.height
            image = client.post(
                "/v1/video-jobs/from-image", headers=AUTH,
                data={"prompt": "A bounded quality check.", "quality": str(quality), "resolution": resolution.value, "aspectPolicy": "reject_mismatch"},
                files={"image": ("start.png", _png(width, height), "image/png")},
            )
            assert image.status_code == 202, image.text
            assert image.json()["quality"] == quality
            assert image.json()["resolution"] == resolution.value


def test_unknown_quality_resolution_and_profile_id_are_rejected(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    for payload, code in (
        ({"prompt": "x", "quality": 4, "resolution": RESOLUTION}, "quality_not_supported"),
        ({"prompt": "x", "resolution": "768x768"}, "resolution_not_supported"),
        ({"prompt": "x", "resolution": RESOLUTION, "profileId": "old"}, "request_invalid"),
    ):
        response = client.post("/v1/video-jobs/from-text", headers=AUTH, json=payload)
        assert response.json() == {"error": code}


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
    response = client.post("/v1/video-jobs/from-text", headers=AUTH, json={"prompt": "A moonlit station answers itself.", "resolution": RESOLUTION, "durationSeconds": 5})
    assert response.status_code == 202
    job = response.json(); assert job["inputMode"] == "text" and job["aspectPolicy"] is None
    client.app.state.gateway.dispatch_once()
    inputs = session.submissions[0]["prompt"]["105:104"]["inputs"]
    assert "first_frame" not in inputs and "last_frame" not in inputs


def test_direct_contract_rejects_missing_start_mixed_or_retired_idempotency(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    missing = client.post(
        "/v1/video-jobs/from-image", headers=AUTH,
        data={"resolution": RESOLUTION, "aspectPolicy": "reject_mismatch"},
        files={"prompt": (None, "A missing frame.")},
    )
    assert missing.json() == {"error": "image_file_required"}
    mixed = client.post("/v1/video-jobs/from-image", headers=AUTH, data={**{key: str(value) for key, value in _image_payload().items()}, "sourceUrl": "https://example.test/a.png"}, files={"image": ("a.png", _png(), "image/png")})
    assert mixed.json() == {"error": "request_fields_invalid"}
    idempotency = client.post("/v1/video-jobs/from-image", headers=AUTH, data={**{key: str(value) for key, value in _image_payload().items()}, "idempotencyKey": "no"}, files={"image": ("a.png", _png(), "image/png")})
    assert idempotency.json() == {"error": "request_fields_invalid"}
    text_bad = client.post("/v1/video-jobs/from-text", headers=AUTH, json={"prompt": "x", "resolution": RESOLUTION, "aspectPolicy": "reject_mismatch"})
    assert text_bad.json() == {"error": "request_invalid"}


def test_seed_duration_grid_and_status_timing_are_frozen(tmp_path: Path) -> None:
    client, session = _client(tmp_path)
    random_job = _submit_image(client, durationSeconds=5)
    assert isinstance(random_job["seed"], int) and random_job["frameCount"] == 124
    explicit = _submit_image(client, seed=19, durationSeconds=15)
    assert explicit["seed"] == 19 and explicit["frameCount"] == 362
    assert explicit["actualDurationSeconds"] == 362 / 24
    invalid = client.post("/v1/video-jobs/from-text", headers=AUTH, json={"prompt": "x", "resolution": RESOLUTION, "durationSeconds": 4})
    assert invalid.json() == {"error": "request_invalid"}
    client.app.state.gateway.dispatch_once()
    submitted = client.get(f"/v1/video-jobs/{random_job['id']}", headers=AUTH).json()
    assert submitted["generationSubmittedAt"] is not None and submitted["generationElapsedMs"] is not None
    session.history["comfy-1"] = {"status": {"status_str": "success", "completed": True}, "outputs": {"92": {"images": [{"filename": "job.mp4", "subfolder": "video", "type": "output"}]}}}
    output = tmp_path / "output" / "video" / "job.mp4"; output.parent.mkdir(parents=True); output.write_bytes(b"mp4")
    completed = client.get(f"/v1/video-jobs/{random_job['id']}", headers=AUTH).json()
    assert completed["generationCompletedAt"] is not None and completed["generationElapsedMs"] >= 0


def test_workflow_has_intended_zero_one_two_frame_connections() -> None:
    execution = admitted_execution(quality=1, resolution=RESOLUTION)
    template = load_h3_template()["prompt"]
    for start, end in ((None, None), ("start.png", None), ("start.png", "end.png")):
        graph = render_workflow(template, execution=execution, prompt="x", start_input_name=start, end_input_name=end, seed=1, frame_count=124)
        inputs = graph["105:104"]["inputs"]
        assert ("first_frame" in inputs) is (start is not None)
        assert ("last_frame" in inputs) is (end is not None)
        assert set(node for node in graph if node.startswith("h3_")) == ({"h3_start_frame"} if start and not end else {"h3_start_frame", "h3_end_frame"} if start and end else set())


def test_workflow_renders_the_complete_corrected_sampling_recipe() -> None:
    execution = admitted_execution(quality=1, resolution=RESOLUTION)
    graph = render_workflow(
        load_h3_template()["prompt"], execution=execution, prompt="x",
        start_input_name=None, end_input_name=None, seed=1, frame_count=124,
    )
    assert graph["105:121"]["inputs"] == {
        "lora_name": "minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors",
        "strength_model": 1.0, "model": ["105:6", 0],
    }
    assert graph["105:122"]["class_type"] == "MiniMaxH3SigmaShift"
    assert graph["105:122"]["inputs"] == {
        "model": ["105:121", 0], "shift_video": 6.0, "shift_audio": 3.0,
    }
    assert graph["105:9"]["inputs"] == {
        "scheduler": "simple", "steps": 4, "denoise": 1.0, "model": ["105:122", 0],
    }
    assert graph["105:17"]["inputs"]["sampler_name"] == "euler"


@pytest.mark.parametrize("quality", [1, 2, 3])
def test_turbo_workflows_have_their_reviewed_lora_and_explicit_shifts(quality: int) -> None:
    execution = admitted_execution(quality=quality, resolution=RESOLUTION)
    graph = render_workflow(
        load_h3_template()["prompt"], execution=execution, prompt="x",
        start_input_name=None, end_input_name=None, seed=1, frame_count=124,
    )
    assert graph["105:121"]["inputs"]["lora_name"] == execution.recipe.lora_file
    assert graph["105:122"]["inputs"]["shift_video"] == 6.0
    assert graph["105:122"]["inputs"]["shift_audio"] == 3.0
    assert graph["105:9"]["inputs"]["steps"] == execution.recipe.inference_steps
    assert graph["105:17"]["inputs"]["sampler_name"] == execution.recipe.sampler


def test_base20_workflow_has_no_turbo_nodes_or_shift_override() -> None:
    execution = admitted_execution(quality=8, resolution=RESOLUTION)
    graph = render_workflow(
        load_h3_template()["prompt"], execution=execution, prompt="x",
        start_input_name=None, end_input_name=None, seed=1, frame_count=124,
    )
    assert "105:121" not in graph and "105:122" not in graph
    assert graph["105:9"]["inputs"]["model"] == ["105:6", 0]
    assert graph["105:16"]["inputs"]["model"] == ["105:6", 0]
    assert graph["105:9"]["inputs"]["steps"] == 20


def test_dispatch_uses_frozen_snapshot_not_the_live_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, session = _client(tmp_path)
    job = client.post(
        "/v1/video-jobs/from-text", headers=AUTH,
        json={"prompt": "A frozen quality-two request.", "quality": 2, "resolution": RESOLUTION},
    ).json()
    import plotloom_h3_gateway.gateway as gateway_module
    monkeypatch.setattr(gateway_module, "admitted_execution", lambda **_: (_ for _ in ()).throw(AssertionError("live catalog used")))
    dispatched = client.app.state.gateway.dispatch_once()
    assert dispatched is not None and dispatched["id"] == job["id"]
    workflow = session.submissions[0]["prompt"]
    assert workflow["105:9"]["inputs"]["steps"] == 4
    assert workflow["105:17"]["inputs"]["sampler_name"] == "res_multistep"


def test_retired_gateway_state_requires_an_operator_reset(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sqlite3"; asset_path = tmp_path / "asset.png"; asset_path.write_bytes(_png())
    import sqlite3
    connection = sqlite3.connect(path)
    connection.executescript("""
      CREATE TABLE assets (id TEXT PRIMARY KEY, mime_type TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, sha256 TEXT NOT NULL, path TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
      CREATE TABLE jobs (id TEXT PRIMARY KEY, asset_id TEXT NOT NULL, profile_id TEXT NOT NULL, aspect_policy TEXT NOT NULL, prompt TEXT NOT NULL, seed INTEGER NOT NULL, prepared_input_name TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """)
    connection.execute("INSERT INTO assets VALUES ('asset_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'image/png', 832, 480, 'x', ?, CURRENT_TIMESTAMP)", (str(asset_path),))
    connection.execute("INSERT INTO jobs (id, asset_id, profile_id, aspect_policy, prompt, seed, prepared_input_name, status) VALUES ('h3_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'asset_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'retired_profile', 'reject_mismatch', 'x', 1, '2026-01-01T00-00-00Z_h3_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png', 'succeeded')")
    connection.commit(); connection.close()
    import pytest
    with pytest.raises(RuntimeError, match="state reset required"):
        GatewayStore(path)
    with sqlite3.connect(path) as preserved:
        tables = {row[0] for row in preserved.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert tables == {"assets", "jobs"}


def test_gateway_fifo_dispatch_skips_cancelled_jobs_and_never_overtakes_active_work(
    tmp_path: Path,
) -> None:
    client, session = _client(tmp_path)
    first = _submit_image(client, seed=1)
    cancelled = _submit_image(client, seed=2)
    last = _submit_image(client, seed=3)

    cancellation = client.post(f"/v1/video-jobs/{cancelled['id']}/cancel", headers=AUTH)
    assert cancellation.status_code == 200
    assert cancellation.json()["status"] == "cancelled"
    assert cancellation.json()["error"] == "cancelled_while_queued"

    gateway = client.app.state.gateway
    submitted = gateway.dispatch_once()
    assert submitted is not None and submitted["id"] == first["id"]
    assert [item["client_id"] for item in session.submissions] == [first["id"]]
    assert gateway.dispatch_once() is None
    assert [item["client_id"] for item in session.submissions] == [first["id"]]

    session.history["comfy-1"] = {
        "status": {"status_str": "success", "completed": True},
        "outputs": {"92": {"images": [{"filename": "first.mp4", "subfolder": "video", "type": "output"}]}},
    }
    source = tmp_path / "output" / "video" / "first.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"first-completed-fixture")
    next_submitted = gateway.dispatch_once()
    assert next_submitted is not None and next_submitted["id"] == last["id"]
    assert [item["client_id"] for item in session.submissions] == [first["id"], last["id"]]


def test_gateway_restart_and_uncertain_submit_never_replay_claimed_work(tmp_path: Path) -> None:
    client, _session = _client(tmp_path)
    interrupted = _submit_image(client, seed=4)
    waiting = _submit_image(client, seed=5)
    assert client.app.state.gateway.store.claim_next_queued()["id"] == interrupted["id"]
    client.close()

    resumed_session = _ComfySession()
    settings = GatewaySettings(
        api_key="test-key",
        data_dir=tmp_path / "data",
        comfy_input_dir=tmp_path / "input",
        comfy_output_dir=tmp_path / "output",
        dispatch_worker_enabled=False,
    )
    resumed = TestClient(create_app(settings, session=resumed_session))
    recovered = resumed.get(f"/v1/video-jobs/{interrupted['id']}", headers=AUTH)
    assert recovered.json()["status"] == "outcome_unknown"
    assert recovered.json()["error"] == "gateway_restart_before_known_submission"
    next_submitted = resumed.app.state.gateway.dispatch_once()
    assert next_submitted is not None and next_submitted["id"] == waiting["id"]
    assert [item["client_id"] for item in resumed_session.submissions] == [waiting["id"]]

    uncertain_session = _UncertainSubmitSession()
    uncertain_settings = GatewaySettings(
        api_key="test-key",
        data_dir=tmp_path / "uncertain-data",
        comfy_input_dir=tmp_path / "uncertain-input",
        comfy_output_dir=tmp_path / "uncertain-output",
        dispatch_worker_enabled=False,
    )
    uncertain = TestClient(create_app(uncertain_settings, session=uncertain_session))
    unknown = _submit_image(uncertain, seed=6)
    result = uncertain.app.state.gateway.dispatch_once()
    assert result is not None and result["status"] == "outcome_unknown"
    assert result["error_code"] == "submit_outcome_unknown"
    assert uncertain_session.submit_attempts == 1
    assert uncertain.app.state.gateway.dispatch_once() is None
    assert uncertain_session.submit_attempts == 1


def test_gateway_expired_output_cleanup_preserves_unrelated_files_and_never_regenerates(
    tmp_path: Path,
) -> None:
    client, session = _client(tmp_path)
    job = _submit_image(client, seed=7)
    assert client.app.state.gateway.dispatch_once()["status"] == "submitted"
    session.history["comfy-1"] = {
        "status": {"status_str": "success", "completed": True},
        "outputs": {"92": {"images": [{"filename": "retained.mp4", "subfolder": "video", "type": "output"}]}},
    }
    source = tmp_path / "output" / "video" / "retained.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"managed-output-fixture")
    completed = client.get(f"/v1/video-jobs/{job['id']}", headers=AUTH)
    assert completed.json()["status"] == "succeeded"
    stored = client.app.state.gateway.store.get_job(job["id"])
    managed = tmp_path / "data" / "outputs" / str(stored["managed_output_name"])
    unrelated = tmp_path / "data" / "outputs" / "unrelated.mp4"
    assert managed.is_file()
    unrelated.write_bytes(b"must-survive")
    with client.app.state.gateway.store._connect() as connection:
        connection.execute(
            "UPDATE jobs SET output_expires_at = datetime('now', '-1 second') WHERE id = ?",
            (job["id"],),
        )

    assert client.app.state.gateway.cleanup_expired_outputs() == 1
    assert not managed.exists()
    assert unrelated.read_bytes() == b"must-survive"
    expired = client.get(f"/v1/video-jobs/{job['id']}/output", headers=AUTH)
    assert expired.status_code == 410
    assert expired.json() == {"error": "gateway_output_expired"}
    assert len(session.submissions) == 1
