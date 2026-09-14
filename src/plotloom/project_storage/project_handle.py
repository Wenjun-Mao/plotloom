"""Bound project repository handle and project-local runtime adapters."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from ..domain import (
    AuthoringDraft,
    AuthoringDraftScope,
    FragmentReuseBinding,
    GenerationRun,
    InitialStage,
    Project,
    ProjectBrief,
    RunExecutionTrace,
    RunTrace,
    STAGE_ORDER,
    StageEnvelope,
    StageHead,
    StageName,
    StageStatus,
    WorkUnitRepairScope,
)
from ..exceptions import NotFoundError, RevisionConflictError
from ..persistence import ProjectSQLiteRepository
from .artifacts import _OwnedArtifactStore, ProjectArtifactStore, ProjectRunArtifactStore
from .format import (
    OwnedArtifact,
    PROJECT_MANIFEST_FILENAME,
    ProjectManifest,
    ProjectStorageConfinementError,
    ProjectStorageConflictError,
    ProjectStorageCorruptionError,
    ProjectStorageError,
    _read_json,
    _require_real_directory,
    _utc_folder_timestamp,
)
from .operational_state import ProjectAccessLease
from .recovery_control import (
    ProjectRecoveryControl,
    read_recovery_control,
    recovered_generation_run_ids,
    recovery_operations_present,
)


class ProjectRecoveryRequiredError(ProjectStorageError):
    """Raised when restored unfinished work needs an explicit acknowledgement."""


class ProjectStore:
    """One project home and its directly authoritative canonical repository."""

    def __init__(
        self,
        project_home: Path,
        manifest: ProjectManifest,
        *,
        create_schema: bool,
        read_only: bool = False,
        defer_wal: bool = False,
        access_lease: ProjectAccessLease | None = None,
    ) -> None:
        self.home = project_home.resolve()
        self.manifest = manifest
        self._read_only = read_only
        self.database_path = self.home / manifest.database_path
        if self.database_path.is_symlink():
            raise ProjectStorageConfinementError(
                "project database must not be a symlink"
            )
        self._repository = ProjectSQLiteRepository(
            f"sqlite:///{self.database_path}",
            project_id=manifest.project_id,
            create_schema=create_schema,
            read_only=read_only,
            normalize_sqlite_wal=not read_only and not defer_wal,
        )
        self._repository._set_recovery_admission(
            recovered_run_ids=lambda: recovered_generation_run_ids(
                self.home, self.manifest.project_id
            ),
            recovery_operations_present=lambda: recovery_operations_present(
                self.home, self.manifest.project_id
            ),
        )
        self._artifacts = _OwnedArtifactStore(self.home, create=not read_only)
        self.artifacts = ProjectArtifactStore(
            self._artifacts, writable=not read_only
        )
        self._access_lease = access_lease

    @property
    def repository(self) -> ProjectSQLiteRepository:
        return self._repository

    @property
    def authoring(self):
        return self._repository.authoring

    @property
    def generation(self):
        return self._repository.generation

    @property
    def media(self):
        return self._repository.media

    def run_artifacts(self, run_id: str) -> ProjectRunArtifactStore:
        """Return the project-relative artifact adapter bound to one run's inventory."""

        if self._read_only:
            raise ProjectStorageCorruptionError(
                "a read-only project inspection cannot bind run artifacts"
            )
        return ProjectRunArtifactStore(
            self._artifacts,
            record=lambda artifact: self.generation.record_runtime_artifact(
                run_id,
                relative_path=artifact.relative_path,
                content_hash=artifact.content_hash,
                media_type=artifact.media_type,
                size_bytes=artifact.size_bytes,
            ),
        )

    @classmethod
    def initialize(
        cls,
        project_home: Path,
        manifest: ProjectManifest,
        project: Project,
        *,
        initial_stages: tuple[InitialStage, ...] = (),
        access_lease: ProjectAccessLease | None = None,
    ) -> "ProjectStore":
        if project.id != manifest.project_id:
            raise ProjectStorageCorruptionError(
                "new project and manifest identities differ"
            )
        store = cls(
            project_home,
            manifest,
            create_schema=True,
            access_lease=access_lease,
        )
        try:
            store.repository.initialize_project(project, initial_stages=initial_stages)
        except BaseException:
            store.repository.close()
            raise
        return store

    @classmethod
    def open(
        cls,
        project_home: Path,
        *,
        read_only: bool = False,
        defer_wal: bool = False,
        access_lease: ProjectAccessLease | None = None,
    ) -> "ProjectStore":
        if project_home.is_symlink() or not project_home.is_dir():
            raise ProjectStorageConfinementError(
                "project home must be a real directory"
            )
        home = project_home.resolve()
        manifest_path = home / PROJECT_MANIFEST_FILENAME
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ProjectStorageCorruptionError("project home has no regular manifest")
        try:
            manifest = ProjectManifest.model_validate(_read_json(manifest_path))
        except ValueError as error:
            raise ProjectStorageCorruptionError(
                "project manifest does not meet this storage format"
            ) from error
        store = cls(
            home,
            manifest,
            create_schema=False,
            read_only=read_only,
            defer_wal=defer_wal,
            access_lease=access_lease,
        )
        try:
            store._validate_opened_project()
        except BaseException:
            store.repository.close()
            raise
        return store

    def _validate_opened_project(self) -> None:
        if not self.database_path.exists() or not self.database_path.is_file():
            raise ProjectStorageCorruptionError(
                "project database is missing or not a regular file"
            )
        try:
            project = self.authoring.get_project(self.manifest.project_id)
            heads = self.authoring.list_stage_heads(self.manifest.project_id)
        except (NotFoundError, SQLAlchemyError, ValueError) as error:
            raise ProjectStorageCorruptionError(
                "project database cannot satisfy the project repository contract"
            ) from error
        if project.id != self.manifest.project_id or len(heads) != len(STAGE_ORDER):
            raise ProjectStorageCorruptionError(
                "manifest and project database identities differ"
            )

    def close(self) -> None:
        try:
            self.repository.close()
        finally:
            if self._access_lease is not None:
                self._access_lease.close()
                self._access_lease = None

    def remove_home(self) -> None:
        """Erase this closed archival home while retaining its exclusive lease."""

        if self._access_lease is None or self._access_lease.mode != "exclusive":
            raise ProjectStorageConflictError(
                "project deletion requires an exclusive project lease"
            )
        self.repository.close()
        try:
            shutil.rmtree(self.home)
        finally:
            self._access_lease.close()
            self._access_lease = None

    def project(self) -> Project:
        try:
            return self.authoring.get_project(self.manifest.project_id)
        except NotFoundError as error:
            raise ProjectStorageCorruptionError(
                "project database has no bound project"
            ) from error

    def archive(self, *, expected_lifecycle_revision: int) -> Project:
        return self.repository.lifecycle.archive_project(
            self.manifest.project_id, expected_lifecycle_revision
        )

    def restore(self, *, expected_lifecycle_revision: int) -> Project:
        return self.repository.lifecycle.restore_project(
            self.manifest.project_id, expected_lifecycle_revision
        )

    def recovery_control(self) -> ProjectRecoveryControl | None:
        """Return portable recovery admission without mutating historical work."""

        return read_recovery_control(self.home, self.manifest.project_id)

    def require_recovery_acknowledged(self) -> None:
        control = self.recovery_control()
        if control is not None and control.state == "recovery_required":
            raise ProjectRecoveryRequiredError(
                "recovery_required: acknowledge restored unfinished work before generation"
            )

    def update_brief(self, brief: ProjectBrief, *, expected_revision: int) -> Project:
        if expected_revision < 1:
            raise ValueError("expected_revision must be at least one")
        try:
            return self.authoring.update_project(
                self.manifest.project_id, expected_revision, brief
            )
        except RevisionConflictError as error:
            raise ProjectStorageConflictError("project revision is stale") from error

    def update_brief_consuming_authoring_draft(
        self,
        brief: ProjectBrief,
        *,
        expected_revision: int,
        entity_id: str,
        expected_draft_revision: int,
    ) -> Project:
        if expected_revision < 1:
            raise ValueError("expected_revision must be at least one")
        try:
            return self.authoring.update_project_consuming_authoring_draft(
                self.manifest.project_id,
                expected_revision,
                brief,
                entity_id=entity_id,
                expected_draft_revision=expected_draft_revision,
            )
        except RevisionConflictError as error:
            raise ProjectStorageConflictError(
                "canonical save draft receipt is stale"
            ) from error

    def update_stage(
        self, stage: StageName, payload: dict[str, Any], *, expected_revision: int
    ) -> StageHead:
        try:
            return self.authoring.update_stage(
                self.manifest.project_id, stage, expected_revision, payload
            )
        except RevisionConflictError as error:
            raise ProjectStorageConflictError(
                f"{stage.value} revision is stale"
            ) from error

    def update_stage_consuming_authoring_draft(
        self,
        stage: StageName,
        payload: dict[str, Any],
        *,
        expected_revision: int,
        entity_id: str,
        expected_draft_revision: int,
    ) -> StageHead:
        try:
            return self.authoring.update_stage_consuming_authoring_draft(
                self.manifest.project_id,
                stage,
                expected_revision,
                payload,
                entity_id=entity_id,
                expected_draft_revision=expected_draft_revision,
            )
        except RevisionConflictError as error:
            raise ProjectStorageConflictError(
                "canonical save draft receipt is stale"
            ) from error

    def authoring_drafts(self) -> list[AuthoringDraft]:
        return self.authoring.list_authoring_drafts(self.manifest.project_id)

    def save_authoring_draft(
        self,
        *,
        editor_scope: AuthoringDraftScope,
        entity_id: str,
        base_canonical_revision: int,
        expected_draft_revision: int,
        payload: dict[str, Any],
    ) -> AuthoringDraft:
        try:
            return self.authoring.upsert_authoring_draft(
                self.manifest.project_id,
                editor_scope=editor_scope,
                entity_id=entity_id,
                base_canonical_revision=base_canonical_revision,
                expected_draft_revision=expected_draft_revision,
                payload=payload,
            )
        except RevisionConflictError as error:
            raise ProjectStorageConflictError("authoring draft is stale") from error

    def discard_authoring_draft(
        self,
        *,
        editor_scope: AuthoringDraftScope,
        entity_id: str,
        expected_draft_revision: int,
    ) -> bool:
        return self.authoring.discard_authoring_draft(
            self.manifest.project_id,
            editor_scope=editor_scope,
            entity_id=entity_id,
            expected_draft_revision=expected_draft_revision,
        )

    def canonical_stages(self) -> list[StageEnvelope]:
        envelopes = self.authoring.list_stage_envelopes(self.manifest.project_id)
        ready = [item for item in envelopes if item.head.status == StageStatus.READY]
        if not ready:
            return []
        if len(ready) != len(STAGE_ORDER):
            raise ProjectStorageCorruptionError(
                "project pipeline has partial canonical heads"
            )
        return ready

    def generation_runs(self, *, limit: int = 200) -> list[GenerationRun]:
        return list(
            reversed(
                self.generation.list_project_runs(self.manifest.project_id, limit=limit)
            )
        )

    def generation_runs_for_index(self) -> list[GenerationRun]:
        """Expose frozen route/profile/status fields for startup reconstruction."""

        return self.generation.list_project_runs_for_index(self.manifest.project_id)

    def run_trace(self, run_id: str) -> RunTrace:
        trace = self.generation.get_run_trace(run_id)
        if trace.run.project_id != self.manifest.project_id:
            raise ProjectStorageCorruptionError(
                "run evidence belongs to another project"
            )
        return trace

    def run_execution_trace(self, run_id: str) -> RunExecutionTrace:
        return self.generation.get_run_execution_trace(run_id)

    def repair_scope(self, child_run_id: str) -> WorkUnitRepairScope:
        return self.generation.get_work_unit_repair_scope(child_run_id)

    def fragment_reuse_bindings(self, child_run_id: str) -> list[FragmentReuseBinding]:
        return self.generation.get_fragment_reuse_bindings(child_run_id)

    def read_artifact(self, artifact: OwnedArtifact) -> bytes:
        return self._artifacts.read(artifact)

    def image_exchange_for(self, job: dict[str, Any]):
        """Return the one project-run-local handoff exchange for an image unit."""
        from ..image_job_exchange import ImageJobExchange
        from ..managed_media import DEFAULT_MANAGED_MEDIA_LIMITS

        job_id = str(job.get("id", ""))
        created_at = job.get("createdAt")
        if not job_id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789_-"
            for character in job_id
        ):
            raise ProjectStorageConfinementError(
                "image handoff identity is not path-safe"
            )
        try:
            timestamp = _utc_folder_timestamp(datetime.fromisoformat(str(created_at)))
        except ValueError as error:
            raise ProjectStorageCorruptionError(
                "image handoff has no valid creation timestamp"
            ) from error
        runs = _require_real_directory(self.home / "runs", label="project runs root")
        run_home = runs / f"{timestamp}__{job_id}"
        _require_real_directory(run_home, label="project image handoff run")
        return ImageJobExchange(run_home, limits=DEFAULT_MANAGED_MEDIA_LIMITS)
