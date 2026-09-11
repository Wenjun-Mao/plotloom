from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from plotloom.api import create_app
from plotloom.artifacts import MemoryArtifactStore
from plotloom.domain import StageName
from plotloom.managed_media import ManagedMediaLimits, inspect_import_image, publish_import
from plotloom.persistence import SQLiteRepository

from .test_managed_still_media import _approval, _complete_project_with_three_shots, _intent


def _png(color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (24, 16), color).save(output, format="PNG")
    return output.getvalue()


def _shot_id(repository: SQLiteRepository, project_id: str, scene_id: str) -> str:
    with repository._read() as session:  # noqa: SLF001 - canonical fixture inspection
        board = repository._load_stage_payload(session, project_id, StageName.STORYBOARD)  # noqa: SLF001
    return next(shot.id for shot in board.shots if shot.scene_id == scene_id)


def _prepare(client: TestClient, project_id: str, approval: dict, shot_id: str, revision: int, **extra: str) -> dict:
    response = client.post(
        f"/api/v2/projects/{project_id}/image-jobs",
        json={"approvalId": approval["id"], "shotId": shot_id, "storyboardRevision": revision, **extra},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _complete_delivery(delivery: Path, job: dict, *, delivery_id: str, content: bytes, role: str = "original") -> None:
    outputs = delivery / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    filename = "candidate.png"
    (outputs / filename).write_bytes(content)
    manifest = {
        "schemaVersion": 1,
        "jobId": job["id"],
        "requestHash": job["requestHash"],
        "deliveryId": delivery_id,
        "actualPrompt": "A faithful visual rendering of the frozen Plotloom proposal.",
        "outputs": [{"filename": filename, "sha256": sha256(content).hexdigest(), "role": role}],
        "toolEvidence": {"tool": "codex_imagegen", "taskId": "test-specialist", "available": True},
        "limitations": ["fixture delivery"],
    }
    (delivery / "completion.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_image_job_requires_a_configured_same_host_exchange_before_admission(repository, brief) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore())
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        unavailable = client.post(
            f"/api/v2/projects/{project.id}/image-jobs",
            json={
                "approvalId": approval["id"], "shotId": _shot_id(repository, project.id, scene_id),
                "storyboardRevision": board.revision,
            },
        )
        assert unavailable.status_code == 409 and unavailable.json()["code"] == "image_exchange_not_configured"
        assert client.get(f"/api/v2/projects/{project.id}/image-jobs").json() == {
            "configured": False, "jobs": [],
        }


def test_manual_image_job_prepare_copy_refresh_select_and_refine(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    store = MemoryArtifactStore()
    app = create_app(repository, artifact_store=store, image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        shot_id = _shot_id(repository, project.id, scene_id)
        prepared = _prepare(client, project.id, approval, shot_id, board.revision)
        original = prepared["job"]
        assert original["request"]["frozenSnapshot"]["references"] == []

        copied = client.post(f"/api/v2/projects/{project.id}/image-jobs/{original['id']}/copy")
        assert copied.status_code == 200, copied.text
        package = Path(copied.json()["packagePath"])
        delivery = Path(copied.json()["deliveryPath"])
        request = json.loads((package / "request.json").read_text())
        assert request["jobId"] == original["id"]
        serialized_package = json.dumps(request).lower()
        assert not any(forbidden in serialized_package for forbidden in (
            "credentials", "api_key", "authorization", "bearer", "secret",
        ))
        repeated_copy = client.post(f"/api/v2/projects/{project.id}/image-jobs/{original['id']}/copy")
        assert repeated_copy.status_code == 200
        request["visualProposal"]["title"] = "tampered package fact"
        (package / "request.json").write_text(json.dumps(request), encoding="utf-8")
        tampered_package = client.post(f"/api/v2/projects/{project.id}/image-jobs/{original['id']}/copy")
        assert tampered_package.status_code == 409 and tampered_package.json()["code"] == "package_conflict"
        # Restore the exact trusted transport envelope before completing the
        # independently tested specialist delivery.
        request["visualProposal"]["title"] = original["request"]["visualProposal"]["title"]
        (package / "request.json").write_text(json.dumps(request), encoding="utf-8")

        _complete_delivery(delivery, original, delivery_id="original-001", content=_png((20, 40, 90)))
        # A package can be edited after a successful Copy too. Refresh must
        # revalidate it before it ever reads or publishes the delivery.
        request["visualProposal"]["title"] = "tampered after Copy"
        (package / "request.json").write_text(json.dumps(request), encoding="utf-8")
        post_copy_tamper = client.post(f"/api/v2/projects/{project.id}/image-jobs/{original['id']}/refresh")
        assert post_copy_tamper.status_code == 409 and post_copy_tamper.json()["code"] == "package_conflict"
        request["visualProposal"]["title"] = original["request"]["visualProposal"]["title"]
        (package / "request.json").write_text(json.dumps(request), encoding="utf-8")
        refreshed = client.post(f"/api/v2/projects/{project.id}/image-jobs/{original['id']}/refresh")
        assert refreshed.status_code == 200, refreshed.text
        candidate = refreshed.json()["candidates"][0]
        assert refreshed.json()["state"] == "accepted"
        again = client.post(f"/api/v2/projects/{project.id}/image-jobs/{original['id']}/refresh")
        assert again.status_code == 200 and again.json()["idempotent"] is True
        assert again.json()["candidates"][0]["assetId"] == candidate["assetId"]

        intent = _intent(client, project.id, candidate["assetId"])
        selection = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes",
            json={
                "assetId": candidate["assetId"], "shotId": shot_id, "sceneId": scene_id,
                "expectedSelectionRevision": 0, "storyboardRevision": board.revision,
                "approvalId": approval["id"], "compatibilityNote": "explicit P1 candidate review",
                "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
            },
        )
        assert selection.status_code == 201, selection.text
        preview = client.post(
            f"/api/v2/projects/{project.id}/still-previews",
            json={
                "sceneId": scene_id, "shotIds": [shot_id], "expectedSelectionRevision": 1,
                "storyboardRevision": board.revision, "approvalId": approval["id"],
            },
        )
        assert preview.status_code == 201 and preview.json()["state"] == "current"

        refinement = _prepare(
            client, project.id, approval, shot_id, board.revision,
            parentCandidateAssetId=candidate["assetId"],
        )["job"]
        copied_refinement = client.post(f"/api/v2/projects/{project.id}/image-jobs/{refinement['id']}/copy")
        assert copied_refinement.status_code == 200, copied_refinement.text
        refinement_request = json.loads((Path(copied_refinement.json()["packagePath"]) / "request.json").read_text())
        assert refinement_request["references"][0]["role"] == "parent_output"
        reference_path = Path(copied_refinement.json()["packagePath"]) / refinement_request["references"][0]["filename"]
        original_reference = reference_path.read_bytes()
        reference_path.write_bytes(b"tampered reference")
        tampered_reference = client.post(f"/api/v2/projects/{project.id}/image-jobs/{refinement['id']}/copy")
        assert tampered_reference.status_code == 409 and tampered_reference.json()["code"] == "package_conflict"
        reference_path.write_bytes(original_reference)
        source = repository.get_managed_asset_storage(project.id, candidate["assetId"])
        source_bytes = store.get(source["originalUri"])
        store._items.pop(source["originalUri"].removeprefix("memory://"))  # noqa: SLF001 - force a missing frozen source
        missing_reference = client.post(f"/api/v2/projects/{project.id}/image-jobs/{refinement['id']}/copy")
        assert missing_reference.status_code == 409 and missing_reference.json()["code"] == "invalid_transition"
        store._items[source["originalUri"].removeprefix("memory://")] = source_bytes  # noqa: SLF001 - restore fixture blob
        _complete_delivery(
            Path(copied_refinement.json()["deliveryPath"]), refinement,
            delivery_id="refinement-001", content=_png((70, 50, 20)), role="refinement",
        )
        refinement_return = client.post(f"/api/v2/projects/{project.id}/image-jobs/{refinement['id']}/refresh")
        assert refinement_return.status_code == 200
        assert refinement_return.json()["candidates"][0]["role"] == "refinement"


def test_image_job_rejects_partial_tampered_and_conflicting_delivery(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        job = _prepare(client, project.id, approval, _shot_id(repository, project.id, scene_id), board.revision)["job"]
        copied = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy").json()
        delivery = Path(copied["deliveryPath"])
        outputs = delivery / "outputs"
        outputs.mkdir(parents=True)
        content = _png((10, 10, 10))
        _complete_delivery(delivery, job, delivery_id="no-tool-001", content=content)
        no_tool_manifest = json.loads((delivery / "completion.json").read_text(encoding="utf-8"))
        no_tool_manifest["toolEvidence"]["available"] = False
        (delivery / "completion.json").write_text(json.dumps(no_tool_manifest), encoding="utf-8")
        no_tool = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert no_tool.status_code == 422 and no_tool.json()["code"] == "delivery_manifest_invalid"
        (outputs / "candidate.png").write_bytes(content)
        # A completion marker that claims a second output is a partial delivery,
        # not a usable one-output candidate.
        (delivery / "completion.json").write_text(json.dumps({
            "schemaVersion": 1, "jobId": job["id"], "requestHash": job["requestHash"],
            "deliveryId": "partial-001", "actualPrompt": "fixture",
            "outputs": [
                {"filename": "candidate.png", "sha256": sha256(content).hexdigest(), "role": "original"},
                {"filename": "missing.png", "sha256": "0" * 64, "role": "original"},
            ], "toolEvidence": {"tool": "codex_imagegen", "taskId": "test-specialist", "available": True},
        }), encoding="utf-8")
        partial = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert partial.status_code == 422 and partial.json()["code"] == "delivery_partial"
        assert client.get(f"/api/v2/projects/{project.id}/image-jobs").json()["jobs"][0]["deliveries"][0]["state"] == "rejected"

        (delivery / "outputs" / "missing.png").write_bytes(_png((4, 5, 6)))
        # Hashes are checked before any candidate publication.
        tampered = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert tampered.status_code == 422 and tampered.json()["code"] == "delivery_hash_mismatch"

        (delivery / "outputs" / "missing.png").unlink()
        _complete_delivery(delivery, job, delivery_id="complete-001", content=content)
        complete = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert complete.status_code == 200
        _complete_delivery(delivery, job, delivery_id="complete-001", content=_png((99, 20, 20)))
        conflict = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert conflict.status_code == 409 and conflict.json()["code"] == "delivery_conflict"
        _complete_delivery(delivery, job, delivery_id="second-final-001", content=content)
        second_final = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert second_final.status_code == 409 and second_final.json()["code"] == "delivery_finalized"


def test_cancelled_or_revoked_job_retains_late_delivery_without_candidate(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    store = MemoryArtifactStore()
    app = create_app(repository, artifact_store=store, image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        job = _prepare(client, project.id, approval, _shot_id(repository, project.id, scene_id), board.revision)["job"]
        copied = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy").json()
        cancelled = client.post(
            f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/cancel", json={"reason": "operator stopped pilot"}
        )
        assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled"
        _complete_delivery(Path(copied["deliveryPath"]), job, delivery_id="late-001", content=_png((1, 2, 3)))
        late = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert late.status_code == 200
        assert late.json() == {
            "deliveryId": "late-001", "state": "inapplicable", "diagnosticCode": "late_or_stale_delivery",
            "idempotent": False, "candidates": [],
        }
        assert store._items == {}  # noqa: SLF001 - no blob may precede late-delivery admission


def test_image_job_rejects_forged_authority_cross_project_and_browser_paths(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    other_project, _ = _complete_project_with_three_shots(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        _other_review, other_approval = _approval(client, other_project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        shot_id = _shot_id(repository, project.id, scene_id)

        # The typed browser contract accepts canonical IDs only; it cannot turn
        # a prepared job into a path-, prompt-, or URL-authorized operation.
        attempted_path_authority = client.post(
            f"/api/v2/projects/{project.id}/image-jobs",
            json={
                "approvalId": approval["id"], "shotId": shot_id, "storyboardRevision": board.revision,
                "deliveryPath": "/arbitrary/operator/path", "prompt": "replace frozen facts",
            },
        )
        assert attempted_path_authority.status_code == 422

        forged = client.post(
            f"/api/v2/projects/{project.id}/image-jobs",
            json={"approvalId": other_approval["id"], "shotId": shot_id, "storyboardRevision": board.revision},
        )
        assert forged.status_code == 409 and forged.json()["code"] == "invalid_transition"

        job = _prepare(client, project.id, approval, shot_id, board.revision)["job"]
        copied = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy").json()
        # A job ID scoped to another project never resolves the delivery context.
        cross_project = client.post(f"/api/v2/projects/{other_project.id}/image-jobs/{job['id']}/refresh")
        assert cross_project.status_code == 404

        delivery = Path(copied["deliveryPath"])
        outputs = delivery / "outputs"
        outputs.mkdir(parents=True)
        target = tmp_path / "outside.png"
        target.write_bytes(_png((1, 2, 3)))
        (outputs / "candidate.png").symlink_to(target)
        (delivery / "completion.json").write_text(json.dumps({
            "schemaVersion": 1, "jobId": job["id"], "requestHash": job["requestHash"],
            "deliveryId": "symlink-001", "actualPrompt": "fixture",
            "outputs": [{"filename": "candidate.png", "sha256": sha256(target.read_bytes()).hexdigest(), "role": "original"}],
            "toolEvidence": {"tool": "codex_imagegen", "taskId": "test-specialist", "available": True},
        }), encoding="utf-8")
        symlink = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert symlink.status_code == 422 and symlink.json()["code"] == "delivery_symlink"


def test_image_job_rejects_malformed_or_oversized_and_revoked_late_delivery(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        job = _prepare(client, project.id, approval, _shot_id(repository, project.id, scene_id), board.revision)["job"]
        delivery = Path(client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy").json()["deliveryPath"])

        malformed = b"not an image"
        _complete_delivery(delivery, job, delivery_id="malformed-001", content=malformed)
        invalid = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert invalid.status_code == 422 and invalid.json()["code"] == "invalid_media"
        rejected_codes = {
            item["diagnosticCode"]
            for item in client.get(f"/api/v2/projects/{project.id}/image-jobs").json()["jobs"][0]["deliveries"]
        }
        assert "invalid_media" in rejected_codes

        too_large = b"x" * (ManagedMediaLimits().max_import_bytes + 1)
        _complete_delivery(delivery, job, delivery_id="oversized-001", content=too_large)
        oversized = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert oversized.status_code == 422 and oversized.json()["code"] == "delivery_file_too_large"
        rejected_codes = {
            item["diagnosticCode"]
            for item in client.get(f"/api/v2/projects/{project.id}/image-jobs").json()["jobs"][0]["deliveries"]
        }
        assert "delivery_file_too_large" in rejected_codes

        revoked = client.post(
            f"/api/v2/projects/{project.id}/storyboard-approval",
            json={
                "expectedRevision": review["head"]["revision"], "contentHash": review["head"]["contentHash"],
                "decision": "revoke", "reviewer": "development operator",
                "gateSetVersion": review["gateEvaluation"]["gateSetVersion"], "note": "invalidate copied pilot package",
            },
        )
        assert revoked.status_code == 201
        _complete_delivery(delivery, job, delivery_id="revoked-late-001", content=_png((8, 9, 10)))
        late = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert late.status_code == 200 and late.json()["state"] == "inapplicable"


def test_image_job_delivery_reconciliation_is_concurrently_idempotent(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    store = MemoryArtifactStore()
    app = create_app(repository, artifact_store=store, image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        job = _prepare(client, project.id, approval, _shot_id(repository, project.id, scene_id), board.revision)["job"]
        client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy")
        content = _png((12, 34, 56))
        observed = inspect_import_image(content, ManagedMediaLimits())
        manifest = {
            "schemaVersion": 1, "jobId": job["id"], "requestHash": job["requestHash"],
            "deliveryId": "concurrent-001", "actualPrompt": "fixture",
            "outputs": [{"filename": "candidate.png", "sha256": sha256(content).hexdigest(), "role": "original"}],
            "toolEvidence": {"tool": "codex_imagegen", "taskId": "test-specialist", "available": True},
        }
        output = {
            "filename": "candidate.png", "role": "original", "originalHash": observed.content_hash,
            "displayHash": observed.display_hash,
            "mimeType": observed.mime_type, "byteSize": observed.byte_size,
            "width": observed.width, "height": observed.height, "content": content, "observed": observed,
        }
        publish_calls: list[str] = []

    # Exercise the repository's transaction boundary from two independent
    # callers. Exactly one immutable candidate may be admitted for a delivery ID.
    def reconcile() -> dict:
        return repository.record_image_job_delivery(
            project.id, job["id"], delivery_id="concurrent-001", manifest=manifest,
            manifest_hash=sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            outputs=[output],
            publish=lambda value: (
                publish_calls.append(value["originalHash"])
                or publish_import(store, value["content"], value["observed"])
            ),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = (future.result() for future in (pool.submit(reconcile), pool.submit(reconcile)))
    assert {first["idempotent"], second["idempotent"]} == {False, True}
    jobs = repository.list_image_jobs(project.id)
    assert len(jobs[0]["deliveries"]) == 1
    assert len(jobs[0]["deliveries"][0]["candidates"]) == 1
    assert publish_calls == [observed.content_hash]


def test_archived_project_cannot_refresh_or_publish_an_image_delivery(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    store = MemoryArtifactStore()
    app = create_app(repository, artifact_store=store, image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        job = _prepare(client, project.id, approval, _shot_id(repository, project.id, scene_id), board.revision)["job"]
        delivery = Path(client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy").json()["deliveryPath"])
        _complete_delivery(delivery, job, delivery_id="archived-001", content=_png((7, 8, 9)))
        project_view = client.get(f"/api/v2/projects/{project.id}").json()
        archived = client.post(
            f"/api/v2/projects/{project.id}/archive",
            json={"expectedLifecycleRevision": project_view["lifecycleRevision"]},
        )
        assert archived.status_code == 200
        refresh = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert refresh.status_code == 409 and refresh.json()["code"] == "invalid_transition"
        assert store._items == {}  # noqa: SLF001 - archive blocks all P1 publication
