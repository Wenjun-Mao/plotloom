"""Composition and lineage admission for durable generation runs."""

from __future__ import annotations

import json
from threading import Event
from typing import TYPE_CHECKING

from .artifacts import RunEvidenceArtifactStore
from plotloom.run_contracts import GenerationRun, RunKind
from plotloom.provider_contracts import ProviderSnapshot
from .exceptions import (
    InvalidTransitionError,
    NotFoundError,
)
from .generation.prompts import PromptRenderer
from .provider_profiles import (
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
    is_v2_snapshot,
    is_v3_snapshot,
)
from .runtime import GenerationEngine, RunContext, RunExecutionResult
from .runtime_secrets import RunSecretBroker
from .text_provider_resolution import TextProviderResolver
from .work_unit_pipeline import DurableWorkUnitRunner

if TYPE_CHECKING:
    from .persistence.project.repository_generation import (
        ProjectGenerationRepository as GenerationRunRepository,
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
        # consumes repository-frozen scope and reuse bindings. A missing or
        # corrupt scope always fails closed, before provider resolution.
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
                    profile = TextProviderProfileSnapshotV3.model_validate(
                        run.provider_snapshot
                    )
                elif is_v2_snapshot(run.provider_snapshot):
                    profile = TextProviderProfileSnapshot.model_validate(
                        run.provider_snapshot
                    )
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
            raise InvalidTransitionError(
                "scope-less stage repair is retired; exact repair requires an immutable scope"
            )
        profile: ProviderSnapshot | TextProviderProfileSnapshot
        if is_v3_snapshot(run.provider_snapshot):
            profile = TextProviderProfileSnapshotV3.model_validate(
                run.provider_snapshot
            )
        elif is_v2_snapshot(run.provider_snapshot):
            profile = TextProviderProfileSnapshot.model_validate(run.provider_snapshot)
        else:
            profile = ProviderSnapshot.model_validate(run.provider_snapshot)
        adapter, model = self.provider_resolver.resolve(run.provider_snapshot)
        return DurableWorkUnitRunner(
            self.repository, self.secrets, self.renderer
        ).execute(
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
