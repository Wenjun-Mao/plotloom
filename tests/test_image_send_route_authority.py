"""Both live send routes revalidate persistence after exact lane reservation."""

from __future__ import annotations

import json
from contextlib import closing
import subprocess
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.codex_image_dispatch import NativeCodexImageDispatcher
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage
from plotloom.specialist_settings import SpecialistSettings
from tests.creative_delivery_fixtures import _prepare_art_context
from tests.project_storage_fixtures import FixtureResolver, fixture_profile


@pytest.mark.parametrize("family", ["character", "image"])
def test_route_stale_authority_releases_only_unsent_lane(tmp_path, monkeypatch, family):
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    if family == "character":
        _prepare_art_context(store)
        prepared = store.media.prepare_character_reference_proposal(
            project_id,
            character_id="lin",
            cast_revision=1,
            visual_direction="Offline race",
            parent_candidate_asset_id=None,
        )["proposal"]
        route = "character-reference-proposals"
    else:
        ProjectPipelineExecutor(FixtureResolver()).execute(
            store, profile=fixture_profile()
        )
        route = "image-jobs"
    store.close()
    app = create_project_folder_authoring_app(storage)
    registry = app.state.specialists
    task_id = str(uuid4())
    registry.save(
        SpecialistSettings.model_validate(
            {"image": {"name": "Offline fixture", "taskId": task_id}}
        )
    )
    with TestClient(app) as client:
        if family == "image":
            base = f"/api/v2/projects/{project_id}"
            board = client.get(base + "/stages").json()["stages"][-1]
            shot_id = board["payload"]["shots"][0]["id"]
            approval = client.post(
                base + "/storyboard-approval",
                json={
                    "expectedRevision": board["head"]["revision"],
                    "contentHash": board["head"]["contentHash"],
                    "decision": "approve",
                    "attribution": {"kind": "unnamed_creator"},
                    "gateSetVersion": "storyboard.v2",
                },
            )
            assert approval.status_code == 201, approval.text
            payload = {
                "shotId": shot_id,
                "targetId": "original",
                "contextId": "race",
                "presentationChange": "Offline race",
            }
            draft = client.put(
                base + "/authoring-drafts",
                json={
                    "editorScope": "image_direction",
                    "entityId": shot_id + ":original",
                    "baseCanonicalRevision": board["head"]["revision"],
                    "expectedDraftRevision": 0,
                    "payload": payload,
                },
            )
            assert draft.status_code == 200, draft.text
            response = client.post(
                base + "/image-jobs",
                json={
                    "shotId": shot_id,
                    "approvalId": approval.json()["decision"]["id"],
                    "storyboardRevision": board["head"]["revision"],
                    "contextId": "race",
                    "presentationChange": "Offline race",
                    "consumedDraft": {
                        "editorScope": "image_direction",
                        "entityId": shot_id + ":original",
                        "draftRevision": draft.json()["draftRevision"],
                    },
                },
            )
            assert response.status_code == 201, response.text
            prepared = response.json()["job"]
        job_id = prepared["id"]
        native_dispatch = NativeCodexImageDispatcher.dispatch
        observed = []

        def raced_dispatch(dispatcher, **kwargs):
            original = kwargs["before_send"]

            def stale_before_send():
                # Reservation is real and belongs to the configured send task.
                lease = json.loads(
                    (dispatcher.state_root / "inflight.json").read_text()
                )
                assert lease == {"jobId": job_id, "taskId": task_id}
                observed.append(lease)
                with closing(storage.projects.open(project_id)) as current:
                    if family == "character":
                        current.media.cancel_character_reference_proposal(
                            project_id, job_id, "fixture changed before queue"
                        )
                    else:
                        current.media.cancel_image_job(
                            project_id, job_id, "fixture changed before queue"
                        )
                original()

            kwargs["before_send"] = stale_before_send
            return native_dispatch(dispatcher, **kwargs)

        monkeypatch.setattr(NativeCodexImageDispatcher, "dispatch", raced_dispatch)
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: pytest.fail("stale route must never queue"),
        )
        refused = client.post(f"/api/v2/projects/{project_id}/{route}/{job_id}/send")
        assert refused.status_code == 409, refused.text
        assert refused.json()["code"] == "invalid_transition"
        assert len(observed) == 1
        assert not registry.view()["busy"]
        assert registry.status(job_id)["state"] == "prepared"
        binding = registry.delivery_task_binding(job_id, require_bound=True)
        assert binding.mode == "configured_task" and str(binding.task_id) == task_id
        assert not list(registry.root.rglob("inflight.json"))
        assert not list(registry.root.rglob("receipt.json"))
