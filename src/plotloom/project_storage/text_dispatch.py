"""Project-scoped text-run creation, routing, and local-process dispatch."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import Future
from dataclasses import dataclass
from threading import RLock
from typing import Any

from ..artifacts import LocalArtifactStore
from ..domain import GenerationRun, RunKind, StageName, StartupRecoveryPlan
from ..exceptions import NotFoundError
from ..jobs import LifecycleJobRunner
from ..pipeline import PipelineEngine, RunSecretBroker, TextProviderResolver
from ..providers import ProviderPorts
from ..runtime import RunContext
from .composition import ProjectFolderStorage
from .project_handle import ProjectStore


@dataclass
class _ActiveRun:
    store: ProjectStore
    runner: LifecycleJobRunner


class ProjectRunDispatcher:
    """Dispatch only through the project identified by the application index.

    The application index is deliberately disposable: startup rebuilds it from
    validated manifests and project-local run rows. It is never consulted as
    canonical run evidence and a missing route never triggers a database-wide
    request-time search.
    """

    def __init__(
        self,
        storage: ProjectFolderStorage,
        *,
        provider_resolver: TextProviderResolver,
        secrets: RunSecretBroker,
        max_workers: int,
    ) -> None:
        self.storage = storage
        self.provider_resolver = provider_resolver
        self.secrets = secrets
        self.max_workers = max_workers
        self._active: dict[str, _ActiveRun] = {}
        self._lock = RLock()

    def rebuild_index(self) -> None:
        routes: list[tuple[str, str]] = []
        for home in self.storage.projects.discover():
            store = self.storage.projects.inspect(home.manifest.project_id)
            try:
                routes.extend(
                    (run_id, home.manifest.project_id)
                    for run_id in store.generation_run_ids_for_index()
                )
            finally:
                store.close()
        self.storage.application.replace_run_index(routes)

    def reconcile_startup(self) -> dict[str, StartupRecoveryPlan]:
        """Reconcile durable state without submitting any operation at startup."""

        plans: dict[str, StartupRecoveryPlan] = {}
        for home in self.storage.projects.discover():
            store = self.storage.projects.inspect(home.manifest.project_id)
            try:
                plans[home.manifest.project_id] = store.generation.reconcile_startup_jobs()
            finally:
                store.close()
        self.rebuild_index()
        return plans

    def create_run(
        self,
        project_id: str,
        *,
        kind: RunKind,
        requested_stages: Sequence[StageName],
        provider_snapshot: Mapping[str, Any],
        instructions: str | None = None,
    ) -> GenerationRun:
        store = self.storage.projects.open(project_id)
        try:
            store.require_recovery_acknowledged()
            with store.generation.admit_provider_snapshot(dict(provider_snapshot)):
                run = store.generation.create_run(
                    project_id,
                    kind,
                    requested_stages,
                    instructions=instructions,
                    provider_snapshot=dict(provider_snapshot),
                )
            self.storage.application.index_run(run.id, project_id)
            return run
        finally:
            store.close()

    def project_id_for_run(self, run_id: str) -> str:
        project_id = self.storage.application.project_for_run(run_id)
        if project_id is None:
            raise NotFoundError("generation run is not known by this application index")
        return project_id

    def create_repair(
        self,
        source_run_id: str,
        *,
        provider_snapshot: Mapping[str, Any],
        stage: StageName | None,
        instructions: str | None,
    ) -> GenerationRun:
        store = self.open_run_project(source_run_id)
        try:
            with store.generation.admit_provider_snapshot(dict(provider_snapshot)):
                run = store.generation.create_repair_run(
                    source_run_id,
                    stage=stage,
                    instructions=instructions,
                    provider_snapshot=dict(provider_snapshot),
                )
            self.storage.application.index_run(run.id, store.manifest.project_id)
            return run
        finally:
            store.close()

    def create_exact_repair(
        self, source_run_id: str, work_unit_id: str, *, idempotency_key: str
    ) -> tuple[GenerationRun, bool]:
        store = self.open_run_project(source_run_id)
        try:
            source = store.generation.get_run(source_run_id)
            with store.generation.admit_provider_snapshot(source.provider_snapshot):
                creation = store.generation.create_work_unit_repair_run(
                    source_run_id, work_unit_id, idempotency_key=idempotency_key
                )
            self.storage.application.index_run(creation.run.id, store.manifest.project_id)
            return creation.run, creation.created
        finally:
            store.close()

    def open_run_project(self, run_id: str) -> ProjectStore:
        return self.storage.projects.inspect(self.project_id_for_run(run_id))

    def submit(self, run_id: str, *, session_api_key: str | None = None) -> Future[GenerationRun]:
        with self._lock:
            existing = self._active.get(run_id)
            if existing is not None:
                return existing.runner.submit(run_id, session_api_key=session_api_key)
            project_id = self.project_id_for_run(run_id)
            store = self.storage.projects.open(project_id)
            runner = LifecycleJobRunner(
                store.generation,
                PipelineEngine(store.generation, self.provider_resolver, self.secrets),
                RunContext(
                    providers=ProviderPorts(),
                    artifacts=LocalArtifactStore(store.home / "runs"),
                ),
                max_workers=self.max_workers,
                secret_registrar=self.secrets,
            )
            try:
                future = runner.submit(run_id, session_api_key=session_api_key)
            except BaseException:
                runner.close()
                store.close()
                raise
            self._active[run_id] = _ActiveRun(store=store, runner=runner)
            future.add_done_callback(lambda _completed, resource_id=run_id: self._release(resource_id))
            return future

    def request_cancel(self, run_id: str) -> GenerationRun:
        with self._lock:
            active = self._active.get(run_id)
            if active is not None:
                return active.runner.request_cancel(run_id)
        store = self.open_run_project(run_id)
        try:
            return store.generation.cancel_run(run_id)
        finally:
            store.close()

    def _release(self, run_id: str) -> None:
        with self._lock:
            active = self._active.pop(run_id, None)
        if active is not None:
            # Completion callbacks run on the runner's worker thread; waiting
            # there would attempt to join the current worker.
            active.runner.close(wait=False)
            active.store.close()

    def close(self) -> None:
        with self._lock:
            active = list(self._active.items())
        for run_id, item in active:
            item.runner.close()
            self._release(run_id)
