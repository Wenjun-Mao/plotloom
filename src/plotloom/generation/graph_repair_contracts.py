"""Frozen graph edge and join repair authority."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from ..canonical_schema import NonBlankText
from plotloom.domain_base import CamelModel
from ..json_value_contract import finite_canonical_json


class JoinIncomingEdgeRepairTarget(CamelModel):
    """Frozen direct incoming edge identity, never a model-selected endpoint."""

    model_config = CamelModel.model_config | {"frozen": True}

    edge_id: NonBlankText
    source_node_id: NonBlankText


class JoinNewRequiredKeyIncomingEdges(CamelModel):
    """Edges that must receive a key promoted into a join requirement."""

    model_config = CamelModel.model_config | {"frozen": True}

    state_key: NonBlankText
    incoming_edges: tuple[JoinIncomingEdgeRepairTarget, ...] = Field(min_length=2)


class JoinAllowedDifferencesRepairFact(CamelModel):
    """Complete, intent-preserving replacement arrays for one join contract.

    A reconstruction correction must not infer the pre-existing required keys
    or allowed differences from the previous untrusted response. This fact
    therefore carries both complete arrays after the safe subset repair, while
    retaining the exact missing keys as auditable derivation evidence.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.join_allowed_differences_must_be_required"]
    path: tuple[str | int, ...]
    join_contract_id: str = Field(min_length=1)
    missing_required_state_keys: tuple[NonBlankText, ...] = Field(min_length=1)
    expected_required_state_keys: tuple[NonBlankText, ...] = Field(
        min_length=1,
    )
    expected_allowed_differences: tuple[NonBlankText, ...] = Field(
        min_length=1,
    )
    new_required_key_incoming_edges: tuple[JoinNewRequiredKeyIncomingEdges, ...]

    @model_validator(mode="after")
    def validate_issue_identity_and_missing_keys(
        self,
    ) -> "JoinAllowedDifferencesRepairFact":
        expected_path = (
            "joinContracts",
            self.join_contract_id,
            "allowedDifferences",
        )
        if self.path != expected_path:
            raise ValueError("path must identify allowedDifferences for joinContractId")
        if len(self.missing_required_state_keys) != len(
            set(self.missing_required_state_keys)
        ):
            raise ValueError("missingRequiredStateKeys must be unique")
        if len(self.expected_required_state_keys) != len(
            set(self.expected_required_state_keys)
        ):
            raise ValueError("expectedRequiredStateKeys must be unique")
        if len(self.expected_allowed_differences) != len(
            set(self.expected_allowed_differences)
        ):
            raise ValueError("expectedAllowedDifferences must be unique")
        required = set(self.expected_required_state_keys)
        allowed = set(self.expected_allowed_differences)
        missing = set(self.missing_required_state_keys)
        if not allowed <= required:
            raise ValueError(
                "expectedAllowedDifferences must be a subset of expectedRequiredStateKeys"
            )
        if not missing <= allowed:
            raise ValueError(
                "missingRequiredStateKeys must belong to expectedAllowedDifferences"
            )
        targets = {
            item.state_key: item for item in self.new_required_key_incoming_edges
        }
        if set(targets) != missing:
            raise ValueError(
                "newRequiredKeyIncomingEdges must name exactly the promoted keys"
            )
        for item in targets.values():
            edge_ids = [edge.edge_id for edge in item.incoming_edges]
            if len(edge_ids) != len(set(edge_ids)):
                raise ValueError("incoming edge targets must be unique")
        return self


class JoinPreservedIncomingStateEffect(CamelModel):
    """One source-validated state value retained on a frozen incoming edge."""

    model_config = CamelModel.model_config | {"frozen": True}

    edge_id: NonBlankText
    expected_value: Any

    @model_validator(mode="after")
    def validate_expected_value(self) -> "JoinPreservedIncomingStateEffect":
        finite_canonical_json(self.expected_value)
        return self


class JoinPreservedStateEffect(CamelModel):
    """One still-valid required key and its exact values on every incoming edge."""

    model_config = CamelModel.model_config | {"frozen": True}

    state_key: NonBlankText
    incoming_effects: tuple[JoinPreservedIncomingStateEffect, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_incoming_effects(self) -> "JoinPreservedStateEffect":
        edge_ids = [effect.edge_id for effect in self.incoming_effects]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("preserved incoming edge effects must be unique")
        return self


class JoinStateEffectRepairFact(CamelModel):
    """Path-bound join edge repair guidance derived from frozen topology."""

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal[
        "semantic.join_state_effect_missing",
        "semantic.join_state_effect_conflict",
    ]
    path: tuple[str | int, ...]
    join_contract_id: NonBlankText
    join_node_id: NonBlankText
    state_key: NonBlankText
    mode: Literal["convergent", "variant"]
    incoming_edges: tuple[JoinIncomingEdgeRepairTarget, ...] = Field(min_length=2)
    repair_action: Literal[
        "set_missing",
        "make_all_equal",
    ]
    # JSON null is a legitimate exact state value, so absence cannot be
    # represented by ``expectedValue is None`` alone.
    has_expected_value: bool = False
    expected_value: Any | None = None
    # Sibling keys are authority only when this rejected response already
    # satisfies their full join contract. Keys with their own repairable issue
    # are deliberately absent, so simultaneous repairs never freeze invalid
    # fields or contradict one another.
    preserved_state_effects: tuple[JoinPreservedStateEffect, ...] = ()

    @model_validator(mode="after")
    def validate_join_effect_target(self) -> "JoinStateEffectRepairFact":
        edge_ids = [edge.edge_id for edge in self.incoming_edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("incoming edge targets must be unique")
        if self.code == "semantic.join_state_effect_conflict":
            if self.path != (
                "joinContracts",
                self.join_contract_id,
                "requiredStateKeys",
                self.state_key,
            ):
                raise ValueError(
                    "conflict path must identify one join requiredStateKey"
                )
        elif (
            len(self.path) != 4
            or self.path[0] != "edges"
            or not isinstance(self.path[1], str)
            or self.path[1] not in edge_ids
            or self.path[2] != "stateEffects"
            or self.path[3] != self.state_key
        ):
            raise ValueError("path must identify one direct incoming edge state effect")
        if self.repair_action == "make_all_equal" and self.mode != "convergent":
            raise ValueError("only convergent join keys may require equal values")
        if self.has_expected_value:
            finite_canonical_json(self.expected_value)
        elif "expected_value" in self.model_fields_set:
            # ``null`` is an authorized state value only when the explicit
            # presence bit says so.  Accepting an explicit null here would
            # turn absence of repair authority into an ambiguous instruction.
            raise ValueError("expectedValue requires hasExpectedValue=true")
        preserved_keys = [effect.state_key for effect in self.preserved_state_effects]
        if len(preserved_keys) != len(set(preserved_keys)):
            raise ValueError("preservedStateEffects must use unique state keys")
        if self.state_key in preserved_keys:
            raise ValueError(
                "preservedStateEffects cannot constrain the repaired state key"
            )
        incoming_edge_ids = tuple(edge.edge_id for edge in self.incoming_edges)
        for effect in self.preserved_state_effects:
            if (
                tuple(item.edge_id for item in effect.incoming_effects)
                != incoming_edge_ids
            ):
                raise ValueError(
                    "preservedStateEffects must cover the exact ordered incoming edge set"
                )
        return self


class EdgeStateEffectJsonRepairFact(CamelModel):
    """One frozen topology edge whose state value must become finite JSON.

    Finite-JSON is a graph-wide invariant, not a special property of join
    edges.  The correction boundary therefore binds the selected edge to its
    topology-owned endpoints, while deliberately withholding a guessed
    replacement value.
    """

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.state_effect_not_json"]
    path: tuple[str | int, ...]
    edge_id: NonBlankText
    source_node_id: NonBlankText
    target_node_id: NonBlankText
    state_key: NonBlankText
    repair_action: Literal["replace_with_finite_json"] = "replace_with_finite_json"

    @model_validator(mode="after")
    def validate_edge_state_effect_target(self) -> "EdgeStateEffectJsonRepairFact":
        if self.path != ("edges", self.edge_id, "stateEffects", self.state_key):
            raise ValueError("path must identify the frozen edge state effect")
        return self


class JoinReconciliationRepairFact(CamelModel):
    """Typed non-prose authority for a missing required reconciliation."""

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal["semantic.join_allowed_difference_without_reconciliation"]
    path: tuple[str | int, ...]
    join_contract_id: NonBlankText
    allowed_difference_keys: tuple[NonBlankText, ...] = Field(min_length=1)
    repair_action: Literal["write_non_blank_reconciliation"] = (
        "write_non_blank_reconciliation"
    )

    @model_validator(mode="after")
    def validate_reconciliation_target(self) -> "JoinReconciliationRepairFact":
        if self.path != ("joinContracts", self.join_contract_id, "reconciliation"):
            raise ValueError("path must identify the join reconciliation")
        if len(self.allowed_difference_keys) != len(set(self.allowed_difference_keys)):
            raise ValueError("allowed difference keys must be unique")
        return self


class JoinEntryStateValueRepairFact(CamelModel):
    """Exact join-entry value compiled from sealed incoming edge effects."""

    model_config = CamelModel.model_config | {"frozen": True}

    code: Literal[
        "semantic.join_entry_state_value_missing",
        "semantic.join_entry_state_value_mismatch",
        "semantic.join_entry_state_value_not_json",
    ]
    path: tuple[str | int, ...]
    contract_version: str = Field(min_length=1)
    contract_hash: str = Field(min_length=64, max_length=64)
    state_key: NonBlankText
    expected_value: Any

    @model_validator(mode="after")
    def validate_exact_join_entry_path(self) -> "JoinEntryStateValueRepairFact":
        if (
            len(self.path) != 5
            or self.path[0] != "scenes"
            or not isinstance(self.path[1], int)
            or isinstance(self.path[1], bool)
            or self.path[1] < 0
            or self.path[2] != "entryState"
            or self.path[3] != "facts"
            or self.path[4] != self.state_key
        ):
            raise ValueError("path must identify one scene entryState fact")
        # Ensure the frozen repair authority uses the same finite JSON
        # identity as the compiler and both validators before it is rendered.
        finite_canonical_json(self.expected_value)
        return self
