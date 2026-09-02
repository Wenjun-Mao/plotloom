from __future__ import annotations

import pytest
from pydantic import ValidationError

from plotloom.domain import ProjectBrief, StoryEdge
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
    validate_story_graph(graph, brief)
    validate_scene_beat_coverage(plan, graph, bible)
    validate_storyboard_coverage(storyboard, plan, bible, brief)
    first_beat = plan.beats[0].model_dump(by_alias=True)
    assert "visibleEvent" in first_beat and "entryState" in first_beat
    first_shot = storyboard.shots[0].model_dump(by_alias=True)
    assert {"audio", "transition", "visualIntent", "motionIntent"} <= set(first_shot)


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
