"""Trusted timing gates reject raw candidate changes before upstream execution."""
import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.persistence.project.storyboard_review import ProjectStoryboardReviewPersistence
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.storyboard_review_contracts import StoryboardReviewPrepareRequest
from tests.test_project_storage_art import _accepted_f4_script


@pytest.fixture(scope="module")
def review_binding(tmp_path_factory):
    root = tmp_path_factory.mktemp("f5a-timing")
    storage = ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        candidate, _request = store.prepare_storyboard_review_candidate("ch_" + "n" * 32)
        return candidate.binding
    finally:
        store.close()


def board():
    return {"params": {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}, "episodes": [
        {"ep": ep, "segments": [{"cuts": [{"seconds": 3}]}]} for ep in (1, 2, 3)
    ]}


@pytest.mark.parametrize("seconds", [1, 9, True, None, float("nan"), float("inf")])
def test_cut_duration_uses_trusted_2_to_8_policy(review_binding, monkeypatch, seconds):
    candidate = board()
    candidate["episodes"][0]["segments"][0]["cuts"][0]["seconds"] = seconds
    monkeypatch.setattr("plotloom.persistence.project.storyboard_review.subprocess.run", lambda *a, **k: pytest.fail("local timing must reject before upstream"))
    with pytest.raises(ValueError, match="cut"):
        ProjectStoryboardReviewPersistence._validate(candidate, review_binding, {}, {}, {})


@pytest.mark.parametrize("key,value", [("minCutSeconds", 1), ("maxCutSeconds", 9), ("maxSegmentSeconds", 16)])
def test_candidate_cannot_loosen_frozen_params(review_binding, key, value):
    candidate = board()
    candidate["params"][key] = value
    with pytest.raises(ValueError, match="frozen review timing limits"):
        ProjectStoryboardReviewPersistence._validate(candidate, review_binding, {}, {}, {})


def test_segment_sum_cannot_exceed_15_seconds(review_binding):
    candidate = board()
    candidate["episodes"][0]["segments"][0]["cuts"] = [{"seconds": 8}, {"seconds": 8}]
    with pytest.raises(ValueError, match="segment duration"):
        ProjectStoryboardReviewPersistence._validate(candidate, review_binding, {}, {}, {})


def test_section_sum_cannot_exceed_frozen_cap(review_binding):
    candidate = board()
    candidate["episodes"][0]["segments"] *= 100
    with pytest.raises(ValueError, match="section duration cap"):
        ProjectStoryboardReviewPersistence._validate(candidate, review_binding, {}, {}, {})


def test_complete_route_cannot_exceed_author_maximum(review_binding):
    candidate = board()
    narrow_route = review_binding.model_copy(update={"target_playthrough_seconds": 3})
    with pytest.raises(ValueError, match="complete storyboard route"):
        ProjectStoryboardReviewPersistence._validate(candidate, narrow_route, {}, {}, {})


def test_explicit_twelve_second_review_freezes_policy_without_staling_default_eight(tmp_path, monkeypatch):
    root = tmp_path / "f5a-editorial-timing"
    storage = ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        old, _ = store.prepare_storyboard_review_candidate("ch_" + "a" * 32)
        assert old.binding.review_max_cut_seconds == 8
        store.cancel_storyboard_review_candidate(old.job_id)
        longer, request = store.prepare_storyboard_review_candidate("ch_" + "b" * 32, max_cut_seconds=12)
        assert longer.binding.review_max_cut_seconds == 12
        assert request.input_artifacts["storyboard-admission.json"]["reviewTiming"] == {
            "minCutSeconds": 2, "maxCutSeconds": 12, "maxSegmentSeconds": 15,
        }
        assert "2–12 seconds" in request.creative_brief
        assert store.storyboard_review_state().stale_reasons == []
        candidate = board()
        candidate["params"]["maxCutSeconds"] = 12
        candidate["episodes"][0]["segments"][0]["cuts"][0]["seconds"] = 12
        monkeypatch.setattr("plotloom.persistence.project.storyboard_review.subprocess.run", lambda *a, **k: type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})())
        ProjectStoryboardReviewPersistence._validate(candidate, longer.binding, {}, {}, {})
        candidate["params"]["maxCutSeconds"] = 15
        with pytest.raises(ValueError, match="frozen review timing limits"):
            ProjectStoryboardReviewPersistence._validate(candidate, longer.binding, {}, {}, {})
    finally:
        store.close()


def test_review_cut_choice_stays_within_segment_limit():
    with pytest.raises(ValueError):
        StoryboardReviewPrepareRequest(max_cut_seconds=16)
