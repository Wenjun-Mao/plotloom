"""Retained-media transfer, input preservation, failure cleanup and lane safety."""
import json
import sqlite3

import pytest
import requests

from plotloom_h3_gateway import frame_binding_schema
from plotloom_h3_gateway.contracts import GatewayError
from plotloom_h3_gateway.store import GatewayStore
from tests.services.minimax_h3_gateway.test_reference_images import (
    AUTH, client_for, metadata, png, post_references,
)
from tests.services.minimax_h3_gateway.test_reference_images import _no_live as _no_live

pytestmark = pytest.mark.usefixtures("_no_live")


def test_terminal_transfer_download_and_expiry_preserve_unrelated_inputs(tmp_path):
    client, comfy = client_for(tmp_path)
    job_id = post_references(client).json()["id"]
    gateway = client.app.state.gateway
    gateway.dispatch_once()
    prompt_id = gateway.store.get_job(job_id)["comfy_prompt_id"]
    comfy.history_response = {prompt_id: {"status": {"status_str": "success"}, "outputs": {
        "output": {"images": [{"filename": "retained.mp4", "subfolder": "", "type": "output"}]}}}}
    # Transport-only fixture bytes. The separate functional QA uses retained AV.
    output = tmp_path/"output/retained.mp4"
    output.write_bytes(b"retained-transport-fixture")
    unrelated = tmp_path/"input/unrelated.png"
    unrelated.write_bytes(b"preserve")
    response = client.get(f"/v1/video-jobs/{job_id}/output", headers=AUTH)
    assert response.status_code == 200 and response.content == b"retained-transport-fixture"
    assert not output.exists()
    assert gateway.store.get_job(job_id)["status"] == "succeeded"
    assert gateway.dispatch_once() is None  # Observe completion and release lane ownership.
    frames = gateway.store.get_job_frames(job_id)
    originals = [gateway.files.gateway_asset_path(frame) for frame in frames]
    prepared = [gateway.files.prepared_input_path(job_id=job_id, frame=frame) for frame in frames]
    gateway.store.update_job(job_id, status="succeeded", output_expires_at="2000-01-01 00:00:00")
    gateway.cleanup_expired_outputs()
    assert all(not path.exists() for path in originals+prepared)
    assert unrelated.read_bytes() == b"preserve"
    assert client.get(f"/v1/video-jobs/{job_id}", headers=AUTH).json()["references"]


@pytest.mark.parametrize("target", ["original", "prepared", "binding", "timeline"])
def test_tamper_refuses_before_native_send(tmp_path, target):
    client, comfy = client_for(tmp_path)
    job_id = post_references(client).json()["id"]
    gateway = client.app.state.gateway
    frame = gateway.store.get_job_frames(job_id)[1]
    if target in {"original", "prepared"}:
        path = (gateway.files.gateway_asset_path(frame) if target == "original" else
                gateway.files.prepared_input_path(job_id=job_id, frame=frame))
        path.write_bytes(b"tampered")
    else:
        with gateway.store._connect() as db:
            if target == "binding":
                db.execute("UPDATE job_frame_bindings SET prepared_input_name='wrong.png' WHERE job_id=? AND role='reference_2'", (job_id,))
            else:
                job = gateway.store.get_job(job_id)
                value = json.loads(job["execution_snapshot_json"])
                value["references"][1]["frameIndex"] = 61
                db.execute("UPDATE jobs SET execution_snapshot_json=? WHERE id=?", (json.dumps(value), job_id))
    gateway.dispatch_once()
    assert not comfy.submissions
    job = gateway.store.get_job(job_id)
    assert job["status"] == "failed" or gateway.lane.active()["error_code"] == "lane.media_binding_mismatch"
    status = client.get(f"/v1/video-jobs/{job_id}", headers=AUTH)
    assert status.status_code == 200
    if target == "timeline":
        assert status.json()["references"] is None


def test_second_image_failure_rolls_back_every_owned_file(tmp_path, monkeypatch):
    client, _ = client_for(tmp_path)
    files = client.app.state.gateway.reference_jobs.files
    prepare = files.prepare
    calls = []
    def fail_second(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise GatewayError("reference_storage_failed", 500)
        return prepare(*args, **kwargs)
    monkeypatch.setattr(files, "prepare", fail_second)
    response = post_references(client)
    assert response.status_code == 500
    assert list((tmp_path/"input").iterdir()) == []
    assert list((tmp_path/"data/assets").iterdir()) == []
    assert client.app.state.gateway.store.queue_counts() == (0, 0)


def test_queued_cancel_and_thirty_day_cleanup_protect_active_unknown(tmp_path):
    client, comfy = client_for(tmp_path)
    gateway = client.app.state.gateway
    cancelled = post_references(client).json()["id"]
    held = post_references(client).json()["id"]
    gateway.cancel_job(cancelled)
    def unknown(*args, **kwargs):
        raise requests.RequestException("synthetic response loss")
    comfy.post = unknown
    result = gateway.dispatch_once()
    assert result["id"] == held and result["status"] == "outcome_unknown"
    with gateway.store._connect() as db:
        db.execute("UPDATE jobs SET created_at='2000-01-01 00:00:00'")
        db.execute("UPDATE assets SET created_at='2000-01-01 00:00:00'")
    gateway.cleanup_expired_gateway_keyframes()
    for frame in gateway.store.get_job_frames(cancelled):
        assert not gateway.files.prepared_input_path(job_id=cancelled, frame=frame).exists()
        assert not gateway.files.gateway_asset_path(frame).exists()
    for frame in gateway.store.get_job_frames(held):
        assert gateway.files.prepared_input_path(job_id=held, frame=frame).exists()
        assert gateway.files.gateway_asset_path(frame).exists()
    restarted, restarted_comfy = client_for(tmp_path)
    assert restarted.app.state.gateway.dispatch_once() is None
    assert restarted_comfy.submissions == []


def test_current_frame_schema_migrates_without_rewriting_existing_job(tmp_path):
    path = tmp_path/"schema.sqlite3"
    store = GatewayStore(path)
    with store._connect() as db:
        db.execute("DROP TABLE job_frame_bindings")
        db.execute(frame_binding_schema.PREVIOUS_TABLE)
        db.execute(frame_binding_schema.ASSET_INDEX)
        before = db.execute("SELECT sql FROM sqlite_master WHERE name='jobs'").fetchone()[0]
    GatewayStore(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT sql FROM sqlite_master WHERE name='jobs'").fetchone()[0] == before
        assert db.execute("SELECT sql FROM sqlite_master WHERE name='job_frame_bindings'").fetchone()[0] == frame_binding_schema.CURRENT_TABLE
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_auth_multipart_mixing_and_single_still_rules(tmp_path):
    client, _ = client_for(tmp_path)
    assert client.post("/v1/video-jobs/from-reference-images", json=metadata()).status_code == 401
    value = metadata()
    value["references"][0]["sourceUrl"] = "http://fixture.test/0"
    assert post_references(client, value).status_code == 422
    assert post_references(client, contents=[png(0)]).status_code == 422
    assert post_references(client, contents=[png(0), b"invalid"]+[png(1)]*3).status_code == 422
    assert list((tmp_path/"data/assets").iterdir()) == []
