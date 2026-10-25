"""Closed semantic repair union and lossless current evidence codec."""

from __future__ import annotations

from typing import Annotated, Any, TypeAlias, get_args

from pydantic import Field, TypeAdapter

from .continuity_repair_contracts import (
    ContinuityEntityStateRepairFact,
    ContinuityFactAssignment,
    ContinuitySequenceRepairFact,
)
from .dialogue_repair_contracts import (
    CueOrderRepairFact,
    DialogueCapacityRepairFact,
    DialogueNodeBudgetRepairFact,
)
from .graph_repair_contracts import (
    EdgeStateEffectJsonRepairFact,
    JoinAllowedDifferencesRepairFact,
    JoinEntryStateValueRepairFact,
    JoinReconciliationRepairFact,
    JoinStateEffectRepairFact,
)
from .scene_beats_edge_entry import EdgeEntryEntityStateRepairFact
from .storyboard_presence_repair import (
    RequiredEntityPresenceRepairFact,
)
from .storyboard_repair_contracts import (
    AudioTimingRepairFact,
    RequiredEntityStateRepairFact,
)
from .storyboard_timing_repair import StoryboardTimingRepairPlanFact

SemanticRepairFact: TypeAlias = Annotated[
    DialogueCapacityRepairFact
    | DialogueNodeBudgetRepairFact
    | CueOrderRepairFact
    | StoryboardTimingRepairPlanFact
    | JoinAllowedDifferencesRepairFact
    | JoinStateEffectRepairFact
    | ContinuitySequenceRepairFact
    | EdgeStateEffectJsonRepairFact
    | JoinReconciliationRepairFact
    | JoinEntryStateValueRepairFact
    | EdgeEntryEntityStateRepairFact
    | AudioTimingRepairFact
    | RequiredEntityStateRepairFact
    | RequiredEntityPresenceRepairFact
    | ContinuityEntityStateRepairFact,
    Field(discriminator="code"),
]

# The discriminated union is the closed admission authority, including exact types.
SEMANTIC_REPAIR_FACT_TYPES = get_args(get_args(SemanticRepairFact)[0])
_SEMANTIC_REPAIR_FACT_ADAPTER = TypeAdapter(SemanticRepairFact)


def parse_semantic_repair_fact(value: Any) -> SemanticRepairFact:
    """Revalidate current repair evidence; retired witness shapes are rejected."""
    return _SEMANTIC_REPAIR_FACT_ADAPTER.validate_python(value)


def serialize_semantic_repair_fact(fact: SemanticRepairFact) -> dict[str, Any]:
    """Serialize current evidence, preserving authorized JSON null assignments."""

    payload = fact.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(fact, JoinStateEffectRepairFact) and fact.has_expected_value:
        payload["expectedValue"] = fact.expected_value
    if isinstance(fact, JoinStateEffectRepairFact):
        # A preserved sibling may deliberately be JSON null.  Unlike the
        # repair target, every preserved assignment carries exact authority,
        # so restore nulls stripped by ``exclude_none`` at every nested edge.
        for serialized_effect, effect in zip(
            payload.get("preservedStateEffects", []),
            fact.preserved_state_effects,
            strict=True,
        ):
            for serialized_incoming, incoming in zip(
                serialized_effect["incomingEffects"],
                effect.incoming_effects,
                strict=True,
            ):
                serialized_incoming["expectedValue"] = incoming.expected_value
    if isinstance(fact, ContinuitySequenceRepairFact):
        # ``exclude_none`` is correct for optional evidence fields, but a
        # continuity fact assignment may deliberately copy JSON null.  Keep
        # that value so persisted facts remain executable and round-trip.
        for serialized_boundary, boundary in zip(
            payload["boundaries"], fact.boundaries, strict=True
        ):
            for serialized_assignment, assignment in zip(
                serialized_boundary["assignments"], boundary.assignments, strict=True
            ):
                if isinstance(assignment, ContinuityFactAssignment):
                    serialized_assignment["expectedValue"] = assignment.expected_value
    return payload
