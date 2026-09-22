from __future__ import annotations

from pathlib import Path

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest, ProductionBridgeIntentUpdateRequest
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.test_project_storage_art import _accepted_f4_script, _deliver_stage


def _source_shaped_review_board() -> dict[str, object]:
    """Pass the pinned upstream validator; no review-validation bypass is used."""

    def segment(ep: int, segment_index: int, beat_ranges: list[list[int]]) -> dict[str, object]:
        cuts = [{"seconds": 3, "beats": beat_range, "size": "medium", "camera": "Static Shot", "characters": [], "props": [], "frame": "medium shot of an empty beacon room at dawn, cinematic film still, cool gray palette, 16:9"} for beat_range in beat_ranges]
        starts = list(range(0, len(cuts) * 3, 3))
        align = "; ".join(f"Picture {index} (from Shot {index}) aligns with the {start:.2f}-second mark of the target video" for index, start in enumerate(starts, 1)) + "."
        shots = "\n".join(f"[Shot {index}] Cinematic, live-action, cool gray palette. The empty beacon room of <Picture {index}> holds while the camera uses a static shot." if index == 1 else f"[Shot {index}] At 00:{starts[index - 1]:02}.000, the camera cuts to <Picture {index}> and holds a static shot in the empty beacon room." for index in range(1, len(cuts) + 1))
        return {"id": f"E{ep:02}-{segment_index:02}", "sceneIndex": 1, "cuts": cuts, "h3Prompt": f"How the reference pictures align with the target video — {align}\n\nintegrated_multimodal_description:\n{shots}\n\noverall_soundscape: Quiet wind around an empty beacon room.\n\nnon_diegetic_music: N/A"}

    return {"source": "Tide Light", "params": {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}, "episodes": [{"ep": ep, "segments": [segment(ep, 1, [[1, 1], [2, 2], [3, 3], [4, 4]]), segment(ep, 2, [[5, 5], [6, 6], [7, 7], [8, 8], [9, 10]])]} for ep in (1, 2, 3)]}


def test_bridge_projects_one_f4_scene_to_one_canonical_scene_and_installs_atomically(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 9, "shots_per_scene_max": 9}))
    try:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32)
        board = _source_shaped_review_board()
        ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", board, "bridge-fixture"))
        store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
        proposal = store.prepare_production_bridge().proposal
        assert proposal and proposal.installable and len(proposal.scenes) == 3 and len(proposal.cuts) == 27
        updates = [{"id": entry.id, "text": "作者复核后的戏剧目标" if entry.target_kind == "scene_objective" else entry.text} for entry in proposal.intent_package.entries]
        revised = store.update_production_bridge_intent_package(ProductionBridgeIntentUpdateRequest(expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash, entries=updates)).proposal
        assert revised and revised.revision == proposal.revision + 1 and revised.intent_package.entries[0].text
        accepted = store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=revised.revision, expected_content_hash=revised.content_hash))
        assert accepted.status == "accepted"
        assert accepted.installed_stage_revisions == {"story_bible": 1, "scene_beats": 1, "storyboard": 1}
    finally:
        store.close()


def test_bridge_surfaces_brief_policy_conflict_without_splitting_source_scene(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "d" * 31 + "1")
        board = _source_shaped_review_board()
        ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", board, "bridge-conflict"))
        store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
        proposal = store.prepare_production_bridge().proposal
        assert proposal and not proposal.installable
        assert len(proposal.scenes) == 3 and len(proposal.cuts) == 27
        assert proposal.conflicts[0].message == "不能安装：源场次有 9 个镜头，当前项目规则为 1–4 个"
        assert proposal.cuts[4]["source"] == {"segmentIndex": 2, "segmentSceneIndex": 1, "cutIndex": 1}
    finally:
        store.close()
