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
from plotloom.canonical_schema import CharacterV2, DialogueCue, LocationV2, PropV2, RequiredEntityState
from plotloom.domain import StageName
from plotloom.image_job_contracts import ImageJobError
from plotloom.image_job_exchange import ImageJobExchange
from plotloom.managed_media import ManagedMediaLimits, inspect_import_image, publish_import
from plotloom.persistence import SQLiteRepository

from .conftest import all_stage_payloads
from .test_managed_still_media import _approval, _complete_project_with_three_shots, _intent


def _png(
    color: tuple[int, int, int], *, width: int = 24, height: int = 16
) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), color).save(output, format="PNG")
    return output.getvalue()


def _shot_id(repository: SQLiteRepository, project_id: str, scene_id: str) -> str:
    with repository._read() as session:  # noqa: SLF001 - canonical fixture inspection
        board = repository._load_stage_payload(session, project_id, StageName.STORYBOARD)  # noqa: SLF001
    return next(shot.id for shot in board.shots if shot.scene_id == scene_id)


def _prepare(client: TestClient, project_id: str, approval: dict, shot_id: str, revision: int, **extra: str) -> dict:
    response = client.post(
        f"/api/v2/projects/{project_id}/image-jobs",
        json={
            "approvalId": approval["id"], "shotId": shot_id, "storyboardRevision": revision,
            "presentationChange": "Keep the reviewed presentation readable and faithful to this approved shot.",
            **extra,
        },
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


def _complete_identity_delivery(delivery: Path, job: dict, *, delivery_id: str, content: bytes) -> None:
    """A retained raster fixture for P1.5 validation; never a visual-pilot claim."""

    outputs = delivery / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    filename = "identity-candidate.png"
    (outputs / filename).write_bytes(content)
    hashes = [
        item["originalHash"]
        for item in job["request"]["frozenSnapshot"]["references"]
        if item["role"] == "character_identity"
    ]
    manifest = {
        "schemaVersion": 2,
        "jobId": job["id"],
        "requestHash": job["requestHash"],
        "deliveryId": delivery_id,
        "actualPrompt": "A cinematic rendering that preserves the viewed approved character identity.",
        "outputs": [{"filename": filename, "sha256": sha256(content).hexdigest(), "role": "original"}],
        "toolEvidence": {"tool": "codex_imagegen", "taskId": "p15-fixture-specialist", "available": True},
        "referenceUse": {"viewedReferenceHashes": hashes, "identityNotes": "Fixture attestation only; creator review remains required."},
        "executorProvenance": {
            "codeRevision": "a" * 40,
            "skillVersion": "plotloom-image-specialist.v3",
            "skillHash": "b" * 64,
            "model": "fixture",
            "reasoningEffort": "none",
        },
        "limitations": ["fixture delivery is not a real ImageGen visual result"],
    }
    (delivery / "executor-pin.json").write_text(json.dumps({
        "jobId": job["id"], "requestHash": job["requestHash"],
        "executionContract": "codex_specialist.v2", "skillVersion": "plotloom-image-specialist.v3",
        "codeRevision": "a" * 40, "skillHash": "b" * 64,
    }), encoding="utf-8")
    (delivery / "completion.json").write_text(json.dumps(manifest), encoding="utf-8")


def _complete_keyframe_adaptation_delivery(
    delivery: Path, job: dict, *, delivery_id: str, content: bytes
) -> None:
    """Write the narrow V3 fixture handoff for an exact-geometry candidate."""

    outputs = delivery / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    filename = "adapted-keyframe.png"
    (outputs / filename).write_bytes(content)
    provenance = {
        "codeRevision": "a" * 40,
        "skillVersion": "plotloom-image-specialist.v3",
        "skillHash": "b" * 64,
    }
    (delivery / "executor-pin.json").write_text(json.dumps({
        "jobId": job["id"], "requestHash": job["requestHash"],
        "executionContract": "codex_specialist.v2", **provenance,
    }), encoding="utf-8")
    (delivery / "completion.json").write_text(json.dumps({
        "schemaVersion": 2,
        "jobId": job["id"],
        "requestHash": job["requestHash"],
        "deliveryId": delivery_id,
        "actualPrompt": "Adapt the frozen reviewed keyframe into the requested complete canvas.",
        "outputs": [{
            "filename": filename,
            "sha256": sha256(content).hexdigest(),
            "role": "keyframe_adaptation",
        }],
        "toolEvidence": {"tool": "codex_imagegen", "taskId": "adaptation-fixture", "available": True},
        "executorProvenance": provenance,
        "limitations": ["fixture delivery is not a creative-quality claim"],
    }), encoding="utf-8")


def _import_asset(client: TestClient, project_id: str, color: tuple[int, int, int], *, origin: str = "creator reference") -> dict:
    response = client.post(
        f"/api/v2/projects/{project_id}/managed-assets",
        files={"image": ("reference.png", _png(color), "image/png")},
        data={"origin": origin, "rights": "unknown", "declared_additions_json": "[]"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _complete_project_with_resolved_image_context(repository: SQLiteRepository, brief, *, include_engineer: bool = False):
    """Build a canonical fixture whose frozen brief must resolve real facts."""

    bible, graph, scene_beats, storyboard = all_stage_payloads()
    scene = scene_beats.scenes[0]
    beat = scene_beats.beats[0]
    character = CharacterV2(
        id="captain", name="林默", role="领航员", description="刚苏醒的领航员",
        visual_anchors=["银色应急服"], sound_anchors=["浅促呼吸"], allowed_states=["steady"],
        continuity_rules=["头盔始终握在左手"], goal="确认飞船航线", traits=["克制"],
        voice_anchors=["低声"],
    )
    engineer = CharacterV2(
        id="engineer", name="周岚", role="工程师", description="维护飞船核心的工程师",
        visual_anchors=["琥珀色护目镜"], sound_anchors=["工具扣轻响"], allowed_states=["steady"],
        continuity_rules=["右腕始终佩戴识别带"], goal="保持反应堆稳定", traits=["果断"],
        voice_anchors=["清晰短句"],
    )
    location = LocationV2(
        id="bridge", name="舰桥", description="低照度舰桥", visual_anchors=["实用控制台灯"],
        sound_anchors=["循环通风"], allowed_states=["powered"], continuity_rules=["主屏保持离线"],
    )
    prop = PropV2(
        id="helmet", name="头盔", description="损伤的飞行头盔", visual_anchors=["划痕面罩"],
        sound_anchors=["扣环轻响"], allowed_states=["held"], continuity_rules=["始终在左手"],
    )
    cue = DialogueCue(
        id="wake-cue", beat_id=beat.id, order=1, speaker_id=character.id, voice_over=None,
        text="a", language="*", delivery="natural", performance_notes="压低声音",
        estimated_duration_units=70,
    )
    scene = scene.model_copy(update={
        "location_id": location.id, "character_ids": [character.id, engineer.id] if include_engineer else [character.id], "duration_budget_units": 100,
    })
    scene_beats = scene_beats.model_copy(update={
        "scenes": [scene, *scene_beats.scenes[1:]],
        "dialogue_cues": [cue],
    })
    first_shot = storyboard.shots[0].model_copy(update={
        "duration_units": 70,
        "character_ids": [character.id, engineer.id] if include_engineer else [character.id], "location_id": location.id, "prop_ids": [prop.id],
        "cue_ids": [cue.id],
        "required_entity_states": [
            RequiredEntityState(entity_type="character", entity_id=character.id, state="steady"),
            RequiredEntityState(entity_type="prop", entity_id=prop.id, state="held"),
        ],
    })
    second_shot = storyboard.shots[1].model_copy(update={"duration_units": 30})
    storyboard = storyboard.model_copy(update={"shots": [first_shot, second_shot, *storyboard.shots[2:]]})
    bible = bible.model_copy(update={"characters": [character, engineer] if include_engineer else [character], "locations": [location], "props": [prop]})
    project = repository.create_project(brief)
    for stage, payload in zip((StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS, StageName.STORYBOARD), (bible, graph, scene_beats, storyboard), strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    return repository.get_project(project.id), scene.id


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
                "presentationChange": "Prepare the approved shot as reviewed.",
            },
        )
        assert unavailable.status_code == 409 and unavailable.json()["code"] == "image_exchange_not_configured"
        assert client.get(f"/api/v2/projects/{project.id}/image-jobs").json() == {
            "configured": False, "jobs": [],
        }


def test_image_job_requires_nonblank_creator_direction_before_admission(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        missing_direction = client.post(
            f"/api/v2/projects/{project.id}/image-jobs",
            json={
                "approvalId": approval["id"], "shotId": _shot_id(repository, project.id, scene_id),
                "storyboardRevision": board.revision, "presentationChange": "   ",
            },
        )
        assert missing_direction.status_code == 422
        assert client.get(f"/api/v2/projects/{project.id}/image-jobs").json()["jobs"] == []


def test_image_job_refresh_reports_absent_delivery_as_waiting_without_a_receipt(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        job = _prepare(client, project.id, approval, _shot_id(repository, project.id, scene_id), board.revision)["job"]
        copied = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy")
        assert copied.status_code == 200, copied.text

        waiting = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert waiting.status_code == 200, waiting.text
        assert waiting.json() == {"state": "awaiting_delivery", "candidates": [], "idempotent": False}

        listed = client.get(f"/api/v2/projects/{project.id}/image-jobs").json()["jobs"]
        assert listed[0]["state"] == "exported"
        assert listed[0]["deliveries"] == []


def test_legacy_v1_package_remains_recheckable_without_a_template(tmp_path: Path) -> None:
    request = {"schemaVersion": 1, "jobId": "ij_" + "a" * 20, "kind": "original"}
    request_hash = sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())
    copied = exchange.write_package(
        job_id=request["jobId"], request=request, request_hash=request_hash, references=[],
    )
    package = Path(copied["packagePath"])
    assert {item.name for item in package.iterdir()} == {"COPY_ASSIGNMENT.txt", "request.json"}
    exchange.verify_package(
        job_id=request["jobId"], request=request, request_hash=request_hash, references=[],
    )


def test_legacy_v3_package_keeps_its_unpinned_skill_template(tmp_path: Path) -> None:
    """New preflight must not rewrite a frozen v3 package's expected bytes."""

    request = {
        "schemaVersion": 3, "jobId": "ij_" + "b" * 20,
        "executionContract": "codex_specialist.v2", "kind": "original",
        "frozenSnapshot": {},
    }
    request_hash = sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())
    copied = exchange.write_package(
        job_id=request["jobId"], request=request, request_hash=request_hash, references=[],
    )
    package = Path(copied["packagePath"])
    package_request = json.loads((package / "request.json").read_text())
    template = json.loads((package / "completion-manifest.example.json").read_text())
    assert package_request["packageVersion"] == 3
    assert "specialistPreflight" not in package_request
    assert template["executorProvenance"]["skillVersion"] == "plotloom-image-specialist.v1"
    assert "pin_image_specialist.py" not in (package / "COPY_ASSIGNMENT.txt").read_text()
    exchange.verify_package(
        job_id=request["jobId"], request=request, request_hash=request_hash, references=[],
    )


def test_v4_executor_pin_is_the_only_awaiting_partial_delivery(tmp_path: Path) -> None:
    """A pre-generation marker is waiting; all other partial states fail closed."""

    job_id = "ij_" + "c" * 20
    request = {"schemaVersion": 3, "jobId": job_id, "kind": "original"}
    request_hash = sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())
    copied = exchange.write_package(
        job_id=job_id,
        request=request,
        request_hash=request_hash,
        references=[],
    )
    delivery = Path(copied["deliveryPath"])
    delivery.mkdir(parents=True)
    pin = {
        "jobId": job_id,
        "requestHash": request_hash,
        "executionContract": "codex_specialist.v2",
        "skillVersion": "plotloom-image-specialist.v3",
        "codeRevision": "a" * 40,
        "skillHash": "b" * 64,
    }
    (delivery / "executor-pin.json").write_text(json.dumps(pin), encoding="utf-8")
    assert exchange.read_delivery(
        job_id=job_id, request_hash=request_hash, require_executor_pin=True,
        expected_executor_skill_version="plotloom-image-specialist.v3",
    ) is None

    pin["jobId"] = "ij_" + "e" * 20
    (delivery / "executor-pin.json").write_text(json.dumps(pin), encoding="utf-8")
    try:
        exchange.read_delivery(
            job_id=job_id, request_hash=request_hash, require_executor_pin=True,
            expected_executor_skill_version="plotloom-image-specialist.v3",
        )
    except ImageJobError as error:
        assert error.code == "delivery_executor_pin_mismatch"
    else:
        raise AssertionError("wrong-job executor pin must not become an awaiting delivery")

    pin["jobId"] = job_id
    (delivery / "executor-pin.json").write_text(json.dumps(pin), encoding="utf-8")
    (delivery / "unexpected.txt").write_text("partial", encoding="utf-8")
    try:
        exchange.read_delivery(
            job_id=job_id, request_hash=request_hash, require_executor_pin=True,
            expected_executor_skill_version="plotloom-image-specialist.v3",
        )
    except ImageJobError as error:
        assert error.code == "delivery_partial"
    else:
        raise AssertionError("undeclared partial delivery must remain rejected")


def test_frozen_v2_executor_pin_remains_a_valid_awaiting_delivery(tmp_path: Path) -> None:
    """A historical v2 package keeps its frozen expected skill version."""

    job_id = "ij_" + "f" * 20
    request_hash = "d" * 64
    delivery = tmp_path / "exchange" / "jobs" / job_id / "delivery"
    delivery.mkdir(parents=True)
    (delivery / "executor-pin.json").write_text(json.dumps({
        "jobId": job_id,
        "requestHash": request_hash,
        "executionContract": "codex_specialist.v2",
        "skillVersion": "plotloom-image-specialist.v2",
        "codeRevision": "a" * 40,
        "skillHash": "b" * 64,
    }), encoding="utf-8")
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())

    assert exchange.read_delivery(
        job_id=job_id,
        request_hash=request_hash,
        require_executor_pin=True,
        expected_executor_skill_version="plotloom-image-specialist.v2",
    ) is None


def test_manual_image_job_prepare_copy_refresh_select_and_refine(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_resolved_image_context(repository, brief)
    store = MemoryArtifactStore()
    app = create_app(repository, artifact_store=store, image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        shot_id = _shot_id(repository, project.id, scene_id)
        prepared = _prepare(client, project.id, approval, shot_id, board.revision)
        original = prepared["job"]
        assert original["request"]["frozenSnapshot"]["references"] == []
        frozen_snapshot = original["request"]["frozenSnapshot"]
        assert original["request"]["schemaVersion"] == 2
        assert frozen_snapshot["creatorDirection"] == {
            "presentationChange": "Keep the reviewed presentation readable and faithful to this approved shot.",
        }
        assert [item["id"] for item in frozen_snapshot["resolvedContext"]["characters"]] == ["captain"]
        assert [item["id"] for item in frozen_snapshot["resolvedContext"]["locations"]] == ["bridge"]
        assert [item["id"] for item in frozen_snapshot["resolvedContext"]["props"]] == ["helmet"]
        assert [item["id"] for item in frozen_snapshot["resolvedContext"]["dialogueCues"]] == ["wake-cue"]

        copied = client.post(f"/api/v2/projects/{project.id}/image-jobs/{original['id']}/copy")
        assert copied.status_code == 200, copied.text
        package = Path(copied.json()["packagePath"])
        delivery = Path(copied.json()["deliveryPath"])
        request = json.loads((package / "request.json").read_text())
        assert request["jobId"] == original["id"]
        assert request["packageVersion"] == 2
        completion_template = json.loads((package / "completion-manifest.example.json").read_text())
        assert completion_template["jobId"] == original["id"]
        assert completion_template["requestHash"] == original["requestHash"]
        assert completion_template["outputs"][0]["role"] == "original"
        assert "completion-manifest.example.json" in (package / "COPY_ASSIGNMENT.txt").read_text()
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
            presentationChange="Keep the parent framing; improve facial clarity under practical control-panel lighting.",
        )["job"]
        copied_refinement = client.post(f"/api/v2/projects/{project.id}/image-jobs/{refinement['id']}/copy")
        assert copied_refinement.status_code == 200, copied_refinement.text
        refinement_request = json.loads((Path(copied_refinement.json()["packagePath"]) / "request.json").read_text())
        assert refinement_request["references"][0]["role"] == "parent_output"
        reviewed_intent = refinement_request["frozenSnapshot"]["reviewedVisualIntent"]
        assert reviewed_intent["bindingId"] == selection.json()["id"]
        assert reviewed_intent["visualIntentId"] == intent["id"]
        assert reviewed_intent["visualIntentRevision"] == intent["revision"]
        assert refinement_request["frozenSnapshot"]["creatorDirection"] == {
            "presentationChange": "Keep the parent framing; improve facial clarity under practical control-panel lighting.",
        }
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

        stale_refinement = _prepare(
            client, project.id, approval, shot_id, board.revision,
            parentCandidateAssetId=candidate["assetId"],
            presentationChange="Hold the same composition while refining the practical-lighting balance.",
        )["job"]
        stale_copy = client.post(f"/api/v2/projects/{project.id}/image-jobs/{stale_refinement['id']}/copy")
        assert stale_copy.status_code == 200, stale_copy.text
        # An edited role-specific VisualIntent deliberately invalidates the
        # copied refinement before its late delivery can publish an asset.
        revised_intent = _intent(client, project.id, candidate["assetId"])
        assert revised_intent["revision"] == 2
        _complete_delivery(
            Path(stale_copy.json()["deliveryPath"]), stale_refinement,
            delivery_id="refinement-stale-001", content=_png((80, 30, 10)), role="refinement",
        )
        stale_return = client.post(f"/api/v2/projects/{project.id}/image-jobs/{stale_refinement['id']}/refresh")
        assert stale_return.status_code == 200
        assert stale_return.json() == {
            "deliveryId": "refinement-stale-001", "state": "inapplicable",
            "diagnosticCode": "late_or_stale_delivery", "idempotent": False, "candidates": [],
        }


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
                "presentationChange": "Keep the approved presentation.",
                "deliveryPath": "/arbitrary/operator/path", "prompt": "replace frozen facts",
            },
        )
        assert attempted_path_authority.status_code == 422

        forged = client.post(
            f"/api/v2/projects/{project.id}/image-jobs",
            json={
                "approvalId": other_approval["id"], "shotId": shot_id, "storyboardRevision": board.revision,
                "presentationChange": "Keep the approved presentation.",
            },
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


def test_identity_reference_job_is_explicitly_reviewed_and_stales_on_replacement(repository, brief, tmp_path: Path) -> None:
    """P1.5 fixture proof: decisions, not image hashes, govern identity currentness."""

    project, scene_id = _complete_project_with_resolved_image_context(repository, brief)
    store = MemoryArtifactStore()
    app = create_app(repository, artifact_store=store, image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        shot_id = _shot_id(repository, project.id, scene_id)
        payload = {
            "approvalId": approval["id"], "shotId": shot_id, "storyboardRevision": board.revision,
            "presentationChange": "Close portrait for cross-shot identity review.", "contractVersion": 3,
        }
        missing = client.post(f"/api/v2/projects/{project.id}/image-jobs", json=payload)
        assert missing.status_code == 422 and missing.json()["code"] == "identity_reference_missing"

        def imported(color: tuple[int, int, int], origin: str) -> dict:
            response = client.post(
                f"/api/v2/projects/{project.id}/managed-assets",
                files={"image": ("reference.png", _png(color), "image/png")},
                data={"origin": origin, "rights": "unknown", "declared_additions_json": "[]"},
            )
            assert response.status_code == 201, response.text
            return response.json()

        reference = imported((50, 80, 120), "creator primary reference")
        selected = client.post(
            f"/api/v2/projects/{project.id}/character-references",
            json={
                "characterId": "captain", "primaryAssetId": reference["id"], "complementaryAssetIds": [],
                "expectedReferenceRevision": 0, "reviewer": "creator", "notes": "Stable face and build; not an outfit or framing mandate.",
            },
        )
        assert selected.status_code == 201, selected.text
        job = client.post(f"/api/v2/projects/{project.id}/image-jobs", json=payload).json()["job"]
        frozen = job["request"]["frozenSnapshot"]
        assert frozen["visibleCharacterIds"] == ["captain"]
        assert frozen["characterIdentity"][0]["referenceDecisionId"] == selected.json()["id"]
        assert [entry["role"] for entry in frozen["references"]] == ["character_identity"]
        copied = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy")
        assert copied.status_code == 200, copied.text
        request = json.loads((Path(copied.json()["packagePath"]) / "request.json").read_text())
        assert request["packageVersion"] == 4
        assert request["references"][0]["role"] == "character_identity:captain"
        delivery_root = Path(copied.json()["deliveryPath"])
        delivery_root.mkdir(parents=True)
        (delivery_root / "executor-pin.json").write_text(json.dumps({
            "jobId": job["id"], "requestHash": job["requestHash"],
            "executionContract": "codex_specialist.v2", "skillVersion": "plotloom-image-specialist.v3",
            "codeRevision": "a" * 40, "skillHash": "b" * 64,
        }), encoding="utf-8")
        awaiting = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert awaiting.status_code == 200 and awaiting.json()["state"] == "awaiting_delivery"
        assert client.get(f"/api/v2/projects/{project.id}/image-jobs").json()["jobs"][0]["deliveries"] == []
        _complete_identity_delivery(Path(copied.json()["deliveryPath"]), job, delivery_id="identity-001", content=_png((40, 90, 140)))
        candidate = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh").json()["candidates"][0]
        intent = client.post(
            f"/api/v2/projects/{project.id}/managed-assets/{candidate['assetId']}/visual-intents",
            json={"role": "shot_keyframe", "identityIntent": "captain identity", "compositionIntent": "close portrait", "styleIntent": "cinematic", "sourceRefs": ["P1.5 fixture"]},
        ).json()
        binding = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes",
            json={
                "assetId": candidate["assetId"], "shotId": shot_id, "sceneId": scene_id, "expectedSelectionRevision": 0,
                "storyboardRevision": board.revision, "approvalId": approval["id"], "compatibilityNote": "creator selected candidate",
                "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
            },
        )
        assert binding.status_code == 201, binding.text
        preview_payload = {"sceneId": scene_id, "shotIds": [shot_id], "expectedSelectionRevision": 1, "storyboardRevision": board.revision, "approvalId": approval["id"]}
        assert client.post(f"/api/v2/projects/{project.id}/still-previews", json=preview_payload).status_code == 409
        review = client.post(
            f"/api/v2/projects/{project.id}/same-person-reviews",
            json={
                "bindingId": binding.json()["id"], "expectedReviewRevision": 0, "reviewer": "creator",
                "comparisons": [{"characterId": "captain", "judgment": "pass", "identityNotes": "Face and build match.", "stateNotes": "Shot state remains authored."}],
                "notes": "Human visual review; not a face-recognition score.",
            },
        )
        assert review.status_code == 201, review.text
        preview = client.post(f"/api/v2/projects/{project.id}/still-previews", json=preview_payload)
        assert preview.status_code == 201 and preview.json()["state"] == "current"
        assert preview.json()["manifest"]["frames"][0]["identityReviewId"] == review.json()["id"]
        replacement = imported((120, 80, 50), "replacement reference")
        replaced = client.post(
            f"/api/v2/projects/{project.id}/character-references",
            json={
                "characterId": "captain", "primaryAssetId": replacement["id"], "complementaryAssetIds": [],
                "expectedReferenceRevision": 1, "reviewer": "creator", "notes": "Explicit replacement keeps old decision history.",
            },
        )
        assert replaced.status_code == 201, replaced.text
        assert client.get(f"/api/v2/projects/{project.id}/image-jobs").json()["jobs"][0]["current"] is False
        assert client.get(f"/api/v2/projects/{project.id}/same-person-reviews").json()["reviews"][0]["current"] is False
        assert client.get(f"/api/v2/projects/{project.id}/still-previews").json()["previews"][0]["state"] == "stale"
        assert len(client.get(f"/api/v2/projects/{project.id}/character-references").json()["decisions"]) == 2


def test_character_reference_proposal_is_story_first_and_never_auto_selects(repository, brief, tmp_path: Path) -> None:
    project, _scene_id = _complete_project_with_resolved_image_context(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        bible = repository.get_stage_head(project.id, StageName.STORY_BIBLE)
        proposal = client.post(
            f"/api/v2/projects/{project.id}/character-reference-proposals",
            json={"characterId": "captain", "storyBibleRevision": bible.revision, "visualDirection": "Cinematic realistic character appearance proposal."},
        )
        assert proposal.status_code == 201, proposal.text
        frozen = proposal.json()["proposal"]["request"]["frozenSnapshot"]
        assert frozen["target"] == "character_reference_proposal"
        assert "approvalId" not in frozen and "shotId" not in frozen
        assert client.get(f"/api/v2/projects/{project.id}/character-references").json()["decisions"] == []


def test_character_reference_decisions_are_project_scoped_and_revision_checked(repository, brief, tmp_path: Path) -> None:
    project, _scene_id = _complete_project_with_resolved_image_context(repository, brief)
    other_project, _other_scene_id = _complete_project_with_resolved_image_context(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        primary = _import_asset(client, project.id, (10, 40, 70))
        created = client.post(
            f"/api/v2/projects/{project.id}/character-references",
            json={
                "characterId": "captain", "primaryAssetId": primary["id"], "complementaryAssetIds": [],
                "expectedReferenceRevision": 0, "reviewer": "creator", "notes": "Primary identity reference.",
            },
        )
        assert created.status_code == 201, created.text
        stale = client.post(
            f"/api/v2/projects/{project.id}/character-references",
            json={
                "characterId": "captain", "primaryAssetId": primary["id"], "complementaryAssetIds": [],
                "expectedReferenceRevision": 0, "reviewer": "creator", "notes": "Conflicting stale request.",
            },
        )
        assert stale.status_code == 409 and stale.json()["code"] == "revision_conflict"
        cross_project = client.post(
            f"/api/v2/projects/{other_project.id}/character-references",
            json={
                "characterId": "captain", "primaryAssetId": primary["id"], "complementaryAssetIds": [],
                "expectedReferenceRevision": 0, "reviewer": "creator", "notes": "This must never cross project scope.",
            },
        )
        assert cross_project.status_code == 404
        revoked = client.post(
            f"/api/v2/projects/{project.id}/character-references/captain/revoke",
            json={"expectedReferenceRevision": 1, "reviewer": "creator", "reason": "Retire this view."},
        )
        assert revoked.status_code == 200 and revoked.json()["current"] is False
        history = client.get(f"/api/v2/projects/{project.id}/character-references").json()
        assert history["states"] == [{"characterId": "captain", "revision": 2, "activeDecisionId": None, "current": False}]
        assert history["decisions"][0]["id"] == created.json()["id"]


def test_v3_maps_two_visible_characters_and_excludes_offscreen_context(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_resolved_image_context(repository, brief, include_engineer=True)
    app = create_app(repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        for character_id, color in (("captain", (30, 50, 70)), ("engineer", (80, 100, 120))):
            reference = _import_asset(client, project.id, color, origin=f"{character_id} reference")
            selected = client.post(
                f"/api/v2/projects/{project.id}/character-references",
                json={
                    "characterId": character_id, "primaryAssetId": reference["id"], "complementaryAssetIds": [],
                    "expectedReferenceRevision": 0, "reviewer": "creator", "notes": f"{character_id} durable identity.",
                },
            )
            assert selected.status_code == 201, selected.text
        job = _prepare(
            client, project.id, approval, _shot_id(repository, project.id, scene_id), board.revision,
            contractVersion=3,
        )["job"]
        frozen = job["request"]["frozenSnapshot"]
        assert frozen["visibleCharacterIds"] == ["captain", "engineer"]
        assert [item["characterId"] for item in frozen["characterIdentity"]] == ["captain", "engineer"]
        copied = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy")
        assert copied.status_code == 200, copied.text
        package = json.loads((Path(copied.json()["packagePath"]) / "request.json").read_text())
        assert [item["role"] for item in package["references"]] == [
            "character_identity:captain", "character_identity:engineer",
        ]
        delivery = Path(copied.json()["deliveryPath"])
        _complete_identity_delivery(delivery, job, delivery_id="missing-engineer-attestation", content=_png((20, 30, 40)))
        manifest_path = delivery / "completion.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["referenceUse"]["viewedReferenceHashes"] = manifest["referenceUse"]["viewedReferenceHashes"][:1]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        rejected = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert rejected.status_code == 422 and rejected.json()["code"] == "delivery_reference_use_mismatch"
        _complete_identity_delivery(delivery, job, delivery_id="two-character-001", content=_png((20, 30, 40)))
        accepted = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert accepted.status_code == 200 and accepted.json()["state"] == "accepted"

    # This direct compiler check isolates the original defect: the scene,
    # dialogue and required character state retain captain as story context,
    # but an authored character-free Shot never projects captain as visible.
    with repository._read() as session:  # noqa: SLF001 - compiler contract inspection
        board_payload = repository._load_stage_payload(session, project.id, StageName.STORYBOARD)  # noqa: SLF001
        bible_payload = repository._load_stage_payload(session, project.id, StageName.STORY_BIBLE)  # noqa: SLF001
        beats_payload = repository._load_stage_payload(session, project.id, StageName.SCENE_BEATS)  # noqa: SLF001
    context = SQLiteRepository._image_job_resolved_context(  # noqa: SLF001 - focused visibility contract
        shot=board_payload.shots[0].model_copy(update={"character_ids": []}), storyboard=board_payload,
        story_bible=bible_payload, scene_beats=beats_payload,
    )
    assert context["characters"] == []
    assert context["scene"]["characterIds"] == ["captain", "engineer"]
    assert context["dialogueCues"][0]["speakerId"] == "captain"


def test_center_crop_is_source_bound_and_never_auto_selects_a_reviewed_keyframe(repository, brief) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore())
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        shot_id = _shot_id(repository, project.id, scene_id)
        source = client.post(
            f"/api/v2/projects/{project.id}/managed-assets",
            files={"image": ("wide-keyframe.png", _png((30, 70, 120), width=640, height=360), "image/png")},
            data={"origin": "creator supplied landscape keyframe", "rights": "unknown", "declared_additions_json": "[]"},
        )
        assert source.status_code == 201, source.text
        intent = _intent(client, project.id, source.json()["id"])
        selected = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes",
            json={
                "assetId": source.json()["id"], "shotId": shot_id, "sceneId": scene_id,
                "expectedSelectionRevision": 0, "storyboardRevision": board.revision,
                "approvalId": approval["id"], "compatibilityNote": "Creator accepted the landscape source as the reviewed keyframe.",
                "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
            },
        )
        assert selected.status_code == 201, selected.text

        cropped = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes/{selected.json()['id']}/center-crops",
            json={
                "targetProfileId": "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
                "expectedSelectionRevision": selected.json()["selectionRevision"],
            },
        )
        assert cropped.status_code == 201, cropped.text
        crop_asset = cropped.json()["asset"]
        assert (crop_asset["width"], crop_asset["height"]) == (576, 1024)

        # A deterministic derivative is a candidate, not an implied creative
        # decision. The original selected binding and global revision stand.
        workbench = client.get(f"/api/v2/projects/{project.id}/visual-workbench").json()
        assert workbench["selectionRevision"] == selected.json()["selectionRevision"]
        assert len(workbench["reviewedKeyframes"]) == 1
        binding = workbench["reviewedKeyframes"][0]
        assert binding["id"] == selected.json()["id"]
        assert binding["assetId"] == source.json()["id"]
        assert binding["selectionRevision"] == selected.json()["selectionRevision"]
        assets = client.get(f"/api/v2/projects/{project.id}/managed-assets").json()["assets"]
        recorded_crop = next(asset for asset in assets if asset["id"] == crop_asset["id"])
        assert recorded_crop["provenance"] == {
            "origin": "plotloom_keyframe_center_crop",
            "sourceBindingId": selected.json()["id"],
            "sourceAssetId": source.json()["id"],
            "sourceOriginalHash": source.json()["originalHash"],
            "targetProfile": {
                "id": "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
                "version": 1,
                "width": 576,
                "height": 1024,
                "orientation": "portrait",
            },
            "transform": {"version": 1, "strategy": "cover_center_crop", "centering": [0.5, 0.5]},
        }


def test_keyframe_adaptation_freezes_source_and_exact_h3_geometry(repository, brief, tmp_path: Path) -> None:
    project, scene_id = _complete_project_with_three_shots(repository, brief)
    app = create_app(
        repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange"
    )
    with TestClient(app) as client:
        _review, approval = _approval(client, project.id)
        board = repository.get_stage_head(project.id, StageName.STORYBOARD)
        shot_id = _shot_id(repository, project.id, scene_id)
        source = client.post(
            f"/api/v2/projects/{project.id}/managed-assets",
            files={"image": ("wide-keyframe.png", _png((90, 40, 20), width=640, height=360), "image/png")},
            data={"origin": "creator supplied landscape keyframe", "rights": "unknown", "declared_additions_json": "[]"},
        )
        assert source.status_code == 201, source.text
        intent = _intent(client, project.id, source.json()["id"])
        selected = client.post(
            f"/api/v2/projects/{project.id}/reviewed-keyframes",
            json={
                "assetId": source.json()["id"], "shotId": shot_id, "sceneId": scene_id,
                "expectedSelectionRevision": 0, "storyboardRevision": board.revision,
                "approvalId": approval["id"], "compatibilityNote": "Creator approved this landscape source before adaptation.",
                "visualIntentId": intent["id"], "visualIntentRevision": intent["revision"],
            },
        )
        assert selected.status_code == 201, selected.text

        prepared = client.post(
            f"/api/v2/projects/{project.id}/image-jobs",
            json={
                "approvalId": approval["id"], "shotId": shot_id,
                "storyboardRevision": board.revision, "contractVersion": 3,
                "keyframeAdaptationProfileId": "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
                "presentationChange": "Recompose the reviewed shot for the portrait H3 frame without adding blank bands.",
            },
        )
        assert prepared.status_code == 201, prepared.text
        job = prepared.json()["job"]
        frozen = job["request"]["frozenSnapshot"]
        assert job["request"]["kind"] == "keyframe_adaptation"
        assert frozen["keyframeAdaptation"]["sourceBindingId"] == selected.json()["id"]
        assert frozen["keyframeAdaptation"]["sourceOriginalHash"] == source.json()["originalHash"]
        assert frozen["keyframeAdaptation"]["outputContract"] == {
            "width": 576, "height": 1024, "mimeTypes": ["image/jpeg", "image/png"],
        }
        assert [entry["role"] for entry in frozen["references"]] == ["source_keyframe"]

        copied = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/copy")
        assert copied.status_code == 200, copied.text
        package = json.loads((Path(copied.json()["packagePath"]) / "request.json").read_text())
        assert package["references"][0]["role"] == "source_keyframe"
        assert "complete 576x1024 composition" in package["deliveryInstruction"]
        delivery = Path(copied.json()["deliveryPath"])

        _complete_keyframe_adaptation_delivery(
            delivery, job, delivery_id="wrong-geometry", content=_png((40, 90, 120), width=576, height=1023)
        )
        rejected = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert rejected.status_code == 422 and rejected.json()["code"] == "delivery_geometry_mismatch"

        _complete_keyframe_adaptation_delivery(
            delivery, job, delivery_id="correct-geometry", content=_png((40, 90, 120), width=576, height=1024)
        )
        accepted = client.post(f"/api/v2/projects/{project.id}/image-jobs/{job['id']}/refresh")
        assert accepted.status_code == 200 and accepted.json()["state"] == "accepted"
        candidate = accepted.json()["candidates"][0]
        assert candidate["role"] == "keyframe_adaptation"

        # Acceptance retains a candidate for the author. It never silently
        # swaps the source reviewed binding to make a video request viable.
        workbench = client.get(f"/api/v2/projects/{project.id}/visual-workbench").json()
        assert workbench["selectionRevision"] == selected.json()["selectionRevision"]
        assert workbench["reviewedKeyframes"][0]["assetId"] == source.json()["id"]
        assert candidate["assetId"] != source.json()["id"]


def test_character_reference_proposal_delivery_retains_candidate_without_auto_selection(repository, brief, tmp_path: Path) -> None:
    project, _scene_id = _complete_project_with_resolved_image_context(repository, brief)
    app = create_app(repository, artifact_store=MemoryArtifactStore(), image_exchange_root=tmp_path / "exchange")
    with TestClient(app) as client:
        bible = repository.get_stage_head(project.id, StageName.STORY_BIBLE)
        proposal = client.post(
            f"/api/v2/projects/{project.id}/character-reference-proposals",
            json={"characterId": "captain", "storyBibleRevision": bible.revision, "visualDirection": "Cinematic realistic explorer portrait."},
        ).json()["proposal"]
        copied = client.post(f"/api/v2/projects/{project.id}/character-reference-proposals/{proposal['id']}/copy")
        assert copied.status_code == 200, copied.text
        template = json.loads((Path(copied.json()["packagePath"]) / "completion-manifest.example.json").read_text())
        assert template["schemaVersion"] == 2 and "referenceUse" not in template
        content = _png((90, 50, 30))
        delivery = Path(copied.json()["deliveryPath"])
        (delivery / "outputs").mkdir(parents=True)
        (delivery / "outputs" / "proposal.png").write_bytes(content)
        provenance = {"codeRevision": "c" * 40, "skillVersion": "plotloom-image-specialist.v3", "skillHash": "d" * 64}
        (delivery / "executor-pin.json").write_text(json.dumps({
            "jobId": proposal["id"], "requestHash": proposal["requestHash"],
            "executionContract": "codex_specialist.v2", **provenance,
        }), encoding="utf-8")
        manifest = {
            "schemaVersion": 2,
            "jobId": proposal["id"],
            "requestHash": proposal["requestHash"],
            "deliveryId": "proposal-001",
            "actualPrompt": "The executor used Bearer sk-secret-must-not-enter-project.",
            "outputs": [{"filename": "proposal.png", "sha256": sha256(content).hexdigest(), "role": "original"}],
            "toolEvidence": {"tool": "codex_imagegen", "taskId": "proposal-fixture", "available": True},
            "executorProvenance": provenance,
        }
        (delivery / "completion.json").write_text(json.dumps(manifest), encoding="utf-8")
        rejected = client.post(
            f"/api/v2/projects/{project.id}/character-reference-proposals/{proposal['id']}/refresh"
        )
        assert rejected.status_code == 422
        assert rejected.json()["code"] == "delivery_manifest_secret"
        proposals = client.get(
            f"/api/v2/projects/{project.id}/character-reference-proposals"
        ).json()["proposals"]
        assert next(item for item in proposals if item["id"] == proposal["id"])["deliveries"] == []

        manifest["actualPrompt"] = (
            "A cinematic realistic appearance study for the frozen character context."
        )
        (delivery / "completion.json").write_text(json.dumps(manifest), encoding="utf-8")
        accepted = client.post(f"/api/v2/projects/{project.id}/character-reference-proposals/{proposal['id']}/refresh")
        assert accepted.status_code == 200 and accepted.json()["state"] == "accepted"
        assert len(accepted.json()["candidates"]) == 1
        assert client.get(f"/api/v2/projects/{project.id}/character-references").json()["decisions"] == []
