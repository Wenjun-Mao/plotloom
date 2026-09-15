"""Project-owned rejection and reconciliation contracts for image deliveries."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage

from tests.project_storage_fixtures import FixtureResolver, fixture_profile


def _png(
    color: tuple[int, int, int], *, width: int = 24, height: int = 16
) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), color).save(output, format="PNG")
    return output.getvalue()


def _delivery_manifest(job: dict, content: bytes, delivery_id: str) -> dict:
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


def _write_delivery(path: Path, job: dict, content: bytes, delivery_id: str) -> None:
    outputs = path / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "candidate.png").write_bytes(content)
    (path / "completion.json").write_text(
        json.dumps(_delivery_manifest(job, content, delivery_id)), encoding="utf-8"
    )


def _ready_exported_job(tmp_path: Path) -> tuple[TestClient, str, dict, Path]:
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
            "reviewer": "offline delivery fixture",
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


def test_image_delivery_rejects_partial_and_hash_tamper_before_candidate_publication(
    tmp_path: Path,
) -> None:
    client, project_id, job, delivery = _ready_exported_job(tmp_path)
    content = _png((10, 10, 10))
    try:
        _write_delivery(delivery, job, content, "partial-001")
        manifest = _delivery_manifest(job, content, "partial-001")
        manifest["outputs"].append(
            {"filename": "missing.png", "sha256": "0" * 64, "role": "original"}
        )
        (delivery / "completion.json").write_text(json.dumps(manifest), encoding="utf-8")
        partial = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
        assert partial.status_code == 422
        assert partial.json()["code"] == "delivery_partial"

        (delivery / "outputs" / "missing.png").write_bytes(_png((4, 5, 6)))
        tampered = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
        assert tampered.status_code == 422
        assert tampered.json()["code"] == "delivery_hash_mismatch"
        listed = client.get(f"/api/v2/projects/{project_id}/image-jobs").json()["jobs"]
        assert listed[0]["deliveries"][0]["state"] == "rejected"
        assert listed[0]["deliveries"][1]["state"] == "rejected"
        assert all(not item["candidates"] for item in listed[0]["deliveries"])
    finally:
        client.close()


def test_copied_image_package_rejects_tampered_frozen_snapshot_before_admission(
    tmp_path: Path,
) -> None:
    client, project_id, job, _delivery = _ready_exported_job(tmp_path)
    try:
        copied = client.post(
            f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/copy"
        )
        assert copied.status_code == 200, copied.text
        request_path = Path(copied.json()["packagePath"]) / "request.json"
        package_request = json.loads(request_path.read_text(encoding="utf-8"))
        assert package_request["requestHash"] == job["requestHash"]
        assert package_request["frozenSnapshot"] == job["request"]["frozenSnapshot"]
        assert package_request["references"] == []

        package_request["frozenSnapshot"]["shot"]["action"] = "tampered browser direction"
        request_path.write_text(json.dumps(package_request), encoding="utf-8")
        rejected = client.post(
            f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh"
        )
        assert rejected.status_code == 409
        assert rejected.json()["code"] == "package_conflict"
        listed = client.get(f"/api/v2/projects/{project_id}/image-jobs").json()["jobs"]
        assert listed[0]["deliveries"][0]["state"] == "rejected"
        assert listed[0]["deliveries"][0]["candidates"] == []
    finally:
        client.close()


def test_image_delivery_rejects_malformed_bytes_before_candidate_publication(
    tmp_path: Path,
) -> None:
    client, project_id, job, delivery = _ready_exported_job(tmp_path)
    try:
        _write_delivery(delivery, job, b"not an image", "malformed-001")
        malformed = client.post(
            f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh"
        )
        assert malformed.status_code == 422
        assert malformed.json()["code"] == "invalid_media"
        jobs = client.get(f"/api/v2/projects/{project_id}/image-jobs").json()["jobs"]
        assert jobs[0]["deliveries"][0]["diagnosticCode"] == "invalid_media"
        assert jobs[0]["deliveries"][0]["candidates"] == []
    finally:
        client.close()


def test_image_delivery_rejects_conflicting_or_second_final_delivery(tmp_path: Path) -> None:
    client, project_id, job, delivery = _ready_exported_job(tmp_path)
    try:
        _write_delivery(delivery, job, _png((20, 30, 40)), "complete-001")
        accepted = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["state"] == "accepted"

        _write_delivery(delivery, job, _png((99, 20, 20)), "complete-001")
        conflict = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "delivery_conflict"

        _write_delivery(delivery, job, _png((20, 30, 40)), "second-final-001")
        second_final = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
        assert second_final.status_code == 409
        assert second_final.json()["code"] == "delivery_finalized"
    finally:
        client.close()


def test_cancelled_image_job_records_late_delivery_without_publishing_a_candidate(
    tmp_path: Path,
) -> None:
    client, project_id, job, delivery = _ready_exported_job(tmp_path)
    try:
        cancelled = client.post(
            f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/cancel",
            json={"reason": "operator stopped the fixture"},
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["state"] == "cancelled"
        _write_delivery(delivery, job, _png((1, 2, 3)), "late-001")
        late = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
        assert late.status_code == 200, late.text
        assert late.json() == {
            "deliveryId": "late-001",
            "state": "inapplicable",
            "diagnosticCode": "late_or_stale_delivery",
            "idempotent": False,
            "candidates": [],
        }
        stored = client.get(f"/api/v2/projects/{project_id}/managed-assets").json()["assets"]
        assert stored == []
    finally:
        client.close()


def test_image_delivery_refresh_is_concurrently_idempotent_at_the_project_owner(
    tmp_path: Path,
) -> None:
    client, project_id, job, delivery = _ready_exported_job(tmp_path)
    _write_delivery(delivery, job, _png((12, 34, 56)), "concurrent-001")
    app = client.app
    client.close()

    def refresh() -> dict:
        with TestClient(app) as contender:
            response = contender.post(
                f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh"
            )
            assert response.status_code == 200, response.text
            return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = (future.result() for future in (pool.submit(refresh), pool.submit(refresh)))
    assert {first["idempotent"], second["idempotent"]} == {False, True}
    with TestClient(app) as inspector:
        stored = inspector.get(f"/api/v2/projects/{project_id}/image-jobs").json()["jobs"]
    assert len(stored[0]["deliveries"]) == 1
    assert len(stored[0]["deliveries"][0]["candidates"]) == 1


def test_image_delivery_rejects_cross_project_and_symlinked_browser_output_paths(
    tmp_path: Path,
) -> None:
    client, project_id, job, delivery = _ready_exported_job(tmp_path)
    try:
        storage = ProjectFolderStorage(
            outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
        )
        other = storage.projects.create(
            FIXED_CHINESE_BRIEF.model_copy(update={"title": "Other project"})
        )
        other_id = other.project().id
        other.close()
        cross_project = client.post(
            f"/api/v2/projects/{other_id}/image-jobs/{job['id']}/refresh"
        )
        assert cross_project.status_code == 404

        output_dir = delivery / "outputs"
        output_dir.mkdir(parents=True)
        outside = tmp_path / "outside.png"
        outside.write_bytes(_png((1, 2, 3)))
        (output_dir / "candidate.png").symlink_to(outside)
        (delivery / "completion.json").write_text(
            json.dumps(_delivery_manifest(job, outside.read_bytes(), "symlink-001")),
            encoding="utf-8",
        )
        symlink = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
        assert symlink.status_code == 422
        assert symlink.json()["code"] == "delivery_symlink"
    finally:
        client.close()


def test_keyframe_adaptation_enforces_frozen_geometry_without_reselecting_source(
    tmp_path: Path,
) -> None:
    client, project_id, original_job, _delivery = _ready_exported_job(tmp_path)
    try:
        storyboard = client.get(f"/api/v2/projects/{project_id}/stages").json()["stages"][-1]
        shot = storyboard["payload"]["shots"][0]
        approval_id = original_job["request"]["frozenSnapshot"]["approvalId"]
        source = client.post(
            f"/api/v2/projects/{project_id}/managed-assets",
            files={"image": ("wide.png", _png((30, 70, 120), width=640, height=360), "image/png")},
            data={"origin": "wide source fixture", "rights": "unknown", "declared_additions_json": "[]"},
        )
        assert source.status_code == 201, source.text
        intent_draft = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={
                "editorScope": "visual_intent",
                "entityId": f"{shot['id']}:{source.json()['id']}",
                "baseCanonicalRevision": storyboard["head"]["revision"],
                "expectedDraftRevision": 0,
                "payload": {"assetId": source.json()["id"], "shotId": shot["id"], "role": "shot_keyframe", "identityIntent": "Keep the source identity.", "sourceRefs": ["fixture"]},
            },
        )
        assert intent_draft.status_code == 200, intent_draft.text
        intent = client.post(
            f"/api/v2/projects/{project_id}/managed-assets/{source.json()['id']}/visual-intents",
            json={"shotId": shot["id"], "role": "shot_keyframe", "identityIntent": "Keep the source identity.", "sourceRefs": ["fixture"], "consumedDraft": {"editorScope": "visual_intent", "entityId": f"{shot['id']}:{source.json()['id']}", "draftRevision": intent_draft.json()["draftRevision"]}},
        )
        assert intent.status_code == 201, intent.text
        selected = client.post(
            f"/api/v2/projects/{project_id}/reviewed-keyframes",
            json={"assetId": source.json()["id"], "shotId": shot["id"], "sceneId": shot["sceneId"], "expectedSelectionRevision": 0, "storyboardRevision": storyboard["head"]["revision"], "approvalId": approval_id, "compatibilityNote": "Creator reviewed the landscape source.", "visualIntentId": intent.json()["id"], "visualIntentRevision": intent.json()["revision"]},
        )
        assert selected.status_code == 201, selected.text
        profile_id = "minimax_h3_fp8_turbo4_portrait_576x1024_v1"
        direction = client.put(
            f"/api/v2/projects/{project_id}/authoring-drafts",
            json={"editorScope": "image_direction", "entityId": f"{shot['id']}:keyframe_adaptation:{profile_id}", "baseCanonicalRevision": storyboard["head"]["revision"], "expectedDraftRevision": 0, "payload": {"shotId": shot["id"], "targetId": f"keyframe_adaptation:{profile_id}", "contextId": "geometry-fixture", "presentationChange": "Recompose for the frozen portrait frame."}},
        )
        assert direction.status_code == 200, direction.text
        prepared = client.post(
            f"/api/v2/projects/{project_id}/image-jobs",
            json={"approvalId": approval_id, "shotId": shot["id"], "storyboardRevision": storyboard["head"]["revision"], "contractVersion": 3, "keyframeAdaptationProfileId": profile_id, "presentationChange": "Recompose for the frozen portrait frame.", "contextId": "geometry-fixture", "consumedDraft": {"editorScope": "image_direction", "entityId": f"{shot['id']}:keyframe_adaptation:{profile_id}", "draftRevision": direction.json()["draftRevision"]}},
        )
        assert prepared.status_code == 201, prepared.text
        job = prepared.json()["job"]
        copied = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/copy")
        assert copied.status_code == 200, copied.text
        delivery = Path(copied.json()["deliveryPath"])
        delivery.mkdir()

        provenance = {"codeRevision": "a" * 40, "skillVersion": "plotloom-image-specialist.v3", "skillHash": "b" * 64}
        (delivery / "executor-pin.json").write_text(json.dumps({"jobId": job["id"], "requestHash": job["requestHash"], "executionContract": "codex_specialist.v2", **provenance}), encoding="utf-8")
        wrong = _png((40, 90, 120), width=576, height=1023)
        (delivery / "outputs").mkdir()
        (delivery / "outputs" / "adapted.png").write_bytes(wrong)
        manifest = {"schemaVersion": 2, "jobId": job["id"], "requestHash": job["requestHash"], "deliveryId": "wrong-geometry", "actualPrompt": "Adapt the frozen reviewed keyframe.", "outputs": [{"filename": "adapted.png", "sha256": sha256(wrong).hexdigest(), "role": "keyframe_adaptation"}], "toolEvidence": {"tool": "codex_imagegen", "taskId": "geometry-fixture", "available": True}, "executorProvenance": provenance}
        (delivery / "completion.json").write_text(json.dumps(manifest), encoding="utf-8")
        rejected = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
        assert rejected.status_code == 422, rejected.text
        assert rejected.json()["code"] == "delivery_geometry_mismatch"
        workbench = client.get(f"/api/v2/projects/{project_id}/visual-workbench").json()
        assert workbench["reviewedKeyframes"][0]["assetId"] == source.json()["id"]
        assert workbench["selectionRevision"] == selected.json()["selectionRevision"]
    finally:
        client.close()
