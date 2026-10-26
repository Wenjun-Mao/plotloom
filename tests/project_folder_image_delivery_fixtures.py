"""Shared offline setup and delivery writers for project-folder image tests."""

from __future__ import annotations

import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage
from tests.project_storage_fixtures import FixtureResolver, fixture_profile


def png(
    color: tuple[int, int, int], *, width: int = 24, height: int = 16
) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), color).save(output, format="PNG")
    return output.getvalue()


def delivery_manifest(job: dict, content: bytes, delivery_id: str) -> dict:
    return {
        "schemaVersion": 1,
        "jobId": job["id"],
        "requestHash": job["requestHash"],
        "deliveryId": delivery_id,
        "actualPrompt": "Offline fixture delivery from the frozen project package.",
        "outputs": [
            {
                "filename": "candidate.png",
                "sha256": sha256(content).hexdigest(),
                "role": "original",
            }
        ],
        "toolEvidence": {
            "tool": "codex_imagegen",
            "taskId": "project-folder-delivery-fixture",
            "available": True,
        },
        "limitations": ["fixture raster only"],
    }


def write_delivery(path: Path, job: dict, content: bytes, delivery_id: str) -> None:
    outputs = path / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "candidate.png").write_bytes(content)
    (path / "completion.json").write_text(
        json.dumps(delivery_manifest(job, content, delivery_id)), encoding="utf-8"
    )


def ready_exported_job(tmp_path: Path) -> tuple[TestClient, str, dict, Path]:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    ProjectPipelineExecutor(FixtureResolver()).execute(store, profile=fixture_profile())
    project_id = store.project().id
    store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    stages = client.get(f"/api/v2/projects/{project_id}/stages").json()["stages"]
    storyboard = stages[-1]
    shot = storyboard["payload"]["shots"][0]
    approval = client.post(
        f"/api/v2/projects/{project_id}/storyboard-approval",
        json={
            "expectedRevision": storyboard["head"]["revision"],
            "contentHash": storyboard["head"]["contentHash"],
            "decision": "approve",
            "attribution": {"kind": "unnamed_creator"},
            "gateSetVersion": "storyboard.v2",
        },
    )
    assert approval.status_code == 201, approval.text
    draft = client.put(
        f"/api/v2/projects/{project_id}/authoring-drafts",
        json={
            "editorScope": "image_direction",
            "entityId": f"{shot['id']}:original",
            "baseCanonicalRevision": storyboard["head"]["revision"],
            "expectedDraftRevision": 0,
            "payload": {
                "shotId": shot["id"],
                "targetId": "original",
                "contextId": "delivery-fixture",
                "presentationChange": "Keep the frozen shot legible.",
            },
        },
    )
    assert draft.status_code == 200, draft.text
    prepared = client.post(
        f"/api/v2/projects/{project_id}/image-jobs",
        json={
            "approvalId": approval.json()["decision"]["id"],
            "shotId": shot["id"],
            "storyboardRevision": storyboard["head"]["revision"],
            "presentationChange": "Keep the frozen shot legible.",
            "contextId": "delivery-fixture",
            "consumedDraft": {
                "editorScope": "image_direction",
                "entityId": f"{shot['id']}:original",
                "draftRevision": draft.json()["draftRevision"],
            },
        },
    )
    assert prepared.status_code == 201, prepared.text
    job = prepared.json()["job"]
    copied = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/copy")
    assert copied.status_code == 200, copied.text
    return client, project_id, job, Path(copied.json()["deliveryPath"])
