"""Real SQLite and private HTTP grants, with no GPU or local-queue fallback."""

import time

import pytest
from fastapi.testclient import TestClient

from plotloom_voice_lab.app import create_app
from plotloom_voice_lab.contracts import TakeCreate
from plotloom_voice_lab.dispatch import ExecutionGrant
from plotloom_voice_lab.store import Store
from test_takes import published_voice
from test_voice_lab import FakeEngine, wait_for


AUTH = {"Authorization": "Bearer private-fixture-key"}


class OfflineLane:
    def register(self, _):
        raise ValueError("dispatch.control_unavailable")

    def progress(self, _):
        raise ValueError("dispatch.control_unavailable")


def app(root, engine=None):
    return create_app(root, engine or FakeEngine(), lane_client=OfflineLane(), dispatch_key="private-fixture-key")


def grant(store, take):
    pending = next(item for item in store.dispatch.pending() if item["jobId"] == take["takeId"])
    return {**pending, "grantId": "a" * 32}


def test_public_admission_cannot_dispatch_and_private_execution_is_bound(tmp_path):
    service = app(tmp_path)
    voice, _ = published_voice(service.state.store)
    with TestClient(service) as client:
        body = {"voiceId": voice["voiceId"], "text": "先切断电源。", "engineId": "index_base",
                "delivery": {"mode": "text", "description": "坚定、果断、时间紧迫"}, "seed": 123}
        take = client.post("/api/voice-takes", json=body).json()
        time.sleep(.05)
        before = client.get(f"/api/voice-takes/{take['takeId']}").json()
        assert before["status"] == "queued" and before["queueAhead"] is None
        assert service.state.worker.tasks.empty()
        command = grant(service.state.store, take)
        assert client.post("/internal/executions", json=command).status_code == 401
        assert client.post("/internal/executions", json=command | {"bindingHash": "f" * 64}, headers=AUTH).status_code == 409
        assert client.post("/internal/executions", json=command, headers=AUTH).status_code == 202
        result = wait_for(client, f"/api/voice-takes/{take['takeId']}")
        assert result["status"] == "completed"
        assert result["executionDetails"]["effectiveVector"] and result["delivery"] == body["delivery"]
        # Duplicate delivery of the same control grant cannot synthesize again.
        assert client.post("/internal/executions", json=command, headers=AUTH).status_code == 202
        assert client.post("/internal/executions", json=command | {"grantId": "b" * 32}, headers=AUTH).status_code == 409
        evidence = client.get("/internal/executions/" + command["grantId"], headers=AUTH).json()
        assert evidence["releaseConfirmed"] is True and evidence["status"] == "completed"
        for kind in ("source", "h3"):
            audio = client.get(f"/internal/voice-takes/{take['takeId']}/audio?kind={kind}", headers=AUTH)
            import hashlib
            assert hashlib.sha256(audio.content).hexdigest() == result[f"{kind}Sha256"]
        assert client.post("/api/voice-takes", json=body | {"path": "/arbitrary.wav"}).status_code == 422
        assert client.post("/api/voice-takes", json=body | {"engineId": "qwen_base"}).status_code == 422


@pytest.mark.parametrize("gateway_first", [True, False])
def test_restart_keeps_unstarted_outbox_but_holds_uncertain_grant(tmp_path, gateway_first):
    # The CPU registration queue and the inference grant have distinct recovery.
    store = Store(tmp_path)
    voice, _ = published_voice(store)
    first = store.takes.create(TakeCreate(voiceId=voice["voiceId"], text="你好", engineId="index_base"))
    queued = store.takes.create(TakeCreate(voiceId=voice["voiceId"], text="再见", engineId="index_base"))
    command = grant(store, first)
    assert store.dispatch.authorize(ExecutionGrant(**command))
    store.takes.mark(first["takeId"], "running")
    from fixtures.shared_lane import SharedLaneFixture
    lane = SharedLaneFixture(tmp_path).lane
    lane.register_voice(command["kind"], command["jobId"], command["bindingHash"])
    held = lane.claim()
    if gateway_first:
        from plotloom_h3_gateway.store import GatewayStore
        GatewayStore(tmp_path / "fixture-gateway.sqlite3")
    reopened = Store(tmp_path)
    reopened.reconcile_interrupted()
    assert reopened.takes.get(first["takeId"])["status"] == "interrupted"
    assert reopened.takes.get(queued["takeId"])["status"] == "queued"
    assert reopened.dispatch.execution(command["grantId"])["releaseConfirmed"] is False
    assert reopened.dispatch.authorize(ExecutionGrant(**command)) is False
    if not gateway_first:
        from plotloom_h3_gateway.store import GatewayStore
        GatewayStore(tmp_path / "fixture-gateway.sqlite3")
    assert lane.active()["grant_id"] == held["grant_id"]
    with pytest.raises(ValueError, match="take.busy"):
        reopened.takes.delete(first["takeId"], first["takeId"])


def test_late_registration_of_deleted_take_releases_without_generation(tmp_path):
    service = app(tmp_path)
    voice, _ = published_voice(service.state.store)
    take = service.state.store.takes.create(TakeCreate(voiceId=voice["voiceId"], text="你好", engineId="index_base"))
    command = grant(service.state.store, take)
    service.state.store.takes.mark(take["takeId"], "failed", "fixture.never_started")
    service.state.store.takes.delete(take["takeId"], take["takeId"])
    with TestClient(service) as client:
        result = client.post("/internal/executions", json=command, headers=AUTH).json()
        assert result["releaseConfirmed"] is True and result["status"] == "deleted"
        assert service.state.worker.tasks.empty()
        assert client.get(f"/api/voice-takes/{take['takeId']}/audio").status_code == 409


def test_failed_take_publication_removes_partial_outputs_and_keeps_identity(tmp_path, monkeypatch):
    service = app(tmp_path)
    voice, _ = published_voice(service.state.store)

    def failed_publication(target, native, rate):
        (target / 'source.wav').write_bytes(b'partial-native')
        (target / 'h3.wav').write_bytes(b'partial-derivative')
        raise ValueError('fixture.publication_failed')

    monkeypatch.setattr('plotloom_voice_lab.worker.persist_reference_file', failed_publication)
    with TestClient(service) as client:
        take = client.post('/api/voice-takes', json={
            'voiceId': voice['voiceId'], 'text': '关门。', 'engineId': 'index_base', 'seed': 1,
        }).json()
        command = grant(service.state.store, take)
        assert client.post('/internal/executions', json=command, headers=AUTH).status_code == 202
        assert wait_for(client, '/api/voice-takes/' + take['takeId'])['status'] == 'failed'
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not service.state.store.dispatch.execution(command['grantId'])['releaseConfirmed']:
            time.sleep(.01)
        target = tmp_path / 'takes' / take['takeId']
        assert not (target / 'source.wav').exists() and not (target / 'h3.wav').exists()
        assert service.state.store.voices.get(voice['voiceId']) == voice
        assert client.get('/api/voice-takes/' + take['takeId'] + '/audio').status_code == 409
