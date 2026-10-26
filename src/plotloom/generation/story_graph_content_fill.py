"""Trusted content-fill binding and ordered source diagnostics."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..canonical_schema import (
    JoinContractV2,
    StoryBibleV2,
    StoryEdgeV2,
    StoryGraphV2,
    StoryNodeV2,
    V2StoryEdgeKind,
)
from ..domain import ProjectBrief
from ..join_state_values import (
    JoinStateValueContractError,
    compile_join_state_value_contract,
)
from ..validation import DomainValidationError, validate_story_graph
from .story_graph_content_contracts import StoryGraphContentFill
from .story_graph_topology_contracts import StoryGraphTopology


class StoryGraphContentBindingError(ValueError):
    """A content fill attempted to omit, duplicate, or alter trusted IDs."""

    def __init__(self, issues: list[dict[str, str]]) -> None:
        self.issues = issues
        super().__init__("; ".join(issue["message"] for issue in issues))


def bind_story_graph_content_fill(
    topology: StoryGraphTopology,
    content: StoryGraphContentFill | dict[str, Any],
    *,
    brief: ProjectBrief,
    bible: StoryBibleV2 | None = None,
) -> StoryGraphV2:
    """Bind model prose to immutable topology and rerun the full domain validator."""

    try:
        fill = (
            content
            if isinstance(content, StoryGraphContentFill)
            else StoryGraphContentFill.model_validate(content, by_alias=True)
        )
    except ValidationError as exc:
        raise StoryGraphContentBindingError(
            [
                {
                    "code": f"schema.{error['type']}",
                    "path": _path(error.get("loc") or ()),
                    "message": error["msg"],
                }
                for error in exc.errors(include_url=False, include_context=False)
            ]
        ) from exc
    _assert_exact_ids(
        "nodes", [item.id for item in fill.nodes], [item.id for item in topology.nodes]
    )
    _assert_exact_ids(
        "edges", [item.id for item in fill.edges], [item.id for item in topology.edges]
    )
    _assert_exact_ids(
        "joinContracts",
        [item.id for item in fill.join_contracts],
        [item.id for item in topology.joins],
    )
    _assert_v2_content_contract(topology, fill)
    try:
        graph = _bound_story_graph_from_content_fill(topology, fill)
        validate_story_graph(graph, brief, bible=bible)
    except ValidationError as exc:
        raise StoryGraphContentBindingError(
            [
                {
                    "code": f"semantic.{error['type']}",
                    "path": _path(error.get("loc") or ()),
                    "message": error["msg"],
                }
                for error in exc.errors(include_url=False, include_context=False)
            ]
        ) from exc
    except DomainValidationError as exc:
        raise StoryGraphContentBindingError(
            [
                {
                    "code": f"semantic.{issue['code']}",
                    "path": issue["path"],
                    "message": issue["message"],
                }
                for issue in exc.issues
            ]
        ) from exc

    return graph


def story_graph_content_fill_join_diagnostic_issues(
    topology: StoryGraphTopology,
    content: StoryGraphContentFill,
) -> list[dict[str, str]]:
    """Expose independent join defects hidden by an allowed-key subset error.

    A response with an allowed-only key cannot construct the canonical V2 join
    contract, so normal binding correctly stops before the join-value compiler.
    For correction evidence only, this helper creates an in-memory diagnostic
    view whose required keys are the ordered union of required and allowed
    keys.  It never accepts, persists, or rewrites the model response.  The
    shared join-state compiler remains the authority for missing values,
    conflicts, finite JSON, and reconciliation semantics.
    """

    _assert_exact_ids(
        "nodes",
        [item.id for item in content.nodes],
        [item.id for item in topology.nodes],
    )
    _assert_exact_ids(
        "edges",
        [item.id for item in content.edges],
        [item.id for item in topology.edges],
    )
    _assert_exact_ids(
        "joinContracts",
        [item.id for item in content.join_contracts],
        [item.id for item in topology.joins],
    )

    try:
        diagnostic_graph = _bound_story_graph_from_content_fill(
            topology,
            content,
            include_allowed_in_required=True,
        )
        # Keep native values (not ``mode='json'``) so NaN/Infinity remain
        # visible to finite_canonical_json instead of being silently coerced.
        compile_join_state_value_contract(diagnostic_graph)
    except JoinStateValueContractError as exc:
        diagnostic_issues = list(exc.issues)
    except ValidationError:
        # Blank/duplicate keys and other malformed join arrays do not grant
        # extra repair authority.  Normal binding reports those defects.
        return []
    else:
        return []

    promoted_by_join = {
        join.id: set(join.allowed_differences) - set(join.required_state_keys)
        for join in content.join_contracts
    }
    joins_by_incoming_edge = {
        edge.id: join.id
        for join in topology.joins
        for edge in topology.edges
        if edge.target_node_id == join.join_node_id
        and edge.source_node_id in set(join.incoming_node_ids)
    }
    retained: list[dict[str, str]] = []
    for issue in diagnostic_issues:
        if issue.code == "join_state_effect_missing":
            parts = issue.path.split(".")
            if len(parts) == 4 and parts[0] == "edges":
                join_id = joins_by_incoming_edge.get(parts[1])
                if join_id is not None and parts[3] in promoted_by_join[join_id]:
                    # The subset repair fact already authorizes writing every
                    # promoted allowed key to each immutable incoming edge.
                    continue
        retained.append(
            {
                "code": f"semantic.{issue.code}",
                "path": issue.path,
                "message": issue.message,
            }
        )
    return retained


def _bound_story_graph_from_content_fill(
    topology: StoryGraphTopology,
    fill: StoryGraphContentFill,
    *,
    include_allowed_in_required: bool = False,
) -> StoryGraphV2:
    """Bind frozen topology to content, optionally normalizing join diagnostics."""

    node_fill = {item.id: item for item in fill.nodes}
    edge_fill = {item.id: item for item in fill.edges}
    join_fill = {item.id: item for item in fill.join_contracts}
    return StoryGraphV2(
        start_node_id=topology.start_node_id,
        nodes=[
            StoryNodeV2(
                id=item.id,
                kind=item.kind,
                title=node_fill[item.id].title,
                summary=node_fill[item.id].summary,
                footage_mode=item.footage_mode,
            )
            for item in topology.nodes
        ],
        edges=[
            StoryEdgeV2(
                id=item.id,
                source_node_id=item.source_node_id,
                target_node_id=item.target_node_id,
                kind=item.kind,
                choice_text=edge_fill[item.id].choice_text,
                state_effects=edge_fill[item.id].state_effects,
                entity_state_effects=edge_fill[item.id].entity_state_effects,
            )
            for item in topology.edges
        ],
        join_contracts=[
            JoinContractV2(
                id=item.id,
                join_node_id=item.join_node_id,
                incoming_node_ids=list(item.incoming_node_ids),
                required_state_keys=(
                    list(
                        dict.fromkeys(
                            (
                                *join_fill[item.id].required_state_keys,
                                *join_fill[item.id].allowed_differences,
                            )
                        )
                    )
                    if include_allowed_in_required
                    else join_fill[item.id].required_state_keys
                ),
                allowed_differences=join_fill[item.id].allowed_differences,
                reconciliation=join_fill[item.id].reconciliation,
                notes=join_fill[item.id].notes,
            )
            for item in topology.joins
        ],
    )


def _assert_v2_content_contract(
    topology: StoryGraphTopology, fill: StoryGraphContentFill
) -> None:
    """Reject all model-controlled values that V2 would reject after binding.

    Classify invalid model values as stable, repairable validation issues
    before constructing the current canonical model.
    """

    edge_by_id = {edge.id: edge for edge in topology.edges}
    issues: list[dict[str, str]] = []
    for edge in fill.edges:
        topology_edge = edge_by_id[edge.id]
        path = f"edges.{edge.id}.choiceText"
        if (
            topology_edge.kind == V2StoryEdgeKind.CONTINUATION
            and edge.choice_text is not None
        ):
            issues.append(
                {
                    "code": "semantic.continuation_choice_text_must_be_null",
                    "path": path,
                    "message": "continuation edges must set choiceText to null",
                }
            )
        elif topology_edge.kind == V2StoryEdgeKind.CHOICE and (
            edge.choice_text is None or not edge.choice_text.strip()
        ):
            issues.append(
                {
                    "code": "semantic.choice_edge_choice_text_required",
                    "path": path,
                    "message": "choice edges require a non-blank choiceText",
                }
            )

    for join in fill.join_contracts:
        required_keys = join.required_state_keys
        allowed_differences = join.allowed_differences
        for field_name, values in (
            ("requiredStateKeys", required_keys),
            ("allowedDifferences", allowed_differences),
        ):
            path = f"joinContracts.{join.id}.{field_name}"
            if any(not value.strip() for value in values):
                issues.append(
                    {
                        "code": "semantic.join_state_key_must_be_non_blank",
                        "path": path,
                        "message": f"{field_name} entries must be non-blank",
                    }
                )
            if len(values) != len(set(values)):
                issues.append(
                    {
                        "code": "semantic.join_state_keys_must_be_unique",
                        "path": path,
                        "message": f"{field_name} entries must be unique",
                    }
                )
        if not set(allowed_differences) <= set(required_keys):
            issues.append(
                {
                    "code": "semantic.join_allowed_differences_must_be_required",
                    "path": f"joinContracts.{join.id}.allowedDifferences",
                    "message": "allowedDifferences must be contained in requiredStateKeys",
                }
            )
    if issues:
        raise StoryGraphContentBindingError(issues)


def _assert_exact_ids(label: str, actual: list[str], expected: list[str]) -> None:
    duplicate = sorted({item for item in actual if actual.count(item) > 1})
    unknown = sorted(set(actual) - set(expected))
    missing = sorted(set(expected) - set(actual))
    issues: list[dict[str, str]] = []
    if duplicate:
        issues.append(
            {
                "code": "binding.duplicate_id",
                "path": label,
                "message": f"duplicate {label} IDs: {', '.join(duplicate)}",
            }
        )
    if unknown:
        issues.append(
            {
                "code": "binding.unknown_id",
                "path": label,
                "message": f"unknown {label} IDs: {', '.join(unknown)}",
            }
        )
    if missing:
        issues.append(
            {
                "code": "binding.missing_id",
                "path": label,
                "message": f"missing {label} IDs: {', '.join(missing)}",
            }
        )
    if issues:
        raise StoryGraphContentBindingError(issues)


def _path(parts: Any) -> str:
    return ".".join(str(part) for part in parts)
