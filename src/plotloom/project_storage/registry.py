"""Filesystem discovery and opening of project homes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from ..domain import (
    Project,
    ProjectBrief,
    ProjectCreation,
    ProjectDuplicateResult,
    ProjectLifecycleStatus,
    InitialStage,
    STAGE_ORDER,
    StageName,
    StageStatus,
    brief_for_new_project,
    validate_initial_stage_prefix,
)
from ..exceptions import (
    InvalidTransitionError,
    ProjectManagedAssetsPresentError,
    RevisionConflictError,
)
from .format import (
    PROJECT_MANIFEST_FILENAME,
    ProjectManifest,
    ProjectStorageConflictError,
    ProjectStorageCorruptionError,
    ProjectStorageError,
    _canonical_json,
    _read_json,
    _require_real_directory,
    _utc_folder_timestamp,
    _write_new_file,
    parse_project_manifest,
)
from .project_handle import ProjectStore
from .recovery_validation import database_state
from .video_candidate_transition import (
    ProjectSchemaTransitionRequiredError,
    project_schema_status,
)
from .operational_state import (
    ProjectAccessLease,
    ProjectBusyError,
    ProjectClosedError,
    close_blockers,
)


@dataclass(frozen=True)
class ProjectHome:
    """One discovered project directory and its immutable manifest."""

    path: Path
    manifest: ProjectManifest


class ProjectDirectoryRegistry:
    """Rebuildable project catalog derived only from validated manifests."""

    def __init__(self, outputs_root: Path) -> None:
        self.outputs_root = _require_real_directory(outputs_root, label="outputs root")

    def _new_home(self, project: Project) -> Path:
        directory_name = f"{_utc_folder_timestamp(project.created_at)}__{project.id}"
        home = self.outputs_root / directory_name
        try:
            home.mkdir(mode=0o700)
        except FileExistsError as error:
            raise ProjectStorageConflictError(
                f"project home already exists: {directory_name}"
            ) from error
        return home

    def create(
        self,
        brief: ProjectBrief,
        *,
        project_id: str | None = None,
        created_at: datetime | None = None,
        initial_stages: tuple[InitialStage, ...] = (),
    ) -> ProjectStore:
        # Reject an invalid bootstrap before publishing a manifest directory.
        # This keeps an idempotent retry reservation recoverable only after a
        # complete project initialization can actually begin.
        validate_initial_stage_prefix(initial_stages)
        brief = brief_for_new_project(brief)
        values: dict[str, object] = {"brief": brief}
        if project_id is not None:
            values["id"] = project_id
        if created_at is not None:
            values["created_at"] = created_at
            values["updated_at"] = created_at
        project = Project(**values)
        home = self._new_home(project)
        manifest = ProjectManifest(project_id=project.id, created_at=project.created_at)
        _write_new_file(
            home / PROJECT_MANIFEST_FILENAME,
            (
                _canonical_json(manifest.model_dump(mode="json", by_alias=True)) + "\n"
            ).encode("utf-8"),
        )
        lease = ProjectAccessLease.acquire(home, mode="shared")
        try:
            return ProjectStore.initialize(
                home,
                manifest,
                project,
                initial_stages=initial_stages,
                access_lease=lease,
            )
        except BaseException:
            lease.close()
            raise

    def resume_creation(
        self,
        brief: ProjectBrief,
        *,
        project_id: str,
        created_at: datetime,
        initial_stages: tuple[InitialStage, ...] = (),
    ) -> ProjectStore:
        """Finish one expired idempotent bootstrap at its reserved home.

        The application ledger grants this method's caller the sole expired
        creation lease.  An interrupted initializer can therefore reuse its
        validated manifest and complete the project transaction, rather than
        opening a half-published home or allocating another project ID.
        """

        validate_initial_stage_prefix(initial_stages)
        brief = brief_for_new_project(brief)
        project = Project(
            id=project_id,
            brief=brief,
            created_at=created_at,
            updated_at=created_at,
        )
        home = self.outputs_root / f"{_utc_folder_timestamp(created_at)}__{project_id}"
        if home.is_symlink() or not home.is_dir():
            raise ProjectStorageCorruptionError(
                "reserved project home is missing or not a real directory"
            )
        manifest_path = home / PROJECT_MANIFEST_FILENAME
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ProjectStorageCorruptionError("reserved project home has no regular manifest")
        try:
            manifest = parse_project_manifest(_read_json(manifest_path))
        except ProjectStorageCorruptionError:
            raise
        if manifest.project_id != project.id or manifest.created_at != project.created_at:
            raise ProjectStorageCorruptionError(
                "reserved project manifest does not match its idempotency reservation"
            )
        lease = ProjectAccessLease.acquire(home, mode="shared")
        try:
            try:
                return ProjectStore.initialize(
                    home,
                    manifest,
                    project,
                    initial_stages=initial_stages,
                    access_lease=lease,
                )
            except InvalidTransitionError as error:
                if str(error) != "project repository has already been initialized":
                    raise
                store = ProjectStore.open(home, defer_wal=True, access_lease=lease)
                store.repository.enable_sqlite_wal()
                return store
        except BaseException:
            if lease.descriptor >= 0:
                lease.close()
            raise

    def discover(self) -> list[ProjectHome]:
        homes: list[ProjectHome] = []
        for candidate in sorted(
            self.outputs_root.iterdir(), key=lambda path: path.name
        ):
            if (
                candidate.name.startswith(".")
                or candidate.is_symlink()
                or not candidate.is_dir()
            ):
                continue
            manifest_path = candidate / PROJECT_MANIFEST_FILENAME
            if manifest_path.is_symlink() or not manifest_path.is_file():
                continue
            try:
                manifest = parse_project_manifest(_read_json(manifest_path))
                lease = ProjectAccessLease.acquire(
                    candidate, mode="shared", create=False
                )
                try:
                    store = ProjectStore.open(
                        candidate, read_only=True, access_lease=lease
                    )
                except ProjectSchemaTransitionRequiredError:
                    # Keep this known legacy folder discoverable so an admitted
                    # writable open can perform its one-time transition.
                    lease.close()
                    homes.append(ProjectHome(path=candidate.resolve(), manifest=manifest))
                    continue
                store.close()
            except (ProjectStorageError, ValueError, SQLAlchemyError):
                continue
            homes.append(ProjectHome(path=candidate.resolve(), manifest=manifest))
        return homes

    def open(self, project_id: str) -> ProjectStore:
        """Open an admitted shared handle; closed homes never reopen implicitly."""

        home = self._project_home(project_id)
        if (
            project_schema_status(
                home.path / home.manifest.database_path, home.manifest.project_id
            )
            != "current"
        ):
            if database_state(
                home.path / home.manifest.database_path, home.manifest.project_id
            ) != "open":
                raise ProjectClosedError(
                    "project_closed: reopen it explicitly before editing"
                )
            # The only project-schema mutation is serialized under an
            # exclusive folder lease. The returned handle below is a fresh,
            # ordinary shared lease after the transaction commits.
            transition_lease = ProjectAccessLease.acquire(home.path, mode="exclusive")
            try:
                transitioned = ProjectStore.open(
                    home.path, defer_wal=True, access_lease=transition_lease
                )
            except BaseException:
                transition_lease.close()
                raise
            transitioned.close()
        lease = ProjectAccessLease.acquire(home.path, mode="shared")
        try:
            store = ProjectStore.open(
                home.path, defer_wal=True, access_lease=lease
            )
            state, _revision = store.repository.operational_state()
            if state != "open":
                store.close()
                raise ProjectClosedError("project_closed: reopen it explicitly before editing")
            store.repository.enable_sqlite_wal()
            return store
        except BaseException:
            if lease.descriptor >= 0:
                lease.close()
            raise

    def inspect(self, project_id: str) -> ProjectStore:
        """Open a shared read handle without changing closed-project admission."""

        home = self._project_home(project_id)
        lease = ProjectAccessLease.acquire(
            home.path, mode="shared", create=False
        )
        try:
            return ProjectStore.open(
                home.path, read_only=True, access_lease=lease
            )
        except BaseException:
            lease.close()
            raise

    def close_project(self, project_id: str) -> int:
        """Quiesce one folder, checkpoint SQLite, then deny future admission."""

        store = self._exclusive_store(project_id)
        try:
            state, revision = store.repository.operational_state()
            if state == "open":
                blockers = close_blockers(store)
                if blockers:
                    raise ProjectBusyError(
                        "project_busy: " + ", ".join(blockers)
                    )
                _state, revision = store.repository.set_operational_state(
                    expected_revision=revision, state="closed"
                )
            # WAL checkpoint happens before the repository/lease are released;
            # no sidecar can race the successful close transition.
            with store.repository.engine.connect() as connection:
                checkpoint = connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)").one()
            if checkpoint[0] != 0 or checkpoint[1] != checkpoint[2]:
                if state == "open":
                    store.repository.set_operational_state(
                        expected_revision=revision, state="open"
                    )
                raise ProjectBusyError("project_busy: SQLite checkpoint did not quiesce")
            return revision
        finally:
            store.close()

    def reopen_project(self, project_id: str) -> int:
        """Explicitly reopen a closed folder without dispatching or replaying work."""

        home = self._project_home(project_id)
        lease = ProjectAccessLease.acquire(home.path, mode="exclusive")
        try:
            store = ProjectStore.open(
                home.path, access_lease=lease, apply_project_schema_transition=False
            )
        except BaseException:
            lease.close()
            raise
        try:
            state, revision = store.repository.operational_state()
            if state == "open":
                store.transition_project_schema()
                return revision
            # Reopening is the sole explicit operation allowed to advance a
            # closed legacy folder before it can accept ordinary writes.
            store.transition_project_schema(allow_closed=True)
            _state, revision = store.repository.set_operational_state(
                expected_revision=revision, state="open"
            )
            return revision
        finally:
            store.close()

    def archive_project(
        self, project_id: str, *, expected_lifecycle_revision: int
    ) -> Project:
        store = self._exclusive_store(project_id)
        try:
            self._require_lifecycle_quiescence(store)
            return store.archive(
                expected_lifecycle_revision=expected_lifecycle_revision
            )
        finally:
            store.close()

    def restore_project(
        self, project_id: str, *, expected_lifecycle_revision: int
    ) -> Project:
        store = self._exclusive_store(project_id)
        try:
            return store.restore(
                expected_lifecycle_revision=expected_lifecycle_revision
            )
        finally:
            store.close()

    def duplicate_project(
        self,
        project_id: str,
        *,
        expected_lifecycle_revision: int,
        target_project_id: str,
        target_created_at: datetime,
        title: str | None,
    ) -> ProjectDuplicateResult:
        """Copy only the contiguous canonical prefix into a fresh project home."""

        source = self._exclusive_store(project_id)
        destination: ProjectStore | None = None
        try:
            source_project = source.project()
            if source_project.lifecycle_revision != expected_lifecycle_revision:
                raise RevisionConflictError(
                    "project-lifecycle",
                    expected_lifecycle_revision,
                    source_project.lifecycle_revision,
                )
            brief = source_project.brief.model_copy(
                update={"title": title.strip()}
            ) if title is not None else source_project.brief
            try:
                destination = self.open(target_project_id)
            except ProjectStorageError as error:
                if not str(error).startswith("project not found"):
                    raise
                destination = self.create(
                    brief,
                    project_id=target_project_id,
                    created_at=target_created_at,
                )

            copied: list[StageName] = []
            for stage in STAGE_ORDER:
                head = source.authoring.get_stage_head(project_id, stage)
                if head.status != StageStatus.READY:
                    break
                destination_head = destination.authoring.get_stage_head(
                    target_project_id, stage
                )
                if destination_head.status == StageStatus.MISSING:
                    payload = source.authoring.get_stage_payload(project_id, stage)
                    destination.update_stage(
                        stage,
                        payload.model_dump(mode="json", by_alias=True),
                        expected_revision=0,
                    )
                copied.append(stage)
            copied_through = copied[-1] if copied else None
            return ProjectDuplicateResult(
                project=ProjectCreation(
                    **destination.project().model_dump(mode="python"),
                    stages=destination.authoring.list_stage_envelopes(
                        target_project_id
                    ),
                ),
                copied_through=copied_through,
                omitted_stages=list(STAGE_ORDER[len(copied) :]),
            )
        finally:
            if destination is not None:
                destination.close()
            source.close()

    def replay_duplicate(
        self,
        project_id: str,
        *,
        copied_through: str | None,
        omitted_stages: tuple[str, ...],
    ) -> ProjectDuplicateResult:
        """Read one reserved duplicate without reconsidering mutable source state."""

        store = self.inspect(project_id)
        try:
            return ProjectDuplicateResult(
                project=ProjectCreation(
                    **store.project().model_dump(mode="python"),
                    stages=store.authoring.list_stage_envelopes(project_id),
                ),
                copied_through=StageName(copied_through) if copied_through else None,
                omitted_stages=[StageName(stage) for stage in omitted_stages],
            )
        finally:
            store.close()

    def permanently_delete_project(
        self,
        project_id: str,
        *,
        expected_lifecycle_revision: int,
        confirmation_title: str,
    ) -> None:
        """Remove one archived, media-free home after exact confirmation."""

        store = self._exclusive_store(project_id)
        removed = False
        try:
            project = store.project()
            if project.lifecycle_revision != expected_lifecycle_revision:
                raise RevisionConflictError(
                    "project-lifecycle",
                    expected_lifecycle_revision,
                    project.lifecycle_revision,
                )
            if project.lifecycle_status != ProjectLifecycleStatus.ARCHIVED:
                raise InvalidTransitionError(
                    "only archived projects can be permanently deleted"
                )
            if confirmation_title != project.brief.title:
                raise InvalidTransitionError(
                    "confirmation title does not match the project title"
                )
            self._require_lifecycle_quiescence(store)
            if store.media.list_managed_assets(project_id):
                raise ProjectManagedAssetsPresentError()
            store.remove_home()
            removed = True
        finally:
            if not removed:
                store.close()

    def _project_home(self, project_id: str) -> ProjectHome:
        matches = [
            home for home in self.discover() if home.manifest.project_id == project_id
        ]
        if not matches:
            # A rejected manifest must remain diagnosable by its known project
            # identity. In particular, format-9 is not silently hidden as a
            # missing folder: callers receive its reset-required admission
            # failure before any schema-opening path can mutate it.
            for candidate in self.outputs_root.iterdir():
                manifest_path = candidate / PROJECT_MANIFEST_FILENAME
                if candidate.is_symlink() or not candidate.is_dir() or manifest_path.is_symlink() or not manifest_path.is_file():
                    continue
                raw = _read_json(manifest_path)
                if raw.get("projectId") == project_id or raw.get("project_id") == project_id:
                    parse_project_manifest(raw)
            raise ProjectStorageError(
                f"project not found in outputs root: {project_id}"
            )
        if len(matches) > 1:
            raise ProjectStorageCorruptionError(
                f"multiple project homes share identity: {project_id}"
            )
        return matches[0]

    def _exclusive_store(self, project_id: str) -> ProjectStore:
        home = self._project_home(project_id)
        lease = ProjectAccessLease.acquire(home.path, mode="exclusive")
        try:
            return ProjectStore.open(home.path, access_lease=lease)
        except BaseException:
            lease.close()
            raise

    @staticmethod
    def _require_lifecycle_quiescence(store: ProjectStore) -> None:
        """Apply the same external-publication guard used by folder close."""

        blockers = close_blockers(store)
        if blockers:
            raise ProjectBusyError("project_busy: " + ", ".join(blockers))
