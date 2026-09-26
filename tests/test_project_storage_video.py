"""Direct project-folder video ownership and portable playback proof."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.canonical_schema import CharacterV2, DialogueCue
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.persistence.codec import stable_hash
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import (
    ProjectArtifactStore,
    ProjectFolderStorage,
    ProjectStorageConflictError,
    ProjectStorageError,
    ProjectStore,
)
from plotloom.project_storage.operational_state import ProjectAccessLease
from plotloom.project_storage.recovery_validation import assert_database_contract
from plotloom.project_storage.video_candidate_transition import (
    ProjectSelectionTransitionRequiredError,
    ProjectVideoSegmentTransitionRequiredError,
    ProjectVideoEndFrameTransitionRequiredError,
)
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_contracts import VideoReviewRequest
from plotloom.video_ingestion import ObservedVideo, probe_video
from plotloom.video_jobs import VideoJobService
from plotloom.video_provider import VideoBackendInstanceIdentity
from tests.project_storage_fixtures import FixtureResolver as _FixtureResolver
from tests.project_storage_fixtures import fixture_profile as _fixture_profile
from tests.video_prompt_fixtures import reviewed_h3_body as _reviewed_video_body


def test_whole_job_review_annotations_are_optional_and_trimmed() -> None:
    omitted = VideoReviewRequest.model_validate({"decision": "reject", "expectedSelectionRevision": 0})
    assert omitted.reviewer == "" and omitted.note == ""
    whitespace = VideoReviewRequest.model_validate({
        "decision": "reject", "expectedSelectionRevision": 0,
        "reviewer": "  ", "note": "  短  ",
    })
    assert whitespace.reviewer == "" and whitespace.note == "短"


class FakeH3:
    """Typed transport fixture; it never sends a network request."""

    def __init__(self, *, endpoint: str = "http://127.0.0.1:9010", outputs: list[bytes] | None = None) -> None:
        self.submits: list[dict] = []
        self.downloads = 0
        self.preflight_calls = 0
        self.upload_calls = 0
        self.images: list[bytes] = []
        self.end_images: list[bytes | None] = []
        self.poll_calls = 0
        self.quality = 1
        self.resolution = "576x1024"
        self.before_preflight: Callable[[], None] | None = None
        self.submit_error: Exception | None = None
        self._endpoint = endpoint
        self._outputs = outputs

    def configured_backend_identity(self) -> VideoBackendInstanceIdentity:
        return VideoBackendInstanceIdentity.from_public_configuration(
            "fixture_h3_endpoint_v1", {"endpoint": self._endpoint}
        )

    def preflight(self) -> None:
        self.preflight_calls += 1
        if self.before_preflight is not None:
            self.before_preflight()

    def submit_image(self, image: bytes, *, mime_type: str, payload: dict,
                     end_image: bytes | None = None, end_mime_type: str | None = None) -> dict:
        assert image and mime_type == "image/png" and payload["durationSeconds"] in {5, 8}
        assert end_image is None or end_mime_type == "image/png"
        self.upload_calls += 1
        self.images.append(image)
        self.end_images.append(end_image)
        self.submits.append(payload)
        self.aspect_policy = payload["aspectPolicy"]
        self.quality = payload["quality"]
        self.resolution = payload["resolution"]
        self.duration = payload["durationSeconds"]
        self.seed = payload["seed"]
        if self.submit_error is not None:
            raise self.submit_error
        return _h3_job("submitted", False, self.quality, self.resolution, payload["aspectPolicy"], duration=self.duration, seed=self.seed)

    def poll(self, prediction_id: str) -> dict:
        self.poll_calls += 1
        return _h3_job("succeeded", True, self.quality, self.resolution, getattr(self, "aspect_policy", "reject_mismatch"), identifier=prediction_id, duration=getattr(self, "duration", 5), seed=getattr(self, "seed", 1))

    def download(self, reference: str) -> bytes:
        assert reference == "h3_0123456789abcdef0123456789abcdef"
        self.downloads += 1
        if self._outputs:
            return self._outputs[min(self.downloads - 1, len(self._outputs) - 1)]
        return b"offline-h3-project-video"


def _h3_job(status: str, output_ready: bool, quality: int, resolution: str, aspect_policy: str, *, identifier: str = "h3_0123456789abcdef0123456789abcdef", duration: int = 5, seed: int = 1) -> dict[str, object]:
    frame_count = {5: 124, 8: 192}[duration]
    return {"id": identifier, "status": status, "inputMode": "image", "quality": quality, "resolution": resolution,
            "aspectPolicy": aspect_policy, "seed": seed, "requestedDurationSeconds": duration,
            "frameCount": frame_count, "actualDurationSeconds": frame_count / 24,
            "generationSubmittedAt": None, "generationCompletedAt": None,
            "generationElapsedMs": None, "outputReady": output_ready, "error": None}


def _png(width: int = 576, height: int = 1024) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), (20, 30, 40)).save(output, format="PNG")
    return output.getvalue()


def _fixture_app(
    tmp_path: Path, provider: FakeH3, *, adapter: object | None = None
) -> tuple[ProjectFolderStorage, TestClient]:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "source" / "outputs",
        application_data_root=tmp_path / "source" / "application",
    )
    return storage, TestClient(
        create_project_folder_authoring_app(
            storage,
            video_provider=provider,
            video_adapter=adapter or MiniMaxH3GatewayAdapter(),  # type: ignore[arg-type]
            video_probe=lambda _content: ObservedVideo(
                {5: 124, 8: 192}[getattr(provider, "duration", 5)] / 24,
                576, 1024, "h264", "aac", frame_rate=24,
                frame_count={5: 124, 8: 192}[getattr(provider, "duration", 5)],
            ),
        )
    )


def _install_visible_fixture_character(store: ProjectStore) -> None:
    """Keep the identity-currentness test on an internally consistent story."""

    project_id = store.manifest.project_id
    bible = store.authoring.get_stage_payload(project_id, StageName.STORY_BIBLE)
    hero = CharacterV2(
        id="fixture-hero",
        name="Fixture hero",
        description="A deterministic identity-reference fixture.",
        visual_anchors=["red coat"],
        sound_anchors=[],
        allowed_states=["alert"],
        continuity_rules=["The red coat remains visible."],
        role="lead",
        goal="Keep the fixture coherent.",
        traits=["steady"],
        voice_anchors=[],
    )
    store.update_stage(
        StageName.STORY_BIBLE,
        bible.model_copy(update={"characters": [hero]}),
        expected_revision=store.authoring.get_stage_head(project_id, StageName.STORY_BIBLE).revision,
    )
    graph = store.authoring.get_stage_payload(project_id, StageName.STORY_GRAPH)
    store.update_stage(
        StageName.STORY_GRAPH,
        graph,
        expected_revision=store.authoring.get_stage_head(project_id, StageName.STORY_GRAPH).revision,
    )
    plan = store.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS)
    plan = plan.model_copy(
        update={
            "scenes": [
                scene.model_copy(update={"character_ids": [hero.id]})
                for scene in plan.scenes
            ]
        }
    )
    store.update_stage(
        StageName.SCENE_BEATS,
        plan,
        expected_revision=store.authoring.get_stage_head(project_id, StageName.SCENE_BEATS).revision,
    )
    storyboard = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    storyboard = storyboard.model_copy(
        update={
            "shots": [
                shot.model_copy(update={"character_ids": [hero.id]})
                for shot in storyboard.shots
            ]
        }
    )
    store.update_stage(
        StageName.STORYBOARD,
        storyboard,
        expected_revision=store.authoring.get_stage_head(project_id, StageName.STORYBOARD).revision,
    )


def _approved_keyframe(
    client: TestClient, storage: ProjectFolderStorage, project_id: str,
    *, keyframe_bytes: bytes | None = None, author_frame_grid: bool = True,
) -> tuple[dict, dict]:
    store = storage.projects.open(project_id)
    try:
        storyboard = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
        if author_frame_grid and storyboard.shots[0].duration_units * 24 % 1_000:
            # The generic text fixture emits a one-unit demonstration shot.
            # Video tests explicitly author a frame-representable five-second
            # shot before Approval; production admission never rounds it.
            revised = storyboard.model_copy(update={
                "shots": [item.model_copy(update={"duration_units": 5_000})
                          if item.id == storyboard.shots[0].id else item for item in storyboard.shots]
            })
            store.update_stage(
                StageName.STORYBOARD, revised,
                expected_revision=store.authoring.get_stage_head(project_id, StageName.STORYBOARD).revision,
            )
        board = store.authoring.get_stage_head(project_id, StageName.STORYBOARD)
        shot = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD).shots[0]
    finally:
        store.close()
    approval = client.post(
        f"/api/v2/projects/{project_id}/storyboard-approval",
        json={
            "expectedRevision": board.revision,
            "contentHash": board.content_hash,
            "decision": "approve",
            "reviewer": "project-video fixture",
            "gateSetVersion": "storyboard.v2",
        },
    ).json()["decision"]
    asset = client.post(
        f"/api/v2/projects/{project_id}/managed-assets",
        files={"image": ("keyframe.png", keyframe_bytes or _png(), "image/png")},
        data={"origin": "offline H3 fixture", "rights": "unknown", "declared_additions_json": "[]"},
    ).json()
    draft = client.put(
        f"/api/v2/projects/{project_id}/authoring-drafts",
        json={
            "editorScope": "visual_intent",
            "entityId": f"{shot.id}:{asset['id']}",
            "baseCanonicalRevision": board.revision,
            "expectedDraftRevision": 0,
            "payload": {
                "assetId": asset["id"],
                "shotId": shot.id,
                "role": "shot_keyframe",
                "identityIntent": "Retain the fixture identity.",
                "sourceRefs": ["offline H3 fixture"],
            },
        },
    )
    assert draft.status_code == 200, draft.text
    intent = client.post(
        f"/api/v2/projects/{project_id}/managed-assets/{asset['id']}/visual-intents",
        json={
            "shotId": shot.id,
            "role": "shot_keyframe",
            "identityIntent": "Retain the fixture identity.",
            "sourceRefs": ["offline H3 fixture"],
            "consumedDraft": {
                "editorScope": "visual_intent",
                "entityId": f"{shot.id}:{asset['id']}",
                "draftRevision": draft.json()["draftRevision"],
            },
        },
    ).json()
    selected = client.post(
        f"/api/v2/projects/{project_id}/reviewed-keyframes",
        json={
            "assetId": asset["id"],
            "shotId": shot.id,
            "sceneId": shot.scene_id,
            "expectedSelectionRevision": 0,
            "storyboardRevision": board.revision,
            "approvalId": approval["id"],
            "compatibilityNote": "The fixture matches the frozen H3 profile.",
            "visualIntentId": intent["id"],
            "visualIntentRevision": intent["revision"],
        },
    )
    assert selected.status_code == 201, selected.text
    return approval, {"shot": shot, "revision": board.revision, "selection": selected.json()}


def test_h3_off_grid_authored_shot_is_rejected_before_review_or_dispatch(tmp_path: Path) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id, author_frame_grid=False)
    assert context["shot"].duration_units * 24 % 1_000 != 0
    response = client.post(f"/api/v2/projects/{project_id}/video-jobs/prompt-preview", json={
        "approvalId": approval["id"], "shotId": context["shot"].id,
        "storyboardRevision": context["revision"],
        "expectedSelectionRevision": context["selection"]["selectionRevision"],
        "idempotencyKey": "off-grid-source-must-fail", "aspectPolicy": "reject_mismatch", "seed": 31,
        "playbackIntent": "segment_required",
    })
    assert response.status_code == 409 and "not representable" in response.text
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"] == []
    assert provider.submits == []


@pytest.mark.parametrize("missing_segments", [False, True])
def test_retained_project_adds_end_frame_table_without_touching_existing_assets(
    tmp_path: Path, missing_segments: bool,
) -> None:
    storage, client = _fixture_app(tmp_path, FakeH3())
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id, database = store.manifest.project_id, store.database_path
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    job = _prepare_video(client, project_id, approval, context, key=f"retained-pre-end-{missing_segments}")
    retained = storage.projects.open(project_id)
    try:
        start = retained.media.get_managed_asset_storage(project_id, context["selection"]["assetId"])
        original_bytes = retained.artifacts.get(start["originalUri"])
    finally:
        retained.close()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE v2_video_end_frame_decisions")
        if missing_segments:
            connection.execute("DROP TABLE v2_video_segments")
        connection.commit()
    before = database.read_bytes()
    with pytest.raises(ProjectVideoEndFrameTransitionRequiredError):
        storage.projects.inspect(project_id)
    assert database.read_bytes() == before
    reopened = storage.projects.open(project_id)
    try:
        assert reopened.artifacts.get(start["originalUri"]) == original_bytes
        restored = reopened.media.direct_video.list_video_jobs(project_id)
        assert len(restored) == 1 and restored[0]["id"] == job["id"]
        assert restored[0]["snapshotHash"] == job["snapshotHash"]
        assert restored[0]["current"] is True
    finally:
        reopened.close()
    assert _sqlite_rows(database, "SELECT name FROM sqlite_master WHERE name = 'v2_video_end_frame_decisions'")
    assert _sqlite_rows(database, "SELECT name FROM sqlite_master WHERE name = 'v2_video_segments'")
    storage.projects.open(project_id).close()


def test_h3_end_frame_decision_freezes_prompt_bytes_and_stales_after_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    base = f"/api/v2/projects/{project_id}"
    shot_id = context["shot"].id
    end_bytes = BytesIO()
    Image.new("RGB", (576, 1024), (95, 30, 40)).save(end_bytes, format="PNG")
    asset_response = client.post(f"{base}/managed-assets",
        files={"image": ("end.png", end_bytes.getvalue(), "image/png")},
        data={"origin": "reviewed end frame fixture", "rights": "known", "declared_additions_json": "[]"})
    assert asset_response.status_code == 201
    end_asset = asset_response.json()
    endpoint = f"{base}/shots/{shot_id}/video-end-frame"
    assert client.get(endpoint).json() == {"revision": 0, "assetId": None}
    choice = {"assetId": end_asset["id"], "approvalId": approval["id"],
              "storyboardRevision": context["revision"], "expectedRevision": 0,
              "aspectPolicy": "reject_mismatch"}
    assert client.post(endpoint, json={**choice, "expectedRevision": 1}).status_code == 409
    selected = client.post(endpoint, json=choice)
    assert selected.status_code == 200, selected.text
    assert selected.json()["originalHash"] == end_asset["originalHash"]
    assert selected.json()["provenance"]
    body = _reviewed_video_body(client, project_id, {
        "approvalId": approval["id"], "shotId": shot_id,
        "storyboardRevision": context["revision"],
        "expectedSelectionRevision": context["selection"]["selectionRevision"],
        "idempotencyKey": "end-frame-first-last", "aspectPolicy": "reject_mismatch", "seed": 31,
    })
    preview = client.post(f"{base}/video-jobs/prompt-preview", json=body)
    assert preview.status_code == 200
    assert "Picture 2 (from Shot 1) aligns with the 5.17-second mark" in preview.json()["compiledPrompt"]
    prepared = client.post(f"{base}/video-jobs", json=body)
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    assert job["snapshot"]["endFrame"]["originalHash"] == end_asset["originalHash"]
    assert client.post(f"{base}/video-jobs/{job['id']}/submit").status_code == 200
    assert provider.end_images == [end_bytes.getvalue()]
    cleared = client.post(endpoint, json={**choice, "assetId": None, "aspectPolicy": None, "expectedRevision": 1})
    assert cleared.status_code == 200 and cleared.json()["revision"] == 2
    assert client.get(f"{base}/video-jobs").json()["jobs"][0]["current"] is False
    incompatible = client.post(endpoint, json={**choice, "expectedRevision": 2, "aspectPolicy": "contain_pad"})
    assert incompatible.status_code == 200
    mismatched = client.post(f"{base}/video-jobs/prompt-preview", json={
        **body, "idempotencyKey": "end-frame-aspect-mismatch", "reviewedDirections": None,
    })
    assert mismatched.status_code == 409 and "aspect treatment" in mismatched.text
    selected_again = client.post(endpoint, json={**choice, "expectedRevision": 3})
    assert selected_again.status_code == 200
    second_body = _reviewed_video_body(client, project_id, {
        **body, "idempotencyKey": "end-frame-corrupt-before-submit", "reviewedDirections": None,
    })
    second = client.post(f"{base}/video-jobs", json=second_body)
    assert second.status_code == 201
    current = storage.projects.open(project_id)
    try:
        uri = current.media.get_managed_asset_storage(project_id, end_asset["id"])["originalUri"]
    finally:
        current.close()
    original_get = ProjectArtifactStore.get
    monkeypatch.setattr(ProjectArtifactStore, "get", lambda self, value:
                        b"changed end bytes" if value == uri else original_get(self, value))
    failed = client.post(f"{base}/video-jobs/{second.json()['id']}/submit")
    assert failed.status_code == 200 and failed.json()["state"] != "submitted"
    assert len(provider.submits) == 1


def _prepare_video(
    client: TestClient, project_id: str, approval: dict, context: dict, *, key: str,
    requested_duration_seconds: int | None = None,
) -> dict:
    body = {
            "approvalId": approval["id"],
            "shotId": context["shot"].id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": key,
            "aspectPolicy": "reject_mismatch",
            "seed": 31,
            **({"requestedDurationSeconds": requested_duration_seconds} if requested_duration_seconds is not None else {}),
    }
    prepared = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=_reviewed_video_body(client, project_id, body))
    assert prepared.status_code == 201, prepared.text
    return prepared.json()


def _select_character_reference(
    client: TestClient,
    project_id: str,
    context: dict,
    *,
    asset_id: str,
    expected_revision: int,
    note: str,
) -> dict:
    response = client.post(
        f"/api/v2/projects/{project_id}/character-references",
        json={
            "characterId": context["shot"].character_ids[0],
            "authority": "story_bible",
            "primaryAssetId": asset_id,
            "complementaryAssetIds": [],
            "expectedReferenceRevision": expected_revision,
            "reviewer": "project-video fixture",
            "notes": note,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _sqlite_rows(path: Path, statement: str, parameters: tuple[object, ...] = ()) -> list[tuple]:
    with sqlite3.connect(path) as connection:
        return connection.execute(statement, parameters).fetchall()


@pytest.mark.parametrize(
    "authored_units,in_frame,out_frame,playback_intent",
    [(6_000, 24, 168, "segment_required"),
     (7_500, 6, 186, "segment_required"),
     (8_000, 0, 192, "source_exact")],
)
def test_synthetic_reviewed_segment_survives_reopen_and_blocks_old_revision(
    tmp_path: Path, authored_units: int, in_frame: int, out_frame: int, playback_intent: str,
) -> None:
    """An offline 8-second H3-shaped take is never playable before window review."""

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg tools are required for synthetic audiovisual proof")
    source = tmp_path / "explicitly-synthetic-eight-second-take.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:size=576x1024:rate=24:duration=8",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8",
         "-frames:v", "192", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", "-y", str(source)],
        check=True, timeout=90,
    )
    provider = FakeH3(outputs=[source.read_bytes()])
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "project" / "outputs",
        application_data_root=tmp_path / "project" / "application",
    )
    client = TestClient(create_project_folder_authoring_app(
        storage, video_provider=provider, video_adapter=MiniMaxH3GatewayAdapter(),
        video_probe=probe_video,
    ))
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    changed = board.model_copy(update={
        "shots": [board.shots[0].model_copy(update={"duration_units": authored_units}), *board.shots[1:]],
    })
    store.update_stage(
        StageName.STORYBOARD, changed,
        expected_revision=store.authoring.get_stage_head(project_id, StageName.STORYBOARD).revision,
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    base = f"/api/v2/projects/{project_id}"
    prepared = client.post(f"{base}/video-jobs", json=_reviewed_video_body(client, project_id, {
        "approvalId": approval["id"], "shotId": context["shot"].id,
        "storyboardRevision": context["revision"],
        "expectedSelectionRevision": context["selection"]["selectionRevision"],
        "idempotencyKey": "synthetic-reviewed-segment-8-to-6",
        "requestedDurationSeconds": 8, "playbackIntent": playback_intent,
        "aspectPolicy": "reject_mismatch", "seed": 31,
    }))
    assert prepared.status_code == 201, prepared.text
    job_id = prepared.json()["id"]
    assert prepared.json()["snapshot"]["sourceTiming"]["durationUnits"] == authored_units
    assert client.post(f"{base}/video-jobs/{job_id}/submit").status_code == 200
    ingested = client.post(f"{base}/video-jobs/{job_id}/reconcile")
    assert ingested.status_code == 200 and ingested.json()["state"] == "ingested", ingested.text
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    whole_take_selection = client.post(f"{base}/video-jobs/{job_id}/review", json={
        "reviewer": "synthetic test operator", "decision": "select",
        "note": "A whole H3 take must not bypass segment review.", "expectedSelectionRevision": 0,
    })
    assert whole_take_selection.status_code == 409
    proposed = client.post(f"{base}/video-jobs/{job_id}/segments", json={
        "inFrame": in_frame, "outFrame": out_frame, "expectedSelectionRevision": 0,
    })
    assert proposed.status_code == 201, proposed.text
    segment = proposed.json()
    assert segment["derivativeProbe"]["frameCount"] == authored_units * 24 // 1_000
    assert client.get(f"{base}/video-segments/{segment['id']}/preview").status_code == 200
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    assert client.post(f"{base}/video-jobs/{job_id}/discard", json={"expectedSelectionRevision": 0}).status_code == 409
    proposal_snapshot = storage.recovery.create_snapshot(project_id)
    assert any(item.relative_path.endswith(segment["derivativeHash"]) for item in proposal_snapshot.manifest.files)
    selected = client.post(f"{base}/video-segments/{segment['id']}/select", json={
        "expectedSelectionRevision": 0,
    })
    assert selected.status_code == 201, selected.text
    assert selected.json()["selected"] is True
    selected_job = client.get(f"{base}/video-jobs").json()["jobs"][0]
    assert selected_job["reviews"][-1]["reviewer"] == ""
    assert selected_job["reviews"][-1]["note"] == ""
    assert client.post(f"{base}/video-segments/{segment['id']}/select", json={
        "reviewer": "synthetic test operator", "note": "Stale concurrent selection.",
        "expectedSelectionRevision": 0,
    }).status_code == 409
    playback = client.get(f"{base}/video-jobs/{job_id}/playback")
    assert playback.status_code == 200 and sha256(playback.content).hexdigest() == segment["derivativeHash"]
    assert client.post(f"{base}/video-jobs/{job_id}/discard", json={"expectedSelectionRevision": 1}).status_code == 409
    snapshot = storage.recovery.create_snapshot(project_id)
    assert any(item.relative_path.endswith(segment["derivativeHash"]) for item in snapshot.manifest.files)
    restored_storage = ProjectFolderStorage(
        outputs_root=tmp_path / "restored" / "outputs",
        application_data_root=tmp_path / "restored" / "application",
    )
    restored_storage.recovery.restore(Path(snapshot.location))
    restored_client = TestClient(create_project_folder_authoring_app(restored_storage))
    assert restored_client.get(f"{base}/video-jobs/{job_id}/playback").content == playback.content
    assert restored_client.get(f"{base}/video-segments/{segment['id']}/preview").content == playback.content
    rejected = restored_client.post(f"{base}/video-jobs/{job_id}/review", json={
        "decision": "reject", "note": "短",
        "expectedSelectionRevision": 1,
    })
    assert rejected.status_code == 201 and rejected.json()["selectionRevision"] == 2
    assert rejected.json()["reviewer"] == "" and rejected.json()["note"] == "短"
    assert restored_client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    assert restored_client.get(f"{base}/video-jobs/{job_id}/media").status_code == 200
    reopened = storage.projects.open(project_id)
    reopened.close()
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 200
    with sqlite3.connect(reopened.database_path) as connection:
        connection.execute("UPDATE v2_video_jobs SET output_hash = ? WHERE id = ?", ("0" * 64, job_id))
        connection.commit()
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    with sqlite3.connect(reopened.database_path) as connection:
        connection.execute("UPDATE v2_video_jobs SET output_hash = ? WHERE id = ?", (ingested.json()["outputHash"], job_id))
        connection.commit()
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 200
    edited = storage.projects.open(project_id)
    board = edited.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    changed = board.model_copy(update={
        "shots": [board.shots[0].model_copy(update={"action": "Synthetic fixture action changed."}), *board.shots[1:]],
    })
    edited.update_stage(
        StageName.STORYBOARD, changed,
        expected_revision=edited.authoring.get_stage_head(project_id, StageName.STORYBOARD).revision,
    )
    edited.close()
    assert client.get(f"{base}/video-jobs/{job_id}/playback").status_code == 404
    assert client.get(f"{base}/video-jobs/{job_id}/media").status_code == 200


def test_existing_project_adds_only_empty_segment_table_on_writable_open(tmp_path: Path) -> None:
    storage, _client = _fixture_app(tmp_path, FakeH3())
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id, database = store.manifest.project_id, store.database_path
    store.close()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE v2_video_segments")
        connection.commit()
    prior = database.read_bytes()
    shared_lease = ProjectAccessLease.acquire(database.parent, mode="shared")
    try:
        with pytest.raises(ProjectVideoSegmentTransitionRequiredError, match="exclusive project lease"):
            ProjectStore.open(database.parent, access_lease=shared_lease)
    finally:
        shared_lease.close()
    assert database.read_bytes() == prior
    with pytest.raises(ProjectStorageError, match="video segment transition"):
        storage.projects.inspect(project_id)
    assert database.read_bytes() == prior
    opened = storage.projects.open(project_id)
    opened.close()
    assert _sqlite_rows(database, "SELECT name FROM sqlite_master WHERE name = 'v2_video_segments'") == [("v2_video_segments",)]
    reopened = storage.projects.open(project_id)
    reopened.close()


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


def test_project_video_is_local_reviewable_and_restores_without_gateway(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    body = {
        "approvalId": approval["id"],
        "shotId": context["shot"].id,
        "storyboardRevision": context["revision"],
        "expectedSelectionRevision": context["selection"]["selectionRevision"],
        "idempotencyKey": "project-folder-h3-idempotency",
        "aspectPolicy": "reject_mismatch",
        "seed": 13,
    }
    missing_seed = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/prompt-preview",
        json={key: value for key, value in body.items() if key != "seed"},
    )
    assert missing_seed.status_code == 422
    assert "explicit stable seed" in missing_seed.text
    body = _reviewed_video_body(client, project_id, body)
    prepared = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=body)
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    binding = job["snapshot"]["provider"]["backendBinding"]
    assert binding["adapterId"] == "minimax_h3_gateway"
    assert binding["adapterVersion"] == "6"
    assert binding["instance"]["kind"] == "fixture_h3_endpoint_v1"
    assert len(binding["instance"]["fingerprint"]) == 64
    assert "endpoint" not in job["snapshot"]["provider"]
    duplicate = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=body)
    assert duplicate.status_code == 201 and duplicate.json()["id"] == job["id"]
    assert client.get("/api/v2/video-pilot-budget").json()["configured"] is False
    submitted = client.post(f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit")
    assert submitted.status_code == 200 and submitted.json()["state"] == "submitted"
    assert len(provider.submits) == 1
    ingested = client.post(f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/reconcile")
    assert ingested.status_code == 200 and ingested.json()["state"] == "ingested"
    assert provider.downloads == 1
    selected = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/review",
        json={"decision": "select", "expectedSelectionRevision": 0},
    )
    assert selected.status_code == 409, selected.text
    media = client.get(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/media",
        headers={"Range": "bytes=0-6"},
    )
    assert media.status_code == 206 and media.content == b"offline"
    receipt = client.post(f"/api/v2/projects/{project_id}/snapshots")
    assert receipt.status_code == 201, receipt.text
    assert any(item["relativePath"].startswith("assets/") for item in receipt.json()["manifest"]["files"])

    source = storage.projects.open(project_id)
    source_home = source.home
    source.close()
    shutil.rmtree(source_home)
    shutil.rmtree(tmp_path / "source" / "application")
    restored_storage = ProjectFolderStorage(
        outputs_root=tmp_path / "restored" / "outputs",
        application_data_root=tmp_path / "restored" / "application",
    )
    restored_storage.recovery.restore(Path(receipt.json()["location"]))
    restored_client = TestClient(
        create_project_folder_authoring_app(
            restored_storage,
        )
    )
    restored_jobs = restored_client.get(
        f"/api/v2/projects/{project_id}/video-jobs"
    )
    assert restored_jobs.status_code == 200
    assert restored_jobs.json()["jobs"][0]["selected"] is False
    local_review = restored_client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/review",
        json={
            "reviewer": "offline restore fixture",
            "decision": "select",
            "note": "The retained local candidate remains selected.",
            "expectedSelectionRevision": 1,
        },
    )
    assert local_review.status_code == 409, local_review.text
    restored_media = restored_client.get(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/media"
    )
    assert restored_media.content == b"offline-h3-project-video"


def test_video_candidates_dispose_only_named_unselected_shared_bytes(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)

    first = _prepare_video(client, project_id, approval, context, key="candidate-one")
    second = _prepare_video(client, project_id, approval, context, key="candidate-two")
    assert first["id"] != second["id"]
    for candidate in (first, second):
        assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/submit").status_code == 200
        assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/reconcile").status_code == 200

    discarded = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{first['id']}/discard",
        json={"expectedSelectionRevision": 0},
    )
    assert discarded.status_code == 204, discarded.text
    jobs = {item["id"]: item for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"]}
    assert jobs[first["id"]]["state"] == "discarded"
    assert jobs[second["id"]]["state"] == "ingested"
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs/{first['id']}/media").status_code == 404
    # The fixture provider intentionally returns identical bytes; disposal of
    # the first candidate must not erase the other candidate's shared blob.
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs/{second['id']}/media").status_code == 200
    # Discarded rows retain no half-addressed output metadata.
    reopened = storage.projects.open(project_id)
    reopened.close()
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs/{second['id']}/media").status_code == 200


def test_prechange_project_folder_transitions_selection_on_writable_production_open(
    tmp_path: Path,
) -> None:
    """A format-8 folder from before candidate selection must move once, not fall back."""

    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    candidate = _prepare_video(client, project_id, approval, context, key="prechange-selection")
    assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/submit").status_code == 200
    assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/reconcile").status_code == 200

    current = storage.projects.open(project_id)
    try:
        database = current.database_path
    finally:
        current.close()
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("DROP TABLE v2_video_candidate_selections")
        connection.commit()
    before_inspection = database.read_bytes()

    # A regular shared work handle cannot advance schema authority while a
    # second handle may still observe the old folder. Registry.open first
    # obtains an exclusive transition lease, then returns a new shared handle.
    shared_lease = ProjectAccessLease.acquire(database.parent, mode="shared")
    try:
        with pytest.raises(ProjectSelectionTransitionRequiredError, match="exclusive project lease"):
            ProjectStore.open(database.parent, access_lease=shared_lease)
    finally:
        shared_lease.close()
    assert database.read_bytes() == before_inspection

    # The real read-only project-folder path must identify the required
    # transition without changing a closed-over historical database.
    with pytest.raises(ProjectStorageError, match="selection transition"):
        storage.projects.inspect(project_id)
    assert database.read_bytes() == before_inspection
    with pytest.raises(ProjectStorageError, match="writable video selection transition"):
        assert_database_contract(database, store.manifest)
    assert database.read_bytes() == before_inspection

    # Registry.open is the production writable path. It performs one bounded
    # transition and leaves no invented selection for an unreviewed H3 take.
    transitioned = storage.projects.open(project_id)
    try:
        selected = [
            item
            for item in transitioned.media.direct_video.list_video_jobs(project_id)
            if item["selected"]
        ]
        assert selected == []
    finally:
        transitioned.close()
    reopened = storage.projects.open(project_id)
    try:
        selected = [
            item
            for item in reopened.media.direct_video.list_video_jobs(project_id)
            if item["selected"]
        ]
        assert selected == []
    finally:
        reopened.close()


def test_bulk_video_discard_keeps_candidates_arriving_after_confirmation(
    tmp_path: Path,
) -> None:
    provider = FakeH3(outputs=[b"first", b"second", b"third"])
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)

    def ingest(key: str) -> dict:
        candidate = _prepare_video(client, project_id, approval, context, key=key)
        assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/submit").status_code == 200
        assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/reconcile").status_code == 200
        return candidate

    first, second = ingest("bulk-first"), ingest("bulk-second")
    confirmed_ids = [second["id"]]

    # This candidate arrives after the reviewer has confirmed the exact bulk
    # target set; the request must never recalculate a broader set server-side.
    third = ingest("bulk-arrived-after-confirmation")
    discarded = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/discard-unselected",
        json={"shotId": context["shot"].id, "videoJobIds": confirmed_ids, "expectedSelectionRevision": 0},
    )
    assert discarded.status_code == 204, discarded.text
    states = {item["id"]: item["state"] for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"]}
    assert states[second["id"]] == "discarded"
    assert states[third["id"]] == "ingested"

    stale = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/discard-unselected",
        json={"shotId": context["shot"].id, "videoJobIds": [first["id"]], "expectedSelectionRevision": 1},
    )
    assert stale.status_code == 409
    states = {item["id"]: item["state"] for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"]}
    assert states[first["id"]] == "ingested"


def test_interrupted_video_disposal_reopens_and_retries_without_retained_blob_damage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeH3(outputs=[b"discarded-by-interruption", b"retained-shared", b"retained-shared"])
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)

    def ingest(key: str) -> dict:
        candidate = _prepare_video(client, project_id, approval, context, key=key)
        assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/submit").status_code == 200
        assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/reconcile").status_code == 200
        return candidate

    interrupted, retained, shared = ingest("interrupt-delete"), ingest("keep-retained"), ingest("keep-shared")
    opened = storage.projects.open(project_id)
    try:
        interrupted_uri = opened.media.direct_video.get_video_output_storage(project_id, interrupted["id"])["uri"]
    finally:
        opened.close()
    original_delete = ProjectArtifactStore.delete

    def delete_then_interrupt(self: ProjectArtifactStore, uri: str) -> None:
        original_delete(self, uri)
        if uri == interrupted_uri:
            raise RuntimeError("simulated interruption after bytes removal")

    monkeypatch.setattr(ProjectArtifactStore, "delete", delete_then_interrupt)
    with pytest.raises(RuntimeError, match="after bytes removal"):
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{interrupted['id']}/discard",
            json={"expectedSelectionRevision": 0},
        )
    monkeypatch.setattr(ProjectArtifactStore, "delete", original_delete)

    reopened = storage.projects.open(project_id)
    try:
        states = {item["id"]: item["state"] for item in reopened.media.direct_video.list_video_jobs(project_id)}
        assert states[interrupted["id"]] == "discard_pending"
    finally:
        reopened.close()
    retried = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{interrupted['id']}/discard",
        json={"expectedSelectionRevision": 0},
    )
    assert retried.status_code == 204, retried.text
    states = {item["id"]: item["state"] for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"]}
    assert states[interrupted["id"]] == "discarded"
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs/{retained['id']}/media").content == b"retained-shared"
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs/{shared['id']}/media").content == b"retained-shared"


def test_video_disposal_keeps_a_cross_kind_managed_asset_blob(
    tmp_path: Path,
) -> None:
    provider = FakeH3(outputs=[b"first-candidate", b"selected-candidate"])
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    first = _prepare_video(client, project_id, approval, context, key="cross-kind-first")
    second = _prepare_video(client, project_id, approval, context, key="cross-kind-second")
    for candidate in (first, second):
        assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/submit").status_code == 200
        assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/reconcile").status_code == 200
    opened = storage.projects.open(project_id)
    retained = opened.media.direct_video.get_video_output_storage(project_id, first["id"])
    retained_bytes = opened.artifacts.get(retained["uri"])
    opened.media.record_managed_import(
        project_id, original_hash=sha256(retained_bytes).hexdigest(), display_hash=sha256(retained_bytes).hexdigest(),
        mime_type="video/mp4", byte_size=len(retained_bytes), width=1, height=1,
        declaration={"source": "cross-kind disposal fixture"},
        publish=lambda: (retained["uri"], retained["uri"]),
    )
    opened.close()
    assert client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{first['id']}/discard",
        json={"expectedSelectionRevision": 0},
    ).status_code == 204
    reopened = storage.projects.open(project_id)
    assert reopened.artifacts.get(retained["uri"]) == retained_bytes
    reopened.close()
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs/{first['id']}/media").status_code == 404
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs/{second['id']}/media").status_code == 200


def test_eight_second_h3_job_freezes_output_contract_and_survives_restart(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    job = _prepare_video(
        client, project_id, approval, context, key="qualified-eight-seconds",
        requested_duration_seconds=8,
    )
    request = job["snapshot"]["request"]
    assert request["durationSeconds"] == 8
    assert request["frameCount"] == 192
    assert request["fps"] == 24
    restarted = TestClient(create_project_folder_authoring_app(
        storage, video_provider=provider, video_adapter=MiniMaxH3GatewayAdapter(),
        video_probe=lambda _content: ObservedVideo(8.0, 576, 1024, "h264", "aac", frame_rate=24, frame_count=192),
    ))
    submitted = restarted.post(f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit")
    assert submitted.status_code == 200 and provider.submits[-1]["durationSeconds"] == 8
    ingested = restarted.post(f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/reconcile")
    assert ingested.status_code == 200
    assert ingested.json()["observed"]["frameCount"] == 192

    rejected = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json={
            "approvalId": approval["id"], "shotId": context["shot"].id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": "source-mismatched-seven-seconds", "requestedDurationSeconds": 7,
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
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    _install_visible_fixture_character(store)
    beats = store.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS)
    cue = DialogueCue(
        id="fixture-line", beat_id=beats.beats[0].id, order=1,
        speaker_id="fixture-hero", voice_over=None, text="嗯",
        language="zh-CN", delivery="natural", performance_notes="",
        estimated_duration_units=500,
    )
    store.update_stage(
        StageName.SCENE_BEATS,
        beats.model_copy(update={"dialogue_cues": [cue]}),
        expected_revision=store.authoring.get_stage_head(project_id, StageName.SCENE_BEATS).revision,
    )
    board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    store.update_stage(
        StageName.STORYBOARD,
        board.model_copy(update={"shots": [
            board.shots[0].model_copy(update={
                "cue_ids": [cue.id], "duration_units": 1_000,
                "action": "沈岚把铜质熔断器放在两条并列插槽之间。",
            }), *board.shots[1:]
        ]}),
        expected_revision=store.authoring.get_stage_head(project_id, StageName.STORYBOARD).revision,
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    _select_character_reference(
        client, project_id, context,
        asset_id=context["selection"]["assetId"], expected_revision=0,
        note="Use the reviewed fixture still for the visible speaker.",
    )
    body = {
        "approvalId": approval["id"], "shotId": context["shot"].id,
        "storyboardRevision": context["revision"],
        "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": "reviewed-english-directions", "aspectPolicy": "reject_mismatch", "seed": 31,
            "playbackIntent": "segment_required",
    }
    refused = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=body)
    assert refused.status_code == 409 and provider.submits == []
    sources_response = client.post(f"/api/v2/projects/{project_id}/video-jobs/prompt-preview", json=body)
    assert sources_response.status_code == 200, sources_response.text
    sources = sources_response.json()
    assert sources["compiledPrompt"] is None
    assert any(source["path"] == "shot.action" and source["text"] == "沈岚把铜质熔断器放在两条并列插槽之间。" for source in sources["sources"])
    reviewed = {
        "sourceHash": sources["sourceHash"], "reviewedEnglish": True,
        "fields": [{"path": source["path"], "english": (
            "The keeper places the brass fuse between the two parallel sockets."
            if source["path"] == "shot.action" else
            "A small metallic contact sound accompanies the visible movement."
            if source["path"] == "reviewedSoundscape" else source["text"]
        )} for source in sources["sources"]],
    }
    full_preview = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/prompt-preview",
        json={**body, "reviewedDirections": reviewed},
    )
    assert full_preview.status_code == 200, full_preview.text
    prompt = full_preview.json()["compiledPrompt"]
    assert "沈岚把铜质熔断器放在两条并列插槽之间。" not in prompt
    assert "The keeper places the brass fuse between the two parallel sockets." in prompt
    assert "<d>[Chinese] 嗯</d>" in prompt
    assert "only vocal utterance" not in prompt
    assert client.post(f"/api/v2/projects/{project_id}/video-jobs", json={
        **body, "reviewedDirections": {**reviewed, "sourceHash": "0" * 64},
    }).status_code == 409
    assert client.post(f"/api/v2/projects/{project_id}/video-jobs", json={
        **body, "reviewedDirections": reviewed,
    }).status_code == 409
    reviewed["promptSha256"] = full_preview.json()["compiledPromptSha256"]
    prepared = client.post(f"/api/v2/projects/{project_id}/video-jobs", json={**body, "reviewedDirections": reviewed})
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    assert job["snapshot"]["compilerVersion"] == "plotloom.h3-reviewed-frame.v4"
    assert job["snapshot"]["shot"]["action"] == "沈岚把铜质熔断器放在两条并列插槽之间。"
    assert job["snapshot"]["compiledPrompt"] == prompt
    assert job["snapshot"]["reviewedDirections"] == reviewed
    restarted = TestClient(create_project_folder_authoring_app(
        storage, video_provider=provider, video_adapter=MiniMaxH3GatewayAdapter(),
    ))
    submitted = restarted.post(f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit")
    assert submitted.status_code == 200, submitted.text
    assert provider.submits == [{
        "prompt": prompt, "quality": 8, "resolution": "576x1024",
        "aspectPolicy": "reject_mismatch", "seed": 31, "durationSeconds": 5,
    }]


def test_row_duration_tamper_cannot_change_a_frozen_h3_submission(tmp_path: Path) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    job = _prepare_video(client, project_id, approval, context, key="row-duration-tamper")
    store = storage.projects.open(project_id)
    try:
        database = store.database_path
    finally:
        store.close()
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE v2_video_jobs SET requested_seconds = 8 WHERE id = ?", (job["id"],))
    rejected = client.post(f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit")
    assert rejected.status_code == 409
    assert provider.submits == []


def test_explicit_h3_gateway_crop_freezes_original_bytes_across_restart_and_tamper_stales(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    original = _png(941, 1672)
    approval, context = _approved_keyframe(
        client, storage, project_id, keyframe_bytes=original
    )
    body = {
        "approvalId": approval["id"], "shotId": context["shot"].id,
        "storyboardRevision": context["revision"],
        "expectedSelectionRevision": context["selection"]["selectionRevision"],
        "idempotencyKey": "explicit-gateway-crop", "aspectPolicy": "cover_center_crop",
        "allowCenterCrop": True, "allowLetterbox": False, "seed": 41,
    }
    prepared = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=_reviewed_video_body(client, project_id, body))
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    frozen_keyframe = job["snapshot"]["keyframe"]
    assert frozen_keyframe["bindingId"] == context["selection"]["id"]
    assert frozen_keyframe["assetId"] == context["selection"]["assetId"]
    assert (frozen_keyframe["width"], frozen_keyframe["height"]) == (941, 1672)
    assert job["snapshot"]["request"] == {
        "durationSeconds": 5, "resolution": "576x1024", "audio": True,
        "aspectPolicy": "cover_center_crop", "seed": 41,
            "profileId": "minimax_h3_quality8_portrait_576x1024_v2",
            "profileVersion": 2, "width": 576, "height": 1024,
        "fps": 24, "frameCount": 124,
            "allowLetterbox": False, "allowCenterCrop": True, "quality": 8,
    }

    # Restart only the application composition; the frozen project database
    # and original asset must be sufficient to send the exact reviewed bytes.
    restarted_client = TestClient(create_project_folder_authoring_app(
        storage, video_provider=provider, video_adapter=MiniMaxH3GatewayAdapter(),
        video_probe=lambda _content: ObservedVideo(5.167, 576, 1024, "h264", "aac", frame_rate=24, frame_count=124),
    ))
    after_restart = restarted_client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"]
    assert len(after_restart) == 1
    assert after_restart[0]["id"] == job["id"] and after_restart[0]["current"] is True
    submitted = restarted_client.post(f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit")
    assert submitted.status_code == 200 and provider.images == [original]
    assert provider.submits[0]["aspectPolicy"] == "cover_center_crop"

    tampered = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json=_reviewed_video_body(client, project_id, {
            **body, "idempotencyKey": "tampered-gateway-crop", "seed": 42,
        }),
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
    assert next(item for item in listed if item["id"] == tampered_job["id"])["current"] is False
    assert client.post(f"/api/v2/projects/{project_id}/video-jobs/{tampered_job['id']}/submit").status_code == 409
    assert len(provider.submits) == 1


def test_historical_h3_letterbox_snapshot_remains_restart_dispatchable(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(
        client, storage, project_id, keyframe_bytes=_png(941, 1672)
    )
    body = {
        "approvalId": approval["id"], "shotId": context["shot"].id,
        "storyboardRevision": context["revision"],
        "expectedSelectionRevision": context["selection"]["selectionRevision"],
        "idempotencyKey": "historical-letterbox", "aspectPolicy": "contain_pad",
        "allowLetterbox": True, "seed": 43,
    }
    prepared = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=_reviewed_video_body(client, project_id, body))
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    historical = job["snapshot"]
    # V4 snapshots predate the additive crop consent field. Preserve their
    # exact request projection and its recalculated stored integrity hashes.
    historical["request"].pop("allowCenterCrop")
    home = storage.projects.open(project_id)
    try:
        database = home.database_path
    finally:
        home.close()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE v2_video_jobs SET snapshot = ?, snapshot_hash = ?, request_hash = ? WHERE id = ?",
            (
                json.dumps(historical), stable_hash(historical),
                stable_hash({"snapshot": historical, "idempotencyKey": body["idempotencyKey"]}), job["id"],
            ),
        )
    restarted_client = TestClient(create_project_folder_authoring_app(
        storage, video_provider=provider, video_adapter=MiniMaxH3GatewayAdapter(),
        video_probe=lambda _content: ObservedVideo(5.167, 576, 1024, "h264", "aac", frame_rate=24, frame_count=124),
    ))
    restored = restarted_client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"]
    assert restored[0]["current"] is True
    assert restarted_client.post(f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit").status_code == 200
    assert provider.submits[0]["aspectPolicy"] == "contain_pad"


def test_application_reservation_is_idempotent_and_enforces_cross_project_cap(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )
    try:
        storage.application.reserve_video_dispatch(
            dispatch_identity="project-video-" + "c" * 64,
            resource="test-paid-video",
            reserved_units=5,
            requires_accounting=True,
        )
    except ProjectStorageError as error:
        assert "accounting is not initialized" in str(error)
    else:
        raise AssertionError("missing accounting must disable paid dispatch")
    storage.application.initialize_video_accounting(limit_units=5)
    assert storage.application.video_accounting_budget()["remainingUnits"] == 5
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [
            workers.submit(
                storage.application.reserve_video_dispatch,
                dispatch_identity=identity,
                resource="test-paid-video",
                reserved_units=5,
                requires_accounting=True,
            )
            for identity in ("project-video-" + "a" * 64, "project-video-" + "b" * 64)
        ]
    results = []
    failures = []
    for future in futures:
        try:
            results.append(future.result())
        except ProjectStorageConflictError as error:
            failures.append(error)
    assert len(results) == len(failures) == 1
    assert results[0].reserved_units == 5
    assert storage.application.video_accounting_budget()["reservedUnits"] == 5


def test_restored_known_h3_job_reconciles_but_unknown_job_never_replays(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    prepared = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json=_reviewed_video_body(client, project_id, {
            "approvalId": approval["id"],
            "shotId": context["shot"].id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": "restored-known-h3-video",
            "aspectPolicy": "reject_mismatch",
            "seed": 14,
        }),
    ).json()
    assert client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    ).json()["state"] == "submitted"
    snapshot = storage.recovery.create_snapshot(project_id)

    restored = ProjectFolderStorage(
        outputs_root=tmp_path / "known-restored" / "outputs",
        application_data_root=tmp_path / "known-restored" / "application",
    )
    restored.recovery.restore(Path(snapshot.location))
    recovered = restored.projects.open(project_id)
    try:
        assert {(item.kind, item.operation_id, item.provider_state) for item in recovered.recovery_control().operations} == {
            ("video_job", prepared["id"], "known")
        }
    finally:
        recovered.close()
    restored_provider = FakeH3()
    # A known gateway job retains its frozen seed even though the fresh local
    # fixture instance did not submit it.
    restored_provider.seed = 14
    restored_provider.quality = 8
    restored_client = TestClient(
        create_project_folder_authoring_app(
            restored,
            video_provider=restored_provider,
            video_adapter=MiniMaxH3GatewayAdapter(),
            video_probe=lambda _content: ObservedVideo(
                5.167, 576, 1024, "h264", "aac", frame_rate=24, frame_count=124
            ),
        )
    )
    reconciled = restored_client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/reconcile"
    )
    assert reconciled.status_code == 200 and reconciled.json()["state"] == "ingested"
    assert restored_provider.downloads == 1 and restored_provider.submits == []

    # A recorded unknown never becomes a new submit after a portable restore.
    unknown_provider = FakeH3()
    unknown_storage, unknown_client = _fixture_app(tmp_path / "unknown", unknown_provider)
    unknown_store = unknown_storage.projects.create(FIXED_CHINESE_BRIEF)
    unknown_project_id = unknown_store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(unknown_store, profile=_fixture_profile())
    unknown_store.close()
    unknown_approval, unknown_context = _approved_keyframe(
        unknown_client, unknown_storage, unknown_project_id
    )
    unknown_job = unknown_client.post(
        f"/api/v2/projects/{unknown_project_id}/video-jobs",
        json=_reviewed_video_body(unknown_client, unknown_project_id, {
            "approvalId": unknown_approval["id"],
            "shotId": unknown_context["shot"].id,
            "storyboardRevision": unknown_context["revision"],
            "expectedSelectionRevision": unknown_context["selection"]["selectionRevision"],
            "idempotencyKey": "restored-unknown-h3-video",
            "aspectPolicy": "reject_mismatch",
            "seed": 15,
        }),
    ).json()
    unknown_provider.submit_image = lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("fixture lost response"))  # type: ignore[method-assign]
    assert unknown_client.post(
        f"/api/v2/projects/{unknown_project_id}/video-jobs/{unknown_job['id']}/submit"
    ).json()["state"] == "outcome_unknown"
    unknown_snapshot = unknown_storage.recovery.create_snapshot(unknown_project_id)
    unknown_restored = ProjectFolderStorage(
        outputs_root=tmp_path / "unknown-restored" / "outputs",
        application_data_root=tmp_path / "unknown-restored" / "application",
    )
    unknown_restored.recovery.restore(Path(unknown_snapshot.location))
    no_replay = TestClient(
        create_project_folder_authoring_app(
            unknown_restored,
            video_provider=FakeH3(),
            video_adapter=MiniMaxH3GatewayAdapter(),
        )
    )
    assert no_replay.post(
        f"/api/v2/projects/{unknown_project_id}/video-jobs/{unknown_job['id']}/submit"
    ).status_code == 409
    assert no_replay.post(
        f"/api/v2/projects/{unknown_project_id}/video-jobs/{unknown_job['id']}/reconcile"
    ).status_code == 409


def test_h3_uncertain_submit_is_terminal_and_never_replays_the_post(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    provider.submit_error = OSError("offline fixture lost the post response")
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    prepared = _prepare_video(client, project_id, approval, context, key="uncertain-submit")

    unknown = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    )
    assert unknown.status_code == 200
    assert unknown.json()["state"] == "outcome_unknown"
    retry = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    )
    assert retry.status_code == 409
    assert provider.preflight_calls == provider.upload_calls == len(provider.submits) == 1


def test_backend_instance_binding_blocks_preflight_and_restored_reconcile(
    tmp_path: Path,
) -> None:
    provider = FakeH3(endpoint="http://127.0.0.1:9010")
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    prepared = _prepare_video(client, project_id, approval, context, key="binding-fresh")

    # The adapter/profile are unchanged, but this is a distinct configured
    # gateway.  Identity admission happens before health/upload/submit.
    provider._endpoint = "http://127.0.0.1:9011"
    rejected = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    )
    assert rejected.status_code == 409
    assert (
        provider.preflight_calls,
        provider.upload_calls,
        provider.submits,
    ) == (0, 0, [])
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"][0][
        "state"
    ] == "prepared"

    provider._endpoint = "http://127.0.0.1:9010"
    assert client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    ).json()["state"] == "submitted"
    snapshot = storage.recovery.create_snapshot(project_id)
    restored = ProjectFolderStorage(
        outputs_root=tmp_path / "restored" / "outputs",
        application_data_root=tmp_path / "restored" / "application",
    )
    restored.recovery.restore(Path(snapshot.location))
    wrong_provider = FakeH3(endpoint="http://127.0.0.1:9011")
    restored_client = TestClient(
        create_project_folder_authoring_app(
            restored,
            video_provider=wrong_provider,
            video_adapter=MiniMaxH3GatewayAdapter(),
        )
    )
    rejected_reconcile = restored_client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/reconcile"
    )
    assert rejected_reconcile.status_code == 409
    assert wrong_provider.poll_calls == wrong_provider.downloads == 0


def test_direct_h3_dispatch_persists_claims_before_provider_calls_and_never_uses_wan_ledger(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    prepared = _prepare_video(client, project_id, approval, context, key="ordered-dispatch")
    dispatch_identity = "project-video-" + sha256(prepared["id"].encode("utf-8")).hexdigest()

    def assert_durable_boundary() -> None:
        assert _sqlite_rows(
            storage.application.path,
            "SELECT state FROM direct_video_dispatch_leases WHERE dispatch_identity = ?",
            (dispatch_identity,),
        ) == [("dispatch_claimed",)]
        opened = storage.projects.open(project_id)
        try:
            assert opened.media.direct_video.list_video_jobs(project_id)[0]["state"] == "dispatching"
        finally:
            opened.close()

    provider.before_preflight = assert_durable_boundary
    submitted = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    )
    assert submitted.status_code == 200, submitted.text
    assert provider.preflight_calls == provider.upload_calls == len(provider.submits) == 1
    assert _sqlite_rows(
        storage.application.path,
        "SELECT event, units FROM direct_video_dispatch_events WHERE dispatch_identity = ? ORDER BY rowid",
        (dispatch_identity,),
    ) == [("reserved", 5), ("dispatch_claimed", 5)]

    project_home = storage.projects.open(project_id)
    try:
        project_database = project_home.database_path
    finally:
        project_home.close()
    assert not {
        "v2_video_pilot_ledger",
        "v2_video_pilot_ledger_events",
    }.intersection(
        name
        for (name,) in _sqlite_rows(
            project_database, "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    )
    assert not {
        "v2_video_pilot_ledger",
        "v2_video_pilot_ledger_events",
    }.intersection(
        name
        for (name,) in _sqlite_rows(
            storage.application.path, "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    )


def test_direct_dispatch_faults_and_cancel_race_never_call_provider_or_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)

    before_event = _prepare_video(client, project_id, approval, context, key="event-fault")
    original_record_claim = storage.application.record_video_dispatch_claim

    def lose_after_project_claim(_identity: str) -> object:
        raise ProjectStorageError("injected application claim-event loss")

    monkeypatch.setattr(
        storage.application, "record_video_dispatch_claim", lose_after_project_claim
    )
    failed = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{before_event['id']}/submit"
    )
    assert failed.status_code == 422
    assert provider.preflight_calls == provider.upload_calls == len(provider.submits) == 0
    identity = "project-video-" + sha256(before_event["id"].encode("utf-8")).hexdigest()
    assert _sqlite_rows(
        storage.application.path,
        "SELECT state FROM direct_video_dispatch_leases WHERE dispatch_identity = ?",
        (identity,),
    ) == [("reserved",)]
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"][0][
        "state"
    ] == "dispatching"
    monkeypatch.setattr(
        storage.application, "record_video_dispatch_claim", original_record_claim
    )

    restarted = ProjectFolderStorage(
        outputs_root=tmp_path / "source" / "outputs",
        application_data_root=tmp_path / "source" / "application",
    )
    restarted_provider = FakeH3()
    restarted_client = TestClient(
        create_project_folder_authoring_app(
            restarted,
            video_provider=restarted_provider,
            video_adapter=MiniMaxH3GatewayAdapter(),
        )
    )
    assert restarted_client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{before_event['id']}/submit"
    ).status_code == 409
    assert restarted_provider.preflight_calls == restarted_provider.upload_calls == 0

    raced = _prepare_video(client, project_id, approval, context, key="cancel-race")
    original_reserve = storage.application.reserve_video_dispatch

    def cancel_between_reserve_and_claim(**kwargs: object) -> object:
        lease = original_reserve(**kwargs)  # type: ignore[arg-type]
        opened = storage.projects.open(project_id)
        try:
            from plotloom.project_storage.project_video import ProjectVideoRepository

            ProjectVideoRepository(opened, storage.application).cancel_video_job(
                project_id, raced["id"]
            )
        finally:
            opened.close()
        return lease

    monkeypatch.setattr(storage.application, "reserve_video_dispatch", cancel_between_reserve_and_claim)
    cancelled = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{raced['id']}/submit"
    )
    assert cancelled.status_code == 409
    assert provider.preflight_calls == provider.upload_calls == len(provider.submits) == 0
    race_identity = "project-video-" + sha256(raced["id"].encode("utf-8")).hexdigest()
    assert _sqlite_rows(
        storage.application.path,
        "SELECT event FROM direct_video_dispatch_events WHERE dispatch_identity = ? ORDER BY rowid",
        (race_identity,),
    ) == [("reserved",), ("released_before_dispatch",)]
    assert client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{raced['id']}/submit"
    ).status_code == 409


def test_direct_prepare_rejects_missing_or_spoofed_backend_contract_before_reservation(
    tmp_path: Path,
) -> None:
    class MissingIdentityH3(FakeH3):
        configured_backend_identity = None  # type: ignore[assignment]

    provider = MissingIdentityH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    response = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json={
            "approvalId": approval["id"], "shotId": context["shot"].id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": "missing-binding", "aspectPolicy": "reject_mismatch", "seed": 32,
        },
    )
    assert response.status_code == 422
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"] == []

    class SpoofedPaidH3(MiniMaxH3GatewayAdapter):
        def production_contract(self, **kwargs: object):  # type: ignore[override]
            return replace(super().production_contract(**kwargs), cost_policy="wan_paid_pilot_v1")

    paid_provider = FakeH3()
    paid_storage, paid_client = _fixture_app(
        tmp_path / "paid", paid_provider, adapter=SpoofedPaidH3()
    )
    paid_store = paid_storage.projects.create(FIXED_CHINESE_BRIEF)
    paid_project = paid_store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(paid_store, profile=_fixture_profile())
    paid_store.close()
    paid_approval, paid_context = _approved_keyframe(paid_client, paid_storage, paid_project)
    rejected_paid = paid_client.post(
        f"/api/v2/projects/{paid_project}/video-jobs",
        json={
            "approvalId": paid_approval["id"], "shotId": paid_context["shot"].id,
            "storyboardRevision": paid_context["revision"],
            "expectedSelectionRevision": paid_context["selection"]["selectionRevision"],
            "idempotencyKey": "spoofed-paid", "aspectPolicy": "reject_mismatch", "seed": 33,
        },
    )
    assert rejected_paid.status_code == 409
    assert paid_client.get(f"/api/v2/projects/{paid_project}/video-jobs").json()["jobs"] == []
    assert paid_storage.application.video_accounting_budget()["configured"] is False
    assert paid_provider.preflight_calls == paid_provider.upload_calls == 0


def test_video_candidate_stales_when_its_identity_reference_is_replaced(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    _install_visible_fixture_character(store)
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    first_reference = _select_character_reference(
        client,
        project_id,
        context,
        asset_id=context["selection"]["assetId"],
        expected_revision=0,
        note="The reviewed keyframe establishes the fixture identity.",
    )
    job = _prepare_video(client, project_id, approval, context, key="identity-currentness")
    assert client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit"
    ).json()["state"] == "submitted"
    assert client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/reconcile"
    ).json()["state"] == "ingested"
    selected = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/review",
        json={
            "reviewer": "project-video fixture",
            "decision": "select",
            "note": "The local fixture is explicitly reviewed before it is used.",
            "expectedSelectionRevision": 0,
        },
    )
    assert selected.status_code == 409, selected.text
    before_replacement = client.get(
        f"/api/v2/projects/{project_id}/video-jobs"
    ).json()["jobs"]
    assert before_replacement[0]["selected"] is False
    assert before_replacement[0]["current"] is True

    replacement = _select_character_reference(
        client,
        project_id,
        context,
        asset_id=context["selection"]["assetId"],
        expected_revision=first_reference["stateRevision"],
        note="The creator explicitly replaces the identity reference.",
    )
    assert replacement["referenceRevision"] == 2
    jobs = client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["id"] == job["id"]
    assert jobs[0]["selected"] is False and jobs[0]["current"] is False
    retry = client.post(f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit")
    assert retry.status_code == 409
    assert provider.preflight_calls == provider.upload_calls == len(provider.submits) == 1


def test_stale_identity_reference_blocks_initial_h3_submit_without_provider_call(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(store, profile=_fixture_profile())
    _install_visible_fixture_character(store)
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    first_reference = _select_character_reference(
        client,
        project_id,
        context,
        asset_id=context["selection"]["assetId"],
        expected_revision=0,
        note="The prepared video binds the initial identity reference.",
    )
    prepared = _prepare_video(
        client,
        project_id,
        approval,
        context,
        key="identity-stale-before-submit",
    )
    replacement = _select_character_reference(
        client,
        project_id,
        context,
        asset_id=context["selection"]["assetId"],
        expected_revision=first_reference["stateRevision"],
        note="The creator replaces the reference before the video is submitted.",
    )
    assert replacement["referenceRevision"] == 2

    blocked = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    )

    assert blocked.status_code == 409
    assert provider.preflight_calls == provider.upload_calls == len(provider.submits) == 0
