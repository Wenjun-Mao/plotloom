"""Original source entry and transaction-bound outline Brief dependencies."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.domain import ProjectBrief
from plotloom.outline_settings import OUTLINE_SETTINGS_FILENAME, outline_settings
from plotloom.source_outline_contracts import OutlineAcceptRequest, SourceMaterial
from tests.test_project_storage_source_outline import _deliver, _material, _request, _storage


@pytest.mark.parametrize("direction", [None, "", "  ", " 用动作表达情绪 "])
def test_original_synopsis_has_no_required_additional_direction(direction: str | None) -> None:
    values = {"kind": "synopsis", "title": "纸飞机", "text": "放飞或收好。"}
    if direction is not None:
        values["adaptationIntent"] = direction
    source = SourceMaterial.model_validate(values)
    assert source.adaptation_intent == (direction or "").strip()


@pytest.mark.parametrize("kind", ["imported_text", "existing_work"])
@pytest.mark.parametrize("direction", [None, "", "  "])
def test_imported_sources_still_require_an_explicit_adaptation_goal(kind: str, direction: str | None) -> None:
    values = {"kind": kind, "title": "原作", "text": "原作正文。"}
    if direction is not None:
        values["adaptationIntent"] = direction
    with pytest.raises(ValidationError, match="explicit adaptation goal"):
        SourceMaterial.model_validate(values)


def test_source_api_carries_settings_without_inventing_story_or_direction(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        created = client.post("/api/v2/projects", json={"brief": {
            **FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True),
            "targetPlaythroughSeconds": 30, "language": "zh-CN", "visualStyle": "真人写实",
        }})
        assert created.status_code == 201, created.text
        project = created.json()
        base = f"/api/v2/projects/{project['id']}/source-outline"
        material = {"kind": "synopsis", "title": project["brief"]["title"], "text": project["brief"]["synopsis"]}
        saved = client.put(f"{base}/source", json={"expectedSourceRevision": 0, "material": material})
        assert saved.status_code == 200, saved.text
        assert saved.json()["source"]["material"]["adaptationIntent"] == ""
        assert saved.json()["candidate"] is saved.json()["acceptedOutline"] is None
        prepared = client.post(f"{base}/candidates")
        assert prepared.status_code == 201, prepared.text
        package = Path(prepared.json()["packagePath"])
        request = json.loads((package / "request.json").read_text())
        expected = outline_settings(ProjectBrief.model_validate(project["brief"]))
        assert request["inputArtifacts"][OUTLINE_SETTINGS_FILENAME] == expected
        assert json.loads((package / "inputs" / OUTLINE_SETTINGS_FILENAME).read_text()) == expected
        assert "title" not in expected and "synopsis" not in expected
        assert request["source"]["text"] == material["text"]
        assert request["source"]["adaptationIntent"] == ""
        assert "Report conflicts" in request["creativeBrief"]
        assert client.get(base).json()["acceptedOutline"] is None


def test_new_outline_preparation_refuses_missing_and_stale_settings(tmp_path: Path) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    try:
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = _request(store.manifest.project_id, source)
        with pytest.raises(CreativeHandoffError) as missing:
            store.prepare_outline_candidate(request.model_copy(update={"input_artifacts": {}}))
        assert missing.value.code == "outline_settings_missing"
        settings = {**request.input_artifacts[OUTLINE_SETTINGS_FILENAME], "language": "en-US"}
        with pytest.raises(CreativeHandoffError) as stale:
            store.prepare_outline_candidate(request.model_copy(update={"input_artifacts": {OUTLINE_SETTINGS_FILENAME: settings}}))
        assert stale.value.code == "outline_settings_stale"
        assert store.source_outline_state().candidate is None
    finally:
        store.close()


def test_structured_directions_survive_reopen_and_reach_frozen_outline_inputs(tmp_path: Path):
    brief = ProjectBrief.model_validate({**FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True),
        "genreSelections": [{"group": "subject", "value": "科幻"}, {"group": "narrative", "value": "港口传奇"}],
        "visualStyleSelections": [{"group": "representation", "value": "真人写实"}, {"group": "lighting", "value": "暖色"}],
        "genre": "保留原有自由文本", "visualStyle": "真实空间里的温暖灯光"})
    storage = _storage(tmp_path)
    store = storage.projects.create(brief)
    project_id = store.manifest.project_id
    store.close()
    reopened = storage.projects.open(project_id)
    try:
        retained = reopened.project().brief
        assert retained.genre_selections == brief.genre_selections
        assert retained.visual_style_selections == brief.visual_style_selections
        assert retained.genre == brief.genre and retained.visual_style == brief.visual_style
        material = _material()
        reopened.save_source_material(expected_source_revision=0, material=material)
        request = _request(project_id, material, brief=retained)
        reopened.prepare_outline_candidate(request)
        settings = request.input_artifacts[OUTLINE_SETTINGS_FILENAME]
        assert settings["genre"] == "科幻；港口传奇；保留原有自由文本"
        assert settings["visualStyle"] == "真人写实；暖色；真实空间里的温暖灯光"
        assert settings["genreSelections"] == brief.generation_input()["genreSelections"]
    finally:
        reopened.close()


@pytest.mark.parametrize("delivered", [False, True])
def test_brief_change_blocks_old_outline_delivery_or_acceptance(tmp_path: Path, delivered: bool) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    try:
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = _request(store.manifest.project_id, source)
        store.prepare_outline_candidate(request)
        delivery = _deliver(store, request)
        if delivered:
            store.admit_outline_delivery(delivery)
        project = store.project()
        store.update_brief(project.brief.model_copy(update={"target_playthrough_seconds": 30}), expected_revision=project.revision)
        with pytest.raises(CreativeHandoffError) as stale:
            if delivered:
                store.accept_outline_candidate(OutlineAcceptRequest(job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0))
            else:
                store.admit_outline_delivery(delivery)
        assert stale.value.code == "outline_settings_stale"
        state = store.source_outline_state()
        assert state.accepted_outline is None
        assert state.candidate is not None and state.candidate.status == ("ready" if delivered else "prepared")
        assert state.source is not None and state.source.material == source
    finally:
        store.close()


@pytest.mark.parametrize("consume_draft", [False, True])
@pytest.mark.parametrize("change", [{"language": "en-US"}, {"targetPlaythroughSeconds": 30}, {"title": "新的工作片名", "synopsis": "新的简报梗概"}])
def test_brief_save_paths_preserve_already_accepted_source_and_outline(tmp_path: Path, consume_draft: bool, change: dict) -> None:
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    source = _material()
    store.save_source_material(expected_source_revision=0, material=source)
    request = _request(project_id, source)
    store.prepare_outline_candidate(request)
    store.admit_outline_delivery(_deliver(store, request))
    accepted = store.accept_outline_candidate(OutlineAcceptRequest(job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0))
    package_request = store.creative_handoff_exchange().root / "jobs" / request.job_id / "package" / "request.json"
    retained_request = package_request.read_bytes()
    store.close()
    with TestClient(create_project_folder_authoring_app(storage)) as client:
        base = f"/api/v2/projects/{project_id}"
        project = client.get(base).json()
        brief = {**project["brief"], **change}
        payload = {"expectedRevision": project["revision"], "brief": brief}
        if consume_draft:
            draft = client.put(f"{base}/authoring-drafts", json={
                "editorScope": "brief", "entityId": "root", "baseCanonicalRevision": project["revision"],
                "expectedDraftRevision": 0, "payload": brief,
            })
            assert draft.status_code == 200, draft.text
            payload["consumedDraft"] = {"editorScope": "brief", "entityId": "root", "draftRevision": draft.json()["draftRevision"]}
        patched = client.patch(base, json=payload)
        assert patched.status_code == 200, patched.text
        state = client.get(f"{base}/source-outline").json()
        assert state["outlineStatus"] == "accepted"
        assert state["acceptedOutline"] == accepted.accepted_outline.model_dump(mode="json", by_alias=True)
        assert state["source"]["material"] == source.model_dump(mode="json", by_alias=True)
        assert state["candidate"]["status"] == "accepted"
        assert state["candidate"]["jobId"] == request.job_id
        assert package_request.read_bytes() == retained_request
