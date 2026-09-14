"""Direct project-owned execution of the canonical text-generation pipeline.

There is no staging database or evidence projection here.  ``PipelineEngine``
and ``LifecycleJobRunner`` write admission, attempts, work units, seals, and
terminal disposition directly to the one repository in the project folder.
"""

from __future__ import annotations

from .artifacts import LocalArtifactStore
from .domain import GenerationRun, RunKind, RunStatus, STAGE_ORDER, WorkUnitStatus
from .jobs import LifecycleJobRunner
from .pipeline import PipelineEngine, RunSecretBroker, TextProviderResolver
from .project_storage import ProjectStorageError, ProjectStore
from .provider_profiles import TextProviderProfileSnapshot, TextProviderProfileSnapshotV3
from .providers import ProviderPorts
from .runtime import RunContext


TextProfileSnapshot = TextProviderProfileSnapshot | TextProviderProfileSnapshotV3


class ProjectPipelineExecutor:
    """Execute one four-stage run against its durable project repository."""

    def __init__(self, provider_resolver: TextProviderResolver) -> None:
        self.provider_resolver = provider_resolver

    def execute(
        self,
        store: ProjectStore,
        *,
        profile: TextProfileSnapshot,
        exact_repair: bool = False,
        secret_broker: RunSecretBroker | None = None,
        session_api_key: str | None = None,
    ) -> GenerationRun:
        """Persist every lifecycle boundary, including non-success terminals.

        ``profile`` has already been selected by application storage.  It is
        admitted only for this process-local operation, then frozen verbatim on
        each project run.  Credentials are supplied exclusively by the optional
        broker/session input and are never passed to repository methods.
        """

        store.require_recovery_acknowledged()
        project = store.project()
        repository = store.generation
        snapshot = profile.model_dump(mode="json", by_alias=True)
        secrets = secret_broker or RunSecretBroker()
        owns_secrets = secret_broker is None
        runner: LifecycleJobRunner | None = None
        try:
            with repository.admit_provider_snapshot(snapshot):
                run = repository.create_run(
                    project.id,
                    RunKind.PIPELINE,
                    STAGE_ORDER,
                    provider_snapshot=snapshot,
                )
                runner = LifecycleJobRunner(
                    repository,
                    PipelineEngine(repository, self.provider_resolver, secrets),
                    RunContext(
                        providers=ProviderPorts(),
                        artifacts=LocalArtifactStore(store.home / "runs"),
                    ),
                    max_workers=1,
                    secret_registrar=secrets,
                )
                completed = runner.submit(run.id, session_api_key=session_api_key).result()
                if not exact_repair:
                    return completed
                if completed.status != RunStatus.QUARANTINED:
                    raise ProjectStorageError(
                        "exact repair proof requires a quarantined parent run"
                    )
                target = next(
                    (
                        unit
                        for unit in repository.list_generation_work_units(run.id)
                        if unit.status == WorkUnitStatus.QUARANTINED
                    ),
                    None,
                )
                if target is None:
                    raise ProjectStorageError("quarantined parent has no repairable work unit")
                child = repository.create_work_unit_repair_run(
                    run.id,
                    target.id,
                    idempotency_key=f"project-storage-{project.id}-{run.id}",
                ).run
                return runner.submit(child.id, session_api_key=session_api_key).result()
        finally:
            if runner is not None:
                runner.close()
            if owns_secrets:
                secrets.close()
