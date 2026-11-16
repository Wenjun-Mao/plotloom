"""Optional multi-voice public contract and complete native transport fidelity."""
import copy
import json
import wave
from hashlib import sha256
from io import BytesIO

import pytest

from plotloom_h3_gateway.dashboard.reader import DashboardReader
from plotloom_h3_gateway.reference_audio_store import bindings
from plotloom_h3_gateway.vae_policy import ADOPTED_VAE_POLICY
from plotloom_h3_gateway.voice_reference import VOICE_MODEL
from tests.services.minimax_h3_gateway.test_reference_images import (
    AUTH, PROMPT, _Response, client_for, metadata, png,
)
from tests.services.minimax_h3_gateway.test_reference_images import _no_live as _no_live

pytestmark = pytest.mark.usefixtures("_no_live")


def wav(index):
    stream = BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(32000)
        audio.writeframes((index + 1).to_bytes(2, "little") * 32000)
    return stream.getvalue()


def enable_audio(comfy):
    optional = comfy.info["MiniMaxH3ReferenceToVideo"]["input"]["optional"]
    optional["audio_vae"] = ["VAE"]
    optional["ref_audios"] = ["COMFY_AUTOGROW_V3", {"template": {
        "prefix": "ref_audio_", "min": 0, "max": 3,
        "input": {"required": {"ref_audio": ["AUDIO", {}]}},
    }}]


def audio_client(tmp_path):
    client, comfy = client_for(tmp_path)
    enable_audio(comfy)
    return client, comfy


def post_audio(client, count=3, image_count=1, *, value=None, audios=None):
    value = metadata(image_count) | {"audioReferences": [
        {"speaker": f"Character {index+1}"} for index in range(count)]} if value is None else value
    files = [("images", (f"image-{index}.png", png(index), "image/png"))
             for index in range(len(value["references"]))]
    files += [("audios", (f"voice-{index}.wav", content, "audio/wav"))
              for index, content in enumerate([wav(i) for i in range(count)] if audios is None else audios)]
    return client.post("/v1/video-jobs/from-reference-images", headers=AUTH,
                       data={"request": json.dumps(value)}, files=files)


def expected_envelope(template, job, frames, voices):
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
    inputs = {"clip": ["105:13", 0], "vae": ["105:11", 0], "prompt": PROMPT,
              "width": ["115", 0], "height": ["116", 0], "length": ["105:107", 0], "ref_image_size": "match"}
    for index, frame in enumerate(frames, 1):
        inputs[f"ref_images.ref_image_{index-1}"] = [f"reference_image_{index}", 0]
        graph[f"reference_image_{index}"] = {"class_type": "LoadImage", "inputs": {"image": frame["prepared_input_name"]}}
        graph[f"reference_guide_{index}"] = {"class_type": "MiniMaxH3AddGuide", "inputs": {
            "positive": ["105:104", 0] if index == 1 else [f"reference_guide_{index-1}", 0],
            "latent": ["105:104", 1], "vae": ["105:11", 0], "image": [f"reference_image_{index}", 0],
            "frame_idx": (index-1)*24}}
    if voices:
        inputs["audio_vae"] = ["105:24", 0]
    for index, voice in enumerate(voices, 1):
        inputs[f"ref_audios.ref_audio_{index-1}"] = [f"reference_audio_{index}", 0]
        graph[f"reference_audio_{index}"] = {"class_type": "LoadAudio", "inputs": {"audio": voice["prepared_input_name"]}}
    graph["105:104"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": inputs}
    graph["105:16"]["inputs"] = {"model": ["105:6", 0], "conditioning": [f"reference_guide_{len(frames)}", 0]}
    return {"prompt": graph, "client_id": job["id"]}


@pytest.mark.parametrize("mode", ["upload", "url"])
@pytest.mark.parametrize("image_count", [1, 9])
@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_public_round_trip_restart_and_full_native_envelope(tmp_path, mode, image_count, count):
    fetched = []
    class Source:
        max_redirects = 0
        def get(self, url, **kwargs):
            fetched.append(url)
            assert "Authorization" not in kwargs.get("headers", {})
            kind, index = url.rsplit("/", 2)[-2:]
            return _Response(content=png(int(index)) if kind == "image" else wav(int(index)))
    client, comfy = client_for(tmp_path, Source())
    enable_audio(comfy)
    if mode == "upload":
        response = post_audio(client, count, image_count)
    else:
        value = metadata(image_count)
        for index, item in enumerate(value["references"]):
            item["sourceUrl"] = f"http://fixture.test/image/{index}"
        value["audioReferences"] = [{"speaker": f"Character {index+1}",
            "sourceUrl": f"http://fixture.test/audio/{index}"} for index in range(count)]
        response = client.post("/v1/video-jobs/from-reference-images", headers=AUTH, json=value)
        assert len(fetched) == image_count + count
    assert response.status_code == 202, response.text
    body = response.json()
    restarted, comfy = audio_client(tmp_path)
    gateway = restarted.app.state.gateway
    job = gateway.store.get_job(body["id"])
    voices = bindings(gateway.store, job["id"])
    snapshot = json.loads(job["execution_snapshot_json"])
    assert snapshot["workflowRendererVersion"] == (2 if count else 1)
    if count:
        assert body["referenceAudioContractVersion"] == 1
        assert [v["speaker"] for v in body["audioReferences"]] == [f"Character {i+1}" for i in range(count)]
        for index, row in enumerate(voices):
            source, prepared = gateway.reference_jobs.audio_files.paths(job["id"], row)
            assert source.read_bytes() == prepared.read_bytes() == wav(index)
            assert source.stat().st_mode & 0o777 == prepared.stat().st_mode & 0o777 == 0o600
            assert row["source_sha256"] == body["audioReferences"][index]["sourceSha256"] == sha256(wav(index)).hexdigest()
        public = json.dumps(body)
        assert "sourceUrl" not in public and "audioName" not in public
        detail = DashboardReader(tmp_path/"data").detail(job["id"])
        assert detail["audioReferences"] == body["audioReferences"]
        assert "audioName" not in json.dumps(detail)
    else:
        assert "audioReferences" not in body and "referenceAudioContractVersion" not in snapshot
    assert gateway.dispatch_once()["status"] == "submitted"
    frames = gateway.store.get_job_frames(job["id"])
    assert comfy.submissions == [expected_envelope(gateway.workflow_template["prompt"], job, frames, voices)]
    current = restarted.get(f"/v1/video-jobs/{job['id']}", headers=AUTH).json()
    assert current.get("audioReferences") == body.get("audioReferences")


@pytest.mark.parametrize("audio_metadata,audio_contents", [
    (None, []), ([{"speaker": ""}], [wav(0)]), ([{"speaker": "  "}], [wav(0)]),
    ([{"speaker": "A"}, {"speaker": "A"}], [wav(0), wav(1)]),
    ([{"speaker": str(i)} for i in range(4)], [wav(i) for i in range(4)]),
    ([{"speaker": "A", "sourceUrl": "http://fixture.test/voice"}], [wav(0)]),
    ([{"speaker": "A", "atMs": 0}], [wav(0)]),
    ([{"speaker": "A"}], []), ([], [wav(0)]),
    ([{"speaker": "A"}], [b"invalid"]),
    ([{"speaker": "A"}], [b"x" * (2*1024*1024+1)]),
])
def test_invalid_audio_has_no_admitted_job_or_owned_files(tmp_path, audio_metadata, audio_contents):
    client, comfy = audio_client(tmp_path)
    response = post_audio(client, value=metadata(1) | {"audioReferences": audio_metadata}, audios=audio_contents)
    assert response.status_code in (400, 413, 422), response.text
    gateway = client.app.state.gateway
    assert gateway.store.queue_counts() == (0, 0) and not comfy.submissions
    assert not list((tmp_path/"data/reference_audio_inputs").iterdir())
    assert not list((tmp_path/"data/assets").iterdir()) and not list((tmp_path/"input").iterdir())


def test_missing_audio_capability_only_refuses_optional_branch(tmp_path):
    client, comfy = audio_client(tmp_path)
    del comfy.info["LoadAudio"]
    assert client.get("/health").json()["referenceImagesReady"] is True
    assert client.get("/health").json()["referenceAudioReady"] is False
    assert post_audio(client, count=1).status_code == 503
    assert post_audio(client, count=0).status_code == 202


def test_large_noncanonical_wav_header_is_canonicalized_before_native_load(tmp_path):
    client, _ = audio_client(tmp_path)
    original = wav(0)
    junk = b"JUNK" + (5000).to_bytes(4, "little") + b"x"*5000
    source = original[:12] + junk + original[12:]
    source = source[:4] + (len(source)-8).to_bytes(4, "little") + source[8:]
    response = post_audio(client, count=1, audios=[source])
    assert response.status_code == 202, response.text
    audio = response.json()["audioReferences"][0]
    assert audio["sourceSha256"] != audio["preparedSha256"]
    gateway = client.app.state.gateway
    row = bindings(gateway.store, response.json()["id"])[0]
    _, prepared = gateway.reference_jobs.audio_files.paths(response.json()["id"], row)
    assert prepared.read_bytes() == original
    assert gateway.dispatch_once()["status"] == "submitted"


@pytest.mark.parametrize("content", [
    wav(0)[:-10],
    wav(0)[:24] + (16000).to_bytes(4, "little") + wav(0)[28:],
    wav(0)[:22] + (2).to_bytes(2, "little") + wav(0)[24:],
    wav(0)[:40] + (32000).to_bytes(4, "little") + wav(0)[44:32044],
])
def test_malformed_third_voice_fails_before_any_input_write(tmp_path, content):
    client, _ = audio_client(tmp_path)
    response = post_audio(client, audios=[wav(0), wav(1), content])
    assert response.status_code == 422, response.text
    assert not list((tmp_path/"input").iterdir())
    assert not list((tmp_path/"data/reference_audio_inputs").iterdir())


@pytest.mark.parametrize("frames,accepted", [(32000-1, False), (32000, True), (320000, True), (320001, False), (320031, False)])
def test_exact_audio_duration_boundaries(tmp_path, frames, accepted):
    stream = BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(32000)
        audio.writeframes(b"\1\0" * frames)
    client, _ = audio_client(tmp_path)
    response = post_audio(client, count=1, audios=[stream.getvalue()])
    assert response.status_code == (202 if accepted else 422), response.text
    capabilities = client.get("/health").json()["referenceAudioFormat"]
    assert capabilities == {"container": "wav", "codec": "pcm_s16le", "sampleRate": 32000,
        "channels": 1, "minDurationMs": 1000, "maxDurationMs": 10000, "maxBytes": 2097152}
