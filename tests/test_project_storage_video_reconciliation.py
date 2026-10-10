"""test project storage video reconciliation behavior contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import (
    ProjectFolderStorage,
    ProjectStorageConflictError,
    ProjectStorageError,
)
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from plotloom.video_ingestion import ObservedVideo
from tests.project_storage_fixtures import FixtureResolver as _FixtureResolver
from tests.project_storage_fixtures import fixture_profile as _fixture_profile
from tests.video_prompt_fixtures import reviewed_h3_body as _reviewed_video_body
from tests.video_storage_fixtures import (
    FakeH3,
    _approved_keyframe,
    _fixture_app,
    _prepare_video,
)


def test_application_reservation_is_idempotent_and_enforces_cross_project_cap(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
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
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    prepared = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json=_reviewed_video_body(
            client,
            project_id,
            {
                "approvalId": approval["id"],
                "shotId": context["shot"].id,
                "storyboardRevision": context["revision"],
                "expectedSelectionRevision": context["selection"]["selectionRevision"],
                "idempotencyKey": "restored-known-h3-video",
                "aspectPolicy": "reject_mismatch",
                "seed": 14,
            },
        ),
    ).json()
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
        ).json()["state"]
        == "submitted"
    )
    snapshot = storage.recovery.create_snapshot(project_id)

    restored = ProjectFolderStorage(
        outputs_root=tmp_path / "known-restored" / "outputs",
        application_data_root=tmp_path / "known-restored" / "application",
    )
    restored.recovery.restore(Path(snapshot.location))
    recovered = restored.projects.open(project_id)
    try:
        assert {
            (item.kind, item.operation_id, item.provider_state)
            for item in recovered.recovery_control().operations
        } == {("video_job", prepared["id"], "known")}
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
    unknown_storage, unknown_client = _fixture_app(
        tmp_path / "unknown", unknown_provider
    )
    unknown_store = unknown_storage.projects.create(FIXED_CHINESE_BRIEF)
    unknown_project_id = unknown_store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        unknown_store, profile=_fixture_profile()
    )
    unknown_store.close()
    unknown_approval, unknown_context = _approved_keyframe(
        unknown_client, unknown_storage, unknown_project_id
    )
    unknown_job = unknown_client.post(
        f"/api/v2/projects/{unknown_project_id}/video-jobs",
        json=_reviewed_video_body(
            unknown_client,
            unknown_project_id,
            {
                "approvalId": unknown_approval["id"],
                "shotId": unknown_context["shot"].id,
                "storyboardRevision": unknown_context["revision"],
                "expectedSelectionRevision": unknown_context["selection"][
                    "selectionRevision"
                ],
                "idempotencyKey": "restored-unknown-h3-video",
                "aspectPolicy": "reject_mismatch",
                "seed": 15,
            },
        ),
    ).json()
    unknown_provider.submit_image = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        OSError("fixture lost response")
    )  # type: ignore[method-assign]
    assert (
        unknown_client.post(
            f"/api/v2/projects/{unknown_project_id}/video-jobs/{unknown_job['id']}/submit"
        ).json()["state"]
        == "outcome_unknown"
    )
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
    assert (
        no_replay.post(
            f"/api/v2/projects/{unknown_project_id}/video-jobs/{unknown_job['id']}/submit"
        ).status_code
        == 409
    )
    assert (
        no_replay.post(
            f"/api/v2/projects/{unknown_project_id}/video-jobs/{unknown_job['id']}/reconcile"
        ).status_code
        == 409
    )


def test_h3_uncertain_submit_is_terminal_and_never_replays_the_post(
    tmp_path: Path,
) -> None:
    provider = FakeH3()
    provider.submit_error = OSError("offline fixture lost the post response")
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    prepared = _prepare_video(
        client, project_id, approval, context, key="uncertain-submit"
    )

    unknown = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    )
    assert unknown.status_code == 200
    assert unknown.json()["state"] == "outcome_unknown"
    retry = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    )
    assert retry.status_code == 409
    assert (
        provider.preflight_calls == provider.upload_calls == len(provider.submits) == 1
    )


def test_backend_instance_binding_blocks_preflight_and_restored_reconcile(
    tmp_path: Path,
) -> None:
    provider = FakeH3(endpoint="http://127.0.0.1:9010")
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    prepared = _prepare_video(
        client, project_id, approval, context, key="binding-fresh"
    )

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
    assert (
        client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"][0][
            "state"
        ]
        == "prepared"
    )

    provider._endpoint = "http://127.0.0.1:9010"
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
        ).json()["state"]
        == "submitted"
    )
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
