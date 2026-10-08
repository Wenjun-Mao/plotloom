"""API proof for retained reads versus operational production admission."""

import json
import shutil
import sqlite3
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.persistence.codec import stable_hash
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_ingestion import probe_video
from tests.project_storage_fixtures import FixtureResolver, fixture_profile
from tests.test_project_storage_video import FakeH3, _approved_keyframe, _prepare_video


@pytest.fixture
def evidence(tmp_path: Path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Synthetic audiovisual proof requires FFmpeg")
    source = tmp_path / "explicitly-synthetic-eight-second-source.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:size=576x1024:rate=24:duration=8",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8",
        "-frames:v", "192", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-ar", "48000", "-movflags", "+faststart", str(source),
    ], check=True, timeout=60)
    provider = FakeH3(outputs=[source.read_bytes()])
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    client = TestClient(create_project_folder_authoring_app(
        storage, video_provider=provider, video_adapter=MiniMaxH3GatewayAdapter(), video_probe=probe_video,
    ))
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(FixtureResolver()).execute(store, profile=fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    job = _prepare_video(client, project_id, approval, context, key="retained-proof", requested_duration_seconds=8)
    base = f"/api/v2/projects/{project_id}"
    job_url = f"{base}/video-jobs/{job['id']}"
    assert client.post(f"{job_url}/submit").status_code == 200
    assert client.post(f"{job_url}/reconcile").status_code == 200
    proposal = client.post(f"{job_url}/segments", json={"inFrame": 0, "outFrame": 120, "expectedSelectionRevision": 0})
    assert proposal.status_code == 201, proposal.text
    segment = proposal.json()
    segment_url = f"{base}/video-segments/{segment['id']}"
    assert client.post(f"{segment_url}/select", json={"expectedSelectionRevision": 0}).status_code == 201
    return storage, client, provider, project_id, base, job_url, segment_url, job, segment


def _current(evidence) -> dict:
    _, client, _, _, base, _, _, _, _ = evidence
    response = client.get(f"{base}/video-jobs")
    assert response.status_code == 200, response.text
    return response.json()["jobs"][0]


def test_archive_retains_verified_preview_but_refuses_all_production_actions(evidence) -> None:
    storage, client, provider, project_id, _, job_url, segment_url, _, segment = evidence
    before = _current(evidence)
    original = client.get(f"{job_url}/media").content
    derivative = client.get(f"{segment_url}/preview").content
    assert sha256(derivative).hexdigest() == segment["derivativeHash"]
    store = storage.projects.open(project_id)
    project = store.project()
    store.close()
    archived = storage.lifecycle.archive(project_id, expected_lifecycle_revision=project.lifecycle_revision)
    retained = _current(evidence)
    assert retained["lifecycleStatus"] == "archived" and retained["inputStatus"] == "current"
    assert retained["current"] is False and retained["selected"] is False
    assert retained["segments"][0]["previewEligible"] is True
    assert retained["segments"][0]["current"] is False and retained["segments"][0]["selected"] is False
    assert client.get(f"{job_url}/media").content == original
    assert client.get(f"{segment_url}/preview").content == derivative
    ranged = client.get(f"{segment_url}/preview", headers={"Range": "bytes=0-31"})
    assert ranged.status_code == 206 and ranged.content == derivative[:32]
    assert client.get(f"{job_url}/playback").status_code == 404
    for path, body in [
        ("segments", {"inFrame": 0, "outFrame": 120, "expectedSelectionRevision": 1}),
        ("review", {"decision": "reject", "expectedSelectionRevision": 1}),
        ("review/reopen", {"reviewer": "QA", "reason": "technical only", "expectedSelectionRevision": 1}),
    ]:
        response = client.post(f"{job_url}/{path}", json=body)
        assert response.status_code == 409, response.text
    assert client.post(f"{segment_url}/select", json={"expectedSelectionRevision": 1}).status_code == 409
    assert len(provider.submits) == 1
    storage.lifecycle.restore(project_id, expected_lifecycle_revision=archived.lifecycle_revision)
    restored = _current(evidence)
    assert restored["lifecycleStatus"] == "active" and restored["inputStatus"] == "current"
    assert restored["current"] is True and restored["selected"] is True
    assert restored["reviews"] == before["reviews"] and restored["selectionRevision"] == before["selectionRevision"]
    assert client.get(f"{job_url}/playback").content == derivative


def test_rejection_and_changed_canon_retain_preview_without_restoring_playback(evidence) -> None:
    storage, client, _, project_id, _, job_url, segment_url, _, _ = evidence
    derivative = client.get(f"{segment_url}/preview").content
    rejected = client.post(f"{job_url}/review", json={"decision": "reject", "expectedSelectionRevision": 1})
    assert rejected.status_code == 201, rejected.text
    assert _current(evidence)["segments"][0]["previewEligible"] is True
    assert client.get(f"{segment_url}/preview").content == derivative
    assert client.get(f"{job_url}/playback").status_code == 404
    store = storage.projects.open(project_id)
    board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    changed = board.model_copy(update={"shots": [board.shots[0].model_copy(update={"action": "Changed current action."}), *board.shots[1:]]})
    store.update_stage(StageName.STORYBOARD, changed, expected_revision=store.authoring.get_stage_head(project_id, StageName.STORYBOARD).revision)
    store.close()
    stale = _current(evidence)
    assert stale["inputStatus"] == "stale" and stale["current"] is False
    assert stale["segments"][0]["previewEligible"] is True
    assert client.get(f"{segment_url}/preview").content == derivative
    assert client.get(f"{job_url}/playback").status_code == 404
    assert client.post(f"{job_url}/review/reopen", json={"reviewer": "QA", "reason": "technical only", "expectedSelectionRevision": 2}).status_code == 409


def test_corrupt_frozen_identity_refuses_preview_and_preserves_raw_diagnostics(evidence) -> None:
    storage, client, _, project_id, _, job_url, segment_url, job, _ = evidence
    store = storage.projects.open(project_id)
    path = store.database_path
    store.close()
    for malformed in [None, [], {**job["snapshot"], "provider": {**job["snapshot"]["provider"], "adapterId": []}}]:
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE v2_video_jobs SET snapshot=?, snapshot_hash=?, request_hash=? WHERE id=?", (
                json.dumps(malformed), stable_hash(malformed),
                stable_hash({"snapshot": malformed, "idempotencyKey": "retained-proof"}), job["id"],
            ))
        invalid = _current(evidence)
        assert invalid["snapshot"] == malformed and invalid["inputStatus"] == "invalid"
        assert invalid["current"] is False and invalid["segments"][0]["previewEligible"] is False
        response = client.get(f"{segment_url}/preview")
        assert response.status_code == 409, response.text
        assert client.post(f"{job_url}/discard", json={"expectedSelectionRevision": 1}).status_code == 409


def test_corrupt_derivative_bytes_are_refused_before_full_or_range_delivery(evidence) -> None:
    storage, client, _, project_id, _, _, segment_url, _, segment = evidence
    store = storage.projects.open(project_id)
    metadata = store.media.video_segments.proposal_storage(project_id, segment["id"])
    derivative = store.home / metadata["uri"]
    store.close()
    original = derivative.read_bytes()
    derivative.write_bytes(b"corrupt retained bytes")
    try:
        for headers in [{}, {"Range": "bytes=0-31"}]:
            response = client.get(f"{segment_url}/preview", headers=headers)
            assert response.status_code == 422, response.text
            assert response.json()["code"] == "project_storage_error"
            assert b"corrupt retained bytes" not in response.content
    finally:
        derivative.write_bytes(original)
