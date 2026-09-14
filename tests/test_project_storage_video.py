"""Direct project-folder video ownership and portable playback proof."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage import ProjectStorageConflictError, ProjectStorageError
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_ingestion import ObservedVideo

from tests.test_project_storage import _FixtureResolver, _fixture_profile


class FakeH3:
    """Typed transport fixture; it never sends a network request."""

    def __init__(self) -> None:
        self.submits: list[dict] = []
        self.downloads = 0

    def preflight(self) -> None:
        return None

    def upload(self, image: bytes, *, mime_type: str) -> str:
        assert image and mime_type == "image/png"
        return "asset_0123456789abcdef0123456789abcdef"

    def submit(self, payload: dict, *, idempotency_key: str | None = None) -> dict:
        assert idempotency_key
        self.submits.append(payload)
        return {
            "id": "h3_0123456789abcdef0123456789abcdef",
            "status": "submitted",
            "profileId": payload["profileId"],
            "aspectPolicy": payload["aspectPolicy"],
            "outputReady": False,
            "error": None,
        }

    def poll(self, prediction_id: str) -> dict:
        return {
            "id": prediction_id,
            "status": "succeeded",
            "profileId": "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
            "aspectPolicy": "reject_mismatch",
            "outputReady": True,
            "error": None,
        }

    def download(self, reference: str) -> bytes:
        assert reference == "h3_0123456789abcdef0123456789abcdef"
        self.downloads += 1
        return b"offline-h3-project-video"


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (576, 1024), (20, 30, 40)).save(output, format="PNG")
    return output.getvalue()


def _fixture_app(tmp_path: Path, provider: FakeH3) -> tuple[ProjectFolderStorage, TestClient]:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "source" / "outputs",
        application_data_root=tmp_path / "source" / "application",
    )
    return storage, TestClient(
        create_project_folder_authoring_app(
            storage,
            video_provider=provider,
            video_adapter=MiniMaxH3GatewayAdapter(),
            video_probe=lambda _content: ObservedVideo(
                5.167, 576, 1024, "h264", "aac", frame_rate=24, frame_count=124
            ),
        )
    )


def _approved_keyframe(
    client: TestClient, storage: ProjectFolderStorage, project_id: str
) -> tuple[dict, dict]:
    store = storage.projects.open(project_id)
    try:
        board = store.repository.get_stage_head(project_id, StageName.STORYBOARD)
        shot = store.repository.get_stage_payload(project_id, StageName.STORYBOARD).shots[0]
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
        files={"image": ("keyframe.png", _png(), "image/png")},
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
    prepared = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=body)
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
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
        json={"reviewer": "project-video fixture", "decision": "select", "note": "Store this local candidate."},
    )
    assert selected.status_code == 201, selected.text
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
    assert restored_jobs.json()["jobs"][0]["selected"] is True
    local_review = restored_client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/review",
        json={
            "reviewer": "offline restore fixture",
            "decision": "select",
            "note": "The retained local candidate remains selected.",
        },
    )
    assert local_review.status_code == 201, local_review.text
    restored_media = restored_client.get(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/media"
    )
    assert restored_media.content == b"offline-h3-project-video"


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
        json={
            "approvalId": approval["id"],
            "shotId": context["shot"].id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": "restored-known-h3-video",
            "aspectPolicy": "reject_mismatch",
            "seed": 14,
        },
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
        json={
            "approvalId": unknown_approval["id"],
            "shotId": unknown_context["shot"].id,
            "storyboardRevision": unknown_context["revision"],
            "expectedSelectionRevision": unknown_context["selection"]["selectionRevision"],
            "idempotencyKey": "restored-unknown-h3-video",
            "aspectPolicy": "reject_mismatch",
            "seed": 15,
        },
    ).json()
    unknown_provider.submit = lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("fixture lost response"))  # type: ignore[method-assign]
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
