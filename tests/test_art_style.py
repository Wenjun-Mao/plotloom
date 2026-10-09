"""ADR 0094: author choice, prompt, validator and edit paths agree."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import re
import subprocess

from fastapi.testclient import TestClient
import pytest

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtAcceptRequest, ArtReopenRequest, ArtSaveRequest
from plotloom.art_style import ADAPTER, art_style_current, freeze_art_style, validate_art_style
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.review_context_diagnostics import ReviewContextError
from tests.test_project_storage_art import _deliver_stage, _prepare_art_context


def candidate(contract):
    preset = contract["preset"]
    return {
        "source": "Tide Light", "style": contract["style"],
        "scenes": [{
            "id": "S01", "name": "航标室", "primary": True, "summary": "Choice pressure",
            "anchors": [{"name": name, "desc": desc} for name, desc in [
                ("灯", "brass lamp"), ("窗", "salted glass"), ("桌", "worn wood")]],
            "lighting": [{"state": "dawn", "prompt": "cold dawn through a window"}],
            "image": {"prompt": preset["render"] + ", " + preset["surface"] + ", empty beacon room",
                      "sheet": preset["render"], "negativePrompt": preset["negative"],
                      "tags": preset["tags"]},
        }],
        "props": [],
        "sectionUsage": [{"sectionId": sid, "sceneIds": ["S01"], "propIds": []}
                         for sid in ["opening", "ending-a", "ending-b"]],
    }


@pytest.mark.parametrize("style", ["live-action", "realistic", "ghibli"])
def test_each_explicit_preset_retains_upstream_gates(style):
    contract = freeze_art_style(style, "Author visual direction")
    art = candidate(contract)
    cast = {"characters": [{"name": "Lin"}]}
    validate_art_style(art, cast, contract)
    assert art_style_current(contract, "Author visual direction")
    assert not art_style_current(contract, "Changed direction")
    # The extension does not bypass the upstream anchoring or character gates.
    art["scenes"][0]["anchors"] = []
    with pytest.raises(ValueError):
        validate_art_style(art, cast, contract)
    art = candidate(contract)
    art["scenes"][0]["image"]["prompt"] += ", Lin at the window"
    with pytest.raises(ValueError):
        validate_art_style(art, cast, contract)


@pytest.mark.parametrize("field,value", [
    ("prompt", "empty beacon room"),
    ("sheet", "Semi-realistic environment concept art"),
    ("tags", ["painterly"]),
    ("negativePrompt", "people, photorealistic"),
])
def test_live_action_cannot_silently_revert(field, value):
    contract = freeze_art_style("live-action", None)
    art = candidate(contract)
    art["scenes"][0]["image"][field] = value
    with pytest.raises(ValueError):
        validate_art_style(art, {"characters": []}, contract)


def test_style_and_adapter_pin_must_match():
    contract = freeze_art_style("live-action", None)
    art = candidate(contract)
    art["style"] = "realistic"
    with pytest.raises(ValueError, match="frozen author-selected"):
        validate_art_style(art, {"characters": []}, contract)
    art = candidate(contract)
    contract["adapterHash"] = "0" * 64
    assert not art_style_current(contract, None)
    with pytest.raises(ValueError, match="stale"):
        validate_art_style(art, {"characters": []}, contract)
    with pytest.raises(ValueError, match="not frozen"):
        validate_art_style(art, {"characters": []}, None)
    with pytest.raises(ValueError, match="supported"):
        freeze_art_style("unknown", None)


@pytest.mark.parametrize("style,conflict", [
    ("live-action", "painterly"), ("realistic", "anime"), ("ghibli", "live-action"),
])
def test_every_style_requires_matching_positive_prompts(style, conflict):
    contract = freeze_art_style(style, None)
    art = candidate(contract)
    art["scenes"][0]["image"]["prompt"] += ", " + conflict
    with pytest.raises(ValueError, match="conflict"):
        validate_art_style(art, {"characters": []}, contract)
    art["scenes"][0]["image"]["prompt"] = "empty room"
    with pytest.raises(ValueError, match="selected render"):
        validate_art_style(art, {"characters": []}, contract)


def test_stale_prepared_task_cannot_send_or_admit_and_retains_evidence(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _prepare_art_context(store)
        prepared, request = store.prepare_art_candidate("ch_" + "v" * 32, render_style="live-action")
        contract = request.input_artifacts["art-style-contract.json"]
        delivery = _deliver_stage(store, request, "art.json", candidate(contract), "before-direction-change")
        paths = store.creative_handoff_exchange().verified_package_paths(request, store.creative_handoff_execution_pin(request))
        artifact = Path(paths["deliveryPath"]) / "art.json"
        original = artifact.read_bytes()
        current = store.project()
        store.update_brief(current.brief.model_copy(update={"visual_style": "new direction"}), expected_revision=current.revision)
        assert store.art_state().status == "stale"
        client = TestClient(create_project_folder_authoring_app(storage))
        response = client.post(f"/api/v2/projects/{store.manifest.project_id}/specialist-tasks/art/{prepared.job_id}/send")
        assert response.status_code == 409
        assert "过期" in response.text
        with pytest.raises(CreativeHandoffError, match="stale"):
            store.admit_art_delivery(delivery)
        store.cancel_art_candidate(prepared.job_id)
        assert artifact.read_bytes() == original
        assert store.art_state().candidate is None
    finally:
        store.close()


def test_live_action_props_keep_style_scale_and_white_background_gates():
    contract = freeze_art_style("live-action", None)
    art = candidate(contract)
    art["props"] = [{
        "id": "P01", "name": "手机", "summary": "Receives the message",
        "scale": "手持级", "relatedScenes": ["S01"],
        "anchors": [{"name": name, "desc": desc} for name, desc in [
            ("外壳", "black shell"), ("屏幕", "dark screen"), ("边缘", "rounded edge")]],
        "states": [{"state": "idle", "prompt": "dark idle screen"}],
        "image": {
            "prompt": contract["preset"]["render"] + ", handheld scale",
            "sheet": contract["preset"]["render"] + ", handheld scale, white background",
            "negativePrompt": contract["preset"]["negative"] + ", hands",
            "tags": ["photographic"],
        },
    }]
    validate_art_style(art, {"characters": []}, contract)
    for field, value in [("sheet", contract["preset"]["render"] + ", handheld scale"),
                         ("negativePrompt", contract["preset"]["negative"]),
                         ("tags", ["painterly"])]:
        changed = deepcopy(art)
        changed["props"][0]["image"][field] = value
        with pytest.raises(ValueError):
            validate_art_style(changed, {"characters": []}, contract)


@pytest.mark.parametrize("cast", [{"characters": []}, {"characters": [{"name": "Lin", "aliases": ["KeeperAlias"]}]}])
def test_report_uses_original_live_action_document_and_cast_context(tmp_path, cast):
    contract = freeze_art_style("live-action", "写实电影感")
    art = candidate(contract)
    for name, doc in (("art", art), ("cast", cast), ("contract", contract)):
        (tmp_path / f"{name}.json").write_text(json.dumps(doc))
    original = (tmp_path / "art.json").read_bytes()
    result = subprocess.run(["node", str(ADAPTER), "render", str(tmp_path / "art.json"),
                             "--cast", str(tmp_path / "cast.json"),
                             "--contract", str(tmp_path / "contract.json"), "--html"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "真人写实" in result.stdout
    assert contract["preset"]["render"] in result.stdout
    assert "painterly rendering with visible brush texture" not in result.stdout
    assert "未提供 cast.json" not in result.stdout
    assert "gatepill pass" in result.stdout
    embedded = re.search(r'id="art-data">([\s\S]*?)</script>', result.stdout)
    assert embedded is not None
    assert json.loads(embedded.group(1)) == art
    assert json.loads((tmp_path / "art.json").read_text()) == art
    assert (tmp_path / "art.json").read_bytes() == original


@pytest.mark.parametrize("field", ["prompt", "sheet", "lighting"])
def test_report_refuses_cast_contamination_without_rewriting_candidate(tmp_path, field):
    contract = freeze_art_style("live-action", None)
    art = candidate(contract)
    cast = {"characters": [{"name": "CastPerson", "aliases": ["CastAlias"]}]}
    if field == "lighting":
        art["scenes"][0]["lighting"][0]["prompt"] += ", CastAlias"
    else:
        art["scenes"][0]["image"][field] += ", CastPerson"
    for name, doc in (("art", art), ("cast", cast), ("contract", contract)):
        (tmp_path / f"{name}.json").write_text(json.dumps(doc))
    original = (tmp_path / "art.json").read_bytes()
    result = subprocess.run(["node", str(ADAPTER), "render", str(tmp_path / "art.json"),
                             "--cast", str(tmp_path / "cast.json"),
                             "--contract", str(tmp_path / "contract.json"), "--html"],
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert "提示词不含角色名" in result.stderr
    assert not result.stdout
    assert (tmp_path / "art.json").read_bytes() == original


def test_live_action_api_delivery_accept_save_and_staleness(tmp_path: Path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"visual_style": "雨后真人写实"}))
    try:
        _prepare_art_context(store)
        client = TestClient(create_project_folder_authoring_app(storage))
        url = f"/api/v2/projects/{store.manifest.project_id}/art/candidates"
        assert client.post(url).status_code == 422
        assert client.post(url, json={"renderStyle": "unknown"}).status_code == 422
        response = client.post(url, json={"renderStyle": "live-action"})
        assert response.status_code == 201, response.text
        job_id = response.json()["jobId"]
        request = store.art_candidate_request(job_id)
        contract = request.input_artifacts["art-style-contract.json"]
        assert contract["authorDirection"] == "雨后真人写实"
        assert response.json()["binding"]["renderContract"] == contract
        art = candidate(contract)
        art["sectionUsage"] = [{"sectionId": section, "sceneIds": ["S01"], "propIds": []} for section in response.json()["binding"]["sectionIds"]]
        delivery = _deliver_stage(store, request, "art.json", art, "live-action-fixture")
        invalid = deepcopy(art)
        invalid["scenes"][0]["image"]["tags"] = ["painterly"]
        with pytest.raises(ValueError, match="conflict"):
            store.admit_art_delivery(replace(delivery, candidate=invalid))
        ready = store.admit_art_delivery(delivery)
        with pytest.raises(ValueError, match="conflict"):
            store.accept_art_candidate(ArtAcceptRequest(job_id=job_id, expected_art_revision=0, binding=ready.binding, art=invalid))
        accepted = store.accept_art_candidate(ArtAcceptRequest(job_id=job_id, expected_art_revision=0, binding=ready.binding))
        assert accepted.accepted_art.art["style"] == "live-action"
        store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        with pytest.raises(ValueError, match="conflict"):
            store.save_reopened_art(ArtSaveRequest(expected_art_revision=1, binding=ready.binding, art=invalid))
        store.save_reopened_art(ArtSaveRequest(expected_art_revision=1, binding=ready.binding, art=art))
        current = store.project()
        store.update_brief(current.brief.model_copy(update={"visual_style": "吉卜力动画"}), expected_revision=current.revision)
        assert store.art_state().status == "stale"
        with pytest.raises(ReviewContextError):
            store.reopen_art(ArtReopenRequest(expected_art_revision=2))
        assert store.art_state().accepted_review_state.status == "retained"
        assert store.art_state().accepted_art.revision == 2
        with pytest.raises(InvalidTransitionError, match="reopen accepted art"):
            store.save_reopened_art(ArtSaveRequest(expected_art_revision=2, binding=ready.binding, art=art))
    finally:
        store.close()
