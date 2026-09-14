"""Direct project-folder video ownership and portable playback proof."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import shutil
import sqlite3

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage import ProjectStorageConflictError, ProjectStorageError
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_ingestion import ObservedVideo
from plotloom.video_provider import VideoBackendInstanceIdentity

from tests.test_project_storage import _FixtureResolver, _fixture_profile


class FakeH3:
    """Typed transport fixture; it never sends a network request."""

    def __init__(self, *, endpoint: str = "http://127.0.0.1:9010") -> None:
        self.submits: list[dict] = []
        self.downloads = 0
        self.preflight_calls = 0
        self.upload_calls = 0
        self.poll_calls = 0
        self.before_preflight: Callable[[], None] | None = None
        self._endpoint = endpoint

    def configured_backend_identity(self) -> VideoBackendInstanceIdentity:
        return VideoBackendInstanceIdentity.from_public_configuration(
            "fixture_h3_endpoint_v1", {"endpoint": self._endpoint}
        )

    def preflight(self) -> None:
        self.preflight_calls += 1
        if self.before_preflight is not None:
            self.before_preflight()
        return None

    def upload(self, image: bytes, *, mime_type: str) -> str:
        assert image and mime_type == "image/png"
        self.upload_calls += 1
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
        self.poll_calls += 1
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


def _prepare_video(
    client: TestClient, project_id: str, approval: dict, context: dict, *, key: str
) -> dict:
    prepared = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json={
            "approvalId": approval["id"],
            "shotId": context["shot"].id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": key,
            "aspectPolicy": "reject_mismatch",
            "seed": 31,
        },
    )
    assert prepared.status_code == 201, prepared.text
    return prepared.json()


def _sqlite_rows(path: Path, statement: str, parameters: tuple[object, ...] = ()) -> list[tuple]:
    with sqlite3.connect(path) as connection:
        return connection.execute(statement, parameters).fetchall()


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
    prepared = client.post(f"/api/v2/projects/{project_id}/video-jobs", json=body)
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    binding = job["snapshot"]["provider"]["backendBinding"]
    assert binding["adapterId"] == "minimax_h3_gateway"
    assert binding["adapterVersion"] == "2"
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
            assert opened.repository.list_video_jobs(project_id)[0]["state"] == "dispatching"
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
    ) == [("reserved", 0), ("dispatch_claimed", 0)]

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
