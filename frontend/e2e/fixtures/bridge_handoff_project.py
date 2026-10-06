"""Seed an isolated, contract-valid bridge for real-browser handoff checks."""

from __future__ import annotations

import argparse
from pathlib import Path

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest, ProductionBridgeIntentUpdateRequest
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.script_contracts import ScriptReopenRequest, ScriptSectionSaveRequest
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.test_production_bridge import _prepare_installable_bridge, _review_fixture_presentation, _source_shaped_review_board
from tests.test_project_storage_art import _accepted_f4_script, _deliver_stage


def repeated_scene_bridge(store, seconds):
    """Two S01 occurrences through real current admission, never a bypass."""
    _accepted_f4_script(store)
    accepted = store.script_state().accepted_script
    episode = dict(accepted.script["episodes"][0])
    scene = episode["scenes"][0]
    episode["scenes"] = [{**scene, "flow": scene["flow"][:4]}, {**scene, "flow": scene["flow"][4:]}]
    store.reopen_script(ScriptReopenRequest(expected_script_revision=accepted.revision))
    store.save_script_section(ScriptSectionSaveRequest(expected_script_revision=accepted.revision, binding=accepted.binding, section_id="opening", episode=episode))
    candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32)
    board = _source_shaped_review_board(seconds, [item.episode for item in candidate.binding.section_bindings])
    second = board["episodes"][0]["segments"][1]
    second["sceneIndex"] = 2
    for cut in second["cuts"]:
        cut["beats"] = [value - 4 for value in cut["beats"]]
    ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", board, "creator-multiple-scenes"))
    store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
    proposal = _review_fixture_presentation(store, store.prepare_production_bridge().proposal)
    proposal = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(
        expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash,
        entries=[{"id": entry.id, "text": f"作者明确的戏剧目的：{entry.id}"} for entry in proposal.intent_package.entries],
    )).proposal
    assert proposal.installable and len(proposal.scenes) == 4
    return proposal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--application", type=Path, required=True)
    parser.add_argument("--pending", action="store_true", help="Prepare a new unreviewed proposal without installation")
    parser.add_argument("--seconds", type=float, default=3, help="Exact source cut duration for this disposable fixture")
    parser.add_argument("--repeat-scenes", action="store_true")
    args = parser.parse_args()
    storage = ProjectFolderStorage(outputs_root=args.outputs, application_data_root=args.application)
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shot_count_policy": "advisory"}))
    try:
        proposal = repeated_scene_bridge(store, args.seconds) if args.repeat_scenes else _prepare_installable_bridge(store, seconds=args.seconds)
        if args.pending:
            store.prepare_production_bridge()
        else:
            accepted = store.accept_production_bridge(ProductionBridgeAcceptRequest(
                expected_proposal_revision=proposal.revision,
                expected_content_hash=proposal.content_hash,
            ))
            assert accepted.status == "accepted"
        print(store.manifest.project_id)
    finally:
        store.close()


if __name__ == "__main__":
    main()
