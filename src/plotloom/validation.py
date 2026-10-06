from __future__ import annotations

from typing import Literal
from pydantic import ValidationError
from .canonical_schema import DialogueTimingProfile, StoryBibleV2, StoryGraphV2, SceneBeatPlanV2, StoryboardV2, default_dialogue_timing_profile
from .domain import StageName, ProjectBrief, GateEvaluation
from .validation_issues import DomainValidationError, ValidationIssue, _issue
from .validation_graph import validate_story_graph
from .validation_coverage import validate_scene_beat_coverage, validate_storyboard_coverage
from .validation_scene import _validate_v2_scene_order_and_continuity, _validate_v2_dialogue_cues, _validate_v2_scene_timing_allocation
from .validation_storyboard import StoryboardGateEvaluator, STORYBOARD_GATE_SET_VERSION

def pydantic_issues(error: ValidationError) -> list[ValidationIssue]:
    return [
        _issue(
            "schema_validation",
            ".".join(str(part) for part in item["loc"]),
            item["msg"],
        )
        for item in error.errors()
    ]


def validate_stage_payload(
    stage: StageName,
    payload: StoryBibleV2 | StoryGraphV2 | SceneBeatPlanV2 | StoryboardV2,
    *,
    schema_version: Literal[2],
    brief: ProjectBrief,
    bible: StoryBibleV2 | None = None,
    graph: StoryGraphV2 | None = None,
    scene_beats: SceneBeatPlanV2 | None = None,
    dialogue_timing_profile: DialogueTimingProfile | None = None,
) -> GateEvaluation | None:
    """Validate the current schema and preserve its exact immutable gate receipt."""

    if schema_version != 2:
        raise ValueError(f"unsupported canonical schema version: {schema_version}")
    if stage == StageName.STORY_BIBLE:
        if not isinstance(payload, StoryBibleV2):
            raise TypeError("V2 story_bible requires StoryBibleV2")
        return None
    if stage == StageName.STORY_GRAPH:
        if not isinstance(payload, StoryGraphV2):
            raise TypeError("V2 story_graph requires StoryGraphV2")
        if bible is None:
            if any(edge.entity_state_effects for edge in payload.edges):
                raise TypeError("V2 graph entityStateEffects require a sealed StoryBibleV2")
        elif not isinstance(bible, StoryBibleV2):
            raise TypeError("V2 story_graph requires a sealed StoryBibleV2")
        validate_story_graph(
            payload,
            brief,
            bible=bible if isinstance(bible, StoryBibleV2) else None,
        )  # type: ignore[arg-type]
        return None
    if stage == StageName.SCENE_BEATS:
        if not isinstance(payload, SceneBeatPlanV2) or not isinstance(bible, StoryBibleV2) or not isinstance(graph, StoryGraphV2):
            raise TypeError("V2 scene_beats requires SceneBeatPlanV2, StoryBibleV2, and StoryGraphV2")
        validate_scene_beat_coverage(payload, graph, bible)  # type: ignore[arg-type]
        _validate_v2_scene_order_and_continuity(payload, bible)
        _validate_v2_dialogue_cues(
            payload,
            bible,
            timing_profile=dialogue_timing_profile,
        )
        _validate_v2_scene_timing_allocation(payload, graph, brief)
        return None
    if not isinstance(payload, StoryboardV2) or not isinstance(bible, StoryBibleV2) or not isinstance(scene_beats, SceneBeatPlanV2):
        raise TypeError("V2 storyboard requires StoryboardV2, StoryBibleV2, and SceneBeatPlanV2")
    evaluation = StoryboardGateEvaluator().evaluate(
        payload,
        scene_beats,
        bible,
        brief,
        timing_profile=dialogue_timing_profile or default_dialogue_timing_profile(),
    )
    failed = [result for result in evaluation.results if not result.passed]
    if failed:
        raise DomainValidationError(
            _issue(
                f"gate.{result.gate_id}",
                ".".join(str(part) for part in result.entity_path),
                result.reason or f"V2 gate {result.gate_id} did not pass ({result.status.value})",
            )
            for result in failed
        )
    return evaluation
