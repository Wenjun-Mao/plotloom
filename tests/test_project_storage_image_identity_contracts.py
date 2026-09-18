"""Project-owned P1.5 identity delivery and replacement contracts."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.canonical_schema import CharacterV2
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage, ProjectStore
from plotloom.persistence.project.cast import ProjectCastPersistence

from tests.project_storage_fixtures import FixtureResolver, fixture_profile


def _png(color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 16), color).save(output, format="PNG")
    return output.getvalue()


def _install_visible_fixture_character(store: ProjectStore) -> None:
    """Make the fixture's first shot require one explicit identity decision."""

    project_id = store.manifest.project_id
    hero = CharacterV2(
        id="fixture-hero",
        name="Fixture hero",
        role="lead",
        description="A deterministic identity-reference fixture.",
        visual_anchors=["red coat"],
        sound_anchors=[],
        allowed_states=["alert"],
        continuity_rules=["The red coat remains visible."],
        goal="Keep the fixture coherent.",
        traits=["steady"],
        voice_anchors=[],
    )
    bible = store.authoring.get_stage_payload(project_id, StageName.STORY_BIBLE)
    store.update_stage(
        StageName.STORY_BIBLE,
        bible.model_copy(update={"characters": [hero]}),
        expected_revision=store.authoring.get_stage_head(
            project_id, StageName.STORY_BIBLE
        ).revision,
    )
    graph = store.authoring.get_stage_payload(project_id, StageName.STORY_GRAPH)
    store.update_stage(
        StageName.STORY_GRAPH,
        graph,
        expected_revision=store.authoring.get_stage_head(
            project_id, StageName.STORY_GRAPH
        ).revision,
    )
    plan = store.authoring.get_stage_payload(project_id, StageName.SCENE_BEATS)
    store.update_stage(
        StageName.SCENE_BEATS,
        plan.model_copy(
            update={
                "scenes": [
                    scene.model_copy(update={"character_ids": [hero.id]})
                    for scene in plan.scenes
                ]
            }
        ),
        expected_revision=store.authoring.get_stage_head(
            project_id, StageName.SCENE_BEATS
        ).revision,
    )
    storyboard = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    store.update_stage(
        StageName.STORYBOARD,
        storyboard.model_copy(
            update={
                "shots": [
                    shot.model_copy(update={"character_ids": [hero.id]})
                    for shot in storyboard.shots
                ]
            }
        ),
        expected_revision=store.authoring.get_stage_head(
            project_id, StageName.STORYBOARD
        ).revision,
    )


def _direction_draft(
    client: TestClient, project_id: str, shot_id: str, revision: int
) -> dict:
    response = client.put(
        f"/api/v2/projects/{project_id}/authoring-drafts",
        json={
            "editorScope": "image_direction",
            "entityId": f"{shot_id}:original",
            "baseCanonicalRevision": revision,
            "expectedDraftRevision": 0,
            "payload": {
                "shotId": shot_id,
                "targetId": "original",
                "contextId": "identity-currentness-fixture",
                "presentationChange": "Close portrait for cross-shot identity review.",
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _identity_delivery(
    path: Path, job: dict, reference_hash: str, content: bytes
) -> None:
    provenance = {
        "codeRevision": "a" * 40,
        "skillVersion": "plotloom-image-specialist.v3",
        "skillHash": "b" * 64,
    }
    path.mkdir(parents=True, exist_ok=True)
    (path / "executor-pin.json").write_text(
        json.dumps(
            {
                "jobId": job["id"],
                "requestHash": job["requestHash"],
                "executionContract": "codex_specialist.v2",
                **provenance,
            }
        ),
        encoding="utf-8",
    )
    outputs = path / "outputs"
    outputs.mkdir()
    (outputs / "candidate.png").write_bytes(content)
    (path / "completion.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "jobId": job["id"],
                "requestHash": job["requestHash"],
                "deliveryId": "identity-001",
                "actualPrompt": "Offline identity-aware fixture delivery.",
                "outputs": [
                    {
                        "filename": "candidate.png",
                        "sha256": sha256(content).hexdigest(),
                        "role": "original",
                    }
                ],
                "toolEvidence": {
                    "tool": "codex_imagegen",
                    "taskId": "identity-currentness-fixture",
                    "available": True,
                },
                "referenceUse": {
                    "viewedReferenceHashes": [reference_hash],
                    "identityNotes": "Fixture identity reference was viewed.",
                },
                "executorProvenance": provenance,
            }
        ),
        encoding="utf-8",
    )


def test_identity_image_delivery_is_reviewed_then_stales_on_reference_replacement(
    tmp_path: Path, monkeypatch,
) -> None:
    accepted_cast = {
        "revision": 2,
        "contentHash": "c" * 64,
        "castCharacterId": "C01",
        "appearance": "Short rain-dark hair and a worn navy weatherproof coat.",
        "image": {"prompt": "Use the accepted coastal watch officer direction."},
    }
    monkeypatch.setattr(
        ProjectCastPersistence,
        "identity_context_in_session",
        lambda _self, _session, _project_id, consumer_id: (
            accepted_cast if consumer_id == "fixture-hero" else None
        ),
    )
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(FixtureResolver()).execute(store, profile=fixture_profile())
    _install_visible_fixture_character(store)
    store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    try:
        storyboard = client.get(f"/api/v2/projects/{project_id}/stages").json()["stages"][-1]
        shot = storyboard["payload"]["shots"][0]
        approval = client.post(
            f"/api/v2/projects/{project_id}/storyboard-approval",
            json={
                "expectedRevision": storyboard["head"]["revision"],
                "contentHash": storyboard["head"]["contentHash"],
                "decision": "approve",
                "reviewer": "identity fixture",
                "gateSetVersion": "storyboard.v2",
            },
        )
        assert approval.status_code == 201, approval.text
        payload = {
            "approvalId": approval.json()["decision"]["id"],
            "shotId": shot["id"],
            "storyboardRevision": storyboard["head"]["revision"],
            "presentationChange": "Close portrait for cross-shot identity review.",
            "contextId": "identity-currentness-fixture",
        }
        draft = _direction_draft(
            client, project_id, shot["id"], storyboard["head"]["revision"]
        )
        missing = client.post(
            f"/api/v2/projects/{project_id}/image-jobs",
            json={
                **payload,
                "contractVersion": 3,
                "consumedDraft": {
                    "editorScope": "image_direction",
                    "entityId": f"{shot['id']}:original",
                    "draftRevision": draft["draftRevision"],
                },
            },
        )
        assert missing.status_code == 422
        assert missing.json()["code"] == "identity_reference_missing"

        reference = client.post(
            f"/api/v2/projects/{project_id}/managed-assets",
            files={"image": ("reference.png", _png((50, 80, 120)), "image/png")},
            data={
                "origin": "identity fixture reference",
                "rights": "unknown",
                "declared_additions_json": "[]",
            },
        )
        assert reference.status_code == 201, reference.text
        selected_reference = client.post(
            f"/api/v2/projects/{project_id}/character-references",
            json={
                "characterId": "fixture-hero",
                "authority": "story_bible",
                "primaryAssetId": reference.json()["id"],
                "complementaryAssetIds": [],
                "expectedReferenceRevision": 0,
                "reviewer": "identity fixture",
                "notes": "Stable face and build, not a framing mandate.",
            },
        )
        assert selected_reference.status_code == 201, selected_reference.text
        job_response = client.post(
            f"/api/v2/projects/{project_id}/image-jobs",
            json={
                **payload,
                "contractVersion": 3,
                "consumedDraft": {
                    "editorScope": "image_direction",
                    "entityId": f"{shot['id']}:original",
                    "draftRevision": draft["draftRevision"],
                },
            },
        )
        assert job_response.status_code == 201, job_response.text
        job = job_response.json()["job"]
        frozen = job["request"]["frozenSnapshot"]
        assert frozen["visibleCharacterIds"] == ["fixture-hero"]
        assert frozen["characterIdentity"][0]["referenceDecisionId"] == selected_reference.json()["id"]
        assert frozen["characterIdentity"][0]["acceptedCast"] == accepted_cast
        assert [entry["role"] for entry in frozen["references"]] == ["character_identity"]

        copied = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/copy")
        assert copied.status_code == 200, copied.text
        package = Path(copied.json()["packagePath"])
        package_request = json.loads((package / "request.json").read_text(encoding="utf-8"))
        assert package_request["packageVersion"] == 4
        assert package_request["references"][0]["role"] == "character_identity:fixture-hero"
        assert "characterIdentity[].acceptedCast" in (
            package / "COPY_ASSIGNMENT.txt"
        ).read_text(encoding="utf-8")
        delivery = Path(copied.json()["deliveryPath"])
        pin = {
            "jobId": job["id"],
            "requestHash": job["requestHash"],
            "executionContract": "codex_specialist.v2",
            "skillVersion": "plotloom-image-specialist.v3",
            "codeRevision": "a" * 40,
            "skillHash": "b" * 64,
        }
        delivery.mkdir(parents=True)
        (delivery / "executor-pin.json").write_text(json.dumps(pin), encoding="utf-8")
        awaiting = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
        assert awaiting.status_code == 200
        assert awaiting.json()["state"] == "awaiting_delivery"
        assert client.get(f"/api/v2/projects/{project_id}/image-jobs").json()["jobs"][0]["deliveries"] == []

        _identity_delivery(
            delivery,
            job,
            reference.json()["originalHash"],
            _png((40, 90, 140)),
        )
        candidate_delivery = client.post(
            f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh"
        )
        assert candidate_delivery.status_code == 200, candidate_delivery.text
        candidate = candidate_delivery.json()["candidates"][0]["asset"]
        intent_draft = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={
                "editorScope": "visual_intent",
                "entityId": f"{shot['id']}:{candidate['id']}",
                "baseCanonicalRevision": storyboard["head"]["revision"],
                "expectedDraftRevision": 0,
                "payload": {
                    "assetId": candidate["id"],
                    "shotId": shot["id"],
                    "role": "shot_keyframe",
                    "identityIntent": "fixture hero identity",
                    "sourceRefs": ["identity fixture"],
                },
            },
        )
        assert intent_draft.status_code == 200, intent_draft.text
        intent = client.post(
            f"/api/v2/projects/{project_id}/managed-assets/{candidate['id']}/visual-intents",
            json={
                "shotId": shot["id"],
                "role": "shot_keyframe",
                "identityIntent": "fixture hero identity",
                "sourceRefs": ["identity fixture"],
                "consumedDraft": {
                    "editorScope": "visual_intent",
                    "entityId": f"{shot['id']}:{candidate['id']}",
                    "draftRevision": intent_draft.json()["draftRevision"],
                },
            },
        )
        assert intent.status_code == 201, intent.text
        binding = client.post(
            f"/api/v2/projects/{project_id}/reviewed-keyframes",
            json={
                "assetId": candidate["id"],
                "shotId": shot["id"],
                "sceneId": shot["sceneId"],
                "expectedSelectionRevision": 0,
                "storyboardRevision": storyboard["head"]["revision"],
                "approvalId": approval.json()["decision"]["id"],
                "compatibilityNote": "Creator selected the identity candidate.",
                "visualIntentId": intent.json()["id"],
                "visualIntentRevision": intent.json()["revision"],
            },
        )
        assert binding.status_code == 201, binding.text
        preview_payload = {
            "sceneId": shot["sceneId"],
            "shotIds": [shot["id"]],
            "expectedSelectionRevision": 1,
            "storyboardRevision": storyboard["head"]["revision"],
            "approvalId": approval.json()["decision"]["id"],
        }
        assert client.post(
            f"/api/v2/projects/{project_id}/still-previews", json=preview_payload
        ).status_code == 409
        review = client.post(
            f"/api/v2/projects/{project_id}/same-person-reviews",
            json={
                "bindingId": binding.json()["id"],
                "expectedReviewRevision": 0,
                "reviewer": "identity fixture",
                "comparisons": [
                    {
                        "characterId": "fixture-hero",
                        "judgment": "pass",
                        "identityNotes": "Face and build match.",
                        "stateNotes": "Shot state remains authored.",
                    }
                ],
                "notes": "Human visual review, not face-recognition evidence.",
            },
        )
        assert review.status_code == 201, review.text
        preview = client.post(
            f"/api/v2/projects/{project_id}/still-previews", json=preview_payload
        )
        assert preview.status_code == 201
        assert preview.json()["manifest"]["frames"][0]["identityReviewId"] == review.json()["id"]

        replacement_asset = client.post(
            f"/api/v2/projects/{project_id}/managed-assets",
            files={"image": ("replacement.png", _png((120, 80, 50)), "image/png")},
            data={
                "origin": "replacement identity fixture",
                "rights": "unknown",
                "declared_additions_json": "[]",
            },
        )
        assert replacement_asset.status_code == 201, replacement_asset.text
        replaced = client.post(
            f"/api/v2/projects/{project_id}/character-references",
            json={
                "characterId": "fixture-hero",
                "authority": "story_bible",
                "primaryAssetId": replacement_asset.json()["id"],
                "complementaryAssetIds": [],
                "expectedReferenceRevision": selected_reference.json()["stateRevision"],
                "reviewer": "identity fixture",
                "notes": "Explicit replacement preserves the earlier decision.",
            },
        )
        assert replaced.status_code == 201, replaced.text
        assert client.get(f"/api/v2/projects/{project_id}/image-jobs").json()["jobs"][0]["current"] is False
        assert client.get(f"/api/v2/projects/{project_id}/same-person-reviews").json()["reviews"][0]["current"] is False
        assert client.get(f"/api/v2/projects/{project_id}/still-previews").json()["previews"][0]["state"] == "stale"
        assert len(client.get(f"/api/v2/projects/{project_id}/character-references").json()["decisions"]) == 2
    finally:
        client.close()
