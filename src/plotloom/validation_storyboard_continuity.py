from __future__ import annotations

from collections import defaultdict

from .canonical_schema import (
    SceneBeatPlanV2,
    ShotV2,
    StoryBibleV2,
    StoryboardV2,
)
from .storyboard_observation import StoryboardObservation
from .validation_state import (
    _continuity_entity_states_are_unique,
    _continuity_sequence_is_compatible,
    _continuity_state_issues,
)


def shot_continuity_observations(
    shot: ShotV2, bible: StoryBibleV2
) -> tuple[StoryboardObservation, ...]:
    observations: list[StoryboardObservation] = []
    continuity_states_are_available = not _continuity_state_issues(
        "", shot.entry_state, bible
    ) and (not _continuity_state_issues("", shot.exit_state, bible))
    observations.append(
        StoryboardObservation(
            f"continuity.entity_state.available.shot.{shot.id}",
            continuity_states_are_available,
            path=("shots", shot.id),
            reason="shot continuity states must reference Bible entities and allowed states",
        )
    )
    return tuple(observations)


def sequence_continuity_observations(
    storyboard: StoryboardV2, plan: SceneBeatPlanV2, bible: StoryBibleV2
) -> tuple[StoryboardObservation, ...]:
    observations: list[StoryboardObservation] = []
    beats_by_scene: dict[str, list] = defaultdict(list)
    for beat in plan.beats:
        beats_by_scene[beat.scene_id].append(beat)
    shots_by_scene: dict[str, list] = defaultdict(list)
    for shot in storyboard.shots:
        shots_by_scene[shot.scene_id].append(shot)
    for scene in sorted(plan.scenes, key=lambda item: item.id):
        scene_beats = sorted(beats_by_scene[scene.id], key=lambda item: item.order)
        scene_shots = sorted(shots_by_scene[scene.id], key=lambda item: item.order)
        scene_continuity_states_are_available = not _continuity_state_issues(
            "", scene.entry_state, bible
        ) and (not _continuity_state_issues("", scene.exit_state, bible))
        observations.append(
            StoryboardObservation(
                f"continuity.entity_state.available.scene.{scene.id}",
                scene_continuity_states_are_available,
                path=("scenes", scene.id),
                reason="scene continuity states must reference Bible entities and allowed states",
            )
        )
        observations.append(
            StoryboardObservation(
                f"continuity.entity_state.unique.scene.{scene.id}",
                _continuity_entity_states_are_unique(scene.entry_state)
                and _continuity_entity_states_are_unique(scene.exit_state),
                path=("scenes", scene.id),
                reason="scene continuity states must not repeat or conflict on an entity",
            )
        )
        for shot in scene_shots:
            observations.append(
                StoryboardObservation(
                    f"continuity.entity_state.unique.shot.{shot.id}",
                    _continuity_entity_states_are_unique(shot.entry_state)
                    and _continuity_entity_states_are_unique(shot.exit_state),
                    path=("shots", shot.id),
                    reason="shot continuity states must not repeat or conflict on an entity",
                )
            )
        continuity_ok = _continuity_sequence_is_compatible(
            scene.entry_state, scene_shots, scene.exit_state
        )
        observations.append(
            StoryboardObservation(
                f"continuity.shot_sequence.{scene.id}",
                continuity_ok,
                path=("scenes", scene.id),
                reason="scene and adjacent shot entry/exit states must be compatible",
            )
        )
        beat_continuity_ok = _continuity_sequence_is_compatible(
            scene.entry_state, scene_beats, scene.exit_state
        )
        observations.append(
            StoryboardObservation(
                f"continuity.beat_sequence.{scene.id}",
                beat_continuity_ok,
                path=("scenes", scene.id),
                reason="scene and ordered beat entry/exit states must be compatible",
            )
        )
    for beat in sorted(plan.beats, key=lambda item: item.id):
        beat_continuity_states_are_available = not _continuity_state_issues(
            "", beat.entry_state, bible
        ) and (not _continuity_state_issues("", beat.exit_state, bible))
        observations.append(
            StoryboardObservation(
                f"continuity.entity_state.available.beat.{beat.id}",
                beat_continuity_states_are_available,
                path=("beats", beat.id),
                reason="beat continuity states must reference Bible entities and allowed states",
            )
        )
    return tuple(observations)
