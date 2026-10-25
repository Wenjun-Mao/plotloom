"""Ordered Scene Beats acceptance against frozen identity, continuity and capacity."""

from __future__ import annotations

from typing import Any, Mapping

from ..domain import (
    DialogueTimingProfile,
    StoryBibleV2,
)
from ..json_value_contract import (
    CanonicalJsonValueError,
    finite_canonical_json,
    finite_json_values_equal,
)
from .contracts import ValidationIssue
from .dialogue_capacity import (
    DialogueCapacityNodeGuidance,
)
from .fragment_semantics import (
    _issue,
    continuity_sequence_is_compatible,
    continuity_state_issues,
)
from .frozen_join_requirements import (
    _continuity_requirements,
)
from .planning import (
    GenerationWorkUnit,
)
from .scene_beats_edge_entry import (
    edge_entry_state_requirements,
    first_scene_entry_issues,
)
from .scene_response_contracts import (
    BeatContent,
    DialogueCueContent,
    SceneBeatsFragmentOutput,
)
from .work_unit_contracts import (
    WorkUnitContractError,
)


def _scene_beats_semantic_issues(
    output: SceneBeatsFragmentOutput,
    *,
    work_unit: GenerationWorkUnit,
    bible: StoryBibleV2,
    scoped_context: Mapping[str, Any],
    dialogue_timing_profile: DialogueTimingProfile,
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    target = work_unit.selector.stable_id
    target_node = scoped_context.get("story_node", {})
    if target_node.get("id") != target:
        issues.append(
            _issue(
                "context.selector",
                "storyNodeId",
                "trusted context does not match unit selector",
            )
        )
    if dialogue_capacity_guidance.node_id != target:
        raise WorkUnitContractError(
            "dialogue capacity guidance does not match the work-unit selector"
        )
    if len(output.scenes) > dialogue_capacity_guidance.max_scenes:
        issues.append(
            _issue(
                "semantic.scene_capacity_exceeded",
                "scenes",
                "scene count exceeds the frozen dialogue capacity envelope",
            )
        )
    if len(output.dialogue_cues) > dialogue_capacity_guidance.max_dialogue_cues:
        issues.append(
            _issue(
                "semantic.dialogue_cue_count_exceeded",
                "dialogueCues",
                "dialogue cue count exceeds the frozen capacity envelope",
            )
        )
    scene_ids = [scene.local_scene_id for scene in output.scenes]
    if len(scene_ids) != len(set(scene_ids)):
        issues.append(
            _issue(
                "semantic.duplicate_scene_id",
                "scenes",
                "fragment contains duplicate scene IDs",
            )
        )
    scene_orders = sorted(scene.order for scene in output.scenes)
    if scene_orders != list(range(1, len(scene_orders) + 1)):
        issues.append(
            _issue(
                "semantic.scene_order",
                "scenes",
                "scene order must be contiguous from 1",
            )
        )
    beat_ids = [beat.local_beat_id for beat in output.beats]
    if len(beat_ids) != len(set(beat_ids)):
        issues.append(
            _issue(
                "semantic.duplicate_beat_id",
                "beats",
                "fragment contains duplicate beat IDs",
            )
        )
    known_characters = {item.id for item in bible.characters}
    known_locations = {item.id for item in bible.locations}
    edge_entry_requirements = edge_entry_state_requirements(scoped_context)
    issues.extend(
        first_scene_entry_issues(
            [scene.model_dump(mode="json", by_alias=True) for scene in output.scenes],
            edge_entry_requirements,
        )
    )
    beats_by_scene: dict[str, list[BeatContent]] = {}
    for beat in output.beats:
        beats_by_scene.setdefault(beat.scene_local_id, []).append(beat)
        if beat.scene_local_id not in scene_ids:
            issues.append(
                _issue(
                    "semantic.cross_unit_beat",
                    "beats",
                    "beat belongs to a scene outside this fragment",
                )
            )
    cues_by_beat: dict[str, list[DialogueCueContent]] = {}
    cue_ids = [cue.local_cue_id for cue in output.dialogue_cues]
    if len(cue_ids) != len(set(cue_ids)):
        issues.append(
            _issue(
                "semantic.duplicate_cue_id",
                "dialogueCues",
                "fragment contains duplicate cue IDs",
            )
        )
    for cue_index, cue in enumerate(output.dialogue_cues):
        cues_by_beat.setdefault(cue.beat_local_id, []).append(cue)
        if cue.beat_local_id not in beat_ids:
            issues.append(
                _issue(
                    "semantic.cross_unit_cue",
                    ("dialogueCues", cue_index, "beatLocalId"),
                    "cue belongs to a beat outside this fragment",
                )
            )
        if cue.speaker_id is not None and cue.speaker_id not in known_characters:
            issues.append(
                _issue(
                    "semantic.unknown_cue_speaker",
                    ("dialogueCues", cue_index, "speakerId"),
                    "cue speaker is not in the Story Bible",
                )
            )
    for beat_index, beat in enumerate(output.beats):
        issues.extend(
            continuity_state_issues(
                beat.entry_state,
                bible=bible,
                path=("beats", beat_index, "entryState"),
            )
        )
        issues.extend(
            continuity_state_issues(
                beat.exit_state,
                bible=bible,
                path=("beats", beat_index, "exitState"),
            )
        )
        for delta_key, delta_value in beat.continuity_delta.items():
            try:
                finite_canonical_json(delta_value)
            except CanonicalJsonValueError:
                issues.append(
                    _issue(
                        "semantic.continuity_delta_not_json",
                        ("beats", beat_index, "continuityDelta", delta_key),
                        "continuity delta values must be finite canonical JSON",
                    )
                )
    cue_order_invalid = False
    for index, scene in enumerate(output.scenes):
        if scene.location_id is not None and scene.location_id not in known_locations:
            issues.append(
                _issue(
                    "semantic.unknown_location",
                    ("scenes", index, "locationId"),
                    "scene references an unknown location",
                )
            )
        unknown_characters = set(scene.character_ids) - known_characters
        if unknown_characters:
            issues.append(
                _issue(
                    "semantic.unknown_characters",
                    ("scenes", index, "characterIds"),
                    "scene references unknown characters",
                )
            )
        if len(scene.character_ids) != len(set(scene.character_ids)):
            issues.append(
                _issue(
                    "semantic.duplicate_character_ref",
                    ("scenes", index, "characterIds"),
                    "scene references the same character more than once",
                )
            )
        issues.extend(
            continuity_state_issues(
                scene.entry_state,
                bible=bible,
                path=("scenes", index, "entryState"),
            )
        )
        issues.extend(
            continuity_state_issues(
                scene.exit_state,
                bible=bible,
                path=("scenes", index, "exitState"),
            )
        )
        ordered = sorted(
            beats_by_scene.get(scene.local_scene_id, []), key=lambda beat: beat.order
        )
        if not ordered:
            issues.append(
                _issue(
                    "semantic.scene_without_beats",
                    ("scenes", index),
                    "each scene must contain at least one beat",
                )
            )
        if [beat.order for beat in ordered] != list(range(1, len(ordered) + 1)):
            issues.append(
                _issue(
                    "semantic.beat_order",
                    ("scenes", index),
                    "beat order must be contiguous from 1",
                )
            )
        for beat in ordered:
            beat_cues = sorted(
                cues_by_beat.get(beat.local_beat_id, []), key=lambda cue: cue.order
            )
            if any(
                cue.speaker_id is not None and cue.speaker_id not in scene.character_ids
                for cue in beat_cues
            ):
                issues.append(
                    _issue(
                        "semantic.cue_speaker_not_in_scene",
                        "dialogueCues",
                        "cue speaker must appear in its dramatic scene",
                    )
                )
            if [cue.order for cue in beat_cues] != list(range(1, len(beat_cues) + 1)):
                cue_order_invalid = True
        if ordered and not continuity_sequence_is_compatible(
            scene.entry_state,
            ordered,
            scene.exit_state,
        ):
            issues.append(
                _issue(
                    "semantic.continuity_beat_sequence_mismatch",
                    ("scenes", index),
                    "scene entry, ordered beat states, and scene exit must be compatible",
                )
            )
    if cue_order_invalid:
        issues.append(
            _issue(
                "semantic.cue_order",
                "dialogueCues",
                "cue order must be contiguous within its beat",
            )
        )
    timing_allocation = scoped_context.get("scene_timing_allocation")
    if not isinstance(timing_allocation, Mapping) or not isinstance(
        timing_allocation.get("durationBudgetUnits"), int
    ):
        raise WorkUnitContractError(
            "Scene Beats context has no valid frozen node timing allocation"
        )
    structure_is_unambiguous = (
        len(scene_ids) == len(set(scene_ids))
        and len(beat_ids) == len(set(beat_ids))
        and all(beat.scene_local_id in set(scene_ids) for beat in output.beats)
        and all(cue.beat_local_id in set(beat_ids) for cue in output.dialogue_cues)
    )
    if structure_is_unambiguous:
        scene_by_beat = {
            beat.local_beat_id: beat.scene_local_id for beat in output.beats
        }
        cue_minimum_by_scene = {scene_id: 0 for scene_id in scene_ids}
        for cue_index, cue in enumerate(output.dialogue_cues):
            if (
                dialogue_capacity_guidance.authoring_language is not None
                and cue.language != dialogue_capacity_guidance.authoring_language
            ):
                issues.append(
                    _issue(
                        "semantic.dialogue_language_not_authoring_language",
                        ("dialogueCues", cue_index, "language"),
                        "cue language differs from the frozen ProjectBrief language",
                    )
                )
                # The model-authored language is already outside the frozen
                # contract. Do not query the timing profile with that
                # untrusted value: a valid authoring-language-only profile is
                # not required to have a wildcard for arbitrary languages.
                # Returning the semantic issue keeps this failure eligible for
                # the normal bounded correction path.
                continue
            minimum = dialogue_timing_profile.estimate_text_duration_units(
                text=cue.text,
                language=cue.language,
                delivery=cue.delivery,
            )
            if minimum is None:
                raise WorkUnitContractError(
                    "dialogue timing profile has no exact or wildcard rule"
                )
            schema_maximum = dialogue_capacity_guidance.schema_max_text_codepoints
            exceeds_portable_text_cap = (
                schema_maximum is not None and len(cue.text.strip()) > schema_maximum
            )
            if (
                minimum > dialogue_capacity_guidance.per_cue_duration_budget_units
                or exceeds_portable_text_cap
            ):
                issues.append(
                    _issue(
                        "semantic.dialogue_cue_capacity_exceeded",
                        ("dialogueCues", cue_index, "text"),
                        "trusted cue duration exceeds its frozen per-cue capacity",
                    )
                )
            scene_id = scene_by_beat[cue.beat_local_id]
            cue_minimum_by_scene[scene_id] += minimum
        node_budget = timing_allocation["durationBudgetUnits"]
        required_node_budget = sum(
            max(1, minimum) for minimum in cue_minimum_by_scene.values()
        )
        if required_node_budget > node_budget:
            issues.append(
                _issue(
                    "semantic.dialogue_exceeds_node_budget",
                    "dialogueCues",
                    "trusted dialogue minimums exceed the frozen Story Graph node budget",
                )
            )
    join_requirements = _continuity_requirements(scoped_context)
    required_entry_facts = join_requirements["requiredEntryFacts"]
    for scene_index, scene in enumerate(output.scenes):
        for state_key, expected_value in required_entry_facts.items():
            path = (
                "scenes",
                scene_index,
                "entryState",
                "facts",
                state_key,
            )
            if state_key not in scene.entry_state.facts:
                issues.append(
                    _issue(
                        "semantic.join_entry_state_value_missing",
                        path,
                        "join entry is missing a fact from the frozen edge-transition contract",
                    )
                )
            else:
                try:
                    matches = finite_json_values_equal(
                        scene.entry_state.facts[state_key],
                        expected_value,
                    )
                except CanonicalJsonValueError:
                    issues.append(
                        _issue(
                            "semantic.join_entry_state_value_not_json",
                            path,
                            "join entry facts must be finite canonical JSON values",
                        )
                    )
                else:
                    if not matches:
                        issues.append(
                            _issue(
                                "semantic.join_entry_state_value_mismatch",
                                path,
                                "join entry fact differs from the frozen edge-transition contract",
                            )
                        )
    return tuple(issues)
