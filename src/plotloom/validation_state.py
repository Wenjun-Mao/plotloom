from __future__ import annotations

from .canonical_schema import EntityType, StoryBibleV2
from .json_value_contract import CanonicalJsonValueError, finite_canonical_json, finite_json_values_equal
from .validation_issues import DomainValidationError, ValidationIssue, _duplicates, _issue

def _continuity_state_issues(
    path_prefix: str,
    continuity_state,
    bible: StoryBibleV2,
) -> list[ValidationIssue]:
    allowed_states = _allowed_entity_states(bible)
    issues: list[ValidationIssue] = []
    for fact_key, fact_value in continuity_state.facts.items():
        try:
            finite_canonical_json(fact_value)
        except CanonicalJsonValueError:
            issues.append(
                _issue(
                    "continuity_fact_not_json",
                    f"{path_prefix}.facts.{fact_key}",
                    "continuity facts must be finite canonical JSON values",
                )
            )
    for index, state in enumerate(continuity_state.entity_states):
        known_states = allowed_states[state.entity_type].get(state.entity_id)
        state_path = f"{path_prefix}.entityStates.{index}"
        if known_states is None:
            issues.append(
                _issue(
                    "unknown_continuity_entity",
                    f"{state_path}.entityId",
                    "continuity state references an entity absent from the story bible",
                )
            )
        elif state.state not in known_states:
            issues.append(
                _issue(
                    "invalid_continuity_entity_state",
                    f"{state_path}.state",
                    "continuity state is not allowed by the story bible",
                )
            )
    return issues


def _allowed_entity_states(
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


def _continuity_sequence_is_compatible(entry_state, shots, exit_state) -> bool:
    prior = entry_state
    for shot in shots:
        if not _continuity_states_are_compatible(prior, shot.entry_state):
            return False
        prior = shot.exit_state
    return _continuity_states_are_compatible(prior, exit_state)


def _continuity_states_are_compatible(left, right) -> bool:
    if not _continuity_entity_states_are_unique(left) or not _continuity_entity_states_are_unique(right):
        return False
    left_entities = {(state.entity_type, state.entity_id): state.state for state in left.entity_states}
    right_entities = {(state.entity_type, state.entity_id): state.state for state in right.entity_states}
    for key in set(left_entities) & set(right_entities):
        if left_entities[key] != right_entities[key]:
            return False
    try:
        for key in set(left.facts) & set(right.facts):
            if not finite_json_values_equal(left.facts[key], right.facts[key]):
                return False
    except CanonicalJsonValueError:
        return False
    for field in ("screen_direction", "lighting", "sound"):
        left_value = getattr(left, field)
        right_value = getattr(right, field)
        if left_value is not None and right_value is not None and left_value != right_value:
            return False
    return True


def _continuity_entity_states_are_unique(state) -> bool:
    keys = [(item.entity_type, item.entity_id) for item in state.entity_states]
    return len(keys) == len(set(keys))
