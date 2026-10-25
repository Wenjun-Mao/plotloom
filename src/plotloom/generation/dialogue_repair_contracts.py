"""Frozen dialogue capacity, node budget and cue-order authority."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ..canonical_schema import NonBlankText
from ..domain import CamelModel, DialogueDeliveryPace


class DialogueCapacityDeliveryLimit(CamelModel):
    """One frozen delivery option made safe by the portable schema cap."""

    model_config = CamelModel.model_config | {"frozen": True}

    delivery: DialogueDeliveryPace
    max_text_codepoints: int = Field(ge=0)


class DialogueCapacityRepairFact(CamelModel):
    """Exact, non-prose authority for one rejected Scene Beats cue.

    The fact never copies the cue text.  It makes the one trusted capacity cap
    and compatible delivery choices directly visible to a bounded correction,
    rather than asking a provider to traverse a larger contract and recreate
    Unicode arithmetic.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.dialogue_cue_capacity_exceeded"]
    path: tuple[str | int, ...]
    authoring_language: NonBlankText
    language: NonBlankText
    delivery: DialogueDeliveryPace
    current_text_codepoints: int = Field(ge=1)
    max_text_codepoints: int = Field(ge=0)
    compatible_delivery_limits: tuple[DialogueCapacityDeliveryLimit, ...] = Field(
        min_length=1
    )

    @model_validator(mode="after")
    def validate_issue_identity_and_limits(self) -> "DialogueCapacityRepairFact":
        if (
            len(self.path) != 3
            or self.path[0] != "dialogueCues"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "text"
        ):
            raise ValueError("path must identify one dialogueCues text value")
        if self.language != self.authoring_language:
            raise ValueError(
                "capacity facts only authorize the frozen authoring language"
            )
        deliveries = [item.delivery for item in self.compatible_delivery_limits]
        if len(deliveries) != len(set(deliveries)):
            raise ValueError("compatible delivery limits must be unique")
        current = next(
            (
                item
                for item in self.compatible_delivery_limits
                if item.delivery == self.delivery
            ),
            None,
        )
        if current is None or current.max_text_codepoints != self.max_text_codepoints:
            raise ValueError("current delivery must carry the exact text cap")
        return self


class DialogueNodeBudgetRemainingCue(CamelModel):
    """One retained cue's deterministic post-deletion order."""

    model_config = CamelModel.model_config | {"frozen": True}

    local_cue_id: NonBlankText
    beat_local_id: NonBlankText
    expected_order: int = Field(ge=1)


class DialogueNodeBudgetRepairFact(CamelModel):
    """A complete, text-free repair plan for an over-budget dialogue node.

    The model cannot reliably count CJK code points or recompute a frozen
    timing profile.  This fact therefore selects the smallest deterministic
    deletion set and the only required renumbering.  It remains a correction
    instruction, never a server-side mutation of the rejected response.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.dialogue_exceeds_node_budget"]
    path: tuple[str | int, ...]
    node_id: NonBlankText
    node_duration_budget_units: int = Field(ge=1)
    current_minimum_duration_units: int = Field(ge=1)
    remove_local_cue_ids: tuple[NonBlankText, ...] = Field(min_length=1)
    remaining_cues: tuple[DialogueNodeBudgetRemainingCue, ...]
    remaining_minimum_duration_units: int = Field(ge=0)
    repair_strategy: Literal["remove_and_renumber"] = "remove_and_renumber"

    @model_validator(mode="after")
    def validate_deterministic_plan(self) -> "DialogueNodeBudgetRepairFact":
        if self.path != ("dialogueCues",):
            raise ValueError("path must identify the complete dialogueCues collection")
        if self.current_minimum_duration_units <= self.node_duration_budget_units:
            raise ValueError("dialogue node budget fact requires an actual overage")
        if self.remaining_minimum_duration_units > self.node_duration_budget_units:
            raise ValueError(
                "deterministic deletion plan must fit the frozen node budget"
            )
        if len(self.remove_local_cue_ids) != len(set(self.remove_local_cue_ids)):
            raise ValueError("removeLocalCueIds must be unique")
        retained_ids = [item.local_cue_id for item in self.remaining_cues]
        if len(retained_ids) != len(set(retained_ids)):
            raise ValueError("remaining cue IDs must be unique")
        if set(self.remove_local_cue_ids) & set(retained_ids):
            raise ValueError("a cue cannot be both removed and retained")
        by_beat: dict[str, list[int]] = {}
        for item in self.remaining_cues:
            by_beat.setdefault(item.beat_local_id, []).append(item.expected_order)
        if any(
            sorted(orders) != list(range(1, len(orders) + 1))
            for orders in by_beat.values()
        ):
            raise ValueError("remaining cue orders must be contiguous within each beat")
        return self


class CueOrderRepairAssignment(CamelModel):
    """One response-local cue's exact beat ownership and repaired order."""

    model_config = CamelModel.model_config | {"frozen": True}

    # Fragment-local handles are the only stable identities available before
    # trusted canonical binding.  Canonical cue IDs intentionally cannot be
    # used here because their derivation includes the mutable cue order.
    local_cue_id: NonBlankText
    beat_local_id: NonBlankText
    expected_order: int = Field(ge=1)


class CueOrderRepairFact(CamelModel):
    """Complete, identity-preserving renumbering for Scene Beats dialogue.

    The aggregate semantic issue has no individual cue path.  This fact makes
    every response-local cue identity, its existing beat ownership, and its
    exact contiguous replacement order explicit without carrying dialogue
    text or validator prose.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.cue_order"]
    path: tuple[str | int, ...]
    assignments: tuple[CueOrderRepairAssignment, ...] = Field(min_length=1)
    repair_strategy: Literal["preserve_membership_and_renumber"] = (
        "preserve_membership_and_renumber"
    )

    @model_validator(mode="after")
    def validate_complete_renumbering(self) -> "CueOrderRepairFact":
        if self.path != ("dialogueCues",):
            raise ValueError("path must identify the complete dialogueCues collection")
        cue_ids = [item.local_cue_id for item in self.assignments]
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("cue-order assignment local cue IDs must be unique")
        expected_sort = tuple(
            sorted(self.assignments, key=lambda item: item.local_cue_id)
        )
        if self.assignments != expected_sort:
            raise ValueError(
                "cue-order assignments must use canonical local cue ID order"
            )
        by_beat: dict[str, list[int]] = {}
        for item in self.assignments:
            by_beat.setdefault(item.beat_local_id, []).append(item.expected_order)
        if any(
            sorted(orders) != list(range(1, len(orders) + 1))
            for orders in by_beat.values()
        ):
            raise ValueError(
                "cue-order assignments must be contiguous within each beat"
            )
        return self
