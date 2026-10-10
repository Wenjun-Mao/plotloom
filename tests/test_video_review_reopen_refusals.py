"""Explicit video review-reopen refusal contracts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from plotloom.persistence.codec import stable_hash
from tests.video_review_reopen_fixtures import (
    _project,
)
from tests.video_storage_fixtures import (
    FakeH3,
    _png,
    _prepare_video,
)


@pytest.mark.parametrize(
    "failure",
    [
        "missing_fields",
        "blank_fields",
        "nonreject",
        "stale_token",
        "duplicate",
        "non_h3",
        "noningested",
        "tampered",
        "stale_currentness",
    ],
)
def test_reopen_refusals_do_not_append_review_events(
    tmp_path: Path,
    failure: str,
) -> None:
    provider = FakeH3()
    storage, client, project_id, approval, context = _project(tmp_path, provider)
    job = _prepare_video(
        client, project_id, approval, context, key=f"reopen-refusal-{failure}"
    )
    base = f"/api/v2/projects/{project_id}/video-jobs/{job['id']}"
    if failure != "noningested":
        assert client.post(f"{base}/submit").status_code == 200
        assert client.post(f"{base}/reconcile").status_code == 200
    if failure not in {"missing_fields", "blank_fields", "nonreject", "noningested"}:
        assert (
            client.post(
                f"{base}/review",
                json={
                    "decision": "reject",
                    "reviewer": "creator",
                    "note": "Retain for explicit reconsideration.",
                    "expectedSelectionRevision": 0,
                },
            ).status_code
            == 201
        )

    if failure == "stale_currentness":
        shot = context["shot"]
        asset = client.post(
            f"/api/v2/projects/{project_id}/managed-assets",
            files={"image": ("replacement-keyframe.png", _png(576, 1024), "image/png")},
            data={
                "origin": "replacement H3 fixture",
                "rights": "unknown",
                "declared_additions_json": "[]",
            },
        ).json()
        draft = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={
                "editorScope": "visual_intent",
                "entityId": f"{shot.id}:{asset['id']}",
                "baseCanonicalRevision": context["revision"],
                "expectedDraftRevision": 0,
                "payload": {
                    "assetId": asset["id"],
                    "shotId": shot.id,
                    "role": "shot_keyframe",
                    "identityIntent": "Rebind the take to this reviewed keyframe.",
                    "sourceRefs": ["offline H3 replacement fixture"],
                },
            },
        )
        assert draft.status_code == 200, draft.text
        intent = client.post(
            f"/api/v2/projects/{project_id}/managed-assets/{asset['id']}/visual-intents",
            json={
                "shotId": shot.id,
                "role": "shot_keyframe",
                "identityIntent": "Rebind the take to this reviewed keyframe.",
                "sourceRefs": ["offline H3 replacement fixture"],
                "consumedDraft": {
                    "editorScope": "visual_intent",
                    "entityId": f"{shot.id}:{asset['id']}",
                    "draftRevision": draft.json()["draftRevision"],
                },
            },
        ).json()
        binding = client.post(
            f"/api/v2/projects/{project_id}/reviewed-keyframes",
            json={
                "assetId": asset["id"],
                "shotId": shot.id,
                "sceneId": shot.scene_id,
                "expectedSelectionRevision": context["selection"]["selectionRevision"],
                "storyboardRevision": context["revision"],
                "approvalId": approval["id"],
                "compatibilityNote": "The replacement is explicitly reviewed against the frozen H3 profile.",
                "visualIntentId": intent["id"],
                "visualIntentRevision": intent["revision"],
            },
        )
        assert binding.status_code == 201, binding.text
        projected_job = next(
            item
            for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()[
                "jobs"
            ]
            if item["id"] == job["id"]
        )
        assert projected_job["current"] is False

    if failure == "missing_fields":
        response = client.post(
            f"{base}/review/reopen", json={"expectedSelectionRevision": 0}
        )
        assert response.status_code == 422
    elif failure == "blank_fields":
        response = client.post(
            f"{base}/review/reopen",
            json={
                "reviewer": "  ",
                "reason": "  ",
                "expectedSelectionRevision": 0,
            },
        )
        assert response.status_code == 422
    elif failure == "nonreject":
        response = client.post(
            f"{base}/review/reopen",
            json={
                "reviewer": "creator",
                "reason": "No rejection exists.",
                "expectedSelectionRevision": 0,
            },
        )
        assert response.status_code == 409
    elif failure == "noningested":
        response = client.post(
            f"{base}/review/reopen",
            json={
                "reviewer": "creator",
                "reason": "This job has no ingested take.",
                "expectedSelectionRevision": 0,
            },
        )
        assert response.status_code == 409
    elif failure == "stale_token":
        response = client.post(
            f"{base}/review/reopen",
            json={
                "reviewer": "creator",
                "reason": "Selection token is stale.",
                "expectedSelectionRevision": 1,
            },
        )
        assert response.status_code == 409
    elif failure == "duplicate":
        first = client.post(
            f"{base}/review/reopen",
            json={
                "reviewer": "creator",
                "reason": "First explicit reopen.",
                "expectedSelectionRevision": 0,
            },
        )
        assert first.status_code == 201
        response = client.post(
            f"{base}/review/reopen",
            json={
                "reviewer": "creator",
                "reason": "Duplicate reopen.",
                "expectedSelectionRevision": 1,
            },
        )
        assert response.status_code == 409
    elif failure == "non_h3":
        database = storage.projects.open(project_id)
        try:
            connection = sqlite3.connect(database.database_path)
            try:
                row = connection.execute(
                    "SELECT snapshot, idempotency_key FROM v2_video_jobs WHERE id = ?",
                    (job["id"],),
                ).fetchone()
                assert row is not None
                snapshot = json.loads(row[0])
                snapshot["provider"]["adapterId"] = "other_adapter"
                connection.execute(
                    "UPDATE v2_video_jobs SET snapshot = ?, snapshot_hash = ?, request_hash = ? WHERE id = ?",
                    (
                        json.dumps(snapshot),
                        stable_hash(snapshot),
                        stable_hash({"snapshot": snapshot, "idempotencyKey": row[1]}),
                        job["id"],
                    ),
                )
                connection.commit()
            finally:
                connection.close()
        finally:
            database.close()
        response = client.post(
            f"{base}/review/reopen",
            json={
                "reviewer": "creator",
                "reason": "The source is no longer H3.",
                "expectedSelectionRevision": 0,
            },
        )
        assert response.status_code == 409
    elif failure == "stale_currentness":
        response = client.post(
            f"{base}/review/reopen",
            json={
                "reviewer": "creator",
                "reason": "The reviewed keyframe binding changed.",
                "expectedSelectionRevision": 0,
            },
        )
        assert response.status_code == 409
    else:
        database = storage.projects.open(project_id)
        try:
            connection = sqlite3.connect(database.database_path)
            try:
                connection.execute(
                    "UPDATE v2_video_jobs SET snapshot_hash = ? WHERE id = ?",
                    ("0" * 64, job["id"]),
                )
                connection.commit()
            finally:
                connection.close()
        finally:
            database.close()
        response = client.post(
            f"{base}/review/reopen",
            json={
                "reviewer": "creator",
                "reason": "Frozen evidence was tampered.",
                "expectedSelectionRevision": 0,
            },
        )
        assert response.status_code == 409

    listed = client.get(f"/api/v2/projects/{project_id}/video-jobs")
    retained = next(item for item in listed.json()["jobs"] if item["id"] == job["id"])
    expected_count = (
        2
        if failure == "duplicate"
        else 1
        if failure
        not in {
            "missing_fields",
            "blank_fields",
            "nonreject",
            "noningested",
        }
        else 0
    )
    assert len(retained["reviews"]) == expected_count
