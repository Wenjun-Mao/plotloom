"""Frozen, executable Storyboard timing repair plans.

This module owns the narrow correction contract for shot/cue timing.  It does
not inspect provider output prose, mutate candidates, or choose a model.  A
plan is built only after schema-valid response identity and coverage can be
proved, then a correction applies its listed field replacements verbatim.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal, Mapping, Sequence

from pydantic import ConfigDict, Field, model_validator

from ..domain import CamelModel
from ..json_value_contract import finite_canonical_json


STORYBOARD_TIMING_REPAIR_PLAN_VERSION = "storyboard_timing_repair_plan.v1"


class _FrozenCamelModel(CamelModel):
    model_config = ConfigDict(
        alias_generator=CamelModel.model_config.get("alias_generator"),
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


class StoryboardBeatTimingGuidance(_FrozenCamelModel):
    beat_id: str = Field(min_length=1)
    order: int = Field(ge=1)


class StoryboardCueTimingGuidance(_FrozenCamelModel):
    cue_id: str = Field(min_length=1)
    beat_id: str = Field(min_length=1)
    beat_order: int = Field(ge=1)
    cue_order: int = Field(ge=1)
    estimated_duration_units: int = Field(ge=1)


class StoryboardTimingGuidance(_FrozenCamelModel):
    """The full text-free timing scope frozen into a current contract."""

    scene_id: str = Field(min_length=1)
    scene_duration_budget_units: int = Field(ge=1)
    min_shots: int = Field(ge=1)
    # This is the effective max, not merely the project preference.  It is
    # mirrored into the response schema maxItems.
    max_shots: int = Field(ge=1)
    configured_max_shots: int = Field(ge=1)
    beats: tuple[StoryboardBeatTimingGuidance, ...] = Field(min_length=1)
    cues: tuple[StoryboardCueTimingGuidance, ...]

    @model_validator(mode="after")
    def validate_guidance(self) -> "StoryboardTimingGuidance":
        if self.min_shots > self.max_shots or self.max_shots > self.configured_max_shots:
            raise ValueError("Storyboard timing shot bounds are invalid")
        beat_ids = [beat.beat_id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("Storyboard timing beat IDs must be unique")
        if list(self.beats) != sorted(self.beats, key=lambda item: (item.order, item.beat_id)):
            raise ValueError("Storyboard timing beats must use canonical order")
        beat_order = {beat.beat_id: beat.order for beat in self.beats}
        cue_ids = [cue.cue_id for cue in self.cues]
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("Storyboard timing cue IDs must be unique")
        if any(beat_order.get(cue.beat_id) != cue.beat_order for cue in self.cues):
            raise ValueError("Storyboard cue beat order must match frozen beats")
        if list(self.cues) != sorted(
            self.cues, key=lambda cue: (cue.beat_order, cue.cue_order, cue.cue_id)
        ):
            raise ValueError("Storyboard timing cues must use canonical order")
        lower_bound = timing_lower_bound(
            total_cue_duration=sum(cue.estimated_duration_units for cue in self.cues),
            cue_count=len(self.cues),
            shot_count=self.min_shots,
        )
        if lower_bound > self.scene_duration_budget_units:
            raise ValueError("Storyboard timing guidance is infeasible at its minimum shot count")
        expected_max = effective_max_shots(
            configured_max_shots=self.configured_max_shots,
            scene_duration_budget_units=self.scene_duration_budget_units,
            total_cue_duration=sum(cue.estimated_duration_units for cue in self.cues),
            cue_count=len(self.cues),
        )
        if self.max_shots != expected_max:
            raise ValueError("Storyboard timing guidance maxShots must be the effective maximum")
        return self


def storyboard_timing_guidance_hash(guidance: StoryboardTimingGuidance) -> str:
    """Return the stable identity of the full frozen timing scope.

    A repair plan may repeat the values it needs to execute, but its authority
    comes from the prompt contract's complete guidance.  Keeping this hash
    separate from ``plan_hash`` lets correction replay prove that a valid plan
    was made for *this* scene, cue set, and configured bound rather than a
    structurally similar one from another contract.
    """

    return _sha256(guidance.model_dump(mode="json", by_alias=True))


class StoryboardTimingPlanShot(_FrozenCamelModel):
    local_shot_id: str = Field(min_length=1)
    target_order: int = Field(ge=1)
    target_duration_units: int = Field(ge=1)
    target_cue_ids: tuple[str, ...]
    remove_audio_event_indexes: tuple[int, ...]

    @model_validator(mode="after")
    def validate_shot(self) -> "StoryboardTimingPlanShot":
        if len(self.target_cue_ids) != len(set(self.target_cue_ids)):
            raise ValueError("a target shot may schedule a cue only once")
        if list(self.remove_audio_event_indexes) != sorted(
            set(self.remove_audio_event_indexes), reverse=True
        ):
            raise ValueError("audio event indexes must be unique descending zero-based indexes")
        if any(index < 0 for index in self.remove_audio_event_indexes):
            raise ValueError("audio event indexes must be non-negative")
        return self


class StoryboardTimingPlanPrimaryLink(_FrozenCamelModel):
    beat_id: str = Field(min_length=1)
    shot_local_id: str = Field(min_length=1)


class StoryboardTimingPlanSupportingLink(_FrozenCamelModel):
    shot_local_id: str = Field(min_length=1)
    beat_id: str = Field(min_length=1)
    coverage_weight: float = Field(gt=0, le=1)


class StoryboardTimingRepairPlan(_FrozenCamelModel):
    version: str = STORYBOARD_TIMING_REPAIR_PLAN_VERSION
    scene_id: str = Field(min_length=1)
    scene_duration_budget_units: int = Field(ge=1)
    min_shots: int = Field(ge=1)
    max_shots: int = Field(ge=1)
    beats: tuple[StoryboardBeatTimingGuidance, ...] = Field(min_length=1)
    cues: tuple[StoryboardCueTimingGuidance, ...]
    target_shots: tuple[StoryboardTimingPlanShot, ...] = Field(min_length=1)
    target_primary_links: tuple[StoryboardTimingPlanPrimaryLink, ...] = Field(min_length=1)
    target_supporting_links: tuple[StoryboardTimingPlanSupportingLink, ...]
    guidance: StoryboardTimingGuidance
    guidance_hash: str = Field(min_length=64, max_length=64)
    plan_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_plan(self) -> "StoryboardTimingRepairPlan":
        if self.version != STORYBOARD_TIMING_REPAIR_PLAN_VERSION:
            raise ValueError("unsupported Storyboard timing repair plan version")
        if (
            self.scene_id != self.guidance.scene_id
            or self.scene_duration_budget_units
            != self.guidance.scene_duration_budget_units
            or self.min_shots != self.guidance.min_shots
            or self.max_shots != self.guidance.max_shots
            or self.beats != self.guidance.beats
            or self.cues != self.guidance.cues
        ):
            raise ValueError("Storyboard timing plan must repeat its frozen guidance exactly")
        if self.guidance_hash != storyboard_timing_guidance_hash(self.guidance):
            raise ValueError("Storyboard timing plan guidanceHash does not match frozen guidance")
        if not self.min_shots <= len(self.target_shots) <= self.max_shots:
            raise ValueError("target shot count falls outside frozen timing bounds")
        shot_ids = [shot.local_shot_id for shot in self.target_shots]
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError("target shot IDs must be unique")
        if sorted(shot.target_order for shot in self.target_shots) != list(range(1, len(self.target_shots) + 1)):
            raise ValueError("target shot orders must be contiguous")
        beat_ids = [beat.beat_id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("frozen beat IDs must be unique")
        if list(self.beats) != sorted(self.beats, key=lambda item: (item.order, item.beat_id)):
            raise ValueError("frozen beats must use canonical order")
        beat_order = {beat.beat_id: beat.order for beat in self.beats}
        cue_ids = [cue.cue_id for cue in self.cues]
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("frozen cue IDs must be unique")
        if any(beat_order.get(cue.beat_id) != cue.beat_order for cue in self.cues):
            raise ValueError("frozen cue beat identities must match frozen beats")
        if list(self.cues) != sorted(
            self.cues, key=lambda cue: (cue.beat_order, cue.cue_order, cue.cue_id)
        ):
            raise ValueError("frozen cues must use canonical order")
        cue_by_id = {cue.cue_id: cue for cue in self.cues}
        assigned = [cue_id for shot in self.target_shots for cue_id in shot.target_cue_ids]
        if sorted(assigned) != sorted(cue_by_id):
            raise ValueError("every frozen cue must be assigned exactly once")
        total_duration = 0
        for shot in self.target_shots:
            ordered = sorted(
                shot.target_cue_ids,
                key=lambda cue_id: (
                    cue_by_id[cue_id].beat_order,
                    cue_by_id[cue_id].cue_order,
                    cue_id,
                ),
            )
            if list(shot.target_cue_ids) != ordered:
                raise ValueError("target shot cue IDs must use canonical order")
            minimum = max(
                1,
                sum(cue_by_id[cue_id].estimated_duration_units for cue_id in shot.target_cue_ids),
            )
            if shot.target_duration_units != minimum:
                raise ValueError("target shot duration must equal its exact frozen minimum")
            total_duration += shot.target_duration_units
        if total_duration > self.scene_duration_budget_units:
            raise ValueError("target shot durations exceed the frozen scene budget")
        primary = {link.beat_id: link.shot_local_id for link in self.target_primary_links}
        if len(primary) != len(self.target_primary_links) or set(primary) != set(beat_ids):
            raise ValueError("target primary map must contain every frozen beat exactly once")
        if set(primary.values()) - set(shot_ids):
            raise ValueError("target primary map references an unknown target shot")
        supporting_pairs = [(link.shot_local_id, link.beat_id) for link in self.target_supporting_links]
        if len(supporting_pairs) != len(set(supporting_pairs)):
            raise ValueError("target supporting links must be unique")
        if any(shot_id not in set(shot_ids) or beat_id not in set(beat_ids) for shot_id, beat_id in supporting_pairs):
            raise ValueError("target supporting links must reference frozen identities")
        primary_pairs = {(shot_id, beat_id) for beat_id, shot_id in primary.items()}
        if primary_pairs & set(supporting_pairs):
            raise ValueError("target supporting links must not duplicate PRIMARY coverage")
        covered_pairs = primary_pairs | set(supporting_pairs)
        if set(shot_ids) - {shot_id for shot_id, _beat_id in covered_pairs}:
            raise ValueError("every target shot must retain PRIMARY or SUPPORTING coverage")
        for shot in self.target_shots:
            for cue_id in shot.target_cue_ids:
                if (shot.local_shot_id, cue_by_id[cue_id].beat_id) not in covered_pairs:
                    raise ValueError("each target cue must be covered by its target shot")
        if list(self.target_primary_links) != sorted(
            self.target_primary_links, key=lambda link: (next(beat.order for beat in self.beats if beat.beat_id == link.beat_id), link.beat_id)
        ):
            raise ValueError("target primary links must use beat order")
        if list(self.target_supporting_links) != sorted(
            self.target_supporting_links, key=lambda link: (link.shot_local_id, next(beat.order for beat in self.beats if beat.beat_id == link.beat_id), link.beat_id)
        ):
            raise ValueError("target supporting links must use stable order")
        unsigned = self.model_dump(mode="json", by_alias=True, exclude={"plan_hash"})
        if self.plan_hash != _sha256(unsigned):
            raise ValueError("Storyboard timing repair planHash does not match its content")
        return self


class StoryboardTimingRepairPlanFact(_FrozenCamelModel):
    """One issue-bound reference to the same complete executable plan."""

    code: Literal[
        "semantic.shot_duration_budget_exceeded",
        "semantic.cue_duration_exceeds_shot",
    ]
    path: tuple[str | int, ...]
    plan: StoryboardTimingRepairPlan
    guidance_hash: str = Field(min_length=64, max_length=64)
    plan_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_fact(self) -> "StoryboardTimingRepairPlanFact":
        if self.plan_hash != self.plan.plan_hash:
            raise ValueError("fact planHash must match the embedded plan")
        if self.guidance_hash != self.plan.guidance_hash:
            raise ValueError("fact guidanceHash must match the embedded plan")
        if self.code == "semantic.shot_duration_budget_exceeded":
            if self.path != ("shots",):
                raise ValueError("shot total timing fact must target shots")
        elif (
            len(self.path) != 3
            or self.path[0] != "shots"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "cueIds"
        ):
            raise ValueError("cue fit timing fact must target one shot cueIds list")
        return self


def timing_lower_bound(*, total_cue_duration: int, cue_count: int, shot_count: int) -> int:
    return total_cue_duration + max(0, shot_count - cue_count)


def effective_max_shots(
    *,
    configured_max_shots: int,
    scene_duration_budget_units: int,
    total_cue_duration: int,
    cue_count: int,
) -> int:
    return min(
        configured_max_shots,
        cue_count + scene_duration_budget_units - total_cue_duration,
    )


def build_storyboard_timing_guidance(
    *,
    scene_id: str,
    scene_duration_budget_units: int,
    min_shots: int,
    configured_max_shots: int,
    beats: Sequence[Mapping[str, Any]],
    cues: Sequence[Mapping[str, Any]],
) -> StoryboardTimingGuidance:
    """Build a validated current guidance object or fail before a provider."""

    frozen_beats = tuple(
        sorted(
            (
                StoryboardBeatTimingGuidance(
                    beat_id=_required_str(beat, "id", "invalid beat timing identity"),
                    order=_required_int(beat, "order", "invalid beat timing identity"),
                )
                for beat in beats
            ),
            key=lambda beat: (beat.order, beat.beat_id),
        )
    )
    if len({beat.beat_id for beat in frozen_beats}) != len(frozen_beats):
        raise ValueError("invalid duplicate beat timing identity")
    beat_order = {beat.beat_id: beat.order for beat in frozen_beats}
    frozen_cues = tuple(
        sorted(
            (
                StoryboardCueTimingGuidance(
                    cue_id=_required_str(cue, "id", "invalid dialogue cue timing"),
                    beat_id=_required_str(cue, "beatId", "invalid dialogue cue timing"),
                    beat_order=beat_order[_required_str(cue, "beatId", "invalid dialogue cue timing")],
                    cue_order=_required_int(cue, "order", "invalid dialogue cue timing"),
                    estimated_duration_units=_required_int(cue, "estimatedDurationUnits", "invalid dialogue cue timing"),
                )
                for cue in cues
            ),
            key=lambda cue: (cue.beat_order, cue.cue_order, cue.cue_id),
        )
    )
    total = sum(cue.estimated_duration_units for cue in frozen_cues)
    lower = timing_lower_bound(total_cue_duration=total, cue_count=len(frozen_cues), shot_count=min_shots)
    maximum = effective_max_shots(
        configured_max_shots=configured_max_shots,
        scene_duration_budget_units=scene_duration_budget_units,
        total_cue_duration=total,
        cue_count=len(frozen_cues),
    )
    if lower > scene_duration_budget_units or min_shots > maximum:
        raise StoryboardTimingInfeasibleError()
    return StoryboardTimingGuidance(
        scene_id=scene_id,
        scene_duration_budget_units=scene_duration_budget_units,
        min_shots=min_shots,
        max_shots=maximum,
        configured_max_shots=configured_max_shots,
        beats=frozen_beats,
        cues=frozen_cues,
    )


class StoryboardTimingInfeasibleError(ValueError):
    code = "contract.storyboard_timing_infeasible"


def build_storyboard_timing_repair_plan(
    value: Mapping[str, Any],
    *,
    guidance: StoryboardTimingGuidance,
) -> StoryboardTimingRepairPlan | None:
    """Return a total replacement plan only when response identity is safe."""

    shots = value.get("shots")
    primary_map = value.get("primaryShotLocalIdByBeat")
    supporting = value.get("supportingBeatLinks")
    if not isinstance(shots, list) or not isinstance(primary_map, Mapping) or not isinstance(supporting, list):
        return None
    if not guidance.min_shots <= len(shots) <= guidance.max_shots:
        return None
    parsed_shots: list[dict[str, Any]] = []
    for index, shot in enumerate(shots):
        if not isinstance(shot, Mapping):
            return None
        local_id = shot.get("localShotId")
        order = shot.get("order")
        cue_ids = shot.get("cueIds")
        audio = shot.get("audioPlan")
        if (
            not isinstance(local_id, str)
            or not local_id
            or not isinstance(order, int)
            or isinstance(order, bool)
            or order < 1
            or not isinstance(cue_ids, list)
            or not all(isinstance(cue, str) for cue in cue_ids)
            or not isinstance(audio, Mapping)
            or not isinstance(audio.get("events"), list)
        ):
            return None
        parsed_shots.append({"id": local_id, "order": order, "cueIds": cue_ids, "events": audio["events"], "index": index})
    ids = [item["id"] for item in parsed_shots]
    if len(ids) != len(set(ids)) or sorted(item["order"] for item in parsed_shots) != list(range(1, len(parsed_shots) + 1)):
        return None
    shot_ids = set(ids)
    cue_by_id = {cue.cue_id: cue for cue in guidance.cues}
    scheduled = [cue_id for shot in parsed_shots for cue_id in shot["cueIds"]]
    if sorted(scheduled) != sorted(cue_by_id):
        return None
    # Coverage must already be a safe identity before timing code can preserve
    # it.  Missing/cross-unit coverage is repaired by its existing dedicated
    # semantic path first; this avoids a timing plan hiding unrelated damage.
    if set(primary_map) != {beat.beat_id for beat in guidance.beats} or any(
        not isinstance(shot_id, str) or shot_id not in shot_ids
        for shot_id in primary_map.values()
    ):
        return None
    primary_pairs = {(str(shot_id), beat_id) for beat_id, shot_id in primary_map.items()}
    supporting_pairs: set[tuple[str, str]] = set()
    parsed_supporting: list[StoryboardTimingPlanSupportingLink] = []
    beat_ids = {beat.beat_id for beat in guidance.beats}
    for link in supporting:
        if not isinstance(link, Mapping):
            return None
        shot_id, beat_id, weight = link.get("shotLocalId"), link.get("beatId"), link.get("coverageWeight")
        if (
            not isinstance(shot_id, str) or shot_id not in shot_ids
            or not isinstance(beat_id, str) or beat_id not in beat_ids
            or not isinstance(weight, (int, float)) or isinstance(weight, bool)
            or not 0 < float(weight) <= 1
            or (shot_id, beat_id) in supporting_pairs
            or (shot_id, beat_id) in primary_pairs
        ):
            return None
        supporting_pairs.add((shot_id, beat_id))
        parsed_supporting.append(StoryboardTimingPlanSupportingLink(shot_local_id=shot_id, beat_id=beat_id, coverage_weight=float(weight)))
    covered = primary_pairs | supporting_pairs
    if shot_ids - {shot_id for shot_id, _beat_id in covered}:
        return None
    for shot in parsed_shots:
        for cue_id in shot["cueIds"]:
            if (shot["id"], cue_by_id[cue_id].beat_id) not in covered:
                return None
    ordered_shots = sorted(parsed_shots, key=lambda shot: shot["order"])
    assigned: dict[str, list[str]] = {shot["id"]: [] for shot in ordered_shots}
    for index, cue in enumerate(guidance.cues):
        assigned[ordered_shots[index % len(ordered_shots)]["id"]].append(cue.cue_id)
    # Preserve full primary map and complete supporting map with only the
    # additional links required by the new deterministic cue placement.
    for shot in ordered_shots:
        for cue_id in assigned[shot["id"]]:
            pair = (shot["id"], cue_by_id[cue_id].beat_id)
            if pair not in covered:
                parsed_supporting.append(
                    StoryboardTimingPlanSupportingLink(
                        shot_local_id=pair[0], beat_id=pair[1], coverage_weight=1.0
                    )
                )
                covered.add(pair)
    plan_shots: list[StoryboardTimingPlanShot] = []
    for shot in ordered_shots:
        cue_ids = tuple(assigned[shot["id"]])
        target_duration = max(1, sum(cue_by_id[cue].estimated_duration_units for cue in cue_ids))
        removals: list[int] = []
        for index, event in enumerate(shot["events"]):
            if not isinstance(event, Mapping):
                return None
            start, duration = event.get("startOffsetUnits"), event.get("durationUnits")
            if (
                not isinstance(start, int) or isinstance(start, bool) or start < 0
                or not isinstance(duration, int) or isinstance(duration, bool) or duration < 1
            ):
                return None
            if start + duration > target_duration:
                removals.append(index)
        plan_shots.append(
            StoryboardTimingPlanShot(
                local_shot_id=shot["id"],
                target_order=shot["order"],
                target_duration_units=target_duration,
                target_cue_ids=cue_ids,
                remove_audio_event_indexes=tuple(sorted(removals, reverse=True)),
            )
        )
    primary = tuple(
        StoryboardTimingPlanPrimaryLink(beat_id=beat.beat_id, shot_local_id=str(primary_map[beat.beat_id]))
        for beat in guidance.beats
    )
    supporting_out = tuple(
        sorted(
            parsed_supporting,
            key=lambda link: (link.shot_local_id, next(beat.order for beat in guidance.beats if beat.beat_id == link.beat_id), link.beat_id),
        )
    )
    unsigned = {
        "version": STORYBOARD_TIMING_REPAIR_PLAN_VERSION,
        "sceneId": guidance.scene_id,
        "sceneDurationBudgetUnits": guidance.scene_duration_budget_units,
        "minShots": guidance.min_shots,
        "maxShots": guidance.max_shots,
        "beats": [beat.model_dump(mode="json", by_alias=True) for beat in guidance.beats],
        "cues": [cue.model_dump(mode="json", by_alias=True) for cue in guidance.cues],
        "targetShots": [shot.model_dump(mode="json", by_alias=True) for shot in plan_shots],
        "targetPrimaryLinks": [link.model_dump(mode="json", by_alias=True) for link in primary],
        "targetSupportingLinks": [link.model_dump(mode="json", by_alias=True) for link in supporting_out],
        "guidance": guidance.model_dump(mode="json", by_alias=True),
        "guidanceHash": storyboard_timing_guidance_hash(guidance),
    }
    return StoryboardTimingRepairPlan(**unsigned, plan_hash=_sha256(unsigned))


def _required_str(value: Mapping[str, Any], key: str, message: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(message)
    return item


def _required_int(value: Mapping[str, Any], key: str, message: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool) or item < 1:
        raise ValueError(message)
    return item


def _sha256(value: Any) -> str:
    return hashlib.sha256(finite_canonical_json(value).encode("utf-8")).hexdigest()
