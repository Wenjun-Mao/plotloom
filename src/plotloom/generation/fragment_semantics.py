"""Shared, provider-free semantic checks for generated V2 fragments.

The work-unit adapter owns prompt rendering, binding, and correction evidence.
These helpers own only the invariant checks that must agree with canonical
V2 validation before a fragment can be sealed into an aggregate.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

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
