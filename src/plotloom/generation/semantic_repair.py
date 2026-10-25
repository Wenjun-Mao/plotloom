"""Explicit stage/family repair dispatch and exact stable-issue admission."""

from __future__ import annotations

from typing import Any, Mapping

from ..domain import (
    DialogueTimingProfile,
    StageName,
    StoryBibleV2,
)
from .continuity_repair import (
    continuity_sequence_repair_facts,
)
from .contracts import ValidationIssue
from .dialogue_capacity import (
    DialogueCapacityNodeGuidance,
)
from .entity_state_repair import (
    continuity_entity_state_repair_facts,
    storyboard_required_entity_state_repair_facts,
)
from .graph_semantic_repair import (
    _story_graph_edge_state_effect_json_repair_facts,
    _story_graph_join_repair_facts,
)
from .repair_facts import SemanticRepairFact
from .scene_beats_dialogue_repair import (
    scene_beats_cue_order_repair_facts,
    scene_beats_dialogue_capacity_repair_facts,
    scene_beats_dialogue_node_budget_repair_facts,
)
from .scene_beats_edge_entry import (
    edge_entry_entity_state_repair_facts,
    edge_entry_state_requirements,
)
from .scene_beats_join_repair import (
    scene_beats_join_entry_repair_facts,
)
from .story_graph_topology import (
    StoryGraphTopology,
)
from .storyboard_audio_repair import (
    storyboard_audio_timing_repair_facts,
)
from .storyboard_presence_repair import (
    storyboard_required_entity_presence_repair_facts,
)
from .storyboard_timing_repair import (
    StoryboardTimingGuidance,
    storyboard_timing_repair_facts,
)


def semantic_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    stage: StageName,
    bible: StoryBibleV2 | None = None,
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None = None,
    dialogue_timing_profile: DialogueTimingProfile | None = None,
    node_duration_budget_units: int | None = None,
    join_state_value_requirements: Mapping[str, Any] | None = None,
    storyboard_timing_guidance: StoryboardTimingGuidance | None = None,
    story_graph_topology: StoryGraphTopology | None = None,
    scoped_context: Mapping[str, Any] | None = None,
) -> tuple[SemanticRepairFact, ...]:
    """Route stable issues to versioned, stage-owned deterministic facts."""

    if stage == StageName.STORY_GRAPH:
        return (
            *_story_graph_edge_state_effect_json_repair_facts(
                value,
                issues,
                topology=story_graph_topology,
            ),
            *_story_graph_join_repair_facts(
                value,
                issues,
                topology=story_graph_topology,
            ),
        )
    if stage == StageName.STORYBOARD:
        continuity_entity_state_facts = (
            continuity_entity_state_repair_facts(
                value, issues, stage=stage, bible=bible
            )
            if bible is not None
            else ()
        )
        continuity_facts = continuity_sequence_repair_facts(
            value,
            issues,
            stage=stage,
            bible=bible,
            scoped_context=scoped_context,
        )
        required_entity_state_facts = (
            storyboard_required_entity_state_repair_facts(
                value,
                issues,
                bible=bible,
            )
            if bible is not None
            else ()
        )
        required_entity_presence_facts = (
            storyboard_required_entity_presence_repair_facts(value, issues)
        )
        timing_facts = storyboard_timing_repair_facts(
            value,
            issues,
            guidance=storyboard_timing_guidance,
        )
        audio_facts = (
            () if timing_facts else storyboard_audio_timing_repair_facts(value, issues)
        )
        return (
            *continuity_entity_state_facts,
            *continuity_facts,
            *required_entity_state_facts,
            *required_entity_presence_facts,
            *timing_facts,
            *audio_facts,
        )
    if stage == StageName.SCENE_BEATS:
        entity_state_facts = (
            continuity_entity_state_repair_facts(
                value, issues, stage=stage, bible=bible
            )
            if bible is not None
            else ()
        )
        continuity_facts = continuity_sequence_repair_facts(
            value,
            issues,
            stage=stage,
            bible=bible,
            scoped_context=scoped_context,
        )
        capacity_facts = (
            scene_beats_dialogue_capacity_repair_facts(
                value,
                issues,
                guidance=dialogue_capacity_guidance,
            )
            if dialogue_capacity_guidance is not None
            else ()
        )
        join_facts = (
            scene_beats_join_entry_repair_facts(
                value,
                issues,
                requirements=join_state_value_requirements,
            )
            if join_state_value_requirements is not None
            else ()
        )
        edge_entry_facts = (
            edge_entry_entity_state_repair_facts(
                value,
                issues,
                requirements=edge_entry_state_requirements(scoped_context),
            )
            if scoped_context is not None
            else ()
        )
        node_budget_facts = scene_beats_dialogue_node_budget_repair_facts(
            value,
            issues,
            node_id=(
                dialogue_capacity_guidance.node_id
                if dialogue_capacity_guidance is not None
                else ""
            ),
            node_duration_budget_units=node_duration_budget_units,
            dialogue_timing_profile=dialogue_timing_profile,
            dialogue_capacity_guidance=dialogue_capacity_guidance,
        )
        cue_order_facts = scene_beats_cue_order_repair_facts(value, issues)
        return (
            *entity_state_facts,
            *continuity_facts,
            *capacity_facts,
            *join_facts,
            *edge_entry_facts,
            *node_budget_facts,
            *cue_order_facts,
        )
    return ()


def assert_semantic_repair_fact_matches_issue(
    fact: SemanticRepairFact,
    issues: tuple[ValidationIssue, ...],
) -> None:
    """Bind persisted repair authority to one exact stable rejection.

    A syntactically valid fact is not sufficient: it must name the same code
    and data path as an issue in the immutable validation artifact which
    authorizes this correction attempt.
    """

    if not any(issue.code == fact.code and issue.path == fact.path for issue in issues):
        raise ValueError(
            "deterministic repair fact has no matching stable validation issue"
        )
