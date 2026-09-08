"""Provider-independent verification for exact correction repair authority.

The base fragment contract is validated before this module runs.  These
postconditions intentionally repeat the small subset of correction authority
that must be exact at application level, so acceptance does not depend on a
provider honouring a native JSON Schema overlay.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..json_value_contract import CanonicalJsonValueError, finite_json_values_equal
from .contracts import ValidationIssue
from .work_units import (
    ContinuityEntityStateAssignment,
    ContinuityFactAssignment,
    ContinuityScalarAssignment,
    ContinuitySequenceRepairFact,
    CueOrderRepairFact,
    JoinAllowedDifferencesRepairFact,
    JoinStateEffectRepairFact,
    SemanticRepairFact,
    StoryboardTimingRepairPlanFact,
)


_MISMATCH_CODE = "contract.correction_output_constraint_mismatch"
_MISMATCH_MESSAGE = "Correction output does not satisfy an exact repair constraint."
_CONTINUITY_COLLECTIONS = {
    "scene": ("scenes", "localSceneId"),
    "beat": ("beats", "localBeatId"),
    "shot": ("shots", "localShotId"),
}


def validate_correction_postconditions(
    response: Any,
    facts: Sequence[SemanticRepairFact],
) -> tuple[ValidationIssue, ...]:
    """Check executable exact repair facts against one decoded response.

    Facts without an application-level exact check are deliberately ignored.
    Any malformed response shape relevant to a supported fact is a mismatch;
    this avoids accepting an ambiguous repair after a provider bypasses or
    weakly implements a response schema.
    """

    ordered_facts = sorted(
        enumerate(facts),
        key=lambda item: (_fact_sort_key(item[1]), item[0]),
    )
    issues: list[ValidationIssue] = []
    for _, fact in ordered_facts:
        if isinstance(fact, JoinAllowedDifferencesRepairFact):
            valid = _join_allowed_differences_satisfied(response, fact)
        elif isinstance(fact, JoinStateEffectRepairFact):
            valid = _join_state_effect_satisfied(response, fact)
        elif isinstance(fact, ContinuitySequenceRepairFact):
            valid = _continuity_sequence_satisfied(response, fact)
        elif isinstance(fact, CueOrderRepairFact):
            valid = _cue_order_satisfied(response, fact)
        elif isinstance(fact, StoryboardTimingRepairPlanFact):
            valid = _storyboard_timing_plan_satisfied(response, fact)
        else:
            continue
        if not valid:
            issues.append(
                ValidationIssue(
                    code=_MISMATCH_CODE,
                    path=fact.path,
                    message=_MISMATCH_MESSAGE,
                )
            )
    return tuple(issues)


def _fact_sort_key(
    fact: SemanticRepairFact,
) -> tuple[str, tuple[tuple[int, str], ...]]:
    """Sort checks independent of the correction-fact input order."""

    return (
        fact.code,
        tuple(
            (0, str(part)) if isinstance(part, int) else (1, part)
            for part in fact.path
        ),
    )


def _join_allowed_differences_satisfied(
    response: Any,
    fact: JoinAllowedDifferencesRepairFact,
) -> bool:
    if (
        fact.expected_required_state_keys is None
        or fact.expected_allowed_differences is None
    ):
        return False
    join = _unique_collection_item(
        response, "joinContracts", "id", fact.join_contract_id
    )
    if join is None:
        return False
    if not _finite_equal(
        join.get("requiredStateKeys"), list(fact.expected_required_state_keys)
    ):
        return False
    if not _finite_equal(
        join.get("allowedDifferences"), list(fact.expected_allowed_differences)
    ):
        return False
    if fact.new_required_key_incoming_edges is None:
        return True
    for state_key_scope in fact.new_required_key_incoming_edges:
        for edge in state_key_scope.incoming_edges:
            selected_edge = _unique_collection_item(
                response, "edges", "id", edge.edge_id
            )
            if selected_edge is None:
                return False
            state_effects = selected_edge.get("stateEffects")
            if (
                not isinstance(state_effects, Mapping)
                or state_key_scope.state_key not in state_effects
            ):
                return False
    return True


def _join_state_effect_satisfied(
    response: Any,
    fact: JoinStateEffectRepairFact,
) -> bool:
    for edge in fact.incoming_edges:
        selected_edge = _unique_collection_item(response, "edges", "id", edge.edge_id)
        if selected_edge is None:
            return False
        state_effects = selected_edge.get("stateEffects")
        if not isinstance(state_effects, Mapping) or fact.state_key not in state_effects:
            return False
        if fact.has_expected_value and not _finite_equal(
            state_effects[fact.state_key], fact.expected_value
        ):
            return False
    for preserved_effect in fact.preserved_state_effects:
        for incoming_effect in preserved_effect.incoming_effects:
            selected_edge = _unique_collection_item(
                response, "edges", "id", incoming_effect.edge_id
            )
            if selected_edge is None:
                return False
            state_effects = selected_edge.get("stateEffects")
            if (
                not isinstance(state_effects, Mapping)
                or preserved_effect.state_key not in state_effects
                or not _finite_equal(
                    state_effects[preserved_effect.state_key],
                    incoming_effect.expected_value,
                )
            ):
                return False
    return True


def _continuity_sequence_satisfied(
    response: Any,
    fact: ContinuitySequenceRepairFact,
) -> bool:
    for boundary in fact.boundaries:
        target = boundary.target
        if target.id_scope != "response_local":
            return False
        collection_details = _CONTINUITY_COLLECTIONS.get(target.kind)
        if collection_details is None:
            return False
        collection, identity_field = collection_details
        target_item = _unique_collection_item(
            response, collection, identity_field, target.id
        )
        if target_item is None:
            return False
        state = target_item.get(
            "entryState" if target.state == "entry" else "exitState"
        )
        if not isinstance(state, Mapping):
            return False
        for assignment in boundary.assignments:
            if isinstance(assignment, ContinuityFactAssignment):
                facts = state.get("facts")
                if not isinstance(facts, Mapping) or assignment.key not in facts:
                    return False
                if not _finite_equal(facts[assignment.key], assignment.expected_value):
                    return False
            elif isinstance(assignment, ContinuityEntityStateAssignment):
                if not _entity_assignment_satisfied(state, assignment):
                    return False
            elif isinstance(assignment, ContinuityScalarAssignment):
                if assignment.field not in state or not _finite_equal(
                    state[assignment.field], assignment.expected_value
                ):
                    return False
            else:
                return False
    return True


def _entity_assignment_satisfied(
    state: Mapping[str, Any],
    assignment: ContinuityEntityStateAssignment,
) -> bool:
    entity_states = state.get("entityStates")
    if not isinstance(entity_states, list):
        return False
    matching = []
    for entity_state in entity_states:
        if not isinstance(entity_state, Mapping):
            return False
        if (
            entity_state.get("entityType") == assignment.entity_type.value
            and entity_state.get("entityId") == assignment.entity_id
        ):
            matching.append(entity_state)
    return len(matching) == 1 and _finite_equal(
        matching[0].get("state"), assignment.expected_state
    )


def _cue_order_satisfied(response: Any, fact: CueOrderRepairFact) -> bool:
    cues = _collection(response, "dialogueCues")
    if cues is None or len(cues) != len(fact.assignments):
        return False
    expected_by_id = {
        assignment.local_cue_id: (assignment.beat_local_id, assignment.expected_order)
        for assignment in fact.assignments
    }
    if len(expected_by_id) != len(fact.assignments):
        return False
    actual_ids: set[str] = set()
    actual_beat_orders: set[tuple[str, int]] = set()
    for cue in cues:
        if not isinstance(cue, Mapping):
            return False
        cue_id = cue.get("localCueId")
        beat_id = cue.get("beatLocalId")
        order = cue.get("order")
        if (
            not isinstance(cue_id, str)
            or not isinstance(beat_id, str)
            or type(order) is not int
        ):
            return False
        expected = expected_by_id.get(cue_id)
        if expected is None or expected != (beat_id, order):
            return False
        if cue_id in actual_ids or (beat_id, order) in actual_beat_orders:
            return False
        actual_ids.add(cue_id)
        actual_beat_orders.add((beat_id, order))
    return actual_ids == set(expected_by_id)


def _storyboard_timing_plan_satisfied(
    response: Any,
    fact: StoryboardTimingRepairPlanFact,
) -> bool:
    """Require the complete plan-owned timing and coverage replacement.

    ``removeAudioEventIndexes`` is source-relative removal guidance, so it
    cannot be proven from the replacement alone. Remaining audio timing is
    still checked by the ordinary Storyboard validator. The fields below are
    self-contained in the target plan and therefore form executable authority.
    """

    shots = _collection(response, "shots")
    if shots is None or len(shots) != len(fact.plan.target_shots):
        return False
    expected_by_id = {
        target.local_shot_id: target for target in fact.plan.target_shots
    }
    if len(expected_by_id) != len(fact.plan.target_shots):
        return False
    actual_ids: set[str] = set()
    for shot in shots:
        if not isinstance(shot, Mapping):
            return False
        local_shot_id = shot.get("localShotId")
        if not isinstance(local_shot_id, str) or local_shot_id in actual_ids:
            return False
        target = expected_by_id.get(local_shot_id)
        if target is None:
            return False
        if not _finite_equal(shot.get("order"), target.target_order):
            return False
        if not _finite_equal(
            shot.get("durationUnits"), target.target_duration_units
        ):
            return False
        if not _finite_equal(shot.get("cueIds"), list(target.target_cue_ids)):
            return False
        actual_ids.add(local_shot_id)
    if actual_ids != set(expected_by_id):
        return False

    if not isinstance(response, Mapping):
        return False
    expected_primary = {
        link.beat_id: link.shot_local_id
        for link in fact.plan.target_primary_links
    }
    if not _finite_equal(
        response.get("primaryShotLocalIdByBeat"), expected_primary
    ):
        return False
    expected_supporting = [
        {
            "shotLocalId": link.shot_local_id,
            "beatId": link.beat_id,
            "coverageWeight": link.coverage_weight,
        }
        for link in fact.plan.target_supporting_links
    ]
    return _finite_equal(response.get("supportingBeatLinks"), expected_supporting)


def _unique_collection_item(
    response: Any,
    collection_name: str,
    identity_field: str,
    expected_identity: str,
) -> Mapping[str, Any] | None:
    collection = _collection(response, collection_name)
    if collection is None:
        return None
    matching: list[Mapping[str, Any]] = []
    for item in collection:
        if not isinstance(item, Mapping) or not isinstance(
            item.get(identity_field), str
        ):
            return None
        if item[identity_field] == expected_identity:
            matching.append(item)
    return matching[0] if len(matching) == 1 else None


def _collection(response: Any, name: str) -> list[Any] | None:
    if not isinstance(response, Mapping):
        return None
    value = response.get(name)
    return value if isinstance(value, list) else None


def _finite_equal(actual: Any, expected: Any) -> bool:
    try:
        return finite_json_values_equal(actual, expected)
    except CanonicalJsonValueError:
        return False
