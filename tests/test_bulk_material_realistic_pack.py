"""Realistic whole-pack preflight; generated fixtures only, no provider dispatch."""
from contextlib import closing

from plotloom.autopilot_handoff_contracts import BulkHumanHandoffRequest
from plotloom.persistence.project.autopilot_handoff import record_handoff, review_material
from plotloom.persistence.project.autopilot_authority import video_eligible
from tests.autopilot_image_fixtures import run_pack
from tests.bulk_material_pack_fixtures import realistic_pack_environment
from tests.test_bulk_material_handoff import bulk_observation
from plotloom.validation import STORYBOARD_GATE_SET_VERSION


def test_42_frames_five_reference_sets_and_genuine_geometry(tmp_path, monkeypatch):
    storage, _registry, service, view, calls, _text = realistic_pack_environment(tmp_path, monkeypatch)
    try:
        run_pack(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            current = review_material(store)
            frames = current["bundle"]["frames"]
            assert len(frames) == 42 and len(current["bundle"]["references"]) == 5
            assert len(calls) == 47
            assert any(item.get("geometryPreparation") for item in frames)
            assert any(not item["characterIds"] for item in frames)
            assert any(len(item["characterIds"]) == 2 for item in frames)
            # One exact human-bound frame plus machine-provisional material.
            inventory = current["bundle"]["inventory"]
            approval = store.repository._approvals.decide_storyboard_approval(view.project_id,
                expected_revision=inventory["storyboardRevision"], expected_content_hash=inventory["storyboardHash"],
                decision="approve", reviewer="Disposable fixture human", gate_set_version=STORYBOARD_GATE_SET_VERSION, note="Fixture approval")
            frame = frames[0]
            intent = store.media.create_visual_intent(view.project_id, frame["assetId"], {"role": "shot_keyframe",
                "compositionIntent": "Disposable fixture author's reviewed first-frame intent.", "sourceRefs": [frame["shotId"]]})
            with store.repository._read() as session:
                presentation = store.repository._media.shot_presentations.current(session, view.project_id, frame["shotId"])
            store.media.select_reviewed_keyframe(view.project_id, asset_id=frame["assetId"], shot_id=frame["shotId"], scene_id=frame["sceneId"],
                expected_selection_revision=0, storyboard_revision=inventory["storyboardRevision"], approval_id=approval.id,
                compatibility_note="Fixture inspected exact first-frame geometry.", visual_intent_id=intent["id"], visual_intent_revision=intent["revision"],
                expected_presentation_revision=presentation["revision"] if presentation else 0)
            current = review_material(store)
            assert current["bundle"]["frames"][0]["origin"] == "human_binding"
            assert any(item["origin"] == "machine_provisional" for item in current["bundle"]["frames"])
            initial_body = bulk_observation(current)
            visible = next(item for item in initial_body["frames"] if item["comparisons"])
            visible["comparisons"][0].update(judgment="unassessable", productionDecision="authorize", uncertaintyReason="Fixture intentional back view")
            result = record_handoff(store, BulkHumanHandoffRequest.model_validate(initial_body))
            assert result.state == "handed_off"
            with store.repository._read() as session: assert video_eligible(session, view.project_id)
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_video_jobs").scalar() == 0
        with closing(storage.projects.open(view.project_id)) as store:
            fresh = review_material(store)
            assert len(fresh["bundle"]["frames"]) == 42
            assert all(item["origin"] == "human_binding" for item in fresh["bundle"]["frames"])
    finally:
        service.close()
