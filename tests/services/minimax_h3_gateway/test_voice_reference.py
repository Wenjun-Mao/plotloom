"""Bounded Ref2VA HTTP, persistence, graph, and retention regression tests."""
from __future__ import annotations

import sqlite3
import wave
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
import requests
from fastapi.testclient import TestClient
from PIL import Image
from plotloom_h3_gateway.api import create_app
from plotloom_h3_gateway.contracts import GatewaySettings
from plotloom_h3_gateway.profile_catalog import (
    admitted_execution,
    frame_count_for_duration_seconds,
)
from plotloom_h3_gateway.store import _CURRENT_SCHEMA, GatewayStore

AUTH = {"Authorization": "Bearer test-key"}
PROMPT = "<Picture 1> is the first frame. <Audio 1> is voice timbre only. <d>[Chinese] 一枚，只够一边。</d>"


def _wav(*, seconds: int = 8, rate: int = 32_000, channels: int = 1) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(b"\0\0" * rate * seconds * channels)
    return buffer.getvalue()


def _png(width: int = 576, height: int = 1024) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "#435166").save(buffer, "PNG")
    return buffer.getvalue()


class _Response:
    def __init__(self, data: object = None, content: bytes | None = None) -> None:
        self.data = data
        self.content = content
        self.headers = {"Content-Length": str(len(content))} if content is not None else {}

    def json(self) -> object:
        return self.data

    def raise_for_status(self) -> None:
        pass

    def iter_content(self, chunk_size: int) -> list[bytes]:
        return [self.content or b""]

    def close(self) -> None:
        pass


class _Comfy:
    def __init__(self) -> None:
        self.submissions: list[dict[str, Any]] = []

    def get(self, url: str, **_: object) -> _Response:
        if url.endswith("/queue"):
            return _Response({"queue_running": [], "queue_pending": []})
        if url.endswith("/system_stats"):
            return _Response({"system": {}})
        if url.endswith("/object_info"):
            return _Response(_object_info())
        if "/history/" in url:
            return _Response({})
        raise AssertionError(url)

    def post(self, url: str, *, json: dict[str, Any], **_: object) -> _Response:
        assert url.endswith("/prompt")
        self.submissions.append(json)
        return _Response({"prompt_id": f"comfy-{len(self.submissions)}"})


def _object_info() -> dict[str, Any]:
    result = {
        "UNETLoader": {"input": {"required": {"unet_name": [[
            "minimax_h3_fl2va_pruned_fp8_scaled.safetensors",
            "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
        ]]}}},
        "CLIPLoader": {"input": {"required": {"clip_name": [["qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"]]}}},
        "VAELoader": {"input": {"required": {"vae_name": [[
            "minimax_h3_video_vae_fp16.safetensors", "minimax_h3_audio_vae_fp32.safetensors",
        ]]}}},
        "MiniMaxH3ReferenceToVideo": {"input": {"optional": {
            "ref_audios": ["COMFY_AUTOGROW_V3"], "ref_images": ["COMFY_AUTOGROW_V3"],
        }}},
        "MiniMaxH3ImageToVideo": {"input": {"optional": {
            "first_frame": ["IMAGE"], "last_frame": ["IMAGE"],
        }}},
        "LoraLoaderModelOnly": {"input": {"required": {"lora_name": [[
            "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
            "minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16.safetensors",
            "minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors",
        ]]}}},
    }
    for name in ("MiniMaxH3AddGuide", "LoadImage", "LoadAudio", "PrimitiveInt", "KSamplerSelect",
                 "BasicScheduler", "BasicGuider", "SamplerCustomAdvanced", "MiniMaxH3SigmaShift"):
        result[name] = {"input": {"required": {}}}
    return result


def _client(tmp_path: Path, *, source_session: object | None = None) -> tuple[TestClient, _Comfy]:
    comfy = _Comfy()
    app = create_app(
        GatewaySettings(
            api_key="test-key", data_dir=tmp_path / "data", comfy_input_dir=tmp_path / "input",
            comfy_output_dir=tmp_path / "output", dispatch_worker_enabled=False,
        ), session=comfy, source_session=source_session,
    )
    return TestClient(app), comfy


def _post_voice(client: TestClient, *, audio: bytes | None = None, **fields: object):
    return client.post(
        "/v1/video-jobs/from-image-with-voice", headers=AUTH,
        data={"prompt": PROMPT, "resolution": "576x1024", "aspectPolicy": "reject_mismatch",
              **{key: str(value) for key, value in fields.items()}},
        files={"image": ("portrait.png", _png(), "image/png"),
               "voiceAudio": ("voice.wav", audio if audio is not None else _wav(), "audio/wav")},
    )


def test_voice_multipart_admission_and_frozen_ref2va_graph(tmp_path: Path) -> None:
    client, comfy = _client(tmp_path)
    submitted = _post_voice(client, seed=20260923)
    assert submitted.status_code == 202, submitted.text
    body = submitted.json()
    assert body["inputMode"] == "image_voice" and body["quality"] == 8
    assert body["voiceReferenceSha256"] == sha256(_wav()).hexdigest()
    assert body["frameCount"] == frame_count_for_duration_seconds(5)
    gateway = client.app.state.gateway
    job = gateway.store.get_job(body["id"])
    assert job["input_mode"] == "image" and job["h3_contract"] == "ref2va"
    assert gateway.store.get_job_voice(body["id"])["source_sha256"] == body["voiceReferenceSha256"]
    assert [frame["role"] for frame in gateway.store.get_job_frames(body["id"])] == ["start"]
    assert "voiceReferenceSha256" not in client.get(f"/v1/video-jobs/{body['id']}", headers=AUTH).json()
    assert gateway.dispatch_once()["status"] == "submitted"
    graph = comfy.submissions[0]["prompt"]
    assert graph["105:6"]["inputs"]["unet_name"] == "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
    assert graph["105:104"]["class_type"] == "MiniMaxH3ReferenceToVideo"
    assert graph["105:104"]["inputs"]["ref_audios.ref_audio_0"] == ["voice_reference_audio", 0]
    assert graph["105:104"]["inputs"]["ref_images.ref_image_0"] == ["voice_first_frame_image", 0]
    assert graph["voice_first_frame_guide"]["inputs"]["frame_idx"] == 0
    assert graph["105:9"]["inputs"]["steps"] == 20
    assert "105:121" not in graph and "105:122" not in graph
    assert graph["105:107"]["inputs"]["value"] == 124


def test_voice_eight_second_portrait_survives_restart_and_tamper_fails_closed(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    submitted = _post_voice(client, durationSeconds=8)
    assert submitted.status_code == 202
    job_id = submitted.json()["id"]
    restarted, comfy = _client(tmp_path)
    gateway = restarted.app.state.gateway
    assert gateway.store.get_job(job_id)["status"] == "queued"
    binding = gateway.store.get_job_voice(job_id)
    assert binding is not None
    prepared = gateway.voice_files.prepared_path(job_id, binding)
    assert prepared is not None
    prepared.write_bytes(b"tampered")
    failed = gateway.dispatch_once()
    assert failed["status"] == "failed" and failed["error_code"] == "voice_input_integrity_mismatch"
    assert comfy.submissions == []


def test_voice_queued_snapshot_does_not_resolve_against_mutated_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = _client(tmp_path)
    job_id = _post_voice(client, durationSeconds=8).json()["id"]
    from plotloom_h3_gateway import voice_reference

    monkeypatch.setattr(voice_reference, "VOICE_RESOLUTIONS", {})
    restarted, comfy = _client(tmp_path)
    result = restarted.app.state.gateway.dispatch_once()
    assert result["id"] == job_id and result["status"] == "submitted"
    assert comfy.submissions[0]["prompt"]["105:107"]["inputs"]["value"] == frame_count_for_duration_seconds(8)


def test_voice_unknown_submission_is_not_replayed(tmp_path: Path) -> None:
    client, comfy = _client(tmp_path)
    job_id = _post_voice(client).json()["id"]

    def uncertain_post(*_: object, **__: object) -> None:
        raise requests.RequestException("response lost after send")

    comfy.post = uncertain_post  # type: ignore[method-assign]
    gateway = client.app.state.gateway
    result = gateway.dispatch_once()
    assert result["id"] == job_id and result["status"] == "outcome_unknown"
    assert gateway.dispatch_once() is None


@pytest.mark.parametrize("fields", [
    {"quality": "8"}, {"endImage": "no"}, {"sourceUrl": "http://example.test/a.png"},
    {"profileId": "old"}, {"durationSeconds": "9"}, {"resolution": "704x1280"},
])
def test_voice_route_rejects_unadmitted_fields_and_geometry(tmp_path: Path, fields: dict[str, str]) -> None:
    client, _ = _client(tmp_path)
    response = _post_voice(client, **fields)
    assert response.status_code == 422
    assert client.app.state.gateway.store.queue_counts() == (0, 0)


@pytest.mark.parametrize("audio", [b"not wav", _wav(rate=44_100), _wav(channels=2), _wav(seconds=11)])
def test_voice_audio_rejections_leave_no_files_or_jobs(tmp_path: Path, audio: bytes) -> None:
    client, _ = _client(tmp_path)
    response = _post_voice(client, audio=audio)
    assert response.status_code == 422
    assert client.app.state.gateway.store.queue_counts() == (0, 0)
    assert list((tmp_path / "data" / "assets").iterdir()) == []
    assert list((tmp_path / "data" / "voice_inputs").iterdir()) == []


def test_partial_voice_storage_failure_rolls_back_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _client(tmp_path)
    gateway = client.app.state.gateway

    def unavailable(*_: object, **__: object) -> None:
        from plotloom_h3_gateway.contracts import GatewayError

        raise GatewayError("voice_storage_failed", 500)

    monkeypatch.setattr(gateway.voice_files, "prepare", unavailable)
    response = _post_voice(client)
    assert response.status_code == 500
    assert list((tmp_path / "data" / "assets").iterdir()) == []
    assert list((tmp_path / "input").iterdir()) == []
    assert gateway.store.queue_counts() == (0, 0)


def test_voice_url_form_uses_bounded_fetch_and_mixed_inputs_reject(tmp_path: Path) -> None:
    class Source:
        max_redirects = 0

        def get(self, url: str, **_: object) -> _Response:
            return _Response(content=_png() if url.endswith("image.png") else _wav())

    client, _ = _client(tmp_path, source_session=Source())
    response = client.post("/v1/video-jobs/from-image-with-voice", headers=AUTH, json={
        "sourceUrl": "http://example.test/image.png", "voiceSourceUrl": "http://example.test/voice.wav",
        "prompt": PROMPT, "resolution": "576x1024", "aspectPolicy": "reject_mismatch",
    })
    assert response.status_code == 202, response.text
    mixed = client.post("/v1/video-jobs/from-image-with-voice", headers=AUTH, json={
        "sourceUrl": "http://example.test/image.png", "voiceAudio": "bytes",
        "voiceSourceUrl": "http://example.test/voice.wav", "prompt": PROMPT,
        "resolution": "576x1024", "aspectPolicy": "reject_mismatch",
    })
    assert mixed.status_code == 422


def test_voice_files_release_at_output_expiry_but_hash_binding_survives(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    job_id = _post_voice(client).json()["id"]
    gateway = client.app.state.gateway
    voice = gateway.store.get_job_voice(job_id)
    frame = gateway.store.get_job_frames(job_id)[0]
    assert voice is not None
    source_path = gateway.voice_files.source_path(job_id, voice)
    audio_path = gateway.voice_files.prepared_path(job_id, voice)
    image_path = gateway.files.prepared_input_path(job_id=job_id, frame=frame)
    assert all(path is not None and path.is_file() for path in (source_path, audio_path, image_path))
    gateway.store.update_job(job_id, status="succeeded", output_expires_at="2000-01-01 00:00:00")
    gateway.voice_files.cleanup_due()
    assert all(path is not None and not path.exists() for path in (source_path, audio_path, image_path))
    retained = gateway.store.get_job_voice(job_id)
    assert retained is not None and retained["released_at"] is not None
    assert retained["source_sha256"] == sha256(_wav()).hexdigest()


def test_queued_voice_inputs_are_not_pruned_at_day_thirty(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    job_id = _post_voice(client).json()["id"]
    gateway = client.app.state.gateway
    frame = gateway.store.get_job_frames(job_id)[0]
    asset_path = gateway.files.gateway_asset_path(frame)
    voice = gateway.store.get_job_voice(job_id)
    assert asset_path is not None and voice is not None
    with sqlite3.connect(gateway.store._path) as connection:
        connection.execute("UPDATE jobs SET created_at = '2000-01-01 00:00:00' WHERE id = ?", (job_id,))
        connection.execute("UPDATE assets SET created_at = '2000-01-01 00:00:00' WHERE id = ?", (frame["asset_id"],))
    gateway.cleanup_expired_gateway_keyframes()
    assert asset_path.is_file()
    assert gateway.voice_files.prepared_path(job_id, voice).is_file()
    gateway.cancel_job(job_id)
    gateway.cleanup_expired_gateway_keyframes()
    assert not asset_path.exists()
    assert gateway.store.get_job_voice(job_id)["released_at"] is not None


def test_existing_database_adds_voice_binding_without_rewriting_queued_fl2va(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    old_schema = _CURRENT_SCHEMA.replace(
        "  h3_contract TEXT NOT NULL DEFAULT 'fl2va' CHECK(h3_contract IN ('fl2va', 'ref2va')),\n", ""
    )
    with sqlite3.connect(path) as connection:
        connection.executescript(old_schema)
        snapshot = admitted_execution(quality=1, resolution="576x1024").snapshot_json()
        connection.execute(
            """INSERT INTO jobs (id, backend, input_mode, quality, resolution,
               execution_snapshot_json, prompt, seed, requested_duration_seconds,
               frame_count, fps, status) VALUES (?, 'h3_video', 'image', 1, '576x1024',
               ?, 'old prompt', 1, 5, 124, 24, 'queued')""",
            ("h3_" + "a" * 32, snapshot),
        )
    store = GatewayStore(path)
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)")}
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "h3_contract" in columns and "job_voice_bindings" in tables
    old_job = store.get_job("h3_" + "a" * 32)
    assert old_job["execution_snapshot_json"] == snapshot
    assert old_job["h3_contract"] == "fl2va" and old_job["status"] == "queued"
    assert store.get_job_voice(old_job["id"]) is None
