"""The extracted Qwen owner cannot bypass the Gateway's durable global lane."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import requests

from test_qwen_image import AUTH, _client, _Response
from test_shared_lane import VoiceFixture, register


def submit(client, prompt='Boundary proof'):
    response = client.post('/v1/image-jobs/from-text', headers=AUTH,
                           json={'prompt': prompt, 'resolution': '1024x1024'})
    assert response.status_code == 202
    return response.json()


def test_lost_qwen_ack_blocks_later_h3_and_voice_after_reopen(tmp_path):
    client, qwen = _client(tmp_path)
    first = submit(client)

    def lost(url, **options):
        qwen.calls.append((url, options))
        raise requests.Timeout('fixture acknowledgement lost')

    qwen.post = lost
    gateway = client.app.state.gateway
    video = client.post('/v1/video-jobs/from-text', headers=AUTH,
                        json={'prompt': 'Later video', 'resolution': '832x480'}).json()
    voice = register(gateway.lane)
    result = gateway.dispatch_once()
    assert result['id'] == first['id'] and result['status'] == 'outcome_unknown'
    reopened, new_qwen = _client(tmp_path)
    resumed = reopened.app.state.gateway
    voice_client = VoiceFixture()
    resumed.dispatcher.voice = voice_client
    for _ in range(3):
        resumed.dispatch_once()
    assert len(qwen.calls) == 1 and new_qwen.calls == [] and voice_client.posts == []
    assert resumed.store.get_job(video['id'])['status'] == 'queued'
    assert resumed.lane.active()['job_id'] == first['id']
    assert voice['sequence'] > resumed.lane.active()['sequence']


def test_competing_qwen_dispatch_claim_performs_at_most_one_post(tmp_path):
    client, qwen = _client(tmp_path)
    created = submit(client)
    gateway = client.app.state.gateway
    frozen = gateway.store.get_job(created['id'])
    started, release = Event(), Event()
    original = qwen.post

    def held(url, **options):
        started.set()
        assert release.wait(5)
        return original(url, **options)

    qwen.post = held
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(gateway.dispatch_media, frozen)
        assert started.wait(5)
        second = workers.submit(gateway.dispatch_media, frozen)
        try:
            assert second.result(timeout=5) is None
        finally:
            release.set()
        assert first.result(timeout=5)['status'] == 'succeeded'
    assert len(qwen.calls) == 1


def test_queued_qwen_cancel_never_calls_provider(tmp_path):
    client, qwen = _client(tmp_path)
    job = submit(client)
    gateway = client.app.state.gateway
    assert gateway.cancel_job(job['id'])['status'] == 'cancelled'
    assert gateway.dispatch_once() is None
    assert qwen.calls == [] and gateway.lane.active() is None


def test_queued_frozen_snapshot_survives_current_catalogue_change(tmp_path, monkeypatch):
    client, qwen = _client(tmp_path)
    job = submit(client)
    from plotloom_h3_gateway import qwen_jobs

    def no_current_catalogue(_resolution):
        raise AssertionError('dispatch must consume the persisted snapshot')

    monkeypatch.setattr(qwen_jobs, 'admitted_qwen_image_canvas', no_current_catalogue)
    gateway = client.app.state.gateway
    frozen = gateway.store.get_job(job['id'])['execution_snapshot_json']
    assert gateway.dispatch_once()['status'] == 'succeeded'
    assert gateway.store.get_job(job['id'])['execution_snapshot_json'] == frozen
    assert len(qwen.calls) == 1


def test_comfy_queue_blocks_qwen_before_claim_or_post(tmp_path):
    client, qwen = _client(tmp_path)
    job = submit(client)
    gateway = client.app.state.gateway
    original = gateway.comfy.session.get
    gateway.comfy.session.get = lambda url, **options: (
        _Response({'queue_running': [[1]], 'queue_pending': []})
        if url.endswith('/queue') else original(url, **options))
    gateway.dispatch_once()
    assert gateway.store.get_job(job['id'])['status'] == 'queued'
    assert qwen.calls == []
