"""F5A saved-Brief receiving, admission and source-frame propagation."""
from __future__ import annotations

from copy import deepcopy

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.stage_contracts import StageName
from plotloom.persistence.project.storyboard_review import (
    ProjectStoryboardReviewPersistence,
)
from plotloom.production_bridge_contracts import (
    ProductionBridgeAcceptRequest,
    ProductionBridgeIntentUpdateRequest,
)
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.script_contracts import ScriptReopenRequest, ScriptSectionSaveRequest
from plotloom.storyboard_brief_style import (
    CONTRACT_FILENAME,
    storyboard_brief_style_current,
)
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.creative_delivery_fixtures import (
    _accepted_f4_script,
    _deliver_stage,
    run_brief_instruction_delivery,
)
from tests.production_bridge_fixtures import (
    _review_fixture_presentation,
    _source_shaped_review_board,
)
from tests.storyboard_brief_fixtures import (
    brief_board,
    execute_example_package,
    invoke_adapter,
    real_example_request,
)


@pytest.mark.parametrize("direction", ["2D动画；手工拼贴；低饱和", None])
def test_real_upstream_commands_and_server_share_frozen_authority(tmp_path, direction):
    request, board, binding = real_example_request(direction)
    delivery = execute_example_package(tmp_path, request, board)
    inputs = request.input_artifacts
    ProjectStoryboardReviewPersistence._validate(board, binding, inputs["script.json"], inputs["outline.json"], inputs["cast.json"], request)
    assert binding.storyboard_render_contract["direction"] == direction
    assert "Saved Brief direction" in delivery.report.decode()
    assert all("cinematic film still" not in cut["frame"] for episode in board["episodes"] for segment in episode["segments"] for cut in segment["cuts"])


@pytest.mark.parametrize("change,match", [
    ("style", "identify saved Brief"), ("prompt-language", "promptLang"),
    ("marker", "风格短语"), ("frame-language", "非英文"),
    ("frame-name", "角色名"), ("size", "景别短语"),
    ("coverage", "节拍"), ("reference", "不在剧本"), ("h3", "H3"),
])
def test_saved_brief_keeps_style_membership_and_unrelated_upstream_gates(change, match):
    request, board, binding = real_example_request("2D动画；手工拼贴")
    cut = board["episodes"][0]["segments"][0]["cuts"][0]
    if change == "style": board["style"] = "realistic"
    elif change == "prompt-language": board["promptLang"] = "zh"
    elif change == "marker": cut["frame"] = cut["frame"].replace("Saved Brief direction", "cinematic film still")
    elif change == "frame-language": cut["frame"] += ", 拼贴"
    elif change == "frame-name": cut["frame"] += ", " + request.input_artifacts["cast.json"]["characters"][0]["name"]
    elif change == "size": cut["frame"] = cut["frame"].replace("medium shot", "view")
    elif change == "coverage": cut["beats"] = [2, 2]
    elif change == "reference": cut["characters"] = ["C999"]
    elif change == "h3": board["episodes"][0]["segments"][0]["h3Prompt"] = "Invalid H3 prompt"
    inputs = request.input_artifacts
    with pytest.raises(ValueError, match=match):
        ProjectStoryboardReviewPersistence._validate(board, binding, inputs["script.json"], inputs["outline.json"], inputs["cast.json"], request)


@pytest.mark.parametrize("change", ["missing", "wrong", "mutated", "adapter", "parent"])
def test_missing_wrong_or_mutated_frozen_authority_is_refused(tmp_path, change):
    request, board, binding = real_example_request("2D动画")
    contract = deepcopy(binding.storyboard_render_contract)
    if change == "missing": contract = None
    elif change == "wrong": contract["authority"] = "preset"
    elif change == "mutated": contract["direction"] = "Model-authored replacement"
    elif change == "adapter": contract["validatorHashes"]["adapter"] = "0" * 64
    elif change == "parent": contract["inheritedArtRenderContract"]["direction"] = "Replacement"
    inputs = deepcopy(request.input_artifacts)
    if contract is None: inputs.pop(CONTRACT_FILENAME)
    else: inputs[CONTRACT_FILENAME] = contract
    altered = request.model_copy(update={"input_artifacts": inputs})
    # The stored binding remains authoritative even when request metadata is forged.
    with pytest.raises(ValueError, match="authority"):
        ProjectStoryboardReviewPersistence._validate(board, binding, inputs["script.json"], inputs["outline.json"], inputs["cast.json"], altered)
    assert not storyboard_brief_style_current(contract or {}, binding.render_contract)
    assert invoke_adapter(tmp_path, altered, board).returncode != 0


def _brief_store(tmp_path, direction):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"visual_style_selections": [], "visual_style": direction or "", "shots_per_scene_min": 9, "shots_per_scene_max": 9}))
    _accepted_f4_script(store, render_style="brief")
    return storage, store


@pytest.mark.parametrize("direction", ["2D动画；手工拼贴；低饱和", None])
def test_saved_brief_f5_admission_acceptance_install_and_image_snapshot(tmp_path, direction):
    _storage, store = _brief_store(tmp_path, direction)
    project_id = store.manifest.project_id
    try:
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32)
        parent = store.art_state().accepted_art.binding.render_contract
        assert candidate.binding.render_contract == parent
        assert candidate.binding.storyboard_render_contract["direction"] == direction
        assert request.input_artifacts[CONTRACT_FILENAME] == candidate.binding.storyboard_render_contract
        historical = candidate.binding.model_copy(update={"storyboard_render_contract": None})
        prior_bytes = historical.model_dump(mode="json", by_alias=True)
        assert "storyboardRenderContract" not in prior_bytes
        owner = store.repository.storyboard_review
        with owner._access.leases.read() as session:
            current, *_ = owner.context_for_binding(session, project_id, historical)
            assert current == historical and owner._stale(session, project_id, historical) == []
        assert historical.model_validate(prior_bytes).model_dump(mode="json", by_alias=True) == prior_bytes
        assert "Run the pinned novel-storyboard validate" not in request.creative_brief
        board = brief_board(_source_shaped_review_board(), direction)
        _commands, files = run_brief_instruction_delivery(store, request, board)
        assert files == {"storyboard.json", "report.html", "completion.json"}
        exchange = store.creative_handoff_exchange()
        delivery = exchange.read_delivery(request, store.creative_handoff_execution_pin(request))
        ready = store.admit_storyboard_review_delivery(delivery)
        altered_binding = ready.binding.model_copy(update={"storyboard_render_contract": None})
        with pytest.raises(Exception, match="changed"):
            store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=altered_binding))
        accepted = store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
        assert accepted.status == "accepted" and not accepted.stale_reasons
        proposal = store.prepare_production_bridge(store.production_bridge_state().preparation.request).proposal
        proposal = _review_fixture_presentation(store, proposal)
        proposal = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(expected_proposal_revision=proposal.revision,
            expected_content_hash=proposal.content_hash, entries=[{"id": entry.id, "text": "作者确认的画面目的"} for entry in proposal.intent_package.entries])).proposal
        store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash))
        head = store.authoring.get_stage_head(project_id, StageName.STORYBOARD)
        installed = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
        frame = board["episodes"][0]["segments"][0]["cuts"][0]["frame"]
        assert installed.shots[0].composition == frame
        approval = store.authoring.decide_storyboard_approval(project_id, expected_revision=head.revision, expected_content_hash=head.content_hash,
            decision="approve", reviewer="disposable fixture", gate_set_version="storyboard.v2")
        image = store.media.prepare_image_job(project_id, approval_id=approval.id, shot_id=installed.shots[0].id, storyboard_revision=head.revision,
            presentation_change="Frozen F5 frame propagation", contract_version=3)
        composition = image["job"]["request"]["frozenSnapshot"]["visualProposal"]["composition"]
        assert composition == frame and "cinematic film still" not in composition
    finally:
        store.close()


def test_ordinary_reopen_late_delivery_and_superseded_script_keep_frozen_direction(tmp_path):
    _storage, store = _brief_store(tmp_path, "2D动画；手工拼贴")
    try:
        first, original = store.prepare_storyboard_review_candidate("ch_" + "x" * 32)
        raw = original.model_dump(mode="json", by_alias=True)
        store.cancel_storyboard_review_candidate(first.job_id)
        active, request = store.prepare_storyboard_review_candidate("ch_" + "y" * 32)
        late = _deliver_stage(store, original, "storyboard.json", brief_board(_source_shaped_review_board(), "2D动画"), "late")
        with pytest.raises(Exception, match="current prepared"):
            store.admit_storyboard_review_delivery(late)
        assert store.storyboard_review_state().stale_reasons == []
        script = store.script_state().accepted_script
        store.reopen_script(ScriptReopenRequest(expected_script_revision=script.revision))
        store.save_script_section(ScriptSectionSaveRequest(expected_script_revision=script.revision, binding=script.binding,
            section_id="opening", episode=script.script["episodes"][0]))
        assert store.storyboard_review_state().status == "stale"
        with pytest.raises(Exception, match="stale"):
            store.storyboard_review_candidate_request(active.job_id)
        store.cancel_storyboard_review_candidate(active.job_id)
        new, renewed = store.prepare_storyboard_review_candidate("ch_" + "z" * 32)
        assert new.binding.script_revision == 2
        assert new.binding.storyboard_render_contract == active.binding.storyboard_render_contract
        assert renewed.input_artifacts[CONTRACT_FILENAME] == request.input_artifacts[CONTRACT_FILENAME]
        assert original.model_dump(mode="json", by_alias=True) == raw
    finally:
        store.close()


def test_manual_binding_keeps_omitted_visual_contract_and_uses_receiving_path(tmp_path):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "m" * 32)
        assert "storyboardRenderContract" not in candidate.binding.model_dump(mode="json", by_alias=True)
        assert CONTRACT_FILENAME not in request.input_artifacts and "scripts/storyboard-receiving.mjs" in request.creative_brief
        ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", _source_shaped_review_board(), "manual"))
        state = store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
        assert state.status == "accepted" and not state.stale_reasons
    finally:
        store.close()
