from __future__ import annotations

import pytest

from plotloom.domain import (
    DialogueDeliveryPace,
    DialogueTimingProfile,
    DialogueTimingRule,
    ProjectBrief,
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
    default_dialogue_timing_profile,
)
from plotloom.generation.dialogue_capacity import (
    DIALOGUE_CAPACITY_POLICY_VERSION,
    DialogueCapacityPlan,
    DialogueCapacityPlanningError,
    plan_dialogue_capacity,
)
from plotloom.generation.planning import (
    StagePlan,
    _stage_plan_hash,
    create_generation_plan,
    plan_stage,
)
from plotloom.generation.scene_timing_allocation import (
    SceneTimingAllocation,
    SceneTimingNodeAllocation,
    plan_scene_timing_allocation,
)
from plotloom.domain import StageName


def _brief(*, seconds: int = 4) -> ProjectBrief:
    return ProjectBrief(
        title="容量规划",
        synopsis="角色在警报响起后决定是否离开。",
        target_playthrough_seconds=seconds,
    )


def _graph() -> StoryGraphV2:
    return StoryGraphV2(
        start_node_id="start",
        nodes=[
            StoryNodeV2(footage_mode="footage", id="start", title="开始", summary="警报响起", kind="start"),
            StoryNodeV2(footage_mode="footage", id="ending", title="结局", summary="决定离开", kind="ending"),
        ],
        edges=[
            StoryEdgeV2(
                id="to-ending",
                source_node_id="start",
                target_node_id="ending",
                kind="continuation",
                choice_text=None,
                state_effects={},
            )
        ],
        join_contracts=[],
    )


def test_capacity_plan_is_deterministic_and_projects_each_timing_rule() -> None:
    allocation = plan_scene_timing_allocation(graph=_graph(), brief=_brief())
    profile = default_dialogue_timing_profile()

    first = plan_dialogue_capacity(
        scene_timing_allocation=allocation,
        dialogue_timing_profile=profile,
        authoring_language="zh-CN",
    )
    second = plan_dialogue_capacity(
        scene_timing_allocation=allocation,
        dialogue_timing_profile=profile,
        authoring_language="zh-CN",
    )

    assert first == second
    start = first.guidance_for("start")
    assert start.duration_budget_units == 2_000
    assert start.max_scenes == 2
    assert first.policy_version == DIALOGUE_CAPACITY_POLICY_VERSION
    assert first.authoring_language == "zh-CN"
    assert start.max_dialogue_cues == 2
    assert start.per_cue_duration_budget_units == 999
    assert start.schema_max_text_codepoints == 2
    limits = {
        (rule.language, rule.delivery.value): rule.max_text_codepoints
        for rule in start.rule_guidance
    }
    assert limits[("zh-CN", "measured")] == 2
    assert limits[("zh-CN", "natural")] == 3
    assert limits[("en", "natural")] == 16
    assert limits[("*", "brisk")] == 18


def test_capacity_plan_rejects_a_node_that_cannot_fund_scene_and_cue_slots() -> None:
    allocation = SceneTimingAllocation.model_construct(
        node_allocations=(
            SceneTimingNodeAllocation(node_id="tiny", depth=0, duration_budget_units=3, footage_mode="footage"),
        )
    )

    with pytest.raises(DialogueCapacityPlanningError) as failure:
        plan_dialogue_capacity(
                scene_timing_allocation=allocation,
                dialogue_timing_profile=default_dialogue_timing_profile(),
                authoring_language="zh-CN",
        )

    assert failure.value.code == "dialogue_capacity.node_budget_too_small"


def test_capacity_plan_hash_rejects_tampered_guidance() -> None:
    allocation = plan_scene_timing_allocation(graph=_graph(), brief=_brief())
    plan = plan_dialogue_capacity(
        scene_timing_allocation=allocation,
        dialogue_timing_profile=default_dialogue_timing_profile(),
        authoring_language="zh-CN",
    )
    payload = plan.model_dump(mode="json", by_alias=True)
    payload["nodeGuidance"][0]["ruleGuidance"][0]["maxTextCodepoints"] += 1

    with pytest.raises(ValueError, match="capacityPlanHash"):
        DialogueCapacityPlan.model_validate(payload)


def test_capacity_plan_rejects_retired_policy() -> None:
    allocation = plan_scene_timing_allocation(graph=_graph(), brief=_brief())
    current = plan_dialogue_capacity(scene_timing_allocation=allocation, dialogue_timing_profile=default_dialogue_timing_profile(), authoring_language="zh-CN")
    payload = current.model_dump(mode="json", by_alias=True)
    payload["policyVersion"] = "dialogue_capacity.v1"
    with pytest.raises(ValueError):
        DialogueCapacityPlan.model_validate(payload)


def test_v2_marks_dialogue_unavailable_when_no_authoring_delivery_has_capacity() -> None:
    allocation = plan_scene_timing_allocation(graph=_graph(), brief=_brief())
    profile = DialogueTimingProfile(
        version="slow-authoring.v1",
        rules=[
            DialogueTimingRule(
                language="zh-CN", delivery=delivery, units_per_character=2_000
            )
            for delivery in DialogueDeliveryPace
        ],
    )

    plan = plan_dialogue_capacity(
        scene_timing_allocation=allocation,
        dialogue_timing_profile=profile,
        authoring_language="zh-CN",
    )

    assert all(
        item.schema_max_text_codepoints == 0 for item in plan.node_guidance
    )


def test_v2_rejects_an_incomplete_authoring_language_timing_profile() -> None:
    allocation = plan_scene_timing_allocation(graph=_graph(), brief=_brief())
    incomplete = DialogueTimingProfile(
        version="partial-authoring.v1",
        rules=[
            DialogueTimingRule(
                language="zh-CN",
                delivery=DialogueDeliveryPace.NATURAL,
                units_per_character=330,
            )
        ],
    )

    with pytest.raises(DialogueCapacityPlanningError) as failure:
        plan_dialogue_capacity(
            scene_timing_allocation=allocation,
            dialogue_timing_profile=incomplete,
            authoring_language="zh-CN",
        )

    assert failure.value.code == "dialogue_capacity.timing_profile_incomplete"


def test_scene_beats_stage_plan_requires_current_frozen_capacity() -> None:
    graph = _graph()
    bible = {
        "logline": "l",
        "premise": "p",
        "genre": "",
        "tone": "",
        "audience": "",
        "narrativePromise": "",
        "visualLanguage": "",
        "themes": [],
        "worldRules": [],
        "knownFacts": [],
        "openQuestions": [],
        "sourceNotes": [],
        "characters": [],
        "locations": [],
        "props": [],
    }
    from plotloom.domain import StoryBibleV2

    generation_plan = create_generation_plan(
        run_id="capacity-stage",
        requested_stages=list(StageName),
        provider_profile_hash="profile",
        canonical_snapshot={"brief": _brief().model_dump(mode="json", by_alias=True)},
    )
    stage_plan = plan_stage(
        generation_plan,
        stage=StageName.SCENE_BEATS,
        dependencies={
            StageName.STORY_BIBLE: StoryBibleV2.model_validate(bible),
            StageName.STORY_GRAPH: graph,
        },
        brief=_brief(),
    )
    assert stage_plan.dialogue_timing_profile is not None
    assert stage_plan.dialogue_capacity_plan is not None

    retired = stage_plan.model_dump(mode="json")
    retired.pop("dialogue_timing_profile")
    retired.pop("dialogue_capacity_plan")
    with pytest.raises(ValueError):
        StagePlan.model_validate(retired)
