"""Application bridge from durable Plotloom runs to the prompt-generation subsystem.

The generation package deliberately knows nothing about projects or SQLite.
This module bridges a frozen canonical run to either the durable bounded-unit
runner or the explicitly isolated historical repair flow.
"""

from __future__ import annotations

import json
from threading import Event, RLock
from typing import TYPE_CHECKING, Any, Callable, Mapping, Protocol

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
)
from .artifacts import RunEvidenceArtifactStore
from .generation.contracts import (
    ExtractionPolicy,
    GenerationAttempt as PromptAttempt,
    ProviderCapabilities,
    QuarantineRecord,
    RunStatus as PromptRunStatus,
    ValidationIssue,
    ReasoningMode,
    RequestExtension,
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
from .exceptions import (
    InvalidTransitionError,
    NotFoundError,
    QuarantinedOutputError,
    SchemaResetRequiredError,
)
from .persistence.codec import stable_hash
from .provider_profiles import (
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
    is_v2_snapshot,
    is_v3_snapshot,
)
from .text_adapters import DEFAULT_TEXT_ADAPTER_REGISTRY
from .runtime import GenerationEngine, RunContext, RunExecutionResult
from .work_unit_pipeline import DurableWorkUnitRunner

if TYPE_CHECKING:
    from .persistence.project.repository_generation import (
        ProjectGenerationRepository as GenerationRunRepository,
    )


class RunSecretBroker:
    """Resolve server credentials and per-run browser overrides without storage.

    Only opaque leases leave this object. Run overrides are removed after the
    run ends, and neither names nor values are included in persistence models.
    """

    def __init__(
        self,
        server_text_key: str | None = None,
        *,
        server_profile_keys: Mapping[str, str] | None = None,
        server_key_resolver: Callable[[str], str | None] | None = None,
    ) -> None:
        self._vault = InMemorySecretVault()
        self._lock = RLock()
        self._run_aliases: dict[str, tuple[str, str]] = {}
        self._server_aliases: dict[str, str] = {}
        self._server_key_resolver = server_key_resolver
        if server_text_key:
            self._server_aliases["default"] = "server:default:text"
            self._vault.put(self._server_aliases["default"], server_text_key)
        for profile_id, value in (server_profile_keys or {}).items():
            normalized = value.strip()
            if not normalized:
                continue
            alias = f"server:{profile_id}:text"
            self._server_aliases[profile_id] = alias
            self._vault.put(alias, normalized)

    def server_key_available(self, profile_id: str = "default") -> bool:
        with self._lock:
            return self._server_alias_for(profile_id) is not None

    def _server_alias_for(self, profile_id: str) -> str | None:
        alias = self._server_aliases.get(profile_id)
        if alias is not None:
            return alias
        if self._server_key_resolver is None:
            return None
        value = (self._server_key_resolver(profile_id) or "").strip()
        if not value:
            return None
        alias = f"server:{profile_id}:text"
        self._vault.put(alias, value)
        self._server_aliases[profile_id] = alias
        return alias

    def register_run_override(
        self,
        run_id: str,
        value: str | None,
        *,
        profile_id: str = "default",
    ) -> None:
        normalized = (value or "").strip()
        if not normalized:
            return
        alias = f"run:{run_id}:text"
        with self._lock:
            previous = self._run_aliases.get(run_id)
            if previous:
                self._vault.remove(previous[0])
            self._vault.put(alias, normalized)
            self._run_aliases[run_id] = (alias, profile_id)

    def lease_for_run(
        self,
        run_id: str,
        *,
        auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER,
        profile_id: str = "default",
    ) -> SecretLease | None:
        if auth_mode == ProviderAuthMode.NONE:
            return None
        with self._lock:
            override = self._run_aliases.get(run_id)
            if override is not None and override[1] != profile_id:
                raise SecretLeaseError("Run session credential is bound to a different provider profile")
            alias = override[0] if override is not None else self._server_alias_for(profile_id)
            if alias is None:
                raise SecretLeaseError(
                    f"No text-provider key is available for profile {profile_id!r}; "
                    "configure its profile-specific environment key or provide a browser-session key"
                )
            return self._vault.lease(alias, ttl_seconds=900, max_uses=1)

    def lease_for_profile(
        self,
        profile_id: str,
        *,
        auth_mode: ProviderAuthMode = ProviderAuthMode.BEARER,
    ) -> SecretLease | None:
        """Lease a server-owned key for a secret-free connection probe."""

        if auth_mode == ProviderAuthMode.NONE:
            return None
        with self._lock:
            alias = self._server_alias_for(profile_id)
            if alias is None:
                raise SecretLeaseError(
                    f"No text-provider key is available for profile {profile_id!r}"
                )
            return self._vault.lease(alias, ttl_seconds=60, max_uses=1)

    def release_run(self, run_id: str) -> None:
        with self._lock:
            binding = self._run_aliases.pop(run_id, None)
            if binding:
                self._vault.remove(binding[0])

    def close(self) -> None:
        with self._lock:
            self._run_aliases.clear()
            self._server_aliases.clear()
            self._server_key_resolver = None
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
        snapshot: ProviderSnapshot | TextProviderProfileSnapshot | TextProviderProfileSnapshotV3
        if is_v3_snapshot(provider_snapshot):
            snapshot = TextProviderProfileSnapshotV3.model_validate(provider_snapshot)
            return DEFAULT_TEXT_ADAPTER_REGISTRY.resolve(snapshot), snapshot.text_model
        if is_v2_snapshot(provider_snapshot):
            snapshot = TextProviderProfileSnapshot.model_validate(provider_snapshot)
        else:
            snapshot = ProviderSnapshot.model_validate(provider_snapshot)
        capabilities = ProviderCapabilities.model_validate(
            snapshot.text_capabilities.model_dump()
        )
        adapter = OpenAICompatibleAdapter(
            name=snapshot.text_provider,
            base_url=snapshot.text_base_url,
            capabilities=capabilities,
            auth_mode=(
                snapshot.text_auth_mode.value
                if isinstance(snapshot.text_auth_mode, ProviderAuthMode)
                else snapshot.text_auth_mode
            ),
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
        repository: "GenerationRunRepository",
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
        repository: "GenerationRunRepository",
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
        self._record_project_run_evidence(run, context)
        # Exact work-unit repair has a separate lineage contract.  It only
        # consumes repository-frozen scope and reuse bindings; a legacy repair
        # keeps the historic stage-level bridge below.  The existence of the
        # scope is the discriminator rather than a mutable request flag.
        if run.kind == RunKind.REPAIR:
            if run.work_unit_repair_scope_id is not None:
                try:
                    repair_scope = self.repository.get_work_unit_repair_scope(run.id)
                except NotFoundError as error:
                    # A row-linked exact child without its scope is corrupt
                    # durable lineage, never a request to fall back to the
                    # historical stage-repair interpreter.
                    raise InvalidTransitionError(
                        "exact repair run is missing its immutable scope"
                    ) from error
                if run.parent_run_id != repair_scope.parent_run_id:
                    raise InvalidTransitionError(
                        "exact repair scope is not bound to the child run parent"
                    )
                if run.work_unit_repair_scope_id != repair_scope.child_run_id:
                    raise InvalidTransitionError(
                        "exact repair scope identity does not match its child run"
                    )
                profile: ProviderSnapshot | TextProviderProfileSnapshot
                if is_v3_snapshot(run.provider_snapshot):
                    profile = TextProviderProfileSnapshotV3.model_validate(run.provider_snapshot)
                elif is_v2_snapshot(run.provider_snapshot):
                    profile = TextProviderProfileSnapshot.model_validate(run.provider_snapshot)
                else:
                    profile = ProviderSnapshot.model_validate(run.provider_snapshot)
                adapter, model = self.provider_resolver.resolve(run.provider_snapshot)
                return DurableWorkUnitRunner(
                    self.repository, self.secrets, self.renderer
                ).execute_exact_repair(
                    run,
                    repair_scope=repair_scope,
                    adapter=adapter,
                    model=model,
                    profile=profile,
                    cancellation=cancellation,
                )
            # Older databases/repository adapters contain only the legacy
            # bridge. A repair without an exact scope retains that behavior.
            if run.parent_run_id is None or run.repair_source is None:
                raise ValueError("legacy repair run is missing frozen parent evidence")
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
        profile: ProviderSnapshot | TextProviderProfileSnapshot
        if is_v3_snapshot(run.provider_snapshot):
            profile = TextProviderProfileSnapshotV3.model_validate(run.provider_snapshot)
        elif is_v2_snapshot(run.provider_snapshot):
            profile = TextProviderProfileSnapshot.model_validate(run.provider_snapshot)
        else:
            profile = ProviderSnapshot.model_validate(run.provider_snapshot)
        adapter, model = self.provider_resolver.resolve(run.provider_snapshot)
        return DurableWorkUnitRunner(self.repository, self.secrets, self.renderer).execute(
            run,
            adapter=adapter,
            model=model,
            profile=profile,
            cancellation=cancellation,
        )

    @staticmethod
    def _record_project_run_evidence(run: GenerationRun, context: RunContext) -> None:
        """Make the production runner's immutable input envelope portable.

        The capability is deliberately absent from generic and historical
        artifact stores, so this remains a project-folder runtime boundary.
        """

        if not isinstance(context.artifacts, RunEvidenceArtifactStore):
            return
        envelope = {
            "formatVersion": 1,
            "runId": run.id,
            "projectId": run.project_id,
            "kind": run.kind.value,
            "requestedStages": [stage.value for stage in run.requested_stages],
            "providerSnapshot": run.provider_snapshot,
            "canonicalSnapshotHash": run.canonical_snapshot.snapshot_hash,
        }
        context.artifacts.record_run_evidence(
            json.dumps(
                envelope, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
        )

    def _execute_legacy_repair(
        self,
        run: GenerationRun,
        context: RunContext,
        cancellation: Event,
    ) -> RunExecutionResult:
        del context  # provider/artifact ports are used by media; text uses typed adapters here.
        profile: ProviderSnapshot | TextProviderProfileSnapshot
        if is_v3_snapshot(run.provider_snapshot):
            profile = TextProviderProfileSnapshotV3.model_validate(run.provider_snapshot)
        elif is_v2_snapshot(run.provider_snapshot):
            profile = TextProviderProfileSnapshot.model_validate(run.provider_snapshot)
        else:
            profile = ProviderSnapshot.model_validate(run.provider_snapshot)
        adapter, model = self.provider_resolver.resolve(run.provider_snapshot)
        if isinstance(profile, TextProviderProfileSnapshot):
            request_extension, reasoning_mode, extraction_policy = profile.request_contract()
        else:
            request_extension = RequestExtension.NONE
            reasoning_mode = ReasoningMode.PROVIDER_DEFAULT
            extraction_policy = ExtractionPolicy()
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
                        auth_mode=ProviderAuthMode(profile.text_auth_mode),
                        profile_id=profile.profile_id,
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
                            extraction_policy=extraction_policy,
                            request_extension=request_extension,
                            reasoning_mode=reasoning_mode,
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
                            extraction_policy=extraction_policy,
                            request_extension=request_extension,
                            reasoning_mode=reasoning_mode,
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
        # Historical whole-stage candidates did not record a canonical schema
        # version. Guessing here could reinterpret V1 free-text dialogue/audio
        # as the V2 authoring contract, so legacy repair fails closed. The
        # immutable artifact remains available through the trace for review.
        raise SchemaResetRequiredError(stage=stage, schema_version=None)

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
        extraction_policy: ExtractionPolicy,
        request_extension: RequestExtension,
        reasoning_mode: ReasoningMode,
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
            extraction_policy=extraction_policy,
            request_extension=request_extension,
            reasoning_mode=reasoning_mode,
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
