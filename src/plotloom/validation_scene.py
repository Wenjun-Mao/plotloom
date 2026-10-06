from __future__ import annotations

from collections import defaultdict
from .canonical_schema import DialogueCue, DialogueTimingProfile, SceneBeatPlanV2, StoryBibleV2, StoryGraphV2, default_dialogue_timing_profile
from .domain import ProjectBrief
from .json_value_contract import CanonicalJsonValueError, finite_canonical_json
from .generation.scene_timing_allocation import plan_scene_timing_allocation
from .validation_state import _continuity_sequence_is_compatible, _continuity_state_issues
from .validation_issues import DomainValidationError, ValidationIssue, _duplicates, _issue

def _validate_v2_scene_order_and_continuity(
    plan: SceneBeatPlanV2,
    bible: StoryBibleV2,
) -> None:
    """Validate V2-only order and Bible-backed continuity state references.

    Entity-state labels must be backed by the current Story Bible, even when
    neighbouring scenes happen to agree with one another.
    """

    issues: list[ValidationIssue] = []
    scenes_by_node: dict[str, list] = defaultdict(list)
    for scene in plan.scenes:
        scenes_by_node[scene.story_node_id].append(scene)
    for node_id in sorted(scenes_by_node):
        orders = sorted(scene.order for scene in scenes_by_node[node_id])
        if orders != list(range(1, len(orders) + 1)):
            issues.append(
                _issue(
                    "non_contiguous_scene_order",
                    f"scenes.{node_id}",
                    "dramatic scene order must be contiguous and start at 1 within a story node",
                )
            )

    for scene in plan.scenes:
        issues.extend(_continuity_state_issues(f"scenes.{scene.id}.entryState", scene.entry_state, bible))
        issues.extend(_continuity_state_issues(f"scenes.{scene.id}.exitState", scene.exit_state, bible))
    for beat in plan.beats:
        issues.extend(_continuity_state_issues(f"beats.{beat.id}.entryState", beat.entry_state, bible))
        issues.extend(_continuity_state_issues(f"beats.{beat.id}.exitState", beat.exit_state, bible))
        for delta_key, delta_value in beat.continuity_delta.items():
            try:
                finite_canonical_json(delta_value)
            except CanonicalJsonValueError:
                issues.append(
                    _issue(
                        "continuity_delta_not_json",
                        f"beats.{beat.id}.continuityDelta.{delta_key}",
                        "continuity delta values must be finite canonical JSON",
                    )
                )
    beats_by_scene: dict[str, list] = defaultdict(list)
    for beat in plan.beats:
        beats_by_scene[beat.scene_id].append(beat)
    for scene in plan.scenes:
        ordered_beats = sorted(beats_by_scene[scene.id], key=lambda beat: beat.order)
        if not _continuity_sequence_is_compatible(
            scene.entry_state,
            ordered_beats,
            scene.exit_state,
        ):
            issues.append(
                _issue(
                    "continuity_beat_sequence_mismatch",
                    f"scenes.{scene.id}",
                    "scene entry, ordered beat states, and scene exit must be compatible",
                )
            )
    if issues:
        raise DomainValidationError(issues)


def _validate_v2_dialogue_cues(
    plan: SceneBeatPlanV2,
    bible: StoryBibleV2,
    *,
    timing_profile: DialogueTimingProfile | None = None,
) -> None:
    """Stage-local cue checks that do not require a storyboard schedule."""

    issues: list[ValidationIssue] = []
    beats_by_id = {beat.id: beat for beat in plan.beats}
    character_ids = {character.id for character in bible.characters}
    duplicate_ids = _duplicates(cue.id for cue in plan.dialogue_cues)
    for cue_id in sorted(duplicate_ids):
        issues.append(_issue("duplicate_dialogue_cue_id", "dialogueCues", f"duplicate dialogue cue id: {cue_id}"))
    cues_by_beat: dict[str, list[DialogueCue]] = defaultdict(list)
    timing_profile = timing_profile or default_dialogue_timing_profile()
    for cue in plan.dialogue_cues:
        cues_by_beat[cue.beat_id].append(cue)
        if cue.beat_id not in beats_by_id:
            issues.append(_issue("unknown_dialogue_cue_beat", f"dialogueCues.{cue.id}.beatId", f"unknown beat: {cue.beat_id}"))
        if cue.speaker_id is not None and cue.speaker_id not in character_ids:
            issues.append(_issue("unknown_dialogue_speaker", f"dialogueCues.{cue.id}.speakerId", f"unknown character: {cue.speaker_id}"))
        minimum = timing_profile.estimate_duration_units(cue)
        if minimum is None or cue.estimated_duration_units < minimum:
            issues.append(
                _issue(
                    "dialogue_duration_underestimated",
                    f"dialogueCues.{cue.id}.estimatedDurationUnits",
                    "dialogue duration must meet the versioned language/delivery minimum",
                )
            )
    for beat_id in sorted(cues_by_beat):
        orders = sorted(cue.order for cue in cues_by_beat[beat_id])
        if orders != list(range(1, len(orders) + 1)):
            issues.append(
                _issue(
                    "non_contiguous_dialogue_cue_order",
                    f"dialogueCues.{beat_id}",
                    "dialogue cue order must be contiguous and start at 1 within a beat",
                )
            )

    scene_budget_by_id = {
        scene.id: scene.duration_budget_units for scene in plan.scenes
    }
    cue_duration_by_scene: dict[str, int] = defaultdict(int)
    for cue in plan.dialogue_cues:
        beat = beats_by_id.get(cue.beat_id)
        if beat is not None:
            cue_duration_by_scene[beat.scene_id] += cue.estimated_duration_units
    for scene_id, cue_duration in sorted(cue_duration_by_scene.items()):
        budget = scene_budget_by_id.get(scene_id)
        if budget is not None and cue_duration > budget:
            issues.append(
                _issue(
                    "dialogue_scene_budget_exceeded",
                    f"scenes.{scene_id}.durationBudgetUnits",
                    f"dialogue requires {cue_duration} units but scene budget is {budget}",
                )
            )
    if issues:
        raise DomainValidationError(issues)


def _validate_v2_scene_timing_allocation(
    plan: SceneBeatPlanV2,
    graph: StoryGraphV2,
    brief: ProjectBrief,
) -> None:
    """Keep manual canonical edits inside the generation-time path cap."""

    allocation = plan_scene_timing_allocation(graph=graph, brief=brief)
    budget_by_node: dict[str, int] = defaultdict(int)
    for scene in plan.scenes:
        budget_by_node[scene.story_node_id] += scene.duration_budget_units
    issues = [
        _issue(
            "scene_node_budget_exceeded",
            f"scenes.{node_id}.durationBudgetUnits",
            "dramatic-scene budgets exceed the versioned Story Graph node cap",
        )
        for node_id, actual in sorted(budget_by_node.items())
        if actual > allocation.node_duration_budget(node_id)
    ]
    if issues:
        raise DomainValidationError(issues)
