"""test project storage video review behavior contracts."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectArtifactStore
from plotloom.video_contracts import VideoReviewRequest
from tests.project_storage_fixtures import FixtureResolver as _FixtureResolver
from tests.project_storage_fixtures import fixture_profile as _fixture_profile
from tests.video_prompt_fixtures import reviewed_h3_body as _reviewed_video_body
from tests.video_storage_fixtures import FakeH3, _approved_keyframe, _fixture_app


def test_whole_job_review_annotations_are_optional_and_trimmed() -> None:
    omitted = VideoReviewRequest.model_validate(
        {"decision": "reject", "expectedSelectionRevision": 0}
    )
    assert omitted.reviewer == "" and omitted.note == ""
    whitespace = VideoReviewRequest.model_validate(
        {
            "decision": "reject",
            "expectedSelectionRevision": 0,
            "reviewer": "  ",
            "note": "  短  ",
        }
    )
    assert whitespace.reviewer == "" and whitespace.note == "短"


def test_h3_off_grid_authored_shot_is_rejected_before_review_or_dispatch(
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
    approval, context = _approved_keyframe(
        client, storage, project_id, author_frame_grid=False
    )
    assert context["shot"].duration_units * 24 % 1_000 != 0
    response = client.post(
        f"/api/v2/projects/{project_id}/video-jobs/prompt-preview",
        json={
            "approvalId": approval["id"],
            "shotId": context["shot"].id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": "off-grid-source-must-fail",
            "aspectPolicy": "reject_mismatch",
            "seed": 31,
            "playbackIntent": "segment_required",
        },
    )
    assert response.status_code == 409 and "not representable" in response.text
    assert client.get(f"/api/v2/projects/{project_id}/video-jobs").json()["jobs"] == []
    assert provider.submits == []


def test_h3_end_frame_decision_freezes_prompt_bytes_and_stales_after_clear(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    base = f"/api/v2/projects/{project_id}"
    shot_id = context["shot"].id
    end_bytes = BytesIO()
    Image.new("RGB", (576, 1024), (95, 30, 40)).save(end_bytes, format="PNG")
    asset_response = client.post(
        f"{base}/managed-assets",
        files={"image": ("end.png", end_bytes.getvalue(), "image/png")},
        data={
            "origin": "reviewed end frame fixture",
            "rights": "known",
            "declared_additions_json": "[]",
        },
    )
    assert asset_response.status_code == 201
    end_asset = asset_response.json()
    endpoint = f"{base}/shots/{shot_id}/video-end-frame"
    assert client.get(endpoint).json() == {"revision": 0, "assetId": None}
    choice = {
        "assetId": end_asset["id"],
        "approvalId": approval["id"],
        "storyboardRevision": context["revision"],
        "expectedRevision": 0,
        "aspectPolicy": "reject_mismatch",
    }
    assert (
        client.post(endpoint, json={**choice, "expectedRevision": 1}).status_code == 409
    )
    selected = client.post(endpoint, json=choice)
    assert selected.status_code == 200, selected.text
    assert selected.json()["originalHash"] == end_asset["originalHash"]
    assert selected.json()["provenance"]
    body = _reviewed_video_body(
        client,
        project_id,
        {
            "approvalId": approval["id"],
            "shotId": shot_id,
            "storyboardRevision": context["revision"],
            "expectedSelectionRevision": context["selection"]["selectionRevision"],
            "idempotencyKey": "end-frame-first-last",
            "aspectPolicy": "reject_mismatch",
            "seed": 31,
        },
    )
    preview = client.post(f"{base}/video-jobs/prompt-preview", json=body)
    assert preview.status_code == 200
    assert (
        "Picture 2 (from Shot 1) aligns with the 5.17-second mark"
        in preview.json()["compiledPrompt"]
    )
    prepared = client.post(f"{base}/video-jobs", json=body)
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()
    assert job["snapshot"]["endFrame"]["originalHash"] == end_asset["originalHash"]
    assert client.post(f"{base}/video-jobs/{job['id']}/submit").status_code == 200
    assert provider.end_images == [end_bytes.getvalue()]
    cleared = client.post(
        endpoint,
        json={**choice, "assetId": None, "aspectPolicy": None, "expectedRevision": 1},
    )
    assert cleared.status_code == 200 and cleared.json()["revision"] == 2
    assert client.get(f"{base}/video-jobs").json()["jobs"][0]["current"] is False
    incompatible = client.post(
        endpoint, json={**choice, "expectedRevision": 2, "aspectPolicy": "contain_pad"}
    )
    assert incompatible.status_code == 200
    mismatched = client.post(
        f"{base}/video-jobs/prompt-preview",
        json={
            **body,
            "idempotencyKey": "end-frame-aspect-mismatch",
            "reviewedDirections": None,
        },
    )
    assert mismatched.status_code == 409 and "aspect treatment" in mismatched.text
    selected_again = client.post(endpoint, json={**choice, "expectedRevision": 3})
    assert selected_again.status_code == 200
    second_body = _reviewed_video_body(
        client,
        project_id,
        {
            **body,
            "idempotencyKey": "end-frame-corrupt-before-submit",
            "reviewedDirections": None,
        },
    )
    second = client.post(f"{base}/video-jobs", json=second_body)
    assert second.status_code == 201
    current = storage.projects.open(project_id)
    try:
        uri = current.media.get_managed_asset_storage(project_id, end_asset["id"])[
            "originalUri"
        ]
    finally:
        current.close()
    original_get = ProjectArtifactStore.get
    monkeypatch.setattr(
        ProjectArtifactStore,
        "get",
        lambda self, value: (
            b"changed end bytes" if value == uri else original_get(self, value)
        ),
    )
    failed = client.post(f"{base}/video-jobs/{second.json()['id']}/submit")
    assert failed.status_code == 200 and failed.json()["state"] != "submitted"
    assert len(provider.submits) == 1
