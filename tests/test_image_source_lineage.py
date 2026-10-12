"""Reviewed refinements retain generation ancestry without retaining old selection."""
from contextlib import closing
import json
from pathlib import Path
import pytest
from sqlalchemy import select
from plotloom.persistence.schema import ImageJobRow, ProductionUnitRow, ReviewedShotBindingRow, VisualSelectionStateRow
from tests.test_project_storage_image_delivery_contracts import _ready_exported_job, _write_delivery, _png


def select_output(store, project_id, asset_id, unit):
    intent = store.media.create_visual_intent(project_id, asset_id,
        {"role": "shot_keyframe", "compositionIntent": "Inspected selected fixture output.", "sourceRefs": [unit.shot_id]})
    with store.repository._read() as session:
        state = session.get(VisualSelectionStateRow, project_id)
    binding = store.media.select_reviewed_keyframe(project_id, asset_id=asset_id, shot_id=unit.shot_id, scene_id=unit.scene_id,
        expected_selection_revision=state.revision if state else 0, storyboard_revision=unit.storyboard_revision,
        approval_id=unit.approval_id, compatibility_note="Actually inspected deterministic fixture.",
        visual_intent_id=intent["id"], visual_intent_revision=intent["revision"])
    with store.repository._read() as session:
        row = session.get(ReviewedShotBindingRow, binding["id"])
        assert store.repository._media.admission.reviewed_binding_admission_eligible_in_session(session, project_id, row)
    return binding


@pytest.mark.parametrize("withdraw", ["cancel-ancestor", "replace-ancestor-intent"])
def test_selected_refinement_and_next_refinement_retain_full_ancestor_currentness(tmp_path, withdraw):
    client, project_id, original, path = _ready_exported_job(tmp_path)
    storage = client.app.state.project_folder_storage
    try:
        _write_delivery(path, original, _png((10, 20, 30)), "original-lineage")
        response = client.post(f"/api/v2/projects/{project_id}/image-jobs/{original['id']}/refresh")
        assert response.status_code == 200, response.text
        original_asset = response.json()["candidates"][0]["assetId"]
        with closing(storage.projects.open(project_id)) as store:
            with store.repository._read() as session:
                unit = session.get(ProductionUnitRow, session.get(ImageJobRow, original["id"]).production_unit_id)
            select_output(store, project_id, original_asset, unit)
        parent_asset = original_asset
        refined = None
        for index in range(2):
            with closing(storage.projects.open(project_id)) as store:
                refined = store.media.prepare_image_job(project_id, approval_id=unit.approval_id,
                    shot_id=unit.shot_id, storyboard_revision=unit.storyboard_revision,
                    parent_candidate_asset_id=parent_asset, presentation_change="Refine current reviewed fixture.", contract_version=2)["job"]
            copied = client.post(f"/api/v2/projects/{project_id}/image-jobs/{refined['id']}/copy")
            assert copied.status_code == 200, copied.text
            delivery = Path(copied.json()["deliveryPath"])
            _write_delivery(delivery, refined, _png((40+index, 70, 100)), f"refinement-{index}")
            manifest_path = delivery / "completion.json"
            manifest = json.loads(manifest_path.read_text()); manifest["outputs"][0]["role"] = "refinement"
            manifest_path.write_text(json.dumps(manifest))
            response = client.post(f"/api/v2/projects/{project_id}/image-jobs/{refined['id']}/refresh")
            assert response.status_code == 200, response.text
            parent_asset = response.json()["candidates"][0]["assetId"]
            with closing(storage.projects.open(project_id)) as store:
                select_output(store, project_id, parent_asset, unit)
                with store.repository._read() as session:
                    assert store.repository._media.image_currentness.image_job_is_current_in_session(session, session.get(ImageJobRow, refined["id"]))
        with closing(storage.projects.open(project_id)) as store:
            if withdraw == "cancel-ancestor":
                store.media.cancel_image_job(project_id, original["id"], "Explicit ancestor withdrawal.")
            else:
                store.media.create_visual_intent(project_id, original_asset,
                    {"role": "shot_keyframe", "compositionIntent": "Changed original frozen source intent.", "sourceRefs": [unit.shot_id]})
            with store.repository._read() as session:
                assert not store.repository._media.image_currentness.image_job_is_current_in_session(session, session.get(ImageJobRow, refined["id"]))
                binding = session.scalar(select(ReviewedShotBindingRow).where(ReviewedShotBindingRow.project_id == project_id)
                    .order_by(ReviewedShotBindingRow.selection_revision.desc()).limit(1))
                assert not store.repository._media.admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding)
    finally:
        client.close()
