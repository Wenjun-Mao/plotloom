"""Compile typed Story Graph edge effects into target scene-entry requirements.

An ``entityStateEffects`` assignment is a post-edge fact.  It therefore owns
the first scene entry of the target node, not the source exit or later scene /
beat boundaries.  The compiler deliberately has no path-state propagation: a
target with multiple direct inputs is representable only when every input
assigns the same state for an affected entity.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

from pydantic import ConfigDict, Field, model_validator

from .canonical_schema import EntityType, StoryGraphV2
from .domain import CamelModel


EDGE_ENTRY_STATE_CONTRACT_VERSION = "edge_entity_entry_states.v1"


class _FrozenCamelModel(CamelModel):
    model_config = ConfigDict(
        alias_generator=CamelModel.model_config.get("alias_generator"),
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


class EdgeEntryEntityState(_FrozenCamelModel):
    entity_type: EntityType
    entity_id: str = Field(min_length=1)
    state: str = Field(min_length=1)
    incoming_edge_ids: tuple[str, ...] = Field(min_length=1)


class EdgeEntryStateContract(_FrozenCamelModel):
    """Hash-bound typed state requirements for first target-scene entries."""

    version: str = EDGE_ENTRY_STATE_CONTRACT_VERSION
    graph_content_hash: str = Field(min_length=64, max_length=64)
    requirements_by_target: dict[str, tuple[EdgeEntryEntityState, ...]]
    contract_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_contract_hash(self) -> "EdgeEntryStateContract":
        unsigned = self.model_dump(mode="json", by_alias=True, exclude={"contract_hash"})
        if self.contract_hash != _sha256(unsigned):
            raise ValueError("contractHash does not match the edge entry state contract")
        return self

    def requirements_for_node(self, node_id: str) -> dict[str, Any]:
        requirements = self.requirements_by_target.get(node_id, ())
        return {
            "contractVersion": self.version,
            "contractHash": self.contract_hash,
            "requiredEntityStates": [
                item.model_dump(mode="json", by_alias=True)
                for item in requirements
            ],
        }


class EdgeEntryStateIssue(_FrozenCamelModel):
    code: str = Field(min_length=1)
    path: str = Field(min_length=1)
    message: str = Field(min_length=1)


class EdgeEntryStateContractError(ValueError):
    def __init__(self, issues: list[EdgeEntryStateIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.message for issue in issues))


def compile_edge_entry_state_contract(graph: StoryGraphV2) -> EdgeEntryStateContract:
    """Compile direct-edge typed entry state, rejecting unrepresentable joins.

    Omitted effects create no requirement.  If any direct input to one target
    assigns an entity, every direct input must assign that entity identically;
    otherwise one canonical first scene entry cannot truthfully represent all
    possible arrivals.  A future path-aware state domain may support variants,
    but this compiler must not invent one.
    """

    graph_json = graph.model_dump(mode="json", by_alias=True)
    incoming_by_target: dict[str, list[Any]] = {}
    for edge in graph.edges:
        incoming_by_target.setdefault(edge.target_node_id, []).append(edge)

    issues: list[EdgeEntryStateIssue] = []
    requirements_by_target: dict[str, tuple[EdgeEntryEntityState, ...]] = {}
    for target_node_id, incoming_edges in sorted(incoming_by_target.items()):
        incoming_edges = sorted(incoming_edges, key=lambda edge: edge.id)
        effects_by_entity: dict[tuple[EntityType, str], list[tuple[str, str]]] = {}
        for edge in incoming_edges:
            for effect in edge.entity_state_effects:
                effects_by_entity.setdefault((effect.entity_type, effect.entity_id), []).append(
                    (edge.id, effect.state)
                )
        requirements: list[EdgeEntryEntityState] = []
        for (entity_type, entity_id), assignments in sorted(
            effects_by_entity.items(), key=lambda item: (item[0][0].value, item[0][1])
        ):
            assignment_edges = tuple(edge_id for edge_id, _state in assignments)
            if len(assignments) != len(incoming_edges):
                missing_edge_ids = sorted(
                    edge.id for edge in incoming_edges if edge.id not in assignment_edges
                )
                issues.append(
                    EdgeEntryStateIssue(
                        code="edge_entry_entity_state_incomplete",
                        path=f"nodes.{target_node_id}.entityStateEffects.{entity_type.value}.{entity_id}",
                        message=(
                            f"target node {target_node_id!r} receives {entity_type.value} "
                            f"{entity_id!r} from edges {', '.join(assignment_edges)}, but "
                            f"incoming edges {', '.join(missing_edge_ids)} omit it; edit every "
                            "incoming edge to assign the same state, or remove the assignment "
                            "from all incoming edges before saving or resubmitting the graph"
                        ),
                    )
                )
                continue
            states = {state for _edge_id, state in assignments}
            if len(states) != 1:
                issues.append(
                    EdgeEntryStateIssue(
                        code="edge_entry_entity_state_conflict",
                        path=f"nodes.{target_node_id}.entityStateEffects.{entity_type.value}.{entity_id}",
                        message=(
                            f"target node {target_node_id!r} receives conflicting {entity_type.value} "
                            f"{entity_id!r} states from incoming edges "
                            f"{', '.join(f'{edge_id}={state!r}' for edge_id, state in assignments)}; "
                            "edit those edges to assign one identical state, or remove the assignment "
                            "from all incoming edges before saving or resubmitting the graph"
                        ),
                    )
                )
                continue
            requirements.append(
                EdgeEntryEntityState(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    state=assignments[0][1],
                    incoming_edge_ids=assignment_edges,
                )
            )
        if requirements:
            requirements_by_target[target_node_id] = tuple(requirements)

    if issues:
        raise EdgeEntryStateContractError(issues)
    unsigned = {
        "version": EDGE_ENTRY_STATE_CONTRACT_VERSION,
        "graphContentHash": _sha256(graph_json),
        "requirementsByTarget": {
            target: [item.model_dump(mode="json", by_alias=True) for item in requirements]
            for target, requirements in requirements_by_target.items()
        },
    }
    return EdgeEntryStateContract(
        graph_content_hash=unsigned["graphContentHash"],
        requirements_by_target=deepcopy(requirements_by_target),
        contract_hash=_sha256(unsigned),
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
