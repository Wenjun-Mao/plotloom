"""Stage composition for durable immutable generation work units."""

from __future__ import annotations

from threading import Event
from typing import TYPE_CHECKING, Any, Mapping

from plotloom.generation.planning_contracts import StagePlan

from .domain import (
    ArtifactKind,
    AttemptStatus,
    GenerationRun,
    ProviderSnapshot,
    RunStatus,
    StageName,
    StagePayload,
    WorkUnitRepairScope,
    stage_payload_model,
)
from .exceptions import QuarantinedOutputError, RunExecutionError
from .generation.prompts import PromptRenderer
from .generation.providers import ProviderAdapter
from .generation.work_unit_contracts import (
    WorkUnitContractError,
)
from .persistence.codec import stable_hash
from .provider_profiles import TextProviderProfileSnapshot
from .runtime import RunExecutionResult

if TYPE_CHECKING:
    from .persistence.project.repository_generation import (
        ProjectGenerationRepository as GenerationRunRepository,
    )

from .runtime_secrets import RunSecretLeaser
from .work_unit_execution import DurableUnitExecutor


class DurableWorkUnitRunner:
    """Own stage ordering, scope-frozen reuse, aggregate seals and run release."""

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
        run: GenerationRun,
        *,
        adapter: ProviderAdapter,
        model: str,
        profile: ProviderSnapshot | TextProviderProfileSnapshot,
        cancellation: Event,
        repair_scope: WorkUnitRepairScope | None = None,
    ) -> RunExecutionResult:
        """Run exact units, returning only repository-owned aggregate IDs."""

        unit_executor = DurableUnitExecutor(
            self.repository, self.secrets, self.renderer
        )
        generation_plan = self.repository.get_generation_plan(run.id)
        story_graph_topology = self.repository.get_story_graph_topology(run.id)
        brief = run.canonical_snapshot.brief
        sealed_payloads: dict[StageName, StagePayload] = {}
        sealed_ids: list[str] = []
        try:
            for stage in run.requested_stages:
                if self._cancelled(run.id, cancellation):
                    return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
                existing = self._sealed_stage(run.id, stage)
                if existing is not None:
                    sealed_payloads[stage] = stage_payload_model(
                        stage, schema_version=2
                    ).model_validate(existing.payload)
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
                        # The scope authorizes the target plus only siblings
                        # that were still queued in the quarantined parent.
                        # Zero is valid after a crash that happened after all
                        # child candidates committed but before aggregation.
                        unresolved = [
                            unit.unit_id
                            for unit in stage_plan.work_units
                            if unit.unit_id not in candidates
                        ]
                        parent_units = {
                            unit.id: unit
                            for unit in self.repository.list_generation_work_units(
                                repair_scope.parent_run_id
                            )
                        }
                        allowed = {stable_hash(repair_scope.target_selector)}
                        allowed.update(
                            stable_hash(parent_units[work_unit_id].selector)
                            for work_unit_id in repair_scope.pending_sibling_work_unit_ids
                        )
                        unresolved_selectors = {
                            stable_hash(
                                next(
                                    unit.selector
                                    for unit in stage_plan.work_units
                                    if unit.unit_id == work_unit_id
                                )
                            )
                            for work_unit_id in unresolved
                        }
                        if not unresolved_selectors <= allowed:
                            raise ValueError(
                                "exact repair scope leaves an unauthorized target-stage work unit unresolved"
                            )
                for work_unit in stage_plan.work_units:
                    if work_unit.unit_id in candidates:
                        continue
                    if self._cancelled(run.id, cancellation):
                        return RunExecutionResult(sealed_aggregate_ids=sealed_ids)
                    try:
                        candidate_id = unit_executor.execute(
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
                            for attempt in self.repository.get_run_trace(
                                run.id
                            ).attempts
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
                sealed_payloads[stage] = stage_payload_model(
                    stage, schema_version=2
                ).model_validate(aggregate.payload)
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

    def _stage_dependencies(
        self,
        run: GenerationRun,
        stage: StageName,
        sealed_payloads: Mapping[StageName, StagePayload],
        *,
        repair_scope: WorkUnitRepairScope | None = None,
    ) -> dict[StageName, StagePayload]:
        if repair_scope is not None:
            # The target stage may depend on parent-run output that was sealed
            # but never canonically installed after quarantine.  Only the
            # repository can resolve that immutable boundary; later child
            # stages resolve exclusively through child-local seals.
            return self.repository.get_repair_stage_dependencies(
                run.id,
                stage,
            )
        ordered = (
            StageName.STORY_BIBLE,
            StageName.STORY_GRAPH,
            StageName.SCENE_BEATS,
            StageName.STORYBOARD,
        )
        dependencies: dict[StageName, StagePayload] = {}
        requested = set(run.requested_stages)
        for upstream in ordered[: ordered.index(stage)]:
            if upstream in requested:
                payload = sealed_payloads.get(upstream)
                if payload is None:
                    raise ValueError(
                        f"{stage.value} cannot run before {upstream.value} is sealed"
                    )
                dependencies[upstream] = payload
            else:
                dependencies[upstream] = self.repository.get_snapshot_stage_payload(
                    run.id, upstream
                )
        return dependencies

    def _get_stage_plan(
        self,
        run: GenerationRun,
        stage: StageName,
        *,
        dependencies: Mapping[StageName, StagePayload],
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
                raise ValueError(
                    "repair scope has more than one reuse binding for a work unit"
                )
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
        return next(
            (seal for seal in trace.sealed_aggregates if seal.stage == stage), None
        )

    def _cancelled(self, run_id: str, cancellation: Event) -> bool:
        return (
            cancellation.is_set()
            or self.repository.get_run(run_id).status == RunStatus.CANCEL_REQUESTED
        )
