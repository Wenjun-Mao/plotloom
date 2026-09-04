"""Shared, provider-free semantic checks for generated V2 fragments.

The work-unit adapter owns prompt rendering, binding, and correction evidence.
These helpers own only the invariant checks that must agree with canonical
V2 validation before a fragment can be sealed into an aggregate.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from pydantic import ValidationError

from ..canonical_schema import ContinuityStateV2, EntityType, RequiredEntityState
from ..domain import StoryBibleV2
from ..json_value_contract import (
    CanonicalJsonValueError,
    finite_canonical_json,
    finite_json_values_equal,
)
from .contracts import ValidationIssue


class FragmentSemanticContextError(ValueError):
    """Trusted fragment context is incomplete or no longer canonical-shaped."""


@dataclass(frozen=True)
class ContinuityAssignmentCandidate:
    """One exact boundary-owner continuity assignment.

    The work-unit layer binds these value-level differences to response-local
    endpoint identities.  Keeping this comparison provider-free ensures the
    repair compiler and the canonical validator share one definition of an
    incompatible boundary.
    """

    kind: Literal["fact", "entity_state", "scalar"]
    expected_value: Any
    fact_key: str | None = None
    entity_type: EntityType | None = None
    entity_id: str | None = None
    scalar_field: Literal["screen_direction", "lighting", "sound"] | None = None


@dataclass(frozen=True)
class ContinuityBoundaryDifference:
    """All repairable differences at one ordered sequence boundary."""

    boundary_index: int
    assignments: tuple[ContinuityAssignmentCandidate, ...]


def continuity_state_issues(
    state: ContinuityStateV2,
    *,
    bible: StoryBibleV2,
    path: tuple[str | int, ...],
) -> tuple[ValidationIssue, ...]:
    """Return Bible-vocabulary failures with response-local paths."""

    allowed_states = allowed_entity_states(bible)
    issues: list[ValidationIssue] = []
    for fact_key, fact_value in state.facts.items():
        try:
            finite_canonical_json(fact_value)
        except CanonicalJsonValueError:
            issues.append(
                ValidationIssue(
                    code="semantic.continuity_fact_not_json",
                    path=(*path, "facts", fact_key),
                    message="continuity facts must be finite canonical JSON values",
                )
            )
    for state_index, entity_state in enumerate(state.entity_states):
        allowed = allowed_states[entity_state.entity_type].get(entity_state.entity_id)
        entity_path = (*path, "entityStates", state_index)
        if allowed is None:
            issues.append(
                ValidationIssue(
                    code="semantic.unknown_continuity_entity",
                    path=(*entity_path, "entityId"),
                    message="continuity state references an entity absent from the Story Bible",
                )
            )
        elif entity_state.state not in allowed:
            issues.append(
                ValidationIssue(
                    code="semantic.invalid_continuity_entity_state",
                    path=(*entity_path, "state"),
                    message="continuity state is not allowed by the Story Bible",
                )
            )
    return tuple(issues)


def allowed_entity_states(
    bible: StoryBibleV2,
) -> dict[EntityType, dict[str, set[str]]]:
    return {
        EntityType.CHARACTER: {
            entity.id: set(entity.allowed_states) for entity in bible.characters
        },
        EntityType.LOCATION: {
            entity.id: set(entity.allowed_states) for entity in bible.locations
        },
        EntityType.PROP: {
            entity.id: set(entity.allowed_states) for entity in bible.props
        },
    }


def continuity_sequence_is_compatible(
    entry_state: ContinuityStateV2,
    ordered_items: Sequence[Any],
    exit_state: ContinuityStateV2,
) -> bool:
    """Match the canonical compatibility rule without importing stage binders."""

    prior = entry_state
    for item in ordered_items:
        if not continuity_states_are_compatible(prior, item.entry_state):
            return False
        prior = item.exit_state
    return continuity_states_are_compatible(prior, exit_state)


def continuity_sequence_repair_boundaries(
    entry_state: ContinuityStateV2,
    ordered_items: Sequence[Any],
    exit_state: ContinuityStateV2,
    *,
    bible: StoryBibleV2,
    final_boundary_source: Literal["last_item_exit", "sequence_exit"] = "last_item_exit",
) -> tuple[ContinuityBoundaryDifference, ...] | None:
    """Return every safe ordered repair boundary, or no authority.

    A compatibility mismatch alone does not prove that either endpoint is a
    valid repair source.  The caller may use this result only after every
    participating state has finite facts, unique entity identities, and valid
    Story Bible entity states.  ``None`` deliberately means fail closed;
    callers must leave the more precise validation failures in place.
    """

    if not ordered_items:
        return ()
    states = [entry_state, exit_state]
    for item in ordered_items:
        states.extend((item.entry_state, item.exit_state))
    if any(not _entity_states_are_unique(state) for state in states):
        return None
    if any(continuity_state_issues(state, bible=bible, path=()) for state in states):
        return None

    pairs: list[tuple[ContinuityStateV2, ContinuityStateV2]] = [
        (entry_state, ordered_items[0].entry_state)
    ]
    pairs.extend(
        (previous.exit_state, following.entry_state)
        for previous, following in zip(ordered_items, ordered_items[1:])
    )
    if final_boundary_source == "last_item_exit":
        pairs.append((ordered_items[-1].exit_state, exit_state))
    else:
        # Storyboard's enclosing scene is frozen canonical context.  It owns
        # its exit boundary even though compatibility itself is symmetric.
        pairs.append((exit_state, ordered_items[-1].exit_state))

    differences: list[ContinuityBoundaryDifference] = []
    for boundary_index, (source, target) in enumerate(pairs):
        assignments = continuity_state_repair_assignments(source, target)
        if assignments:
            differences.append(
                ContinuityBoundaryDifference(
                    boundary_index=boundary_index,
                    assignments=assignments,
                )
            )
    return tuple(differences)


def continuity_state_repair_assignments(
    source: ContinuityStateV2,
    target: ContinuityStateV2,
) -> tuple[ContinuityAssignmentCandidate, ...]:
    """Compile only incompatible shared declarations from source to target."""

    assignments: list[ContinuityAssignmentCandidate] = []
    for key in sorted(set(source.facts) & set(target.facts)):
        source_value = source.facts[key]
        target_value = target.facts[key]
        try:
            equal = finite_json_values_equal(source_value, target_value)
        except CanonicalJsonValueError:
            # The sequence compiler gates finite JSON before this comparison.
            # Treat an unexpected violation as no repair authority.
            return ()
        if not equal:
            assignments.append(
                ContinuityAssignmentCandidate(
                    kind="fact",
                    fact_key=key,
                    expected_value=deepcopy(source_value),
                )
            )

    source_entities = {
        (item.entity_type, item.entity_id): item.state for item in source.entity_states
    }
    target_entities = {
        (item.entity_type, item.entity_id): item.state for item in target.entity_states
    }
    for entity_type, entity_id in sorted(
        set(source_entities) & set(target_entities),
        key=lambda item: (item[0].value, item[1]),
    ):
        if source_entities[(entity_type, entity_id)] != target_entities[(entity_type, entity_id)]:
            assignments.append(
                ContinuityAssignmentCandidate(
                    kind="entity_state",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    expected_value=source_entities[(entity_type, entity_id)],
                )
            )

    for field in ("screen_direction", "lighting", "sound"):
        source_value = getattr(source, field)
        target_value = getattr(target, field)
        if source_value is not None and target_value is not None and source_value != target_value:
            assignments.append(
                ContinuityAssignmentCandidate(
                    kind="scalar",
                    scalar_field=field,
                    expected_value=source_value,
                )
            )
    return tuple(assignments)


def continuity_states_are_compatible(
    left: ContinuityStateV2,
    right: ContinuityStateV2,
) -> bool:
    left_entities = {
        (item.entity_type, item.entity_id): item.state for item in left.entity_states
    }
    right_entities = {
        (item.entity_type, item.entity_id): item.state for item in right.entity_states
    }
    if any(
        left_entities[key] != right_entities[key]
        for key in set(left_entities) & set(right_entities)
    ):
        return False
    try:
        if any(
            not finite_json_values_equal(left.facts[key], right.facts[key])
            for key in set(left.facts) & set(right.facts)
        ):
            return False
    except CanonicalJsonValueError:
        # ``continuity_state_issues`` reports the precise fact path.  Treating
        # an invalid value as incompatible here prevents the sequence helper
        # from ever converting it into an internal validation error.
        return False
    return all(
        getattr(left, field) is None
        or getattr(right, field) is None
        or getattr(left, field) == getattr(right, field)
        for field in ("screen_direction", "lighting", "sound")
    )


def _entity_states_are_unique(state: ContinuityStateV2) -> bool:
    keys = [(item.entity_type, item.entity_id) for item in state.entity_states]
    return len(keys) == len(set(keys))


def continuity_state_from_context(
    scene: Mapping[str, Any],
    field_name: str,
) -> ContinuityStateV2:
    value = scene.get(field_name)
    if not isinstance(value, Mapping):
        raise FragmentSemanticContextError(
            f"Storyboard context has no valid dramatic-scene {field_name}"
        )
    try:
        return ContinuityStateV2.model_validate(value, by_alias=True)
    except ValidationError as exc:
        raise FragmentSemanticContextError(
            f"Storyboard context has invalid dramatic-scene {field_name}"
        ) from exc


def required_entity_is_in_shot(
    required: RequiredEntityState,
    shot: Any,
) -> bool:
    if required.entity_type == EntityType.CHARACTER:
        return required.entity_id in shot.character_ids
    if required.entity_type == EntityType.LOCATION:
        return required.entity_id == shot.location_id
    return required.entity_id in shot.prop_ids


def cue_canonical_order_key(
    cue: Mapping[str, Any],
    *,
    scoped_context: Mapping[str, Any],
) -> tuple[int, int]:
    beat_id = cue.get("beatId")
    cue_order = cue.get("order")
    if not isinstance(beat_id, str) or not isinstance(cue_order, int):
        raise FragmentSemanticContextError("Storyboard context has an invalid dialogue cue")
    for beat in scoped_context.get("beats", []):
        if not isinstance(beat, Mapping) or beat.get("id") != beat_id:
            continue
        beat_order = beat.get("order")
        if isinstance(beat_order, int):
            return beat_order, cue_order
        break
    raise FragmentSemanticContextError(
        "Storyboard context has dialogue cue without a valid selected beat"
    )


def cue_duration_units(cue: Mapping[str, Any]) -> int:
    duration = cue.get("estimatedDurationUnits")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration < 1:
        raise FragmentSemanticContextError(
            "Storyboard context has an invalid dialogue cue duration"
        )
    return duration
