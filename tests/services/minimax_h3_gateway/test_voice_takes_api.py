"""Authenticated facade transports only configured, hash-bound voice data."""

import hashlib

import requests
from fastapi.testclient import TestClient

from plotloom_h3_gateway.app import GatewaySettings, create_app
from test_app import AUTH, _ComfySession


TAKE = "take_" + "1" * 32
VOICE = "voice_" + "2" * 32


class Response:
    def __init__(self, value, status=200, content=b""):
        self.value, self.status_code, self.content = value, status, content

    def json(self):
        return self.value


class Session:
    def __init__(self):
        self.calls = []
        self.audio = b"fixture WAV bytes"
        self.fail = False

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        assert url.startswith("http://configured-lab/internal/voice-takes")
        assert kwargs["headers"] == {"Authorization": "Bearer private-key"}
        assert kwargs["allow_redirects"] is False and kwargs["timeout"] == (3, 3)
        if self.fail:
            raise requests.RequestException("lost reply")
        if method == "DELETE":
            return Response(None, 204)
        if "/audio?" in url:
            return Response(None, content=self.audio)
        take = {"takeId": TAKE, "voiceId": VOICE, "sourceSha256": hashlib.sha256(b"fixture WAV bytes").hexdigest()}
        return Response({"takes": [take]} if url.endswith("?voiceId=" + VOICE) else take, 202 if method == "POST" else 200)


def client(root):
    app = create_app(GatewaySettings(api_key="test-key", data_dir=root / "data", comfy_input_dir=root / "input",
        comfy_output_dir=root / "output", dispatch_worker_enabled=False, voice_lab_url="http://configured-lab",
        voice_lab_key="private-key"), session=_ComfySession())
    session = Session()
    app.state.gateway.voice_control.session = session
    return TestClient(app), session


def test_facade_auth_list_create_get_audio_and_confirmed_delete(tmp_path):
    api, session = client(tmp_path)
    assert api.get("/v1/voice-takes?voiceId=" + VOICE).status_code == 401
    assert api.post("/v1/voice-takes", headers=AUTH, json={"voiceId": VOICE, "text": "你好", "engineId": "index_base"}).status_code == 202
    assert api.get("/v1/voice-takes?voiceId=" + VOICE, headers=AUTH).json()["takes"][0]["takeId"] == TAKE
    assert api.get("/v1/voice-takes/" + TAKE, headers=AUTH).status_code == 200
    assert api.get(f"/v1/voice-takes/{TAKE}/audio", headers=AUTH).content == session.audio
    session.audio = b"corrupt"
    assert api.get(f"/v1/voice-takes/{TAKE}/audio", headers=AUTH).json() == {"error": "voice.audio_hash_mismatch"}
    assert api.delete("/v1/voice-takes/" + TAKE, headers=AUTH).status_code == 422
    assert api.request("DELETE", "/v1/voice-takes/" + TAKE, headers=AUTH, json={"confirmTakeId": TAKE}).status_code == 204
    assert all("/arbitrary" not in url for _, url, _ in session.calls)


def test_ambiguous_cpu_create_is_not_retried_or_silently_switched(tmp_path):
    api, session = client(tmp_path)
    session.fail = True
    result = api.post("/v1/voice-takes", headers=AUTH, json={"voiceId": VOICE, "text": "你好", "engineId": "index_base"})
    assert result.status_code == 503 and result.json() == {"error": "voice.dispatch_outcome_unknown"}
    assert len(session.calls) == 1
    assert api.get("/v1/voice-takes/bad/audio?kind=source", headers=AUTH).status_code == 422
    assert api.get(f"/v1/voice-takes/{TAKE}/audio?kind=wrong", headers=AUTH).status_code == 422
    assert len(session.calls) == 1


def test_registration_uses_private_key_and_matching_kind_only(tmp_path):
    api, _ = client(tmp_path)
    body = {"kind": "take", "jobId": TAKE, "bindingHash": "1" * 64}
    assert api.post("/internal/voice-registrations", headers=AUTH, json=body).status_code == 401
    headers = {"Authorization": "Bearer private-key"}
    first = api.post("/internal/voice-registrations", headers=headers, json=body)
    assert first.status_code == 202
    assert api.post("/internal/voice-registrations", headers=headers, json=body).json() == first.json()
    assert api.post("/internal/voice-registrations", headers=headers, json=body | {"kind": "clone"}).status_code == 422
    assert api.get("/internal/voice-registrations/" + TAKE, headers=headers).json()["phase"] == "queued"
