"""Direct project-folder video ownership and portable playback proof."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.domain import StageName
from plotloom.project_storage import ProjectFolderStorage
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_ingestion import ObservedVideo
from plotloom.video_provider import VideoBackendInstanceIdentity
from tests.video_prompt_fixtures import reviewed_h3_body as _reviewed_video_body


class FakeH3:
    """Typed transport fixture; it never sends a network request."""

    def __init__(
        self,
        *,
        endpoint: str = "http://127.0.0.1:9010",
        outputs: list[bytes] | None = None,
    ) -> None:
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

    def submit_image(
        self,
        image: bytes,
        *,
        mime_type: str,
        payload: dict,
        end_image: bytes | None = None,
        end_mime_type: str | None = None,
    ) -> dict:
        assert (
            image and mime_type == "image/png" and payload["durationSeconds"] in {5, 8}
        )
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
        return _h3_job(
            "submitted",
            False,
            self.quality,
            self.resolution,
            payload["aspectPolicy"],
            duration=self.duration,
            seed=self.seed,
        )

    def poll(self, prediction_id: str) -> dict:
        self.poll_calls += 1
        return _h3_job(
            "succeeded",
            True,
            self.quality,
            self.resolution,
            getattr(self, "aspect_policy", "reject_mismatch"),
            identifier=prediction_id,
            duration=getattr(self, "duration", 5),
            seed=getattr(self, "seed", 1),
        )

    def download(self, reference: str) -> bytes:
        assert reference == "h3_0123456789abcdef0123456789abcdef"
        self.downloads += 1
        if self._outputs:
            return self._outputs[min(self.downloads - 1, len(self._outputs) - 1)]
        return b"offline-h3-project-video"


def _h3_job(
    status: str,
    output_ready: bool,
    quality: int,
    resolution: str,
    aspect_policy: str,
    *,
    identifier: str = "h3_0123456789abcdef0123456789abcdef",
    duration: int = 5,
    seed: int = 1,
) -> dict[str, object]:
    frame_count = {5: 124, 8: 192}[duration]
    return {
        "id": identifier,
        "status": status,
        "inputMode": "image",
        "quality": quality,
        "resolution": resolution,
        "aspectPolicy": aspect_policy,
        "seed": seed,
        "requestedDurationSeconds": duration,
        "frameCount": frame_count,
        "actualDurationSeconds": frame_count / 24,
        "generationSubmittedAt": None,
        "generationCompletedAt": None,
        "generationElapsedMs": None,
        "outputReady": output_ready,
        "error": None,
    }


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
                576,
                1024,
                "h264",
                "aac",
                frame_rate=24,
                frame_count={5: 124, 8: 192}[getattr(provider, "duration", 5)],
            ),
        )
    )


def _approved_keyframe(
    client: TestClient,
    storage: ProjectFolderStorage,
    project_id: str,
    *,
    keyframe_bytes: bytes | None = None,
    author_frame_grid: bool = True,
) -> tuple[dict, dict]:
    store = storage.projects.open(project_id)
    try:
        storyboard = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
        if author_frame_grid and storyboard.shots[0].duration_units * 24 % 1_000:
            # The generic text fixture emits a one-unit demonstration shot.
            # Video tests explicitly author a frame-representable five-second
            # shot before Approval; production admission never rounds it.
            revised = storyboard.model_copy(
                update={
                    "shots": [
                        item.model_copy(update={"duration_units": 5_000})
                        if item.id == storyboard.shots[0].id
                        else item
                        for item in storyboard.shots
                    ]
                }
            )
            store.update_stage(
                StageName.STORYBOARD,
                revised,
                expected_revision=store.authoring.get_stage_head(
                    project_id, StageName.STORYBOARD
                ).revision,
            )
        board = store.authoring.get_stage_head(project_id, StageName.STORYBOARD)
        shot = store.authoring.get_stage_payload(
            project_id, StageName.STORYBOARD
        ).shots[0]
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
        data={
            "origin": "offline H3 fixture",
            "rights": "unknown",
            "declared_additions_json": "[]",
        },
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
    return approval, {
        "shot": shot,
        "revision": board.revision,
        "selection": selected.json(),
    }


def _prepare_video(
    client: TestClient,
    project_id: str,
    approval: dict,
    context: dict,
    *,
    key: str,
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
        **(
            {"requestedDurationSeconds": requested_duration_seconds}
            if requested_duration_seconds is not None
            else {}
        ),
    }
    prepared = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json=_reviewed_video_body(client, project_id, body),
    )
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


def _sqlite_rows(
    path: Path, statement: str, parameters: tuple[object, ...] = ()
) -> list[tuple]:
    with sqlite3.connect(path) as connection:
        return connection.execute(statement, parameters).fetchall()
