from __future__ import annotations

import pytest
from pydantic import ValidationError

from plotloom.domain import CoverageRole, ProjectBrief, StoryBible, DramaticScene, Beat, SceneBeatPlan, Shot, ShotBeatLink, ShotSize, Storyboard, StoryEdge
from plotloom.validation import (
    DomainValidationError,
    validate_scene_beat_coverage,
    validate_story_graph,
    validate_storyboard_coverage,
)

from .conftest import (
    make_scene_beats,
    make_story_bible,
    make_story_graph,
    make_storyboard,
)


def test_project_brief_defaults_and_http_aliases(brief: ProjectBrief) -> None:
    payload = brief.model_dump(mode="json", by_alias=True)
    assert payload["language"] == "zh-CN"
    assert payload["aspectRatio"] == "16:9"
    assert payload["targetPlaythroughSeconds"] == 180
    assert payload["decisionPointsPerPath"] == 2
    assert payload["endingCount"] == 3
    assert payload["nodeBudget"] == 10
    assert payload["maxOutDegree"] == 3
    assert payload["desiredJoinCount"] == 1
    assert payload["shotsPerSceneMin"] == 2
    assert payload["shotsPerSceneMax"] == 4


def test_strict_schema_rejects_unknown_fields(brief: ProjectBrief) -> None:
    with pytest.raises(ValidationError):
        ProjectBrief.model_validate({**brief.model_dump(), "apiKey": "must-not-enter"})


def test_valid_default_graph_and_coverage(brief: ProjectBrief) -> None:
    bible = make_story_bible()
    graph = make_story_graph()
    plan = make_scene_beats(graph)
    storyboard = make_storyboard(plan)
    # These fixtures are explicit V2 payloads.  V1 validation intentionally
    # retains the historical source-exit join convention for persisted runs,
    # while new V2 data uses exact post-edge join-entry values.
    validate_story_graph(graph, brief, strict_v2=True)
    validate_scene_beat_coverage(plan, graph, bible, strict_v2=True)
    validate_storyboard_coverage(storyboard, plan, bible, brief)
    first_beat = plan.beats[0].model_dump(by_alias=True)
    assert "visibleEvent" in first_beat and "entryState" in first_beat
    first_shot = storyboard.shots[0].model_dump(by_alias=True)
    assert {"audioPlan", "cueIds", "requiredEntityStates", "transition", "visualIntent", "motionIntent"} <= set(first_shot)
    assert "audio" not in first_shot


def test_v1_shot_count_policy_preserves_strict_validation_without_new_review_channel() -> None:
    bible = StoryBible(logline="One choice", premise="A scene")
    plan = SceneBeatPlan(
        scenes=[DramaticScene(id="scene", story_node_id="node", title="Scene", objective="Choose", beat_ids=["beat"])],
        beats=[Beat(id="beat", scene_id="scene", order=1, description="Choose", purpose="Reveal")],
    )
    board = Storyboard(
        shots=[Shot(id=f"shot-{index}", scene_id="scene", order=index, title="View", shot_size=ShotSize.MEDIUM, duration_seconds=3) for index in range(1, 11)],
        shot_beat_links=[ShotBeatLink(shot_id="shot-1", beat_id="beat")]
        + [ShotBeatLink(shot_id=f"shot-{index}", beat_id="beat", role=CoverageRole.SUPPORTING) for index in range(2, 11)],
    )
    strict = ProjectBrief(title="x", synopsis="y", shots_per_scene_min=2, shots_per_scene_max=4)
    with pytest.raises(DomainValidationError) as captured:
        validate_storyboard_coverage(board, plan, bible, strict)
    assert {issue["code"] for issue in captured.value.issues} == {"shots_per_scene_out_of_range"}
    assert validate_storyboard_coverage(board, plan, bible, strict.model_copy(update={"shot_count_policy": "advisory"})) is None


def test_graph_cycle_is_rejected(brief: ProjectBrief) -> None:
    graph = make_story_graph()
    graph.edges.append(StoryEdge(id="cycle", source_node_id="ending-1", target_node_id="start"))
    with pytest.raises(DomainValidationError) as captured:
        validate_story_graph(graph, brief)
    assert any(issue["code"] == "cycle" for issue in captured.value.issues)


def test_primary_beat_coverage_is_required(brief: ProjectBrief) -> None:
    bible = make_story_bible()
    graph = make_story_graph()
    plan = make_scene_beats(graph)
    storyboard = make_storyboard(plan)
    storyboard.shot_beat_links = storyboard.shot_beat_links[2:]
    with pytest.raises(DomainValidationError) as captured:
        validate_storyboard_coverage(storyboard, plan, bible, brief)
    codes = {issue["code"] for issue in captured.value.issues}
    assert "beats_without_primary_coverage" in codes
    assert "unlinked_shots" in codes


def test_each_beat_requires_exactly_one_primary_shot(brief: ProjectBrief) -> None:
    bible = make_story_bible()
    graph = make_story_graph()
    plan = make_scene_beats(graph)
    storyboard = make_storyboard(plan)
    first_beat_id = plan.beats[0].id
    supporting_index = next(
        index
        for index, link in enumerate(storyboard.shot_beat_links)
        if link.beat_id == first_beat_id and link.role == CoverageRole.SUPPORTING
    )
    storyboard.shot_beat_links[supporting_index] = storyboard.shot_beat_links[
        supporting_index
    ].model_copy(update={"role": CoverageRole.PRIMARY})

    with pytest.raises(DomainValidationError) as captured:
        validate_storyboard_coverage(storyboard, plan, bible, brief)

    assert any(
        issue["code"] == "multiple_primary_shot_coverage"
        for issue in captured.value.issues
    )
