"""test project storage video recovery behavior contracts."""

from __future__ import annotations

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
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_ingestion import probe_video
from plotloom.video_provider import VideoBackendInstanceIdentity
from tests.project_storage_fixtures import FixtureResolver as _FixtureResolver
from tests.project_storage_fixtures import fixture_profile as _fixture_profile
from tests.video_prompt_fixtures import reviewed_h3_body as _reviewed_video_body
from tests.video_storage_fixtures import FakeH3, _approved_keyframe


@pytest.mark.parametrize(
    "authored_units,in_frame,out_frame,playback_intent",
    [
        (6_000, 24, 168, "segment_required"),
        (7_500, 6, 186, "segment_required"),
        (8_000, 0, 192, "source_exact"),
    ],
)
def test_synthetic_reviewed_segment_survives_reopen_and_blocks_old_revision(
    tmp_path: Path,
    authored_units: int,
    in_frame: int,
    out_frame: int,
    playback_intent: str,
) -> None:
    """An offline 8-second H3-shaped take is never playable before window review."""

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg tools are required for synthetic audiovisual proof")
    source = tmp_path / "explicitly-synthetic-eight-second-take.mp4"
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
    provider = FakeH3(outputs=[source.read_bytes()])
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "project" / "outputs",
        application_data_root=tmp_path / "project" / "application",
    )
    client = TestClient(
        create_project_folder_authoring_app(
            storage,
            video_provider=provider,
            video_adapter=MiniMaxH3GatewayAdapter(),
            video_probe=probe_video,
        )
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    changed = board.model_copy(
        update={
            "shots": [
                board.shots[0].model_copy(update={"duration_units": authored_units}),
                *board.shots[1:],
            ],
        }
    )
    store.update_stage(
        StageName.STORYBOARD,
        changed,
        expected_revision=store.authoring.get_stage_head(
            project_id, StageName.STORYBOARD
        ).revision,
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    base = f"/api/v2/projects/{project_id}"
    prepared = client.post(
        f"{base}/video-jobs",
        json=_reviewed_video_body(
            client,
            project_id,
            {
                "approvalId": approval["id"],
                "shotId": context["shot"].id,
                "storyboardRevision": context["revision"],
                "expectedSelectionRevision": context["selection"]["selectionRevision"],
                "idempotencyKey": "synthetic-reviewed-segment-8-to-6",
                "requestedDurationSeconds": 8,
                "playbackIntent": playback_intent,
                "aspectPolicy": "reject_mismatch",
                "seed": 31,
            },
        ),
    )
    assert prepared.status_code == 201, prepared.text
    job_id = prepared.json()["id"]
    assert (
        prepared.json()["snapshot"]["sourceTiming"]["durationUnits"] == authored_units
    )
    assert client.post(f"{base}/video-jobs/{job_id}/submit").status_code == 200
    ingested = client.post(f"{base}/video-jobs/{job_id}/reconcile")
    assert ingested.status_code == 200 and ingested.json()["state"] == "ingested", (
        ingested.text
    )
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    whole_take_selection = client.post(
        f"{base}/video-jobs/{job_id}/review",
        json={
            "reviewer": "synthetic test operator",
            "decision": "select",
            "note": "A whole H3 take must not bypass segment review.",
            "expectedSelectionRevision": 0,
        },
    )
    assert whole_take_selection.status_code == 409
    proposed = client.post(
        f"{base}/video-jobs/{job_id}/segments",
        json={
            "inFrame": in_frame,
            "outFrame": out_frame,
            "expectedSelectionRevision": 0,
        },
    )
    assert proposed.status_code == 201, proposed.text
    segment = proposed.json()
    assert segment["derivativeProbe"]["frameCount"] == authored_units * 24 // 1_000
    assert (
        client.get(f"{base}/video-segments/{segment['id']}/preview").status_code == 200
    )
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    assert (
        client.post(
            f"{base}/video-jobs/{job_id}/discard", json={"expectedSelectionRevision": 0}
        ).status_code
        == 409
    )
    proposal_snapshot = storage.recovery.create_snapshot(project_id)
    assert any(
        item.relative_path.endswith(segment["derivativeHash"])
        for item in proposal_snapshot.manifest.files
    )
    selected = client.post(
        f"{base}/video-segments/{segment['id']}/select",
        json={
            "expectedSelectionRevision": 0,
        },
    )
    assert selected.status_code == 201, selected.text
    assert selected.json()["selected"] is True
    selected_job = client.get(f"{base}/video-jobs").json()["jobs"][0]
    assert selected_job["reviews"][-1]["reviewer"] == ""
    assert selected_job["reviews"][-1]["note"] == ""
    assert (
        client.post(
            f"{base}/video-segments/{segment['id']}/select",
            json={
                "reviewer": "synthetic test operator",
                "note": "Stale concurrent selection.",
                "expectedSelectionRevision": 0,
            },
        ).status_code
        == 409
    )
    playback = client.get(f"{base}/video-jobs/{job_id}/playback")
    assert (
        playback.status_code == 200
        and sha256(playback.content).hexdigest() == segment["derivativeHash"]
    )
    assert (
        client.post(
            f"{base}/video-jobs/{job_id}/discard", json={"expectedSelectionRevision": 1}
        ).status_code
        == 409
    )
    snapshot = storage.recovery.create_snapshot(project_id)
    assert any(
        item.relative_path.endswith(segment["derivativeHash"])
        for item in snapshot.manifest.files
    )
    restored_storage = ProjectFolderStorage(
        outputs_root=tmp_path / "restored" / "outputs",
        application_data_root=tmp_path / "restored" / "application",
    )
    restored_storage.recovery.restore(Path(snapshot.location))
    restored_client = TestClient(create_project_folder_authoring_app(restored_storage))
    assert (
        restored_client.get(f"{base}/video-jobs/{job_id}/playback").content
        == playback.content
    )
    assert (
        restored_client.get(f"{base}/video-segments/{segment['id']}/preview").content
        == playback.content
    )
    rejected = restored_client.post(
        f"{base}/video-jobs/{job_id}/review",
        json={
            "decision": "reject",
            "note": "短",
            "expectedSelectionRevision": 1,
        },
    )
    assert rejected.status_code == 201 and rejected.json()["selectionRevision"] == 2
    assert rejected.json()["reviewer"] == "" and rejected.json()["note"] == "短"
    assert (
        restored_client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    )
    assert restored_client.get(f"{base}/video-jobs/{job_id}/media").status_code == 200
    reopened = storage.projects.open(project_id)
    reopened.close()
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 200
    with sqlite3.connect(reopened.database_path) as connection:
        connection.execute(
            "UPDATE v2_video_jobs SET output_hash = ? WHERE id = ?", ("0" * 64, job_id)
        )
        connection.commit()
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    with sqlite3.connect(reopened.database_path) as connection:
        connection.execute(
            "UPDATE v2_video_jobs SET output_hash = ? WHERE id = ?",
            (ingested.json()["outputHash"], job_id),
        )
        connection.commit()
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 200
    edited = storage.projects.open(project_id)
    board = edited.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    changed = board.model_copy(
        update={
            "shots": [
                board.shots[0].model_copy(
                    update={"action": "Synthetic fixture action changed."}
                ),
                *board.shots[1:],
            ],
        }
    )
    edited.update_stage(
        StageName.STORYBOARD,
        changed,
        expected_revision=edited.authoring.get_stage_head(
            project_id, StageName.STORYBOARD
        ).revision,
    )
    edited.close()
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    assert client.get(f"{base}/video-jobs/{job_id}/media").status_code == 200


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://user:password@127.0.0.1:9010",
        "http://127.0.0.1:9010/?X-Amz-Signature=not-allowed",
        "ftp://127.0.0.1:9010/?X-Amz-Signature=not-allowed",
    ],
)
def test_backend_instance_identity_rejects_credentials_signed_urls_and_non_http_endpoints(
    endpoint: str,
) -> None:
    with pytest.raises(ValueError, match="secret-free|credential-free HTTP"):
        VideoBackendInstanceIdentity.from_public_configuration(
            "fixture_h3_endpoint_v1", {"endpoint": endpoint}
        )
