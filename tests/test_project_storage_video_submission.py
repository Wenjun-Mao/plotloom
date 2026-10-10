"""test project storage video submission behavior contracts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.canonical_schema import DialogueCue
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_ingestion import ObservedVideo
from tests.image_identity_fixtures import (
    install_visible_fixture_character as _install_visible_fixture_character,
)
from tests.project_storage_fixtures import FixtureResolver as _FixtureResolver
from tests.project_storage_fixtures import fixture_profile as _fixture_profile
from tests.video_prompt_fixtures import reviewed_h3_body as _reviewed_video_body
from tests.video_storage_fixtures import (
    FakeH3,
    _approved_keyframe,
    _fixture_app,
    _png,
    _prepare_video,
    _select_character_reference,
)


def test_eight_second_h3_job_freezes_output_contract_and_survives_restart(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    job = _prepare_video(
        client,
        project_id,
        approval,
        context,
        key="qualified-eight-seconds",
        requested_duration_seconds=8,
    )
    request = job["snapshot"]["request"]
    assert request["durationSeconds"] == 8
    assert request["frameCount"] == 192
    assert request["fps"] == 24
    restarted = TestClient(
        create_project_folder_authoring_app(
            storage,
            video_provider=provider,
            video_adapter=MiniMaxH3GatewayAdapter(),
            video_probe=lambda _content: ObservedVideo(
                8.0, 576, 1024, "h264", "aac", frame_rate=24, frame_count=192
            ),
        )
    )
    submitted = restarted.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit"
    )
    assert submitted.status_code == 200 and provider.submits[-1]["durationSeconds"] == 8
    ingested = restarted.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/reconcile"
    )
    assert ingested.status_code == 200
    assert ingested.json()["observed"]["frameCount"] == 192

    rejected = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json={
            "approvalId": approval["id"],
            "shotId": context["shot"].id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": "source-mismatched-seven-seconds",
            "requestedDurationSeconds": 7,
            "aspectPolicy": "reject_mismatch",
        },
    )
    assert rejected.status_code == 409


def test_h3_reviewed_directions_preview_bind_and_dispatch_after_restart(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    _install_visible_fixture_character(store)
    beats = store.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS)
    cue = DialogueCue(
        id="fixture-line",
        beat_id=beats.beats[0].id,
        order=1,
        speaker_id="fixture-hero",
        voice_over=None,
        text="嗯",
        language="zh-CN",
        delivery="natural",
        performance_notes="",
        estimated_duration_units=500,
    )
    store.update_stage(
        StageName.SCENE_BEATS,
        beats.model_copy(update={"dialogue_cues": [cue]}),
        expected_revision=store.authoring.get_stage_head(
            project_id, StageName.SCENE_BEATS
        ).revision,
    )
    board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    store.update_stage(
        StageName.STORYBOARD,
        board.model_copy(
            update={
                "shots": [
                    board.shots[0].model_copy(
                        update={
                            "cue_ids": [cue.id],
                            "duration_units": 1_000,
                            "action": "沈岚把铜质熔断器放在两条并列插槽之间。",
                        }
                    ),
                    *board.shots[1:],
                ]
            }
        ),
        expected_revision=store.authoring.get_stage_head(
            project_id, StageName.STORYBOARD
        ).revision,
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    _select_character_reference(
        client,
        project_id,
        context,
        asset_id=context["selection"]["assetId"],
        expected_revision=0,
        note="Use the reviewed fixture still for the visible speaker.",
    )
    body = {
        "approvalId": approval["id"],
        "shotId": context["shot"].id,
        "storyboardRevision": context["revision"],
        "expectedSelectionRevision": context["selection"]["selectionRevision"],
        "idempotencyKey": "reviewed-english-directions",
        "aspectPolicy": "reject_mismatch",
        "seed": 31,
        "playbackIntent": "segment_required",
    }
    refused = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=body)
    assert refused.status_code == 409 and provider.submits == []
    sources_response = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/prompt-preview", json=body
    )
    assert sources_response.status_code == 200, sources_response.text
    sources = sources_response.json()
    assert sources["compiledPrompt"] is None
    assert any(
        source["path"] == "shot.action"
        and source["text"] == "沈岚把铜质熔断器放在两条并列插槽之间。"
        for source in sources["sources"]
    )
    reviewed = {
        "sourceHash": sources["sourceHash"],
        "reviewedEnglish": True,
        "fields": [
            {
                "path": source["path"],
                "english": (
                    "The keeper places the brass fuse between the two parallel sockets."
                    if source["path"] == "shot.action"
                    else "A small metallic contact sound accompanies the visible movement."
                    if source["path"] == "reviewedSoundscape"
                    else source["text"]
                ),
            }
            for source in sources["sources"]
        ],
    }
    full_preview = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/prompt-preview",
        json={**body, "reviewedDirections": reviewed},
    )
    assert full_preview.status_code == 200, full_preview.text
    prompt = full_preview.json()["compiledPrompt"]
    assert "沈岚把铜质熔断器放在两条并列插槽之间。" not in prompt
    assert (
        "The keeper places the brass fuse between the two parallel sockets." in prompt
    )
    assert "<d>[Chinese] 嗯</d>" in prompt
    assert "only vocal utterance" not in prompt
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs",
            json={
                **body,
                "reviewedDirections": {**reviewed, "sourceHash": "0" * 64},
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs",
            json={
                **body,
                "reviewedDirections": reviewed,
            },
        ).status_code
        == 409
    )
    reviewed["promptSha256"] = full_preview.json()["compiledPromptSha256"]
    prepared = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json={**body, "reviewedDirections": reviewed},
    )
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    assert (
        job["snapshot"]["compilerVersion"]
        == "plotloom.h3-reviewed-frame.v5-presentation"
    )
    assert job["snapshot"]["shot"]["action"] == "沈岚把铜质熔断器放在两条并列插槽之间。"
    assert job["snapshot"]["compiledPrompt"] == prompt
    assert job["snapshot"]["reviewedDirections"] == reviewed
    restarted = TestClient(
        create_project_folder_authoring_app(
            storage,
            video_provider=provider,
            video_adapter=MiniMaxH3GatewayAdapter(),
        )
    )
    submitted = restarted.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit"
    )
    assert submitted.status_code == 200, submitted.text
    assert provider.submits == [
        {
            "prompt": prompt,
            "quality": 8,
            "resolution": "576x1024",
            "aspectPolicy": "reject_mismatch",
            "seed": 31,
            "durationSeconds": 5,
        }
    ]


def test_row_duration_tamper_cannot_change_a_frozen_h3_submission(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    job = _prepare_video(
        client, project_id, approval, context, key="row-duration-tamper"
    )
    store = storage.projects.open(project_id)
    try:
        database = store.database_path
    finally:
        store.close()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE v2_video_jobs SET requested_seconds = 8 WHERE id = ?", (job["id"],)
        )
    rejected = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit"
    )
    assert rejected.status_code == 409
    assert provider.submits == []


def test_explicit_h3_gateway_crop_freezes_original_bytes_across_restart_and_tamper_stales(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    original = _png(941, 1672)
    approval, context = _approved_keyframe(
        client, storage, project_id, keyframe_bytes=original
    )
    body = {
        "approvalId": approval["id"],
        "shotId": context["shot"].id,
        "storyboardRevision": context["revision"],
        "expectedSelectionRevision": context["selection"]["selectionRevision"],
        "idempotencyKey": "explicit-gateway-crop",
        "aspectPolicy": "cover_center_crop",
        "allowCenterCrop": True,
        "allowLetterbox": False,
        "seed": 41,
    }
    prepared = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json=_reviewed_video_body(client, project_id, body),
    )
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    frozen_keyframe = job["snapshot"]["keyframe"]
    assert frozen_keyframe["bindingId"] == context["selection"]["id"]
    assert frozen_keyframe["assetId"] == context["selection"]["assetId"]
    assert (frozen_keyframe["width"], frozen_keyframe["height"]) == (941, 1672)
    assert job["snapshot"]["request"] == {
        "durationSeconds": 5,
        "resolution": "576x1024",
        "audio": True,
        "aspectPolicy": "cover_center_crop",
        "seed": 41,
        "profileId": "minimax_h3_quality8_portrait_576x1024_v2",
        "profileVersion": 2,
        "width": 576,
        "height": 1024,
        "fps": 24,
        "frameCount": 124,
        "allowLetterbox": False,
        "allowCenterCrop": True,
        "quality": 8,
    }

    # Restart only the application composition; the frozen project database
    # and original asset must be sufficient to send the exact reviewed bytes.
    restarted_client = TestClient(
        create_project_folder_authoring_app(
            storage,
            video_provider=provider,
            video_adapter=MiniMaxH3GatewayAdapter(),
            video_probe=lambda _content: ObservedVideo(
                5.167, 576, 1024, "h264", "aac", frame_rate=24, frame_count=124
            ),
        )
    )
    after_restart = restarted_client.get(
        f"/api/v2/projects/{project_id}/video-jobs"
    ).json()["jobs"]
    assert len(after_restart) == 1
    assert after_restart[0]["id"] == job["id"] and after_restart[0]["current"] is True
    submitted = restarted_client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit"
    )
    assert submitted.status_code == 200 and provider.images == [original]
    assert provider.submits[0]["aspectPolicy"] == "cover_center_crop"

    tampered = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json=_reviewed_video_body(
            client,
            project_id,
            {
                **body,
                "idempotencyKey": "tampered-gateway-crop",
                "seed": 42,
            },
        ),
    )
    assert tampered.status_code == 201, tampered.text
    tampered_job = tampered.json()
    home = storage.projects.open(project_id)
    try:
        database = home.database_path
    finally:
        home.close()
    altered_snapshot = tampered_job["snapshot"]
    altered_snapshot["request"]["allowCenterCrop"] = False
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE v2_video_jobs SET snapshot = ? WHERE id = ?",
            (json.dumps(altered_snapshot), tampered_job["id"]),
        )
    listed = client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"]
    assert (
        next(item for item in listed if item["id"] == tampered_job["id"])["current"]
        is False
    )
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{tampered_job['id']}/submit"
        ).status_code
        == 409
    )
    assert len(provider.submits) == 1
