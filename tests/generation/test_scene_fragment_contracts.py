"""test scene fragment contracts behavior contracts."""

from __future__ import annotations

from copy import deepcopy

import pytest

from plotloom.domain import (
    JoinContractV2,
    RequiredEntityState,
    StageName,
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
)
from plotloom.generation.correction_directives import (
    compile_correction_instruction_plan,
)
from plotloom.generation.correction_postconditions import (
    validate_correction_postconditions,
)
from plotloom.generation.fragments import SceneBeatsFragment
from plotloom.generation.planning import plan_stage
from plotloom.generation.scene_beats_edge_entry import (
    assert_edge_entry_entity_state_repair_fact_matches_source,
)
from plotloom.generation.validation import SemanticValidationContext
from plotloom.generation.work_units import (
    WorkUnitContractError,
    compile_work_unit_request,
    semantic_repair_facts,
)
from tests.generation.work_unit_contract_fixtures import (
    _bible_with_hero,
    _compile_scene_beats,
    _plan_and_inputs,
    _scene_output,
)


def test_scene_fragment_rejects_legacy_parent_ids_and_binds_metadata_only_after_validation() -> (
    None
):
    compiled, stage_plan, unit, _, _ = _compile_scene_beats()
    legacy_parent = _scene_output()
    legacy_parent["storyNodeId"] = "node-b"
    rejected = compiled.validator.validate(
        legacy_parent,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert rejected.accepted is False
    assert "schema.extra_forbidden" in {issue.code for issue in rejected.issues}

    nested_legacy_parent = _scene_output()
    nested_legacy_parent["scenes"][0]["storyNodeId"] = "node-b"
    nested_rejected = compiled.validator.validate(
        nested_legacy_parent,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert nested_rejected.accepted is False
    assert "schema.extra_forbidden" in {issue.code for issue in nested_rejected.issues}

    legacy_beat_list = _scene_output()
    legacy_beat_list["scenes"][0]["beatLocalIds"] = ["beat-node-a"]
    legacy_beat_list_rejected = compiled.validator.validate(
        legacy_beat_list,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert legacy_beat_list_rejected.accepted is False
    assert "schema.extra_forbidden" in {
        issue.code for issue in legacy_beat_list_rejected.issues
    }

    accepted = compiled.validator.validate(
        _scene_output(),
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert accepted.accepted is True
    assert isinstance(accepted.value, SceneBeatsFragment)
    assert accepted.value.stage_plan_hash == stage_plan.stage_plan_hash
    assert accepted.value.work_unit_id == unit.unit_id
    assert accepted.value.scenes[0].id != "scene-node-a"
    assert accepted.value.beats[0].id != "beat-node-a"
    assert accepted.value.scenes[0].beat_ids == [accepted.value.beats[0].id]
    assert accepted.value.beats[0].scene_id == accepted.value.scenes[0].id

    repeated = compiled.validator.validate(
        _scene_output(),
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert repeated.accepted is True
    assert repeated.value.scenes[0].id == accepted.value.scenes[0].id
    assert repeated.value.beats[0].id == accepted.value.beats[0].id


def test_scene_fragment_requires_at_least_one_beat_per_scene() -> None:
    compiled, _, _, _, _ = _compile_scene_beats()
    output = _scene_output()
    output["scenes"].append(
        {
            **output["scenes"][0],
            "localSceneId": "scene-empty",
            "title": "空场",
            "objective": "不能没有节拍",
        }
    )

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is False
    assert "semantic.scene_without_beats" in {issue.code for issue in report.issues}


def test_scene_fragment_binding_namespaces_identical_model_ids_by_story_node() -> None:
    _, _, plan, bible, graph, _ = _plan_and_inputs()
    brief, snapshot, _, _, _, _ = _plan_and_inputs()
    stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
    )
    bound_ids: list[str] = []
    for unit in stage_plan.work_units:
        compiled = compile_work_unit_request(
            generation_plan=plan,
            stage_plan=stage_plan,
            work_unit=unit,
            dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
            brief=brief,
            canonical_snapshot=snapshot,
            instructions="preserve the project brief",
        )
        report = compiled.validator.validate(
            _scene_output(),
            context=SemanticValidationContext(stage="scene_beats"),
        )
        assert report.accepted is True
        bound_ids.append(report.value.scenes[0].id)

    assert len(set(bound_ids)) == 2


def test_join_continuity_keys_are_explicit_in_schema_prompt_and_validation() -> None:
    brief, snapshot, plan, bible, _, _ = _plan_and_inputs()
    graph = StoryGraphV2(
        start_node_id="node-a",
        nodes=[
            StoryNodeV2(
                footage_mode="footage",
                id="node-a",
                title="甲",
                summary="甲线",
                kind="start",
            ),
            StoryNodeV2(
                footage_mode="footage",
                id="node-c",
                title="乙",
                summary="乙线",
                kind="scene",
            ),
            StoryNodeV2(
                footage_mode="footage",
                id="node-b",
                title="汇流",
                summary="会合",
                kind="ending",
            ),
        ],
        edges=[
            StoryEdgeV2(
                id="edge-a-b",
                source_node_id="node-a",
                target_node_id="node-b",
                kind="choice",
                choice_text="直接汇流",
                state_effects={"船钟归属": "由摆渡人保管"},
            ),
            StoryEdgeV2(
                id="edge-a-c",
                source_node_id="node-a",
                target_node_id="node-c",
                kind="choice",
                choice_text="先走乙线",
                state_effects={},
            ),
            StoryEdgeV2(
                id="edge-c-b",
                source_node_id="node-c",
                target_node_id="node-b",
                kind="continuation",
                choice_text=None,
                state_effects={"船钟归属": "由摆渡人保管"},
            ),
        ],
        join_contracts=[
            JoinContractV2(
                id="join-a-c-b",
                join_node_id="node-b",
                incoming_node_ids=["node-a", "node-c"],
                required_state_keys=["船钟归属"],
                allowed_differences=[],
                reconciliation="",
                notes="",
            )
        ],
    )
    stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
    )
    unit = next(
        item for item in stage_plan.work_units if item.selector.stable_id == "node-b"
    )
    compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=unit,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    entry_schema = compiled.response_schema["properties"]["scenes"]["items"][
        "properties"
    ]["entryState"]
    assert entry_schema["properties"]["facts"]["required"] == ["船钟归属"]
    assert entry_schema["properties"]["facts"]["properties"]["船钟归属"] == {
        "const": "由摆渡人保管"
    }
    assert (
        '"requiredEntryFactKeys":["船钟归属"]' in compiled.rendered.messages[1].content
    )

    output = _scene_output()
    missing = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert missing.accepted is False
    assert "schema.missing" in {issue.code for issue in missing.issues}

    output["scenes"][0]["entryState"]["facts"] = {"船钟归属": "错误值"}
    mismatched = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert mismatched.accepted is False
    assert {issue.code for issue in mismatched.issues} == {
        "semantic.join_entry_state_value_mismatch"
    }

    output["scenes"][0]["entryState"]["facts"] = {"船钟归属": "由摆渡人保管"}
    accepted = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )
    assert accepted.accepted is True


def test_typed_direct_edge_state_binds_first_scene_only_and_allows_later_transition() -> (
    None
):
    brief, snapshot, plan, bible, graph, _ = _plan_and_inputs()
    bible = _bible_with_hero()
    graph.edges[0].entity_state_effects = [
        RequiredEntityState(entity_type="character", entity_id="hero", state="alert")
    ]
    stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
    )
    unit = next(
        item for item in stage_plan.work_units if item.selector.stable_id == "node-b"
    )
    compiled = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=stage_plan,
        work_unit=unit,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
    )
    requirements = compiled.validator.scoped_context["edge_entry_state_requirements"]
    assert requirements["requiredEntityStates"] == [
        {
            "entityType": "character",
            "entityId": "hero",
            "state": "alert",
            "incomingEdgeIds": ["edge-a-b"],
        }
    ]
    schema_scene = compiled.response_schema["properties"]["scenes"]["items"]
    assert schema_scene["allOf"][-1]["if"]["properties"]["order"] == {"const": 1}
    assert '"requiredEntityStates"' in compiled.rendered.messages[1].content

    output = _scene_output()
    alert = {"entityType": "character", "entityId": "hero", "state": "alert"}
    calm = {"entityType": "character", "entityId": "hero", "state": "calm"}
    output["scenes"][0]["entryState"]["entityStates"] = [alert]
    output["beats"][0]["entryState"]["entityStates"] = [alert]
    output["beats"][0]["exitState"]["entityStates"] = [calm]
    output["scenes"][0]["exitState"]["entityStates"] = [calm]
    assert (
        compiled.validator.validate(
            output, context=SemanticValidationContext(stage="scene_beats")
        ).accepted
        is True
    )

    output["scenes"][0]["entryState"]["entityStates"] = [calm]
    rejected = compiled.validator.validate(
        output, context=SemanticValidationContext(stage="scene_beats")
    )
    assert rejected.accepted is False
    assert "semantic.edge_entry_entity_state_mismatch" in {
        issue.code for issue in rejected.issues
    }
    facts = semantic_repair_facts(
        output,
        rejected.issues,
        stage=StageName.SCENE_BEATS,
        bible=bible,
        dialogue_capacity_guidance=compiled.contract.dialogue_capacity_guidance,
        dialogue_timing_profile=stage_plan.dialogue_timing_profile,
        node_duration_budget_units=compiled.contract.node_duration_budget_units,
        join_state_value_requirements=compiled.validator.scoped_context[
            "join_state_value_requirements"
        ],
        scoped_context=compiled.validator.scoped_context,
    )
    edge_facts = [
        fact
        for fact in facts
        if fact.code == "semantic.edge_entry_entity_state_mismatch"
    ]
    assert len(edge_facts) == 1
    assert edge_facts[0].expected_state == "alert"
    directive_plan = compile_correction_instruction_plan(rejected.issues, facts)
    assert "edge_entry_entity_state" in {
        directive.id for directive in directive_plan.directives
    }
    corrected = deepcopy(output)
    corrected["scenes"][0]["entryState"]["entityStates"] = [alert]
    assert validate_correction_postconditions(corrected, edge_facts) == ()

    # Correction authority is re-derived from the rejected response and the
    # frozen work-unit requirements; self-consistent forged evidence cannot
    # reach a correction request.
    fact = edge_facts[0]
    requirements = compiled.validator.scoped_context["edge_entry_state_requirements"]
    assert_edge_entry_entity_state_repair_fact_matches_source(
        fact, output, requirements=requirements
    )
    with pytest.raises(ValueError, match="typed edge-entry repair fact"):
        assert_edge_entry_entity_state_repair_fact_matches_source(
            fact, corrected, requirements=requirements
        )
    for forged in (
        fact.model_copy(update={"scene_local_id": "another-scene"}),
        fact.model_copy(
            update={
                "path": (
                    "scenes",
                    0,
                    "entryState",
                    "entityStates",
                    "character",
                    "other",
                )
            }
        ),
        fact.model_copy(update={"entity_id": "other"}),
        fact.model_copy(update={"expected_state": "calm"}),
        fact.model_copy(update={"contract_hash": "f" * 64}),
    ):
        with pytest.raises(ValueError, match="typed edge-entry repair fact"):
            assert_edge_entry_entity_state_repair_fact_matches_source(
                forged, output, requirements=requirements
            )


def test_scene_fragment_rejects_nonfinite_join_fact_and_continuity_delta() -> None:
    compiled, _, _, _, _ = _compile_scene_beats()
    output = _scene_output()
    output["scenes"][0]["entryState"]["facts"] = {"bad": float("nan")}
    output["beats"][0]["continuityDelta"] = {"bad": float("nan")}

    report = compiled.validator.validate(
        output,
        context=SemanticValidationContext(stage="scene_beats"),
    )

    assert report.accepted is False
    assert {issue.code for issue in report.issues} == {
        "semantic.continuity_fact_not_json",
        "semantic.continuity_delta_not_json",
    }


def test_scene_beats_compilation_requires_the_exact_stage_plan_join_marker() -> None:
    compiled, stage_plan, unit, bible, graph = _compile_scene_beats()
    brief, snapshot, plan, _, _, _ = _plan_and_inputs()
    assert (
        stage_plan.join_state_value_contract_version == "join_required_state_values.v1"
    )
    assert stage_plan.join_state_value_contract_hash == (
        compiled.contract.join_state_value_contract_hash
    )

    tampered = stage_plan.model_copy(
        update={"join_state_value_contract_hash": "0" * 64}
    )
    with pytest.raises(WorkUnitContractError, match="does not match"):
        compile_work_unit_request(
            generation_plan=plan,
            stage_plan=tampered,
            work_unit=unit,
            dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
            brief=brief,
            canonical_snapshot=snapshot,
            instructions="preserve the project brief",
        )
