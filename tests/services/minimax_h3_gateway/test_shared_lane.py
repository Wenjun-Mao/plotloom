"""Control-plane faults must never release unknown inference or replay it."""

from types import SimpleNamespace

import pytest

from plotloom_h3_gateway.contracts import GatewayError
from plotloom_h3_gateway.lane import GenerationLane, LaneDispatcher
from plotloom_h3_gateway.store import GatewayStore
from test_app import _client, _submit_image


class VoiceFixture:
    def __init__(self, *, lost_ack=False, released=True, status="completed"):
        self.posts, self.gets = [], []
        self.lost_ack, self.released, self.status = lost_ack, released, status

    def result(self, entry):
        return {"jobId": entry["job_id"], "kind": entry["job_kind"],
                "grantId": entry["grant_id"], "bindingHash": entry["binding_hash"],
                "status": self.status, "releaseConfirmed": self.released}

    def execute(self, entry):
        self.posts.append(entry["job_id"])
        if self.lost_ack:
            raise GatewayError("voice.dispatch_outcome_unknown", 503)
        return self.result(entry)

    def execution(self, entry):
        self.gets.append(entry["job_id"])
        return self.result(entry)


def register(lane, kind="take", n=1):
    prefix = {"take": "take", "clone": "vt", "generation": "vg"}[kind]
    return lane.register_voice(kind, f"{prefix}_{n:032x}", f"{n:064x}")


def test_one_sequence_covers_every_producer_and_cancelled_entries(tmp_path):
    client, _ = _client(tmp_path)
    gateway = client.app.state.gateway
    events = []
    voice = VoiceFixture()
    register(gateway.lane, "generation", 1)
    image = _submit_image(client)
    register(gateway.lane, "clone", 2)
    cancelled = _submit_image(client)
    gateway.store.update_job(cancelled["id"], status="cancelled")
    # The same local transaction used for H3 also registers Qwen's typed entry.
    record = gateway.store.get_job(image["id"])
    record.update(id="img_" + "4" * 32, backend="qwen_image")
    gateway.store.reserve_job(record, [])
    register(gateway.lane, "take", 3)
    def media(job):
        events.append(job["backend"])
        return gateway.store.update_job(job["id"], status="failed", error_code="fixture.known_not_sent")
    gateway.dispatch_media = media
    gateway.dispatcher.voice = voice
    for _ in range(5):
        gateway.dispatch_once()
    assert voice.posts == [f"vg_{1:032x}", f"vt_{2:032x}", f"take_{3:032x}"]
    assert events == ["h3_video", "qwen_image"]
    assert gateway.lane.counts() == (0, 0)


def test_lost_ack_is_observed_after_gateway_restart_never_reposted(tmp_path):
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    lane = GenerationLane(store)
    first = register(lane)
    register(lane, n=2)
    voice = VoiceFixture(lost_ack=True, released=False, status="running")
    dispatch = LaneDispatcher(SimpleNamespace(store=store, lane=lane), voice)
    assert dispatch.advance() is None
    assert lane.active()["error_code"] == "voice.dispatch_outcome_unknown"
    # Reopen the database before the Lab status becomes available.
    restarted = GatewayStore(tmp_path / "gateway.sqlite3")
    dispatch = LaneDispatcher(SimpleNamespace(store=restarted, lane=GenerationLane(restarted)), voice)
    for _ in range(3):
        dispatch.advance()
    assert voice.posts == [first["job_id"]] and len(voice.gets) == 3
    voice.status = "failed"
    dispatch.advance()
    assert dispatch.lane.active()["error_code"] == "dispatch.release_unproven"
    voice.released = True
    voice.lost_ack = False
    dispatch.advance()
    assert voice.posts == [first["job_id"], f"take_{2:032x}"]
    assert dispatch.lane.active() is None


def test_wrong_terminal_or_binding_cannot_release_and_registration_is_unique(tmp_path):
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    lane = GenerationLane(store)
    entry = register(lane)
    assert register(lane)["sequence"] == entry["sequence"]
    with pytest.raises(GatewayError, match="lane.binding_conflict"):
        lane.register_voice("take", entry["job_id"], "f" * 64)
    voice = VoiceFixture(status="invented-success")
    dispatch = LaneDispatcher(SimpleNamespace(store=store, lane=lane), voice)
    dispatch.advance()
    assert lane.active()["error_code"] == "lane.voice_status_invalid"
    wrong = voice.result(lane.active()) | {"status": "completed", "jobId": f"take_{2:032x}"}
    dispatch._voice_result(lane.active(), wrong)
    assert lane.active()["error_code"] == "lane.voice_binding_mismatch"
    assert len(voice.posts) == 1


def test_terminal_voice_audit_expires_but_unknown_owner_is_retained(tmp_path):
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    lane = GenerationLane(store)
    register(lane)
    done = lane.claim()
    lane.finish(done)
    register(lane, n=2)
    held = lane.claim()
    lane.hold(held, "voice.dispatch_outcome_unknown")
    with store._connect() as db:
        db.execute("UPDATE generation_lane SET updated_at=datetime('now','-31 days')")
    assert lane.purge_finished_voice_records() == 1
    assert lane.active()["job_id"] == held["job_id"]


def test_media_dispatch_has_one_durable_intent_and_refuses_changed_binding(tmp_path):
    client, session = _client(tmp_path)
    gateway = client.app.state.gateway
    created = _submit_image(client)
    job = gateway.store.get_job(created["id"])
    assert gateway.dispatch_media(job)["status"] == "submitted"
    assert gateway.dispatch_media(job) is None
    assert len(session.submissions) == 1
    other_client, _ = _client(tmp_path / "other")
    other = other_client.app.state.gateway
    created = _submit_image(other_client)
    other.store.update_job(created["id"], status="queued", prompt="changed outside admission")
    assert other.dispatch_once() is None
    assert other.lane.active()["error_code"] == "lane.media_binding_mismatch"
