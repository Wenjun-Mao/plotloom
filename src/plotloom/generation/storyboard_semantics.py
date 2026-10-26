"""Ordered Storyboard acceptance for coverage, cues, continuity, entities and audio."""

from __future__ import annotations

from typing import Any, Mapping

from plotloom.canonical_schema import EntityType, StoryBibleV2
from plotloom.brief_contracts import ProjectBrief
from .contracts import ValidationIssue
from .fragment_semantics import (
    FragmentSemanticContextError,
    _issue,
    allowed_entity_states,
    continuity_sequence_is_compatible,
    continuity_state_from_context,
    continuity_state_issues,
    cue_canonical_order_key,
    cue_duration_units,
    required_entity_is_in_shot,
)
from plotloom.generation.planning_contracts import GenerationWorkUnit
from .storyboard_response_contracts import (
    StoryboardFragmentOutput,
)
from .work_unit_contracts import (
    WorkUnitContractError,
)


def _storyboard_semantic_issues(
    output: StoryboardFragmentOutput,
    *,
    work_unit: GenerationWorkUnit,
    brief: ProjectBrief,
    bible: StoryBibleV2,
    scoped_context: Mapping[str, Any],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    target = work_unit.selector.stable_id
    scene = scoped_context.get("dramatic_scene", {})
    if scene.get("id") != target:
        issues.append(
            _issue(
                "context.selector",
                "sceneId",
                "trusted context does not match unit selector",
            )
        )
    scene_duration_budget = scene.get("durationBudgetUnits")
    if (
        not isinstance(scene_duration_budget, int)
        or isinstance(scene_duration_budget, bool)
        or scene_duration_budget < 1
    ):
        raise WorkUnitContractError(
            "Storyboard context has no valid dramatic-scene duration budget"
        )
    beat_ids = {beat["id"] for beat in scoped_context.get("beats", [])}
    shot_ids = [shot.local_shot_id for shot in output.shots]
    if len(shot_ids) != len(set(shot_ids)):
        issues.append(
            _issue(
                "semantic.duplicate_shot_id",
                "shots",
                "fragment contains duplicate shot IDs",
            )
        )
    known_characters = {item.id for item in bible.characters}
    known_locations = {item.id for item in bible.locations}
    known_props = {item.id for item in bible.props}
    entities_by_type = allowed_entity_states(bible)
    cues_by_id = {
        str(cue["id"]): cue
        for cue in scoped_context.get("dialogue_cues", [])
        if isinstance(cue, Mapping) and cue.get("id")
    }
    scheduled_cues: dict[str, str] = {}
    for index, shot in enumerate(output.shots):
        if shot.location_id is not None and shot.location_id not in known_locations:
            issues.append(
                _issue(
                    "semantic.unknown_location",
                    ("shots", index, "locationId"),
                    "shot references an unknown location",
                )
            )
        if set(shot.character_ids) - known_characters:
            issues.append(
                _issue(
                    "semantic.unknown_characters",
                    ("shots", index, "characterIds"),
                    "shot references unknown characters",
                )
            )
        if len(shot.character_ids) != len(set(shot.character_ids)):
            issues.append(
                _issue(
                    "semantic.duplicate_character_ref",
                    ("shots", index, "characterIds"),
                    "shot references the same character more than once",
                )
            )
        if set(shot.prop_ids) - known_props:
            issues.append(
                _issue(
                    "semantic.unknown_props",
                    ("shots", index, "propIds"),
                    "shot references unknown props",
                )
            )
        if len(shot.prop_ids) != len(set(shot.prop_ids)):
            issues.append(
                _issue(
                    "semantic.duplicate_prop_ref",
                    ("shots", index, "propIds"),
                    "shot references the same prop more than once",
                )
            )
        issues.extend(
            continuity_state_issues(
                shot.entry_state,
                bible=bible,
                path=("shots", index, "entryState"),
            )
        )
        issues.extend(
            continuity_state_issues(
                shot.exit_state,
                bible=bible,
                path=("shots", index, "exitState"),
            )
        )
        for cue_id in shot.cue_ids:
            if cue_id not in cues_by_id:
                issues.append(
                    _issue(
                        "semantic.unknown_cue_ref",
                        ("shots", index, "cueIds"),
                        "shot references an unknown cue",
                    )
                )
            elif cue_id in scheduled_cues:
                issues.append(
                    _issue(
                        "semantic.duplicate_cue_ref",
                        ("shots", index, "cueIds"),
                        "a cue may be scheduled only once per scene",
                    )
                )
            else:
                scheduled_cues[cue_id] = shot.local_shot_id
        required_entities: set[tuple[EntityType, str]] = set()
        for state_index, required in enumerate(shot.required_entity_states):
            key = (required.entity_type, required.entity_id)
            if key in required_entities:
                issues.append(
                    _issue(
                        "semantic.duplicate_required_entity_state",
                        ("shots", index, "requiredEntityStates", state_index),
                        "entity state is duplicated within one shot",
                    )
                )
            required_entities.add(key)
            allowed = entities_by_type[required.entity_type].get(required.entity_id)
            if allowed is None:
                issues.append(
                    _issue(
                        "semantic.unknown_required_entity",
                        (
                            "shots",
                            index,
                            "requiredEntityStates",
                            state_index,
                            "entityId",
                        ),
                        "required entity is absent from the Story Bible or has the wrong type",
                    )
                )
            elif required.state not in allowed:
                issues.append(
                    _issue(
                        "semantic.invalid_required_entity_state",
                        ("shots", index, "requiredEntityStates", state_index, "state"),
                        "required entity state is not allowed by the Story Bible",
                    )
                )
            if not required_entity_is_in_shot(required, shot):
                issues.append(
                    _issue(
                        "semantic.required_entity_not_in_shot",
                        (
                            "shots",
                            index,
                            "requiredEntityStates",
                            state_index,
                            "entityId",
                        ),
                        "required entity state must belong to an entity present in the shot",
                    )
                )
        for event_index, event in enumerate(shot.audio_plan.events):
            if event.start_offset_units + event.duration_units > shot.duration_units:
                issues.append(
                    _issue(
                        "semantic.audio_timing",
                        (
                            "shots",
                            index,
                            "audioPlan",
                            "events",
                            event_index,
                            "durationUnits",
                        ),
                        "audio event must fit within the shot duration",
                    )
                )
    ordered = sorted(output.shots, key=lambda shot: shot.order)
    if [shot.order for shot in ordered] != list(range(1, len(ordered) + 1)):
        issues.append(
            _issue(
                "semantic.shot_order", "shots", "shot order must be contiguous from 1"
            )
        )
    if (
        brief.shot_count_is_strict
        and not brief.shots_per_scene_min
        <= len(output.shots)
        <= brief.shots_per_scene_max
    ):
        issues.append(
            _issue(
                "semantic.shot_count",
                "shots",
                "shot count falls outside the project scene budget",
            )
        )
    total_duration = sum(shot.duration_units for shot in output.shots)
    if total_duration > scene_duration_budget:
        issues.append(
            _issue(
                "semantic.shot_duration_budget_exceeded",
                "shots",
                "ordered shot durations exceed the frozen dramatic-scene duration budget",
            )
        )
    try:
        scene_entry_state = continuity_state_from_context(scene, "entryState")
        scene_exit_state = continuity_state_from_context(scene, "exitState")
    except FragmentSemanticContextError as exc:
        raise WorkUnitContractError(str(exc)) from exc
    if ordered and not continuity_sequence_is_compatible(
        scene_entry_state,
        ordered,
        scene_exit_state,
    ):
        issues.append(
            _issue(
                "semantic.continuity_shot_sequence_mismatch",
                "shots",
                "scene entry, ordered shot states, and scene exit must be compatible",
            )
        )
    linked_shots: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    primary_map = output.primary_shot_local_id_by_beat
    if set(primary_map) != beat_ids:
        issues.append(
            _issue(
                "semantic.primary_coverage",
                "primaryShotLocalIdByBeat",
                "PRIMARY coverage must contain exactly the selected beat IDs",
            )
        )
    for beat_id, shot_local_id in primary_map.items():
        pair = (shot_local_id, beat_id)
        if pair in pairs:
            issues.append(
                _issue(
                    "semantic.duplicate_link",
                    "primaryShotLocalIdByBeat",
                    "duplicate shot-to-beat link",
                )
            )
        pairs.add(pair)
        if shot_local_id not in shot_ids:
            issues.append(
                _issue(
                    "semantic.unknown_link_shot",
                    ("primaryShotLocalIdByBeat", beat_id),
                    "PRIMARY link references a shot outside this fragment",
                )
            )
        else:
            linked_shots.add(shot_local_id)
        if beat_id not in beat_ids:
            issues.append(
                _issue(
                    "semantic.cross_unit_beat",
                    ("primaryShotLocalIdByBeat", beat_id),
                    "PRIMARY link references a beat outside this fragment",
                )
            )
    for index, link in enumerate(output.supporting_beat_links):
        pair = (link.shot_local_id, link.beat_id)
        if pair in pairs:
            issues.append(
                _issue(
                    "semantic.duplicate_link",
                    ("supportingBeatLinks", index),
                    "duplicate shot-to-beat link",
                )
            )
        pairs.add(pair)
        if link.shot_local_id not in shot_ids:
            issues.append(
                _issue(
                    "semantic.unknown_link_shot",
                    ("supportingBeatLinks", index),
                    "supporting link references a shot outside this fragment",
                )
            )
        else:
            linked_shots.add(link.shot_local_id)
        if link.beat_id not in beat_ids:
            issues.append(
                _issue(
                    "semantic.cross_unit_beat",
                    ("supportingBeatLinks", index),
                    "supporting link references a beat outside this fragment",
                )
            )
    if set(shot_ids) - linked_shots:
        issues.append(
            _issue(
                "semantic.unlinked_shots",
                "primaryShotLocalIdByBeat",
                "each shot must cover a selected beat",
            )
        )
    for cue_id, cue in cues_by_id.items():
        scheduled_shot = scheduled_cues.get(cue_id)
        if scheduled_shot is None:
            issues.append(
                _issue(
                    "semantic.unscheduled_cue_ref",
                    "shots",
                    f"cue {cue_id} is not scheduled by a shot",
                )
            )
            continue
        cue_beat_id = str(cue.get("beatId") or "")
        covered_beats = {
            beat_id
            for beat_id, shot_id in primary_map.items()
            if shot_id == scheduled_shot
        } | {
            link.beat_id
            for link in output.supporting_beat_links
            if link.shot_local_id == scheduled_shot
        }
        if cue_beat_id not in covered_beats:
            issues.append(
                _issue(
                    "semantic.cue_not_covered_by_shot",
                    "shots",
                    f"cue {cue_id} must be scheduled by a shot covering its beat",
                )
            )
    for index, shot in enumerate(output.shots):
        known_cues = [
            cues_by_id[cue_id] for cue_id in shot.cue_ids if cue_id in cues_by_id
        ]
        try:
            cue_order_keys = [
                cue_canonical_order_key(cue, scoped_context=scoped_context)
                for cue in known_cues
            ]
            total_cue_duration = sum(cue_duration_units(cue) for cue in known_cues)
        except FragmentSemanticContextError as exc:
            raise WorkUnitContractError(str(exc)) from exc
        if cue_order_keys != sorted(cue_order_keys):
            issues.append(
                _issue(
                    "semantic.cue_canonical_order",
                    ("shots", index, "cueIds"),
                    "cue IDs must retain canonical beat and cue order within a shot",
                )
            )
        if total_cue_duration > shot.duration_units:
            issues.append(
                _issue(
                    "semantic.cue_duration_exceeds_shot",
                    ("shots", index, "cueIds"),
                    "scheduled dialogue durations must fit within the shot duration",
                )
            )
    return tuple(issues)
