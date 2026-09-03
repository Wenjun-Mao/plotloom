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
    GenerationRun,
    ProjectBrief,
    ProviderAuthMode,
    ProviderSnapshot,
    RunStatus,
    StageName,
    StagePayload,
    stage_payload_model,
)
from .exceptions import QuarantinedOutputError
from .generation.contracts import GenerationRequest, ValidationIssue
from .generation.exceptions import ProviderCapabilityError, ResponseExtractionError
from .generation.fragments import StoryBibleFragment, StoryGraphFragment
from .generation.planning import StagePlan
from .generation.prompts import PromptRenderer
from .generation.providers import ProviderAdapter
from .generation.responses import extract_assistant_text, parse_json_text
from .generation.secrets import SecretLease
from .generation.validation import SemanticValidationContext
from .generation.work_units import CompiledWorkUnitRequest, compile_work_unit_request
from .persistence import SQLiteRepository, stable_hash
from .runtime import RunExecutionResult


class RunSecretLeaser(Protocol):
    def lease_for_run(
        self,
        run_id: str,
        *,
        auth_mode: ProviderAuthMode,
    ) -> SecretLease | None: ...

    def release_run(self, run_id: str) -> None: ...


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
        profile: ProviderSnapshot,
        cancellation: Event,
    ) -> RunExecutionResult:
        """Run exact units, returning only repository-owned aggregate IDs."""

        generation_plan = self.repository.get_generation_plan(run.id)
        brief = run.canonical_snapshot.brief
        sealed_payloads: dict[StageName, StagePayload] = {}
        sealed_ids: list[str] = []
        try:
            for stage in run.requested_stages:
                if self._cancelled(run.id, cancellation):
                    return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
                existing = self._sealed_stage(run.id, stage)
                if existing is not None:
                    sealed_payloads[stage] = stage_payload_model(stage).model_validate(
                        existing.payload
                    )
                    sealed_ids.append(existing.id)
                    continue

                dependencies = self._stage_dependencies(run, stage, sealed_payloads)
                # Repository planning treats these as assertions against its
                # frozen snapshot/seals, never as caller-provided authority.
                stage_plan = self.repository.get_or_create_stage_plan(
                    run.id, stage, dependencies=dependencies
                )
                candidates = self._existing_unit_candidates(run.id, stage, stage_plan)
                for work_unit in stage_plan.work_units:
                    if work_unit.unit_id in candidates:
                        continue
                    if self._cancelled(run.id, cancellation):
                        return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
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
                        cancellation=cancellation,
                    )
                    if candidate_id is None:
                        return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
                    candidates[work_unit.unit_id] = candidate_id

                if self._cancelled(run.id, cancellation):
                    return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
                aggregate = self.repository.seal_stage_aggregate(
                    run.id,
                    stage,
                    candidate_artifact_ids=[candidates[unit.unit_id] for unit in stage_plan.work_units],
                )
                sealed_payloads[stage] = stage_payload_model(stage).model_validate(
                    aggregate.payload
                )
                sealed_ids.append(aggregate.id)
            return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
        finally:
            self.secrets.release_run(run.id)

    def _execute_work_unit(
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
        profile: ProviderSnapshot,
        cancellation: Event,
    ) -> str | None:
        work_unit = next(unit for unit in stage_plan.work_units if unit.unit_id == work_unit_id)
        attempt = self.repository.allocate_attempt_for_work_unit(
            work_unit_id, provider=adapter.name, model=model
        )
        try:
            compiled = compile_work_unit_request(
                generation_plan=generation_plan,
                stage_plan=stage_plan,
                work_unit=work_unit,
                dependencies=dependencies,
                brief=brief,
                canonical_snapshot=run.canonical_snapshot,
                instructions=run.instructions or "",
                stage_constraints=self._stage_constraints(work_unit.stage, brief, run.instructions),
                renderer=self.renderer,
            )
            self._assert_prior_prompt_contract(run.id, work_unit_id, compiled)
            self._persist_prompt(run, attempt.id, work_unit_id, compiled, adapter, model)
        except Exception as error:
            self.repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error=str(error))
            raise

        if self._cancelled(run.id, cancellation):
            self.repository.finish_attempt(attempt.id, AttemptStatus.CANCELLED)
            return None
        try:
            provider_schema = self._provider_schema(compiled, adapter)
            lease = self.secrets.lease_for_run(run.id, auth_mode=profile.text_auth_mode)
        except Exception as error:
            self.repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error=str(error))
            raise

        # Commit immediately before the non-idempotent provider boundary.
        try:
            self.repository.mark_attempt_dispatched(attempt.id)
        except Exception as error:
            self.repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error=str(error))
            raise
        request = GenerationRequest(
            messages=compiled.rendered.messages,
            model=model,
            temperature=profile.text_temperature,
            max_output_tokens=min(work_unit.budget.max_output_tokens, profile.text_max_output_tokens),
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
        )
        try:
            provider_response = adapter.generate(request, lease)
        except Exception as error:
            self.repository.mark_attempt_outcome_unknown(attempt.id, error=str(error))
            raise

        response_content = {
            # The unmodified envelope is durable before local extraction/parsing.
            "rawResponse": provider_response.raw,
            "providerRequestId": provider_response.request_id,
            "finishReason": provider_response.finish_reason,
            "usage": {
                "inputTokens": provider_response.usage.input_tokens,
                "outputTokens": provider_response.usage.output_tokens,
            },
            "contract": compiled.contract.model_dump(mode="json", by_alias=True),
        }
        try:
            self.repository.persist_attempt_response(
                attempt.id,
                response_content,
                provider_request_id=provider_response.request_id,
            )
        except Exception as error:
            self.repository.mark_attempt_outcome_unknown(attempt.id, error=str(error))
            raise
        if self._cancelled(run.id, cancellation):
            self.repository.finish_attempt(attempt.id, AttemptStatus.CANCELLED)
            return None

        try:
            raw_text = extract_assistant_text(provider_response)
            extracted = parse_json_text(raw_text)
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
            return self._quarantine(
                run,
                attempt.id,
                work_unit_id,
                compiled,
                error=str(error),
                issues=(ValidationIssue(code="response.extraction", message=str(error)),),
            )
        except Exception as error:
            self._persist_validation(
                run, attempt.id, work_unit_id, compiled,
                accepted=False, issues=(), transformations=(), error=str(error),
            )
            self.repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error=str(error))
            raise

        if not report.accepted:
            return self._quarantine(
                run,
                attempt.id,
                work_unit_id,
                compiled,
                error="response failed schema or semantic validation",
                issues=report.issues,
                transformations=extracted.transformations,
            )
        self._persist_validation(
            run, attempt.id, work_unit_id, compiled,
            accepted=True, issues=report.issues, transformations=extracted.transformations,
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
            self.repository.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
        except Exception as error:
            self.repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error=str(error))
            raise
        return candidate.id

    def _quarantine(
        self,
        run: GenerationRun,
        attempt_id: str,
        work_unit_id: str,
        compiled: CompiledWorkUnitRequest,
        *,
        error: str,
        issues: tuple[ValidationIssue, ...],
        transformations: tuple[str, ...] = (),
    ) -> str:
        self._persist_validation(
            run, attempt_id, work_unit_id, compiled,
            accepted=False, issues=issues, transformations=transformations, error=error,
        )
        self.repository.finish_attempt(attempt_id, AttemptStatus.FAILED, error=error)
        raise QuarantinedOutputError(error, artifacts=[])

    def _persist_prompt(
        self,
        run: GenerationRun,
        attempt_id: str,
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
            "contract": compiled.contract.model_dump(mode="json", by_alias=True),
        }
        self.repository.add_artifact(
            Artifact(
                run_id=run.id,
                attempt_id=attempt_id,
                work_unit_id=work_unit_id,
                stage=compiled.contract.stage,
                kind=ArtifactKind.PROMPT,
                content=content,
                content_hash=stable_hash(content),
            )
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
    ) -> None:
        content = {
            "accepted": accepted,
            "issues": [issue.model_dump(mode="json") for issue in issues],
            "transformations": list(transformations),
            "error": error,
            "contract": compiled.contract.model_dump(mode="json", by_alias=True),
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

        expected = compiled.contract.model_dump(mode="json", by_alias=True)
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
        sealed_payloads: Mapping[StageName, StagePayload],
    ) -> dict[StageName, StagePayload]:
        ordered = (StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS, StageName.STORYBOARD)
        dependencies: dict[StageName, StagePayload] = {}
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

    def _existing_unit_candidates(
        self, run_id: str, stage: StageName, stage_plan: StagePlan
    ) -> dict[str, str]:
        expected = {unit.unit_id for unit in stage_plan.work_units}
        candidates: dict[str, str] = {}
        for artifact in self.repository.get_run_trace(run_id).artifacts:
            if (
                artifact.kind == ArtifactKind.CANDIDATE
                and artifact.stage == stage
                and artifact.work_unit_id in expected
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
