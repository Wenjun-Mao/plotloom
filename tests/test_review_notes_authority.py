"""Observation scratch cannot revoke the exact material being reviewed."""
from contextlib import closing

import pytest

from plotloom.persistence.project.autopilot_handoff import review_material
from plotloom.review_drafts import is_observation_notes_draft
from tests.test_native_material_qa import native_environment


@pytest.mark.parametrize("editor", ["material_review", "video_pack_notes", "video_segment_notes"])
@pytest.mark.parametrize("handed_off", [False, True])
def test_review_note_save_and_discard_preserve_native_bundle_and_qa_authority(
    tmp_path, monkeypatch, awaiting_handoff_seed, editor, handed_off,
):
    storage, client, project, review, _scope, actor = native_environment(
        awaiting_handoff_seed, tmp_path, monkeypatch)
    if handed_off:
        from tests.test_bulk_material_handoff import bulk_observation
        response = client.post(f"/api/v2/projects/{project}/autopilot/handoff",
            json=bulk_observation(review) | {"attribution": actor})
        assert response.status_code == 200, response.text
        with closing(storage.projects.open(project)) as store:
            review = review_material(store)
    target = review["bundleHash"]
    identity = f"{editor}:{target}"
    with closing(storage.projects.open(project)) as store:
        base = store.project().revision
        before = store.repository.autopilot.current(project)
    url = f"/api/v2/projects/{project}"
    response = client.put(url + "/authoring-drafts", json={
        "editorScope": "review_buffer", "entityId": identity,
        "baseCanonicalRevision": base, "expectedDraftRevision": 0,
        "payload": {"editor": editor, "targetId": target,
            "basis": f"{review['runRevision']}:{target}", "text": "Actual agent QA observations awaiting explicit submission."},
    })
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["draftRevision"] == 1 and saved["payload"]["text"].startswith("Actual agent QA")
    with closing(storage.projects.open(project)) as store:
        current = store.repository.autopilot.current(project)
        assert (current.id, current.state, current.revision, current.handoff) == (
            before.id, before.state, before.revision, before.handoff)
        assert review_material(store) == review
        assert store.authoring_drafts()[0].payload == saved["payload"]
    assert client.get(url + "/qa-context").json() == {
        "eligible": True, "required": True, "reason": None, "attribution": actor}
    removed = client.request("DELETE", url + "/authoring-drafts", json={
        "editorScope": "review_buffer", "entityId": identity, "expectedDraftRevision": 1})
    assert removed.status_code == 204
    with closing(storage.projects.open(project)) as store:
        assert review_material(store) == review and not store.authoring_drafts()
        assert store.repository.autopilot.current(project).revision == before.revision


@pytest.mark.parametrize("editor", ["source", "video_directions", "production_intent"])
def test_source_or_direction_draft_still_withdraws_material_authority(
    tmp_path, monkeypatch, awaiting_handoff_seed, editor,
):
    storage, client, project, review, _scope, _actor = native_environment(
        awaiting_handoff_seed, tmp_path, monkeypatch)
    with closing(storage.projects.open(project)) as store:
        base = store.project().revision
    url = f"/api/v2/projects/{project}"
    result = client.put(url + "/authoring-drafts", json={
        "editorScope": "review_buffer", "entityId": editor,
        "baseCanonicalRevision": base, "expectedDraftRevision": 0,
        "payload": {"editor": editor, "basis": "changed-source", "text": "Source or direction edit."},
    })
    assert result.status_code == 200, result.text
    with closing(storage.projects.open(project)) as store:
        assert store.repository.autopilot.current(project).state == "taken_over"
        assert review_material(store)["bundleHash"] != review["bundleHash"]
    context = client.get(url + "/qa-context").json()
    assert context["required"] and not context["eligible"] and context["attribution"] is None


def test_unknown_or_mislabeled_scratch_is_not_excluded_from_material_authority():
    correct = {"editor_scope": "review_buffer", "entity_id": "material_review:bundle",
        "payload": {"editor": "material_review", "targetId": "bundle"}}
    assert is_observation_notes_draft(correct)
    assert not is_observation_notes_draft(correct | {"entity_id": "source"})
    assert not is_observation_notes_draft(correct | {"editor_scope": "brief"})
    assert not is_observation_notes_draft(correct | {"payload": {"editor": "unknown"}})
    assert not is_observation_notes_draft(correct | {"payload": None})
