"""Project-owned projection of the existing text generation pipeline.

The retained runtime is deliberately not wired to this module yet.  It runs the
existing durable pipeline in a disposable harness, then atomically projects the
fully validated canonical result and its secret-free lineage into one project
folder database.  This keeps the new storage boundary independent from the
mixed application repository without inventing a second text-generation
contract.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import sqlite3
import tempfile
from pathlib import Path

from .artifacts import LocalArtifactStore
from .domain import (
    EntityRevision,
    FragmentReuseBinding,
    GenerationRun,
    Project,
    RunExecutionTrace,
    RunKind,
    RunStatus,
    RunTrace,
    STAGE_ORDER,
    StageEnvelope,
    StageStatus,
    WorkUnitRepairScope,
)
from .jobs import LifecycleJobRunner
from .persistence import SQLiteRepository
from .pipeline import PipelineEngine, RunSecretBroker, TextProviderResolver
from .project_storage import ProjectStorageConflictError, ProjectStorageError, ProjectStore
from .provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
)
from .providers import ProviderPorts
from .runtime import RunContext


TextProfileSnapshot = TextProviderProfileSnapshot | TextProviderProfileSnapshotV3


@dataclass(frozen=True)
class RunExecutionEvidence:
    """One run ID paired with the durable plan, unit, and seal evidence."""

    run_id: str
    trace: RunExecutionTrace


@dataclass(frozen=True)
class ProjectGenerationEvidence:
    """Complete, independently validated input to one atomic installation."""

    stages: tuple[StageEnvelope, ...]
    entity_revisions: tuple[EntityRevision, ...]
    run_traces: tuple[RunTrace, ...]
    execution_traces: tuple[RunExecutionEvidence, ...]
    repair_scopes: tuple[WorkUnitRepairScope, ...]
    fragment_reuse_bindings: tuple[FragmentReuseBinding, ...]
    install_run_id: str

    @property
    def install_run(self) -> GenerationRun:
        for trace in self.run_traces:
            if trace.run.id == self.install_run_id:
                return trace.run
        raise ProjectStorageError("generation evidence has no declared install run")

    def validate_for_install(self, *, project: Project) -> None:
        """Reject non-current or incomplete evidence before a project write.

        This validation intentionally accepts neither a failed/quarantined
        result nor a partial set of seals.  Cancellation and unknown provider
        outcomes therefore retain their original terminal evidence in the
        disposable execution record, but never become success-shaped canonical
        state in a project folder.
        """

        expected_stages = list(STAGE_ORDER)
        if [envelope.head.stage for envelope in self.stages] != expected_stages:
            raise ProjectStorageError("canonical evidence must contain the four stages in order")
        heads = {envelope.head.stage: envelope.head for envelope in self.stages}
        revisions = {revision.id: revision for revision in self.entity_revisions}
        if len(revisions) != len(self.entity_revisions):
            raise ProjectStorageError("canonical evidence contains duplicate revision identities")
        for stage in expected_stages:
            head = heads[stage]
            revision = revisions.get(head.entity_revision_id or "")
            if (
                head.status != StageStatus.READY
                or revision is None
                or revision.project_id != project.id
                or revision.stage != stage
                or revision.revision != head.revision
                or revision.content_hash != head.content_hash
                or head.schema_version != revision.schema_version
            ):
                raise ProjectStorageError("canonical heads and revisions are not a complete current set")
        if project.lifecycle_status.value != "active":
            raise ProjectStorageConflictError("cannot install canonical evidence into an inactive project")

        runs = [trace.run for trace in self.run_traces]
        by_id = {run.id: run for run in runs}
        if len(by_id) != len(runs) or not runs:
            raise ProjectStorageError("generation evidence must contain uniquely identified runs")
        if any(
            run.project_id != project.id
            or run.canonical_snapshot.project_id != project.id
            or run.canonical_snapshot.project_revision != project.revision
            or run.canonical_snapshot.brief != project.brief
            for run in runs
        ):
            raise ProjectStorageConflictError("generation evidence is stale or belongs to another project")
        for index, run in enumerate(runs):
            if run.parent_run_id is not None and run.parent_run_id not in by_id:
                raise ProjectStorageError("repair parent evidence is not included in the installation")
            if run.parent_run_id is not None and runs.index(by_id[run.parent_run_id]) >= index:
                raise ProjectStorageError("repair parent evidence must precede its child run")

        install_run = self.install_run
        if (
            install_run.status != RunStatus.SUCCEEDED
            or install_run.kind not in {RunKind.PIPELINE, RunKind.REPAIR, RunKind.REBUILD}
            or install_run.requested_stages != expected_stages
            or set(install_run.result_revision_ids) != set(revisions)
        ):
            raise ProjectStorageError("only a successful complete pipeline run may install canonical stages")
        execution_by_run = {item.run_id: item.trace for item in self.execution_traces}
        if set(execution_by_run) != set(by_id):
            raise ProjectStorageError("every persisted run requires durable execution evidence")
        install_execution = execution_by_run[install_run.id]
        if (
            install_execution.generation_plan is None
            or [plan.stage for plan in install_execution.stage_plans] != expected_stages
            or [seal.stage for seal in install_execution.sealed_aggregates] != expected_stages
            or len({seal.id for seal in install_execution.sealed_aggregates}) != len(expected_stages)
        ):
            raise ProjectStorageError("successful canonical installation requires one sealed aggregate per stage")
        if any(seal.run_id != install_run.id for seal in install_execution.sealed_aggregates):
            raise ProjectStorageError("sealed aggregate evidence belongs to another run")

        scopes = {scope.child_run_id: scope for scope in self.repair_scopes}
        for run in runs:
            if run.work_unit_repair_scope_id is not None:
                scope = scopes.get(run.id)
                if (
                    scope is None
                    or scope.parent_run_id != run.parent_run_id
                    or scope.child_run_id != run.work_unit_repair_scope_id
                ):
                    raise ProjectStorageError("exact repair run is missing its immutable repair scope")
        if any(
            binding.child_run_id not in scopes
            or binding.source_run_id != scopes[binding.child_run_id].parent_run_id
            for binding in self.fragment_reuse_bindings
        ):
            raise ProjectStorageError("fragment reuse evidence is not bound to an exact repair scope")


class ProjectPipelineExecutor:
    """Exercise the authoritative offline text pipeline before project install.

    The runner uses `PipelineEngine`, `LifecycleJobRunner`, and the normal
    durable work-unit repository.  That temporary repository is a harness only:
    it is deleted after its fully validated data has been projected into the
    project-owned schema, and it never becomes a selectable runtime.
    """

    def __init__(self, provider_resolver: TextProviderResolver) -> None:
        self.provider_resolver = provider_resolver

    def execute(
        self,
        store: ProjectStore,
        *,
        profile: TextProfileSnapshot,
        exact_repair: bool = False,
        before_install: Callable[[ProjectStore], None] | None = None,
    ) -> GenerationRun:
        evidence = self.collect(store, profile=profile, exact_repair=exact_repair)
        if before_install is not None:
            before_install(store)
        return store.install_generation_evidence(evidence)

    def collect(
        self,
        store: ProjectStore,
        *,
        profile: TextProfileSnapshot,
        exact_repair: bool = False,
    ) -> ProjectGenerationEvidence:
        project = store.project()
        with tempfile.TemporaryDirectory(prefix="plotloom-project-pipeline-") as temporary_root:
            root = Path(temporary_root)
            database_path = root / "pipeline.sqlite3"
            repository = SQLiteRepository(f"sqlite:///{database_path}")
            secrets = RunSecretBroker()
            runner: LifecycleJobRunner | None = None
            try:
                self._seed_profile(repository, profile)
                staged_project = repository.create_project(project.brief.model_copy(deep=True))
                repository.close()
                self._rebind_staging_project_id(
                    database_path,
                    source_id=staged_project.id,
                    target_id=project.id,
                )
                repository = SQLiteRepository(f"sqlite:///{database_path}")
                run = repository.create_run(
                    project.id,
                    RunKind.PIPELINE,
                    STAGE_ORDER,
                    provider_snapshot=profile.model_dump(mode="json", by_alias=True),
                )
                runner = LifecycleJobRunner(
                    repository,
                    PipelineEngine(repository, self.provider_resolver, secrets),
                    RunContext(
                        providers=ProviderPorts(),
                        artifacts=LocalArtifactStore(root / "artifacts"),
                    ),
                    max_workers=1,
                    secret_registrar=secrets,
                )
                completed = runner.submit(run.id).result()
                run_ids = [run.id]
                if exact_repair:
                    if completed.status != RunStatus.QUARANTINED:
                        raise ProjectStorageError(
                            "exact repair proof requires a quarantined parent run"
                        )
                    target = next(
                        (
                            unit
                            for unit in repository.list_generation_work_units(run.id)
                            if unit.status.value == "quarantined"
                        ),
                        None,
                    )
                    if target is None:
                        raise ProjectStorageError("quarantined parent has no repairable work unit")
                    child = repository.create_work_unit_repair_run(
                        run.id,
                        target.id,
                        idempotency_key=f"project-storage-{project.id}",
                    ).run
                    completed = runner.submit(child.id).result()
                    run_ids.append(child.id)
                if completed.status != RunStatus.SUCCEEDED:
                    raise ProjectStorageError(
                        f"pipeline result is {completed.status.value}; canonical output was not installed"
                    )
                return self._evidence_from_repository(repository, project.id, run_ids, completed.id)
            finally:
                if runner is not None:
                    runner.close()
                secrets.close()
                repository.close()

    @staticmethod
    def _seed_profile(repository: SQLiteRepository, profile: TextProfileSnapshot) -> None:
        # The retained profile-control schema is V2 plus adapter columns. A
        # freshly admitted run is V3, so retain its additive adapter fields on
        # the run while materializing the matching V2 control-plane profile in
        # the disposable admission harness.
        control_data = profile.model_dump(mode="json", by_alias=True)
        control_data.pop("adapterId", None)
        control_data.pop("adapterVersion", None)
        control_data.update(profileSchemaVersion=2, profileHash="")
        control_profile = TextProviderProfileSnapshot.model_validate(control_data)
        if profile.profile_id == DEFAULT_PROVIDER_PROFILE_ID:
            repository.bootstrap_default_text_provider_profile(control_profile)
            return
        default_data = control_profile.model_dump(mode="json", by_alias=True)
        default_data.update(profileId=DEFAULT_PROVIDER_PROFILE_ID, profileVersion=0, profileHash="")
        repository.bootstrap_default_text_provider_profile(
            TextProviderProfileSnapshot.model_validate(default_data)
        )
        repository.create_text_provider_profile(
            profile.profile_id,
            profile.profile_id,
            configuration=control_profile,
            adapter_id=(profile.adapter_id if isinstance(profile, TextProviderProfileSnapshotV3) else None),
            adapter_version=(profile.adapter_version if isinstance(profile, TextProviderProfileSnapshotV3) else None),
        )

    @staticmethod
    def _rebind_staging_project_id(database_path: Path, *, source_id: str, target_id: str) -> None:
        """Bind a disposable runner project to the already-allocated folder ID.

        `SQLiteRepository.create_project` owns public project-ID allocation. The
        harness must nevertheless execute against the real folder identity so
        its frozen snapshot, run IDs, plans, and repair scope are directly
        reusable.  This private, empty-harness migration runs before any run or
        evidence exists and is never available in the retained runtime.
        """

        with sqlite3.connect(database_path) as connection:
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("UPDATE v2_projects SET id = ? WHERE id = ?", (target_id, source_id))
            if connection.total_changes != 1:
                raise ProjectStorageError("disposable pipeline project identity was not allocated")
            for table in ("v2_stage_heads", "v2_entity_revisions"):
                connection.execute(f"UPDATE {table} SET project_id = ? WHERE project_id = ?", (target_id, source_id))
            connection.commit()

    @staticmethod
    def _evidence_from_repository(
        repository: SQLiteRepository,
        project_id: str,
        run_ids: Sequence[str],
        install_run_id: str,
    ) -> ProjectGenerationEvidence:
        stages = tuple(repository.list_stage_envelopes(project_id))
        revisions = tuple(
            repository.get_entity_revision(envelope.head.entity_revision_id)
            for envelope in stages
            if envelope.head.entity_revision_id is not None
        )
        traces = tuple(repository.get_run_trace(run_id) for run_id in run_ids)
        execution = tuple(
            RunExecutionEvidence(run_id=run_id, trace=repository.get_run_execution_trace(run_id))
            for run_id in run_ids
        )
        repair_runs = [trace.run for trace in traces if trace.run.work_unit_repair_scope_id]
        scopes = tuple(repository.get_work_unit_repair_scope(run.id) for run in repair_runs)
        bindings = tuple(
            binding
            for run in repair_runs
            for binding in repository.get_fragment_reuse_bindings(run.id)
        )
        return ProjectGenerationEvidence(
            stages=stages,
            entity_revisions=revisions,
            run_traces=traces,
            execution_traces=execution,
            repair_scopes=scopes,
            fragment_reuse_bindings=bindings,
            install_run_id=install_run_id,
        )
