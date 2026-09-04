"""Durable application runner for immutable generation work units.

Pure planning and fragment validation live under :mod:`plotloom.generation`.
This module owns the application boundary where repository allocated IDs,
provider calls, and durable artifacts meet.  Keeping it separate from the
legacy repair bridge prevents either execution model from weakening the other.
"""

from __future__ import annotations

import re
from threading import Event
from typing import Any, Mapping, Protocol

from .domain import (
    Artifact,
    ArtifactKind,
    AttemptStatus,
    GenerationAttempt,
    GenerationAttemptKind,
    GenerationRun,
    ProjectBrief,
    ProviderAuthMode,
    ProviderSnapshot,
    RunStatus,
    StageName,
    StagePayloadV2,
    WorkUnitRepairScope,
    WorkUnitFailureDisposition,
    stage_payload_model,
)
from .exceptions import QuarantinedOutputError, RunExecutionError
from .generation.contracts import (
    ExtractionPolicy,
    GenerationRequest,
    ProviderResponse,
    ProviderUsage,
    ReasoningMode,
    RequestExtension,
    ValidationIssue,
)
from .generation.correction_directives import (
    CorrectionDirectivePlanError,
    compile_correction_instruction_plan,
)
from .generation.correction_schema import (
    CorrectionResponseSchemaError,
    compile_correction_response_schema,
)
from .generation.exceptions import (
    ProviderCapabilityError,
    ProviderError,
    ProviderOutcomeUnknownError,
    ProviderRequestNotSentError,
    ProviderResponseError,
    ResponseExtractionError,
)
from .generation.fragments import StoryBibleFragment, StoryGraphFragment
from .generation.planning import GenerationWorkUnit, StagePlan
from .generation.prompts import PromptRenderer
from .generation.providers import ProviderAdapter
from .generation.responses import (
    extract_assistant_text,
    parse_json_text,
    redact_provider_boundary_evidence,
)
from .generation.secrets import SecretLease
from .generation.validation import SemanticValidationContext
from .generation.work_units import (
    AUDIO_EVENT_ID_BINDING_VERSION,
    FRAGMENT_ID_BINDING_VERSION,
    CompiledWorkUnitRequest,
    SemanticRepairFact,
    StoryboardTimingRepairPlanFact,
    WorkUnitContractError,
    compile_work_unit_request,
    parse_semantic_repair_fact,
    assert_continuity_repair_fact_matches_source,
    assert_semantic_repair_fact_matches_issue,
    semantic_repair_facts,
    serialize_semantic_repair_fact,
)
from .generation.storyboard_timing_repair import (
    StoryboardTimingGuidance,
    storyboard_timing_guidance_hash,
)
from .persistence import SQLiteRepository, stable_hash
from .provider_profiles import TextProviderProfileSnapshot
from .generation.story_graph_topology import StoryGraphTopology
from .runtime import RunExecutionResult


class RunSecretLeaser(Protocol):
    def lease_for_run(
        self,
        run_id: str,
        *,
        auth_mode: ProviderAuthMode,
        profile_id: str = "default",
    ) -> SecretLease | None: ...

    def release_run(self, run_id: str) -> None: ...


class CorrectionPromptBudgetError(ValueError):
    """A correction packet cannot fit the work unit's frozen byte budget."""

    code = "contract.correction_input_budget_exceeded"


class CorrectionSourceContractError(ValueError):
    """A rejected attempt cannot be corrected under changed executable rules."""

    code = "contract.correction_source_changed"


_CORRECTION_VARIANT_CONTRACT_FIELDS = frozenset(
    {
        "prompt_id",
        "prompt_version",
        "prompt_spec_hash",
        "variables_hash",
        "rendered_hash",
        "correction_ordinal",
        "correction_strategy",
        "correction_directive_set_hash",
        "correction_evidence_projection_hash",
        "correction_response_schema_hash",
    }
)


class DurableWorkUnitRunner:
    """Execute one non-repair run as artifacts, candidate fragments, and seals."""

    def __init__(
        self,
        repository: SQLiteRepository,
        secrets: RunSecretLeaser,
        renderer: PromptRenderer,
    ) -> None:
        self.repository = repository
        self.secrets = secrets
        self.renderer = renderer

    def execute(
        self,
        run: GenerationRun,
        *,
        adapter: ProviderAdapter,
        model: str,
        profile: ProviderSnapshot | TextProviderProfileSnapshot,
        cancellation: Event,
        repair_scope: WorkUnitRepairScope | None = None,
    ) -> RunExecutionResult:
        """Run exact units, returning only repository-owned aggregate IDs."""

        generation_plan = self.repository.get_generation_plan(run.id)
        story_graph_topology = self.repository.get_story_graph_topology(run.id)
        brief = run.canonical_snapshot.brief
        sealed_payloads: dict[StageName, StagePayloadV2] = {}
        sealed_ids: list[str] = []
        try:
            for stage in run.requested_stages:
                if self._cancelled(run.id, cancellation):
                    return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
                existing = self._sealed_stage(run.id, stage)
                if existing is not None:
                    sealed_payloads[stage] = stage_payload_model(stage, schema_version=2).model_validate(
                        existing.payload
                    )
                    sealed_ids.append(existing.id)
                    continue

                dependencies = self._stage_dependencies(
                    run,
                    stage,
                    sealed_payloads,
                    repair_scope=repair_scope,
                )
                # Repository planning treats these as assertions against its
                # frozen snapshot/seals, never as caller-provided authority.
                stage_plan = self._get_stage_plan(
                    run,
                    stage,
                    dependencies=dependencies,
                    repair_scope=repair_scope,
                )
                candidates = self._existing_unit_candidates(run.id, stage, stage_plan)
                if repair_scope is not None:
                    candidates.update(
                        self._materialize_reused_unit_candidates(
                            run.id,
                            stage,
                            stage_plan,
                        )
                    )
                    if stage == repair_scope.stage:
                        # The scope authorizes at most one provider-bound unit
                        # in its repaired stage.  Zero is valid after a crash
                        # that happened after the target candidate committed
                        # but before aggregation; more than one would quietly
                        # turn a precise repair into a partial rebuild.
                        unresolved = [
                            unit.unit_id
                            for unit in stage_plan.work_units
                            if unit.unit_id not in candidates
                        ]
                        if len(unresolved) > 1:
                            raise ValueError(
                                "exact repair scope leaves more than one target-stage work unit unresolved"
                            )
                for work_unit in stage_plan.work_units:
                    if work_unit.unit_id in candidates:
                        continue
                    if self._cancelled(run.id, cancellation):
                        return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
                    try:
                        candidate_id = self._execute_work_unit(
                            run=run,
                            generation_plan=generation_plan,
                            stage_plan=stage_plan,
                            work_unit_id=work_unit.unit_id,
                            dependencies=dependencies,
                            brief=brief,
                            adapter=adapter,
                            model=model,
                            profile=profile,
                            story_graph_topology=story_graph_topology,
                            cancellation=cancellation,
                        )
                    except QuarantinedOutputError:
                        raise
                    except Exception as error:
                        if isinstance(error, WorkUnitContractError):
                            # This is a frozen-contract impossibility detected
                            # before a prompt or provider call exists.  Do not
                            # allocate/replay a correction attempt merely to
                            # make the durable code visible to the run owner.
                            raise RunExecutionError(
                                code=error.code,
                                stage=work_unit.stage,
                            ) from error
                        attempts = [
                            attempt
                            for attempt in self.repository.get_run_trace(run.id).attempts
                            if attempt.work_unit_id == work_unit.unit_id
                            and attempt.status == AttemptStatus.FAILED
                            and attempt.outcome_code
                        ]
                        if attempts:
                            latest = max(
                                attempts,
                                key=lambda attempt: attempt.attempt_number,
                            )
                            raise RunExecutionError(
                                code=str(latest.outcome_code),
                                stage=work_unit.stage,
                            ) from error
                        raise
                    if candidate_id is None:
                        return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
                    candidates[work_unit.unit_id] = candidate_id

                if self._cancelled(run.id, cancellation):
                    return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
                candidate_artifact_ids = [
                    candidates[unit.unit_id] for unit in stage_plan.work_units
                ]
                if repair_scope is not None:
                    aggregate = self.repository.seal_repair_stage_aggregate(
                        run.id,
                        stage,
                        candidate_artifact_ids=candidate_artifact_ids,
                    )
                else:
                    aggregate = self.repository.seal_stage_aggregate(
                        run.id,
                        stage,
                        candidate_artifact_ids=candidate_artifact_ids,
                    )
                sealed_payloads[stage] = stage_payload_model(stage, schema_version=2).model_validate(
                    aggregate.payload
                )
                sealed_ids.append(aggregate.id)
            return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
        finally:
            self.secrets.release_run(run.id)

    def execute_exact_repair(
        self,
        run: GenerationRun,
        *,
        repair_scope: WorkUnitRepairScope,
        adapter: ProviderAdapter,
        model: str,
        profile: ProviderSnapshot | TextProviderProfileSnapshot,
        cancellation: Event,
    ) -> RunExecutionResult:
        """Execute a scope-frozen child repair without touching parent evidence.

        The repository owns the delicate boundary: it resolves scope-bound
        upstream inputs, creates child-local reuse evidence, and verifies that
        only the targeted unit remains executable.  This runner deliberately
        retains the normal attempt/correction code path for that target and
        for newly planned downstream work.
        """

        if run.id != repair_scope.child_run_id:
            raise ValueError("exact repair scope is bound to a different child run")
        if run.parent_run_id != repair_scope.parent_run_id:
            raise ValueError("exact repair scope parent does not match child lineage")
        return self.execute(
            run,
            adapter=adapter,
            model=model,
            profile=profile,
            cancellation=cancellation,
            repair_scope=repair_scope,
        )

    def _execute_work_unit(
        self,
        *,
        run: GenerationRun,
        generation_plan: Any,
        stage_plan: StagePlan,
        work_unit_id: str,
        dependencies: Mapping[StageName, StagePayloadV2],
        brief: ProjectBrief,
        adapter: ProviderAdapter,
        model: str,
        profile: ProviderSnapshot | TextProviderProfileSnapshot,
        story_graph_topology: StoryGraphTopology | None,
        cancellation: Event,
    ) -> str | None:
        work_unit = next(unit for unit in stage_plan.work_units if unit.unit_id == work_unit_id)
        base_compiled = compile_work_unit_request(
            generation_plan=generation_plan,
            stage_plan=stage_plan,
            work_unit=work_unit,
            dependencies=dependencies,
            brief=brief,
            canonical_snapshot=run.canonical_snapshot,
            instructions=run.instructions or "",
            stage_constraints=self._stage_constraints(work_unit.stage, brief, run.instructions),
            story_graph_topology=(
                story_graph_topology
                if work_unit.stage == StageName.STORY_GRAPH
                else None
            ),
            renderer=self.renderer,
        )
        if work_unit.stage == StageName.STORY_GRAPH and story_graph_topology is None:
            raise ValueError("new Story Graph work units require a frozen topology")

        if isinstance(profile, TextProviderProfileSnapshot):
            request_extension, reasoning_mode, extraction_policy = profile.request_contract()
            max_corrections = profile.max_semantic_corrections
        else:
            request_extension = RequestExtension.NONE
            reasoning_mode = ReasoningMode.PROVIDER_DEFAULT
            extraction_policy = ExtractionPolicy()
            max_corrections = 0
        max_attempts = 1 + max_corrections

        while True:
            trace = self.repository.get_run_trace(run.id)
            prior_attempts = sorted(
                (
                    item
                    for item in trace.attempts
                    if item.work_unit_id == work_unit_id
                ),
                key=lambda item: item.attempt_number,
            )
            recoverable_attempt = self.repository.get_recoverable_attempt_for_work_unit(
                work_unit_id
            )
            if recoverable_attempt is not None:
                attempt = recoverable_attempt
                if attempt.attempt_number > max_attempts:
                    raise ValueError(
                        "recoverable work-unit attempt exceeds the frozen correction limit"
                    )
                source_attempt = (
                    next(
                        (
                            item
                            for item in prior_attempts
                            if item.id == attempt.source_attempt_id
                        ),
                        None,
                    )
                    if attempt.attempt_kind == GenerationAttemptKind.CORRECTION
                    else None
                )
                if (
                    attempt.attempt_kind == GenerationAttemptKind.CORRECTION
                    and source_attempt is None
                ):
                    raise ValueError(
                        "recoverable correction attempt is missing its durable source attempt"
                    )
            else:
                source_attempt = prior_attempts[-1] if prior_attempts else None
                attempt_kind = (
                    GenerationAttemptKind.CORRECTION
                    if source_attempt is not None
                    else GenerationAttemptKind.PRIMARY
                )
                attempt = self.repository.allocate_attempt_for_work_unit(
                    work_unit_id,
                    provider=adapter.name,
                    model=model,
                    attempt_kind=attempt_kind,
                    source_attempt_id=(
                        source_attempt.id if source_attempt is not None else None
                    ),
                    max_attempts=max_attempts,
                )
            compiled = base_compiled
            try:
                if source_attempt is not None:
                    compiled = self._compile_correction_request(
                        run=run,
                        work_unit=work_unit,
                        work_unit_id=work_unit_id,
                        base_compiled=base_compiled,
                        source_attempt=source_attempt,
                        dependencies=dependencies,
                        extraction_policy=extraction_policy,
                    )
                else:
                    self._assert_prior_prompt_contract(run.id, work_unit_id, compiled)
                existing_prompt = next(
                    (
                        artifact
                        for artifact in trace.artifacts
                        if artifact.attempt_id == attempt.id
                        and artifact.kind == ArtifactKind.PROMPT
                    ),
                    None,
                )
                if existing_prompt is None:
                    self._persist_prompt(
                        run, attempt, work_unit_id, compiled, adapter, model
                    )
                else:
                    self._assert_attempt_prompt_contract(
                        existing_prompt, attempt, compiled
                    )
            except Exception as error:
                self.repository.finish_attempt(
                    attempt.id,
                    AttemptStatus.FAILED,
                    error=str(error),
                    outcome_code=(
                        error.code
                        if isinstance(
                            error,
                            (
                                CorrectionPromptBudgetError,
                                CorrectionSourceContractError,
                            ),
                        )
                        else "contract.prompt_failed"
                    ),
                    failure_disposition=WorkUnitFailureDisposition.FAILED,
                )
                raise

            if self._cancelled(run.id, cancellation):
                self.repository.finish_attempt(attempt.id, AttemptStatus.CANCELLED)
                return None
            response_artifact = next(
                (
                    artifact
                    for artifact in trace.artifacts
                    if artifact.attempt_id == attempt.id
                    and artifact.kind == ArtifactKind.RESPONSE
                ),
                None,
            )
            if response_artifact is not None:
                provider_response = self._provider_response_from_artifact(
                    response_artifact,
                    attempt=attempt,
                    compiled=compiled,
                    fallback_provider=adapter.name,
                    fallback_model=model,
                )
            else:
                try:
                    provider_schema = self._provider_schema(compiled, adapter)
                    lease = self.secrets.lease_for_run(
                        run.id,
                        auth_mode=ProviderAuthMode(profile.text_auth_mode),
                        profile_id=profile.profile_id,
                    )
                except Exception as error:
                    self.repository.finish_attempt(
                        attempt.id,
                        AttemptStatus.FAILED,
                        error=str(error),
                        outcome_code="provider.preflight_failed",
                        failure_disposition=WorkUnitFailureDisposition.FAILED,
                    )
                    raise

                # Commit immediately before the non-idempotent provider boundary.
                try:
                    self.repository.mark_attempt_dispatched(attempt.id)
                except Exception as error:
                    self.repository.finish_attempt(
                        attempt.id,
                        AttemptStatus.FAILED,
                        error=str(error),
                        outcome_code="provider.dispatch_not_started",
                        failure_disposition=WorkUnitFailureDisposition.FAILED,
                    )
                    raise
                request = GenerationRequest(
                    messages=compiled.rendered.messages,
                    model=model,
                    temperature=profile.text_temperature,
                    max_output_tokens=min(
                        work_unit.budget.max_output_tokens,
                        profile.text_max_output_tokens,
                    ),
                    response_schema=provider_schema,
                    response_schema_name=(
                        _provider_schema_name(compiled.contract.schema_id)
                        if provider_schema is not None
                        else None
                    ),
                    metadata={
                        "run_id": run.id,
                        "attempt_id": attempt.id,
                        "work_unit_id": work_unit_id,
                        "prompt_hash": compiled.contract.rendered_hash,
                    },
                    request_extension=request_extension,
                    reasoning_mode=reasoning_mode,
                )
                try:
                    provider_response = adapter.generate(request, lease)
                except ProviderOutcomeUnknownError as error:
                    self.repository.mark_attempt_outcome_unknown(
                        attempt.id,
                        error=redact_provider_boundary_evidence(
                            str(error), secret_lease=lease
                        ),
                    )
                    raise
                except ProviderRequestNotSentError as error:
                    self.repository.finish_attempt(
                        attempt.id,
                        AttemptStatus.FAILED,
                        error=redact_provider_boundary_evidence(
                            str(error), secret_lease=lease
                        ),
                        outcome_code=error.code,
                        failure_disposition=WorkUnitFailureDisposition.FAILED,
                    )
                    raise
                except ProviderResponseError as error:
                    self.repository.finish_attempt(
                        attempt.id,
                        AttemptStatus.FAILED,
                        error=redact_provider_boundary_evidence(
                            str(error), secret_lease=lease
                        ),
                        outcome_code=error.code,
                        failure_disposition=WorkUnitFailureDisposition.FAILED,
                    )
                    raise
                except ProviderCapabilityError as error:
                    # The built-in adapter checks typed extensions before its
                    # HTTP call.  Persist the violated preflight contract
                    # without inventing an ambiguous external side effect.
                    self.repository.finish_attempt(
                        attempt.id,
                        AttemptStatus.FAILED,
                        error="provider capability preflight failed",
                        outcome_code="provider.request_not_sent",
                        failure_disposition=WorkUnitFailureDisposition.FAILED,
                    )
                    raise
                except ProviderError as error:
                    # Third-party adapters using only the historic base class
                    # do not declare delivery certainty.  Preserve the safe,
                    # conservative no-replay behavior.
                    self.repository.mark_attempt_outcome_unknown(
                        attempt.id,
                        error=redact_provider_boundary_evidence(
                            str(error), secret_lease=lease
                        ),
                    )
                    raise
                except Exception as error:
                    self.repository.mark_attempt_outcome_unknown(
                        attempt.id,
                        error=f"unexpected provider boundary failure: {type(error).__name__}",
                    )
                    raise

                provider_response = provider_response.model_copy(
                    update={
                        "raw": redact_provider_boundary_evidence(
                            provider_response.raw,
                            secret_lease=lease,
                        )
                    }
                )
                # Canonical final content is always message.content. Normalize
                # adapters that omit the convenience field without ever
                # falling back to reasoning/reasoning_content.
                try:
                    final_content = extract_assistant_text(provider_response)
                except ResponseExtractionError:
                    final_content = None
                provider_response = provider_response.model_copy(
                    update={
                        "final_content": final_content,
                        "outcome_code": (
                            provider_response.outcome_code
                            or (
                                None
                                if final_content is not None
                                else "response.missing_final_content"
                            )
                        ),
                    }
                )
                response_content = {
                    # The unmodified envelope is durable before local extraction/parsing.
                    # Reasoning remains here as evidence only and is never copied
                    # into a correction prompt or canonical candidate.
                    "rawResponse": provider_response.raw,
                    "providerRequestId": provider_response.request_id,
                    "finishReason": provider_response.finish_reason,
                    "finalContentPresent": provider_response.final_content is not None,
                    "reasoningPresent": provider_response.reasoning_present,
                    "outcomeCode": provider_response.outcome_code,
                    "usage": {
                        "inputTokens": provider_response.usage.input_tokens,
                        "outputTokens": provider_response.usage.output_tokens,
                    },
                    "contract": compiled.contract.snapshot_dump(),
                }
                try:
                    self.repository.persist_attempt_response(
                        attempt.id,
                        response_content,
                        provider_request_id=provider_response.request_id,
                    )
                except Exception as error:
                    # A provider response is already present in this process;
                    # failure to persist it is a storage failure, not an
                    # ambiguous provider outcome.  Do not replay or correct an
                    # attempt whose required evidence could not be committed.
                    self.repository.finish_attempt(
                        attempt.id,
                        AttemptStatus.FAILED,
                        error="provider response persistence failed",
                        outcome_code="storage.response_persist_failed",
                        failure_disposition=WorkUnitFailureDisposition.FAILED,
                    )
                    raise ProviderError(
                        "provider response persistence failed"
                    ) from error
            if self._cancelled(run.id, cancellation):
                self.repository.finish_attempt(attempt.id, AttemptStatus.CANCELLED)
                return None

            try:
                if provider_response.outcome_code == "response.missing_final_content":
                    raise ResponseExtractionError(
                        "Assistant message contains no final textual content"
                    )
                raw_text = extract_assistant_text(provider_response)
                extracted = parse_json_text(raw_text, policy=extraction_policy)
                report = compiled.validator.validate(
                    extracted.value,
                    context=SemanticValidationContext(
                        stage=work_unit.stage.value,
                        metadata={
                            "projectId": run.project_id,
                            "runId": run.id,
                            "attemptId": attempt.id,
                            "workUnitId": work_unit_id,
                        },
                    ),
                )
            except ResponseExtractionError as error:
                issue = ValidationIssue(
                    code=(
                        provider_response.outcome_code
                        or "response.extraction"
                    ),
                    message=str(error),
                )
                if self._reject_or_continue(
                    run=run,
                    attempt=attempt,
                    work_unit_id=work_unit_id,
                    compiled=compiled,
                    error=str(error),
                    issues=(issue,),
                    transformations=(),
                    max_attempts=max_attempts,
                ):
                    continue
                raise AssertionError("unreachable")
            except Exception as error:
                self._persist_validation(
                    run,
                    attempt.id,
                    work_unit_id,
                    compiled,
                    accepted=False,
                    issues=(),
                    transformations=(),
                    error=str(error),
                )
                self.repository.finish_attempt(
                    attempt.id,
                    AttemptStatus.FAILED,
                    error=str(error),
                    outcome_code="validation.internal_error",
                    failure_disposition=WorkUnitFailureDisposition.FAILED,
                )
                raise

            if not report.accepted:
                repair_facts = semantic_repair_facts(
                    extracted.value,
                    report.issues,
                    stage=work_unit.stage,
                    bible=(
                        dependencies.get(StageName.STORY_BIBLE)
                        if work_unit.stage
                        in {StageName.SCENE_BEATS, StageName.STORYBOARD}
                        else None
                    ),
                    dialogue_capacity_guidance=(
                        compiled.contract.dialogue_capacity_guidance
                        if work_unit.stage == StageName.SCENE_BEATS
                        else None
                    ),
                    dialogue_timing_profile=(
                        stage_plan.dialogue_timing_profile
                        if work_unit.stage == StageName.SCENE_BEATS
                        else None
                    ),
                    node_duration_budget_units=(
                        compiled.contract.node_duration_budget_units
                        if work_unit.stage == StageName.SCENE_BEATS
                        else None
                    ),
                    join_state_value_requirements=(
                        getattr(compiled.validator, "scoped_context", {}).get(
                            "join_state_value_requirements"
                        )
                        if work_unit.stage == StageName.SCENE_BEATS
                        else None
                    ),
                    storyboard_timing_guidance=(
                        compiled.contract.storyboard_timing_guidance
                        if work_unit.stage == StageName.STORYBOARD
                        else None
                    ),
                    story_graph_topology=(
                        story_graph_topology
                        if work_unit.stage == StageName.STORY_GRAPH
                        else None
                    ),
                    scoped_context=(
                        getattr(compiled.validator, "scoped_context", None)
                        if work_unit.stage
                        in {StageName.SCENE_BEATS, StageName.STORYBOARD}
                        else None
                    ),
                )
                if self._reject_or_continue(
                    run=run,
                    attempt=attempt,
                    work_unit_id=work_unit_id,
                    compiled=compiled,
                    error="response failed schema or semantic validation",
                    issues=report.issues,
                    transformations=extracted.transformations,
                    max_attempts=max_attempts,
                    repair_facts=repair_facts,
                ):
                    continue
                raise AssertionError("unreachable")

            self._persist_validation(
                run,
                attempt.id,
                work_unit_id,
                compiled,
                accepted=True,
                issues=report.issues,
                transformations=(
                    *extracted.transformations,
                    *(
                        (FRAGMENT_ID_BINDING_VERSION,)
                        if work_unit.stage in {StageName.SCENE_BEATS, StageName.STORYBOARD}
                        else ()
                    ),
                    *(
                        (AUDIO_EVENT_ID_BINDING_VERSION,)
                        if work_unit.stage == StageName.STORYBOARD
                        else ()
                    ),
                ),
            )
            fragment = self._fragment_for_unit(
                stage=work_unit.stage,
                stage_plan=stage_plan,
                work_unit_id=work_unit_id,
                value=report.value,
            )
            candidate_content = fragment.model_dump(mode="json", by_alias=False)
            try:
                candidate = self.repository.add_artifact(
                    Artifact(
                        run_id=run.id,
                        attempt_id=attempt.id,
                        work_unit_id=work_unit_id,
                        stage=work_unit.stage,
                        kind=ArtifactKind.CANDIDATE,
                        content=candidate_content,
                        content_hash=stable_hash(candidate_content),
                    )
                )
                self.repository.finish_attempt(
                    attempt.id,
                    AttemptStatus.SUCCEEDED,
                    outcome_code="response.accepted",
                )
            except Exception as error:
                self.repository.finish_attempt(
                    attempt.id,
                    AttemptStatus.FAILED,
                    error=str(error),
                    outcome_code="artifact.commit_failed",
                    failure_disposition=WorkUnitFailureDisposition.FAILED,
                )
                raise
            return candidate.id

    def _reject_or_continue(
        self,
        *,
        run: GenerationRun,
        attempt: GenerationAttempt,
        work_unit_id: str,
        compiled: CompiledWorkUnitRequest,
        error: str,
        issues: tuple[ValidationIssue, ...],
        transformations: tuple[str, ...],
        max_attempts: int,
        repair_facts: tuple[SemanticRepairFact, ...] = (),
    ) -> bool:
        """Persist one known rejection, then either expose a correction or stop."""

        self._persist_validation(
            run,
            attempt.id,
            work_unit_id,
            compiled,
            accepted=False,
            issues=issues,
            transformations=transformations,
            error=error,
            repair_facts=repair_facts,
        )
        outcome_code = issues[0].code if issues else "response.rejected"
        can_correct = attempt.attempt_number < max_attempts
        self.repository.finish_attempt(
            attempt.id,
            AttemptStatus.FAILED,
            error=error,
            outcome_code=outcome_code,
            allow_correction=can_correct,
            failure_disposition=WorkUnitFailureDisposition.QUARANTINED,
        )
        if can_correct:
            return True
        raise QuarantinedOutputError(
            error,
            artifacts=[],
            code=outcome_code,
            stage=attempt.stage,
        )

    def _compile_correction_request(
        self,
        *,
        run: GenerationRun,
        work_unit: GenerationWorkUnit,
        work_unit_id: str,
        base_compiled: CompiledWorkUnitRequest,
        source_attempt: GenerationAttempt,
        dependencies: Mapping[StageName, StagePayloadV2],
        extraction_policy: ExtractionPolicy,
    ) -> CompiledWorkUnitRequest:
        """Render one compact correction packet from durable final evidence.

        The closed response schema carries the immutable topology/selector
        structure.  The correction packet deliberately omits the broader
        creative context: the previous final answer supplies its prose while
        the schema, frozen contract, and stable code/path pairs supply the only
        correction authority.  Free-form validator messages remain in the
        audit artifact.
        """

        trace = self.repository.get_run_trace(run.id)
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
        self._assert_correction_source_contract(
            source_attempt=source_attempt,
            source_contract=source_contract,
            base_compiled=base_compiled,
        )
        issues = []
        validated_issues: list[ValidationIssue] = []
        for item in validation_content.get("issues", []):
            if not isinstance(item, Mapping):
                continue
            issue = ValidationIssue.model_validate(item)
            validated_issues.append(issue)
            issues.append({"code": issue.code, "path": list(issue.path)})
        if not issues:
            raise ValueError("correction source has no stable validation issues")
        parsed_repair_facts: list[SemanticRepairFact] = []
        raw_repair_facts = validation_content.get("repairFacts", [])
        if not isinstance(raw_repair_facts, list):
            raise ValueError("correction source has malformed deterministic repair facts")
        source_value: Any | None = None
        for item in raw_repair_facts:
            if not isinstance(item, Mapping):
                raise ValueError("correction source has malformed deterministic repair facts")
            fact = parse_semantic_repair_fact(item)
            assert_semantic_repair_fact_matches_issue(
                fact, tuple(validated_issues)
            )
            self._assert_timing_fact_guidance(
                fact,
                source_contract=source_contract,
            )
            if fact.code in {
                "semantic.continuity_beat_sequence_mismatch",
                "semantic.continuity_shot_sequence_mismatch",
            }:
                if source_value is None:
                    try:
                        source_value = parse_json_text(
                            previous_final_content,
                            policy=extraction_policy,
                        ).value
                    except ResponseExtractionError as error:
                        raise CorrectionSourceContractError(
                            "continuity repair source can no longer be extracted"
                        ) from error
                try:
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
            parsed_repair_facts.append(fact)
        try:
            instruction_plan = compile_correction_instruction_plan(
                validated_issues,
                parsed_repair_facts,
            )
            correction_schema = compile_correction_response_schema(
                base_compiled.response_schema,
                parsed_repair_facts,
            )
        except (CorrectionDirectivePlanError, CorrectionResponseSchemaError) as error:
            raise CorrectionSourceContractError(str(error)) from error
        correction_ordinal = source_attempt.attempt_number
        correction_strategy = (
            "repair_previous_final"
            if correction_ordinal == 1
            else "reconstruct_from_schema"
        )
        rendered = self.renderer.render(
            "work_unit_correction",
            {
                "original_contract": base_compiled.contract.snapshot_dump(),
                "response_schema": correction_schema.schema,
                "previous_final_content": previous_final_content,
                "validation_issues": issues,
                "repair_evidence_projection": instruction_plan.prompt_evidence,
                "correction_directives": [
                    directive.model_dump(mode="json")
                    for directive in instruction_plan.directives
                ],
                "correction_ordinal": correction_ordinal,
                "correction_strategy": correction_strategy,
            },
        )
        if source_attempt.attempt_kind == GenerationAttemptKind.CORRECTION:
            current_prompt_identity = {
                "prompt_id": rendered.trace.prompt_id,
                "prompt_version": rendered.trace.prompt_version,
                "prompt_spec_hash": rendered.trace.spec_hash,
            }
            if any(
                source_contract.get(key) != value
                for key, value in current_prompt_identity.items()
            ):
                raise CorrectionSourceContractError(
                    "correction prompt contract changed after the source rejection"
                )
        input_bytes = sum(
            len(message.content.encode("utf-8")) for message in rendered.messages
        )
        if input_bytes > work_unit.budget.max_input_bytes:
            raise CorrectionPromptBudgetError(
                "correction prompt is "
                f"{input_bytes} bytes, exceeding the frozen max_input_bytes "
                f"budget of {work_unit.budget.max_input_bytes}"
            )
        contract = type(base_compiled.contract).model_validate(
            {
                **base_compiled.contract.snapshot_dump(),
                "prompt_id": rendered.trace.prompt_id,
                "prompt_version": rendered.trace.prompt_version,
                "prompt_spec_hash": rendered.trace.spec_hash,
                "variables_hash": rendered.trace.input_hash,
                "rendered_hash": rendered.trace.rendered_hash,
                "correction_ordinal": correction_ordinal,
                "correction_strategy": correction_strategy,
                "correction_directive_set_hash": instruction_plan.directive_set_hash,
                "correction_evidence_projection_hash": (
                    instruction_plan.evidence_projection_hash
                ),
                "correction_response_schema_hash": correction_schema.schema_hash,
            }
        )
        return CompiledWorkUnitRequest(
            rendered=rendered,
            validator=base_compiled.validator,
            contract=contract,
            response_schema=correction_schema.schema,
        )

    @staticmethod
    def _assert_timing_fact_guidance(
        fact: SemanticRepairFact,
        *,
        source_contract: Mapping[str, Any],
    ) -> None:
        """Reject a self-consistent timing plan from another frozen scope.

        Artifact hashes make persisted evidence tamper-evident only when the
        semantic fact is also bound back to the source prompt contract.  The
        plan's internal hash alone cannot establish that its scene/cues were
        those supplied to the rejected work unit.
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

    @staticmethod
    def _assert_correction_source_contract(
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
        if source_contract.get("correction_ordinal") != (
            source_attempt.attempt_number - 1
        ):
            raise CorrectionSourceContractError(
                "correction source ordinal does not match its durable attempt lineage"
            )

    def _persist_prompt(
        self,
        run: GenerationRun,
        attempt: GenerationAttempt,
        work_unit_id: str,
        compiled: CompiledWorkUnitRequest,
        adapter: ProviderAdapter,
        model: str,
    ) -> None:
        content = {
            "trace": compiled.rendered.trace.model_dump(mode="json"),
            "messages": [message.model_dump(mode="json") for message in compiled.rendered.messages],
            "schemaId": compiled.contract.schema_id,
            "structuredOutputMode": compiled.rendered.output.structured_output_mode,
            "provider": adapter.name,
            "model": model,
            "attemptKind": attempt.attempt_kind.value,
            "sourceAttemptId": attempt.source_attempt_id,
            "contract": compiled.contract.snapshot_dump(),
        }
        self.repository.add_artifact(
            Artifact(
                run_id=run.id,
                attempt_id=attempt.id,
                work_unit_id=work_unit_id,
                stage=compiled.contract.stage,
                kind=ArtifactKind.PROMPT,
                content=content,
                content_hash=stable_hash(content),
            )
        )

    @staticmethod
    def _assert_attempt_prompt_contract(
        artifact: Artifact,
        attempt: GenerationAttempt,
        compiled: CompiledWorkUnitRequest,
    ) -> None:
        """Verify that a resumed attempt still means exactly the same request."""

        content = artifact.content if isinstance(artifact.content, Mapping) else {}
        expected_contract = compiled.contract.snapshot_dump()
        if (
            artifact.attempt_id != attempt.id
            or content.get("contract") != expected_contract
            or content.get("attemptKind") != attempt.attempt_kind.value
            or content.get("sourceAttemptId") != attempt.source_attempt_id
        ):
            raise ValueError(
                "recoverable attempt prompt evidence does not match its frozen execution contract"
            )

    @staticmethod
    def _provider_response_from_artifact(
        artifact: Artifact,
        *,
        attempt: GenerationAttempt,
        compiled: CompiledWorkUnitRequest,
        fallback_provider: str,
        fallback_model: str,
    ) -> ProviderResponse:
        """Rehydrate a durable response for local-only post-crash processing."""

        content = artifact.content if isinstance(artifact.content, Mapping) else {}
        raw = content.get("rawResponse")
        if not isinstance(raw, dict):
            raise ValueError("durable provider response has no object envelope")
        expected_contract = compiled.contract.snapshot_dump()
        if content.get("contract") != expected_contract:
            raise ValueError(
                "durable provider response does not match the frozen prompt contract"
            )
        try:
            final_content = extract_assistant_text(raw)
        except ResponseExtractionError:
            final_content = None
        usage = content.get("usage")
        usage_data = usage if isinstance(usage, Mapping) else {}
        outcome_code = content.get("outcomeCode")
        return ProviderResponse(
            provider=attempt.provider or fallback_provider,
            model=attempt.model or fallback_model,
            raw=raw,
            request_id=(
                str(content["providerRequestId"])
                if content.get("providerRequestId") is not None
                else attempt.provider_request_id
            ),
            finish_reason=(
                str(content["finishReason"])
                if content.get("finishReason") is not None
                else None
            ),
            usage=ProviderUsage(
                input_tokens=_optional_non_negative_int(usage_data.get("inputTokens")),
                output_tokens=_optional_non_negative_int(usage_data.get("outputTokens")),
            ),
            final_content=final_content,
            reasoning_present=bool(content.get("reasoningPresent")),
            outcome_code=(
                str(outcome_code)
                if outcome_code is not None
                else (
                    None
                    if final_content is not None
                    else "response.missing_final_content"
                )
            ),
        )

    def _persist_validation(
        self,
        run: GenerationRun,
        attempt_id: str,
        work_unit_id: str,
        compiled: CompiledWorkUnitRequest,
        *,
        accepted: bool,
        issues: tuple[ValidationIssue, ...],
        transformations: tuple[str, ...],
        error: str | None = None,
        repair_facts: tuple[SemanticRepairFact, ...] = (),
    ) -> None:
        content = {
            "accepted": accepted,
            "issues": [issue.model_dump(mode="json") for issue in issues],
            "transformations": list(transformations),
            "error": error,
            "repairFacts": [
                serialize_semantic_repair_fact(fact)
                for fact in repair_facts
            ],
            "contract": compiled.contract.snapshot_dump(),
        }
        self.repository.add_artifact(
            Artifact(
                run_id=run.id,
                attempt_id=attempt_id,
                work_unit_id=work_unit_id,
                stage=compiled.contract.stage,
                kind=ArtifactKind.VALIDATION,
                content=content,
                content_hash=stable_hash(content),
            )
        )

    def _assert_prior_prompt_contract(
        self, run_id: str, work_unit_id: str, compiled: CompiledWorkUnitRequest
    ) -> None:
        """Refuse an undispatched recovery when its prompt/schema changed."""

        expected = compiled.contract.snapshot_dump()
        previous_prompts = [
            artifact
            for artifact in self.repository.get_run_trace(run_id).artifacts
            if artifact.work_unit_id == work_unit_id and artifact.kind == ArtifactKind.PROMPT
        ]
        if not previous_prompts:
            return
        prior = previous_prompts[-1].content
        prior_contract = prior.get("contract") if isinstance(prior, Mapping) else None
        if prior_contract != expected:
            raise ValueError(
                "work-unit prompt contract changed after durable prompt evidence; "
                "the undispatched unit must not be resent"
            )

    @staticmethod
    def _provider_schema(
        compiled: CompiledWorkUnitRequest, adapter: ProviderAdapter
    ) -> dict[str, Any] | None:
        mode = compiled.rendered.output.structured_output_mode
        if mode == "none":
            return None
        if adapter.capabilities.json_schema:
            return compiled.response_schema
        if mode == "require":
            raise ProviderCapabilityError(
                f"Prompt {compiled.contract.prompt_id!r} requires native JSON Schema output, "
                f"but provider {adapter.name!r} does not advertise it"
            )
        return None

    def _stage_dependencies(
        self,
        run: GenerationRun,
        stage: StageName,
        sealed_payloads: Mapping[StageName, StagePayloadV2],
        *,
        repair_scope: WorkUnitRepairScope | None = None,
    ) -> dict[StageName, StagePayloadV2]:
        if repair_scope is not None:
            # The target stage may depend on parent-run output that was sealed
            # but never canonically installed after quarantine.  Only the
            # repository can resolve that immutable boundary; later child
            # stages resolve exclusively through child-local seals.
            return self.repository.get_repair_stage_dependencies(
                run.id,
                stage,
            )
        ordered = (StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS, StageName.STORYBOARD)
        dependencies: dict[StageName, StagePayloadV2] = {}
        requested = set(run.requested_stages)
        for upstream in ordered[: ordered.index(stage)]:
            if upstream in requested:
                payload = sealed_payloads.get(upstream)
                if payload is None:
                    raise ValueError(f"{stage.value} cannot run before {upstream.value} is sealed")
                dependencies[upstream] = payload
            else:
                dependencies[upstream] = self.repository.get_snapshot_stage_payload(run.id, upstream)
        return dependencies

    def _get_stage_plan(
        self,
        run: GenerationRun,
        stage: StageName,
        *,
        dependencies: Mapping[StageName, StagePayloadV2],
        repair_scope: WorkUnitRepairScope | None,
    ) -> StagePlan:
        """Obtain an immutable plan without giving repair callers authority.

        A normal run asserts the dependency values it just resolved.  An exact
        child repair delegates to the repository's scope-aware planner because
        its initial dependency boundary may be a parent seal rather than a
        canonical head.  The runner never gets to substitute either form.
        """

        if repair_scope is not None:
            return self.repository.get_or_create_repair_stage_plan(
                run.id,
                stage,
                dependencies=dict(dependencies),
            )
        return self.repository.get_or_create_stage_plan(
            run.id,
            stage,
            dependencies=dict(dependencies),
        )

    def _materialize_reused_unit_candidates(
        self,
        run_id: str,
        stage: StageName,
        stage_plan: StagePlan,
    ) -> dict[str, str]:
        """Create child-local evidence only for scope-frozen reuse bindings.

        The binding service verifies all source hashes and creates an immutable
        child candidate with ``sourceArtifactId``.  We retain normal candidate
        ownership for aggregate sealing; no caller is allowed to point an
        aggregate directly at a parent candidate.
        """

        expected_unit_ids = {unit.unit_id for unit in stage_plan.work_units}
        candidates: dict[str, str] = {}
        for binding in self.repository.prepare_repair_stage_reuse(run_id, stage):
            artifact = self.repository.materialize_fragment_reuse_binding(
                run_id,
                binding.id,
            )
            if (
                artifact.run_id != run_id
                or artifact.stage != stage
                or artifact.kind != ArtifactKind.CANDIDATE
                or artifact.work_unit_id not in expected_unit_ids
            ):
                raise ValueError(
                    "repository materialized a reuse artifact outside the child stage plan"
                )
            if artifact.work_unit_id in candidates:
                raise ValueError("repair scope has more than one reuse binding for a work unit")
            candidates[artifact.work_unit_id] = artifact.id
        return candidates

    def _existing_unit_candidates(
        self, run_id: str, stage: StageName, stage_plan: StagePlan
    ) -> dict[str, str]:
        expected = {unit.unit_id for unit in stage_plan.work_units}
        trace = self.repository.get_run_trace(run_id)
        succeeded_attempt_ids = {
            attempt.id
            for attempt in trace.attempts
            if attempt.status == AttemptStatus.SUCCEEDED
        }
        candidates: dict[str, str] = {}
        for artifact in trace.artifacts:
            if (
                artifact.kind == ArtifactKind.CANDIDATE
                and artifact.stage == stage
                and artifact.work_unit_id in expected
                and artifact.attempt_id in succeeded_attempt_ids
                and artifact.work_unit_id not in candidates
            ):
                candidates[artifact.work_unit_id] = artifact.id
        return candidates

    def _sealed_stage(self, run_id: str, stage: StageName) -> Any | None:
        trace = self.repository.get_run_execution_trace(run_id)
        return next((seal for seal in trace.sealed_aggregates if seal.stage == stage), None)

    @staticmethod
    def _fragment_for_unit(
        *, stage: StageName, stage_plan: StagePlan, work_unit_id: str, value: Any
    ) -> Any:
        if stage == StageName.STORY_BIBLE:
            return StoryBibleFragment(
                stage_plan_hash=stage_plan.stage_plan_hash,
                work_unit_id=work_unit_id,
                payload=value,
            )
        if stage == StageName.STORY_GRAPH:
            return StoryGraphFragment(
                stage_plan_hash=stage_plan.stage_plan_hash,
                work_unit_id=work_unit_id,
                payload=value,
            )
        return value

    def _cancelled(self, run_id: str, cancellation: Event) -> bool:
        return cancellation.is_set() or self.repository.get_run(run_id).status == RunStatus.CANCEL_REQUESTED

    @staticmethod
    def _stage_constraints(
        stage: StageName, brief: ProjectBrief, instructions: str | None
    ) -> dict[str, Any]:
        extra = {"runInstructions": instructions} if instructions else {}
        if stage == StageName.STORY_BIBLE:
            return extra
        if stage == StageName.STORY_GRAPH:
            return {
                "nodeBudget": brief.node_budget,
                "maxOutDegree": brief.max_out_degree,
                "endingCount": brief.ending_count,
                "decisionPointsPerPath": brief.decision_points_per_path,
                "desiredJoinCount": brief.desired_join_count,
                **extra,
            }
        if stage == StageName.SCENE_BEATS:
            return {
                "targetPlaythroughSeconds": brief.target_playthrough_seconds,
                "language": brief.language,
                "oneVisibleChangePerBeat": True,
                **extra,
            }
        return {
            "aspectRatio": brief.aspect_ratio,
            "visualStyle": brief.visual_style,
            "shotsPerSceneMin": brief.shots_per_scene_min,
            "shotsPerSceneMax": brief.shots_per_scene_max,
            **extra,
        }


def _provider_schema_name(schema_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", schema_id).strip("_-")
    if not normalized or not normalized[0].isalpha():
        normalized = f"schema_{normalized}"
    return normalized[:64]


def _optional_non_negative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None
