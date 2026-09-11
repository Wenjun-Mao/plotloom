from __future__ import annotations

from base64 import b64decode
from io import BytesIO
from struct import pack
from threading import Event, Thread
from zlib import crc32

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_app
from plotloom.artifacts import MemoryArtifactStore
from plotloom.canonical_schema import ShotBeatLinkV2, StoryboardV2, V2CoverageRole
from plotloom.domain import STAGE_ORDER, StageName
from plotloom.managed_media import ManagedMediaLimits, inspect_import_image, publish_import
from plotloom.persistence import ManagedAssetRow, SQLiteRepository, StillPreviewRow

from .conftest import all_stage_payloads


def _png(red: int, green: int, blue: int) -> bytes:
    output = BytesIO()
    Image.new("RGB", (12, 8), (red, green, blue)).save(output, format="PNG")
    return output.getvalue()


def _jpeg(red: int, green: int, blue: int) -> bytes:
    output = BytesIO()
    Image.new("RGB", (12, 8), (red, green, blue)).save(output, format="JPEG")
    return output.getvalue()


def _animated_png() -> bytes:
    output = BytesIO()
    first = Image.new("RGBA", (12, 8), (10, 20, 30, 255))
    second = Image.new("RGBA", (12, 8), (30, 20, 10, 255))
    first.save(output, format="PNG", save_all=True, append_images=[second], duration=100, loop=0)
    return output.getvalue()


def _oversized_png_header() -> bytes:
    """A parseable PNG header whose raster exceeds P0's pixel budget."""

    payload = b"IHDR" + pack(">IIBBBBB", 5_000, 5_000, 8, 2, 0, 0, 0)
    header = pack(">I", 13) + payload + pack(">I", crc32(payload) & 0xFFFFFFFF)
    end = b"IEND"
    return b"\x89PNG\r\n\x1a\n" + header + pack(">I", 0) + end + pack(">I", crc32(end) & 0xFFFFFFFF)


def _complete_project_with_three_shots(repository: SQLiteRepository, brief):
    bible, graph, beats, storyboard = all_stage_payloads()
    first_scene = beats.scenes[0]
    first_scene_shots = [shot for shot in storyboard.shots if shot.scene_id == first_scene.id]
    first_shot = first_scene_shots[0]
    second_shot = first_scene_shots[1].model_copy(update={"duration_units": 2})
    first_shot = first_shot.model_copy(update={"duration_units": 2})
    third = first_shot.model_copy(update={"id": f"{first_shot.id}-third", "order": 3, "title": "第三镜头", "duration_units": 4})
    storyboard = StoryboardV2(
        shots=[
            first_shot if shot.id == first_shot.id else second_shot if shot.id == second_shot.id else shot
            for shot in storyboard.shots
        ] + [third],
        shot_beat_links=[
            *storyboard.shot_beat_links,
            ShotBeatLinkV2(shot_id=third.id, beat_id=first_scene.beat_ids[0], role=V2CoverageRole.SUPPORTING, coverage_weight=1.0),
        ],
    )
    project = repository.create_project(brief)
    for stage, payload in zip(STAGE_ORDER, (bible, graph, beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    return repository.get_project(project.id), first_scene.id


def _approval(client: TestClient, project_id: str) -> tuple[dict, dict]:
    review = client.get(f"/api/v2/projects/{project_id}/storyboard-review").json()
    approved = client.post(
        f"/api/v2/projects/{project_id}/storyboard-approval",
        json={
            "expectedRevision": review["head"]["revision"],
            "contentHash": review["head"]["contentHash"],
            "decision": "approve",
            "reviewer": "development operator",
            "gateSetVersion": review["gateEvaluation"]["gateSetVersion"],
            "note": "explicit local development review",
        },
    )
    assert approved.status_code == 201, approved.text
    return review, approved.json()["decision"]


def _import(client: TestClient, project_id: str, content: bytes, origin: str) -> dict:
    response = client.post(
        f"/api/v2/projects/{project_id}/managed-assets",
        files={"image": ("fixture.png", content, "image/png")},
        data={"origin": origin, "rights": "unknown", "declared_additions_json": "[\"reference only\"]"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _intent(client: TestClient, project_id: str, asset_id: str, role: str = "shot_keyframe") -> dict:
    response = client.post(
        f"/api/v2/projects/{project_id}/managed-assets/{asset_id}/visual-intents",
        json={
            "role": role,
            "identityIntent": "reference identity",
            "compositionIntent": "frame the authored subject",
            "styleIntent": "controlled development still",
            "sourceRefs": ["creator session reference"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_imported_still_preview_is_immutable_and_lifecycle_safe(repository, brief) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    store = MemoryArtifactStore()
    app = create_app(repository, artifact_store=store)
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        # Resolve from the persisted revision so the test does not make story
        # facts up outside the canonical contract.
        with repository._read() as session:
            persisted = repository._load_stage_payload(session, project.id, StageName.STORYBOARD)
            shots = [item.id for item in sorted((item for item in persisted.shots if item.scene_id == scene_id), key=lambda item: item.order)]
        assert len(shots) == 3

        assets = [_import(client, project.id, _png(20 * index, 20, 120), f"fixture {index}") for index in range(1, 5)]
        intents = [_intent(client, project.id, asset["id"]) for asset in assets]
        # Identical byte imports remain separate provenance records.
        same = _import(client, project.id, _png(20, 20, 120), "same bytes, separate declaration")
        listed = client.get(f"/api/v2/projects/{project.id}/managed-assets").json()
        assert len(listed["assets"]) == 5
        assert assets[0]["originalHash"] == same["originalHash"]
        assert assets[0]["id"] != same["id"]

        selection_revision = 0
        for shot_id, asset, intent in zip(shots, assets[:3], intents[:3], strict=True):
            selected = client.post(
                f"/api/v2/projects/{project.id}/reviewed-keyframes",
                json={
                    "assetId": asset["id"], "shotId": shot_id, "sceneId": scene_id,
                    "expectedSelectionRevision": selection_revision,
                    "storyboardRevision": board.revision, "approvalId": approval["id"],
                    "compatibilityNote": "creator confirmed compatibility",
                    "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
                },
            )
            assert selected.status_code == 201, selected.text
            selection_revision += 1

        stale_writer = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes",
            json={
                "assetId": assets[3]["id"], "shotId": shots[0], "sceneId": scene_id,
                "expectedSelectionRevision": 0,
                "storyboardRevision": board.revision, "approvalId": approval["id"],
                "compatibilityNote": "must not overwrite a newer selection",
                "visualIntentId": intents[3]["id"], "visualIntentRevision": intents[3]["revision"],
            },
        )
        assert stale_writer.status_code == 409

        preview = client.post(
            f"/api/v2/projects/{project.id}/still-previews",
            json={
                "sceneId": scene_id, "shotIds": shots,
                "expectedSelectionRevision": selection_revision,
                "storyboardRevision": board.revision, "approvalId": approval["id"],
            },
        )
        assert preview.status_code == 201, preview.text
        frozen = preview.json()
        assert frozen["state"] == "current"
        assert [frame["shotId"] for frame in frozen["manifest"]["frames"]] == shots
        assert [frame["visualIntentId"] for frame in frozen["manifest"]["frames"]] == [intent["id"] for intent in intents[:3]]
        assert frozen["manifest"]["canonicalInputRevisions"]
        assert client.get(f"/api/v2/projects/{project.id}/managed-assets/{assets[0]['id']}/original").content == _png(20, 20, 120)

        # A selection for an unrelated Shot advances the global append
        # sequence but must not invalidate this preview's frozen dependencies.
        unrelated_shot = next(shot for shot in repository.get_stage_payload(project.id, StageName.STORYBOARD).shots if shot.scene_id != scene_id)
        unrelated = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes",
            json={
                "assetId": assets[3]["id"], "shotId": unrelated_shot.id, "sceneId": unrelated_shot.scene_id,
                "expectedSelectionRevision": selection_revision,
                "storyboardRevision": board.revision, "approvalId": approval["id"],
                "compatibilityNote": "unrelated current shot selection",
                "visualIntentId": intents[3]["id"], "visualIntentRevision": intents[3]["revision"],
            },
        )
        assert unrelated.status_code == 201, unrelated.text
        selection_revision += 1
        assert client.get(f"/api/v2/projects/{project.id}/still-previews").json()["previews"][0]["state"] == "current"

        # Refining an intent that is actually frozen into a frame makes that
        # preview stale; a later intent must not be silently ignored.
        revised_first_intent = _intent(client, project.id, assets[0]["id"])
        assert revised_first_intent["revision"] == 2
        assert client.get(f"/api/v2/projects/{project.id}/still-previews").json()["previews"][0]["state"] == "stale"

        # Preview rows and asset metadata are storage evidence, not trusted
        # projection inputs. Deliberately corrupt each and verify read-time
        # derivation rejects the frozen preview without rewriting its history.
        with repository._write() as session:  # noqa: SLF001 - durable corruption fixture
            session.get(StillPreviewRow, frozen["id"]).manifest_hash = "0" * 64
        assert client.get(f"/api/v2/projects/{project.id}/still-previews").json()["previews"][0]["state"] == "corrupt"
        with repository._write() as session:  # noqa: SLF001 - durable corruption fixture
            session.get(StillPreviewRow, frozen["id"]).manifest_hash = frozen["manifestHash"]
            session.get(ManagedAssetRow, assets[0]["id"]).display_hash = "f" * 64
        assert client.get(f"/api/v2/projects/{project.id}/still-previews").json()["previews"][0]["state"] == "corrupt"
        with repository._write() as session:  # noqa: SLF001 - durable corruption fixture
            session.get(ManagedAssetRow, assets[0]["id"]).display_hash = assets[0]["displayHash"]

        replacement = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes",
            json={
                "assetId": assets[3]["id"], "shotId": shots[0], "sceneId": scene_id,
                "expectedSelectionRevision": selection_revision,
                "storyboardRevision": board.revision, "approvalId": approval["id"],
                "compatibilityNote": "replacement explicitly reviewed",
                "visualIntentId": intents[3]["id"], "visualIntentRevision": intents[3]["revision"],
            },
        )
        assert replacement.status_code == 201
        history = client.get(f"/api/v2/projects/{project.id}/still-previews").json()["previews"]
        assert history[0]["id"] == frozen["id"]
        assert history[0]["state"] == "stale"

        subset_preview = client.post(
            f"/api/v2/projects/{project.id}/still-previews",
            json={
                "sceneId": scene_id, "shotIds": shots[:2],
                "expectedSelectionRevision": selection_revision + 1,
                "storyboardRevision": board.revision, "approvalId": approval["id"],
            },
        )
        assert subset_preview.status_code == 201, subset_preview.text

        revoked = client.post(
            f"/api/v2/projects/{project.id}/storyboard-approval",
            json={
                "expectedRevision": board.revision,
                "contentHash": board.content_hash,
                "decision": "revoke",
                "reviewer": "development operator",
                "gateSetVersion": "storyboard.v2",
            },
        )
        assert revoked.status_code == 201, revoked.text
        assert client.get(f"/api/v2/projects/{project.id}/still-previews").json()["previews"][0]["state"] == "revoked"

        archived = client.post(f"/api/v2/projects/{project.id}/archive", json={"expectedLifecycleRevision": 1})
        assert archived.status_code == 200
        deleted = client.post(
            f"/api/v2/projects/{project.id}/permanent-delete",
            json={"expectedLifecycleRevision": 2, "confirmationTitle": project.brief.title},
        )
        assert deleted.status_code == 409
        assert deleted.json()["code"] == "project_managed_assets_present"


def test_storyboard_edit_blocks_reviewed_selection_until_reapproved(repository, brief) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore())
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        old_board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        asset = _import(client, project.id, _png(80, 30, 10), "approval-bound fixture")
        intent = _intent(client, project.id, asset["id"])
        storyboard = repository.get_stage_payload(project.id, StageName.STORYBOARD)
        changed = storyboard.model_copy(update={
            "shots": [
                shot.model_copy(update={"title": f"{shot.title} (edited)"})
                if shot.scene_id == scene_id and shot.order == 1 else shot
                for shot in storyboard.shots
            ],
        })
        current_board = repository.update_stage(
            project.id, StageName.STORYBOARD, old_board.revision, changed
        )
        selected_shot = next(shot for shot in changed.shots if shot.scene_id == scene_id and shot.order == 1)

        blocked = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes",
            json={
                "assetId": asset["id"], "shotId": selected_shot.id, "sceneId": scene_id,
                "expectedSelectionRevision": 0,
                "storyboardRevision": old_board.revision, "approvalId": approval["id"],
                "compatibilityNote": "old approval must not admit a changed board",
                "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
            },
        )
        assert blocked.status_code == 409

        _review, current_approval = _approval(client, project.id)
        accepted = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes",
            json={
                "assetId": asset["id"], "shotId": selected_shot.id, "sceneId": scene_id,
                "expectedSelectionRevision": 0,
                "storyboardRevision": current_board.revision, "approvalId": current_approval["id"],
                "compatibilityNote": "new current approval admits the revised board",
                "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
            },
        )
        assert accepted.status_code == 201, accepted.text


def test_corrupt_deduplicated_blob_is_rejected_before_metadata_publication(repository, brief) -> None:
    project = repository.create_project(brief)
    store = MemoryArtifactStore()
    app = create_app(repository, artifact_store=store)
    content = _png(1, 2, 3)
    with TestClient(app) as client:
        _import(client, project.id, content, "first declaration")
        digest = next(iter(store._items))
        store._items[digest] = b"corrupt"  # noqa: SLF001 - intentional storage corruption fixture
        rejected = client.post(
            f"/api/v2/projects/{project.id}/managed-assets",
            files={"image": ("again.png", content, "image/png")},
            data={"origin": "second declaration", "rights": "unknown"},
        )
        assert rejected.status_code == 422
        assert rejected.json()["code"] == "corrupt_existing_blob"
        assert len(client.get(f"/api/v2/projects/{project.id}/managed-assets").json()["assets"]) == 1


def test_decode_boundaries_reject_invalid_or_unsupported_uploads(repository, brief) -> None:
    project = repository.create_project(brief)
    with TestClient(create_app(repository, artifact_store=MemoryArtifactStore())) as client:
        for name, content in (("not-image.txt", b"not an image"), ("animated.gif", b"GIF89a")):
            response = client.post(
                f"/api/v2/projects/{project.id}/managed-assets",
                files={"image": (name, content, "application/octet-stream")},
                data={"origin": "boundary fixture", "rights": "unknown"},
            )
            assert response.status_code == 422
        oversized = client.post(
            f"/api/v2/projects/{project.id}/managed-assets",
            files={"image": ("oversized.png", _oversized_png_header(), "image/png")},
            data={"origin": "pixel-boundary fixture", "rights": "unknown"},
        )
        assert oversized.status_code == 422
        assert oversized.json()["code"] == "media_pixel_limit"
        assert client.get(f"/api/v2/projects/{project.id}/managed-assets").json()["assets"] == []


def test_import_admission_rejects_unowned_publication_and_cross_project_access(repository, brief) -> None:
    source = repository.create_project(brief)
    target, scene_id = _complete_project_with_three_shots(repository, brief)
    store = MemoryArtifactStore()
    with TestClient(create_app(repository, artifact_store=store)) as client:
        missing = client.post(
            "/api/v2/projects/does-not-exist/managed-assets",
            files={"image": ("missing.png", _png(1, 2, 3), "image/png")},
            data={"origin": "rejected project", "rights": "unknown"},
        )
        assert missing.status_code == 404
        assert store._items == {}  # noqa: SLF001 - publication must not begin before admission

        archived = client.post(
            f"/api/v2/projects/{source.id}/archive", json={"expectedLifecycleRevision": 1},
        )
        assert archived.status_code == 200
        blocked = client.post(
            f"/api/v2/projects/{source.id}/managed-assets",
            files={"image": ("archived.png", _png(4, 5, 6), "image/png")},
            data={"origin": "archived project", "rights": "unknown"},
        )
        assert blocked.status_code == 409
        assert store._items == {}  # noqa: SLF001 - archived admission cannot write a blob

        # Create one source-owned asset, then prove every public read/bind
        # route refuses it from another project's namespace.
        repository.restore_project(source.id, expected_lifecycle_revision=2)
        source_asset = _import(client, source.id, _png(7, 8, 9), "source project")
        opaque_intent = client.post(
            f"/api/v2/projects/{source.id}/managed-assets/{source_asset['id']}/visual-intents",
            json={"role": "shot_keyframe"},
        )
        assert opaque_intent.status_code == 422
        source_intent = _intent(client, source.id, source_asset["id"])
        assert client.get(
            f"/api/v2/projects/{target.id}/managed-assets/{source_asset['id']}/display"
        ).status_code == 404
        assert client.post(
            f"/api/v2/projects/{target.id}/managed-assets/{source_asset['id']}/visual-intents",
            json={
                "role": "shot_keyframe",
                "compositionIntent": "cross-project attempt",
                "sourceRefs": ["cross-project attempt"],
            },
        ).status_code == 404

        _review, approval = _approval(client, target.id)
        board = repository.get_stage_head(target.id, StageName.STORYBOARD)
        target_shot = next(shot for shot in repository.get_stage_payload(target.id, StageName.STORYBOARD).shots if shot.scene_id == scene_id)
        cross_bind = client.post(
            f"/api/v2/projects/{target.id}/reviewed-keyframes",
            json={
                "assetId": source_asset["id"], "shotId": target_shot.id, "sceneId": scene_id,
                "expectedSelectionRevision": 0, "storyboardRevision": board.revision, "approvalId": approval["id"],
                "compatibilityNote": "must not cross project", "visualIntentId": source_intent["id"],
                "visualIntentRevision": source_intent["revision"],
            },
        )
        assert cross_bind.status_code == 404
        assert client.get(f"/api/v2/projects/{target.id}/managed-assets").json()["assets"] == []


def test_import_publication_and_archive_are_serialized_by_lifecycle_admission(repository, brief) -> None:
    class BlockingStore(MemoryArtifactStore):
        def __init__(self) -> None:
            super().__init__()
            self.entered_publication = Event()
            self.release_publication = Event()
            self._block_once = True

        def put(self, content: bytes, *, expected_hash: str | None = None) -> str:
            if self._block_once:
                self._block_once = False
                self.entered_publication.set()
                assert self.release_publication.wait(5)
            return super().put(content, expected_hash=expected_hash)

    project = repository.create_project(brief)
    content = _png(11, 22, 33)
    observed = inspect_import_image(content)
    store = BlockingStore()
    import_errors: list[Exception] = []
    archive_errors: list[Exception] = []
    archived = Event()

    def import_asset() -> None:
        try:
            repository.record_managed_import(
                project.id,
                original_hash=observed.content_hash,
                display_hash=observed.display_hash,
                mime_type=observed.mime_type,
                byte_size=observed.byte_size,
                width=observed.width,
                height=observed.height,
                declaration={"origin": "race fixture", "rights": "unknown", "rightsNote": None, "declaredAdditions": []},
                publish=lambda: publish_import(store, content, observed),
            )
        except Exception as error:  # pragma: no cover - asserted after the thread joins
            import_errors.append(error)

    def archive_project() -> None:
        try:
            repository.archive_project(project.id, expected_lifecycle_revision=1)
        except Exception as error:  # pragma: no cover - asserted after the thread joins
            archive_errors.append(error)
        finally:
            archived.set()

    importer = Thread(target=import_asset)
    importer.start()
    assert store.entered_publication.wait(2)
    archiver = Thread(target=archive_project)
    archiver.start()
    # Archive cannot observe a half-published import: it waits for the same
    # lifecycle lease that owns both admission and immutable metadata.
    assert not archived.wait(0.1)
    store.release_publication.set()
    importer.join(5)
    archiver.join(5)

    assert not import_errors
    assert not archive_errors
    assert repository.get_project(project.id).lifecycle_status.value == "archived"
    assert len(repository.list_managed_assets(project.id)) == 1


def test_import_format_and_configured_size_boundaries(repository, brief) -> None:
    project = repository.create_project(brief)
    store = MemoryArtifactStore()
    with TestClient(create_app(repository, artifact_store=store)) as client:
        for name, content, mime in (
            ("valid.jpg", _jpeg(10, 20, 30), "image/jpeg"),
            ("valid.png", _png(30, 20, 10), "image/png"),
        ):
            response = client.post(
                f"/api/v2/projects/{project.id}/managed-assets",
                files={"image": (name, content, mime)},
                data={"origin": "format fixture", "rights": "unknown"},
            )
            assert response.status_code == 201, response.text
        for name, content, mime in (
            ("invalid.jpg", b"not a JPEG", "image/jpeg"),
            ("invalid.png", b"not a PNG", "image/png"),
            ("bad-checksum.png", b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAF/gJ/l9mZlgAAAABJRU5ErkJggg=="), "image/png"),
            ("animated.png", _animated_png(), "image/png"),
        ):
            rejected = client.post(
                f"/api/v2/projects/{project.id}/managed-assets",
                files={"image": (name, content, mime)},
                data={"origin": "format boundary", "rights": "unknown"},
            )
            assert rejected.status_code == 422
        assert len(client.get(f"/api/v2/projects/{project.id}/managed-assets").json()["assets"]) == 2

    constrained = repository.create_project(brief)
    with TestClient(create_app(
        repository,
        artifact_store=MemoryArtifactStore(),
        managed_media_limits=ManagedMediaLimits(max_import_bytes=10_000, max_import_pixels=50),
    )) as client:
        pixel_limited = client.post(
            f"/api/v2/projects/{constrained.id}/managed-assets",
            files={"image": ("small-but-bounded.png", _png(1, 2, 3), "image/png")},
            data={"origin": "configured pixel limit", "rights": "unknown"},
        )
        assert pixel_limited.status_code == 422
        assert pixel_limited.json()["code"] == "media_pixel_limit"
