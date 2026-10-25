"""Frozen continuity endpoint, assignment and sequence authority."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field, model_validator

from ..canonical_schema import NonBlankText
from ..domain import CamelModel, EntityType
from ..json_value_contract import finite_canonical_json

CONTINUITY_SEQUENCE_OWNERSHIP_POLICY_VERSION = "continuity_sequence.boundary_owner.v1"


class ContinuityStateEndpoint(CamelModel):
    """One state boundary identified without relying on an array index."""

    model_config = CamelModel.model_config | {"frozen": True}

    kind: Literal["scene", "beat", "shot"]
    id: NonBlankText
    id_scope: Literal["response_local", "canonical_context"]
    state: Literal["entry", "exit"]


class ContinuityFactAssignment(CamelModel):
    """Copy one finite JSON fact from a prior boundary to its successor."""

    model_config = CamelModel.model_config | {"frozen": True}

    kind: Literal["fact"]
    key: NonBlankText
    expected_value: Any

    @model_validator(mode="after")
    def validate_finite_expected_value(self) -> "ContinuityFactAssignment":
        finite_canonical_json(self.expected_value)
        return self


class ContinuityEntityStateAssignment(CamelModel):
    """Copy an already-valid entity state without changing its identity."""

    model_config = CamelModel.model_config | {"frozen": True}

    kind: Literal["entity_state"]
    entity_type: EntityType
    entity_id: NonBlankText
    expected_state: NonBlankText


class ContinuityScalarAssignment(CamelModel):
    """Copy one shared visual/audio scalar at an incompatible boundary."""

    model_config = CamelModel.model_config | {"frozen": True}

    kind: Literal["scalar"]
    field: Literal["screenDirection", "lighting", "sound"]
    expected_value: NonBlankText


ContinuityRepairAssignment: TypeAlias = Annotated[
    ContinuityFactAssignment
    | ContinuityEntityStateAssignment
    | ContinuityScalarAssignment,
    Field(discriminator="kind"),
]


class ContinuityBoundaryRepair(CamelModel):
    """All exact assignments at one left-to-right sequence boundary."""

    model_config = CamelModel.model_config | {"frozen": True}

    source: ContinuityStateEndpoint
    target: ContinuityStateEndpoint
    assignments: tuple[ContinuityRepairAssignment, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_direction_and_unique_targets(self) -> "ContinuityBoundaryRepair":
        if self.source == self.target:
            raise ValueError("continuity boundary source and target must differ")
        keys: list[tuple[str, str, str]] = []
        for assignment in self.assignments:
            if isinstance(assignment, ContinuityFactAssignment):
                keys.append(("fact", assignment.key, ""))
            elif isinstance(assignment, ContinuityEntityStateAssignment):
                keys.append(
                    ("entity_state", assignment.entity_type.value, assignment.entity_id)
                )
            else:
                keys.append(("scalar", assignment.field, ""))
        if len(keys) != len(set(keys)):
            raise ValueError("continuity boundary assignments must not overlap")
        return self


class ContinuitySequenceRepairFact(CamelModel):
    """A complete exact repair plan for one incompatible local sequence.

    The versioned ownership rule uses sequence order for Scene Beats.  For
    Storyboard, frozen canonical scene context owns both outer boundaries.
    It is deliberately a correction-only policy; canonical validation
    continues to reject a mismatched response before any plan is derived.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal[
        "semantic.continuity_beat_sequence_mismatch",
        "semantic.continuity_shot_sequence_mismatch",
    ]
    path: tuple[str | int, ...]
    ownership_policy_version: Literal[CONTINUITY_SEQUENCE_OWNERSHIP_POLICY_VERSION] = (
        CONTINUITY_SEQUENCE_OWNERSHIP_POLICY_VERSION
    )
    sequence_kind: Literal["beat", "shot"]
    owner: ContinuityStateEndpoint
    ordered_item_ids: tuple[NonBlankText, ...] = Field(min_length=1)
    boundaries: tuple[ContinuityBoundaryRepair, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_issue_identity_and_direction(self) -> "ContinuitySequenceRepairFact":
        if len(self.ordered_item_ids) != len(set(self.ordered_item_ids)):
            raise ValueError("continuity sequence item IDs must be unique")
        if self.code == "semantic.continuity_beat_sequence_mismatch":
            if (
                self.sequence_kind != "beat"
                or len(self.path) != 2
                or self.path[0] != "scenes"
                or not isinstance(self.path[1], int)
                or isinstance(self.path[1], bool)
                or self.path[1] < 0
                or self.owner.kind != "scene"
                or self.owner.id_scope != "response_local"
                or self.owner.state != "entry"
            ):
                raise ValueError(
                    "beat continuity repair must identify one response-local scene"
                )
        elif (
            self.sequence_kind != "shot"
            or self.path != ("shots",)
            or self.owner.kind != "scene"
            or self.owner.id_scope != "canonical_context"
            or self.owner.state != "entry"
        ):
            raise ValueError(
                "shot continuity repair must identify the canonical selected scene"
            )
        legal_boundaries = _legal_continuity_repair_boundaries(
            sequence_kind=self.sequence_kind,
            owner=self.owner,
            ordered_item_ids=self.ordered_item_ids,
        )
        for boundary in self.boundaries:
            if (boundary.source, boundary.target) not in legal_boundaries:
                raise ValueError(
                    "continuity repair boundary is not adjacent in its owned sequence"
                )
        targets = [
            (boundary.target.kind, boundary.target.id, boundary.target.state)
            for boundary in self.boundaries
        ]
        if len(targets) != len(set(targets)):
            raise ValueError(
                "continuity sequence boundaries must not share a target state"
            )
        return self


def _legal_continuity_repair_boundaries(
    *,
    sequence_kind: Literal["beat", "shot"],
    owner: ContinuityStateEndpoint,
    ordered_item_ids: tuple[str, ...],
) -> set[tuple[ContinuityStateEndpoint, ContinuityStateEndpoint]]:
    item_scope: Literal["response_local"] = "response_local"
    item_entries = [
        ContinuityStateEndpoint(
            kind=sequence_kind,
            id=item_id,
            id_scope=item_scope,
            state="entry",
        )
        for item_id in ordered_item_ids
    ]
    item_exits = [
        ContinuityStateEndpoint(
            kind=sequence_kind,
            id=item_id,
            id_scope=item_scope,
            state="exit",
        )
        for item_id in ordered_item_ids
    ]
    legal = {
        (item_exits[index], item_entries[index + 1])
        for index in range(len(ordered_item_ids) - 1)
    }
    legal.add((owner, item_entries[0]))
    if sequence_kind == "beat":
        legal.add(
            (
                item_exits[-1],
                ContinuityStateEndpoint(
                    kind="scene",
                    id=owner.id,
                    id_scope="response_local",
                    state="exit",
                ),
            )
        )
    else:
        legal.add(
            (
                ContinuityStateEndpoint(
                    kind="scene",
                    id=owner.id,
                    id_scope="canonical_context",
                    state="exit",
                ),
                item_exits[-1],
            )
        )
    return legal


class ContinuityEntityStateRepairFact(CamelModel):
    """One source-bound Bible vocabulary repair at a continuity boundary.

    This fact deliberately names both the original response array path and
    its response-local parent identity.  A correction cannot evade the
    rejected assignment by deleting, replacing, or moving that entry.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.invalid_continuity_entity_state"]
    path: tuple[str | int, ...]
    target: ContinuityStateEndpoint
    entity_state_index: int = Field(ge=0)
    entity_type: EntityType
    entity_id: NonBlankText
    allowed_states: tuple[NonBlankText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_exact_response_target(self) -> "ContinuityEntityStateRepairFact":
        collections = {
            "scenes": ("scene", "localSceneId"),
            "beats": ("beat", "localBeatId"),
            "shots": ("shot", "localShotId"),
        }
        if (
            len(self.path) != 6
            or self.path[0] not in collections
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] not in {"entryState", "exitState"}
            or self.path[3] != "entityStates"
            or self.path[4] != self.entity_state_index
            or self.path[5] != "state"
        ):
            raise ValueError(
                "path must identify one continuity entityStates state value"
            )
        expected_kind, _identity = collections[self.path[0]]
        if (
            self.target.kind != expected_kind
            or self.target.id_scope != "response_local"
            or self.target.state
            != ("entry" if self.path[2] == "entryState" else "exit")
        ):
            raise ValueError(
                "target must identify the exact response-local continuity boundary"
            )
        if len(self.allowed_states) != len(set(self.allowed_states)):
            raise ValueError("allowedStates must be unique")
        return self
