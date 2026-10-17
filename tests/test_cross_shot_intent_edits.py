"""Saved target-use edits retain exact source proof across source reselection."""
from contextlib import closing

import pytest

from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import VisualSelectionStateRow
from tests.test_cross_shot_image_use import ready_source, reuse


def reselect_source(store, project_id, source, unit, asset):
    with store.repository._read() as session:
        revision = session.get(VisualSelectionStateRow, project_id).revision
    return store.media.select_reviewed_keyframe(project_id, asset_id=asset, shot_id=unit.shot_id,
        scene_id=unit.scene_id, expected_selection_revision=revision, storyboard_revision=unit.storyboard_revision,
        approval_id=unit.approval_id, compatibility_note="Reselect A without changing intent",
        visual_intent_id=source["visualIntentId"], visual_intent_revision=source["visualIntentRevision"])


def post_intent(client, project_id, asset, target, intent, source_id, direction, *, mutate_request=False):
    payload = {"assetId": asset, "shotId": target.id, "role": "shot_keyframe", "identityIntent": None,
        "compositionIntent": direction, "styleIntent": None, "sourceRefs": [target.id],
        "sourceBindingId": source_id, "retainedVisualIntentId": intent["id"]}
    url = f"/api/v2/projects/{project_id}"
    revision = client.get(url + "/stages").json()["stages"][-1]["head"]["revision"]
    draft = client.put(url + "/authoring-drafts", json={"editorScope": "visual_intent", "entityId": f"{target.id}:{asset}",
        "baseCanonicalRevision": revision, "expectedDraftRevision": 0, "payload": payload})
    assert draft.status_code == 200, draft.text
    request = {key: value for key, value in payload.items() if key != "assetId"}
    if mutate_request:
        request["retainedVisualIntentId"] = "forged-replacement"
    return client.post(url + f"/managed-assets/{asset}/visual-intents", json=request | {
        "consumedDraft": {"editorScope": "visual_intent", "entityId": f"{target.id}:{asset}", "draftRevision": draft.json()["draftRevision"]}})


def test_repeated_unselected_target_edits_after_source_reselection_preserve_frozen_use(tmp_path):
    client, storage, project_id, _job, source, unit, target, asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store:
            intent, _binding = reuse(store, project_id, source, unit, target, asset)
            new_source = reselect_source(store, project_id, source, unit, asset)
        frozen = intent["intent"]["targetUse"]
        for index in range(2):
            response = post_intent(client, project_id, asset, target, intent, source["id"], f"B edit {index}")
            assert response.status_code == 201, response.text
            intent = response.json()
            assert intent["intent"]["targetUse"] == frozen
            with closing(storage.projects.open(project_id)) as store:
                listed = store.media.list_visual_intents(project_id)
                assert next(row for row in listed if row["id"] == intent["id"])["targetUseCurrent"] is True
                assert "targetUseCurrent" not in next(row for row in listed if row["id"] == source["visualIntentId"])
                assert all(row["shotId"] != target.id for row in store.media.list_current_reviewed_keyframes(project_id))
        with closing(storage.projects.open(project_id)) as store:
            with store.repository._read() as session:
                revision = session.get(VisualSelectionStateRow, project_id).revision
            selected = store.media.select_reviewed_keyframe(project_id, asset_id=asset, shot_id=target.id,
                scene_id=target.scene_id, expected_selection_revision=revision, storyboard_revision=unit.storyboard_revision,
                approval_id=unit.approval_id, compatibility_note="Re-reviewed B after both author edits",
                visual_intent_id=intent["id"], visual_intent_revision=intent["revision"])
            assert selected["id"] in {item["id"] for item in store.media.list_current_reviewed_keyframes(project_id)}
            # Explicitly changing to A's new binding freezes fresh authority.
            fresh = store.media.create_visual_intent(project_id, asset, {"role": "shot_keyframe",
                "compositionIntent": "Explicit fresh source", "sourceRefs": [target.id], "sourceBindingId": new_source["id"]}, target_shot_id=target.id)
            assert fresh["intent"]["targetUse"]["source"]["bindingId"] == new_source["id"]
    finally:
        client.close()


@pytest.mark.parametrize("defect", ["stale", "forged", "different-source", "target-context", "target-presentation"])
def test_retained_intent_edits_refuse_wrong_selector_or_changed_target_context(tmp_path, defect, monkeypatch):
    client, storage, project_id, _job, source, unit, target, asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store:
            intent, _binding = reuse(store, project_id, source, unit, target, asset)
            selector, source_id = intent["id"], source["id"]
            if defect == "forged": selector = source["visualIntentId"]
            if defect == "different-source": source_id = reselect_source(store, project_id, source, unit, asset)["id"]
            if defect == "stale":
                store.media.create_visual_intent(project_id, asset, {"role": "shot_keyframe", "compositionIntent": "New B edit",
                    "sourceRefs": [target.id], "sourceBindingId": source_id, "retainedVisualIntentId": selector}, target_shot_id=target.id)
            if defect == "target-context":
                with store.repository._write() as session:
                    from plotloom.persistence.schema import ApprovalDecisionRow
                    session.get(ApprovalDecisionRow, unit.approval_id).decision = "reject"
            if defect == "target-presentation":
                presentations = store.repository._media.image_currentness.presentations
                original = presentations.current
                monkeypatch.setattr(presentations, "current", lambda session, project, shot:
                    {"id": "changed-target-presentation"} if shot == target.id else original(session, project, shot))
            count = len(store.media.list_visual_intents(project_id))
            if defect in {"target-context", "target-presentation"}:
                assert next(row for row in store.media.list_visual_intents(project_id) if row["id"] == intent["id"])["targetUseCurrent"] is False
            with pytest.raises(InvalidTransitionError):
                store.media.create_visual_intent(project_id, asset, {"role": "shot_keyframe", "compositionIntent": "Rejected edit",
                    "sourceRefs": [target.id], "sourceBindingId": source_id, "retainedVisualIntentId": selector}, target_shot_id=target.id)
            assert len(store.media.list_visual_intents(project_id)) == count
    finally:
        client.close()


def test_durable_draft_cannot_swap_retained_intent_selector_at_consumption(tmp_path):
    client, storage, project_id, _job, source, unit, target, asset = ready_source(tmp_path)
    try:
        with closing(storage.projects.open(project_id)) as store:
            intent, _binding = reuse(store, project_id, source, unit, target, asset)
        refused = post_intent(client, project_id, asset, target, intent, source["id"], "CAS-bound B edit", mutate_request=True)
        assert refused.status_code == 409, refused.text
        drafts = client.get(f"/api/v2/projects/{project_id}/authoring-drafts").json()
        assert drafts[0]["payload"]["retainedVisualIntentId"] == intent["id"]
    finally:
        client.close()
