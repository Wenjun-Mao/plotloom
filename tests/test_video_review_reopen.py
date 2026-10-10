"""Explicit reopening of retained, rejected H3 takes."""

from __future__ import annotations

from pathlib import Path

import pytest

from plotloom.project_storage.project_handle import (
    ProjectRecoveryRequiredError,
    ProjectStore,
)
from plotloom.video_contracts import VideoReviewReopenRequest
from tests.video_review_reopen_fixtures import _create_ingested_job, _project
from tests.video_storage_fixtures import (
    FakeH3,
)


def test_reopen_contract_requires_trimmed_nonblank_reviewer_and_reason() -> None:
    request = VideoReviewReopenRequest.model_validate(
        {
            "reviewer": " Creator ",
            "reason": " Consider again ",
            "expectedSelectionRevision": 0,
        }
    )
    assert request.reviewer == "Creator" and request.reason == "Consider again"
    with pytest.raises(ValueError):
        VideoReviewReopenRequest.model_validate(
            {
                "reviewer": " ",
                "reason": "valid",
                "expectedSelectionRevision": 0,
            }
        )


def test_reopen_requires_project_recovery_acknowledgement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _storage, client, project_id, approval, context = _project(tmp_path, FakeH3())
    job = _create_ingested_job(
        client, project_id, approval, context, key="reopen-recovery-ack"
    )
    base = f"/api/v2/projects/{project_id}/video-jobs/{job['id']}"
    assert (
        client.post(
            f"{base}/review",
            json={
                "decision": "reject",
                "reviewer": "creator",
                "note": "Retain for recovery test.",
                "expectedSelectionRevision": 0,
            },
        ).status_code
        == 201
    )

    def require_acknowledgement(_store: ProjectStore) -> None:
        raise ProjectRecoveryRequiredError(
            "recovery_required: acknowledge restored unfinished work before generation"
        )

    monkeypatch.setattr(
        ProjectStore, "require_recovery_acknowledged", require_acknowledgement
    )
    response = client.post(
        f"{base}/review/reopen",
        json={
            "reviewer": "creator",
            "reason": "Reconsider after recovery.",
            "expectedSelectionRevision": 0,
        },
    )
    assert response.status_code == 422
    history = client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"][0][
        "reviews"
    ]
    assert [item["decision"] for item in history] == ["reject"]
