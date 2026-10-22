"""Manual handoff preserves exact target uses without source-context rebasing."""
from contextlib import closing
from copy import deepcopy

import pytest

from plotloom.autopilot_handoff_contracts import HumanHandoffRequest, ReviewFrame
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.project.autopilot_handoff import (
    record_handoff,
    review_material,
)
from plotloom.persistence.project.handoff_visual_intents import (
    authored_intent,
    prepare_handoff_intents,
)
from plotloom.persistence.schema import (
    ReviewedShotBindingRow,
    VisualIntentRow,
    VisualSelectionStateRow,
)
from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed
from tests.test_autopilot_handoff import observation


def shared_frames(tmp_path, seed):
    storage, view, _calls = copy_awaiting_handoff_seed(seed, tmp_path / "shared-frame-copy")
    with closing(storage.projects.open(view.project_id)) as store:
        record_handoff(store, HumanHandoffRequest.model_validate(observation(review_material(store))))
        initial = review_material(store)["bundle"]["frames"]
        source, target = initial[:2]
        intent = store.media.create_visual_intent(view.project_id, source["assetId"], {
            "role": "shot_keyframe", "compositionIntent": "Independent reviewed target use",
            "sourceRefs": [target["shotId"]], "sourceBindingId": source["sourceId"],
        }, target_shot_id=target["shotId"])
        with store.repository._read() as session:
            binding = session.get(ReviewedShotBindingRow, source["sourceId"])
            state = session.get(VisualSelectionStateRow, view.project_id)
        store.media.select_reviewed_keyframe(view.project_id, asset_id=source["assetId"], shot_id=target["shotId"],
            scene_id=target["sceneId"], expected_selection_revision=state.revision,
            storyboard_revision=binding.storyboard_revision, approval_id=binding.approval_id,
            compatibility_note="Exact pixels inspected independently for target", visual_intent_id=intent["id"],
            visual_intent_revision=intent["revision"])
    return storage, view.project_id


def unchanged_observation(store, review):
    body = observation(review)
    with store.repository._read() as session:
        for item, frame in zip(body["frames"], review["bundle"]["frames"], strict=True):
            binding = session.get(ReviewedShotBindingRow, frame["sourceId"])
            intent = session.get(VisualIntentRow, binding.visual_intent_id)
            item["intent"] = authored_intent(intent.intent)
    return body


@pytest.mark.parametrize("change_target", [False, True])
def test_manual_shared_frame_handoff_preserves_target_use_and_source_intent(tmp_path, awaiting_handoff_seed, change_target):
    storage, project_id = shared_frames(tmp_path, awaiting_handoff_seed)
    with closing(storage.projects.open(project_id)) as store:
        review = review_material(store)
        body = unchanged_observation(store, review)
        source, target = review["bundle"]["frames"][:2]
        assert "targetUse" not in source and target["targetUse"]["targetShotId"] == target["shotId"]
        if change_target:
            body["frames"][1]["intent"]["compositionIntent"] += " Fresh B-only author observation."
        with store.repository._read() as session:
            source_intent = session.get(ReviewedShotBindingRow, source["sourceId"]).visual_intent_id
        result = record_handoff(store, HumanHandoffRequest.model_validate(body))
        assert result.state == "handed_off"
        current = store.media.list_current_reviewed_keyframes(project_id)
        with store.repository._read() as session:
            bindings = {item["shotId"]: session.get(ReviewedShotBindingRow, item["id"]) for item in current}
            assert bindings[source["shotId"]].visual_intent_id == source_intent
            target_intent = session.get(VisualIntentRow, bindings[target["shotId"]].visual_intent_id)
            assert target_intent.intent["targetUse"] == target["targetUse"]
            assert target_intent.intent["compositionIntent"] == body["frames"][1]["intent"]["compositionIntent"]
    with closing(storage.projects.open(project_id)):
        pass  # Raw historical admission validates both handoff receipts.


def test_source_intent_change_and_forged_display_refuse_without_partial_handoff(tmp_path, awaiting_handoff_seed):
    storage, project_id = shared_frames(tmp_path, awaiting_handoff_seed)
    with closing(storage.projects.open(project_id)) as store:
        review = review_material(store)
        body = unchanged_observation(store, review)
        tables = ("v2_visual_intents", "v2_reviewed_shot_bindings", "v2_same_person_reviews", "v2_autopilot_handoffs")
        with store.repository._read() as session:
            before = [session.connection().exec_driver_sql(f"SELECT count(*) FROM {table}").scalar() for table in tables]
            forged = deepcopy(review["bundle"]["frames"])
            forged[1]["targetUse"]["source"]["originalHash"] = "0" * 64
            with pytest.raises(InvalidTransitionError, match="target use changed"):
                prepare_handoff_intents(session, store.repository, project_id, HumanHandoffRequest.model_validate(body).frames, forged)
        body["frames"][0]["intent"]["compositionIntent"] += " Source intent changed."
        with pytest.raises(InvalidTransitionError, match="required source intent"):
            record_handoff(store, HumanHandoffRequest.model_validate(body))
        with store.repository._read() as session:
            after = [session.connection().exec_driver_sql(f"SELECT count(*) FROM {table}").scalar() for table in tables]
        assert after == before


def test_ordinary_review_frame_serialization_does_not_add_null_target_use():
    frame = ReviewFrame.model_validate({"shotId": "A", "sceneId": "scene", "title": "A", "sceneName": "scene",
        "direction": "frame", "assetId": "asset", "originalHash": "a" * 64, "width": 10, "height": 10,
        "characterIds": [], "description": "A", "origin": "human_binding", "sourceId": "binding"})
    assert "targetUse" not in frame.model_dump(mode="json", by_alias=True)
