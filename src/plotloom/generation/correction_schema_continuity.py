"""ContinuityCorrectionSchema authority and projection."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..json_value_contract import finite_canonical_json
from .continuity_repair_contracts import (
    ContinuityEntityStateAssignment,
    ContinuityEntityStateRepairFact,
    ContinuityFactAssignment,
    ContinuityScalarAssignment,
    ContinuitySequenceRepairFact,
)
from .correction_schema_contracts import CorrectionResponseSchemaError
from .correction_schema_shapes import (
    _collection_schema,
    _continuity_collection,
    _merge_exact_constraint,
)
from .repair_facts import (
    SemanticRepairFact,
)
from .scene_beats_edge_entry import EdgeEntryEntityStateRepairFact


class ContinuityCorrectionSchema:
    """Collect exact family authority, then project it deterministically."""

    def __init__(self) -> None:
        self.continuity_requirements: dict[
            tuple[str, str, str, str],
            dict[str, Any],
        ] = {}
        self.continuity_entity_state_requirements: dict[
            tuple[str, str, str, str, int], ContinuityEntityStateRepairFact
        ] = {}
        self.applied_codes: set[str] = set()

    def collect(self, fact: SemanticRepairFact) -> bool:
        if isinstance(fact, ContinuitySequenceRepairFact):
            for boundary in fact.boundaries:
                target = boundary.target
                if target.id_scope != "response_local":
                    raise CorrectionResponseSchemaError(
                        "continuity correction target is outside the model response"
                    )
                collection, identity_field = _continuity_collection(target.kind)
                state_field = "entryState" if target.state == "entry" else "exitState"
                target_key = (collection, identity_field, target.id, state_field)
                target_constraints = self.continuity_requirements.setdefault(
                    target_key,
                    {"facts": {}, "entities": {}, "scalars": {}},
                )
                for assignment in boundary.assignments:
                    if isinstance(assignment, ContinuityFactAssignment):
                        finite_canonical_json(assignment.expected_value)
                        _merge_exact_constraint(
                            target_constraints["facts"],
                            assignment.key,
                            deepcopy(assignment.expected_value),
                            label="continuity fact",
                        )
                    elif isinstance(assignment, ContinuityEntityStateAssignment):
                        entity_key = (
                            assignment.entity_type.value,
                            assignment.entity_id,
                        )
                        _merge_exact_constraint(
                            target_constraints["entities"],
                            entity_key,
                            assignment.expected_state,
                            label="continuity entity state",
                        )
                    elif isinstance(assignment, ContinuityScalarAssignment):
                        _merge_exact_constraint(
                            target_constraints["scalars"],
                            assignment.field,
                            assignment.expected_value,
                            label="continuity scalar",
                        )
                    else:  # Defensive against a future union member.
                        raise CorrectionResponseSchemaError(
                            "unsupported continuity assignment type"
                        )
            self.applied_codes.add(fact.code)
            return True

        if isinstance(fact, ContinuityEntityStateRepairFact):
            target = fact.target
            if target.id_scope != "response_local":
                raise CorrectionResponseSchemaError(
                    "continuity entity-state correction target is outside the model response"
                )
            collection, identity_field = _continuity_collection(target.kind)
            state_field = "entryState" if target.state == "entry" else "exitState"
            key = (
                collection,
                identity_field,
                target.id,
                state_field,
                fact.entity_state_index,
            )
            previous = self.continuity_entity_state_requirements.setdefault(key, fact)
            if previous != fact:
                raise CorrectionResponseSchemaError(
                    "conflicting continuity entity-state repair facts target the same response path"
                )
            self.applied_codes.add(fact.code)
            return True

        if isinstance(fact, EdgeEntryEntityStateRepairFact):
            target_key = ("scenes", "localSceneId", fact.scene_local_id, "entryState")
            target_constraints = self.continuity_requirements.setdefault(
                target_key,
                {"facts": {}, "entities": {}, "scalars": {}},
            )
            _merge_exact_constraint(
                target_constraints["entities"],
                (fact.entity_type.value, fact.entity_id),
                fact.expected_state,
                label="typed direct-edge entry state",
            )
            self.applied_codes.add(fact.code)
            return True

        return False

    def apply(self, schema: dict[str, Any]) -> None:
        for collection, identity_field, identity, state_field in sorted(
            self.continuity_requirements
        ):
            requirements = self.continuity_requirements[
                (collection, identity_field, identity, state_field)
            ]
            state_properties: dict[str, Any] = {}
            state_required: list[str] = []
            if requirements["facts"]:
                state_properties["facts"] = {
                    "properties": {
                        key: {"const": requirements["facts"][key]}
                        for key in sorted(requirements["facts"])
                    },
                    "required": sorted(requirements["facts"]),
                }
                state_required.append("facts")
            if requirements["entities"]:
                entity_presence_constraints = []
                for entity_type, entity_id in sorted(requirements["entities"]):
                    entity_presence_constraints.append(
                        {
                            "contains": {
                                "type": "object",
                                "properties": {
                                    "entityType": {"const": entity_type},
                                    "entityId": {"const": entity_id},
                                    "state": {
                                        "const": requirements["entities"][
                                            (entity_type, entity_id)
                                        ]
                                    },
                                },
                                "required": ["entityType", "entityId", "state"],
                            },
                            "minContains": 1,
                            "maxContains": 1,
                        }
                    )
                state_properties["entityStates"] = {
                    "allOf": entity_presence_constraints,
                }
                state_required.append("entityStates")
            for field in sorted(requirements["scalars"]):
                state_properties[field] = {"const": requirements["scalars"][field]}
                state_required.append(field)
            collection_schema = _collection_schema(schema, collection)
            branches = collection_schema.setdefault("allOf", [])
            if not isinstance(branches, list):
                raise CorrectionResponseSchemaError(
                    f"{collection} schema has a non-list allOf"
                )
            branches.append(
                {
                    "contains": {
                        "type": "object",
                        "properties": {
                            identity_field: {"const": identity},
                            state_field: {
                                "properties": state_properties,
                                "required": sorted(state_required),
                            },
                        },
                        "required": [identity_field, state_field],
                    },
                    "minContains": 1,
                    "maxContains": 1,
                }
            )

        for key, fact in sorted(self.continuity_entity_state_requirements.items()):
            collection, identity_field, identity, state_field, entity_state_index = key
            collection_schema = _collection_schema(schema, collection)
            branches = collection_schema.setdefault("allOf", [])
            if not isinstance(branches, list):
                raise CorrectionResponseSchemaError(
                    f"{collection} schema has a non-list allOf"
                )
            constrained_assignment = {
                "type": "object",
                "properties": {
                    "entityType": {"const": fact.entity_type.value},
                    "entityId": {"const": fact.entity_id},
                    "state": {"enum": list(fact.allowed_states)},
                },
                "required": ["entityType", "entityId", "state"],
            }
            branches.append(
                {
                    "contains": {
                        "type": "object",
                        "properties": {
                            identity_field: {"const": identity},
                            state_field: {
                                "properties": {
                                    "entityStates": {
                                        "allOf": [
                                            {
                                                "prefixItems": [
                                                    *(
                                                        {}
                                                        for _ in range(
                                                            entity_state_index
                                                        )
                                                    ),
                                                    constrained_assignment,
                                                ],
                                                "minItems": entity_state_index + 1,
                                            }
                                        ]
                                    }
                                },
                                "required": ["entityStates"],
                            },
                        },
                        "required": [identity_field, state_field],
                    },
                    "minContains": 1,
                    "maxContains": 1,
                }
            )
