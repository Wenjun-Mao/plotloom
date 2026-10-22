"""test project storage video dispatch behavior contracts."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage, ProjectStorageError
from plotloom.video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from tests.image_identity_fixtures import (
    install_visible_fixture_character as _install_visible_fixture_character,
)
from tests.project_storage_fixtures import FixtureResolver as _FixtureResolver
from tests.project_storage_fixtures import fixture_profile as _fixture_profile
from tests.video_storage_fixtures import (
    FakeH3,
    _approved_keyframe,
    _fixture_app,
    _prepare_video,
    _select_character_reference,
    _sqlite_rows,
)


def test_direct_h3_dispatch_persists_claims_before_provider_calls_and_never_uses_wan_ledger(
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
    prepared = _prepare_video(
        client, project_id, approval, context, key="ordered-dispatch"
    )
    dispatch_identity = (
        "project-video-" + sha256(prepared["id"].encode("utf-8")).hexdigest()
    )

    def assert_durable_boundary() -> None:
        assert _sqlite_rows(
            storage.application.path,
            "SELECT state FROM direct_video_dispatch_leases WHERE dispatch_identity = ?",
            (dispatch_identity,),
        ) == [("dispatch_claimed",)]
        opened = storage.projects.open(project_id)
        try:
            assert (
                opened.media.direct_video.list_video_jobs(project_id)[0]["state"]
                == "dispatching"
            )
        finally:
            opened.close()

    provider.before_preflight = assert_durable_boundary
    submitted = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{prepared['id']}/submit"
    )
    assert submitted.status_code == 200, submitted.text
    assert (
        provider.preflight_calls == provider.upload_calls == len(provider.submits) == 1
    )
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
            storage.application.path,
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        )
    )


def test_direct_dispatch_faults_and_cancel_race_never_call_provider_or_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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

    before_event = _prepare_video(
        client, project_id, approval, context, key="event-fault"
    )
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
    assert (
        provider.preflight_calls == provider.upload_calls == len(provider.submits) == 0
    )
    identity = "project-video-" + sha256(before_event["id"].encode("utf-8")).hexdigest()
    assert _sqlite_rows(
        storage.application.path,
        "SELECT state FROM direct_video_dispatch_leases WHERE dispatch_identity = ?",
        (identity,),
    ) == [("reserved",)]
    assert (
        client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"][0][
            "state"
        ]
        == "dispatching"
    )
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
    assert (
        restarted_client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{before_event['id']}/submit"
        ).status_code
        == 409
    )
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

    monkeypatch.setattr(
        storage.application, "reserve_video_dispatch", cancel_between_reserve_and_claim
    )
    cancelled = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{raced['id']}/submit"
    )
    assert cancelled.status_code == 409
    assert (
        provider.preflight_calls == provider.upload_calls == len(provider.submits) == 0
    )
    race_identity = "project-video-" + sha256(raced["id"].encode("utf-8")).hexdigest()
    assert _sqlite_rows(
        storage.application.path,
        "SELECT event FROM direct_video_dispatch_events WHERE dispatch_identity = ? ORDER BY rowid",
        (race_identity,),
    ) == [("reserved",), ("released_before_dispatch",)]
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{raced['id']}/submit"
        ).status_code
        == 409
    )


def test_direct_prepare_rejects_missing_or_spoofed_backend_contract_before_reservation(
    tmp_path: Path,
) -> None:
    class MissingIdentityH3(FakeH3):
        configured_backend_identity = None  # type: ignore[assignment]

    provider = MissingIdentityH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    response = client.post(
        f"/api/v2/projects/{project_id}/video-jobs",
        json={
            "approvalId": approval["id"],
            "shotId": context["shot"].id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": "missing-binding",
            "aspectPolicy": "reject_mismatch",
            "seed": 32,
        },
    )
    assert response.status_code == 422
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"] == []

    class SpoofedPaidH3(MiniMaxH3GatewayAdapter):
        def production_contract(self, **kwargs: object):  # type: ignore[override]
            return replace(
                super().production_contract(**kwargs), cost_policy="wan_paid_pilot_v1"
            )

    paid_provider = FakeH3()
    paid_storage, paid_client = _fixture_app(
        tmp_path / "paid", paid_provider, adapter=SpoofedPaidH3()
    )
    paid_store = paid_storage.projects.create(FIXED_CHINESE_BRIEF)
    paid_project = paid_store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        paid_store, profile=_fixture_profile()
    )
    paid_store.close()
    paid_approval, paid_context = _approved_keyframe(
        paid_client, paid_storage, paid_project
    )
    rejected_paid = paid_client.post(
        f"/api/v2/projects/{paid_project}/video-jobs",
        json={
            "approvalId": paid_approval["id"],
            "shotId": paid_context["shot"].id,
            "storyboardRevision": paid_context["revision"],
            "expectedSelectionRevision": paid_context["selection"]["selectionRevision"],
            "idempotencyKey": "spoofed-paid",
            "aspectPolicy": "reject_mismatch",
            "seed": 33,
        },
    )
    assert rejected_paid.status_code == 409
    assert (
        paid_client.get(f"/api/v2/projects/{paid_project}/video-jobs").json()["jobs"]
        == []
    )
    assert paid_storage.application.video_accounting_budget()["configured"] is False
    assert paid_provider.preflight_calls == paid_provider.upload_calls == 0


def test_video_candidate_stales_when_its_identity_reference_is_replaced(
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
    job = _prepare_video(
        client, project_id, approval, context, key="identity-currentness"
    )
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit"
        ).json()["state"]
        == "submitted"
    )
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/reconcile"
        ).json()["state"]
        == "ingested"
    )
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
    before_replacement = client.get(f"/api/v2/projects/{project_id}/video-jobs").json()[
        "jobs"
    ]
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
    assert (
        provider.preflight_calls == provider.upload_calls == len(provider.submits) == 1
    )


def test_stale_identity_reference_blocks_initial_h3_submit_without_provider_call(
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
    assert (
        provider.preflight_calls == provider.upload_calls == len(provider.submits) == 0
    )
