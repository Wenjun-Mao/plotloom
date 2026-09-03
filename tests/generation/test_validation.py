from __future__ import annotations

import pytest

from plotloom.domain import (
    ProjectBrief,
    SceneBeatPlan,
    StageName,
    StoryBible,
    StoryGraph,
)
from plotloom.generation.validation import (
    CanonicalStageValidationAdapter,
    SemanticValidationContext,
)


def _brief() -> ProjectBrief:
    return ProjectBrief(
        title="测试",
        synopsis="一名失忆领航员寻找身份。",
        ending_count=1,
        decision_points_per_path=0,
        desired_join_count=0,
        node_budget=4,
    )


def test_canonical_stage_schema_uses_wire_aliases_and_required_shot_fields() -> None:
    bible_adapter = CanonicalStageValidationAdapter(StageName.STORY_BIBLE, brief=_brief())
    bible_schema = bible_adapter.json_schema()
    assert "worldRules" in bible_schema["properties"]
    assert "world_rules" not in bible_schema["properties"]

    storyboard_adapter = CanonicalStageValidationAdapter(
        StageName.STORYBOARD,
        brief=_brief(),
        bible=StoryBible(logline="失忆", premise="寻找身份"),
        scene_beats=SceneBeatPlan(),
    )
    shot_schema = storyboard_adapter.json_schema()["properties"]["shots"]["items"][
        "properties"
    ]
    for field in ("audio", "transition", "visualIntent", "motionIntent"):
        assert field in shot_schema
    required = storyboard_adapter.json_schema()["properties"]["shots"]["items"][
        "required"
    ]
    for field in ("audio", "transition", "visualIntent", "motionIntent"):
        assert field in required

    missing_generated_fields = storyboard_adapter.validate(
        {
            "shots": [
                {
                    "id": "shot-1",
                    "sceneId": "scene-1",
                    "order": 1,
                    "title": "镜头",
                    "shotSize": "close_up",
                    "durationSeconds": 2,
                }
            ],
            "shotBeatLinks": [],
        },
        context=SemanticValidationContext(stage="storyboard"),
    )
    assert missing_generated_fields.accepted is False
    missing_names = {issue.path[-1] for issue in missing_generated_fields.issues}
    assert {
        "audio",
        "transition",
        "visualIntent",
        "motionIntent",
        "action",
        "entryState",
        "exitState",
    } <= missing_names


def test_canonical_adapter_applies_semantic_validation_after_schema() -> None:
    adapter = CanonicalStageValidationAdapter(StageName.STORY_GRAPH, brief=_brief())
    invalid_graph = {
        "startNodeId": "missing",
        "nodes": [
            {"id": "end", "title": "结局", "summary": "结束", "kind": "ending"}
        ],
        "edges": [],
        "joinContracts": [],
    }
    report = adapter.validate(
        invalid_graph,
        context=SemanticValidationContext(stage="story_graph"),
    )
    assert report.accepted is False
    assert "semantic.missing_start_node" in {issue.code for issue in report.issues}

    valid_graph = {
        "startNodeId": "start",
        "nodes": [
            {"id": "start", "title": "开始", "summary": "苏醒", "kind": "start"},
            {"id": "end", "title": "结局", "summary": "离开", "kind": "ending"},
        ],
        "edges": [
            {
                "id": "edge-1",
                "sourceNodeId": "start",
                "targetNodeId": "end",
                "kind": "continuation",
                "choiceText": None,
                "stateEffects": {},
            }
        ],
        "joinContracts": [],
    }
    accepted = adapter.validate(
        valid_graph,
        context=SemanticValidationContext(stage="story_graph"),
    )
    assert accepted.accepted is True
    assert isinstance(accepted.value, StoryGraph)


def test_canonical_adapter_requires_upstream_context() -> None:
    with pytest.raises(ValueError, match="requires bible and graph"):
        CanonicalStageValidationAdapter(StageName.SCENE_BEATS, brief=_brief())
    with pytest.raises(ValueError, match="requires bible and scene_beats"):
        CanonicalStageValidationAdapter(StageName.STORYBOARD, brief=_brief())
