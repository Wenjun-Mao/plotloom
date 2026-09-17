"""Source-bound repair evidence for Storyboard required-entity presence.

This boundary fully parses the canonical Storyboard fragment before projecting
only the rejected requirement and same-shot depiction fields needed to explain
it. It does not import the work-unit compiler: Storyboard validation and
correction orchestration remain the owners of when this projection is requested.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from ..canonical_schema import AudioKind, NonBlankText, V2ShotSize
from ..domain import CamelModel, ContinuityStateV2, EntityType, RequiredEntityState
from .contracts import ValidationIssue
from .fragment_semantics import required_entity_is_in_shot


class RequiredEntityPresenceRepairFact(CamelModel):
    """Source-bound depiction context for one absent required entity state.

    The fact does not choose whether to delete the requirement or add depicted
    membership. It makes that bounded creative choice auditable by carrying
    only the rejected requirement and the same-shot fields that establish what
    the response actually depicts.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.required_entity_not_in_shot"]
    path: tuple[str | int, ...]
    shot_local_id: NonBlankText
    entity_type: EntityType
    entity_id: NonBlankText
    state: NonBlankText
    character_ids: tuple[NonBlankText, ...]
    location_id: NonBlankText | None
    prop_ids: tuple[NonBlankText, ...]
    action: str
    composition: str

    @model_validator(mode="after")
    def validate_absent_same_shot_membership(self) -> "RequiredEntityPresenceRepairFact":
        if (
            len(self.path) != 5
            or self.path[0] != "shots"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "requiredEntityStates"
            or not isinstance(self.path[3], int)
            or isinstance(self.path[3], bool)
            or self.path[3] < 0
            or self.path[4] != "entityId"
        ):
            raise ValueError("path must identify one requiredEntityStates entityId")
        if self.entity_type == EntityType.CHARACTER:
            is_present = self.entity_id in self.character_ids
        elif self.entity_type == EntityType.LOCATION:
            is_present = self.entity_id == self.location_id
        else:
            is_present = self.entity_id in self.prop_ids
        if is_present:
            raise ValueError("presence repair fact requires an entity absent from its shot")
        return self


class AudioEventContent(CamelModel):
    """Model-authored audio semantics, without a canonical event identifier."""

    kind: AudioKind
    description: str = Field(min_length=1)
    start_offset_units: int = Field(ge=0)
    duration_units: int = Field(ge=1)


class AudioPlanContent(CamelModel):
    """Model-facing audio events; the binder owns stable event IDs."""

    events: list[AudioEventContent]


class ShotContent(CamelModel):
    """Model-authored shot fields, without the selected dramatic-scene ID."""

    local_shot_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    title: str = Field(min_length=1)
    shot_size: V2ShotSize
    duration_units: int = Field(ge=1)
    camera_angle: str
    camera_movement: str
    composition: str
    visual_intent: str
    motion_intent: str
    action: str
    transition: str
    cue_ids: list[str]
    audio_plan: AudioPlanContent
    character_ids: list[str]
    location_id: str | None
    prop_ids: list[str]
    required_entity_states: list[RequiredEntityState]
    entry_state: ContinuityStateV2
    exit_state: ContinuityStateV2


class SupportingBeatLinkContent(CamelModel):
    """Optional non-primary coverage; the binder owns its fixed role."""

    shot_local_id: str = Field(min_length=1)
    beat_id: str = Field(min_length=1)
    coverage_weight: float = Field(gt=0, le=1)


class StoryboardFragmentOutput(CamelModel):
    """Model content for one scene; trusted code owns parent and PRIMARY links."""

    shots: list[ShotContent] = Field(min_length=1)
    primary_shot_local_id_by_beat: dict[str, str] = Field(min_length=1)
    supporting_beat_links: list[SupportingBeatLinkContent] = Field(default_factory=list)


def storyboard_required_entity_presence_repair_facts(
    value: Any,
    issues: tuple[ValidationIssue, ...],
) -> tuple[RequiredEntityPresenceRepairFact, ...]:
    """Project rejected shot membership and depiction context without choosing a fix."""

    relevant_issues = tuple(
        issue
        for issue in issues
        if issue.code == "semantic.required_entity_not_in_shot"
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
    facts: list[RequiredEntityPresenceRepairFact] = []
    for issue in relevant_issues:
        path = issue.path
        if (
            len(path) != 5
            or path[0] != "shots"
            or not isinstance(path[1], int)
            or isinstance(path[1], bool)
            or path[1] < 0
            or path[2] != "requiredEntityStates"
            or not isinstance(path[3], int)
            or isinstance(path[3], bool)
            or path[3] < 0
            or path[4] != "entityId"
        ):
            continue
        shot_index = path[1]
        state_index = path[3]
        if shot_index >= len(output.shots):
            continue
        shot = output.shots[shot_index]
        if state_index >= len(shot.required_entity_states):
            continue
        requirement = shot.required_entity_states[state_index]
        if required_entity_is_in_shot(requirement, shot):
            continue
        facts.append(
            RequiredEntityPresenceRepairFact(
                code=issue.code,
                path=path,
                shot_local_id=shot.local_shot_id,
                entity_type=requirement.entity_type,
                entity_id=requirement.entity_id,
                state=requirement.state,
                character_ids=tuple(shot.character_ids),
                location_id=shot.location_id,
                prop_ids=tuple(shot.prop_ids),
                action=shot.action,
                composition=shot.composition,
            )
        )
    return tuple(facts)


def assert_required_entity_presence_repair_fact_matches_source(
    fact: RequiredEntityPresenceRepairFact,
    source_value: Any,
    *,
    issues: tuple[ValidationIssue, ...],
) -> None:
    """Prove a persisted depiction fact was derived from its rejected response."""

    current_facts = storyboard_required_entity_presence_repair_facts(
        source_value,
        issues,
    )
    if fact not in current_facts:
        raise ValueError(
            "required-entity presence repair fact does not match the rejected source"
        )
