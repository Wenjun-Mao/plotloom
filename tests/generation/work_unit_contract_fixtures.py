from __future__ import annotations

from copy import deepcopy

from plotloom.domain import (
    BeatV2,
    CharacterV2,
    ContinuityStateV2,
    DramaticSceneV2,
    ProjectBrief,
    SceneBeatPlanV2,
    StageName,
    StoryBibleV2,
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
)
from plotloom.generation.planning import create_generation_plan, plan_stage
from plotloom.generation.work_units import (
    BeatContent,
    DramaticSceneContent,
    SceneBeatsFragmentOutput,
    ShotContent,
    StoryboardFragmentOutput,
    compile_work_unit_request,
)


def _brief() -> ProjectBrief:
    return ProjectBrief(
        title="分片测试",
        synopsis="领航员在空间站寻找身份。",
        ending_count=1,
        decision_points_per_path=0,
        desired_join_count=0,
        node_budget=3,
        shots_per_scene_min=1,
        shots_per_scene_max=2,
    )


def _state() -> ContinuityStateV2:
    return ContinuityStateV2(
        facts={},
        entity_states=[],
        screen_direction=None,
        lighting=None,
        sound=None,
        notes=[],
    )


def _character_state(state: str) -> ContinuityStateV2:
    return ContinuityStateV2(
        facts={},
        entity_states=[{"entityType": "character", "entityId": "hero", "state": state}],
        screen_direction=None,
        lighting=None,
        sound=None,
        notes=[],
    )


def _bible() -> StoryBibleV2:
    return StoryBibleV2(
        logline="领航员寻找身份。",
        premise="记忆决定生存。",
        genre="",
        tone="",
        audience="",
        narrative_promise="",
        visual_language="",
        themes=[],
        world_rules=[],
        known_facts=[],
        open_questions=[],
        source_notes=[],
        characters=[],
        locations=[],
        props=[],
    )


def _bible_with_hero() -> StoryBibleV2:
    return _bible().model_copy(
        update={
            "characters": [
                CharacterV2(
                    id="hero",
                    name="领航员",
                    description="失忆的领航员。",
                    visual_anchors=[],
                    sound_anchors=[],
                    allowed_states=["alert", "calm"],
                    continuity_rules=[],
                    role="protagonist",
                    goal="找回身份",
                    traits=[],
                    voice_anchors=[],
                )
            ]
        }
    )


def _graph() -> StoryGraphV2:
    return StoryGraphV2(
        start_node_id="node-a",
        nodes=[
            StoryNodeV2(
                footage_mode="footage",
                id="node-a",
                title="苏醒",
                summary="她在控制室醒来。",
                kind="start",
            ),
            StoryNodeV2(
                footage_mode="footage",
                id="node-b",
                title="秘密节点",
                summary="PRIVATE_OTHER_NODE",
                kind="ending",
            ),
        ],
        edges=[
            StoryEdgeV2(
                id="edge-a-b",
                source_node_id="node-a",
                target_node_id="node-b",
                kind="continuation",
                choice_text=None,
                state_effects={},
            )
        ],
        join_contracts=[],
    )


def _scene_beats(graph: StoryGraphV2) -> SceneBeatPlanV2:
    scenes: list[DramaticSceneV2] = []
    beats: list[BeatV2] = []
    for node in graph.nodes:
        scene_id = f"scene-{node.id}"
        beat_id = f"beat-{node.id}"
        scenes.append(
            DramaticSceneV2(
                id=scene_id,
                story_node_id=node.id,
                title=node.title,
                objective=node.summary,
                order=1,
                beat_ids=[beat_id],
                duration_budget_units=2,
                entry_state=_state(),
                exit_state=_state(),
                location_id=None,
                character_ids=[],
            )
        )
        beats.append(
            BeatV2(
                id=beat_id,
                scene_id=scene_id,
                order=1,
                description=node.summary,
                purpose="推进叙事",
                visible_event="",
                immediate_result="",
                dramatic_change="",
                entry_state=_state(),
                exit_state=_state(),
                continuity_anchors=[],
                continuity_delta={},
            )
        )
    return SceneBeatPlanV2(scenes=scenes, beats=beats, dialogue_cues=[])


def _plan_and_inputs():
    brief = _brief()
    snapshot = {"brief": brief.model_dump(mode="json", by_alias=True)}
    plan = create_generation_plan(
        run_id="work-unit-test",
        requested_stages=list(StageName),
        provider_profile_hash="profile-hash",
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    bible = _bible()
    graph = _graph()
    scene_beats = _scene_beats(graph)
    return brief, snapshot, plan, bible, graph, scene_beats


def _compile_scene_beats():
    brief, snapshot, plan, bible, graph, _ = _plan_and_inputs()
    stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
    )
    unit = stage_plan.work_units[0]
    compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=unit,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
        stage_constraints={"maxBeats": 2},
    )
    return compiled, stage_plan, unit, bible, graph


def _scene_output() -> dict:
    return SceneBeatsFragmentOutput(
        scenes=[
            DramaticSceneContent(
                local_scene_id="scene-node-a",
                order=1,
                title="苏醒",
                objective="确认身份",
                location_id=None,
                character_ids=[],
                duration_weight=1,
                entry_state=_state(),
                exit_state=_state(),
            )
        ],
        beats=[
            BeatContent(
                local_beat_id="beat-node-a",
                scene_local_id="scene-node-a",
                order=1,
                description="她睁开眼睛。",
                purpose="建立危机",
                visible_event="",
                immediate_result="",
                dramatic_change="",
                entry_state=_state(),
                exit_state=_state(),
                continuity_anchors=[],
                continuity_delta={},
            )
        ],
        dialogue_cues=[],
    ).model_dump(mode="json", by_alias=True)


def _cue_order_output(*, second_order: int = 2) -> dict:
    """A valid fragment shape whose second per-beat order is deliberately wrong."""

    output = _scene_output()
    output["beats"].append(
        {
            **deepcopy(output["beats"][0]),
            "localBeatId": "beat-node-b",
            "order": 2,
            "description": "她听见远处警报。",
        }
    )
    output["dialogueCues"] = [
        {
            "localCueId": "cue-a",
            "beatLocalId": "beat-node-a",
            "order": 1,
            "speakerId": None,
            "voiceOver": "narrator",
            "text": "第一句",
            "language": "zh-CN",
            "delivery": "natural",
            "performanceNotes": "平静",
        },
        {
            "localCueId": "cue-b",
            "beatLocalId": "beat-node-b",
            "order": second_order,
            "speakerId": None,
            "voiceOver": "narrator",
            "text": "第二句",
            "language": "zh-CN",
            "delivery": "natural",
            "performanceNotes": "平静",
        },
    ]
    return output


def _storyboard_output(*, beat_ids: list[str], local_shot_id: str = "shot-a") -> dict:
    return StoryboardFragmentOutput(
        shots=[
            ShotContent(
                local_shot_id=local_shot_id,
                order=1,
                title="苏醒",
                shot_size="close_up",
                duration_units=2,
                camera_angle="",
                camera_movement="",
                composition="",
                visual_intent="",
                motion_intent="",
                action="",
                transition="",
                cue_ids=[],
                audio_plan={"events": []},
                character_ids=[],
                location_id=None,
                prop_ids=[],
                required_entity_states=[],
                entry_state=_state(),
                exit_state=_state(),
            )
        ],
        primary_shot_local_id_by_beat={beat_id: local_shot_id for beat_id in beat_ids},
        supporting_beat_links=[],
    ).model_dump(mode="json", by_alias=True)
