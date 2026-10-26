"""Frozen Storyboard audio and entity vocabulary repair authority."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ..canonical_schema import NonBlankText
from plotloom.domain_base import CamelModel
from plotloom.canonical_schema import EntityType


class AudioTimingRepairFact(CamelModel):
    """One deterministic, path-bound correction for a timed audio event.

    Audio timing relates two sibling model fields and cannot be expressed by
    the portable provider JSON Schema subset.  The semantic validator owns the
    relationship, then supplies one exact replacement or removal action rather
    than asking a model to redo timing arithmetic from an error message.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.audio_timing"]
    path: tuple[str | int, ...]
    shot_local_id: NonBlankText
    event_index: int = Field(ge=0)
    start_offset_units: int = Field(ge=0)
    duration_units: int = Field(ge=1)
    shot_duration_units: int = Field(ge=1)
    repair_action: Literal["replace_duration", "remove_event"]
    replacement_duration_units: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_exact_timing_action(self) -> "AudioTimingRepairFact":
        # The shot index is intentionally not duplicated as an independently
        # mutable field.  It is the second component of the immutable issue
        # path, while ``event_index`` is the final selected event component.
        if (
            len(self.path) != 6
            or self.path[0] != "shots"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "audioPlan"
            or self.path[3] != "events"
            or self.path[4] != self.event_index
            or self.path[5] != "durationUnits"
        ):
            raise ValueError("path must identify one audioPlan event duration")
        remaining = self.shot_duration_units - self.start_offset_units
        if self.start_offset_units + self.duration_units <= self.shot_duration_units:
            raise ValueError("audio timing fact requires an out-of-bounds event")
        if remaining >= 1:
            if (
                self.repair_action != "replace_duration"
                or self.replacement_duration_units != remaining
            ):
                raise ValueError(
                    "replace_duration must use the exact remaining shot duration"
                )
        elif (
            self.repair_action != "remove_event"
            or self.replacement_duration_units is not None
        ):
            raise ValueError("an event starting at or after shot end must be removed")
        return self


class RequiredEntityStateRepairFact(CamelModel):
    """Trusted Story Bible choices for one invalid Storyboard state.

    The model-authored invalid value and validator prose are deliberately not
    carried forward.  A correction receives only the immutable entity identity
    and the exact allowed values from the frozen Story Bible dependency.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.invalid_required_entity_state"]
    path: tuple[str | int, ...]
    entity_type: EntityType
    entity_id: NonBlankText
    allowed_states: tuple[NonBlankText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_issue_identity_and_allowed_states(
        self,
    ) -> "RequiredEntityStateRepairFact":
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
            or self.path[4] != "state"
        ):
            raise ValueError("path must identify one requiredEntityStates state value")
        if len(self.allowed_states) != len(set(self.allowed_states)):
            raise ValueError("allowedStates must be unique")
        return self
