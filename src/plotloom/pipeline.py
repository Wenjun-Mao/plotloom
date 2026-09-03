"""Application bridge from durable Plotloom runs to the prompt-generation subsystem.

The generation package deliberately knows nothing about projects or SQLite.
This module bridges a frozen canonical run to either the durable bounded-unit
runner or the explicitly isolated historical repair flow.
"""

from __future__ import annotations

from threading import Event, RLock
from typing import Any, Mapping, Protocol

from .domain import (
    Artifact,
    ArtifactKind,
    AttemptStatus,
    GenerationRun,
    ProjectBrief,
    ProviderAuthMode,
    ProviderSnapshot,
    RunKind,
    SceneBeatPlan,
    StageName,
    StoryBible,
    StoryGraph,
    stage_payload_model,
)
from .generation.contracts import (
    GenerationAttempt as PromptAttempt,
    ProviderCapabilities,
    QuarantineRecord,
    RunStatus as PromptRunStatus,
    ValidationIssue,
)
from .generation.exceptions import GenerationRunFailed, SecretLeaseError
from .generation.fragments import StoryBibleFragment, StoryGraphFragment
from .generation.orchestration import (
    AttemptLifecycleObserver,
    GenerationOrchestrator,
    InMemoryQuarantineStore,
)
from .generation.prompts import PromptRenderer
from .generation.providers import OpenAICompatibleAdapter, ProviderAdapter
from .generation.secrets import InMemorySecretVault, SecretLease
from .generation.validation import CanonicalStageValidationAdapter
from .exceptions import InvalidTransitionError, QuarantinedOutputError
from .persistence import SQLiteRepository, stable_hash
from .runtime import GenerationEngine, RunContext, RunExecutionResult
from .work_unit_pipeline import DurableWorkUnitRunner


class RunSecretBroker:
    """Resolve server credentials and per-run browser overrides without storage.

    Only opaque leases leave this object. Run overrides are removed after the
    run ends, and neither names nor values are included in persistence models.
    """

    def __init__(self, server_text_key: str | None = None) -> None:
        self._vault = InMemorySecretVault()
        self._lock = RLock()
        self._run_aliases: dict[str, str] = {}
        self._server_alias: str | None = None
        if server_text_key:
            self._server_alias = "server:text"
            self._vault.put(self._server_alias, server_text_key)

    @property
    def server_key_available(self) -> bool:
        return self._server_alias is not None

    def register_run_override(self, run_id: str, value: str | None) -> None:
        normalized = (value or "").strip()
        if not normalized:
            return
        alias = f"run:{run_id}:text"
        with self._lock:
            previous = self._run_aliases.get(run_id)
            if previous:
                self._vault.remove(previous)
            self._vault.put(alias, normalized)
            self._run_aliases[run_id] = alias

    def lease_for_run(
        self,
        run_id: str,
        *,
        auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER,
    ) -> SecretLease | None:
        if auth_mode == ProviderAuthMode.NONE:
            return None
        with self._lock:
            alias = self._run_aliases.get(run_id) or self._server_alias
            if alias is None:
                raise SecretLeaseError(
                    "No text-provider key is available; configure TEXT_MODEL_API_KEY "
                    "or provide a browser-session key"
                )
            return self._vault.lease(alias, ttl_seconds=900, max_uses=1)

    def release_run(self, run_id: str) -> None:
        with self._lock:
            alias = self._run_aliases.pop(run_id, None)
            if alias:
                self._vault.remove(alias)

    def close(self) -> None:
        with self._lock:
            self._run_aliases.clear()
            self._server_alias = None
            self._vault.clear()


class TextProviderResolver(Protocol):
    """Build one adapter from the public settings frozen on a run."""

    def resolve(self, provider_snapshot: Mapping[str, Any]) -> tuple[ProviderAdapter, str]: ...


class SnapshotTextProviderResolver:
    """Resolve only from enqueue-time public settings plus runtime defaults.

    Reading mutable provider settings inside a worker would let a later settings
    edit silently change a queued run.  The API therefore stores a secret-free
    provider snapshot on each run, and this resolver consumes only that snapshot.
    """

    def resolve(self, provider_snapshot: Mapping[str, Any]) -> tuple[ProviderAdapter, str]:
        snapshot = ProviderSnapshot.model_validate(provider_snapshot)
        capabilities = ProviderCapabilities.model_validate(
            snapshot.text_capabilities.model_dump()
        )
        adapter = OpenAICompatibleAdapter(
            name=snapshot.text_provider,
            base_url=snapshot.text_base_url,
            capabilities=capabilities,
            auth_mode=snapshot.text_auth_mode.value,
            connect_timeout_seconds=snapshot.text_connect_timeout_seconds,
            timeout_seconds=snapshot.text_attempt_timeout_seconds,
        )
        return adapter, snapshot.text_model


class _DurableTraceObserver(AttemptLifecycleObserver):
    """Persist each attempt boundary before orchestration can advance.

    Candidate artifacts remain non-canonical. The runner still installs the
    complete requested stage range atomically only after every stage validates.
    """

    def __init__(
        self,
        repository: SQLiteRepository,
        *,
        run_id: str,
        stage: StageName,
        attempt_id: str,
    ) -> None:
        self.repository = repository
        self.run_id = run_id
        self.stage = stage
        self.attempt_id = attempt_id

    def prompt_prepared(self, attempt: PromptAttempt) -> None:
        content = {
            "trace": attempt.prompt_trace.model_dump(mode="json"),
            "messages": [
                message.model_dump(mode="json") for message in attempt.rendered_messages
            ],
            "schemaId": attempt.schema_id,
            "structuredOutputMode": attempt.structured_output_mode,
            "nativeJsonSchemaUsed": attempt.native_json_schema_used,
            "provider": attempt.provider,
            "model": attempt.model,
        }
        self._persist(ArtifactKind.PROMPT, content)

    def response_extracted(self, attempt: PromptAttempt) -> None:
        content = {
            "rawResponse": attempt.raw_response,
            "responseHash": attempt.response_hash,
            "providerRequestId": attempt.provider_request_id,
            "finishReason": attempt.finish_reason,
            "usage": {
                "inputTokens": attempt.usage.input_tokens,
                "outputTokens": attempt.usage.output_tokens,
            },
            "transformations": list(attempt.transformations),
        }
        self._persist(ArtifactKind.RESPONSE, content)

    def validation_completed(
        self,
        attempt: PromptAttempt,
        candidate: Any | None,
    ) -> None:
        content = {
            "accepted": attempt.validation_accepted,
            "issues": [
                issue.model_dump(mode="json") for issue in attempt.validation_issues
            ],
            "transformations": list(attempt.transformations),
            "errorType": attempt.error_type,
            "error": attempt.error_message,
        }
        self._persist(ArtifactKind.VALIDATION, content)
        if candidate is not None:
            candidate_content = candidate.model_dump(mode="json", by_alias=False)
            self._persist(ArtifactKind.CANDIDATE, candidate_content)

    def _persist(self, kind: ArtifactKind, content: Any) -> None:
        self.repository.add_artifact(
            Artifact(
                run_id=self.run_id,
                attempt_id=self.attempt_id,
                stage=self.stage,
                kind=kind,
                content=content,
                content_hash=stable_hash(content),
            )
        )


class PipelineEngine(GenerationEngine):
    """Generate or explicitly repair canonical stages in dependency order."""

    def __init__(
        self,
        repository: SQLiteRepository,
        provider_resolver: TextProviderResolver,
        secrets: RunSecretBroker,
        *,
        renderer: PromptRenderer | None = None,
    ) -> None:
        self.repository = repository
        self.provider_resolver = provider_resolver
        self.secrets = secrets
        self.renderer = renderer or PromptRenderer()

    def execute(
        self,
        run: GenerationRun,
        context: RunContext,
        cancellation: Event,
    ) -> RunExecutionResult:
        # Exact work-unit repair has a separate lineage contract: the old
        # repair flow reuses historical, unsealed candidates and cannot safely
        # manufacture StagePlan-bound fragments from them.  Keep it on the
        # explicit compatibility path until targeted work-unit repair exists;
        # ordinary production runs always use seals below.
        if run.kind == RunKind.REPAIR:
            if run.parent_run_id is None or run.repair_source is None:
                raise ValueError("repair run is missing frozen parent evidence")
            failed_attempt = next(
                (
                    attempt
                    for attempt in self.repository.get_run_trace(run.parent_run_id).attempts
                    if attempt.id == run.repair_source.failed_attempt_id
                ),
                None,
            )
            if failed_attempt is None:
                raise ValueError("repair run references a missing failed attempt")
            if failed_attempt.work_unit_id is not None:
                raise InvalidTransitionError(
                    "exact work-unit repair is not implemented; start a rebuild from the failed stage instead"
                )
            return self._execute_legacy_repair(run, context, cancellation)
        profile = ProviderSnapshot.model_validate(run.provider_snapshot)
        adapter, model = self.provider_resolver.resolve(run.provider_snapshot)
        return DurableWorkUnitRunner(self.repository, self.secrets, self.renderer).execute(
            run,
            adapter=adapter,
            model=model,
            profile=profile,
            cancellation=cancellation,
        )

    def _execute_legacy_repair(
        self,
        run: GenerationRun,
        context: RunContext,
        cancellation: Event,
    ) -> RunExecutionResult:
        del context  # provider/artifact ports are used by media; text uses typed adapters here.
        profile = ProviderSnapshot.model_validate(run.provider_snapshot)
        adapter, model = self.provider_resolver.resolve(run.provider_snapshot)
        quarantine = InMemoryQuarantineStore()
        orchestrator = GenerationOrchestrator(
            renderer=self.renderer,
            provider=adapter,
            quarantine=quarantine,
        )
        brief = run.canonical_snapshot.brief
        candidates: dict[StageName, dict[str, Any]] = {}
        canonical: dict[StageName, Any] = {}

        try:
            for stage in run.requested_stages:
                if cancellation.is_set():
                    return RunExecutionResult(stage_payloads=candidates)
                if (
                    run.kind == RunKind.REPAIR
                    and run.repair_stage is not None
                    and run.requested_stages.index(stage) < run.requested_stages.index(run.repair_stage)
                ):
                    reused, source_artifact_id = self._parent_candidate(run, stage)
                    canonical[stage] = reused
                    candidate_data = reused.model_dump(mode="json", by_alias=False)
                    candidates[stage] = candidate_data
                    self.repository.add_artifact(
                        Artifact(
                            run_id=run.id,
                            source_artifact_id=source_artifact_id,
                            stage=stage,
                            kind=ArtifactKind.CANDIDATE,
                            content=candidate_data,
                            content_hash=stable_hash(candidate_data),
                        )
                    )
                    continue
                self._load_unrequested_upstream(run, stage, canonical)
                validator = self._validator(stage, brief, canonical)
                persisted_attempt = self.repository.create_attempt(
                    run.id,
                    stage,
                    provider=adapter.name,
                    model=model,
                )
                observer = _DurableTraceObserver(
                    self.repository,
                    run_id=run.id,
                    stage=stage,
                    attempt_id=persisted_attempt.id,
                )
                try:
                    lease = self.secrets.lease_for_run(
                        run.id,
                        auth_mode=profile.text_auth_mode,
                    )
                    if run.kind == RunKind.REPAIR and stage == run.repair_stage:
                        result = self._repair(
                            run,
                            stage,
                            validator,
                            model,
                            lease,
                            orchestrator,
                            quarantine,
                            observer,
                            temperature=profile.text_temperature,
                            max_output_tokens=profile.text_max_output_tokens,
                        )
                    else:
                        result = orchestrator.generate(
                            prompt_id=stage.value,
                            variables=self._variables(stage, brief, canonical, run.instructions),
                            validator=validator,
                            model=model,
                            secret=lease,
                            temperature=profile.text_temperature,
                            max_output_tokens=profile.text_max_output_tokens,
                            validation_metadata={"projectId": run.project_id, "runId": run.id},
                            observer=observer,
                        )
                except GenerationRunFailed as error:
                    prompt_run = error.run
                    self.repository.finish_attempt(
                        persisted_attempt.id,
                        AttemptStatus.FAILED,
                        error=str(error),
                    )
                    if prompt_run.status == PromptRunStatus.QUARANTINED:
                        raise QuarantinedOutputError(str(error), artifacts=[]) from error
                    raise
                except Exception as error:
                    self.repository.finish_attempt(
                        persisted_attempt.id,
                        AttemptStatus.FAILED,
                        error=str(error),
                    )
                    raise

                parsed = result.value
                self.repository.finish_attempt(persisted_attempt.id, AttemptStatus.SUCCEEDED)
                canonical[stage] = parsed
                candidates[stage] = parsed.model_dump(mode="json", by_alias=False)

            return RunExecutionResult(stage_payloads=candidates)
        finally:
            self.secrets.release_run(run.id)

    def _parent_candidate(self, run: GenerationRun, stage: StageName) -> tuple[Any, str]:
        if not run.parent_run_id or run.repair_source is None:
            raise ValueError("repair run is missing frozen parent evidence")
        source_id = run.repair_source.reused_candidate_artifact_ids.get(stage)
        if source_id is None:
            raise ValueError(f"repair run has no frozen candidate for {stage.value}")
        source = self.repository.get_artifact(source_id)
        if (
            source.run_id != run.parent_run_id
            or source.stage != stage
            or source.kind != ArtifactKind.CANDIDATE
        ):
            raise ValueError(f"frozen candidate evidence is invalid for {stage.value}")
        # New ordinary runs retain a whole-stage fragment for Bible/Graph;
        # compatibility repair predates exact unit repair and needs the payload
        # that fragment represents.  Do not attempt to flatten multi-unit
        # SceneBeats/Storyboard candidates here.
        if stage == StageName.STORY_BIBLE:
            try:
                return StoryBibleFragment.model_validate(source.content).payload, source.id
            except Exception:  # historical candidate payload, not a fragment
                pass
        if stage == StageName.STORY_GRAPH:
            try:
                return StoryGraphFragment.model_validate(source.content).payload, source.id
            except Exception:  # historical candidate payload, not a fragment
                pass
        return stage_payload_model(stage).model_validate(source.content), source.id

    def _repair(
        self,
        run: GenerationRun,
        stage: StageName,
        validator: CanonicalStageValidationAdapter,
        model: str,
        lease: SecretLease | None,
        orchestrator: GenerationOrchestrator,
        quarantine: InMemoryQuarantineStore,
        observer: AttemptLifecycleObserver,
        *,
        temperature: float,
        max_output_tokens: int,
    ) -> Any:
        if not run.parent_run_id or run.repair_source is None:
            raise ValueError("repair run is missing frozen parent evidence")
        source_response = self.repository.get_artifact(run.repair_source.response_artifact_id)
        source_validation = self.repository.get_artifact(run.repair_source.validation_artifact_id)
        if (
            source_response.run_id != run.parent_run_id
            or source_response.attempt_id != run.repair_source.failed_attempt_id
            or source_response.stage != stage
            or source_response.kind != ArtifactKind.RESPONSE
            or source_validation.run_id != run.parent_run_id
            or source_validation.attempt_id != run.repair_source.failed_attempt_id
            or source_validation.stage != stage
            or source_validation.kind != ArtifactKind.VALIDATION
        ):
            raise ValueError("frozen repair response/validation evidence is invalid")
        response_content = source_response.content if isinstance(source_response.content, dict) else {}
        validation_content = source_validation.content if isinstance(source_validation.content, dict) else {}
        issues = tuple(
            ValidationIssue.model_validate(item)
            for item in validation_content.get("issues", [])
            if isinstance(item, dict)
        )
        quarantine_id = f"artifact:{source_response.id}"
        if quarantine.get(quarantine_id) is None:
            quarantine.put(
                QuarantineRecord(
                    quarantine_id=quarantine_id,
                    run_id=run.parent_run_id,
                    attempt_id=source_response.attempt_id or "unknown",
                    stage=stage.value,
                    schema_id=validator.schema_id,
                    reason=str(validation_content.get("error") or "explicit repair requested"),
                    response_hash=source_response.content_hash,
                    raw_response=self._repair_raw_response(response_content),
                    validation_issues=issues,
                )
            )
        return orchestrator.repair(
            quarantine_id=quarantine_id,
            parent_run_id=run.parent_run_id,
            validator=validator,
            model=model,
            secret=lease,
            instructions=run.instructions,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            validation_metadata={"projectId": run.project_id, "runId": run.id},
            observer=observer,
        )

    @staticmethod
    def _repair_raw_response(response_content: Mapping[str, Any]) -> str:
        """Read either historical text evidence or the new durable envelope."""

        raw = response_content.get("rawResponse")
        if isinstance(raw, str):
            return raw
        if isinstance(raw, Mapping):
            choices = raw.get("choices")
            if isinstance(choices, list) and choices and isinstance(choices[0], Mapping):
                message = choices[0].get("message")
                if isinstance(message, Mapping) and isinstance(message.get("content"), str):
                    return message["content"]
        return ""

    def _load_unrequested_upstream(
        self,
        run: GenerationRun,
        stage: StageName,
        canonical: dict[StageName, Any],
    ) -> None:
        ordered = (
            StageName.STORY_BIBLE,
            StageName.STORY_GRAPH,
            StageName.SCENE_BEATS,
            StageName.STORYBOARD,
        )
        for upstream in ordered[: ordered.index(stage)]:
            if upstream not in canonical:
                canonical[upstream] = self.repository.get_snapshot_stage_payload(run.id, upstream)

    @staticmethod
    def _validator(
        stage: StageName,
        brief: ProjectBrief,
        canonical: dict[StageName, Any],
    ) -> CanonicalStageValidationAdapter:
        return CanonicalStageValidationAdapter(
            stage,
            brief=brief,
            bible=canonical.get(StageName.STORY_BIBLE),
            graph=canonical.get(StageName.STORY_GRAPH),
            scene_beats=canonical.get(StageName.SCENE_BEATS),
        )

    @staticmethod
    def _variables(
        stage: StageName,
        brief: ProjectBrief,
        canonical: dict[StageName, Any],
        instructions: str | None,
    ) -> dict[str, Any]:
        brief_data = brief.model_dump(mode="json", by_alias=True)
        extra = {"runInstructions": instructions} if instructions else {}
        if stage == StageName.STORY_BIBLE:
            return {
                "project_input": brief_data,
                "creative_constraints": extra,
            }
        if stage == StageName.STORY_GRAPH:
            return {
                "story_bible": canonical[StageName.STORY_BIBLE],
                "graph_constraints": {
                    "nodeBudget": brief.node_budget,
                    "maxOutDegree": brief.max_out_degree,
                    "endingCount": brief.ending_count,
                    "decisionPointsPerPath": brief.decision_points_per_path,
                    "desiredJoinCount": brief.desired_join_count,
                    **extra,
                },
            }
        if stage == StageName.SCENE_BEATS:
            return {
                "story_bible": canonical[StageName.STORY_BIBLE],
                "story_graph": canonical[StageName.STORY_GRAPH],
                "beat_constraints": {
                    "targetPlaythroughSeconds": brief.target_playthrough_seconds,
                    "language": brief.language,
                    "oneVisibleChangePerBeat": True,
                    **extra,
                },
            }
        return {
            "story_bible": canonical[StageName.STORY_BIBLE],
            "story_graph": canonical[StageName.STORY_GRAPH],
            "scene_beats": canonical[StageName.SCENE_BEATS],
            "storyboard_constraints": {
                "aspectRatio": brief.aspect_ratio,
                "visualStyle": brief.visual_style,
                "shotsPerSceneMin": brief.shots_per_scene_min,
                "shotsPerSceneMax": brief.shots_per_scene_max,
                **extra,
            },
        }
