"""test project storage video disposal behavior contracts."""

from __future__ import annotations

import shutil
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectArtifactStore, ProjectFolderStorage
from tests.project_storage_fixtures import FixtureResolver as _FixtureResolver
from tests.project_storage_fixtures import fixture_profile as _fixture_profile
from tests.video_prompt_fixtures import reviewed_h3_body as _reviewed_video_body
from tests.video_storage_fixtures import (
    FakeH3,
    _approved_keyframe,
    _fixture_app,
    _prepare_video,
)


def test_project_video_is_local_reviewable_and_restores_without_gateway(
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
    submitted = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/submit"
    )
    assert submitted.status_code == 200 and submitted.json()["state"] == "submitted"
    assert len(provider.submits) == 1
    ingested = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{job['id']}/reconcile"
    )
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
    assert any(
        item["relativePath"].startswith("assets/")
        for item in receipt.json()["manifest"]["files"]
    )

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
    restored_jobs = restored_client.get(f"/api/v2/projects/{project_id}/video-jobs")
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
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)

    first = _prepare_video(client, project_id, approval, context, key="candidate-one")
    second = _prepare_video(client, project_id, approval, context, key="candidate-two")
    assert first["id"] != second["id"]
    for candidate in (first, second):
        assert (
            client.post(
                f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/submit"
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/reconcile"
            ).status_code
            == 200
        )

    discarded = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{first['id']}/discard",
        json={"expectedSelectionRevision": 0},
    )
    assert discarded.status_code == 204, discarded.text
    jobs = {
        item["id"]: item
        for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()[
            "jobs"
        ]
    }
    assert jobs[first["id"]]["state"] == "discarded"
    assert jobs[second["id"]]["state"] == "ingested"
    assert (
        client.get(
            f"/api/v2/projects/{project_id}/video-jobs/{first['id']}/media"
        ).status_code
        == 404
    )
    # The fixture provider intentionally returns identical bytes; disposal of
    # the first candidate must not erase the other candidate's shared blob.
    assert (
        client.get(
            f"/api/v2/projects/{project_id}/video-jobs/{second['id']}/media"
        ).status_code
        == 200
    )
    # Discarded rows retain no half-addressed output metadata.
    reopened = storage.projects.open(project_id)
    reopened.close()
    assert (
        client.get(
            f"/api/v2/projects/{project_id}/video-jobs/{second['id']}/media"
        ).status_code
        == 200
    )


def test_bulk_video_discard_keeps_candidates_arriving_after_confirmation(
    tmp_path: Path,
) -> None:
    provider = FakeH3(outputs=[b"first", b"second", b"third"])
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)

    def ingest(key: str) -> dict:
        candidate = _prepare_video(client, project_id, approval, context, key=key)
        assert (
            client.post(
                f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/submit"
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/reconcile"
            ).status_code
            == 200
        )
        return candidate

    first, second = ingest("bulk-first"), ingest("bulk-second")
    confirmed_ids = [second["id"]]

    # This candidate arrives after the reviewer has confirmed the exact bulk
    # target set; the request must never recalculate a broader set server-side.
    third = ingest("bulk-arrived-after-confirmation")
    discarded = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/discard-unselected",
        json={
            "shotId": context["shot"].id,
            "videoJobIds": confirmed_ids,
            "expectedSelectionRevision": 0,
        },
    )
    assert discarded.status_code == 204, discarded.text
    states = {
        item["id"]: item["state"]
        for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()[
            "jobs"
        ]
    }
    assert states[second["id"]] == "discarded"
    assert states[third["id"]] == "ingested"

    stale = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/discard-unselected",
        json={
            "shotId": context["shot"].id,
            "videoJobIds": [first["id"]],
            "expectedSelectionRevision": 1,
        },
    )
    assert stale.status_code == 409
    states = {
        item["id"]: item["state"]
        for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()[
            "jobs"
        ]
    }
    assert states[first["id"]] == "ingested"


def test_interrupted_video_disposal_reopens_and_retries_without_retained_blob_damage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeH3(
        outputs=[b"discarded-by-interruption", b"retained-shared", b"retained-shared"]
    )
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)

    def ingest(key: str) -> dict:
        candidate = _prepare_video(client, project_id, approval, context, key=key)
        assert (
            client.post(
                f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/submit"
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/reconcile"
            ).status_code
            == 200
        )
        return candidate

    interrupted, retained, shared = (
        ingest("interrupt-delete"),
        ingest("keep-retained"),
        ingest("keep-shared"),
    )
    opened = storage.projects.open(project_id)
    try:
        interrupted_uri = opened.media.direct_video.get_video_output_storage(
            project_id, interrupted["id"]
        )["uri"]
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
        states = {
            item["id"]: item["state"]
            for item in reopened.media.direct_video.list_video_jobs(project_id)
        }
        assert states[interrupted["id"]] == "discard_pending"
    finally:
        reopened.close()
    retried = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{interrupted['id']}/discard",
        json={"expectedSelectionRevision": 0},
    )
    assert retried.status_code == 204, retried.text
    states = {
        item["id"]: item["state"]
        for item in client.get(f"/api/v2/projects/{project_id}/video-jobs").json()[
            "jobs"
        ]
    }
    assert states[interrupted["id"]] == "discarded"
    assert (
        client.get(
            f"/api/v2/projects/{project_id}/video-jobs/{retained['id']}/media"
        ).content
        == b"retained-shared"
    )
    assert (
        client.get(
            f"/api/v2/projects/{project_id}/video-jobs/{shared['id']}/media"
        ).content
        == b"retained-shared"
    )


def test_video_disposal_keeps_a_cross_kind_managed_asset_blob(
    tmp_path: Path,
) -> None:
    provider = FakeH3(outputs=[b"first-candidate", b"selected-candidate"])
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(_FixtureResolver()).execute(
        store, profile=_fixture_profile()
    )
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    first = _prepare_video(
        client, project_id, approval, context, key="cross-kind-first"
    )
    second = _prepare_video(
        client, project_id, approval, context, key="cross-kind-second"
    )
    for candidate in (first, second):
        assert (
            client.post(
                f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/submit"
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v2/projects/{project_id}/video-jobs/{candidate['id']}/reconcile"
            ).status_code
            == 200
        )
    opened = storage.projects.open(project_id)
    retained = opened.media.direct_video.get_video_output_storage(
        project_id, first["id"]
    )
    retained_bytes = opened.artifacts.get(retained["uri"])
    opened.media.record_managed_import(
        project_id,
        original_hash=sha256(retained_bytes).hexdigest(),
        display_hash=sha256(retained_bytes).hexdigest(),
        mime_type="video/mp4",
        byte_size=len(retained_bytes),
        width=1,
        height=1,
        declaration={
            "origin": "cross-kind disposal fixture",
            "source": "cross-kind disposal fixture",
        },
        publish=lambda: (retained["uri"], retained["uri"]),
    )
    opened.close()
    assert (
        client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{first['id']}/discard",
            json={"expectedSelectionRevision": 0},
        ).status_code
        == 204
    )
    reopened = storage.projects.open(project_id)
    assert reopened.artifacts.get(retained["uri"]) == retained_bytes
    reopened.close()
    assert (
        client.get(
            f"/api/v2/projects/{project_id}/video-jobs/{first['id']}/media"
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v2/projects/{project_id}/video-jobs/{second['id']}/media"
        ).status_code
        == 200
    )
