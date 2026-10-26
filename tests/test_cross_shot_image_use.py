"""Explicit target review preserves native origin and independent freshness."""
import json
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from plotloom.stage_contracts import StageName
from plotloom.exceptions import InvalidTransitionError
from plotloom.image_job_contracts import ImageJobCreateRequest
from plotloom.image_job_package import project_image_package
from plotloom.persistence.project.image_reviewed_use import freeze_reviewed_source
from plotloom.persistence.project.image_source_lineage import source_in_session
from plotloom.persistence.project.media_same_person_reviews import (
    SamePersonReviewPersistence,
)
from plotloom.persistence.schema import (
    ImageJobRow,
    ProductionUnitRow,
    VisualSelectionStateRow,
)
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.cross_shot_validation import assert_cross_shot_contracts
from plotloom.project_storage.format import ProjectStorageCorruptionError
from tests.project_folder_image_delivery_fixtures import (
    png,
    ready_exported_job,
    write_delivery,
)
from tests.test_image_source_lineage import select_output


def ready_source(tmp_path):
    client, project_id, job, path = ready_exported_job(tmp_path)
    write_delivery(path, job, png((14, 40, 90)), "cross-shot-source")
    response = client.post(f"/api/v2/projects/{project_id}/image-jobs/{job['id']}/refresh")
    assert response.status_code == 200, response.text
    asset = response.json()["candidates"][0]["assetId"]
    storage = client.app.state.project_folder_storage
    with closing(storage.projects.open(project_id)) as store:
        with store.repository._read() as session:
            unit = session.get(ProductionUnitRow, session.get(ImageJobRow, job["id"]).production_unit_id)
        source = select_output(store, project_id, asset, unit)
        board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
        target = next(item for item in board.shots if item.id != unit.shot_id)
    return client, storage, project_id, job, source, unit, target, asset


def reuse(store, project_id, source, unit, target, asset):
    intent = store.media.create_visual_intent(project_id, asset, {"role": "shot_keyframe",
        "compositionIntent": "Independent target framing review", "sourceRefs": [target.id],
        "sourceBindingId": source["id"]}, target_shot_id=target.id)
    with store.repository._read() as session:
        revision = session.get(VisualSelectionStateRow, project_id).revision
    binding = store.media.select_reviewed_keyframe(project_id, asset_id=asset, shot_id=target.id,
        scene_id=target.scene_id, expected_selection_revision=revision, storyboard_revision=unit.storyboard_revision,
        approval_id=unit.approval_id, compatibility_note="Pixels independently inspected for target shot",
        visual_intent_id=intent["id"], visual_intent_revision=intent["revision"])
    return intent, binding


def test_explicit_reuse_separate_intents_strict_origin_and_source_intent_withdrawal(tmp_path):
    client, storage, project_id, _job, source, unit, target, asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store:
            with store.repository._read() as session, pytest.raises(InvalidTransitionError, match="different shot"):
                source_in_session(session, project_id, asset, shot_id=target.id)
            intent, binding = reuse(store, project_id, source, unit, target, asset)
            assert intent["intent"]["targetUse"]["source"]["originShotId"] == unit.shot_id
            assert len(store.media.list_visual_intents(project_id)) == 2
            assert {item["shotId"] for item in store.media.list_current_reviewed_keyframes(project_id)} == {unit.shot_id, target.id}
            # A new source intent withdraws B's required context without rewriting history.
            select_output(store, project_id, asset, unit)
            assert target.id not in {item["shotId"] for item in store.media.list_current_reviewed_keyframes(project_id)}
            assert binding["id"] != source["id"]
        # Historical frozen evidence remains valid despite current source intent supersession.
        with closing(storage.projects.open(project_id)) as store, store.repository._read() as session:
            assert_cross_shot_contracts(session.connection().connection.driver_connection)
    finally:
        client.close()


def test_continuity_freezes_independent_role_and_survives_source_selection(tmp_path):
    client, storage, project_id, job, source, unit, target, asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store:
            prepared = store.media.prepare_image_job(project_id, approval_id=unit.approval_id, shot_id=target.id,
                storyboard_revision=unit.storyboard_revision, presentation_change="Target owns action and framing",
                scene_continuity_binding_id=source["id"], contract_version=3)["job"]
            snapshot = prepared["request"]["frozenSnapshot"]
            assert snapshot["sceneContinuity"]["bindingId"] == source["id"]
            assert snapshot["references"][-1]["role"] == "scene_continuity"
            assert snapshot["shot"]["id"] == target.id and prepared["request"]["kind"] == "original"
            source_intent = next(item for item in store.media.list_visual_intents(project_id) if item["id"] == source["visualIntentId"])
            with store.repository._read() as session:
                revision = session.get(VisualSelectionStateRow, project_id).revision
            store.media.select_reviewed_keyframe(project_id, asset_id=asset, shot_id=unit.shot_id, scene_id=unit.scene_id,
                expected_selection_revision=revision, storyboard_revision=unit.storyboard_revision, approval_id=unit.approval_id,
                compatibility_note="Another independent A selection", visual_intent_id=source_intent["id"], visual_intent_revision=source_intent["revision"])
            assert next(item for item in store.media.list_image_jobs(project_id) if item["id"] == prepared["id"])["current"]
            store.media.cancel_image_job(project_id, job["id"], "Source authority withdrawn")
            assert not next(item for item in store.media.list_image_jobs(project_id) if item["id"] == prepared["id"])["current"]
    finally:
        client.close()


def test_refined_source_reuse_survives_unrelated_source_selection_and_snapshot(tmp_path):
    client, storage, project_id, _job, source, unit, target, asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store:
            refined = store.media.prepare_image_job(project_id, approval_id=unit.approval_id,
                shot_id=unit.shot_id, storyboard_revision=unit.storyboard_revision,
                parent_candidate_asset_id=asset, presentation_change="Refine A", contract_version=2)["job"]
        copied = client.post(f"/api/v2/projects/{project_id}/image-jobs/{refined['id']}/copy")
        assert copied.status_code == 200, copied.text
        delivery = Path(copied.json()["deliveryPath"])
        write_delivery(delivery, refined, png((36, 70, 95)), "refined-source")
        manifest = json.loads((delivery / "completion.json").read_text())
        manifest["outputs"][0]["role"] = "refinement"
        (delivery / "completion.json").write_text(json.dumps(manifest))
        accepted = client.post(f"/api/v2/projects/{project_id}/image-jobs/{refined['id']}/refresh")
        assert accepted.status_code == 200, accepted.text
        refined_asset = accepted.json()["candidates"][0]["assetId"]
        with closing(storage.projects.open(project_id)) as store:
            refined_source = select_output(store, project_id, refined_asset, unit)
            _intent, target_binding = reuse(store, project_id, refined_source, unit, target, refined_asset)
            original_intent = next(item for item in store.media.list_visual_intents(project_id) if item["id"] == source["visualIntentId"])
            with store.repository._read() as session:
                revision = session.get(VisualSelectionStateRow, project_id).revision
            store.media.select_reviewed_keyframe(project_id, asset_id=asset, shot_id=unit.shot_id,
                scene_id=unit.scene_id, expected_selection_revision=revision, storyboard_revision=unit.storyboard_revision,
                approval_id=unit.approval_id, compatibility_note="Select another still for A only",
                visual_intent_id=original_intent["id"], visual_intent_revision=original_intent["revision"])
            assert target_binding["id"] in {item["id"] for item in store.media.list_current_reviewed_keyframes(project_id)}
            target_refinement = store.media.prepare_image_job(project_id, approval_id=unit.approval_id,
                shot_id=target.id, storyboard_revision=unit.storyboard_revision,
                parent_candidate_asset_id=refined_asset, presentation_change="Refine B's independently reviewed pixels",
                contract_version=2)["job"]
            assert target_refinement["request"]["frozenSnapshot"]["reviewedVisualIntent"]["bindingId"] == target_binding["id"]
            assert target_refinement["current"]
            store.media.cancel_image_job(project_id, target_refinement["id"], "Fixture preparation verified; leave project idle for snapshot")
            preview = store.media.create_still_preview(project_id, scene_id=target.scene_id, shot_ids=[target.id],
                expected_selection_revision=revision + 1, storyboard_revision=unit.storyboard_revision, approval_id=unit.approval_id)
            assert preview["manifest"]["frames"][0]["bindingId"] == target_binding["id"]
        receipt = storage.recovery.create_snapshot(project_id)
        fresh = ProjectFolderStorage(outputs_root=tmp_path / "restored-output", application_data_root=tmp_path / "restored-app")
        fresh.recovery.restore(Path(receipt.location))
        with closing(fresh.projects.open(project_id)) as restored:
            assert target_binding["id"] in {item["id"] for item in restored.media.list_current_reviewed_keyframes(project_id)}
    finally:
        client.close()


@pytest.mark.parametrize("tamper", ["binding", "hash", "origin", "self", "remove"])
def test_historical_target_use_rejects_forged_json(tmp_path, tamper):
    client, storage, project_id, _job, source, unit, target, asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store:
            intent, _binding = reuse(store, project_id, source, unit, target, asset)
            payload = deepcopy(intent["intent"])
            if tamper == "binding": payload["targetUse"]["source"]["bindingId"] = "missing"
            if tamper == "hash": payload["targetUse"]["source"]["originalHash"] = "0" * 64
            if tamper == "origin": payload["targetUse"]["source"]["originShotId"] = target.id
            if tamper == "self": payload["targetUse"]["targetShotId"] = unit.shot_id
            if tamper == "remove": payload.pop("targetUse")
            with store.repository._write() as session:
                connection = session.connection().connection.driver_connection
                connection.execute("UPDATE v2_visual_intents SET intent=? WHERE id=?", (json.dumps(payload), intent["id"]))
                with pytest.raises(ProjectStorageCorruptionError):
                    assert_cross_shot_contracts(connection)
                session.rollback()
    finally:
        client.close()


@pytest.mark.parametrize("contract", ["codex_specialist.v3", "codex_exec.v1"])
def test_both_image_package_consumers_view_continuity_with_target_precedence(tmp_path, contract):
    request = {"schemaVersion": 3, "kind": "original", "executionContract": contract,
        "specialistPreflight": {"version": "p1.5-pin.v2", "executionContract": contract},
        "frozenSnapshot": {"sceneContinuity": {"bindingId": "source"}}}
    projected, instructions, template, _ = project_image_package(root=tmp_path, job_id="ij_" + "a" * 32,
        request=request, request_hash="1" * 64, reference_entries=[{"role": "scene_continuity", "filename": "references/a.png", "sha256": "2" * 64}],
        native_task_binding={"mode": "current_task"} if contract == "codex_specialist.v3" else None)
    assert "target shot" in instructions.decode() and "scene_continuity" in projected["deliveryInstruction"]
    if template:
        assert "referenceUse" in json.loads(template)
    else:
        assert "tools.view_image" in instructions.decode()


def test_continuity_source_is_mutually_exclusive_with_edit_and_adaptation():
    for other in ({"parentCandidateAssetId": "parent"}, {"keyframeAdaptationProfileId": "h3_portrait"}, {"contractVersion": 2}):
        with pytest.raises(ValueError):
            ImageJobCreateRequest.model_validate({"approvalId": "approval", "shotId": "target", "storyboardRevision": 1,
                "presentationChange": "Target direction", "contractVersion": 3, "sceneContinuityBindingId": "source", **other})


def test_reused_target_identity_mapping_uses_target_visible_cast_and_current_references():
    from plotloom.persistence.schema import ManagedAssetRow, VisualIntentRow
    target = SimpleNamespace(id="B", character_ids=["person-B"])
    canonical = SimpleNamespace(_load_stage_payload=lambda _s, _p, stage:
        SimpleNamespace(shots=[target]) if stage == StageName.STORYBOARD else
        SimpleNamespace(characters=[SimpleNamespace(id="person-A"), SimpleNamespace(id="person-B")]))
    decision = SimpleNamespace(id="current-B-reference", reference_revision=4,
        primary_asset_id="portrait-B", complementary_asset_ids=[], character_context_hash="B-context")
    references = SimpleNamespace(current_character_reference_in_session=lambda _s, _p, character:
        decision if character.id == "person-B" else None)
    def get(model, identifier):
        if model is VisualIntentRow:
            return SimpleNamespace(intent={"targetUse": {"targetShotId": "B"}})
        assert model is ManagedAssetRow and identifier == "portrait-B"
        return SimpleNamespace(id="portrait-B", original_hash="b" * 64)
    owner = SamePersonReviewPersistence(None, canonical, None, references)
    mapping = owner.identity_mapping_for_binding_in_session(SimpleNamespace(get=get),
        SimpleNamespace(visual_intent_id="B-intent", shot_id="B", project_id="project"))
    assert mapping == [{"characterId": "person-B", "referenceDecisionId": "current-B-reference",
        "referenceRevision": 4, "characterContextHash": "B-context",
        "assets": [{"assetId": "portrait-B", "originalHash": "b" * 64}]}]


def test_creation_refuses_self_cross_project_and_target_use_cycles(tmp_path):
    client, storage, project_id, _job, source, unit, target, asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store:
            with store.repository._read() as session:
                admission, currentness = store.repository._media.admission, store.repository._media.image_currentness
                for project, shot in ((project_id, unit.shot_id), ("another-project", target.id)):
                    with pytest.raises(InvalidTransitionError, match="another shot's current reviewed frame"):
                        freeze_reviewed_source(session, project, source["id"], shot, admission, currentness)
            _intent, binding = reuse(store, project_id, source, unit, target, asset)
            with pytest.raises(InvalidTransitionError, match="cycle"):
                store.media.create_visual_intent(project_id, asset, {"role": "shot_keyframe",
                    "compositionIntent": "Do not let B point back into A", "sourceRefs": [unit.shot_id],
                    "sourceBindingId": binding["id"]}, target_shot_id=unit.shot_id)
    finally:
        client.close()


def test_adaptation_of_reused_target_tracks_its_exact_source_use_context(tmp_path):
    client, storage, project_id, _job, source, unit, target, asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store:
            _intent, binding = reuse(store, project_id, source, unit, target, asset)
            adapted = store.media.prepare_image_job(project_id, approval_id=unit.approval_id, shot_id=target.id,
                storyboard_revision=unit.storyboard_revision, presentation_change="Square target composition",
                keyframe_adaptation={"targetProfile": {"id": "fixture-square", "width": 256, "height": 256}}, contract_version=3)["job"]
            assert adapted["request"]["frozenSnapshot"]["keyframeAdaptation"]["sourceBindingId"] == binding["id"]
            assert next(item for item in store.media.list_image_jobs(project_id) if item["id"] == adapted["id"])["current"]
            store.media.create_visual_intent(project_id, asset, {"role": "shot_keyframe",
                "compositionIntent": "Required source-A intent changed", "sourceRefs": [unit.shot_id]})
            assert not next(item for item in store.media.list_image_jobs(project_id) if item["id"] == adapted["id"])["current"]
    finally:
        client.close()


@pytest.mark.parametrize("missing_origin", [None, "", " "])
def test_ordinary_missing_native_origin_remains_readable_but_ineligible(tmp_path, missing_origin):
    client, storage, project_id, job, _source, _unit, _target, _asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store, store.repository._write() as session:
            row = session.get(ImageJobRow, job["id"])
            payload = deepcopy(row.request)
            if missing_origin is None:
                payload["frozenSnapshot"]["shot"].pop("id")
            else:
                payload["frozenSnapshot"]["shot"]["id"] = missing_origin
            row.request = payload
        with closing(storage.projects.open(project_id)) as store:
            assert store.media.list_current_reviewed_keyframes(project_id) == []
    finally:
        client.close()
