"""Application bridge from durable Plotloom runs to the prompt-generation subsystem.

The generation package deliberately knows nothing about projects or SQLite.
This module bridges frozen canonical runs and exact work-unit repairs to the
durable bounded-unit runner.
"""

from __future__ import annotations

import json
from threading import Event, RLock
from typing import TYPE_CHECKING, Any, Callable, Mapping, Protocol

from .artifacts import RunEvidenceArtifactStore
from .domain import (
    GenerationRun,
    ProviderAuthMode,
    ProviderSnapshot,
    RunKind,
)
from .exceptions import (
    InvalidTransitionError,
    NotFoundError,
)
from .generation.contracts import (
    ProviderCapabilities,
)
from .generation.exceptions import SecretLeaseError
from .generation.prompts import PromptRenderer
from .generation.providers import OpenAICompatibleAdapter, ProviderAdapter
from .generation.secrets import InMemorySecretVault, SecretLease
from .provider_profiles import (
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
    is_v2_snapshot,
    is_v3_snapshot,
)
from .runtime import GenerationEngine, RunContext, RunExecutionResult
from .text_adapters import DEFAULT_TEXT_ADAPTER_REGISTRY
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
            raise InvalidTransitionError(
                "scope-less stage repair is retired; exact repair requires an immutable scope"
            )
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
