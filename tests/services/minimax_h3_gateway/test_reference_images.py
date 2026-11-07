"""Image-only Ref2VA request and complete final native envelope contracts."""
from __future__ import annotations

import copy
import json
from hashlib import sha256
from io import BytesIO

import pytest
import requests
from fastapi.testclient import TestClient
from PIL import Image

from plotloom_h3_gateway.api import create_app
from plotloom_h3_gateway.contracts import GatewaySettings
from plotloom_h3_gateway.reference_contracts import reference_frame_count
from plotloom_h3_gateway.vae_policy import ADOPTED_VAE_POLICY
from plotloom_h3_gateway.voice_reference import VOICE_MODEL
from tests.services.minimax_h3_gateway.test_voice_reference import _Comfy, _Response, _object_info

AUTH = {"Authorization": "Bearer test-key"}
PROMPT = "  <Picture 1> → <Picture 2> → <Picture 3> → <Picture 4> → <Picture 5>\r\n<d>[Chinese] 还是差两块。</d>\n"


@pytest.fixture(autouse=True)
def _no_live(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("reference tests attempted live HTTP")
    monkeypatch.setattr(requests.Session, "send", refuse)


def object_info():
    info = _object_info()
    node = info["MiniMaxH3ReferenceToVideo"]
    node["output"] = ["CONDITIONING", "LATENT"]
    node["input"]["optional"]["ref_images"] = ["COMFY_AUTOGROW_V3", {"template": {
        "prefix": "ref_image_", "min": 0, "max": 9,
        "input": {"required": {"ref_image": ["IMAGE", {}]}},
    }}]
    info["MiniMaxH3AddGuide"] = {"output": ["CONDITIONING"], "input": {
        "required": {"positive": ["CONDITIONING"], "latent": ["LATENT"], "frame_idx": ["INT"]},
        "optional": {"image": ["IMAGE"], "vae": ["VAE"]},
    }}
    return info


class ReferenceComfy(_Comfy):
    def __init__(self):
        super().__init__()
        self.info = object_info()

    def get(self, url, **kwargs):
        if url.endswith("/health"):
            return _Response({"status": "ok"})
        if url.endswith("/object_info"):
            return _Response(self.info)
        return super().get(url, **kwargs)


def client_for(tmp_path, source_session=None):
    comfy = ReferenceComfy()
    app = create_app(GatewaySettings(api_key="test-key", data_dir=tmp_path/"data",
        comfy_input_dir=tmp_path/"input", comfy_output_dir=tmp_path/"output",
        dispatch_worker_enabled=False), session=comfy, source_session=source_session, qwen_session=comfy)
    return TestClient(app), comfy


def png(index):
    stream = BytesIO()
    Image.new("RGB", (960, 544), (index*20, 70, 100)).save(stream, "PNG")
    return stream.getvalue()


def metadata(count=5):
    times = [0, 2500, 4500, 6800, 9000] if count == 5 else [index*1000 for index in range(count)]
    return {"prompt": PROMPT, "resolution": "960x544", "aspectPolicy": "reject_mismatch",
            "seed": 20261106, "durationMs": 11300, "references": [{"atMs": time} for time in times]}


def post_references(client, value=None, contents=None):
    value = metadata() if value is None else value
    contents = [png(index) for index in range(len(value["references"]))] if contents is None else contents
    return client.post("/v1/video-jobs/from-reference-images", headers=AUTH,
        data={"request": json.dumps(value, ensure_ascii=False)},
        files=[("images", (f"image-{index}.png", content, "image/png")) for index, content in enumerate(contents)])


def expected_graph(template, job, frames):
    """Independent complete transport expectation, including all unchanged nodes."""
    graph = copy.deepcopy(template)
    del graph["105:121"], graph["105:122"]
    graph["105:11"] = {"class_type": "PlotloomH3VideoVAELoader", "inputs": {
        "vae_name": ADOPTED_VAE_POLICY.video_checkpoint, "policy": ADOPTED_VAE_POLICY.policy_id}}
    graph["105:24"] = {"class_type": "VAELoader", "inputs": {"vae_name": ADOPTED_VAE_POLICY.audio_checkpoint}}
    graph["105:6"]["inputs"] = {"unet_name": VOICE_MODEL, "weight_dtype": "default"}
    graph["105:9"]["inputs"] = {"model": ["105:6", 0], "scheduler": "simple", "steps": 20, "denoise": 1.0}
    graph["105:15"]["inputs"] = {"noise_seed": 20261106}
    graph["105:17"]["inputs"] = {"sampler_name": "res_multistep"}
    graph["105:107"]["inputs"] = {"value": 277}
    graph["115"]["inputs"], graph["116"]["inputs"] = {"value": 960}, {"value": 544}
    graph["105:104"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {
        "clip": ["105:13", 0], "vae": ["105:11", 0], "prompt": PROMPT,
        "width": ["115", 0], "height": ["116", 0], "length": ["105:107", 0], "ref_image_size": "match",
        **{f"ref_images.ref_image_{index}": [f"reference_image_{index+1}", 0] for index in range(5)},
    }}
    for index, (frame, at) in enumerate(zip(frames, (0, 60, 108, 163, 216)), 1):
        graph[f"reference_image_{index}"] = {"class_type": "LoadImage", "inputs": {"image": frame["prepared_input_name"]}}
        graph[f"reference_guide_{index}"] = {"class_type": "MiniMaxH3AddGuide", "inputs": {
            "positive": ["105:104", 0] if index == 1 else [f"reference_guide_{index-1}", 0],
            "latent": ["105:104", 1], "vae": ["105:11", 0],
            "image": [f"reference_image_{index}", 0], "frame_idx": at,
        }}
    graph["105:16"]["inputs"] = {"model": ["105:6", 0], "conditioning": ["reference_guide_5", 0]}
    return {"prompt": graph, "client_id": job["id"]}


def test_five_references_preserve_complete_final_envelope_and_restart(tmp_path):
    client, _ = client_for(tmp_path)
    response = post_references(client)
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["inputMode"] == "reference_images"
    assert body["requestedDurationMs"] == 11300 and body["requestedDurationSeconds"] == 11.3
    assert body["frameCount"] == 277 and body["actualDurationSeconds"] == 277/24
    assert [row["frameIndex"] for row in body["references"]] == [0, 60, 108, 163, 216]
    restarted, comfy = client_for(tmp_path)
    gateway = restarted.app.state.gateway
    job = gateway.store.get_job(body["id"])
    frames = gateway.store.get_job_frames(job["id"])
    assert [row["role"] for row in frames] == [f"reference_{index}" for index in range(1, 6)]
    for index, frame in enumerate(frames):
        source = gateway.files.gateway_asset_path(frame)
        prepared = gateway.files.prepared_input_path(job_id=job["id"], frame=frame)
        assert source.read_bytes() == png(index)
        assert sha256(prepared.read_bytes()).hexdigest() == body["references"][index]["preparedSha256"]
        assert source.stat().st_mode & 0o777 == prepared.stat().st_mode & 0o777 == 0o600
    assert gateway.dispatch_once()["status"] == "submitted"
    assert comfy.submissions == [expected_graph(gateway.workflow_template["prompt"], job, frames)]
    assert comfy.submissions[0]["prompt"]["105:104"]["inputs"]["prompt"].encode() == PROMPT.encode()
    status = restarted.get(f"/v1/video-jobs/{job['id']}", headers=AUTH).json()
    assert status["references"] == body["references"]
    assert "test-key" not in json.dumps(job)


@pytest.mark.parametrize("count", [1, 5, 9])
def test_reference_cardinality(tmp_path, count):
    client, _ = client_for(tmp_path)
    assert post_references(client, metadata(count)).status_code == 202


@pytest.mark.parametrize("change", [
    {"references": []}, {"references": [{"atMs": i*500} for i in range(10)]},
    {"references": [{"atMs": 1}]}, {"references": [{"atMs": -1}]},
    {"references": [{"atMs": 0}, {"atMs": 0}]},
    {"references": [{"atMs": 0}, {"atMs": 1}]},
    {"references": [{"atMs": 0}, {"atMs": 11300}]},
    {"references": [{"atMs": 0}, {"atMs": 20.0}]},
    {"references": [{"atMs": 0}, {"atMs": True}]},
    {"references": [{"atMs": 0, "length": 5}]},
    {"durationMs": 5166, "references": [{"atMs": 0}, {"atMs": 5165}]},
    {"durationMs": 11300.1}, {"durationMs": float("inf")},
    {"durationMs": 4999}, {"durationMs": 15001}, {"quality": 8},
    {"voiceAudio": "unsupported"}, {"resolution": "1280x704"},
])
def test_invalid_requests_refuse_before_writes(tmp_path, change):
    client, comfy = client_for(tmp_path)
    response = post_references(client, metadata() | change, [png(0)])
    assert response.status_code in (400, 422), response.text
    gateway = client.app.state.gateway
    assert gateway.store.queue_counts() == (0, 0)
    assert list((tmp_path/"data/assets").iterdir()) == []
    assert list((tmp_path/"input").iterdir()) == []
    assert not comfy.submissions


def test_json_urls_order_and_duplicate_json_field_refusal(tmp_path):
    urls = []
    class Source:
        max_redirects = 0
        def get(self, url, **kwargs):
            urls.append(url)
            return _Response(content=png(int(url.rsplit("/", 1)[1])))
    client, _ = client_for(tmp_path, Source())
    value = metadata()
    for index, item in enumerate(value["references"]):
        item["sourceUrl"] = f"http://fixture.test/{index}"
    response = client.post("/v1/video-jobs/from-reference-images", json=value, headers=AUTH)
    assert response.status_code == 202, response.text
    assert urls == [f"http://fixture.test/{index}" for index in range(5)]
    duplicate = json.dumps(value).replace('"atMs": 0', '"atMs": 0, "atMs": 1', 1)
    assert client.post("/v1/video-jobs/from-reference-images", content=duplicate,
        headers={**AUTH, "Content-Type": "application/json"}).status_code == 422
    assert len(urls) == 5


def test_readiness_is_independent_of_reference_audio(tmp_path):
    client, comfy = client_for(tmp_path)
    del comfy.info["LoadAudio"]
    del comfy.info["MiniMaxH3ReferenceToVideo"]["input"]["optional"]["ref_audios"]
    client.app.state.gateway.comfy.preflight_references(5)
    health = client.get("/health").json()
    assert health["referenceImagesReady"] is True and health["voiceReferenceReady"] is False
    comfy.info["MiniMaxH3ReferenceToVideo"]["input"]["optional"]["ref_images"][1]["template"]["max"] = 4
    assert post_references(client).status_code == 503


def test_fractional_grid_end_is_refused_by_snapshot_validation(tmp_path):
    from plotloom_h3_gateway.reference_execution import reference_execution_from_snapshot
    client, _ = client_for(tmp_path)
    job_id = post_references(client).json()["id"]
    job = client.app.state.gateway.store.get_job(job_id)
    value = json.loads(job["execution_snapshot_json"])
    value["requestedDurationMs"], value["frameCount"] = 5166, reference_frame_count(5166)
    value["references"] = value["references"][:2]
    value["references"][1].update(atMs=5165, frameIndex=124)
    with pytest.raises(ValueError, match="invalid frozen"):
        reference_execution_from_snapshot(json.dumps(value))
