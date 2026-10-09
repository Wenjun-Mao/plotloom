"""Typed review projections preserve stale refusal and retained evidence."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtReopenRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.review_binding_diagnostics import FIELD_OWNERS, review_binding_diagnostics
from plotloom.script_contracts import ScriptReviewState, ScriptReopenRequest
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest, StoryboardReviewBinding, StoryboardReviewState
from tests.test_project_storage_art import _accepted_f4_script, _deliver_stage


def test_every_storyboard_binding_field_has_an_explicit_diagnostic_owner() -> None:
    assert set(FIELD_OWNERS) == set(StoryboardReviewBinding.model_fields)
    frozen = SimpleNamespace(**dict.fromkeys(FIELD_OWNERS, "before"))
    current = SimpleNamespace(**dict.fromkeys(FIELD_OWNERS, "after"))
    diagnostics = review_binding_diagnostics(current, frozen, tuple(FIELD_OWNERS))
    assert [item.field for item in diagnostics] == list(FIELD_OWNERS)
    for item in diagnostics:
        assert item.owner == FIELD_OWNERS[item.field]
        field = item.field
        label = field.replace("_content_hash", " content").replace("_revision", " revision").replace("_", " ")
        assert item.technical_message == f"{label} changed"
        assert item.code == (
            "binding_revision_changed" if field.endswith("_revision") else
            "binding_content_changed" if field.endswith("_content_hash") else "binding_value_changed"
        )
    assert review_binding_diagnostics(frozen, frozen, tuple(FIELD_OWNERS)) == []


@pytest.mark.parametrize("model", [ScriptReviewState, StoryboardReviewState])
def test_string_diagnostics_are_not_a_supported_contract(model: type) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({"status": "stale", "staleReasons": ["raw text"], "acceptedReviewState": {"status": "missing", "staleReasons": []}})


@pytest.mark.parametrize("stage,owner,code", [
    ("script", "art", "accepted_art_not_current"),
    ("storyboard-source-review", "script", "accepted_script_not_current"),
])
def test_reopened_prerequisite_has_same_typed_read_and_refusal_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str, owner: str, code: str,
) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        _accepted_f4_script(store)
        script = store.script_state().accepted_script
        report = store.script_candidate_report(script.candidate_job_id)
        if stage == "script":
            store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        else:
            # This is a lifecycle test, not an upstream storyboard validator test.
            # Accept first: a pending candidate must still win the duplicate guard.
            monkeypatch.setattr("plotloom.persistence.project.storyboard_review.ProjectStoryboardReviewPersistence._validate", staticmethod(lambda *_: None))
            candidate, request = store.prepare_storyboard_review_candidate("ch_" + "s" * 32)
            ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", {"episodes": []}, "diagnostic-board"))
            store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
            store.reopen_script(ScriptReopenRequest(expected_script_revision=1))
    finally:
        store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    url = f"/api/v2/projects/{project_id}/{stage}"
    before = client.get(url)
    assert before.status_code == 200
    state = before.json()
    assert state["status"] == "stale"
    diagnostic = state["staleReasons"][0]
    assert diagnostic["code"] == code and diagnostic["owner"] == owner
    response = client.post(url + "/candidates")
    assert response.status_code == 409
    assert response.json()["code"] == "review_context_not_current"
    assert response.json()["diagnostic"] == diagnostic
    assert client.get(url).json() == state
    retained = client.get(f"/api/v2/projects/{project_id}/script").json()["acceptedScript"]
    assert retained == script.model_dump(mode="json", by_alias=True)
    assert client.get(f"/api/v2/projects/{project_id}/script/candidates/{script.candidate_job_id}/report").text == report
