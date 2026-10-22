"""test work unit prompts behavior contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from plotloom.domain import (
    ContinuityStateV2,
    LocationV2,
    RequiredEntityState,
    StageName,
    StoryEdgeV2,
    StoryGraphV2,
)
from plotloom.generation.contracts import ValidationIssue
from plotloom.generation.correction_directives import (
    compile_correction_instruction_plan,
)
from plotloom.generation.fragment_semantics import (
    continuity_state_issues,
    continuity_states_are_compatible,
)
from plotloom.generation.planning import plan_stage
from plotloom.generation.prompts import PromptRenderer
from plotloom.generation.work_units import (
    WorkUnitPromptContract,
    compile_work_unit_request,
    parse_semantic_repair_fact,
    serialize_semantic_repair_fact,
)
from plotloom.validation_state import (
    _continuity_state_issues,
    _continuity_states_are_compatible,
)
from tests.generation.work_unit_contract_fixtures import (
    _bible,
    _bible_with_hero,
    _compile_scene_beats,
    _graph,
    _plan_and_inputs,
    _state,
)


def test_join_exact_json_null_survives_repair_fact_rendering() -> None:
    fact = parse_semantic_repair_fact(
        {
            "code": "semantic.join_state_effect_missing",
            "path": ["edges", "edge-a", "stateEffects", "route"],
            "joinContractId": "join-a",
            "joinNodeId": "node-a",
            "stateKey": "route",
            "mode": "convergent",
            "incomingEdges": [
                {"edgeId": "edge-a", "sourceNodeId": "left"},
                {"edgeId": "edge-b", "sourceNodeId": "right"},
            ],
            "repairAction": "set_missing",
            "hasExpectedValue": True,
            "expectedValue": None,
            "preservedStateEffects": [
                {
                    "stateKey": "variant",
                    "incomingEffects": [
                        {"edgeId": "edge-a", "expectedValue": None},
                        {"edgeId": "edge-b", "expectedValue": {"branch": 2}},
                    ],
                }
            ],
        }
    )
    serialized = serialize_semantic_repair_fact(fact)
    assert serialized["hasExpectedValue"] is True
    assert "expectedValue" in serialized and serialized["expectedValue"] is None
    assert serialized["preservedStateEffects"][0]["incomingEffects"][0] == {
        "edgeId": "edge-a",
        "expectedValue": None,
    }
    issue = ValidationIssue(code=fact.code, message="stable", path=fact.path)
    instruction_plan = compile_correction_instruction_plan([issue], [fact])
    rendered = PromptRenderer().render(
        "work_unit_correction",
        {
            "original_contract": {},
            "response_schema": {},
            "previous_final_content": "{}",
            "validation_issues": [{"code": fact.code, "path": list(fact.path)}],
            "repair_evidence_projection": instruction_plan.prompt_evidence,
            "correction_directives": [
                directive.model_dump(mode="json")
                for directive in instruction_plan.directives
            ],
            "correction_ordinal": 1,
            "correction_strategy": "repair_previous_final",
        },
    )
    assert '"hasExpectedValue":true' in rendered.messages[1].content
    assert '"expectedValue":null' in rendered.messages[1].content
    projected = instruction_plan.prompt_evidence["facts"][0]
    assert projected["preservedStateEffects"][0]["incomingEffects"][0] == {
        "edgeId": "edge-a",
        "expectedValue": None,
    }


@pytest.mark.parametrize("expected_value", [None, "unauthorized"])
def test_join_repair_fact_rejects_explicit_expected_value_without_authority(
    expected_value: object,
) -> None:
    payload = {
        "code": "semantic.join_state_effect_missing",
        "path": ["edges", "edge-a", "stateEffects", "route"],
        "joinContractId": "join-a",
        "joinNodeId": "node-a",
        "stateKey": "route",
        "mode": "convergent",
        "incomingEdges": [
            {"edgeId": "edge-a", "sourceNodeId": "left"},
            {"edgeId": "edge-b", "sourceNodeId": "right"},
        ],
        "repairAction": "set_missing",
        "hasExpectedValue": False,
        "expectedValue": expected_value,
    }
    with pytest.raises(ValidationError, match="expectedValue requires"):
        parse_semantic_repair_fact(payload)


def test_scene_work_unit_prompt_only_contains_the_selected_node_and_public_schema() -> (
    None
):
    compiled, stage_plan, unit, bible, graph = _compile_scene_beats()
    brief, snapshot, plan, _, _, _ = _plan_and_inputs()
    second_stage_plan = plan_stage(
        plan,
        stage=StageName.SCENE_BEATS,
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
    )
    second = compile_work_unit_request(
        generation_plan=plan,
        stage_plan=second_stage_plan,
        work_unit=second_stage_plan.work_units[0],
        dependencies={StageName.STORY_BIBLE: bible, StageName.STORY_GRAPH: graph},
        brief=brief,
        canonical_snapshot=snapshot,
        instructions="preserve the project brief",
        stage_constraints={"maxBeats": 2},
    )
    message = compiled.rendered.messages[1].content

    assert "node-a" in message
    assert "PRIVATE_OTHER_NODE" not in message
    # The node ID may appear in an incident edge; the other node's title and
    # summary must not be copied into the unit's creative context.
    assert "stagePlanHash" not in compiled.response_schema["properties"]
    assert "workUnitId" not in compiled.response_schema["properties"]
    assert "unitDependencyHash" not in compiled.response_schema["properties"]
    assert compiled.contract.work_unit_id == unit.unit_id
    assert compiled.contract.stage_plan_hash == stage_plan.stage_plan_hash
    assert compiled.contract.prompt_id == "scene_beats_fragment"
    assert compiled.rendered.output.schema_id == "scene_beats.fragment.v13"
    assert "allowedStates" in message
    assert "scene.entryState →" in message
    scene_properties = compiled.response_schema["properties"]["scenes"]["items"][
        "properties"
    ]
    assert "storyNodeId" not in compiled.response_schema["properties"]
    assert "storyNodeId" not in scene_properties
    assert "beatLocalIds" not in scene_properties
    assert "beatIds" not in scene_properties
    assert "localSceneId" in scene_properties
    cue_schema = compiled.response_schema["properties"]["dialogueCues"]["items"]
    assert cue_schema["properties"]["order"]["description"] == (
        "One-based contiguous dialogue order within this cue's beatLocalId."
    )
    assert (
        "exactly one of speakerId and voiceOver"
        in cue_schema["properties"]["speakerId"]["description"]
    )
    assert (
        "exactly one of speakerId and voiceOver"
        in cue_schema["properties"]["voiceOver"]["description"]
    )
    assert "oneOf" not in cue_schema
    assert "$defs" not in compiled.response_schema
    assert '"$ref"' not in str(compiled.response_schema)
    assert scene_properties["exitState"]["required"] == [
        "facts",
        "entityStates",
        "screenDirection",
        "lighting",
        "sound",
        "notes",
    ]
    assert compiled.contract.schema_hash
    assert compiled.contract.variables_hash == second.contract.variables_hash
    assert compiled.contract.rendered_hash == second.contract.rendered_hash


def test_scene_prompt_separates_regular_facts_from_typed_incoming_entity_effects() -> (
    None
):
    brief, snapshot, plan, _bible_unused, _graph_unused, _scene_beats_unused = (
        _plan_and_inputs()
    )
    bible = _bible_with_hero().model_copy(
        update={
            "locations": [
                LocationV2(
                    id="loc_station",
                    name="空间站",
                    description="目标地点。",
                    visual_anchors=[],
                    sound_anchors=[],
                    allowed_states=["occupied", "empty"],
                    continuity_rules=[],
                )
            ]
        }
    )
    base_graph = _graph()
    graph = StoryGraphV2(
        start_node_id=base_graph.start_node_id,
        nodes=base_graph.nodes,
        edges=[
            StoryEdgeV2(
                id="edge-a-b",
                source_node_id="node-a",
                target_node_id="node-b",
                kind="continuation",
                choice_text=None,
                state_effects={"loc_station_state": "misleading ordinary fact"},
                entity_state_effects=[
                    RequiredEntityState(
                        entity_type="location",
                        entity_id="loc_station",
                        state="occupied",
                    )
                ],
            )
        ],
        join_contracts=[],
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
        stage_constraints={"maxBeats": 2},
    )

    message = compiled.rendered.messages[1].content
    incident_edge = compiled.validator.scoped_context["incident_edges"][0]

    assert compiled.contract.prompt_version == "3.14.0"
    assert incident_edge["stateEffects"] == {
        "loc_station_state": "misleading ordinary fact",
    }
    assert incident_edge["entityStateEffects"] == [
        {
            "entityType": "location",
            "entityId": "loc_station",
            "state": "occupied",
        }
    ]
    assert "misleading ordinary fact" in message
    assert '"entityStateEffects"' in message
    assert "无论键名是否含 *_state，都绝不能把它推断" in message
    assert "目标节点 entryState 之前生效" in message


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (
            _state().model_copy(update={"facts": {"x": 1}}),
            _state().model_copy(update={"facts": {"x": 1.0}}),
            False,
        ),
        (
            _state().model_copy(update={"facts": {"x": "same"}}),
            _state().model_copy(update={"facts": {"x": "same"}}),
            True,
        ),
    ],
)
def test_fragment_and_canonical_continuity_use_identical_finite_json_identity(
    left: ContinuityStateV2,
    right: ContinuityStateV2,
    expected: bool,
) -> None:
    """Fragment checks must use the same value identity as canonical gates."""

    assert continuity_states_are_compatible(left, right) is expected
    assert _continuity_states_are_compatible(left, right) is expected


def test_nonfinite_continuity_facts_are_rejected_locally_and_canonically() -> None:
    state = _state().model_copy(update={"facts": {"x": float("nan")}})
    local = continuity_state_issues(
        state, bible=_bible(), path=("scenes", 0, "entryState")
    )
    canonical = _continuity_state_issues("scenes.scene-a.entryState", state, _bible())

    assert [(issue.code, issue.path) for issue in local] == [
        ("semantic.continuity_fact_not_json", ("scenes", 0, "entryState", "facts", "x"))
    ]
    assert [(issue["code"], issue["path"]) for issue in canonical] == [
        ("continuity_fact_not_json", "scenes.scene-a.entryState.facts.x")
    ]


@pytest.mark.parametrize(
    "invalid_value",
    [
        ("tuple values are not JSON arrays",),
        {1: "object keys must stay strings"},
        object(),
    ],
)
def test_non_native_continuity_facts_are_rejected_locally_and_canonically(
    invalid_value: object,
) -> None:
    """The fragment and canonical boundaries reject the same non-JSON value."""

    state = _state().model_copy(update={"facts": {"x": invalid_value}})
    local = continuity_state_issues(
        state,
        bible=_bible(),
        path=("scenes", 0, "entryState"),
    )
    canonical = _continuity_state_issues(
        "scenes.scene-a.entryState",
        state,
        _bible(),
    )

    assert [(issue.code, issue.path) for issue in local] == [
        ("semantic.continuity_fact_not_json", ("scenes", 0, "entryState", "facts", "x"))
    ]
    assert [(issue["code"], issue["path"]) for issue in canonical] == [
        ("continuity_fact_not_json", "scenes.scene-a.entryState.facts.x")
    ]


def test_prompt_contract_requires_complete_correction_schedule() -> None:
    compiled, _, _, _, _ = _compile_scene_beats()
    primary = compiled.contract.model_dump(mode="json")

    with pytest.raises(ValidationError, match="must be set together"):
        WorkUnitPromptContract.model_validate({**primary, "correction_ordinal": 1})

    with pytest.raises(ValidationError, match="must be set together"):
        WorkUnitPromptContract.model_validate(
            {**primary, "correction_strategy": "repair_previous_final"}
        )

    with pytest.raises(ValidationError, match="does not match"):
        WorkUnitPromptContract.model_validate(
            {
                **primary,
                "correction_ordinal": 1,
                "correction_strategy": "reconstruct_from_schema",
            }
        )

    with pytest.raises(ValidationError, match="compiler hashes"):
        WorkUnitPromptContract.model_validate(
            {
                **primary,
                "correction_ordinal": 1,
                "correction_strategy": "repair_previous_final",
            }
        )

    with pytest.raises(ValidationError, match="current correction policy"):
        WorkUnitPromptContract.model_validate(
            {**primary, "correction_policy_version": "bounded_correction.future"}
        )

    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        WorkUnitPromptContract.model_validate(
            {
                **primary,
                "correction_ordinal": 1,
                "correction_strategy": "repair_previous_final",
                "correction_directive_set_hash": "g" * 64,
                "correction_evidence_projection_hash": "0" * 64,
                "correction_issue_selection_hash": "0" * 64,
                "correction_response_schema_hash": "0" * 64,
            }
        )
