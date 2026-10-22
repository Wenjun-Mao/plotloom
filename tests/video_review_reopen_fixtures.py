"""Isolated retained-video setup used by review-reopen tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_generation_storage import ProjectPipelineExecutor
from tests.project_storage_fixtures import FixtureResolver, fixture_profile
from tests.video_storage_fixtures import (
    FakeH3,
    _approved_keyframe,
    _fixture_app,
    _prepare_video,
)


def _project(
    tmp_path: Path, provider: FakeH3
) -> tuple[object, TestClient, str, dict, dict]:
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(FixtureResolver()).execute(store, profile=fixture_profile())
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    return storage, client, project_id, approval, context


def _create_ingested_job(
    client: TestClient,
    project_id: str,
    approval: dict,
    context: dict,
    *,
    key: str,
) -> dict:
    job = _prepare_video(
        client,
        project_id,
        approval,
        context,
        key=key,
        requested_duration_seconds=8,
    )
    path = f"/api/v2/projects/{project_id}/video-jobs/{job['id']}"
    submitted = client.post(f"{path}/submit")
    assert submitted.status_code == 200, submitted.text
    ingested = client.post(f"{path}/reconcile")
    assert ingested.status_code == 200 and ingested.json()["state"] == "ingested", (
        ingested.text
    )
    return ingested.json()


def _propose_segment(
    client: TestClient,
    project_id: str,
    video_job_id: str,
    expected_revision: int,
) -> dict:
    response = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/{video_job_id}/segments",
        json={
            "inFrame": 0,
            "outFrame": 120,
            "expectedSelectionRevision": expected_revision,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
