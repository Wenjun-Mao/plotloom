"""Closed, typed candidate schemas for bounded stage work units.

Fragments are candidates, not canonical stage revisions.  Their metadata binds
them to the immutable StagePlan and work unit that requested them; aggregation
performs the remaining cross-unit checks before a full canonical validator runs.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from pydantic import ConfigDict, Field, model_validator

from ..domain import (
    Beat,
    CoverageRole,
    DramaticScene,
    Shot,
    ShotBeatLink,
    StoryBible,
    StoryGraph,
)
from .planning import PlanningModel


class FragmentValidationError(ValueError):
    """A unit candidate cannot be safely combined with any sibling fragment."""


class FragmentBase(PlanningModel):
    stage_plan_hash: str = Field(min_length=1)
    work_unit_id: str = Field(min_length=1)


class StoryBibleFragment(FragmentBase):
    payload: StoryBible


class StoryGraphFragment(FragmentBase):
    payload: StoryGraph


class SceneBeatsFragment(FragmentBase):
    """All scenes and beats assigned to one stable Story Graph node."""

    story_node_id: str = Field(min_length=1)
    scenes: tuple[DramaticScene, ...] = Field(min_length=1)
    beats: tuple[Beat, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_closed_scene_partition(self) -> "SceneBeatsFragment":
        if any(scene.story_node_id != self.story_node_id for scene in self.scenes):
            raise ValueError("scene-beats fragments may only contain their selected story node")
        scene_ids = {scene.id for scene in self.scenes}
        if len(scene_ids) != len(self.scenes):
            raise ValueError("scene-beats fragments may not contain duplicate scene IDs")
        if any(beat.scene_id not in scene_ids for beat in self.beats):
            raise ValueError("scene-beats fragments may not contain beats from another unit")
        if len({beat.id for beat in self.beats}) != len(self.beats):
            raise ValueError("scene-beats fragments may not contain duplicate beat IDs")
        beats_by_scene: dict[str, list[Beat]] = defaultdict(list)
        for beat in self.beats:
            beats_by_scene[beat.scene_id].append(beat)
        for scene in self.scenes:
            ordered = sorted(beats_by_scene[scene.id], key=lambda beat: beat.order)
            if scene.beat_ids != [beat.id for beat in ordered]:
                raise ValueError("scene beatIds must exactly match this fragment's beats in order")
            if [beat.order for beat in ordered] != list(range(1, len(ordered) + 1)):
                raise ValueError("fragment beat order must be contiguous and start at 1")
        return self


class StoryboardFragment(FragmentBase):
    """All shots and coverage links assigned to one stable dramatic scene."""

    scene_id: str = Field(min_length=1)
    shots: tuple[Shot, ...] = Field(min_length=1)
    shot_beat_links: tuple[ShotBeatLink, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_closed_scene_partition(self) -> "StoryboardFragment":
        if any(shot.scene_id != self.scene_id for shot in self.shots):
            raise ValueError("storyboard fragments may only contain their selected dramatic scene")
        shot_ids = {shot.id for shot in self.shots}
        if len(shot_ids) != len(self.shots):
            raise ValueError("storyboard fragments may not contain duplicate shot IDs")
        if any(link.shot_id not in shot_ids for link in self.shot_beat_links):
            raise ValueError("storyboard fragments may not link a shot from another unit")
        pairs = [(link.shot_id, link.beat_id) for link in self.shot_beat_links]
        if len(set(pairs)) != len(pairs):
            raise ValueError("storyboard fragments may not contain duplicate shot-to-beat links")
        ordered = sorted(self.shots, key=lambda shot: shot.order)
        if [shot.order for shot in ordered] != list(range(1, len(ordered) + 1)):
            raise ValueError("fragment shot order must be contiguous and start at 1")
        return self


StageFragment = (
    StoryBibleFragment | StoryGraphFragment | SceneBeatsFragment | StoryboardFragment
)


def primary_link_counts(fragment: StoryboardFragment) -> Counter[str]:
    """Return local primary coverage counts; aggregate validation owns global truth."""

    return Counter(
        link.beat_id
        for link in fragment.shot_beat_links
        if link.role == CoverageRole.PRIMARY
    )
