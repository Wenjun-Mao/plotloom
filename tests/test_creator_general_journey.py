"""General Source topology reaches every existing downstream contract."""
from copy import deepcopy
import json
from pathlib import Path
from plotloom.art_contracts import ArtAcceptRequest
from plotloom.cast_contracts import CastAcceptRequest, CastConsumerMapping
from plotloom.script_contracts import ScriptAcceptRequest
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest, ProductionBridgeIntentUpdateRequest
from plotloom.source_outline_contracts import SectionMapGraphInstallRequest
from tests.test_creator_branch_suggestions import store, prepare, proposal, save_map
from tests.test_project_storage_art import _deliver_stage, _pilot_script
from tests.test_production_bridge import _source_shaped_review_board, _review_fixture_presentation

FIXTURES = Path(__file__).parents[1] / "frontend/e2e/fixtures/f5a"


def test_general_structure_reaches_script_storyboard_and_installed_production(store):
    project = store.project()
    store.update_brief(project.brief.model_copy(update={"target_playthrough_seconds": 180}), expected_revision=project.revision)
    branch = prepare(store)
    store.admit_branch_delivery(_deliver_stage(store, branch, "branches.json", proposal(branch.source["topology"]), "general-branches"))
    saved = save_map(store, store.branch_draft(branch.job_id))
    source, outline, mapping = saved.source, saved.accepted_outline, saved.accepted_section_map
    store.install_section_map_graph(SectionMapGraphInstallRequest(expected_source_revision=source.revision, expected_source_content_hash=source.content_hash,
        expected_outline_revision=outline.revision, expected_outline_content_hash=outline.content_hash, expected_section_map_revision=mapping.revision,
        expected_section_map_content_hash=mapping.content_hash, expected_graph_revision=0))
    candidate, request = store.prepare_cast_candidate("ch_" + "c" * 32)
    cast = json.loads((FIXTURES / "cast.json").read_text())
    ready = store.admit_cast_delivery(_deliver_stage(store, request, "cast.json", cast, "general-cast"))
    store.accept_cast_candidate(CastAcceptRequest(job_id=candidate.job_id, expected_cast_revision=0, binding=ready.binding,
        consumer_mappings=[CastConsumerMapping(cast_character_id=item["id"], consumer_character_id=item["id"]) for item in cast["characters"]]))
    candidate, request = store.prepare_art_candidate("ch_" + "g" * 32, render_style="realistic")
    art = json.loads((FIXTURES / "art.json").read_text())
    art["sectionUsage"] = [{"sectionId": section, "sceneIds": ["S01"], "propIds": []} for section in candidate.binding.section_ids]
    ready = store.admit_art_delivery(_deliver_stage(store, request, "art.json", art, "general-art"))
    store.accept_art_candidate(ArtAcceptRequest(job_id=candidate.job_id, expected_art_revision=0, binding=ready.binding, art=ready.art))
    candidate, request = store.prepare_script_candidate("ch_" + "s" * 32)
    binding = candidate.binding
    assert len(binding.section_bindings) == 9 and len(binding.complete_route_section_ids) == 6
    assert len(request.input_artifacts["outline.json"]["episodes"]) == 9
    script = _pilot_script()
    script["sectionBindings"] = [item.model_dump(mode="json", by_alias=True) for item in binding.section_bindings]
    script["episodes"] = [dict(deepcopy(script["episodes"][0]), ep=item.episode) for item in binding.section_bindings]
    ready = store.admit_script_delivery(_deliver_stage(store, request, "script.json", script, "general-script"))
    store.accept_script_candidate(ScriptAcceptRequest(job_id=candidate.job_id, expected_script_revision=0, binding=ready.binding, script=ready.script))
    candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32)
    board = _source_shaped_review_board()
    episode = deepcopy(board["episodes"][0])
    board["episodes"] = []
    for item in binding.section_bindings:
        current = dict(deepcopy(episode), ep=item.episode)
        for index, segment in enumerate(current["segments"], 1):
            segment["id"] = f"E{item.episode:02}-{index:02}"
        board["episodes"].append(current)
    ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", board, "general-storyboard"))
    store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
    proposed = store.prepare_production_bridge().proposal
    assert len(proposed.presentation.runtime_choice["choices"]) == 2
    proposed = _review_fixture_presentation(store, proposed)
    proposed = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(expected_proposal_revision=proposed.revision,
        expected_content_hash=proposed.content_hash, entries=[{"id": item.id, "text": "Reviewed dramatic purpose."} for item in proposed.intent_package.entries])).proposal
    assert proposed.installable, proposed.conflicts
    accepted = store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposed.revision, expected_content_hash=proposed.content_hash))
    assert accepted.installed_storyboard_current
    assert len(accepted.runtime_choice["choices"]) == 2
    assert sorted(len(choice["outcomes"]) for choice in accepted.runtime_choice["choices"]) == [2, 3]
