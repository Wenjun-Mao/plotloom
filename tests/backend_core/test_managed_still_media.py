from __future__ import annotations

from io import BytesIO
from struct import pack
from zlib import crc32

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_app
from plotloom.artifacts import MemoryArtifactStore
from plotloom.canonical_schema import ShotBeatLinkV2, StoryboardV2, V2CoverageRole
from plotloom.domain import STAGE_ORDER, StageName
from plotloom.persistence import ManagedAssetRow, SQLiteRepository, StillPreviewRow

from .conftest import all_stage_payloads


def _png(red: int, green: int, blue: int) -> bytes:
    output = BytesIO()
    Image.new("RGB", (12, 8), (red, green, blue)).save(output, format="PNG")
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
        # Identical byte imports remain separate provenance records.
        same = _import(client, project.id, _png(20, 20, 120), "same bytes, separate declaration")
        listed = client.get(f"/api/v2/projects/{project.id}/managed-assets").json()
        assert len(listed["assets"]) == 5
        assert assets[0]["originalHash"] == same["originalHash"]
        assert assets[0]["id"] != same["id"]

        selection_revision = 0
        for shot_id, asset in zip(shots, assets[:3], strict=True):
            selected = client.post(
                f"/api/v2/projects/{project.id}/reviewed-keyframes",
                json={
                    "assetId": asset["id"], "shotId": shot_id, "sceneId": scene_id,
                    "expectedSelectionRevision": selection_revision,
                    "storyboardRevision": board.revision, "approvalId": approval["id"],
                    "compatibilityNote": "creator confirmed compatibility",
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
        assert client.get(f"/api/v2/projects/{project.id}/managed-assets/{assets[0]['id']}/original").content == _png(20, 20, 120)

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
            },
        )
        assert replacement.status_code == 201
        history = client.get(f"/api/v2/projects/{project.id}/still-previews").json()["previews"]
        assert history[0]["id"] == frozen["id"]
        assert history[0]["state"] == "stale"

        # This P0 projection is exactly three contiguous shots at its API
        # boundary too; a UI caller cannot weaken it by bypassing the form.
        invalid_length = client.post(
            f"/api/v2/projects/{project.id}/still-previews",
            json={
                "sceneId": scene_id, "shotIds": shots[:2],
                "expectedSelectionRevision": selection_revision + 1,
                "storyboardRevision": board.revision, "approvalId": approval["id"],
            },
        )
        assert invalid_length.status_code == 422

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
