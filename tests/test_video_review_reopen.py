"""Explicit reopening of retained, rejected H3 takes."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.persistence.codec import stable_hash
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage.project_handle import (
    ProjectRecoveryRequiredError,
    ProjectStore,
)
from plotloom.video_contracts import VideoReviewReopenRequest
from tests.project_storage_fixtures import FixtureResolver, fixture_profile
from tests.test_project_storage_video import (
    FakeH3,
    _approved_keyframe,
    _fixture_app,
    _png,
    _prepare_video,
)


def _project(tmp_path: Path, provider: FakeH3) -> tuple[object, TestClient, str, dict, dict]:
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(FixtureResolver()).execute(store, profile=fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    return storage, client, project_id, approval, context


def _create_ingested_job(
    client: TestClient, project_id: str, approval: dict, context: dict, *, key: str,
) -> dict:
    job = _prepare_video(
        client, project_id, approval, context, key=key, requested_duration_seconds=8,
    )
    path = f"/api/v2/projects/{project_id}/video-jobs/{job['id']}"
    submitted = client.post(f"{path}/submit")
    assert submitted.status_code == 200, submitted.text
    ingested = client.post(f"{path}/reconcile")
    assert ingested.status_code == 200 and ingested.json()["state"] == "ingested", ingested.text
    return ingested.json()


def _propose_segment(
    client: TestClient, project_id: str, video_job_id: str, expected_revision: int,
) -> dict:
    response = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{video_job_id}/segments",
        json={"inFrame": 0, "outFrame": 120, "expectedSelectionRevision": expected_revision},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_reopen_retains_history_bytes_and_other_selected_playback(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg tools are required for audiovisual retention proof")
    source = tmp_path / "synthetic-eight-second-take.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:size=576x1024:rate=24:duration=8",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8",
         "-frames:v", "192", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", "-y", str(source)],
        check=True, timeout=90,
    )
    original_bytes = source.read_bytes()
    provider = FakeH3(outputs=[original_bytes, original_bytes, original_bytes])
    _storage, client, project_id, approval, context = _project(tmp_path, provider)
    base = f"/api/v2/projects/{project_id}"

    rejected_job = _create_ingested_job(client, project_id, approval, context, key="review-reopen-first")
    other_job = _create_ingested_job(client, project_id, approval, context, key="review-reopen-other")
    target_job = _create_ingested_job(client, project_id, approval, context, key="review-reopen-target")
    rejected_segment = _propose_segment(client, project_id, rejected_job["id"], 0)
    other_segment = _propose_segment(client, project_id, other_job["id"], 0)
    target_segment = _propose_segment(client, project_id, target_job["id"], 0)
    rejected_preview = client.get(f"{base}/video-segments/{rejected_segment['id']}/preview").content
    other_preview = client.get(f"{base}/video-segments/{other_segment['id']}/preview").content
    target_preview = client.get(f"{base}/video-segments/{target_segment['id']}/preview").content

    first_rejection = client.post(f"{base}/video-jobs/{rejected_job['id']}/review", json={
        "decision": "reject", "reviewer": "creator", "note": "Keep this take as history.",
        "expectedSelectionRevision": 0,
    })
    assert first_rejection.status_code == 201
    reopen_without_selection = client.post(
        f"{base}/video-jobs/{rejected_job['id']}/review/reopen",
        json={"reviewer": "creator", "reason": "Reconsider the retained camera move.", "expectedSelectionRevision": 0},
    )
    assert reopen_without_selection.status_code == 201, reopen_without_selection.text
    assert reopen_without_selection.json()["decision"] == "reopen"
    assert reopen_without_selection.json()["selectionRevision"] == 1
    first_projection = next(
        item for item in client.get(f"{base}/video-jobs").json()["jobs"]
        if item["id"] == rejected_job["id"]
    )
    assert first_projection["selected"] is False and first_projection["selectionRevision"] == 1
    assert [item["decision"] for item in first_projection["reviews"]] == ["reject", "reopen"]
    assert first_projection["reviews"][0]["createdAt"] < first_projection["reviews"][1]["createdAt"]
    assert client.get(f"{base}/video-jobs/{rejected_job['id']}/media").content == original_bytes
    assert client.get(f"{base}/video-segments/{rejected_segment['id']}/preview").content == rejected_preview
    assert client.post(f"{base}/video-segments/{rejected_segment['id']}/select", json={
        "expectedSelectionRevision": 0,
    }).status_code == 409

    selected_other = client.post(f"{base}/video-segments/{other_segment['id']}/select", json={
        "reviewer": "creator", "note": "Keep current story playback.", "expectedSelectionRevision": 1,
    })
    assert selected_other.status_code == 201, selected_other.text
    assert client.get(f"{base}/video-jobs/{other_job['id']}/playback").content == other_preview

    target_rejection = client.post(f"{base}/video-jobs/{target_job['id']}/review", json={
        "decision": "reject", "reviewer": "creator", "note": "Reopen another retained take.",
        "expectedSelectionRevision": 2,
    })
    assert target_rejection.status_code == 201
    reopened = client.post(f"{base}/video-jobs/{target_job['id']}/review/reopen", json={
        "reviewer": "creator", "reason": "Owner wants to reconsider this camera path.",
        "expectedSelectionRevision": 2,
    })
    assert reopened.status_code == 201, reopened.text
    assert reopened.json()["selectionRevision"] == 3
    target_projection = next(
        item for item in client.get(f"{base}/video-jobs").json()["jobs"]
        if item["id"] == target_job["id"]
    )
    other_projection = next(
        item for item in client.get(f"{base}/video-jobs").json()["jobs"]
        if item["id"] == other_job["id"]
    )
    assert [item["decision"] for item in target_projection["reviews"]] == ["reject", "reopen"]
    assert other_projection["selected"] is True
    assert other_projection["playbackSegment"]["selectedRevision"] == 3
    assert client.get(f"{base}/video-jobs/{other_job['id']}/playback").content == other_preview
    assert client.post(f"{base}/video-segments/{target_segment['id']}/select", json={
        "expectedSelectionRevision": 2,
    }).status_code == 409

    selected_target = client.post(f"{base}/video-segments/{target_segment['id']}/select", json={
        "reviewer": "creator", "note": "Listen to this retained segment.",
        "expectedSelectionRevision": 3,
    })
    assert selected_target.status_code == 201, selected_target.text
    assert selected_target.json()["selected"] is True
    assert client.get(f"{base}/video-jobs/{target_job['id']}/playback").content == target_preview
    assert client.get(f"{base}/video-jobs/{target_job['id']}/media").content == original_bytes
    assert client.get(f"{base}/video-segments/{target_segment['id']}/preview").content == target_preview
    assert sha256(target_preview).hexdigest() == target_segment["derivativeHash"]
    assert len(provider.submits) == 3


@pytest.mark.parametrize(
    "failure",
    [
        "missing_fields", "blank_fields", "nonreject", "stale_token", "duplicate",
        "non_h3", "noningested", "tampered", "stale_currentness",
    ],
)
def test_reopen_refusals_do_not_append_review_events(
    tmp_path: Path, failure: str,
) -> None:
    provider = FakeH3()
    storage, client, project_id, approval, context = _project(tmp_path, provider)
    job = _prepare_video(client, project_id, approval, context, key=f"reopen-refusal-{failure}")
    base = f"/api/v2/projects/{project_id}/video-jobs/{job['id']}"
    if failure != "noningested":
        assert client.post(f"{base}/submit").status_code == 200
        assert client.post(f"{base}/reconcile").status_code == 200
    if failure not in {"missing_fields", "blank_fields", "nonreject", "noningested"}:
        assert client.post(f"{base}/review", json={
            "decision": "reject", "reviewer": "creator", "note": "Retain for explicit reconsideration.",
            "expectedSelectionRevision": 0,
        }).status_code == 201

    if failure == "stale_currentness":
        shot = context["shot"]
        asset = client.post(
            f"/api/v2/projects/{project_id}/managed-assets",
            files={"image": ("replacement-keyframe.png", _png(576, 1024), "image/png")},
            data={"origin": "replacement H3 fixture", "rights": "unknown", "declared_additions_json": "[]"},
        ).json()
        draft = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={
                "editorScope": "visual_intent",
                "entityId": f"{shot.id}:{asset['id']}",
                "baseCanonicalRevision": context["revision"],
                "expectedDraftRevision": 0,
                "payload": {
                    "assetId": asset["id"], "shotId": shot.id, "role": "shot_keyframe",
                    "identityIntent": "Rebind the take to this reviewed keyframe.",
                    "sourceRefs": ["offline H3 replacement fixture"],
                },
            },
        )
        assert draft.status_code == 200, draft.text
        intent = client.post(
            f"/api/v2/projects/{project_id}/managed-assets/{asset['id']}/visual-intents",
            json={
                "shotId": shot.id, "role": "shot_keyframe",
                "identityIntent": "Rebind the take to this reviewed keyframe.",
                "sourceRefs": ["offline H3 replacement fixture"],
                "consumedDraft": {
                    "editorScope": "visual_intent", "entityId": f"{shot.id}:{asset['id']}",
                    "draftRevision": draft.json()["draftRevision"],
                },
            },
        ).json()
        binding = client.post(
            f"/api/v2/projects/{project_id}/reviewed-keyframes",
            json={
                "assetId": asset["id"], "shotId": shot.id, "sceneId": shot.scene_id,
                "expectedSelectionRevision": context["selection"]["selectionRevision"],
                "storyboardRevision": context["revision"], "approvalId": approval["id"],
                "compatibilityNote": "The replacement is explicitly reviewed against the frozen H3 profile.",
                "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
            },
        )
        assert binding.status_code == 201, binding.text
        projected_job = next(
            item for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"]
            if item["id"] == job["id"]
        )
        assert projected_job["current"] is False

    if failure == "missing_fields":
        response = client.post(f"{base}/review/reopen", json={"expectedSelectionRevision": 0})
        assert response.status_code == 422
    elif failure == "blank_fields":
        response = client.post(f"{base}/review/reopen", json={
            "reviewer": "  ", "reason": "  ", "expectedSelectionRevision": 0,
        })
        assert response.status_code == 422
    elif failure == "nonreject":
        response = client.post(f"{base}/review/reopen", json={
            "reviewer": "creator", "reason": "No rejection exists.", "expectedSelectionRevision": 0,
        })
        assert response.status_code == 409
    elif failure == "noningested":
        response = client.post(f"{base}/review/reopen", json={
            "reviewer": "creator", "reason": "This job has no ingested take.", "expectedSelectionRevision": 0,
        })
        assert response.status_code == 409
    elif failure == "stale_token":
        response = client.post(f"{base}/review/reopen", json={
            "reviewer": "creator", "reason": "Selection token is stale.", "expectedSelectionRevision": 1,
        })
        assert response.status_code == 409
    elif failure == "duplicate":
        first = client.post(f"{base}/review/reopen", json={
            "reviewer": "creator", "reason": "First explicit reopen.", "expectedSelectionRevision": 0,
        })
        assert first.status_code == 201
        response = client.post(f"{base}/review/reopen", json={
            "reviewer": "creator", "reason": "Duplicate reopen.", "expectedSelectionRevision": 1,
        })
        assert response.status_code == 409
    elif failure == "non_h3":
        database = storage.projects.open(project_id)
        try:
            connection = sqlite3.connect(database.database_path)
            try:
                row = connection.execute(
                    "SELECT snapshot, idempotency_key FROM v2_video_jobs WHERE id = ?", (job["id"],)
                ).fetchone()
                assert row is not None
                snapshot = json.loads(row[0])
                snapshot["provider"]["adapterId"] = "other_adapter"
                connection.execute(
                    "UPDATE v2_video_jobs SET snapshot = ?, snapshot_hash = ?, request_hash = ? WHERE id = ?",
                    (json.dumps(snapshot), stable_hash(snapshot), stable_hash({"snapshot": snapshot, "idempotencyKey": row[1]}), job["id"]),
                )
                connection.commit()
            finally:
                connection.close()
        finally:
            database.close()
        response = client.post(f"{base}/review/reopen", json={
            "reviewer": "creator", "reason": "The source is no longer H3.", "expectedSelectionRevision": 0,
        })
        assert response.status_code == 409
    elif failure == "stale_currentness":
        response = client.post(f"{base}/review/reopen", json={
            "reviewer": "creator", "reason": "The reviewed keyframe binding changed.",
            "expectedSelectionRevision": 0,
        })
        assert response.status_code == 409
    else:
        database = storage.projects.open(project_id)
        try:
            connection = sqlite3.connect(database.database_path)
            try:
                connection.execute(
                    "UPDATE v2_video_jobs SET snapshot_hash = ? WHERE id = ?", ("0" * 64, job["id"])
                )
                connection.commit()
            finally:
                connection.close()
        finally:
            database.close()
        response = client.post(f"{base}/review/reopen", json={
            "reviewer": "creator", "reason": "Frozen evidence was tampered.", "expectedSelectionRevision": 0,
        })
        assert response.status_code == 409

    listed = client.get(f"/api/v2/projects/{project_id}/video-jobs")
    retained = next(item for item in listed.json()["jobs"] if item["id"] == job["id"])
    expected_count = 2 if failure == "duplicate" else 1 if failure not in {
        "missing_fields", "blank_fields", "nonreject", "noningested",
    } else 0
    assert len(retained["reviews"]) == expected_count


def test_reopen_contract_requires_trimmed_nonblank_reviewer_and_reason() -> None:
    request = VideoReviewReopenRequest.model_validate({
        "reviewer": " Creator ", "reason": " Consider again ", "expectedSelectionRevision": 0,
    })
    assert request.reviewer == "Creator" and request.reason == "Consider again"
    with pytest.raises(ValueError):
        VideoReviewReopenRequest.model_validate({
            "reviewer": " ", "reason": "valid", "expectedSelectionRevision": 0,
        })


def test_reopen_requires_project_recovery_acknowledgement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _storage, client, project_id, approval, context = _project(tmp_path, FakeH3())
    job = _create_ingested_job(client, project_id, approval, context, key="reopen-recovery-ack")
    base = f"/api/v2/projects/{project_id}/video-jobs/{job['id']}"
    assert client.post(f"{base}/review", json={
        "decision": "reject", "reviewer": "creator", "note": "Retain for recovery test.",
        "expectedSelectionRevision": 0,
    }).status_code == 201

    def require_acknowledgement(_store: ProjectStore) -> None:
        raise ProjectRecoveryRequiredError("recovery_required: acknowledge restored unfinished work before generation")

    monkeypatch.setattr(ProjectStore, "require_recovery_acknowledged", require_acknowledgement)
    response = client.post(f"{base}/review/reopen", json={
        "reviewer": "creator", "reason": "Reconsider after recovery.", "expectedSelectionRevision": 0,
    })
    assert response.status_code == 422
    history = client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"][0]["reviews"]
    assert [item["decision"] for item in history] == ["reject"]
