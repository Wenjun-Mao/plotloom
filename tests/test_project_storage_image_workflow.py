"""Offline direct-storage proof for the existing still/image workbench routes."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage

# The deterministic text fixture is intentionally reused rather than inventing
# a second project or provider harness for the storage-only media proof.
from tests.test_project_storage import _FixtureResolver, _fixture_profile


def _png(color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 16), color).save(output, format="PNG")
    return output.getvalue()


def _approve(client: TestClient, project_id: str, storage: ProjectFolderStorage) -> dict:
    store = storage.projects.open(project_id)
    try:
        board = store.repository.get_stage_head(project_id, StageName.STORYBOARD)
    finally:
        store.close()
    response = client.post(
        f"/api/v2/projects/{project_id}/storyboard-approval",
        json={
            "expectedRevision": board.revision,
            "contentHash": board.content_hash,
            "decision": "approve",
            "reviewer": "offline fixture",
            "gateSetVersion": "storyboard.v2",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["decision"]


def _complete_delivery(
    path: Path,
    job: dict,
    content: bytes,
    delivery_id: str,
    *,
    actual_prompt: str = "Offline fixture delivery; no live generation occurred.",
) -> None:
    (path / "outputs").mkdir(parents=True, exist_ok=True)
    (path / "outputs" / "candidate.png").write_bytes(content)
    (path / "completion.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "jobId": job["id"],
                "requestHash": job["requestHash"],
                "deliveryId": delivery_id,
                "actualPrompt": actual_prompt,
                "outputs": [{"filename": "candidate.png", "sha256": sha256(content).hexdigest(), "role": "original"}],
                "toolEvidence": {"tool": "codex_imagegen", "taskId": "offline-fixture", "available": True},
                "limitations": ["fixture raster only"],
            }
        ),
        encoding="utf-8",
    )


def test_project_owned_image_handoff_isolated_across_restart_and_stales_after_intent_replacement(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    first = storage.projects.create(FIXED_CHINESE_BRIEF)
    second = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"title": "第二个图像项目"}))
    ProjectPipelineExecutor(_FixtureResolver()).execute(first, profile=_fixture_profile())
    ProjectPipelineExecutor(_FixtureResolver()).execute(second, profile=_fixture_profile())
    first_id, second_id = first.project().id, second.project().id
    first_home = first.home.resolve()
    first.close()
    second.close()

    client = TestClient(create_project_folder_authoring_app(storage))
    assert client.get("/api/v2/authoring-draft-capabilities").json() == {
        "durableProjectDrafts": True,
        "durableMediaDrafts": True,
        "explicitProjectClose": True,
    }
    approval = _approve(client, first_id, storage)
    _approve(client, second_id, storage)
    stages = client.get(f"/api/v2/projects/{first_id}/stages").json()["stages"]
    storyboard = stages[-1]
    shot = storyboard["payload"]["shots"][0]

    imported_bytes = _png((12, 42, 90))
    imported = client.post(
        f"/api/v2/projects/{first_id}/managed-assets",
        files={"image": ("reference.png", imported_bytes, "image/png")},
        data={"origin": "offline fixture reference", "rights": "unknown", "declared_additions_json": "[]"},
    )
    assert imported.status_code == 201, imported.text
    asset = imported.json()
    assert client.get(f"/api/v2/projects/{second_id}/managed-assets").json()["assets"] == []

    # The media form drafts use the same project/SQLite CAS boundary as the
    # canonical editors, but only after project creation produced a durable ID.
    visual_draft = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "visual_intent",
            "entityId": f"{shot['id']}:{asset['id']}",
            "baseCanonicalRevision": storyboard["head"]["revision"],
            "expectedDraftRevision": 0,
            "payload": {
                "assetId": asset["id"], "shotId": shot["id"], "role": "shot_keyframe",
                "identityIntent": "Preserve the fixture identity.", "sourceRefs": ["offline fixture"],
            },
        },
    )
    assert visual_draft.status_code == 200, visual_draft.text
    newer_visual_draft = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "visual_intent",
            "entityId": f"{shot['id']}:{asset['id']}",
            "baseCanonicalRevision": storyboard["head"]["revision"],
            "expectedDraftRevision": visual_draft.json()["draftRevision"],
            "payload": {
                "assetId": asset["id"], "shotId": shot["id"], "role": "shot_keyframe",
                "identityIntent": "Preserve the fixture identity.", "sourceRefs": ["offline fixture"],
            },
        },
    )
    assert newer_visual_draft.status_code == 200, newer_visual_draft.text
    stale_semantic_save = client.post(
        f"/api/v2/projects/{first_id}/managed-assets/{asset['id']}/visual-intents",
        json={
            "shotId": shot["id"], "role": "shot_keyframe",
            "identityIntent": "Preserve the fixture identity.", "sourceRefs": ["offline fixture"],
            "consumedDraft": {"editorScope": "visual_intent", "entityId": f"{shot['id']}:{asset['id']}", "draftRevision": visual_draft.json()["draftRevision"]},
        },
    )
    assert stale_semantic_save.status_code == 409, stale_semantic_save.text
    retained_visual_drafts = client.get(
        f"/api/v2/projects/{first_id}/authoring-drafts"
    ).json()
    assert any(
        draft["editorScope"] == "visual_intent"
        and draft["entityId"] == f"{shot['id']}:{asset['id']}"
        and draft["draftRevision"] == newer_visual_draft.json()["draftRevision"]
        for draft in retained_visual_drafts
    )
    direction_draft = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "image_direction", "entityId": f"{shot['id']}:original",
            "baseCanonicalRevision": storyboard["head"]["revision"], "expectedDraftRevision": 0,
            "payload": {"shotId": shot["id"], "targetId": "original", "contextId": "fixture-context", "presentationChange": "Keep the approved fixture legible."},
        },
    )
    assert direction_draft.status_code == 200, direction_draft.text
    newer_direction_draft = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "image_direction",
            "entityId": f"{shot['id']}:original",
            "baseCanonicalRevision": storyboard["head"]["revision"],
            "expectedDraftRevision": direction_draft.json()["draftRevision"],
            "payload": {
                "shotId": shot["id"],
                "targetId": "original",
                "contextId": "fixture-context",
                "presentationChange": "Keep the approved fixture legible.",
            },
        },
    )
    assert newer_direction_draft.status_code == 200, newer_direction_draft.text

    intent = client.post(
        f"/api/v2/projects/{first_id}/managed-assets/{asset['id']}/visual-intents",
        json={
            "shotId": shot["id"], "role": "shot_keyframe",
            "identityIntent": "Preserve the fixture identity.", "sourceRefs": ["offline fixture"],
            "consumedDraft": {"editorScope": "visual_intent", "entityId": f"{shot['id']}:{asset['id']}", "draftRevision": newer_visual_draft.json()["draftRevision"]},
        },
    ).json()
    selected = client.post(
        f"/api/v2/projects/{first_id}/reviewed-keyframes",
        json={
            "assetId": asset["id"], "shotId": shot["id"], "sceneId": shot["sceneId"], "expectedSelectionRevision": 0,
            "storyboardRevision": storyboard["head"]["revision"], "approvalId": approval["id"],
            "compatibilityNote": "Fixture keyframe matches the approved shot.",
            "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
        },
    )
    assert selected.status_code == 201, selected.text

    # Adaptation direction has a distinct target identity, so its receipt can
    # neither consume the original direction nor a candidate refinement.
    adaptation_profile_id = "minimax_h3_fp8_turbo4_portrait_576x1024_v1"
    adaptation_draft = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "image_direction",
            "entityId": f"{shot['id']}:keyframe_adaptation:{adaptation_profile_id}",
            "baseCanonicalRevision": storyboard["head"]["revision"],
            "expectedDraftRevision": 0,
            "payload": {
                "shotId": shot["id"],
                "targetId": f"keyframe_adaptation:{adaptation_profile_id}",
                "contextId": "fixture-adaptation",
                "presentationChange": "Recompose the reviewed fixture for the portrait frame.",
            },
        },
    )
    assert adaptation_draft.status_code == 200, adaptation_draft.text
    adaptation = client.post(
        f"/api/v2/projects/{first_id}/image-jobs",
        json={
            "approvalId": approval["id"],
            "shotId": shot["id"],
            "storyboardRevision": storyboard["head"]["revision"],
            "contractVersion": 3,
            "keyframeAdaptationProfileId": adaptation_profile_id,
            "presentationChange": "Recompose the reviewed fixture for the portrait frame.",
            "contextId": "fixture-adaptation",
            "consumedDraft": {
                "editorScope": "image_direction",
                "entityId": f"{shot['id']}:keyframe_adaptation:{adaptation_profile_id}",
                "draftRevision": adaptation_draft.json()["draftRevision"],
            },
        },
    )
    assert adaptation.status_code == 201, adaptation.text
    assert adaptation.json()["job"]["request"]["kind"] == "keyframe_adaptation"

    stale_job = client.post(
        f"/api/v2/projects/{first_id}/image-jobs",
        json={
            "approvalId": approval["id"],
            "shotId": shot["id"],
            "storyboardRevision": storyboard["head"]["revision"],
            "presentationChange": "Keep the approved fixture legible.",
            "contextId": "fixture-context",
            "consumedDraft": {
                "editorScope": "image_direction",
                "entityId": f"{shot['id']}:original",
                "draftRevision": direction_draft.json()["draftRevision"],
            },
        },
    )
    assert stale_job.status_code == 409, stale_job.text
    assert [job["id"] for job in client.get(f"/api/v2/projects/{first_id}/image-jobs").json()["jobs"]] == [
        adaptation.json()["job"]["id"],
    ]

    original = client.post(
        f"/api/v2/projects/{first_id}/image-jobs",
        json={
            "approvalId": approval["id"], "shotId": shot["id"], "storyboardRevision": storyboard["head"]["revision"],
            "presentationChange": "Keep the approved fixture legible.", "contextId": "fixture-context",
            "consumedDraft": {"editorScope": "image_direction", "entityId": f"{shot['id']}:original", "draftRevision": newer_direction_draft.json()["draftRevision"]},
        },
    )
    assert original.status_code == 201, original.text
    original_job = original.json()["job"]
    copied = client.post(f"/api/v2/projects/{first_id}/image-jobs/{original_job['id']}/copy")
    assert copied.status_code == 200, copied.text
    package_path = Path(copied.json()["packagePath"]).resolve()
    delivery_path = Path(copied.json()["deliveryPath"]).resolve()
    assert package_path.is_relative_to(first_home / "runs")
    assert delivery_path.is_relative_to(first_home / "runs")
    _complete_delivery(
        delivery_path, original_job, _png((90, 42, 12)), "secret-fixture",
        actual_prompt="The executor used Bearer sk-secret-must-not-enter-project.",
    )
    secret_delivery = client.post(f"/api/v2/projects/{first_id}/image-jobs/{original_job['id']}/refresh")
    assert secret_delivery.status_code == 422
    assert secret_delivery.json()["code"] == "delivery_manifest_secret"
    assert client.get(f"/api/v2/projects/{first_id}/image-jobs").json()["jobs"][0]["deliveries"] == []
    _complete_delivery(delivery_path, original_job, _png((90, 42, 12)), "original-fixture")
    ingested = client.post(f"/api/v2/projects/{first_id}/image-jobs/{original_job['id']}/refresh")
    assert ingested.status_code == 200, ingested.text
    candidate = ingested.json()["candidates"][0]["asset"]

    candidate_draft = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "visual_intent", "entityId": f"{shot['id']}:{candidate['id']}",
            "baseCanonicalRevision": storyboard["head"]["revision"], "expectedDraftRevision": 0,
            "payload": {"assetId": candidate["id"], "shotId": shot["id"], "role": "shot_keyframe", "identityIntent": "Candidate fixture identity.", "sourceRefs": ["offline fixture candidate"]},
        },
    )
    assert candidate_draft.status_code == 200, candidate_draft.text
    candidate_intent = client.post(
        f"/api/v2/projects/{first_id}/managed-assets/{candidate['id']}/visual-intents",
        json={
            "shotId": shot["id"], "role": "shot_keyframe", "identityIntent": "Candidate fixture identity.", "sourceRefs": ["offline fixture candidate"],
            "consumedDraft": {"editorScope": "visual_intent", "entityId": f"{shot['id']}:{candidate['id']}", "draftRevision": candidate_draft.json()["draftRevision"]},
        },
    ).json()
    replacement = client.post(
        f"/api/v2/projects/{first_id}/reviewed-keyframes",
        json={
            "assetId": candidate["id"], "shotId": shot["id"], "sceneId": shot["sceneId"], "expectedSelectionRevision": 1,
            "storyboardRevision": storyboard["head"]["revision"], "approvalId": approval["id"],
            "compatibilityNote": "Candidate now reviewed for fixture refinement.",
            "visualIntentId": candidate_intent["id"], "visualIntentRevision": candidate_intent["revision"],
        },
    )
    assert replacement.status_code == 201, replacement.text
    refinement_draft = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "image_direction", "entityId": f"{shot['id']}:refinement:{candidate['id']}",
            "baseCanonicalRevision": storyboard["head"]["revision"], "expectedDraftRevision": 0,
            "payload": {"shotId": shot["id"], "targetId": f"refinement:{candidate['id']}", "contextId": "fixture-refinement", "presentationChange": "Refine the selected fixture candidate."},
        },
    )
    assert refinement_draft.status_code == 200, refinement_draft.text
    refinement = client.post(
        f"/api/v2/projects/{first_id}/image-jobs",
        json={
            "approvalId": approval["id"], "shotId": shot["id"], "storyboardRevision": storyboard["head"]["revision"], "parentCandidateAssetId": candidate["id"],
            "presentationChange": "Refine the selected fixture candidate.", "contextId": "fixture-refinement",
            "consumedDraft": {"editorScope": "image_direction", "entityId": f"{shot['id']}:refinement:{candidate['id']}", "draftRevision": refinement_draft.json()["draftRevision"]},
        },
    )
    assert refinement.status_code == 201, refinement.text
    refinement_job = refinement.json()["job"]
    copied_refinement = client.post(f"/api/v2/projects/{first_id}/image-jobs/{refinement_job['id']}/copy")
    assert copied_refinement.status_code == 200, copied_refinement.text

    # A newer role-scoped intent replaces the frozen reference currentness;
    # the already copied delivery is retained as inapplicable, never selected.
    replacement_draft = client.put(
        f"/api/v2/projects/{first_id}/authoring-drafts",
        json={
            "editorScope": "visual_intent", "entityId": f"{shot['id']}:{candidate['id']}",
            "baseCanonicalRevision": storyboard["head"]["revision"], "expectedDraftRevision": 0,
            "payload": {"assetId": candidate["id"], "shotId": shot["id"], "role": "shot_keyframe", "identityIntent": "Replacement fixture identity.", "sourceRefs": ["replacement fixture"]},
        },
    )
    assert replacement_draft.status_code == 200, replacement_draft.text
    replacement_intent = client.post(
        f"/api/v2/projects/{first_id}/managed-assets/{candidate['id']}/visual-intents",
        json={
            "shotId": shot["id"], "role": "shot_keyframe", "identityIntent": "Replacement fixture identity.", "sourceRefs": ["replacement fixture"],
            "consumedDraft": {"editorScope": "visual_intent", "entityId": f"{shot['id']}:{candidate['id']}", "draftRevision": replacement_draft.json()["draftRevision"]},
        },
    )
    assert replacement_intent.status_code == 201, replacement_intent.text
    _complete_delivery(Path(copied_refinement.json()["deliveryPath"]), refinement_job, _png((50, 70, 20)), "late-refinement")
    stale = client.post(f"/api/v2/projects/{first_id}/image-jobs/{refinement_job['id']}/refresh")
    assert stale.status_code == 200, stale.text
    assert stale.json()["state"] == "inapplicable"
    foreign = client.post(f"/api/v2/projects/{second_id}/image-jobs/{refinement_job['id']}/refresh")
    assert foreign.status_code == 404

    reopened = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    reopened_client = TestClient(create_project_folder_authoring_app(reopened))
    assert reopened_client.get(f"/api/v2/projects/{first_id}/managed-assets/{candidate['id']}/original").content == _png((90, 42, 12))
    jobs = reopened_client.get(f"/api/v2/projects/{first_id}/image-jobs").json()["jobs"]
    assert {job["id"] for job in jobs} == {
        adaptation.json()["job"]["id"],
        original_job["id"],
        refinement_job["id"],
    }
    store = reopened.projects.open(first_id)
    try:
        stored = store.repository.get_managed_asset_storage(first_id, candidate["id"])
        assert stored["originalUri"].startswith("assets/")
        assert not stored["originalUri"].startswith("file:")
    finally:
        store.close()
