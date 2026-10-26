"""Executable correction selection and lossless evidence projection."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping, Sequence

from .contracts import FrozenModel, ValidationIssue
from .correction_contract import (
    CORRECTION_DIRECTIVE_REGISTRY_VERSION,
    CORRECTION_EVIDENCE_PROJECTION_VERSION,
    CORRECTION_ISSUE_SELECTION_VERSION,
)
from .correction_registry import (
    _DIRECTIVE_BY_CODE,
    _DIRECTIVES,
    _is_base_issue_code,
    _required_fact_model,
)
from .repair_facts import SEMANTIC_REPAIR_FACT_TYPES, serialize_semantic_repair_fact

_FACT_TYPE_BY_NAME = {model.__name__: model for model in SEMANTIC_REPAIR_FACT_TYPES}


class CorrectionDirectivePlanError(ValueError):
    """A persisted rejection has no current, safe correction instruction."""

    code = "contract.correction_directive_unsupported"


class GraphEntityStateEffectCorrectionPlanError(CorrectionDirectivePlanError):
    """A graph entity-state violation must return to primary graph generation."""

    code = "contract.graph_entity_state_effect_correction_forbidden"


class CorrectionDirective(FrozenModel):
    id: str
    text: str


class CorrectionInstructionPlan(FrozenModel):
    registry_version: str
    directives: tuple[CorrectionDirective, ...]
    directive_set_hash: str
    issue_selection_version: str
    issue_selection_hash: str
    audit_issue_selection: dict[str, Any]
    executable_issue_indexes: tuple[int, ...]
    deferred_issue_indexes: tuple[int, ...]
    executable_fact_indexes: tuple[int, ...]
    evidence_projection_version: str
    evidence_projection_hash: str
    prompt_evidence: dict[str, Any]


_GRAPH_ENTITY_STATE_EFFECT_FAIL_CLOSED_CODES = frozenset(
    {
        "semantic.invalid_entity_state_effect",
        "semantic.unknown_entity_state_effect_entity",
    }
)


_CONTINUITY_SEQUENCE_CODES = frozenset(
    {
        "semantic.continuity_beat_sequence_mismatch",
        "semantic.continuity_shot_sequence_mismatch",
    }
)


_CONTINUITY_SEQUENCE_BLOCKER_CODES = frozenset(
    {
        "semantic.unknown_continuity_entity",
        "semantic.invalid_continuity_entity_state",
        "semantic.continuity_fact_not_json",
    }
)


_CONTINUITY_DEFERRAL_REASON = "authority.sequence_fact_blocked_by_invalid_state"


_CUE_ORDER_CODE = "semantic.cue_order"


_CUE_ORDER_BLOCKER_CODES = frozenset(
    {
        "semantic.duplicate_beat_id",
        "semantic.cross_unit_beat",
        "semantic.duplicate_cue_id",
        "semantic.cross_unit_cue",
        "semantic.dialogue_cue_count_exceeded",
        "semantic.dialogue_exceeds_node_budget",
        "semantic.scene_capacity_exceeded",
    }
)


_CUE_ORDER_DEFERRAL_REASON = "authority.cue_order_blocked_by_mutable_membership"


def compile_correction_instruction_plan(
    issues: Sequence[ValidationIssue],
    facts: Sequence[Any],
) -> CorrectionInstructionPlan:
    """Select trusted directives and make a lossless, compact prompt view.

    ``facts`` remain the caller's immutable validation evidence.  This function
    returns a new prompt projection only; it never mutates facts or issues.
    """

    issue_keys = tuple((issue.code, tuple(issue.path)) for issue in issues)
    if not issue_keys:
        raise CorrectionDirectivePlanError("correction requires at least one issue")
    if len(issue_keys) != len(set(issue_keys)):
        raise CorrectionDirectivePlanError(
            "correction issues must be unique by code/path"
        )

    fact_payloads: list[dict[str, Any]] = []
    facts_by_issue: dict[tuple[str, tuple[str | int, ...]], list[int]] = {}
    for index, fact in enumerate(facts):
        payload = _serialize_current_fact(fact)
        code = payload.get("code")
        path = payload.get("path")
        if not isinstance(code, str) or not isinstance(path, list):
            raise CorrectionDirectivePlanError("current repair fact has no code/path")
        key = (code, tuple(path))
        if key not in issue_keys:
            raise CorrectionDirectivePlanError(
                "current repair fact has no matching stable validation issue"
            )
        expected_model = _required_fact_model(code)
        if expected_model is None:
            raise CorrectionDirectivePlanError(
                f"repair fact code is not supported by the directive registry: {code}"
            )
        if type(fact) is not _FACT_TYPE_BY_NAME.get(expected_model):
            raise CorrectionDirectivePlanError(
                f"repair fact for {code} is not the current {expected_model}"
            )
        fact_payloads.append(payload)
        facts_by_issue.setdefault(key, []).append(index)

    issue_index_by_key = {key: index for index, key in enumerate(issue_keys)}
    active_directives: set[str] = set()
    executable_issue_indexes: list[int] = []
    deferred_issue_indexes: list[int] = []
    executable_fact_indexes: list[int] = []
    deferred_issues: list[dict[str, Any]] = []
    # Continuity blocker matching is intentionally rejection-wide. The
    # deterministic fact compiler emits an exact fact whenever a mismatched
    # sequence is safe; a blocker can therefore only make this selector more
    # conservative, never authorize an unrelated repair.
    continuity_blocker_indexes = [
        index
        for index, issue in enumerate(issues)
        if issue.code in _CONTINUITY_SEQUENCE_BLOCKER_CODES
    ]
    cue_order_blocker_indexes = [
        index
        for index, issue in enumerate(issues)
        if issue.code in _CUE_ORDER_BLOCKER_CODES
    ]
    for issue_index, (code, path) in enumerate(issue_keys):
        if _is_base_issue_code(code):
            executable_issue_indexes.append(issue_index)
            continue
        if code in _GRAPH_ENTITY_STATE_EFFECT_FAIL_CLOSED_CODES:
            raise GraphEntityStateEffectCorrectionPlanError(
                "graph entity-state effect violations require a new Story Graph "
                "generation; correction has no authority to select a Bible state "
                "or replace an entity identity"
            )
        directive = _DIRECTIVE_BY_CODE.get(code)
        if directive is None:
            raise CorrectionDirectivePlanError(
                f"unsupported correction issue code: {code}"
            )
        expected_model = directive.required_fact_models.get(code)
        if expected_model is not None:
            matching_indexes = facts_by_issue.get((code, path), [])
            if len(matching_indexes) > 1:
                raise CorrectionDirectivePlanError(
                    f"correction issue {code} has duplicate {expected_model} authority"
                )
            if code == _CUE_ORDER_CODE and cue_order_blocker_indexes:
                if matching_indexes:
                    raise CorrectionDirectivePlanError(
                        "cue-order authority must be deferred while cue membership is mutable"
                    )
                deferred_issue_indexes.append(issue_index)
                deferred_issues.append(
                    {
                        "code": code,
                        "path": list(path),
                        "reasonCode": _CUE_ORDER_DEFERRAL_REASON,
                        "blockingIssues": [
                            {
                                "code": issues[index].code,
                                "path": list(issues[index].path),
                            }
                            for index in cue_order_blocker_indexes
                        ],
                    }
                )
                continue
            if not matching_indexes:
                if code in _CONTINUITY_SEQUENCE_CODES and continuity_blocker_indexes:
                    deferred_issue_indexes.append(issue_index)
                    deferred_issues.append(
                        {
                            "code": code,
                            "path": list(path),
                            "reasonCode": _CONTINUITY_DEFERRAL_REASON,
                            "blockingIssues": [
                                {
                                    "code": issues[index].code,
                                    "path": list(issues[index].path),
                                }
                                for index in continuity_blocker_indexes
                            ],
                        }
                    )
                    continue
                raise CorrectionDirectivePlanError(
                    f"correction issue {code} requires a matching {expected_model}"
                )
            executable_fact_indexes.extend(matching_indexes)
        executable_issue_indexes.append(issue_index)
        active_directives.add(directive.id)

    if not executable_issue_indexes:
        raise CorrectionDirectivePlanError(
            "correction has no issue with sufficient executable authority"
        )

    if set(executable_fact_indexes) != set(range(len(facts))):
        raise CorrectionDirectivePlanError(
            "correction contains repair facts outside its executable issue selection"
        )

    fact_bindings = [
        {
            "factIndex": fact_index,
            "issueIndex": issue_index_by_key[
                (
                    str(fact_payloads[fact_index]["code"]),
                    tuple(fact_payloads[fact_index]["path"]),
                )
            ],
            "code": fact_payloads[fact_index]["code"],
            "path": deepcopy(fact_payloads[fact_index]["path"]),
            "model": type(facts[fact_index]).__name__,
        }
        for fact_index in executable_fact_indexes
    ]
    executable_issues = [
        {
            "code": issues[index].code,
            "path": list(issues[index].path),
        }
        for index in executable_issue_indexes
    ]
    issue_selection = {
        "version": CORRECTION_ISSUE_SELECTION_VERSION,
        "allIssues": [
            {"code": issue.code, "path": list(issue.path)} for issue in issues
        ],
        "executableIssues": executable_issues,
        "deferredIssues": deferred_issues,
        "factBindings": fact_bindings,
    }

    # Deferred identities and blocker details are audit evidence, not model
    # authority. Rebase the visible bindings to the executable-only issue list
    # so every prompt index resolves inside the projection the model receives.
    prompt_issue_index_by_key = {
        issue_keys[source_index]: prompt_index
        for prompt_index, source_index in enumerate(executable_issue_indexes)
    }
    prompt_fact_bindings = [
        {
            "factIndex": prompt_fact_index,
            "issueIndex": prompt_issue_index_by_key[
                (
                    str(fact_payloads[source_fact_index]["code"]),
                    tuple(fact_payloads[source_fact_index]["path"]),
                )
            ],
            "code": fact_payloads[source_fact_index]["code"],
            "path": deepcopy(fact_payloads[source_fact_index]["path"]),
            "model": type(facts[source_fact_index]).__name__,
        }
        for prompt_fact_index, source_fact_index in enumerate(executable_fact_indexes)
    ]
    prompt_issue_selection = {
        "version": CORRECTION_ISSUE_SELECTION_VERSION,
        "executableIssues": deepcopy(executable_issues),
        "factBindings": prompt_fact_bindings,
    }

    directives = tuple(
        CorrectionDirective(id=item.id, text=item.text)
        for item in _DIRECTIVES
        if item.id in active_directives
    )
    executable_fact_payloads = [
        fact_payloads[index] for index in executable_fact_indexes
    ]
    prompt_evidence = _project_prompt_evidence(
        executable_fact_payloads,
        issue_selection=prompt_issue_selection,
    )
    directive_set_hash = _sha256(
        {
            "registryVersion": CORRECTION_DIRECTIVE_REGISTRY_VERSION,
            "directives": [item.model_dump(mode="json") for item in directives],
        }
    )
    return CorrectionInstructionPlan(
        registry_version=CORRECTION_DIRECTIVE_REGISTRY_VERSION,
        directives=directives,
        directive_set_hash=directive_set_hash,
        issue_selection_version=CORRECTION_ISSUE_SELECTION_VERSION,
        issue_selection_hash=_sha256(issue_selection),
        audit_issue_selection=deepcopy(issue_selection),
        executable_issue_indexes=tuple(executable_issue_indexes),
        deferred_issue_indexes=tuple(deferred_issue_indexes),
        executable_fact_indexes=tuple(executable_fact_indexes),
        evidence_projection_version=CORRECTION_EVIDENCE_PROJECTION_VERSION,
        evidence_projection_hash=_sha256(prompt_evidence),
        prompt_evidence=prompt_evidence,
    )


def _serialize_current_fact(fact: Any) -> dict[str, Any]:
    if type(fact) not in SEMANTIC_REPAIR_FACT_TYPES:
        raise CorrectionDirectivePlanError("repair fact is not a typed current fact")
    try:
        return deepcopy(serialize_semantic_repair_fact(fact))
    except (TypeError, ValueError) as exc:
        raise CorrectionDirectivePlanError("repair fact cannot be serialized") from exc


def _project_prompt_evidence(
    facts: Sequence[dict[str, Any]],
    *,
    issue_selection: Mapping[str, Any],
) -> dict[str, Any]:
    grouped_indexes: set[int] = set()
    groups_by_key: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, fact in enumerate(facts):
        if fact.get("code") not in {
            "semantic.join_state_effect_missing",
            "semantic.join_state_effect_conflict",
        }:
            continue
        operational = {
            key: deepcopy(fact[key])
            for key in (
                "code",
                "joinContractId",
                "joinNodeId",
                "stateKey",
                "mode",
                "incomingEdges",
                "repairAction",
                "hasExpectedValue",
                "preservedStateEffects",
            )
            if key in fact
        }
        if "expectedValue" in fact:
            operational["expectedValue"] = deepcopy(fact["expectedValue"])
        groups_by_key.setdefault(_canonical_json(operational), []).append((index, fact))

    join_groups: list[dict[str, Any]] = []
    for members in groups_by_key.values():
        if len(members) < 2:
            continue
        first_index, first = members[0]
        grouped_indexes.update(index for index, _ in members)
        group = {
            key: deepcopy(first[key])
            for key in (
                "code",
                "joinContractId",
                "joinNodeId",
                "stateKey",
                "mode",
                "incomingEdges",
                "repairAction",
                "hasExpectedValue",
                "preservedStateEffects",
            )
            if key in first
        }
        if "expectedValue" in first:
            group["expectedValue"] = deepcopy(first["expectedValue"])
        group["sourceFactIndexes"] = [index for index, _ in members]
        group["issuePaths"] = sorted(
            (deepcopy(item["path"]) for _, item in members),
            key=_canonical_json,
        )
        join_groups.append((first_index, group))

    join_groups.sort(key=lambda item: item[0])
    return {
        "version": CORRECTION_EVIDENCE_PROJECTION_VERSION,
        "issueSelection": deepcopy(dict(issue_selection)),
        "facts": [
            deepcopy(fact)
            for index, fact in enumerate(facts)
            if index not in grouped_indexes
        ],
        "joinStateEffectGroups": [group for _, group in join_groups],
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
