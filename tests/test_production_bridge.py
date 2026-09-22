from __future__ import annotations

from pathlib import Path

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.production_bridge_contracts import ProductionBridgeAcceptRequest
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from plotloom.persistence.project.storyboard_review import ProjectStoryboardReviewPersistence
from tests.test_project_storage_art import _accepted_f4_script, _deliver_stage


def test_bridge_projects_one_f4_scene_to_one_canonical_scene_and_installs_atomically(tmp_path: Path, monkeypatch) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"shots_per_scene_min": 1, "shots_per_scene_max": 1}))
    try:
        _accepted_f4_script(store)
        monkeypatch.setattr(ProjectStoryboardReviewPersistence, "_validate", staticmethod(lambda *_args: None))
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32)
        board = {"params": {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}, "episodes": [
            {"ep": episode, "segments": [{"sceneIndex": 1, "cuts": [{"seconds": 3, "beats": [1, 10], "frame": {"size": "medium", "description": "accepted frame", "camera": "static"}}]}]}
            for episode in (1, 2, 3)
        ]}
        ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", board, "bridge-fixture"))
        store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
        proposal = store.prepare_production_bridge().proposal
        assert proposal and proposal.installable and len(proposal.scenes) == len(proposal.cuts) == 3
        accepted = store.accept_production_bridge(ProductionBridgeAcceptRequest(expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash))
        assert accepted.status == "accepted"
        assert accepted.installed_stage_revisions == {"story_bible": 1, "scene_beats": 1, "storyboard": 1}
    finally:
        store.close()


def test_bridge_surfaces_brief_policy_conflict_without_splitting_source_scene(tmp_path: Path, monkeypatch) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        monkeypatch.setattr(ProjectStoryboardReviewPersistence, "_validate", staticmethod(lambda *_args: None))
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "d" * 31 + "1")
        cuts = [{"seconds": 3, "beats": [1, 10], "frame": {"size": "medium", "description": "frame", "camera": "static"}} for _ in range(5)]
        board = {"params": {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}, "episodes": [{"ep": episode, "segments": [{"sceneIndex": 1, "cuts": cuts}]} for episode in (1, 2, 3)]}
        ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", board, "bridge-conflict"))
        store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
        proposal = store.prepare_production_bridge().proposal
        assert proposal and not proposal.installable
        assert len(proposal.scenes) == 3 and len(proposal.cuts) == 15
        assert proposal.conflicts[0].message == "不能安装：源场次有 5 个镜头，当前项目规则为 1–4 个"
    finally:
        store.close()
