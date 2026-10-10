"""Explicit video review-reopen retention contracts."""

from __future__ import annotations

import shutil
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from tests.video_review_reopen_fixtures import (
    _create_ingested_job,
    _project,
    _propose_segment,
)
from tests.video_storage_fixtures import (
    FakeH3,
)


def test_reopen_retains_history_bytes_and_other_selected_playback(
    tmp_path: Path,
) -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg tools are required for audiovisual retention proof")
    source = tmp_path / "synthetic-eight-second-take.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:size=576x1024:rate=24:duration=8",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=8",
            "-frames:v",
            "192",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            "-y",
            str(source),
        ],
        check=True,
        timeout=90,
    )
    original_bytes = source.read_bytes()
    provider = FakeH3(outputs=[original_bytes, original_bytes, original_bytes])
    _storage, client, project_id, approval, context = _project(tmp_path, provider)
    base = f"/api/v2/projects/{project_id}"

    rejected_job = _create_ingested_job(
        client, project_id, approval, context, key="review-reopen-first"
    )
    other_job = _create_ingested_job(
        client, project_id, approval, context, key="review-reopen-other"
    )
    target_job = _create_ingested_job(
        client, project_id, approval, context, key="review-reopen-target"
    )
    rejected_segment = _propose_segment(client, project_id, rejected_job["id"], 0)
    other_segment = _propose_segment(client, project_id, other_job["id"], 0)
    target_segment = _propose_segment(client, project_id, target_job["id"], 0)
    rejected_preview = client.get(
        f"{base}/video-segments/{rejected_segment['id']}/preview"
    ).content
    other_preview = client.get(
        f"{base}/video-segments/{other_segment['id']}/preview"
    ).content
    target_preview = client.get(
        f"{base}/video-segments/{target_segment['id']}/preview"
    ).content

    first_rejection = client.post(
        f"{base}/video-jobs/{rejected_job['id']}/review",
        json={
            "decision": "reject",
            "reviewer": "creator",
            "note": "Keep this take as history.",
            "expectedSelectionRevision": 0,
        },
    )
    assert first_rejection.status_code == 201
    reopen_without_selection = client.post(
        f"{base}/video-jobs/{rejected_job['id']}/review/reopen",
        json={
            "reviewer": "creator",
            "reason": "Reconsider the retained camera move.",
            "expectedSelectionRevision": 0,
        },
    )
    assert reopen_without_selection.status_code == 201, reopen_without_selection.text
    assert reopen_without_selection.json()["decision"] == "reopen"
    assert reopen_without_selection.json()["selectionRevision"] == 1
    first_projection = next(
        item
        for item in client.get(f"{base}/video-jobs").json()["jobs"]
        if item["id"] == rejected_job["id"]
    )
    assert (
        first_projection["selected"] is False
        and first_projection["selectionRevision"] == 1
    )
    assert [item["decision"] for item in first_projection["reviews"]] == [
        "reject",
        "reopen",
    ]
    assert (
        first_projection["reviews"][0]["createdAt"]
        < first_projection["reviews"][1]["createdAt"]
    )
    assert (
        client.get(f"{base}/video-jobs/{rejected_job['id']}/media").content
        == original_bytes
    )
    assert (
        client.get(f"{base}/video-segments/{rejected_segment['id']}/preview").content
        == rejected_preview
    )
    assert (
        client.post(
            f"{base}/video-segments/{rejected_segment['id']}/select",
            json={
                "expectedSelectionRevision": 0,
            },
        ).status_code
        == 409
    )

    selected_other = client.post(
        f"{base}/video-segments/{other_segment['id']}/select",
        json={
            "reviewer": "creator",
            "note": "Keep current story playback.",
            "expectedSelectionRevision": 1,
        },
    )
    assert selected_other.status_code == 201, selected_other.text
    assert (
        client.get(f"{base}/video-jobs/{other_job['id']}/playback").content
        == other_preview
    )

    target_rejection = client.post(
        f"{base}/video-jobs/{target_job['id']}/review",
        json={
            "decision": "reject",
            "reviewer": "creator",
            "note": "Reopen another retained take.",
            "expectedSelectionRevision": 2,
        },
    )
    assert target_rejection.status_code == 201
    reopened = client.post(
        f"{base}/video-jobs/{target_job['id']}/review/reopen",
        json={
            "reviewer": "creator",
            "reason": "Owner wants to reconsider this camera path.",
            "expectedSelectionRevision": 2,
        },
    )
    assert reopened.status_code == 201, reopened.text
    assert reopened.json()["selectionRevision"] == 3
    target_projection = next(
        item
        for item in client.get(f"{base}/video-jobs").json()["jobs"]
        if item["id"] == target_job["id"]
    )
    other_projection = next(
        item
        for item in client.get(f"{base}/video-jobs").json()["jobs"]
        if item["id"] == other_job["id"]
    )
    assert [item["decision"] for item in target_projection["reviews"]] == [
        "reject",
        "reopen",
    ]
    assert other_projection["selected"] is True
    assert other_projection["playbackSegment"]["selectedRevision"] == 3
    assert (
        client.get(f"{base}/video-jobs/{other_job['id']}/playback").content
        == other_preview
    )
    assert (
        client.post(
            f"{base}/video-segments/{target_segment['id']}/select",
            json={
                "expectedSelectionRevision": 2,
            },
        ).status_code
        == 409
    )

    selected_target = client.post(
        f"{base}/video-segments/{target_segment['id']}/select",
        json={
            "reviewer": "creator",
            "note": "Listen to this retained segment.",
            "expectedSelectionRevision": 3,
        },
    )
    assert selected_target.status_code == 201, selected_target.text
    assert selected_target.json()["selected"] is True
    assert (
        client.get(f"{base}/video-jobs/{target_job['id']}/playback").content
        == target_preview
    )
    assert (
        client.get(f"{base}/video-jobs/{target_job['id']}/media").content
        == original_bytes
    )
    assert (
        client.get(f"{base}/video-segments/{target_segment['id']}/preview").content
        == target_preview
    )
    assert sha256(target_preview).hexdigest() == target_segment["derivativeHash"]
    assert len(provider.submits) == 3
