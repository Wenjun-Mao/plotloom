"""Versioned, static correction instructions and lossless fact projection.

The correction prompt must not carry directives for unrelated semantic domains.
This module selects only trusted, repository-owned directive text after the
runner has revalidated durable issues and typed facts.  It deliberately does
not import the fact models: the eventual work-unit integration can import this
module without creating a cycle back into ``work_units``.  Runtime callers
already parse facts there; this module additionally verifies each current
fact's stable code, path, and concrete model name.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from .contracts import FrozenModel, ValidationIssue
from .correction_contract import (
    CORRECTION_DIRECTIVE_REGISTRY_VERSION,
    CORRECTION_EVIDENCE_PROJECTION_VERSION,
    CORRECTION_ISSUE_SELECTION_VERSION,
)


class CorrectionDirectivePlanError(ValueError):
    """A persisted rejection has no current, safe correction instruction."""

    code = "contract.correction_directive_unsupported"


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


@dataclass(frozen=True)
class _DirectiveDefinition:
    id: str
    text: str
    codes: tuple[str, ...]
    required_fact_models: Mapping[str, str]


_DIRECTIVES: tuple[_DirectiveDefinition, ...] = (
    _DirectiveDefinition(
        id="topology_identity_and_fields",
        codes=(
            "binding.duplicate_id",
            "binding.unknown_id",
            "binding.missing_id",
            "semantic.missing_start_node",
            "semantic.duplicate_node_id",
            "semantic.continuation_choice_text_must_be_null",
            "semantic.choice_edge_choice_text_required",
            "semantic.join_state_key_must_be_non_blank",
            "semantic.join_state_keys_must_be_unique",
        ),
        required_fact_models={},
        text=(
            "对 topology ID/binding 问题，只使用目标 Schema 枚举的完整 ID 集，逐项删除重复或未知 ID，"
            "并补齐缺失 ID；不得改动边端点或节点类型。continuation edge 的 choiceText 必须为 null，"
            "choice edge 的 choiceText 必须为非空字符串；join 的 key 数组必须为非空、无重复字符串。"
        ),
    ),
    _DirectiveDefinition(
        id="scene_structure",
        codes=(
            "semantic.duplicate_scene_id",
            "semantic.scene_order",
            "semantic.duplicate_beat_id",
            "semantic.duplicate_cue_id",
            "semantic.cross_unit_cue",
            "semantic.scene_without_beats",
            "semantic.beat_order",
        ),
        required_fact_models={},
        text=(
            "对 Scene Beats 的局部结构问题，保持本 work unit 范围：scene、beat、cue 的 local ID 必须"
            "非空且各自唯一；每个 beat 必须引用本响应中的 scene，每个 cue 必须引用本响应中的 beat；"
            "每个 scene 至少一个 beat，并按 scene、各 scene 内 beat、各 beat 内 cue 分别从 1 连续编号。"
        ),
    ),
    _DirectiveDefinition(
        id="dialogue_cue_order",
        codes=("semantic.cue_order",),
        required_fact_models={"semantic.cue_order": "CueOrderRepairFact"},
        text=(
            "对 semantic.cue_order，只以同 code/path 的 CueOrderRepairFact 为权威："
            "保留 assignments 中每个 localCueId 和 beatLocalId，不新增、删除、重命名或改派 cue；"
            "只把 order 改为对应 expectedOrder。order 按 beatLocalId 分组独立编号，每组都从 1 开始。"
        ),
    ),
    _DirectiveDefinition(
        id="work_unit_scope",
        codes=("semantic.cross_unit_beat",),
        required_fact_models={},
        text=(
            "对 semantic.cross_unit_beat，按 path 保持当前 work unit 的封闭范围：Scene Beats 中 beat"
            " 只能引用本响应 scene 的 localSceneId；Storyboard coverage 中 beatId 只能使用目标 Schema"
            " 列出的当前场景 beat ID。不得引入相邻 unit 的 ID。"
        ),
    ),
    _DirectiveDefinition(
        id="scene_references",
        codes=(
            "semantic.unknown_cue_speaker",
            "semantic.cue_speaker_not_in_scene",
        ),
        required_fact_models={},
        text=(
            "对 Scene Beats 引用问题，只使用目标 Schema 允许的故事圣经实体 ID；去除重复 characterId。"
            "有 speakerId 的 cue 必须引用合法角色，且该角色必须同时出现在 cue 所属 scene.characterIds；"
            "不得用姓名、别名或新 ID 代替稳定 ID。"
        ),
    ),
    _DirectiveDefinition(
        id="entity_references",
        codes=(
            "semantic.unknown_location",
            "semantic.unknown_characters",
            "semantic.duplicate_character_ref",
            "semantic.unknown_props",
            "semantic.duplicate_prop_ref",
            "semantic.duplicate_required_entity_state",
            "semantic.unknown_required_entity",
        ),
        required_fact_models={},
        text=(
            "对实体引用问题，只使用目标 Schema 允许的故事圣经稳定 ID；characterIds、propIds 及同类"
            "引用去重。requiredEntityStates 的 entityType/entityId 必须对应同类型合法实体，且同一"
            "entityType/entityId 在一个镜头内只出现一次；不得以姓名、别名或新 ID 替代。"
        ),
    ),
    _DirectiveDefinition(
        id="dialogue_language",
        codes=("semantic.dialogue_language_not_authoring_language",),
        required_fact_models={},
        text=(
            "对 semantic.dialogue_language_not_authoring_language，将 path 指向的 language 完整替换为"
            "原始合同 dialogue_capacity_guidance.authoringLanguage；不得选择 wildcard 或其他语言标签。"
        ),
    ),
    _DirectiveDefinition(
        id="dialogue_node_budget",
        codes=("semantic.dialogue_exceeds_node_budget",),
        required_fact_models={
            "semantic.dialogue_exceeds_node_budget": "DialogueNodeBudgetRepairFact"
        },
        text=(
            "对 semantic.dialogue_exceeds_node_budget，只以同 code/path 的 "
            "DialogueNodeBudgetRepairFact 为权威：删除 removeLocalCueIds 中且仅其中的 cue；"
            "不要新建 cue，也不要改动保留 cue 的 text、language、delivery 或 beatLocalId。"
            "随后按 remainingCues 为每个保留 cue 写入完全相同的 order。"
        ),
    ),
    _DirectiveDefinition(
        id="fragment_capacity",
        codes=(
            "semantic.scene_capacity_exceeded",
            "schema.too_long",
            "semantic.dialogue_cue_count_exceeded",
            "semantic.dialogue_cue_capacity_exceeded",
        ),
        required_fact_models={
            "semantic.dialogue_cue_capacity_exceeded": "DialogueCapacityRepairFact"
        },
        text=(
            "对 semantic.scene_capacity_exceeded 或 schema.too_long，把 scenes 合并或删减到"
            "原始合同 dialogue_capacity_guidance.maxScenes 以内；对 "
            "semantic.dialogue_cue_count_exceeded，把 dialogueCues 精简到 "
            "maxDialogueCues 以内。对 semantic.dialogue_cue_capacity_exceeded，只以同 "
            "code/path 的 DialogueCapacityRepairFact 为权威。"
        ),
    ),
    _DirectiveDefinition(
        id="audio_timing",
        codes=("semantic.audio_timing",),
        required_fact_models={"semantic.audio_timing": "AudioTimingRepairFact"},
        text=(
            "对 semantic.audio_timing，只以同 code/path 的 AudioTimingRepairFact 为权威："
            "按原始 eventIndex 从大到小执行同一 shot 的事实；不得自行计算、改变 shot.durationUnits，"
            "或从验证器说明推断时间。"
        ),
    ),
    _DirectiveDefinition(
        id="required_entity_state",
        codes=("semantic.invalid_required_entity_state",),
        required_fact_models={
            "semantic.invalid_required_entity_state": "RequiredEntityStateRepairFact"
        },
        text=(
            "对 semantic.invalid_required_entity_state，只根据同一 code/path 的 "
            "RequiredEntityStateRepairFact 处理：保持 entityType 和 entityId 逐字不变，"
            "并把 state 改为 allowedStates 中的一个完全相同字符串。"
        ),
    ),
    _DirectiveDefinition(
        id="join_allowed_differences",
        codes=("semantic.join_allowed_differences_must_be_required",),
        required_fact_models={
            "semantic.join_allowed_differences_must_be_required": "JoinAllowedDifferencesRepairFact"
        },
        text=(
            "对 semantic.join_allowed_differences_must_be_required，只以同 code/path 的 "
            "JoinAllowedDifferencesRepairFact 为权威：完整替换 expectedRequiredStateKeys "
            "与 expectedAllowedDifferences；对 newRequiredKeyIncomingEdges 的每个 stateKey，"
            "在每条 immutable incomingEdges.edgeId 的 stateEffects 中显式写入该键。"
        ),
    ),
    _DirectiveDefinition(
        id="join_state_effect",
        codes=(
            "semantic.join_state_effect_missing",
            "semantic.join_state_effect_conflict",
        ),
        required_fact_models={
            "semantic.join_state_effect_missing": "JoinStateEffectRepairFact",
            "semantic.join_state_effect_conflict": "JoinStateEffectRepairFact",
        },
        text=(
            "对 semantic.join_state_effect_missing 或 semantic.join_state_effect_conflict，"
            "只以同 code/path 的 JoinStateEffectRepairFact 为权威：incomingEdges 是唯一可修改的"
            "直接入边集合。mode=convergent 时每条入边对 stateKey 使用逐结构完全相同的有限 JSON 值；"
            "hasExpectedValue=true 时逐结构复制 expectedValue。mode=variant 时每条入边都显式写入"
            "有限 JSON 值但可不同。"
        ),
    ),
    _DirectiveDefinition(
        id="finite_state_effect",
        codes=("semantic.state_effect_not_json",),
        required_fact_models={
            "semantic.state_effect_not_json": "EdgeStateEffectJsonRepairFact"
        },
        text=(
            "对 semantic.state_effect_not_json，只以同 code/path 的 EdgeStateEffectJsonRepairFact"
            " 为权威：只将 edgeId 的 stateKey 值替换为有限 JSON，保留原有叙事意图。"
        ),
    ),
    _DirectiveDefinition(
        id="join_reconciliation",
        codes=("semantic.join_allowed_difference_without_reconciliation",),
        required_fact_models={
            "semantic.join_allowed_difference_without_reconciliation": "JoinReconciliationRepairFact"
        },
        text=(
            "对 semantic.join_allowed_difference_without_reconciliation，只以同 code/path 的 "
            "JoinReconciliationRepairFact 为权威：只为 joinContractId 写入非空 reconciliation，"
            "明确 allowedDifferenceKeys 如何在汇流后保留或处理。"
        ),
    ),
    _DirectiveDefinition(
        id="join_entry_state",
        codes=(
            "semantic.join_entry_state_value_missing",
            "semantic.join_entry_state_value_mismatch",
            "semantic.join_entry_state_value_not_json",
        ),
        required_fact_models={
            "semantic.join_entry_state_value_missing": "JoinEntryStateValueRepairFact",
            "semantic.join_entry_state_value_mismatch": "JoinEntryStateValueRepairFact",
            "semantic.join_entry_state_value_not_json": "JoinEntryStateValueRepairFact",
        },
        text=(
            "对 join entry state value 的 missing、mismatch 或 not_json 问题，"
            "只以同 code/path 的 JoinEntryStateValueRepairFact 为权威，在 scene.entryState.facts "
            "写入 expectedValue 的完整 JSON 结构。"
        ),
    ),
    _DirectiveDefinition(
        id="continuity_values",
        codes=(
            "semantic.unknown_continuity_entity",
            "semantic.invalid_continuity_entity_state",
            "semantic.continuity_fact_not_json",
            "semantic.continuity_delta_not_json",
        ),
        required_fact_models={},
        text=(
            "对 continuity entity/state 问题按 path 使用目标 Schema 允许的故事圣经实体和状态；"
            "对 fact/delta not_json 只把该 path 的值改为有限 JSON，并保留原有叙事意图。"
        ),
    ),
    _DirectiveDefinition(
        id="continuity_sequence",
        codes=(
            "semantic.continuity_beat_sequence_mismatch",
            "semantic.continuity_shot_sequence_mismatch",
        ),
        required_fact_models={
            "semantic.continuity_beat_sequence_mismatch": "ContinuitySequenceRepairFact",
            "semantic.continuity_shot_sequence_mismatch": "ContinuitySequenceRepairFact",
        },
        text=(
            "对连续性序列问题只以同 code/path 的 ContinuitySequenceRepairFact 为权威："
            "按 boundaries 定位 response-local target，并逐项复制 assignments 的 exact value；"
            "不得修改 source、单侧声明、notes、未列字段、ID 或顺序。"
        ),
    ),
    _DirectiveDefinition(
        id="storyboard_structure_and_references",
        codes=(
            "semantic.duplicate_shot_id",
            "semantic.shot_order",
            "semantic.shot_count",
        ),
        required_fact_models={},
        text=(
            "对 Storyboard 结构与引用问题，localShotId 必须唯一，shot.order 必须从 1 连续，shots 数量"
            "必须符合目标 Schema 的 minItems/maxItems；新增或删除镜头后同步修复其 coverage 与 cue 调度，"
            "但不得改变稳定的 beat/cue ID。"
        ),
    ),
    _DirectiveDefinition(
        id="coverage",
        codes=(
            "semantic.primary_coverage",
            "semantic.unknown_link_shot",
            "semantic.duplicate_link",
            "semantic.unlinked_shots",
            "semantic.unknown_cue_ref",
            "semantic.duplicate_cue_ref",
            "semantic.unscheduled_cue_ref",
            "semantic.cue_not_covered_by_shot",
        ),
        required_fact_models={},
        text=(
            "对 coverage/cue 引用问题，从目标 Schema 重建 primaryShotLocalIdByBeat、"
            "supportingBeatLinks 与 cueIds；只能使用 Schema 允许的 IDs，且不得新增对白文本。"
        ),
    ),
    _DirectiveDefinition(
        id="storyboard_timing",
        codes=(
            "semantic.shot_duration_budget_exceeded",
            "semantic.cue_duration_exceeds_shot",
        ),
        required_fact_models={
            "semantic.shot_duration_budget_exceeded": "StoryboardTimingRepairPlanFact",
            "semantic.cue_duration_exceeds_shot": "StoryboardTimingRepairPlanFact",
        },
        text=(
            "对 semantic.shot_duration_budget_exceeded 或 semantic.cue_duration_exceeds_shot，"
            "只以 guidanceHash 与原始合同一致的 StoryboardTimingRepairPlanFact 为权威，"
            "按 plan 完整替换列出的目标字段，不得自行计算或选择另一计划。"
        ),
    ),
    _DirectiveDefinition(
        id="shot_entity_and_cue_order",
        codes=(
            "semantic.required_entity_not_in_shot",
            "semantic.cue_canonical_order",
        ),
        required_fact_models={},
        text=(
            "对 semantic.required_entity_not_in_shot，将实体加入同一 shot 的对应引用或删除不需要的"
            " requirement；对 semantic.cue_canonical_order，按 beat.order、再 cue.order 重排 cueIds。"
        ),
    ),
)

_BASE_CODES = frozenset(
    {
        "response.extraction",
        "response.missing_final_content",
        "schema.missing",
        "schema.extra_forbidden",
    }
)

_REGISTERED_CODES = tuple(
    code
    for directive in _DIRECTIVES
    for code in directive.codes
)
if len(_REGISTERED_CODES) != len(set(_REGISTERED_CODES)):
    raise RuntimeError("correction directive codes must have exactly one owner")
SUPPORTED_CORRECTION_ISSUE_CODES = frozenset(_REGISTERED_CODES)

_DIRECTIVE_BY_CODE = {
    code: directive
    for directive in _DIRECTIVES
    for code in directive.codes
}

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
        raise CorrectionDirectivePlanError("correction issues must be unique by code/path")

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
        if type(fact).__name__ != expected_model:
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
                if (
                    code in _CONTINUITY_SEQUENCE_CODES
                    and continuity_blocker_indexes
                ):
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
        for prompt_fact_index, source_fact_index in enumerate(
            executable_fact_indexes
        )
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


def _required_fact_model(code: str) -> str | None:
    directive = _DIRECTIVE_BY_CODE.get(code)
    return directive.required_fact_models.get(code) if directive is not None else None


def _is_base_issue_code(code: str) -> bool:
    """Return whether the closed response schema itself is full authority.

    Pydantic owns the suffix vocabulary for ``schema.*`` issues and may add a
    new precise code without creating a new semantic repair operation.  The
    supplied schema plus exact path is sufficient for all of them except the
    capacity case, whose repository-owned directive adds a separate frozen
    budget rule.  Semantic codes never receive this prefix allowance.
    """

    return code in _BASE_CODES or (
        code.startswith("schema.") and code not in _DIRECTIVE_BY_CODE
    )


def _serialize_current_fact(fact: Any) -> dict[str, Any]:
    if not hasattr(fact, "model_dump"):
        raise CorrectionDirectivePlanError("repair fact is not a typed current fact")
    try:
        payload = fact.model_dump(mode="json", by_alias=True, exclude_none=True)
    except (TypeError, ValueError) as exc:
        raise CorrectionDirectivePlanError("repair fact cannot be serialized") from exc
    if not isinstance(payload, dict):
        raise CorrectionDirectivePlanError("repair fact serialization must be an object")
    # ``expectedValue: null`` is meaningful only with explicit authority.
    if payload.get("hasExpectedValue") is True and hasattr(fact, "expected_value"):
        payload["expectedValue"] = deepcopy(fact.expected_value)
    if type(fact).__name__ == "ContinuitySequenceRepairFact":
        for serialized_boundary, boundary in zip(
            payload.get("boundaries", []),
            fact.boundaries,
            strict=True,
        ):
            for serialized_assignment, assignment in zip(
                serialized_boundary.get("assignments", []),
                boundary.assignments,
                strict=True,
            ):
                if type(assignment).__name__ == "ContinuityFactAssignment":
                    serialized_assignment["expectedValue"] = deepcopy(
                        assignment.expected_value
                    )
    return deepcopy(payload)


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
