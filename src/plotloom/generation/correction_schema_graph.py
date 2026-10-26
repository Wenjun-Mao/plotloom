"""GraphCorrectionSchema authority and projection."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..json_value_contract import finite_canonical_json
from .correction_schema_contracts import CorrectionResponseSchemaError
from .correction_schema_shapes import (
    _NO_EXPECTED_VALUE,
    _collection_item_schema,
    _merge_edge_state_constraint,
    _selected_item_branch,
)
from .graph_repair_contracts import (
    JoinAllowedDifferencesRepairFact,
    JoinStateEffectRepairFact,
)
from .repair_facts import (
    SemanticRepairFact,
)


class GraphCorrectionSchema:
    """Collect exact family authority, then project it deterministically."""

    def __init__(self) -> None:
        self.join_arrays: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
        self.edge_state_requirements: dict[str, dict[str, Any]] = {}
        self.applied_codes: set[str] = set()

    def collect(self, fact: SemanticRepairFact) -> bool:
        if isinstance(fact, JoinAllowedDifferencesRepairFact):
            required = fact.expected_required_state_keys
            allowed = fact.expected_allowed_differences
            replacement = (tuple(required), tuple(allowed))
            previous = self.join_arrays.setdefault(fact.join_contract_id, replacement)
            if previous != replacement:
                raise CorrectionResponseSchemaError(
                    "conflicting join-array repair facts target the same join contract"
                )
            for key_scope in fact.new_required_key_incoming_edges:
                for edge in key_scope.incoming_edges:
                    _merge_edge_state_constraint(
                        self.edge_state_requirements,
                        edge_id=edge.edge_id,
                        state_key=key_scope.state_key,
                        expected_value=_NO_EXPECTED_VALUE,
                    )
            self.applied_codes.add(fact.code)
            return True

        if isinstance(fact, JoinStateEffectRepairFact):
            expected_value = (
                deepcopy(fact.expected_value)
                if fact.has_expected_value
                else _NO_EXPECTED_VALUE
            )
            if fact.has_expected_value:
                # Keep response-schema constants within the finite JSON boundary
                # before sending them to a provider
                # schema even if its Pydantic shape remains readable.
                finite_canonical_json(expected_value)
            for edge in fact.incoming_edges:
                _merge_edge_state_constraint(
                    self.edge_state_requirements,
                    edge_id=edge.edge_id,
                    state_key=fact.state_key,
                    expected_value=expected_value,
                )
            for preserved_effect in fact.preserved_state_effects:
                for incoming_effect in preserved_effect.incoming_effects:
                    _merge_edge_state_constraint(
                        self.edge_state_requirements,
                        edge_id=incoming_effect.edge_id,
                        state_key=preserved_effect.state_key,
                        expected_value=deepcopy(incoming_effect.expected_value),
                    )
            self.applied_codes.add(fact.code)
            return True

        return False

    def apply(self, schema: dict[str, Any]) -> None:
        if self.join_arrays:
            item_schema = _collection_item_schema(schema, "joinContracts")
            branches = item_schema.setdefault("allOf", [])
            if not isinstance(branches, list):
                raise CorrectionResponseSchemaError(
                    "joinContracts item schema has a non-list allOf"
                )
            for join_id in sorted(self.join_arrays):
                required, allowed = self.join_arrays[join_id]
                branches.append(
                    _selected_item_branch(
                        "id",
                        join_id,
                        {
                            "requiredStateKeys": {"const": list(required)},
                            "allowedDifferences": {"const": list(allowed)},
                        },
                    )
                )

        if self.edge_state_requirements:
            item_schema = _collection_item_schema(schema, "edges")
            branches = item_schema.setdefault("allOf", [])
            if not isinstance(branches, list):
                raise CorrectionResponseSchemaError(
                    "edges item schema has a non-list allOf"
                )
            for edge_id in sorted(self.edge_state_requirements):
                constraints = self.edge_state_requirements[edge_id]
                state_properties: dict[str, Any] = {}
                for state_key in sorted(constraints):
                    expected = constraints[state_key]
                    state_properties[state_key] = (
                        {} if expected is _NO_EXPECTED_VALUE else {"const": expected}
                    )
                branches.append(
                    _selected_item_branch(
                        "id",
                        edge_id,
                        {
                            "stateEffects": {
                                "properties": state_properties,
                                "required": sorted(state_properties),
                            }
                        },
                    )
                )
