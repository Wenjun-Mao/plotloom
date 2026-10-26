"""Derive capacity, cue-order and node-budget repairs with cue source assertions."""

from __future__ import annotations

from typing import Any

from pydantic import (
    ValidationError,
)

from plotloom.canonical_schema import DialogueDeliveryPace, DialogueTimingProfile
from .contracts import ValidationIssue
from .dialogue_capacity import (
    DialogueCapacityNodeGuidance,
    DialogueCapacityRuleGuidance,
)
from .dialogue_repair_contracts import (
    CueOrderRepairAssignment,
    CueOrderRepairFact,
    DialogueCapacityDeliveryLimit,
    DialogueCapacityRepairFact,
    DialogueNodeBudgetRemainingCue,
    DialogueNodeBudgetRepairFact,
)
from .repair_facts import SemanticRepairFact
from .scene_response_contracts import (
    DialogueCueContent,
    SceneBeatsFragmentOutput,
)


def scene_beats_dialogue_capacity_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    guidance: DialogueCapacityNodeGuidance,
) -> tuple[DialogueCapacityRepairFact, ...]:
    """Derive exact cue caps from schema-valid output and frozen guidance.

    A malformed response, an issue for another field, a language outside the
    frozen ProjectBrief, or a rule that cannot be proved from the sealed plan
    receives no fact.  That keeps corrections from gaining authority through
    guessed indexes or current process configuration.
    """

    if (
        guidance.authoring_language is None
        or guidance.schema_max_text_codepoints is None
    ):
        return ()
    relevant_issues = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.dialogue_cue_capacity_exceeded"
    )
    if not relevant_issues:
        return ()
    try:
        output = SceneBeatsFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()

    def rule_for(
        language: str,
        delivery: DialogueDeliveryPace,
    ) -> DialogueCapacityRuleGuidance | None:
        exact = next(
            (
                rule
                for rule in guidance.rule_guidance
                if rule.language == language and rule.delivery == delivery
            ),
            None,
        )
        if exact is not None:
            return exact
        return next(
            (
                rule
                for rule in guidance.rule_guidance
                if rule.language == "*" and rule.delivery == delivery
            ),
            None,
        )

    compatible_limits: list[DialogueCapacityDeliveryLimit] = []
    for delivery in DialogueDeliveryPace:
        rule = rule_for(guidance.authoring_language, delivery)
        if rule is None:
            return ()
        compatible_limits.append(
            DialogueCapacityDeliveryLimit(
                delivery=delivery,
                max_text_codepoints=min(
                    rule.max_text_codepoints,
                    guidance.schema_max_text_codepoints,
                ),
            )
        )
    limits = tuple(compatible_limits)
    facts: list[DialogueCapacityRepairFact] = []
    for issue in relevant_issues:
        path = issue.path
        if (
            len(path) != 3
            or path[0] != "dialogueCues"
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[2] != "text"
            or path[1] >= len(output.dialogue_cues)
        ):
            continue
        cue = output.dialogue_cues[path[1]]
        if cue.language != guidance.authoring_language:
            continue
        limit = next(item for item in limits if item.delivery == cue.delivery)
        if len(cue.text.strip()) <= limit.max_text_codepoints:
            # The issue was caused by a different invariant; do not invent a
            # text-shortening authority for it.
            continue
        facts.append(
            DialogueCapacityRepairFact(
                code=issue.code,
                path=path,
                authoring_language=guidance.authoring_language,
                language=cue.language,
                delivery=cue.delivery,
                current_text_codepoints=len(cue.text.strip()),
                max_text_codepoints=limit.max_text_codepoints,
                compatible_delivery_limits=limits,
            )
        )
    return tuple(facts)


_CUE_ORDER_COLLECTION_MUTATION_CODES = frozenset(
    {
        # These repairs can remove or rename a cue/beat.  A complete
        # membership-preserving overlay would conflict with that authority, so
        # cue order must wait for the structurally safe rejection that follows.
        "semantic.dialogue_cue_count_exceeded",
        "semantic.dialogue_exceeds_node_budget",
        "semantic.duplicate_beat_id",
        "semantic.duplicate_cue_id",
        "semantic.cross_unit_beat",
        "semantic.cross_unit_cue",
        "semantic.scene_capacity_exceeded",
    }
)


def scene_beats_cue_order_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
) -> tuple[CueOrderRepairFact, ...]:
    """Derive a complete, source-bound cue renumbering when identity is safe.

    Cue order is validated across a collection, rather than at one index.  A
    correction therefore receives the complete response-local membership map,
    not a guessed target cue.  If another stable issue can delete, rename, or
    reassign a cue, no fact is emitted: an exact membership repair would be
    contradictory and must not be fabricated.
    """

    relevant = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.cue_order" and issue.path == ("dialogueCues",)
    )
    if not relevant or any(
        issue.code in _CUE_ORDER_COLLECTION_MUTATION_CODES for issue in issues
    ):
        return ()
    try:
        output = SceneBeatsFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()

    beat_ids = [beat.local_beat_id for beat in output.beats]
    cue_ids = [cue.local_cue_id for cue in output.dialogue_cues]
    known_beat_ids = set(beat_ids)
    if (
        len(beat_ids) != len(set(beat_ids))
        or len(cue_ids) != len(set(cue_ids))
        or any(not beat_id.strip() for beat_id in beat_ids)
        or any(not cue_id.strip() for cue_id in cue_ids)
        or any(cue.beat_local_id not in known_beat_ids for cue in output.dialogue_cues)
    ):
        return ()

    cues_by_beat: dict[str, list[tuple[int, DialogueCueContent]]] = {}
    for source_index, cue in enumerate(output.dialogue_cues):
        cues_by_beat.setdefault(cue.beat_local_id, []).append((source_index, cue))

    assignments: list[CueOrderRepairAssignment] = []
    source_is_invalid = False
    for beat_id in beat_ids:
        # This is the validator's ordering with the response index made
        # explicit as a deterministic duplicate-order tie breaker.
        ordered = sorted(
            cues_by_beat.get(beat_id, ()),
            key=lambda item: (item[1].order, item[0]),
        )
        if [cue.order for _index, cue in ordered] != list(range(1, len(ordered) + 1)):
            source_is_invalid = True
        assignments.extend(
            CueOrderRepairAssignment(
                local_cue_id=cue.local_cue_id,
                beat_local_id=beat_id,
                expected_order=expected_order,
            )
            for expected_order, (_index, cue) in enumerate(ordered, start=1)
        )
    if not source_is_invalid:
        # Do not turn an issue from another validator layer into authority for
        # an otherwise valid source collection.
        return ()
    canonical_assignments = tuple(
        sorted(assignments, key=lambda item: item.local_cue_id)
    )
    return tuple(
        CueOrderRepairFact(
            code=issue.code,
            path=issue.path,
            assignments=canonical_assignments,
        )
        for issue in relevant
    )


def scene_beats_dialogue_node_budget_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
    *,
    node_id: str,
    node_duration_budget_units: int | None,
    dialogue_timing_profile: DialogueTimingProfile | None,
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None,
) -> tuple[DialogueNodeBudgetRepairFact, ...]:
    """Create a deterministic delete-and-renumber plan for a global overage.

    It is intentionally conservative: if the rejected fragment is not
    unambiguous under exactly the same frozen inputs used by semantic
    validation, no fact is emitted and no repair authority is fabricated.
    """

    relevant = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.dialogue_exceeds_node_budget"
    )
    if (
        not relevant
        or node_duration_budget_units is None
        or dialogue_timing_profile is None
        or dialogue_capacity_guidance is None
    ):
        return ()
    try:
        output = SceneBeatsFragmentOutput.model_validate(
            value, by_alias=True, by_name=False
        )
    except ValidationError:
        return ()
    scene_ids = {scene.local_scene_id for scene in output.scenes}
    beat_ids = {beat.local_beat_id for beat in output.beats}
    cue_ids = [cue.local_cue_id for cue in output.dialogue_cues]
    if (
        len(scene_ids) != len(output.scenes)
        or len(beat_ids) != len(output.beats)
        or len(cue_ids) != len(set(cue_ids))
        or any(beat.scene_local_id not in scene_ids for beat in output.beats)
        or any(cue.beat_local_id not in beat_ids for cue in output.dialogue_cues)
        or dialogue_capacity_guidance.authoring_language is None
    ):
        return ()
    beat_scene = {beat.local_beat_id: beat.scene_local_id for beat in output.beats}
    timed: list[tuple[int, int, DialogueCueContent]] = []
    for index, cue in enumerate(output.dialogue_cues):
        if cue.language != dialogue_capacity_guidance.authoring_language:
            return ()
        duration = dialogue_timing_profile.estimate_text_duration_units(
            text=cue.text,
            language=cue.language,
            delivery=cue.delivery,
        )
        if duration is None:
            return ()
        timed.append((duration, index, cue))

    def node_minimum(excluded: set[str]) -> int:
        by_scene = {scene.local_scene_id: 0 for scene in output.scenes}
        for duration, _index, cue in timed:
            if cue.local_cue_id not in excluded:
                by_scene[beat_scene[cue.beat_local_id]] += duration
        # This exactly matches _scene_beats_semantic_issues: every scene
        # consumes a one-unit floor even when all of its cues are removed.
        return sum(max(1, duration) for duration in by_scene.values())

    current_total = node_minimum(set())
    if current_total <= node_duration_budget_units:
        return ()
    remaining = current_total
    removed: set[str] = set()
    # Recompute the exact scene-floor total after every candidate deletion.
    # A last cue in a scene may free no time because that scene's mandatory
    # one-unit floor remains; sorting raw cue durations would produce a plan
    # that still fails the validator.
    candidates = {
        cue.local_cue_id: (duration, index, cue) for duration, index, cue in timed
    }
    while remaining > node_duration_budget_units and candidates:
        ranked: list[tuple[int, int, str, int, DialogueCueContent]] = []
        for cue_id, (duration, index, cue) in candidates.items():
            next_total = node_minimum({*removed, cue_id})
            ranked.append((-(remaining - next_total), -index, cue_id, next_total, cue))
        _negative_reduction, _negative_index, selected_id, next_total, _cue = min(
            ranked
        )
        if next_total >= remaining:
            return ()
        removed.add(selected_id)
        candidates.pop(selected_id)
        remaining = next_total
    if remaining > node_duration_budget_units or not removed:
        return ()
    retained: list[DialogueNodeBudgetRemainingCue] = []
    next_order_by_beat: dict[str, int] = {}
    for _duration, _index, cue in timed:
        if cue.local_cue_id in removed:
            continue
        next_order = next_order_by_beat.get(cue.beat_local_id, 0) + 1
        next_order_by_beat[cue.beat_local_id] = next_order
        retained.append(
            DialogueNodeBudgetRemainingCue(
                local_cue_id=cue.local_cue_id,
                beat_local_id=cue.beat_local_id,
                expected_order=next_order,
            )
        )
    return tuple(
        DialogueNodeBudgetRepairFact(
            code=issue.code,
            path=issue.path,
            node_id=node_id,
            node_duration_budget_units=node_duration_budget_units,
            current_minimum_duration_units=current_total,
            remove_local_cue_ids=tuple(
                cue.local_cue_id
                for _duration, _index, cue in timed
                if cue.local_cue_id in removed
            ),
            remaining_cues=tuple(retained),
            remaining_minimum_duration_units=remaining,
        )
        for issue in relevant
        if issue.path == ("dialogueCues",)
    )


def assert_cue_order_repair_fact_matches_source(
    fact: SemanticRepairFact,
    source_value: Any,
) -> None:
    """Bind executable cue renumbering authority to its rejected response."""

    if not isinstance(fact, CueOrderRepairFact):
        return
    source_issue = ValidationIssue(code=fact.code, path=fact.path, message="")
    expected = scene_beats_cue_order_repair_facts(source_value, (source_issue,))
    if len(expected) != 1 or expected[0] != fact:
        raise ValueError("cue-order repair fact does not match the rejected response")
