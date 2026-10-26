"""Opt-in F4 necessary constraints; retained bytes are immutable test input."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from plotloom.art_contracts import ArtAcceptRequest
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.script_dialogue_compatibility import assert_planned_dialogue_necessary_bounds, freeze_planned_storyboard_dialogue
from tests.art_delivery_fixtures import _deliver
from tests.creative_delivery_fixtures import _deliver_stage, _pilot_script, _prepare_art_context

RETAINED = Path(__file__).parent / "fixtures/script-dialogue/retained-overlong-vo.json"


@pytest.fixture
def script_store(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"target_playthrough_seconds": 20}))
    try:
        _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate("ch_" + "p" * 32, render_style="realistic")
        ready = store.admit_art_delivery(_deliver(store, request))
        store.accept_art_candidate(ArtAcceptRequest(job_id=candidate.job_id, expected_art_revision=0,
            binding=candidate.binding, art=ready.art))
        yield store
    finally:
        store.close()


def test_opted_in_f4_exposes_trusted_requirement_before_model_work(script_store):
    retained = json.loads(RETAINED.read_bytes())
    line = retained["episodes"][0]["scenes"][0]["flow"][1]["line"]
    assert len(line) == 27 and len(line) * 330 == 8910
    candidate, request = script_store.prepare_script_candidate("ch_" + "r" * 32,
        planned_storyboard_max_cut_seconds=8)
    planned = candidate.binding.planned_storyboard_dialogue
    assert planned.language == "zh-CN" and planned.max_cut_seconds == 8
    assert planned.profile.version == "dialogue.default.v1"
    assert request.input_artifacts["script-admission.json"]["plannedStoryboardDialogue"] == planned.model_dump(mode="json", by_alias=True)
    assert "necessary" in request.creative_brief and "canonical" in request.creative_brief


def test_bodyless_f4_preserves_unbound_manual_intent(script_store):
    candidate, request = script_store.prepare_script_candidate("ch_" + "s" * 32)
    assert candidate.binding.model_dump(mode="json", by_alias=True).get("plannedStoryboardDialogue") is None
    assert "plannedStoryboardDialogue" not in request.input_artifacts["script-admission.json"]


def check_bounds(script, *, maximum=8, language="zh-CN", target=20):
    mapping = {item["sectionId"]: item["episode"] for item in script["sectionBindings"]}
    admission = json.loads((RETAINED.parent / "retained-admission.json").read_bytes())
    assert_planned_dialogue_necessary_bounds(script,
        planned=freeze_planned_storyboard_dialogue(max_cut_seconds=maximum, language=language),
        section_episodes=mapping, routes=admission["completeRouteSectionIds"],
        route_only=admission["routeOnlySectionIds"], maximum_seconds=target)


def test_exact_retained_vo_is_rejected_by_planned_eight_second_receiving():
    import hashlib
    assert hashlib.sha256(RETAINED.read_bytes()).hexdigest() == "7b7d56187b411a10f9468a059beb50dcdb378452b151b1e613a7ee3b97be919a"
    script = json.loads(RETAINED.read_bytes())
    with pytest.raises(ValueError, match="planned storyboard maximum"):
        check_bounds(script)
    check_bounds(script, maximum=15)


@pytest.mark.parametrize("length,delivery,limit,valid", [
    (24, "free-form note", 8, True), (25, "free-form note", 8, False),
    (20, "measured", 8, False), (19, "measured", 8, True),
    (30, "brisk", 8, True), (31, "brisk", 8, False),
])
def test_exact_normalized_pace_boundaries(length, delivery, limit, valid):
    script = json.loads(RETAINED.read_bytes())
    for episode in script["episodes"]:
        for scene in episode["scenes"]:
            for flow in scene["flow"]:
                if "line" in flow:
                    flow["line"] = "字" if episode["ep"] != 1 else "字" * length
                    flow["delivery"] = delivery
    if valid:
        check_bounds(script, maximum=limit)
    else:
        with pytest.raises(ValueError, match="planned storyboard maximum"):
            check_bounds(script, maximum=limit)


@pytest.mark.parametrize("speaker", ["VO", "C01"])
def test_language_unicode_internal_whitespace_and_report_language_are_separate(speaker):
    script = json.loads(RETAINED.read_bytes())
    first = script["episodes"][0]["scenes"][0]["flow"][1]
    first.update(speaker=speaker, line="  " + "字" * 23 + " 😀  ", delivery="quietly")
    # 25 stripped codepoints including internal space and a non-BMP character.
    assert len(first["line"].strip()) == 25
    script["lang"] = "en"
    with pytest.raises(ValueError, match="planned storyboard maximum"):
        check_bounds(script)
    script["lang"] = "zh"
    check_bounds(script, language="en")


def test_individually_fitting_lines_can_exceed_complete_route_lower_bound():
    script = json.loads(RETAINED.read_bytes())
    scene = script["episodes"][0]["scenes"][0]
    scene["flow"] = [{"speaker": "VO", "line": "字" * 24} for _ in range(3)]
    with pytest.raises(ValueError, match="lower bound exceeds"):
        check_bounds(script)


@pytest.mark.parametrize("value", [1, 16, 8.5, True, "8"])
def test_public_f4_requirement_rejects_invalid_selected_maximum(value):
    from pydantic import ValidationError
    from plotloom.script_contracts import ScriptPrepareRequest
    with pytest.raises(ValidationError):
        ScriptPrepareRequest.model_validate({"plannedStoryboardMaxCutSeconds": value})


@pytest.mark.parametrize("value", [None, 2, 15])
def test_public_optional_prepare_body_uses_shared_owner(script_store, value):
    from contextlib import contextmanager
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from plotloom.api.project_folder_script import register_project_folder_script_routes
    @contextmanager
    def opened(project_id):
        assert project_id == script_store.manifest.project_id
        yield script_store
    app = FastAPI()
    register_project_folder_script_routes(app, opened)
    with TestClient(app) as client:
        kwargs = {} if value is None else {"json": {"plannedStoryboardMaxCutSeconds": value}}
        response = client.post(f"/api/v2/projects/{script_store.manifest.project_id}/script/candidates", **kwargs)
    assert response.status_code == 201, response.text
    planned = response.json()["binding"].get("plannedStoryboardDialogue")
    assert (planned["maxCutSeconds"] if planned else None) == value


def test_currentness_retains_selected_limit_and_detects_profile_drift(script_store, monkeypatch):
    import plotloom.canonical_schema as schema
    candidate, _request = script_store.prepare_script_candidate("ch_" + "t" * 32, planned_storyboard_max_cut_seconds=15)
    assert script_store.script_state().status == "prepared"
    assert script_store.script_state().candidate.binding == candidate.binding
    monkeypatch.setattr(schema, "DEFAULT_DIALOGUE_TIMING_PROFILE", schema.DEFAULT_DIALOGUE_TIMING_PROFILE.model_copy(update={"version": "changed-profile"}))
    state = script_store.script_state()
    assert state.status == "stale"
    assert any(reason.field == "planned_storyboard_dialogue" for reason in state.stale_reasons)


def dialogue_script(request, *, opening_line="灯亮了，沿这边走。"):
    script = _pilot_script()
    script["lang"] = "en"
    script["sectionBindings"] = request.input_artifacts["script-admission.json"]["sectionBindings"]
    for episode in script["episodes"]:
        line = opening_line if episode["ep"] == 1 else "灯亮了，沿这边走。"
        episode["targetSeconds"] = 2.5 + round(len(line) / 4.5, 1)
        episode["scenes"][0]["flow"] = [{"action": "Lin checks the doorway."},
            {"speaker": "VO", "line": line, "delivery": "quiet performance note"}]
    return script


def ready_script(store, maximum=8):
    kwargs = {} if maximum is None else {"planned_storyboard_max_cut_seconds": maximum}
    candidate, request = store.prepare_script_candidate("ch_" + "u" * 32, **kwargs)
    delivery = _deliver_stage(store, request, "script.json", dialogue_script(request), "planned-script-fixture")
    ready = store.admit_script_delivery(delivery)
    return candidate, request, delivery, ready


def accept_ready(store, ready):
    from plotloom.script_contracts import ScriptAcceptRequest
    return store.accept_script_candidate(ScriptAcceptRequest(job_id=ready.job_id,
        expected_script_revision=0, binding=ready.binding))


def test_project_admission_rejects_retained_line_before_canonical_adoption(script_store):
    candidate, request = script_store.prepare_script_candidate("ch_" + "v" * 32, planned_storyboard_max_cut_seconds=8)
    line = json.loads(RETAINED.read_bytes())["episodes"][0]["scenes"][0]["flow"][1]["line"]
    delivery = _deliver_stage(script_store, request, "script.json", dialogue_script(request, opening_line=line), "overlong-vo-fixture")
    with pytest.raises(ValueError, match="planned storyboard maximum"):
        script_store.admit_script_delivery(delivery)
    state = script_store.script_state()
    assert state.accepted_script is None and state.candidate.job_id == candidate.job_id


@pytest.mark.parametrize("original,forged", [(None, 8), (8, None), (8, 15)])
def test_accept_cannot_rebind_exact_stored_optional_selection(script_store, original, forged):
    from plotloom.script_contracts import ScriptAcceptRequest
    _candidate, _request, _delivery, ready = ready_script(script_store, original)
    replacement = freeze_planned_storyboard_dialogue(max_cut_seconds=forged, language="zh-CN") if forged is not None else None
    changed = ready.binding.model_copy(update={"planned_storyboard_dialogue": replacement})
    with pytest.raises(ValueError, match="context changed"):
        script_store.accept_script_candidate(ScriptAcceptRequest(job_id=ready.job_id,
            expected_script_revision=0, binding=changed))
    assert script_store.script_state().accepted_script is None


@pytest.mark.parametrize("drift", ["language", "profile-rules"])
def test_ready_read_and_repeat_admit_recompute_current_language_and_rules(script_store, monkeypatch, drift):
    import plotloom.canonical_schema as schema
    _candidate, _request, delivery, _ready = ready_script(script_store)
    if drift == "language":
        project = script_store.project()
        script_store.update_brief(project.brief.model_copy(update={"language": "en"}), expected_revision=project.revision)
    else:
        profile = schema.DEFAULT_DIALOGUE_TIMING_PROFILE.model_copy(deep=True)
        profile.rules[1] = profile.rules[1].model_copy(update={"units_per_character": 331})
        monkeypatch.setattr(schema, "DEFAULT_DIALOGUE_TIMING_PROFILE", profile)
    assert script_store.script_state().status == "stale"
    with pytest.raises(ValueError, match="context is stale"):
        script_store.admit_script_delivery(delivery)


def test_bound_edit_retains_requirement_and_rejects_new_unfit_line(script_store):
    from plotloom.script_contracts import ScriptReopenRequest, ScriptSectionSaveRequest
    _candidate, _request, _delivery, ready = ready_script(script_store)
    accepted = accept_ready(script_store, ready).accepted_script
    assert accepted.binding.planned_storyboard_dialogue.max_cut_seconds == 8
    script_store.reopen_script(ScriptReopenRequest(expected_script_revision=1))
    episode = deepcopy(accepted.script["episodes"][0])
    episode["scenes"][0]["flow"][1]["line"] = json.loads(RETAINED.read_bytes())["episodes"][0]["scenes"][0]["flow"][1]["line"]
    episode["targetSeconds"] = 8.5
    with pytest.raises(ValueError, match="planned storyboard maximum"):
        script_store.save_script_section(ScriptSectionSaveRequest(expected_script_revision=1,
            binding=accepted.binding, section_id="opening", episode=episode))
    assert script_store.script_state().accepted_script.revision == 1


def test_f5_keeps_inherited_selection_separate_from_actual_public_choice(script_store):
    from plotloom.script_contracts import ScriptAcceptRequest
    candidate, request = script_store.prepare_script_candidate("ch_" + "x" * 32, planned_storyboard_max_cut_seconds=15)
    line = json.loads(RETAINED.read_bytes())["episodes"][0]["scenes"][0]["flow"][1]["line"]
    ready = script_store.admit_script_delivery(_deliver_stage(script_store, request, "script.json",
        dialogue_script(request, opening_line=line), "fifteen-second-intent"))
    script_store.accept_script_candidate(ScriptAcceptRequest(job_id=candidate.job_id, expected_script_revision=0, binding=ready.binding))
    with pytest.raises(ValueError, match="chosen F5 maximum"):
        script_store.prepare_storyboard_review_candidate("ch_" + "y" * 32, max_cut_seconds=8)
    board, board_request = script_store.prepare_storyboard_review_candidate("ch_" + "9" * 32, max_cut_seconds=15)
    assert board.binding.planned_storyboard_dialogue.max_cut_seconds == 15
    assert board.binding.review_max_cut_seconds == 15
    assert board_request.input_artifacts["dialogue-timing-contract.json"]["lines"][0]["minimumDurationUnits"] == 8910
    assert script_store.storyboard_review_state().status == "prepared"


@pytest.mark.parametrize("boundary", ["accept", "reopen", "save"])
def test_profile_drift_refuses_every_mutating_review_boundary(script_store, monkeypatch, boundary):
    import plotloom.canonical_schema as schema
    from plotloom.review_context_diagnostics import ReviewContextError
    from plotloom.script_contracts import ScriptAcceptRequest, ScriptReopenRequest, ScriptSectionSaveRequest
    _candidate, _request, _delivery, ready = ready_script(script_store)
    if boundary != "accept":
        accepted = accept_ready(script_store, ready).accepted_script
        if boundary == "save":
            script_store.reopen_script(ScriptReopenRequest(expected_script_revision=1))
    monkeypatch.setattr(schema, "DEFAULT_DIALOGUE_TIMING_PROFILE",
        schema.DEFAULT_DIALOGUE_TIMING_PROFILE.model_copy(update={"version": "new-profile"}))
    expected_error = ReviewContextError if boundary == "reopen" else ValueError
    with pytest.raises(expected_error, match="context|changed"):
        if boundary == "accept":
            script_store.accept_script_candidate(ScriptAcceptRequest(job_id=ready.job_id,
                expected_script_revision=0, binding=ready.binding))
        elif boundary == "reopen":
            script_store.reopen_script(ScriptReopenRequest(expected_script_revision=1))
        else:
            script_store.save_script_section(ScriptSectionSaveRequest(expected_script_revision=1,
                binding=accepted.binding, section_id="opening", episode=accepted.script["episodes"][0]))


def test_autopilot_explicitly_uses_one_f5_default_for_both_preparations(script_store, monkeypatch):
    from types import SimpleNamespace
    from plotloom.autopilot_text_stages import prepare_text
    from plotloom.storyboard_review_contracts import DEFAULT_STORYBOARD_MAX_CUT_SECONDS
    observed = []
    def prepare(job_id, **options):
        observed.append(options)
        return None, job_id
    monkeypatch.setattr(script_store, "prepare_script_candidate", prepare)
    monkeypatch.setattr(script_store, "prepare_storyboard_review_candidate", prepare)
    policy = SimpleNamespace(effective_style_authority="brief")
    prepare_text(script_store, "script", policy)
    prepare_text(script_store, "storyboard", policy)
    assert observed == [{"planned_storyboard_max_cut_seconds": DEFAULT_STORYBOARD_MAX_CUT_SECONDS},
        {"max_cut_seconds": DEFAULT_STORYBOARD_MAX_CUT_SECONDS}]
