from __future__ import annotations

from collections import defaultdict

from .canonical_schema import (
    DialogueTimingProfile,
    SceneBeatPlanV2,
    StoryBibleV2,
    StoryboardV2,
)
from .storyboard_observation import StoryboardObservation


def dialogue_observations(
    storyboard: StoryboardV2,
    plan: SceneBeatPlanV2,
    bible: StoryBibleV2,
    timing_profile: DialogueTimingProfile | None,
) -> tuple[StoryboardObservation, ...]:
    observations: list[StoryboardObservation] = []
    beats_by_id = {beat.id: beat for beat in plan.beats}
    cues_by_id = {cue.id: cue for cue in plan.dialogue_cues}
    character_ids = {entity.id for entity in bible.characters}
    cues_by_beat: dict[str, list] = defaultdict(list)
    for cue in plan.dialogue_cues:
        cues_by_beat[cue.beat_id].append(cue)
    for beat_id in sorted(cues_by_beat):
        beat_cues = sorted(cues_by_beat[beat_id], key=lambda item: item.order)
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.ownership.{beat_id}",
                beat_id in beats_by_id,
                path=("dialogueCues", beat_id),
                reason="dialogue cues must be owned by a known beat",
            )
        )
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.order.{beat_id}",
                [cue.order for cue in beat_cues] == list(range(1, len(beat_cues) + 1)),
                path=("dialogueCues", beat_id),
                reason="dialogue cue order must be contiguous and start at 1 within its beat",
            )
        )
        for cue in beat_cues:
            speaker_is_valid = (
                cue.voice_over is not None or cue.speaker_id in character_ids
            )
            observations.append(
                StoryboardObservation(
                    f"dialogue_cue.speaker.{cue.id}",
                    speaker_is_valid,
                    path=("dialogueCues", cue.id, "speakerId"),
                    reason="a dialogue speaker must be a story-bible character; voice-over is explicit",
                )
            )
    references_by_cue: dict[str, list] = defaultdict(list)
    for shot in storyboard.shots:
        for cue_id in shot.cue_ids:
            references_by_cue[cue_id].append(shot)
    for shot in sorted(storyboard.shots, key=lambda item: item.id):
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.reference_unique.{shot.id}",
                len(shot.cue_ids) == len(set(shot.cue_ids)),
                path=("shots", shot.id, "cueIds"),
                reason="a shot must not schedule the same dialogue cue more than once",
            )
        )
        references_are_known = all((cue_id in cues_by_id for cue_id in shot.cue_ids))
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.reference.{shot.id}",
                references_are_known,
                path=("shots", shot.id, "cueIds"),
                reason="shots may reference only canonical dialogue cue IDs",
            )
        )
        known_cues = [
            cues_by_id[cue_id] for cue_id in shot.cue_ids if cue_id in cues_by_id
        ]
        same_scene = all(
            (
                cue.beat_id in beats_by_id
                and beats_by_id[cue.beat_id].scene_id == shot.scene_id
                for cue in known_cues
            )
        )
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.scene_reference.{shot.id}",
                same_scene,
                path=("shots", shot.id, "cueIds"),
                reason="a shot can schedule only dialogue from its own scene",
            )
        )
        key_by_cue = {
            cue.id: (beats_by_id[cue.beat_id].order, cue.order)
            for cue in known_cues
            if cue.beat_id in beats_by_id
        }
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.reference_order.{shot.id}",
                [key_by_cue[cue.id] for cue in known_cues if cue.id in key_by_cue]
                == sorted(
                    (key_by_cue[cue.id] for cue in known_cues if cue.id in key_by_cue)
                ),
                path=("shots", shot.id, "cueIds"),
                reason="cue IDs must retain beat/cue order within a shot",
            )
        )
        total_cue_duration = sum((cue.estimated_duration_units for cue in known_cues))
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.shot_fit.{shot.id}",
                total_cue_duration <= shot.duration_units,
                path=("shots", shot.id, "cueIds"),
                reason="scheduled dialogue estimates must fit the shot duration",
            )
        )
    linked_pairs = {(link.shot_id, link.beat_id) for link in storyboard.shot_beat_links}
    for cue in sorted(plan.dialogue_cues, key=lambda item: item.id):
        scheduled_shots = references_by_cue[cue.id]
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.scheduled.{cue.id}",
                bool(scheduled_shots),
                path=("dialogueCues", cue.id),
                reason="every canonical dialogue cue must be scheduled by at least one shot",
            )
        )
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.schedule_cardinality.{cue.id}",
                len(scheduled_shots) == 1,
                path=("dialogueCues", cue.id),
                reason="a canonical dialogue cue must be scheduled by exactly one shot",
            )
        )
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.beat_coverage.{cue.id}",
                cue.beat_id in beats_by_id
                and all(
                    ((shot.id, cue.beat_id) in linked_pairs for shot in scheduled_shots)
                ),
                path=("dialogueCues", cue.id),
                reason="the shot scheduling a cue must cover the cue's owning beat",
            )
        )
        scheduled_duration = sum((shot.duration_units for shot in scheduled_shots))
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.total_fit.{cue.id}",
                cue.estimated_duration_units <= scheduled_duration,
                path=("dialogueCues", cue.id),
                reason="a cue estimate must fit its scheduled shot duration",
            )
        )
        if timing_profile is None:
            profile_match: bool | None = None
            profile_reason = (
                "dialogue-fit requires an explicit versioned timing profile"
            )
        else:
            expected = timing_profile.estimate_duration_units(cue)
            profile_match = (
                expected is not None and cue.estimated_duration_units >= expected
            )
            profile_reason = "cue estimate must not understate its versioned language/delivery timing-profile minimum"
        observations.append(
            StoryboardObservation(
                f"dialogue_cue.profile_fit.{cue.id}",
                profile_match,
                path=("dialogueCues", cue.id, "estimatedDurationUnits"),
                reason=profile_reason,
            )
        )
    return tuple(observations)
