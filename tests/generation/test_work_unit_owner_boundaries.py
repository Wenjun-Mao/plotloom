"""Compiler-free ownership and isolation of the generation acceptance boundary."""

from __future__ import annotations

import subprocess
import sys
from copy import deepcopy

import pytest

from plotloom.generation.validation import SemanticValidationContext
from tests.generation.work_unit_contract_fixtures import (
    _compile_scene_beats,
    _scene_output,
)


@pytest.mark.parametrize("reverse", [False, True])
def test_binding_validation_and_repair_owners_import_without_compiler_or_dispatcher(
    reverse: bool,
) -> None:
    owners = [
        "fragment_binding",
        "frozen_join_requirements",
        "fragment_schema",
        "json_schema",
        "scene_beats_semantics",
        "storyboard_semantics",
        "story_graph_validation",
        "fragment_validation",
        "graph_semantic_repair",
        "entity_state_repair",
        "storyboard_audio_repair",
        "scene_beats_join_repair",
        "scene_beats_dialogue_repair",
        "storyboard_timing_repair",
        "continuity_repair",
    ]
    if reverse:
        owners.reverse()
    subprocess.run(
        [
            sys.executable,
            "-c",
            f"""
import importlib, sys
for name in {owners!r}:
    importlib.import_module('plotloom.generation.' + name)
assert 'plotloom.generation.work_units' not in sys.modules
assert 'plotloom.generation.semantic_repair' not in sys.modules
assert 'plotloom.work_unit_pipeline' not in sys.modules
compiler = importlib.import_module('plotloom.generation.work_units')
assert compiler.compile_work_unit_request.__module__ == compiler.__name__
assert 'plotloom.generation.semantic_repair' not in sys.modules
assert not any(hasattr(compiler, name) for name in (
    'canonical_fragment_id', 'canonical_audio_event_id', 'semantic_repair_facts',
    'assert_continuity_repair_fact_matches_source',
))
""",
        ],
        check=True,
    )


def test_schema_projections_and_rejections_do_not_mutate_frozen_or_model_inputs() -> (
    None
):
    compiled, _plan, _unit, _bible, _graph = _compile_scene_beats()
    adapter = compiled.validator
    source = _scene_output()
    source["scenes"][0]["locationId"] = "foreign-location"
    before_source = deepcopy(source)
    before_context = deepcopy(adapter.scoped_context)
    schema = adapter.json_schema()
    before_schema = deepcopy(schema)
    schema["properties"]["scenes"]["items"]["properties"]["locationId"].clear()
    schema["properties"]["dialogueCues"]["items"]["properties"]["speakerId"].clear()
    assert adapter.json_schema() == before_schema == compiled.response_schema
    report = adapter.validate(
        source, context=SemanticValidationContext(stage="scene_beats")
    )
    assert not report.accepted
    assert [issue.code for issue in report.issues] == ["semantic.unknown_location"]
    assert source == before_source
    assert adapter.scoped_context == before_context


def test_scene_rounding_ties_follow_authored_order_with_nonempty_dialogue() -> None:
    compiled, _plan, _unit, _bible, _graph = _compile_scene_beats()
    output = _scene_output()
    scene = output["scenes"][0]
    beat = output["beats"][0]
    output["scenes"] = [
        {
            **deepcopy(scene),
            "localSceneId": f"scene-{order}",
            "order": order,
            "durationWeight": 1,
        }
        for order in (2, 1)
    ]
    output["beats"] = [
        {
            **deepcopy(beat),
            "localBeatId": f"beat-{order}",
            "sceneLocalId": f"scene-{order}",
        }
        for order in (2, 1)
    ]
    output["dialogueCues"] = [
        {
            "localCueId": "narration",
            "beatLocalId": "beat-1",
            "order": 1,
            "speakerId": None,
            "voiceOver": "narrator",
            "text": "甲",
            "language": "zh-CN",
            "delivery": "natural",
            "performanceNotes": "平静",
        }
    ]
    report = compiled.validator.validate(
        output, context=SemanticValidationContext(stage="scene_beats")
    )
    assert report.accepted
    fragment = report.value
    cue_duration = fragment.dialogue_cues[0].estimated_duration_units
    budget = compiled.contract.node_duration_budget_units
    remaining, remainder = divmod(budget - cue_duration - 1, 2)
    assert remainder == 1
    budgets = {scene.order: scene.duration_budget_units for scene in fragment.scenes}
    assert budgets == {
        1: cue_duration + remaining + 1,
        2: 1 + remaining,
    }
    assert sum(budgets.values()) == budget


@pytest.mark.parametrize("reverse", [False, True])
def test_generation_owners_import_without_stage_or_unit_coordinators(
    reverse: bool,
) -> None:
    owners = [
        "generation.planning_contracts",
        "generation.planning_context",
        "generation.enqueue_planning",
        "generation.story_graph_topology_contracts",
        "generation.story_graph_topology_flow",
        "generation.story_graph_content_contracts",
        "generation.story_graph_content_fill",
        "generation.correction_registry",
        "generation.correction_schema_graph",
        "generation.correction_schema_continuity",
        "generation.correction_schema_cue_timing",
        "runtime_secrets",
        "text_provider_resolution",
        "work_unit_evidence",
        "correction_source",
        "work_unit_correction",
        "durable_provider_exchange",
    ]
    if reverse:
        owners.reverse()
    subprocess.run(
        [
            sys.executable,
            "-c",
            f"""
import importlib, sys
for name in {owners!r}:
    importlib.import_module('plotloom.' + name)
assert 'plotloom.generation.work_units' not in sys.modules
assert 'plotloom.work_unit_execution' not in sys.modules
assert 'plotloom.work_unit_pipeline' not in sys.modules
assert 'plotloom.pipeline' not in sys.modules
planning = importlib.import_module('plotloom.generation.planning')
assert planning.plan_stage.__module__ == planning.__name__
assert not hasattr(planning, 'create_generation_plan')
assert not hasattr(planning, 'work_unit_context')
stage = importlib.import_module('plotloom.work_unit_pipeline')
assert not any(hasattr(stage, name) for name in (
    'compile_correction_instruction_plan', 'compile_correction_response_schema',
    'assert_join_state_effect_repair_fact_matches_source',
))
""",
        ],
        check=True,
    )
