"""Unit attempt allocation, recovery, rejection and candidate lifecycle."""

from __future__ import annotations

from threading import Event
from typing import TYPE_CHECKING, Any, Mapping

from plotloom.generation.planning_contracts import StagePlan
from plotloom.generation.story_graph_topology_contracts import StoryGraphTopology

from .domain import (
    Artifact,
    ArtifactKind,
    AttemptStatus,
    GenerationAttempt,
    GenerationAttemptKind,
    GenerationRun,
    ProjectBrief,
    ProviderSnapshot,
    RunStatus,
    StageName,
    StagePayload,
    WorkUnitFailureDisposition,
)
from .exceptions import QuarantinedOutputError
from .generation.contracts import (
    ExtractionPolicy,
    ReasoningMode,
    RequestExtension,
    ValidationIssue,
)
from .generation.correction_postconditions import (
    validate_correction_postconditions,
)
from .generation.exceptions import (
    ResponseExtractionError,
)
from .generation.fragments import StoryBibleFragment, StoryGraphFragment
from .generation.prompts import PromptRenderer
from .generation.providers import ProviderAdapter
from .generation.repair_facts import (
    SemanticRepairFact,
)
from .generation.responses import (
    extract_assistant_text,
    parse_json_text,
)
from .generation.semantic_repair import (
    semantic_repair_facts,
)
from .generation.validation import SemanticValidationContext
from .generation.work_unit_contracts import (
    AUDIO_EVENT_ID_BINDING_VERSION,
    FRAGMENT_ID_BINDING_VERSION,
    CompiledWorkUnitRequest,
)
from .generation.work_units import (
    compile_work_unit_request,
)
from .persistence.codec import stable_hash
from .provider_profiles import TextProviderProfileSnapshot

if TYPE_CHECKING:
    from .persistence.project.repository_generation import (
        ProjectGenerationRepository as GenerationRunRepository,
    )

from .correction_execution_contracts import (
    CorrectionPromptBudgetError,
    CorrectionSourceContractError,
)
from .durable_provider_exchange import exchange_provider_response
from .runtime_secrets import RunSecretLeaser
from .work_unit_correction import compile_correction_request
from .work_unit_evidence import (
    assert_attempt_prompt_contract,
    assert_prior_prompt_contract,
    persist_prompt,
    persist_validation,
)


class DurableUnitExecutor:
    """Own one unit attempt/correction loop, with execution-local state."""

    def __init__(
        self,
        repository: "GenerationRunRepository",
        secrets: RunSecretLeaser,
        renderer: PromptRenderer,
    ) -> None:
        self.repository = repository
        self.secrets = secrets
        self.renderer = renderer

    def execute(
        self,
        *,
        run: GenerationRun,
        generation_plan: Any,
        stage_plan: StagePlan,
        work_unit_id: str,
        dependencies: Mapping[StageName, StagePayload],
        brief: ProjectBrief,
        adapter: ProviderAdapter,
        model: str,
        profile: ProviderSnapshot | TextProviderProfileSnapshot,
        story_graph_topology: StoryGraphTopology | None,
        cancellation: Event,
    ) -> str | None:
        work_unit = next(
            unit for unit in stage_plan.work_units if unit.unit_id == work_unit_id
        )
        base_compiled = compile_work_unit_request(
            generation_plan=generation_plan,
            stage_plan=stage_plan,
            work_unit=work_unit,
            dependencies=dependencies,
            brief=brief,
            canonical_snapshot=run.canonical_snapshot,
            instructions=run.instructions or "",
            stage_constraints=self._stage_constraints(
                work_unit.stage, brief, run.instructions
            ),
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
            request_extension, reasoning_mode, extraction_policy = (
                profile.request_contract()
            )
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
                (item for item in trace.attempts if item.work_unit_id == work_unit_id),
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
                    compiled = compile_correction_request(
                        self.repository,
                        self.renderer,
                        run=run,
                        work_unit=work_unit,
                        work_unit_id=work_unit_id,
                        base_compiled=base_compiled,
                        source_attempt=source_attempt,
                        dependencies=dependencies,
                        extraction_policy=extraction_policy,
                    )
                else:
                    assert_prior_prompt_contract(
                        self.repository, run.id, work_unit_id, compiled
                    )
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
                    persist_prompt(
                        self.repository,
                        run,
                        attempt,
                        work_unit_id,
                        compiled,
                        adapter,
                        model,
                    )
                else:
                    assert_attempt_prompt_contract(existing_prompt, attempt, compiled)
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
            provider_response = exchange_provider_response(
                repository=self.repository,
                secrets=self.secrets,
                run=run,
                attempt=attempt,
                work_unit=work_unit,
                work_unit_id=work_unit_id,
                compiled=compiled,
                adapter=adapter,
                model=model,
                profile=profile,
                request_extension=request_extension,
                reasoning_mode=reasoning_mode,
                response_artifact=response_artifact,
            )
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
                    code=(provider_response.outcome_code or "response.extraction"),
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
                persist_validation(
                    self.repository,
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

            if compiled.correction_repair_facts:
                postcondition_issues = validate_correction_postconditions(
                    extracted.value,
                    compiled.correction_repair_facts,
                )
                if postcondition_issues:
                    self._reject_or_continue(
                        run=run,
                        attempt=attempt,
                        work_unit_id=work_unit_id,
                        compiled=compiled,
                        error=(
                            "correction output violated frozen exact repair authority"
                        ),
                        issues=(*postcondition_issues, *report.issues),
                        transformations=extracted.transformations,
                        max_attempts=max_attempts,
                        allow_further_correction=False,
                    )
                    raise AssertionError("unreachable")

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

            persist_validation(
                self.repository,
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
                        if work_unit.stage
                        in {StageName.SCENE_BEATS, StageName.STORYBOARD}
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
        allow_further_correction: bool = True,
    ) -> bool:
        """Persist one known rejection, then either expose a correction or stop."""

        persist_validation(
            self.repository,
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
        can_correct = allow_further_correction and attempt.attempt_number < max_attempts
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
        return (
            cancellation.is_set()
            or self.repository.get_run(run_id).status == RunStatus.CANCEL_REQUESTED
        )

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
            "visualStyle": brief.visual_direction,
            "shotsPerSceneMin": brief.shots_per_scene_min,
            "shotsPerSceneMax": brief.shots_per_scene_max,
            "shotCountPolicy": brief.shot_count_policy,
            **extra,
        }
