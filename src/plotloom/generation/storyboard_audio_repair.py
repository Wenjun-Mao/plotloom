"""Derive exact correction facts for overflowing Storyboard audio events."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    ValidationError,
)

from .contracts import ValidationIssue
from .storyboard_repair_contracts import (
    AudioTimingRepairFact,
)
from .storyboard_response_contracts import (
    StoryboardFragmentOutput,
)


def storyboard_audio_timing_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
) -> tuple[AudioTimingRepairFact, ...]:
    """Turn one schema-valid audio overflow into an exact safe action.

    The portable response schema can constrain each field but cannot express
    ``startOffsetUnits + durationUnits <= shot.durationUnits``.  This router
    derives a correction only when the persisted semantic issue still points
    at the same parsed event.  A correction therefore gets one authoritative
    replacement duration, or an unambiguous removal when an event starts at
    or past the shot end; all malformed or stale evidence fails closed.
    """

    relevant_issues = tuple(
        issue for issue in issues if issue.code == "semantic.audio_timing"
    )
    if not relevant_issues:
        return ()
    try:
        output = StoryboardFragmentOutput.model_validate(
            value,
            by_alias=True,
            by_name=False,
        )
    except ValidationError:
        return ()

    facts_by_target: dict[tuple[int, int], AudioTimingRepairFact] = {}
    for issue in relevant_issues:
        path = issue.path
        if (
            len(path) != 6
            or path[0] != "shots"
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[2] != "audioPlan"
            or path[3] != "events"
            or not isinstance(path[4], int)
            or isinstance(path[4], bool)
            or path[4] < 0
            or path[5] != "durationUnits"
        ):
            continue
        shot_index = path[1]
        event_index = path[4]
        if shot_index >= len(output.shots):
            continue
        shot = output.shots[shot_index]
        if event_index >= len(shot.audio_plan.events):
            continue
        event = shot.audio_plan.events[event_index]
        if event.start_offset_units + event.duration_units <= shot.duration_units:
            continue
        remaining_duration_units = shot.duration_units - event.start_offset_units
        if remaining_duration_units >= 1:
            repair_action: Literal["replace_duration", "remove_event"] = (
                "replace_duration"
            )
            replacement_duration_units: int | None = remaining_duration_units
        else:
            repair_action = "remove_event"
            replacement_duration_units = None
        fact = AudioTimingRepairFact(
            code=issue.code,
            path=path,
            shot_local_id=shot.local_shot_id,
            event_index=event_index,
            start_offset_units=event.start_offset_units,
            duration_units=event.duration_units,
            shot_duration_units=shot.duration_units,
            repair_action=repair_action,
            replacement_duration_units=replacement_duration_units,
        )
        target = (shot_index, event_index)
        # A correction must be an executable sequence, not an unordered bag
        # of suggestions.  Two facts for one original array element would
        # make a later removal/replacement order ambiguous, so fail closed.
        if target in facts_by_target:
            return ()
        facts_by_target[target] = fact
    return tuple(
        fact
        for _target, fact in sorted(
            facts_by_target.items(),
            key=lambda item: (item[0][0], -item[0][1]),
        )
    )
