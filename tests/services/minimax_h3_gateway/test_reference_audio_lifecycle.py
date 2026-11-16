"""Private multi-voice inputs: admission ownership, dispatch, retention and purge."""
import json
import sqlite3
from pathlib import Path

import pytest
import requests

from plotloom_h3_gateway import lane
from plotloom_h3_gateway.contracts import GatewayError
from plotloom_h3_gateway.reference_audio_store import bindings
from tests.services.minimax_h3_gateway.test_reference_audio import audio_client, post_audio
from tests.services.minimax_h3_gateway.test_reference_images import AUTH, client_for
from tests.services.minimax_h3_gateway.test_reference_images import _no_live as _no_live

pytestmark = pytest.mark.usefixtures("_no_live")


def paths(gateway, job_id):
    return [path for row in bindings(gateway.store, job_id)
            for path in gateway.reference_jobs.audio_files.paths(job_id, row)]


@pytest.mark.parametrize("target", ["source", "prepared", "missing", "permissions", "symlink", "binding", "snapshot", "prompt"])
def test_audio_tamper_never_submits(tmp_path, target):
    client, comfy = audio_client(tmp_path)
    job_id = post_audio(client).json()["id"]
    gateway = client.app.state.gateway
    source, prepared = paths(gateway, job_id)[2:4]
    if target in {"source", "prepared"}:
        (source if target == "source" else prepared).write_bytes(b"tampered")
    elif target == "missing":
        prepared.unlink()
    elif target == "permissions":
        prepared.chmod(0o644)
    elif target == "symlink":
        prepared.unlink()
        prepared.symlink_to(source)
    else:
        with gateway.store._connect() as db:
            if target == "binding":
                db.execute("UPDATE job_reference_audio_bindings SET speaker='wrong' WHERE job_id=? AND ordinal=2", (job_id,))
            elif target == "prompt":
                db.execute("UPDATE jobs SET prompt='tampered' WHERE id=?", (job_id,))
            else:
                snapshot = json.loads(gateway.store.get_job(job_id)["execution_snapshot_json"])
                snapshot["audioReferences"][1]["index"] = 1
                db.execute("UPDATE jobs SET execution_snapshot_json=? WHERE id=?", (json.dumps(snapshot), job_id))
    gateway.dispatch_once()
    assert not comfy.submissions
    assert gateway.store.get_job(job_id)["status"] == "failed" or gateway.lane.active()["error_code"]


@pytest.mark.parametrize("boundary", ["third_audio", "lane", "audio_row"])
def test_late_admission_failure_rolls_back_rows_and_owned_inputs(tmp_path, monkeypatch, boundary):
    client, _ = audio_client(tmp_path)
    gateway = client.app.state.gateway
    if boundary == "third_audio":
        prepare = gateway.reference_jobs.audio_files.prepare
        def fail_third(job_id, index, *args):
            if index == 3:
                raise GatewayError("reference_audio_storage_failed", 500)
            return prepare(job_id, index, *args)
        monkeypatch.setattr(gateway.reference_jobs.audio_files, "prepare", fail_third)
    elif boundary == "lane":
        def refuse(*args):
            raise GatewayError("synthetic_lane_failure", 500)
        monkeypatch.setattr(lane, "register", refuse)
    else:
        with gateway.store._connect() as db:
            db.execute("""CREATE TRIGGER refuse_third_audio BEFORE INSERT ON job_reference_audio_bindings
                WHEN NEW.ordinal=3 BEGIN SELECT RAISE(ABORT, 'synthetic row failure'); END""")
    if boundary == "audio_row":
        with pytest.raises(sqlite3.IntegrityError):
            post_audio(client)
    else:
        assert post_audio(client).status_code == 500
    with gateway.store._connect() as db:
        for table in ("jobs", "job_frame_bindings", "job_reference_audio_bindings", "generation_lane"):
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    assert not list((tmp_path/"input").iterdir())
    assert not list((tmp_path/"data/reference_audio_inputs").iterdir())
    assert not list((tmp_path/"data/assets").iterdir())


def test_committed_admission_does_not_depend_on_post_commit_read(tmp_path, monkeypatch):
    client, _ = audio_client(tmp_path)
    gateway = client.app.state.gateway
    def unreadable(*args):
        raise OSError("synthetic post-commit read failure")
    monkeypatch.setattr(gateway.store, "get_job", unreadable)
    response = post_audio(client)
    assert response.status_code == 202, response.text
    assert all(path.exists() for path in paths(gateway, response.json()["id"]))
    assert gateway.store.queue_counts() == (1, 0)


@pytest.mark.parametrize("status", ["queued", "running", "outcome_unknown", "cancelled"])
def test_old_inputs_keep_unresolved_ownership(tmp_path, status):
    client, comfy = audio_client(tmp_path)
    gateway = client.app.state.gateway
    job_id = post_audio(client).json()["id"]
    if status == "cancelled":
        gateway.cancel_job(job_id)
        assert gateway.dispatch_once() is None  # Settle its never-dispatched lane entry.
    elif status == "outcome_unknown":
        def unknown(*args, **kwargs):
            raise requests.RequestException("synthetic response loss")
        comfy.post = unknown
        gateway.dispatch_once()
    elif status == "running":
        gateway.dispatch_once()
        gateway.store.update_job(job_id, status="running")
    with gateway.store._connect() as db:
        db.execute("UPDATE jobs SET created_at='2000-01-01 00:00:00'")
        db.execute("UPDATE assets SET created_at='2000-01-01 00:00:00'")
    gateway.cleanup_expired_gateway_keyframes()
    gateway.cleanup_due_job_records()
    for path in paths(gateway, job_id):
        assert path.exists() == (status != "cancelled")
    for frame in gateway.store.get_job_frames(job_id):
        assert gateway.files.prepared_input_path(job_id=job_id, frame=frame).exists() == (status != "cancelled")
        assert gateway.files.gateway_asset_path(frame).exists() == (status != "cancelled")
    assert all(bool(row["released_at"]) == (status == "cancelled") for row in bindings(gateway.store, job_id))


def expire_completed(gateway, job_id):
    with gateway.store._connect() as db:
        db.execute("UPDATE generation_lane SET state='done' WHERE job_id=?", (job_id,))
    gateway.store.mark_managed_output(job_id, output_name=f"2026-11-16T00-00-00Z_{job_id}.mp4",
        digest="a"*64, size_bytes=1, mime_type="video/mp4")
    gateway.store.update_job(job_id, status="succeeded", output_expires_at="2000-01-01 00:00:00")


def test_direct_record_cleanup_waits_for_all_image_and_audio_unlinks(tmp_path, monkeypatch):
    client, _ = audio_client(tmp_path)
    gateway = client.app.state.gateway
    job_id = post_audio(client).json()["id"]
    expire_completed(gateway, job_id)
    frame = gateway.store.get_job_frames(job_id)[0]
    image = gateway.files.prepared_input_path(job_id=job_id, frame=frame)
    unlink = Path.unlink
    def fail_image(path, *args, **kwargs):
        if path == image:
            raise PermissionError("synthetic image unlink failure")
        return unlink(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", fail_image)
        assert gateway.cleanup_due_job_records() == 0
        assert all(row["released_at"] is None for row in bindings(gateway.store, job_id))
        assert gateway.store.purge_completed_job_record(job_id) is False
    assert gateway.cleanup_due_job_records() == 1
    assert not image.exists()
    assert not list((tmp_path/"data/reference_audio_inputs").iterdir())


def test_terminal_looking_job_with_lane_hold_keeps_all_inputs(tmp_path):
    client, _ = audio_client(tmp_path)
    gateway = client.app.state.gateway
    job_id = post_audio(client).json()["id"]
    expire_completed(gateway, job_id)
    with gateway.store._connect() as db:
        db.execute("UPDATE generation_lane SET state='active' WHERE job_id=?", (job_id,))
        db.execute("UPDATE assets SET created_at='2000-01-01 00:00:00'")
    gateway.cleanup_expired_outputs()
    gateway.cleanup_expired_gateway_keyframes()
    gateway.cleanup_due_job_records()
    assert gateway.store.purge_completed_job_record(job_id) is False
    assert all(path.exists() for path in paths(gateway, job_id))
    for frame in gateway.store.get_job_frames(job_id):
        assert gateway.files.prepared_input_path(job_id=job_id, frame=frame).exists()
        assert gateway.files.gateway_asset_path(frame).exists()


def test_additive_schema_keeps_existing_image_only_job_and_database_inode(tmp_path):
    client, _ = client_for(tmp_path)
    from tests.services.minimax_h3_gateway.test_reference_images import post_references
    job_id = post_references(client).json()["id"]
    before = client.app.state.gateway.store.get_job(job_id)
    path = tmp_path/"data/gateway.sqlite3"
    inode = path.stat().st_ino
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE job_reference_audio_bindings")
    restarted, _ = audio_client(tmp_path)
    assert path.stat().st_ino == inode
    assert restarted.app.state.gateway.store.get_job(job_id) == before
    assert bindings(restarted.app.state.gateway.store, job_id) == []
    assert restarted.get(f"/v1/video-jobs/{job_id}", headers=AUTH).status_code == 200


@pytest.mark.parametrize("copy", ["source", "prepared"])
def test_wrong_audio_owner_is_refused(tmp_path, monkeypatch, copy):
    import os
    client, comfy = audio_client(tmp_path)
    gateway = client.app.state.gateway
    job_id = post_audio(client).json()["id"]
    target = paths(gateway, job_id)[0 if copy == "source" else 1]
    stat = Path.stat
    def wrong_owner(path, *args, **kwargs):
        result = stat(path, *args, **kwargs)
        if path == target:
            values = list(result)
            values[4] += 1
            return os.stat_result(values)
        return result
    with monkeypatch.context() as patch:
        patch.setattr(Path, "stat", wrong_owner)
        gateway.dispatch_once()
    assert not comfy.submissions


def test_partial_audio_unlink_retains_purge_marker_until_retry(tmp_path, monkeypatch):
    client, _ = audio_client(tmp_path)
    gateway = client.app.state.gateway
    job_id = post_audio(client).json()["id"]
    all_paths = paths(gateway, job_id)
    expire_completed(gateway, job_id)
    target = all_paths[3]
    unlink = Path.unlink
    def refuse(path, *args, **kwargs):
        if path == target:
            raise PermissionError("synthetic audio unlink failure")
        return unlink(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", refuse)
        assert gateway.cleanup_due_job_records() == 0
        rows = bindings(gateway.store, job_id)
        assert rows[0]["released_at"] is not None and rows[1]["released_at"] is None
        assert gateway.store.purge_completed_job_record(job_id) is False
    assert gateway.cleanup_due_job_records() == 1
    assert all(not path.exists() for path in all_paths)
