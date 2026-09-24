"""Production composition proof for project-folder storage, without network I/O."""

from __future__ import annotations

import sqlite3
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from plotloom.config import PlotloomSettings
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.project_storage import ProjectStore
from plotloom.runtime import build_runtime_app
from plotloom.video_ingestion import ObservedVideo
from plotloom.video_provider import VideoBackendInstanceIdentity
from tests.backend_core.conftest import all_stage_payloads
from tests.project_storage_fixtures import FixtureResolver, fixture_profile
from tests.video_prompt_fixtures import reviewed_h3_body


class _RuntimeFakeH3:
    """A typed H3 transport used only at the shipped composition boundary."""

    def __init__(self) -> None:
        self.submits: list[dict] = []
        self.downloads = 0
        self.quality = 1
        self.resolution = "576x1024"
        self.aspect_policy = "reject_mismatch"

    def configured_backend_identity(self) -> VideoBackendInstanceIdentity:
        return VideoBackendInstanceIdentity.from_public_configuration(
            "runtime_fixture_h3_v1", {"endpoint": "http://127.0.0.1:9010"}
        )

    def preflight(self) -> None:
        return None

    def submit_image(self, image: bytes, *, mime_type: str, payload: dict) -> dict:
        assert image and mime_type == "image/png" and payload["durationSeconds"] == 5
        self.submits.append(payload)
        self.quality = payload["quality"]
        self.resolution = payload["resolution"]
        self.aspect_policy = payload["aspectPolicy"]
        return _h3_job("submitted", False, self.quality, self.resolution, payload["aspectPolicy"])

    def poll(self, prediction_id: str) -> dict:
        return _h3_job("succeeded", True, self.quality, self.resolution, self.aspect_policy, identifier=prediction_id)

    def download(self, reference: str) -> bytes:
        assert reference == "h3_0123456789abcdef0123456789abcdef"
        self.downloads += 1
        return b"runtime-h3-video"


def _h3_job(status: str, output_ready: bool, quality: int, resolution: str, aspect_policy: str, *, identifier: str = "h3_0123456789abcdef0123456789abcdef") -> dict[str, object]:
    return {"id": identifier, "status": status, "inputMode": "image", "quality": quality, "resolution": resolution,
            "aspectPolicy": aspect_policy, "seed": 31, "requestedDurationSeconds": 5,
            "frameCount": 124, "actualDurationSeconds": 124 / 24,
            "generationSubmittedAt": None, "generationCompletedAt": None,
            "generationElapsedMs": None, "outputReady": output_ready, "error": None}


class _ActiveImagePublicationMedia:
    """Expose one nonterminal manual publication without changing its store."""

    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def list_image_jobs(self, _project_id: str) -> list[dict[str, str]]:
        return [{"state": "prepared"}]


def _settings(tmp_path: Path) -> PlotloomSettings:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<main>Plotloom</main>", encoding="utf-8")
    return PlotloomSettings(
        repo_root=tmp_path,
        outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application",
        static_dir=static,
        text_auth_mode="none",
    )


def _await_terminal(client: TestClient, run_id: str) -> dict:
    for _attempt in range(100):
        response = client.get(f"/api/v2/runs/{run_id}")
        assert response.status_code == 200
        run = response.json()
        if run["status"] not in {"queued", "running", "cancel_requested"}:
            return run
        time.sleep(0.02)
    raise AssertionError("offline run did not become terminal")


def _activate_fixture_profile(client: TestClient) -> None:
    catalog = client.get("/api/v2/text-provider-profiles")
    assert catalog.status_code == 200
    profile = fixture_profile().model_dump(mode="json", by_alias=True)
    created_profile = client.post(
        "/api/v2/text-provider-profiles",
        json={
            "profileId": profile["profileId"],
            "displayName": "Offline fixture",
            "configuration": profile,
        },
    )
    assert created_profile.status_code == 201
    assert client.post(
        f"/api/v2/text-provider-profiles/{profile['profileId']}/activate",
        json={"expectedSelectionRevision": catalog.json()["selectionRevision"]},
    ).status_code == 200


def test_runtime_startup_admits_the_known_writable_selection_transition(
    tmp_path: Path,
) -> None:
    """Startup must not inspect a known active legacy folder before admitting it."""

    settings = _settings(tmp_path)
    app = build_runtime_app(settings, text_provider_resolver=FixtureResolver())
    with TestClient(app) as client:
        created = client.post(
            "/api/v2/projects",
            json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
        )
        assert created.status_code == 201
        project_id = created.json()["id"]
        store = app.state.project_folder_storage.projects.open(project_id)
        try:
            database = store.database_path
        finally:
            store.close()

    # This is the exact immediately preceding schema, not an arbitrary DB
    # mutation supported by runtime. The next production startup must route it
    # through the registry's admitted writable transition before recovery reads.
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE v2_video_candidate_selections")
        connection.commit()

    restarted = build_runtime_app(settings, text_provider_resolver=FixtureResolver())
    with TestClient(restarted) as client:
        assert client.get(f"/api/v2/projects/{project_id}").status_code == 200
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'v2_video_candidate_selections'"
        ).fetchone() == ("v2_video_candidate_selections",)


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (576, 1024), (20, 30, 40)).save(output, format="PNG")
    return output.getvalue()


def test_production_runtime_uses_application_profiles_and_exact_project_routes(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    app = build_runtime_app(settings, text_provider_resolver=FixtureResolver())

    with TestClient(app) as client:
        _activate_fixture_profile(client)

        first = client.post(
            "/api/v2/projects",
            json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
        )
        second = client.post(
            "/api/v2/projects",
            json={
                "brief": FIXED_CHINESE_BRIEF.model_copy(
                    update={"title": "第二个雾港"}
                ).model_dump(mode="json", by_alias=True)
            },
        )
        assert first.status_code == second.status_code == 201
        first_id, second_id = first.json()["id"], second.json()["id"]

        first_run = client.post(f"/api/v2/projects/{first_id}/pipeline-runs", json={})
        second_run = client.post(f"/api/v2/projects/{second_id}/pipeline-runs", json={})
        assert first_run.status_code == second_run.status_code == 202
        completed_first = _await_terminal(client, first_run.json()["id"])
        completed_second = _await_terminal(client, second_run.json()["id"])
        assert completed_first["status"] == completed_second["status"] == "succeeded"
        assert completed_first["projectId"] == first_id
        assert completed_second["projectId"] == second_id
        assert completed_first["providerSnapshot"]["profileId"] == "offline_fixture"
        progress = client.get(f"/api/v2/runs/{first_run.json()['id']}/progress")
        assert progress.status_code == 200
        assert progress.json()["runId"] == first_run.json()["id"]
        assert client.get("/api/v2/runs/not-indexed").status_code == 404

        snapshot = client.post(f"/api/v2/projects/{first_id}/snapshots")
        assert snapshot.status_code == 201
        assert snapshot.json()["status"] == "complete"
        assert client.post(f"/api/v2/projects/{first_id}/close").status_code == 200

    restarted = build_runtime_app(settings, text_provider_resolver=FixtureResolver())
    with TestClient(restarted) as client:
        assert set(restarted.state.startup_recovery) == {first_id, second_id}
        assert client.get(f"/api/v2/runs/{first_run.json()['id']}").json()["projectId"] == first_id
        assert client.get(f"/api/v2/runs/{second_run.json()['id']}").json()["projectId"] == second_id
        # Reconciliation returns a plan but never starts a fresh provider call.
        assert client.get(f"/api/v2/projects/{first_id}").status_code == 409
        assert client.post(f"/api/v2/projects/{first_id}/open").status_code == 200
        assert client.get(f"/api/v2/projects/{first_id}").status_code == 200


def test_production_runtime_owns_archive_duplicate_and_media_free_deletion(
    tmp_path: Path,
) -> None:
    app = build_runtime_app(_settings(tmp_path), text_provider_resolver=FixtureResolver())
    with TestClient(app) as client:
        created = client.post(
            "/api/v2/projects",
            json={
                "brief": FIXED_CHINESE_BRIEF.model_dump(
                    mode="json", by_alias=True
                )
            },
        )
        assert created.status_code == 201
        source_id = created.json()["id"]

        archived = client.post(
            f"/api/v2/projects/{source_id}/archive",
            json={"expectedLifecycleRevision": 1},
        )
        assert archived.status_code == 200
        assert archived.json()["lifecycleStatus"] == "archived"
        assert client.get("/api/v2/projects?status=active").json()["projects"] == []
        assert [item["id"] for item in client.get("/api/v2/projects?status=archived").json()["projects"]] == [source_id]

        stale_restore = client.post(
            f"/api/v2/projects/{source_id}/restore",
            json={"expectedLifecycleRevision": 1},
        )
        assert stale_restore.status_code == 409
        restored = client.post(
            f"/api/v2/projects/{source_id}/restore",
            json={"expectedLifecycleRevision": 2},
        )
        assert restored.status_code == 200
        duplicate_headers = {"Idempotency-Key": "production-folder-duplicate"}
        duplicate_body = {"expectedLifecycleRevision": 3, "title": "Production duplicate"}
        first_duplicate = client.post(
            f"/api/v2/projects/{source_id}/duplicate",
            headers=duplicate_headers,
            json=duplicate_body,
        )
        replayed_duplicate = client.post(
            f"/api/v2/projects/{source_id}/duplicate",
            headers=duplicate_headers,
            json=duplicate_body,
        )
        assert first_duplicate.status_code == replayed_duplicate.status_code == 200
        duplicate_id = first_duplicate.json()["project"]["id"]
        assert replayed_duplicate.json()["project"]["id"] == duplicate_id
        conflict = client.post(
            f"/api/v2/projects/{source_id}/duplicate",
            headers=duplicate_headers,
            json={**duplicate_body, "title": "Conflicting duplicate"},
        )
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "idempotency_conflict"
        assert len(client.get("/api/v2/projects?status=active").json()["projects"]) == 2

        archived_duplicate = client.post(
            f"/api/v2/projects/{duplicate_id}/archive",
            json={"expectedLifecycleRevision": 1},
        )
        assert archived_duplicate.status_code == 200
        wrong_confirmation = client.post(
            f"/api/v2/projects/{duplicate_id}/permanent-delete",
            json={
                "expectedLifecycleRevision": 2,
                "confirmationTitle": "The wrong project title",
            },
        )
        assert wrong_confirmation.status_code == 409
        assert client.get(f"/api/v2/projects/{duplicate_id}").status_code == 200
        deleted = client.post(
            f"/api/v2/projects/{duplicate_id}/permanent-delete",
            json={
                "expectedLifecycleRevision": 2,
                "confirmationTitle": duplicate_body["title"],
            },
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/v2/projects/{duplicate_id}").status_code == 404


def test_production_runtime_rejects_lifecycle_transitions_with_manual_publications(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Archive/delete retain the close boundary for external image delivery."""

    app = build_runtime_app(_settings(tmp_path), text_provider_resolver=FixtureResolver())
    original_media = ProjectStore.media

    def active_publication_media(store: ProjectStore) -> _ActiveImagePublicationMedia:
        return _ActiveImagePublicationMedia(original_media.fget(store))

    with TestClient(app) as client:
        created = client.post(
            "/api/v2/projects",
            json={
                "brief": FIXED_CHINESE_BRIEF.model_dump(
                    mode="json", by_alias=True
                )
            },
        )
        assert created.status_code == 201
        project_id = created.json()["id"]

        with monkeypatch.context() as publication_media:
            publication_media.setattr(
                ProjectStore, "media", property(active_publication_media)
            )
            archive = client.post(
                f"/api/v2/projects/{project_id}/archive",
                json={"expectedLifecycleRevision": 1},
            )
        assert archive.status_code == 409
        assert archive.json() == {
            "code": "project_busy",
            "message": "project_busy: image_publication_active",
        }

        archived = client.post(
            f"/api/v2/projects/{project_id}/archive",
            json={"expectedLifecycleRevision": 1},
        )
        assert archived.status_code == 200

        with monkeypatch.context() as publication_media:
            publication_media.setattr(
                ProjectStore, "media", property(active_publication_media)
            )
            deletion = client.post(
                f"/api/v2/projects/{project_id}/permanent-delete",
                json={
                    "expectedLifecycleRevision": 2,
                    "confirmationTitle": FIXED_CHINESE_BRIEF.title,
                },
            )
        assert deletion.status_code == 409
        assert deletion.json() == {
            "code": "project_busy",
            "message": "project_busy: image_publication_active",
        }
        retained = client.get(f"/api/v2/projects/{project_id}")
        assert retained.status_code == 200
        assert retained.json()["lifecycleStatus"] == "archived"


def test_production_runtime_preserves_structured_domain_validation_issues(
    tmp_path: Path,
) -> None:
    app = build_runtime_app(_settings(tmp_path), text_provider_resolver=FixtureResolver())
    with TestClient(app) as client:
        bible = all_stage_payloads()[0]
        created = client.post(
            "/api/v2/projects",
            json={
                "brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True),
                "initialStages": [
                    {
                        "stage": "story_bible",
                        "payload": bible.model_dump(mode="json", by_alias=True),
                    }
                ],
            },
        )
        assert created.status_code == 201
        project_id = created.json()["id"]
        invalid_graph = {
            "startNodeId": "arrival",
            "nodes": [
                {
                    "id": "arrival",
                    "title": "Arrival",
                    "summary": "No path leaves this non-ending node.",
                    "kind": "start",
                }
            ],
            "edges": [],
            "joinContracts": [],
        }
        response = client.patch(
            f"/api/v2/projects/{project_id}/stages/story_graph",
            json={"expectedRevision": 0, "payload": invalid_graph},
        )
        assert response.status_code == 422
        assert response.json()["code"] == "domain_validation"
        assert {
            "code": "dead_end",
            "path": "nodes.arrival",
            "message": "non-ending nodes must have an outgoing edge",
        } in response.json()["issues"]


def test_application_text_profile_record_is_atomic_when_storage_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = build_runtime_app(_settings(tmp_path), text_provider_resolver=FixtureResolver())
    repository = app.state.application_profile_repository
    store = repository.store
    original_save = store._save_profile_in_transaction

    def fail_after_profile_write(*args: object, **kwargs: object) -> object:
        original_save(*args, **kwargs)
        raise sqlite3.OperationalError("simulated metadata write interruption")

    profile_id = "atomic_fixture"
    profile = fixture_profile().model_copy(update={"profile_id": profile_id})
    monkeypatch.setattr(store, "_save_profile_in_transaction", fail_after_profile_write)
    with pytest.raises(sqlite3.OperationalError, match="interruption"):
        repository.create_text_provider_profile(
            profile_id, "Atomic fixture", configuration=profile
        )
    with store._read() as connection:
        assert connection.execute(
            "SELECT 1 FROM application_profiles WHERE profile_id = ?", (profile_id,)
        ).fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM application_text_profile_metadata WHERE profile_id = ?",
            (profile_id,),
        ).fetchone() is None

    monkeypatch.setattr(store, "_save_profile_in_transaction", original_save)
    created = repository.create_text_provider_profile(
        profile_id, "Atomic fixture", configuration=profile
    )
    monkeypatch.setattr(store, "_save_profile_in_transaction", fail_after_profile_write)
    with pytest.raises(sqlite3.OperationalError, match="interruption"):
        repository.update_text_provider_profile(
            profile_id,
            created.revision,
            display_name="Interrupted update",
            configuration=created.configuration,
        )
    recovered = repository.get_text_provider_profile(profile_id)
    assert recovered.revision == created.revision
    assert recovered.display_name == "Atomic fixture"


def test_production_runtime_composes_the_typed_h3_video_path(tmp_path: Path) -> None:
    provider = _RuntimeFakeH3()
    app = build_runtime_app(
        _settings(tmp_path),
        test_video_provider=provider,
        test_video_probe=lambda _content: ObservedVideo(
            5.167, 576, 1024, "h264", "aac", frame_rate=24, frame_count=124
        ),
        text_provider_resolver=FixtureResolver(),
    )

    with TestClient(app) as client:
        _activate_fixture_profile(client)
        project = client.post(
            "/api/v2/projects",
            json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
        )
        assert project.status_code == 201
        project_id = project.json()["id"]
        run = client.post(f"/api/v2/projects/{project_id}/pipeline-runs", json={})
        assert run.status_code == 202
        assert _await_terminal(client, run.json()["id"])["status"] == "succeeded"

        storage = app.state.project_folder_storage
        store = storage.projects.open(project_id)
        try:
            board = store.authoring.get_stage_head(project_id, StageName.STORYBOARD)
            shot = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD).shots[0]
        finally:
            store.close()
        approval = client.post(
            f"/api/v2/projects/{project_id}/storyboard-approval",
            json={
                "expectedRevision": board.revision,
                "contentHash": board.content_hash,
                "decision": "approve",
                "reviewer": "runtime H3 fixture",
                "gateSetVersion": "storyboard.v2",
            },
        )
        assert approval.status_code == 201
        asset = client.post(
            f"/api/v2/projects/{project_id}/managed-assets",
            files={"image": ("keyframe.png", _png(), "image/png")},
            data={
                "origin": "runtime H3 fixture",
                "rights": "unknown",
                "declared_additions_json": "[]",
            },
        )
        assert asset.status_code == 201
        asset_id = asset.json()["id"]
        draft = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={
                "editorScope": "visual_intent",
                "entityId": f"{shot.id}:{asset_id}",
                "baseCanonicalRevision": board.revision,
                "expectedDraftRevision": 0,
                "payload": {
                    "assetId": asset_id,
                    "shotId": shot.id,
                    "role": "shot_keyframe",
                    "identityIntent": "Retain the fixture identity.",
                    "sourceRefs": ["runtime H3 fixture"],
                },
            },
        )
        assert draft.status_code == 200
        intent = client.post(
            f"/api/v2/projects/{project_id}/managed-assets/{asset_id}/visual-intents",
            json={
                "shotId": shot.id,
                "role": "shot_keyframe",
                "identityIntent": "Retain the fixture identity.",
                "sourceRefs": ["runtime H3 fixture"],
                "consumedDraft": {
                    "editorScope": "visual_intent",
                    "entityId": f"{shot.id}:{asset_id}",
                    "draftRevision": draft.json()["draftRevision"],
                },
            },
        )
        assert intent.status_code == 201
        selected = client.post(
            f"/api/v2/projects/{project_id}/reviewed-keyframes",
            json={
                "assetId": asset_id,
                "shotId": shot.id,
                "sceneId": shot.scene_id,
                "expectedSelectionRevision": 0,
                "storyboardRevision": board.revision,
                "approvalId": approval.json()["decision"]["id"],
                "compatibilityNote": "The fixture matches the frozen H3 profile.",
                "visualIntentId": intent.json()["id"],
                "visualIntentRevision": intent.json()["revision"],
            },
        )
        assert selected.status_code == 201
        job = client.post(
            f"/api/v2/projects/{project_id}/video-jobs",
            json=reviewed_h3_body(client, project_id, {
                "approvalId": approval.json()["decision"]["id"],
                "shotId": shot.id,
                "storyboardRevision": board.revision,
                "expectedSelectionRevision": selected.json()["selectionRevision"],
                "idempotencyKey": "production-runtime-h3-fixture",
                "aspectPolicy": "reject_mismatch",
                "seed": 31,
            }),
        )
        assert job.status_code == 201
        binding = job.json()["snapshot"]["provider"]["backendBinding"]
        assert binding["adapterId"] == "minimax_h3_gateway"
        assert binding["instance"]["kind"] == "runtime_fixture_h3_v1"
        submitted = client.post(f"/api/v2/projects/{project_id}/video-jobs/{job.json()['id']}/submit")
        assert submitted.status_code == 200
        ingested = client.post(f"/api/v2/projects/{project_id}/video-jobs/{job.json()['id']}/reconcile")
        assert ingested.status_code == 200 and ingested.json()["state"] == "ingested"
        reviewed = client.post(
            f"/api/v2/projects/{project_id}/video-jobs/{job.json()['id']}/review",
            json={
                "reviewer": "runtime H3 fixture",
                "decision": "select",
                "note": "Select the locally ingested H3 fixture.",
                "expectedSelectionRevision": 0,
            },
        )
        assert reviewed.status_code == 409
        assert provider.submits and provider.downloads == 1
