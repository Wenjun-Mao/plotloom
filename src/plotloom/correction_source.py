"""Exact correction source contract and typed fact authority verification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from plotloom.generation.planning_contracts import GenerationWorkUnit

from plotloom.artifact_contracts import ArtifactKind
from plotloom.run_contracts import GenerationAttempt, GenerationAttemptKind, GenerationRun
from plotloom.stage_contracts import StageName, StagePayload
from .generation.continuity_repair import (
    assert_continuity_repair_fact_matches_source,
)
from .generation.continuity_repair_contracts import (
    ContinuityEntityStateRepairFact,
)
from .generation.contracts import (
    ExtractionPolicy,
    ValidationIssue,
)
from .generation.entity_state_repair import (
    assert_continuity_entity_state_repair_fact_matches_source,
)
from .generation.exceptions import (
    ResponseExtractionError,
)
from .generation.graph_repair_contracts import (
    JoinStateEffectRepairFact,
)
from .generation.graph_semantic_repair import (
    assert_join_state_effect_repair_fact_matches_source,
)
from .generation.repair_facts import (
    SemanticRepairFact,
    parse_semantic_repair_fact,
)
from .generation.responses import (
    extract_assistant_text,
    parse_json_text,
)
from .generation.scene_beats_dialogue_repair import (
    assert_cue_order_repair_fact_matches_source,
)
from .generation.scene_beats_edge_entry import (
    EdgeEntryEntityStateRepairFact,
    assert_edge_entry_entity_state_repair_fact_matches_source,
    edge_entry_state_requirements,
)
from .generation.semantic_repair import (
    assert_semantic_repair_fact_matches_issue,
)
from .generation.storyboard_presence_repair import (
    RequiredEntityPresenceRepairFact,
    assert_required_entity_presence_repair_fact_matches_source,
)
from .generation.storyboard_timing_repair import (
    StoryboardTimingGuidance,
    StoryboardTimingRepairPlanFact,
    build_storyboard_timing_repair_plan,
    storyboard_timing_guidance_hash,
)
from .generation.work_unit_contracts import (
    CompiledWorkUnitRequest,
)

if TYPE_CHECKING:
    from .persistence.project.repository_generation import (
        ProjectGenerationRepository as GenerationRunRepository,
    )

from dataclasses import dataclass

from .correction_execution_contracts import (
    _CORRECTION_VARIANT_CONTRACT_FIELDS,
    CorrectionSourceContractError,
)


@dataclass(frozen=True)
class CorrectionSourceEvidence:
    previous_final_content: str
    source_contract: Mapping[str, Any]
    validated_issues: tuple[ValidationIssue, ...]
    parsed_repair_facts: tuple[SemanticRepairFact, ...]


def verify_correction_source(
    repository: "GenerationRunRepository",
    *,
    run: GenerationRun,
    work_unit: GenerationWorkUnit,
    work_unit_id: str,
    base_compiled: CompiledWorkUnitRequest,
    source_attempt: GenerationAttempt,
    dependencies: Mapping[StageName, StagePayload],
    extraction_policy: ExtractionPolicy,
) -> CorrectionSourceEvidence:
    """Verify exact durable source evidence and complete stable issue/fact authority."""
    trace = repository.get_run_trace(run.id)
    response = next(
        (
            artifact
            for artifact in trace.artifacts
            if artifact.attempt_id == source_attempt.id
            and artifact.work_unit_id == work_unit_id
            and artifact.kind == ArtifactKind.RESPONSE
        ),
        None,
    )
    prompt = next(
        (
            artifact
            for artifact in trace.artifacts
            if artifact.attempt_id == source_attempt.id
            and artifact.work_unit_id == work_unit_id
            and artifact.kind == ArtifactKind.PROMPT
        ),
        None,
    )
    validation = next(
        (
            artifact
            for artifact in trace.artifacts
            if artifact.attempt_id == source_attempt.id
            and artifact.work_unit_id == work_unit_id
            and artifact.kind == ArtifactKind.VALIDATION
        ),
        None,
    )
    if prompt is None or response is None or validation is None:
        raise ValueError(
            "correction source is missing durable prompt/response/validation evidence"
        )
    response_content = response.content if isinstance(response.content, Mapping) else {}
    raw_envelope = response_content.get("rawResponse")
    if not isinstance(raw_envelope, dict):
        raise ValueError("correction source has no provider response envelope")
    # This helper only reads message.content. It deliberately ignores
    # reasoning/reasoning_content even though those fields remain in the
    # raw evidence artifact.
    try:
        previous_final_content = extract_assistant_text(raw_envelope)
    except ResponseExtractionError:
        if source_attempt.outcome_code != "response.missing_final_content":
            raise
        # There is deliberately no fallback to message.reasoning.  The
        # empty value plus stable issue is enough to request a full final
        # answer without turning hidden reasoning into application data.
        previous_final_content = ""
    validation_content = (
        validation.content if isinstance(validation.content, Mapping) else {}
    )
    source_contract = validation_content.get("contract")
    if not isinstance(source_contract, Mapping):
        raise CorrectionSourceContractError(
            "correction source has no frozen work-unit contract"
        )
    prompt_content = prompt.content if isinstance(prompt.content, Mapping) else {}
    if (
        prompt_content.get("contract") != source_contract
        or response_content.get("contract") != source_contract
    ):
        raise CorrectionSourceContractError(
            "correction source artifacts disagree on their frozen work-unit contract"
        )
    assert_correction_source_contract(
        source_attempt=source_attempt,
        source_contract=source_contract,
        base_compiled=base_compiled,
    )
    validated_issues: list[ValidationIssue] = []
    for item in validation_content.get("issues", []):
        if not isinstance(item, Mapping):
            continue
        issue = ValidationIssue.model_validate(item)
        validated_issues.append(issue)
    if not validated_issues:
        raise ValueError("correction source has no stable validation issues")
    parsed_repair_facts: list[SemanticRepairFact] = []
    raw_repair_facts = validation_content.get("repairFacts", [])
    if not isinstance(raw_repair_facts, list):
        raise ValueError("correction source has malformed deterministic repair facts")
    source_value: Any | None = None
    for item in raw_repair_facts:
        if not isinstance(item, Mapping):
            raise ValueError(
                "correction source has malformed deterministic repair facts"
            )
        fact = parse_semantic_repair_fact(item)
        assert_semantic_repair_fact_matches_issue(fact, tuple(validated_issues))
        if (
            isinstance(fact, StoryboardTimingRepairPlanFact)
            or isinstance(fact, JoinStateEffectRepairFact)
            or isinstance(fact, ContinuityEntityStateRepairFact)
            or isinstance(fact, EdgeEntryEntityStateRepairFact)
            or isinstance(fact, RequiredEntityPresenceRepairFact)
            or fact.code
            in {
                "semantic.continuity_beat_sequence_mismatch",
                "semantic.continuity_shot_sequence_mismatch",
                "semantic.cue_order",
            }
        ) and source_value is None:
            try:
                source_value = parse_json_text(
                    previous_final_content,
                    policy=extraction_policy,
                ).value
            except ResponseExtractionError as error:
                raise CorrectionSourceContractError(
                    "semantic repair source can no longer be extracted"
                ) from error
        assert_timing_fact_guidance(
            fact,
            source_contract=source_contract,
            source_value=source_value,
        )
        if fact.code in {
            "semantic.continuity_beat_sequence_mismatch",
            "semantic.continuity_shot_sequence_mismatch",
            "semantic.cue_order",
        }:
            assert source_value is not None
            try:
                if fact.code == "semantic.cue_order":
                    assert_cue_order_repair_fact_matches_source(
                        fact,
                        source_value,
                    )
                else:
                    assert_continuity_repair_fact_matches_source(
                        fact,
                        source_value,
                        stage=work_unit.stage,
                        bible=(
                            dependencies.get(StageName.STORY_BIBLE)
                            if work_unit.stage
                            in {StageName.SCENE_BEATS, StageName.STORYBOARD}
                            else None
                        ),
                        scoped_context=(
                            getattr(base_compiled.validator, "scoped_context", None)
                            if work_unit.stage
                            in {StageName.SCENE_BEATS, StageName.STORYBOARD}
                            else None
                        ),
                    )
            except ValueError as error:
                raise CorrectionSourceContractError(str(error)) from error
        if isinstance(fact, ContinuityEntityStateRepairFact):
            assert source_value is not None
            try:
                assert_continuity_entity_state_repair_fact_matches_source(
                    fact,
                    source_value,
                    stage=work_unit.stage,
                    bible=(
                        dependencies.get(StageName.STORY_BIBLE)
                        if work_unit.stage
                        in {StageName.SCENE_BEATS, StageName.STORYBOARD}
                        else None
                    ),
                )
            except ValueError as error:
                raise CorrectionSourceContractError(str(error)) from error
        if isinstance(fact, EdgeEntryEntityStateRepairFact):
            assert source_value is not None
            try:
                assert_edge_entry_entity_state_repair_fact_matches_source(
                    fact,
                    source_value,
                    requirements=edge_entry_state_requirements(
                        getattr(base_compiled.validator, "scoped_context", {})
                    ),
                )
            except ValueError as error:
                raise CorrectionSourceContractError(str(error)) from error
        if isinstance(fact, RequiredEntityPresenceRepairFact):
            assert source_value is not None
            try:
                assert_required_entity_presence_repair_fact_matches_source(
                    fact,
                    source_value,
                    issues=tuple(validated_issues),
                )
            except ValueError as error:
                raise CorrectionSourceContractError(str(error)) from error
        if isinstance(fact, JoinStateEffectRepairFact):
            assert source_value is not None
            try:
                assert_join_state_effect_repair_fact_matches_source(
                    fact,
                    source_value,
                    issues=tuple(validated_issues),
                    topology=getattr(base_compiled.validator, "topology", None),
                )
            except ValueError as error:
                raise CorrectionSourceContractError(str(error)) from error
        parsed_repair_facts.append(fact)
    return CorrectionSourceEvidence(
        previous_final_content,
        source_contract,
        tuple(validated_issues),
        tuple(parsed_repair_facts),
    )


def assert_timing_fact_guidance(
    fact: SemanticRepairFact,
    *,
    source_contract: Mapping[str, Any],
    source_value: Any | None,
) -> None:
    """Bind executable timing authority to its contract and source value.

    Artifact hashes make persisted evidence tamper-evident only when the
    semantic fact is also bound back to the source prompt contract and
    rejected response. The plan's internal hash alone cannot establish
    either provenance relationship.
    """

    timing_codes = {
        "semantic.shot_duration_budget_exceeded",
        "semantic.cue_duration_exceeds_shot",
    }
    if not isinstance(fact, StoryboardTimingRepairPlanFact):
        if fact.code in timing_codes:
            # Current source contracts may not downgrade a fully bound
            # plan into any legacy plan or witness shape by deleting its
            # binding fields. Historical evidence is still parseable for
            # terminal inspection, but old policy recovery never reaches
            # this execution boundary.
            raise CorrectionSourceContractError(
                "unbound Storyboard timing repair fact cannot authorize current correction"
            )
        return
    # ``WorkUnitPromptContract`` is a frozen trace model rather than a
    # public CamelModel, so its durable artifact shape is snake_case even
    # when callers request aliases.  Read the actual stored contract key;
    # accepting a second spelling here would weaken this exact replay
    # boundary.
    raw_guidance = source_contract.get("storyboard_timing_guidance")
    if not isinstance(raw_guidance, Mapping):
        raise CorrectionSourceContractError(
            "Storyboard timing repair fact has no frozen source guidance"
        )
    try:
        guidance = StoryboardTimingGuidance.model_validate(raw_guidance)
    except ValueError as error:
        raise CorrectionSourceContractError(
            "Storyboard timing repair fact source guidance is malformed"
        ) from error
    if storyboard_timing_guidance_hash(guidance) != fact.guidance_hash:
        raise CorrectionSourceContractError(
            "Storyboard timing repair fact does not match frozen source guidance"
        )
    if not isinstance(source_value, Mapping):
        raise CorrectionSourceContractError(
            "Storyboard timing repair fact has no structured source response"
        )
    expected_plan = build_storyboard_timing_repair_plan(
        source_value,
        guidance=guidance,
    )
    if expected_plan is None or expected_plan != fact.plan:
        raise CorrectionSourceContractError(
            "Storyboard timing repair fact does not match its rejected source response"
        )


def assert_correction_source_contract(
    *,
    source_attempt: GenerationAttempt,
    source_contract: Mapping[str, Any],
    base_compiled: CompiledWorkUnitRequest,
) -> None:
    """Bind a correction to the exact executable contract that rejected it."""

    current_contract = base_compiled.contract.snapshot_dump()
    try:
        parsed_source = type(base_compiled.contract).model_validate(
            dict(source_contract)
        )
    except ValueError as error:
        raise CorrectionSourceContractError(
            "correction source work-unit contract is malformed"
        ) from error
    if parsed_source.snapshot_dump() != dict(source_contract):
        raise CorrectionSourceContractError(
            "correction source work-unit contract changed shape during validation"
        )
    if source_attempt.attempt_kind == GenerationAttemptKind.PRIMARY:
        if dict(source_contract) != current_contract:
            raise CorrectionSourceContractError(
                "primary work-unit contract changed after the source rejection"
            )
        return

    source_base = {
        key: value
        for key, value in source_contract.items()
        if key not in _CORRECTION_VARIANT_CONTRACT_FIELDS
    }
    current_base = {
        key: value
        for key, value in current_contract.items()
        if key not in _CORRECTION_VARIANT_CONTRACT_FIELDS
    }
    if source_base != current_base:
        raise CorrectionSourceContractError(
            "base work-unit contract changed after the correction rejection"
        )
    if source_contract.get("correction_ordinal") != (source_attempt.attempt_number - 1):
        raise CorrectionSourceContractError(
            "correction source ordinal does not match its durable attempt lineage"
        )
