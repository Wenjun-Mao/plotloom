"""Project-folder storage ownership boundary.

Each project home owns the canonical repository used by its pipeline.  The
small application database is intentionally limited to installation-scoped
profile selection and accounting; it is never a source of project content.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, field_validator, model_validator
from sqlalchemy.exc import SQLAlchemyError

from .domain import (
    AuthoringDraft,
    AuthoringDraftScope,
    CamelModel,
    FragmentReuseBinding,
    GenerationRun,
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
    contains_secret_setting,
    contains_secret_value,
    utc_now,
)
from .exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from .persistence import ProjectSQLiteRepository

if TYPE_CHECKING:
    from .pipeline import RunSecretBroker, TextProviderResolver
    from .provider_profiles import TextProviderProfileSnapshot, TextProviderProfileSnapshotV3


# Checkpoint 2B adds durable authoring-draft rows to the direct project schema.
# A 2A folder is rejected rather than silently receiving an unreviewed schema
# mutation; no importer/compatibility path exists before the planned cutover.
PROJECT_STORAGE_FORMAT_VERSION = 4
PROJECT_DATABASE_RELATIVE_PATH = "project.sqlite3"
PROJECT_MANIFEST_FILENAME = "project.json"


class ProjectStorageError(RuntimeError):
    """Base error for the isolated project-folder storage boundary."""


class ProjectStorageConflictError(ProjectStorageError):
    """Raised when a project edit is based on stale project state."""


class ProjectStorageConfinementError(ProjectStorageError):
    """Raised when a stored path could escape its owning project home."""


class ProjectStorageCorruptionError(ProjectStorageError):
    """Raised when a project manifest or database does not meet this format."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: bytes) -> str:
    return sha256(value).hexdigest()


def _utc_folder_timestamp(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S%fZ")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            value = json.loads(handle.read())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProjectStorageCorruptionError(f"invalid JSON file: {path}") from error
    if not isinstance(value, dict):
        raise ProjectStorageCorruptionError(f"JSON object required: {path}")
    return value


def _write_new_file(path: Path, contents: bytes) -> None:
    """Publish one new immutable file without replacing an existing path."""

    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _require_real_directory(path: Path, *, label: str) -> Path:
    if path.is_symlink():
        raise ProjectStorageConfinementError(f"{label} must not be a symlink: {path}")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or path.is_symlink():
        raise ProjectStorageConfinementError(f"{label} must be a real directory: {path}")
    return path.resolve()


def _relative_owned_path(value: str) -> PurePosixPath:
    candidate = PurePosixPath(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts or "." in candidate.parts:
        raise ProjectStorageConfinementError("owned artifact paths must be normalized relative paths")
    return candidate


class ProjectManifest(CamelModel):
    """Immutable identity record stored at the root of every project home."""

    format_version: Literal[PROJECT_STORAGE_FORMAT_VERSION] = PROJECT_STORAGE_FORMAT_VERSION
    project_id: str = Field(min_length=1)
    created_at: datetime
    database_path: Literal[PROJECT_DATABASE_RELATIVE_PATH] = PROJECT_DATABASE_RELATIVE_PATH


class OwnedArtifact(CamelModel):
    """A hash-addressed project-owned file, never an absolute machine path."""

    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    relative_path: str
    media_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _relative_owned_path(value).as_posix()


class ApplicationProfile(CamelModel):
    """Reusable public provider configuration owned by the installation."""

    profile_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    revision: int = Field(ge=1)
    configuration: dict[str, Any]
    updated_at: datetime

    @model_validator(mode="after")
    def reject_secret_configuration(self) -> "ApplicationProfile":
        if contains_secret_setting(self.configuration) or contains_secret_value(self.configuration):
            raise ValueError("application provider profiles must not contain credentials")
        return self


class GlobalAccountingEntry(CamelModel):
    """Installation-global accounting reservation; it never carries project content."""

    dispatch_identity: str = Field(min_length=1, max_length=255)
    resource: str = Field(min_length=1, max_length=120)
    reserved_units: int = Field(ge=0)
    status: Literal["reserved", "released", "consumed"] = "reserved"
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def reject_secret_fields(self) -> "GlobalAccountingEntry":
        if contains_secret_value(self.dispatch_identity) or contains_secret_value(self.resource):
            raise ValueError("global accounting identifiers must be public")
        return self


class ApplicationStore:
    """Small installation store for profiles, selection, and global accounting only."""

    def __init__(self, application_data_root: Path) -> None:
        self.root = _require_real_directory(application_data_root, label="application data root")
        self.path = self.root / "application.sqlite3"
        if self.path.is_symlink():
            raise ProjectStorageConfinementError("application database must not be a symlink")
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=1000")
        return connection

    @contextmanager
    def _read(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize_schema(self) -> None:
        with self._write() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS application_profiles (
                    profile_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    configuration_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS application_preferences (
                    preference_key TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL REFERENCES application_profiles(profile_id)
                );
                CREATE TABLE IF NOT EXISTS global_accounting (
                    dispatch_identity TEXT PRIMARY KEY,
                    resource TEXT NOT NULL,
                    reserved_units INTEGER NOT NULL CHECK (reserved_units >= 0),
                    status TEXT NOT NULL CHECK (status IN ('reserved', 'released', 'consumed')),
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _profile_from_row(row: sqlite3.Row) -> ApplicationProfile:
        return ApplicationProfile(
            profile_id=row["profile_id"],
            revision=row["revision"],
            configuration=json.loads(row["configuration_json"]),
            updated_at=row["updated_at"],
        )

    def save_profile(
        self,
        profile_id: str,
        configuration: dict[str, Any],
        *,
        expected_revision: int | None = None,
    ) -> ApplicationProfile:
        with self._write() as connection:
            row = connection.execute(
                "SELECT profile_id, revision, configuration_json, updated_at "
                "FROM application_profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            existing = self._profile_from_row(row) if row is not None else None
            if existing is None:
                if expected_revision not in {None, 0}:
                    raise ProjectStorageConflictError("provider profile does not exist at expected revision")
                profile = ApplicationProfile(
                    profile_id=profile_id,
                    revision=1,
                    configuration=configuration,
                    updated_at=utc_now(),
                )
                connection.execute(
                    "INSERT INTO application_profiles "
                    "(profile_id, revision, configuration_json, updated_at) VALUES (?, ?, ?, ?)",
                    (
                        profile.profile_id,
                        profile.revision,
                        _canonical_json(profile.configuration),
                        profile.updated_at.isoformat(),
                    ),
                )
                return profile
            if expected_revision != existing.revision:
                raise ProjectStorageConflictError("provider profile revision is stale")
            profile = ApplicationProfile(
                profile_id=profile_id,
                revision=existing.revision + 1,
                configuration=configuration,
                updated_at=utc_now(),
            )
            connection.execute(
                "UPDATE application_profiles SET revision = ?, configuration_json = ?, updated_at = ? "
                "WHERE profile_id = ? AND revision = ?",
                (
                    profile.revision,
                    _canonical_json(profile.configuration),
                    profile.updated_at.isoformat(),
                    profile.profile_id,
                    existing.revision,
                ),
            )
            return profile

    def select_profile(self, profile_id: str) -> ApplicationProfile:
        with self._write() as connection:
            row = connection.execute(
                "SELECT profile_id, revision, configuration_json, updated_at "
                "FROM application_profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            if row is None:
                raise ProjectStorageError(f"application provider profile not found: {profile_id}")
            connection.execute(
                "INSERT INTO application_preferences (preference_key, profile_id) VALUES ('selected_profile', ?) "
                "ON CONFLICT(preference_key) DO UPDATE SET profile_id = excluded.profile_id",
                (profile_id,),
            )
            return self._profile_from_row(row)

    def selected_profile(self) -> ApplicationProfile | None:
        with self._read() as connection:
            row = connection.execute(
                "SELECT profile_id, revision, configuration_json, updated_at FROM application_profiles "
                "WHERE profile_id = (SELECT profile_id FROM application_preferences "
                "WHERE preference_key = 'selected_profile')"
            ).fetchone()
        return self._profile_from_row(row) if row is not None else None

    def save_text_profile(
        self,
        profile: "TextProviderProfileSnapshot | TextProviderProfileSnapshotV3",
        *,
        expected_revision: int | None = None,
    ) -> ApplicationProfile:
        return self.save_profile(
            profile.profile_id,
            profile.model_dump(mode="json", by_alias=True),
            expected_revision=expected_revision,
        )

    def selected_text_profile(self) -> "TextProviderProfileSnapshot | TextProviderProfileSnapshotV3":
        from .provider_profiles import TextProviderProfileSnapshot, TextProviderProfileSnapshotV3

        selected = self.selected_profile()
        if selected is None:
            raise ProjectStorageError("no application text provider profile is selected")
        try:
            if selected.configuration.get("profileSchemaVersion") == 3:
                return TextProviderProfileSnapshotV3.model_validate(selected.configuration)
            return TextProviderProfileSnapshot.model_validate(selected.configuration)
        except ValueError as error:
            raise ProjectStorageCorruptionError(
                "selected application profile is not a valid secret-free text profile"
            ) from error

    def record_accounting(self, entry: GlobalAccountingEntry) -> GlobalAccountingEntry:
        with self._write() as connection:
            try:
                connection.execute(
                    "INSERT INTO global_accounting "
                    "(dispatch_identity, resource, reserved_units, status, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        entry.dispatch_identity,
                        entry.resource,
                        entry.reserved_units,
                        entry.status,
                        entry.created_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ProjectStorageConflictError(
                    f"global accounting identity already exists: {entry.dispatch_identity}"
                ) from error
        return entry

    def accounting_entries(self) -> list[GlobalAccountingEntry]:
        with self._read() as connection:
            rows = connection.execute(
                "SELECT dispatch_identity, resource, reserved_units, status, created_at "
                "FROM global_accounting ORDER BY created_at, dispatch_identity"
            ).fetchall()
        return [
            GlobalAccountingEntry(
                dispatch_identity=row["dispatch_identity"],
                resource=row["resource"],
                reserved_units=row["reserved_units"],
                status=row["status"],
                created_at=row["created_at"],
            )
            for row in rows
        ]


class _OwnedArtifactStore:
    """Project-relative immutable bytes with confinement and hard-link checks."""

    def __init__(self, project_home: Path) -> None:
        self.project_home = project_home.resolve()
        self.assets_root = _require_real_directory(self.project_home / "assets", label="project assets root")

    def _path_for(self, relative_path: PurePosixPath, *, final_must_exist: bool) -> Path:
        if relative_path.parts[:1] != ("assets",):
            raise ProjectStorageConfinementError("owned artifacts must live below assets/")
        if self.project_home.is_symlink() or not self.project_home.is_dir():
            raise ProjectStorageConfinementError("project home must remain a real directory")
        candidate = self.project_home.joinpath(*relative_path.parts)
        parent = candidate.parent
        if parent.is_symlink() or any(part.is_symlink() for part in parent.parents if part != self.project_home):
            raise ProjectStorageConfinementError("owned artifact path must not traverse a symlink")
        resolved_parent = parent.resolve()
        if self.project_home != resolved_parent and self.project_home not in resolved_parent.parents:
            raise ProjectStorageConfinementError("owned artifact path escapes the project home")
        if final_must_exist:
            if candidate.is_symlink() or not candidate.is_file():
                raise ProjectStorageConfinementError("owned artifact is missing or not a regular file")
            if candidate.stat().st_nlink != 1:
                raise ProjectStorageConfinementError("owned artifact must not be hard linked")
        return candidate

    def put(self, contents: bytes, *, media_type: str) -> OwnedArtifact:
        content_hash = _sha256(contents)
        relative_path = PurePosixPath("assets") / content_hash[:2] / content_hash
        path = self._path_for(relative_path, final_must_exist=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = self._path_for(relative_path, final_must_exist=True)
            if _sha256(existing.read_bytes()) != content_hash:
                raise ProjectStorageCorruptionError("owned artifact hash path has different bytes")
        else:
            _write_new_file(path, contents)
        return OwnedArtifact(
            content_hash=content_hash,
            relative_path=relative_path.as_posix(),
            media_type=media_type,
            size_bytes=len(contents),
        )

    def read(self, artifact: OwnedArtifact) -> bytes:
        relative_path = _relative_owned_path(artifact.relative_path)
        path = self._path_for(relative_path, final_must_exist=True)
        contents = path.read_bytes()
        if len(contents) != artifact.size_bytes or _sha256(contents) != artifact.content_hash:
            raise ProjectStorageCorruptionError("owned artifact bytes do not match stored identity")
        return contents


class ProjectStore:
    """One project home and its directly authoritative canonical repository."""

    def __init__(self, project_home: Path, manifest: ProjectManifest, *, create_schema: bool) -> None:
        self.home = project_home.resolve()
        self.manifest = manifest
        self.database_path = self.home / manifest.database_path
        if self.database_path.is_symlink():
            raise ProjectStorageConfinementError("project database must not be a symlink")
        self._repository = ProjectSQLiteRepository(
            f"sqlite:///{self.database_path}",
            project_id=manifest.project_id,
            create_schema=create_schema,
        )
        self._artifacts = _OwnedArtifactStore(self.home)

    @property
    def repository(self) -> ProjectSQLiteRepository:
        return self._repository

    @classmethod
    def initialize(cls, project_home: Path, manifest: ProjectManifest, project: Project) -> "ProjectStore":
        if project.id != manifest.project_id:
            raise ProjectStorageCorruptionError("new project and manifest identities differ")
        store = cls(project_home, manifest, create_schema=True)
        try:
            store.repository.initialize_project(project)
        except BaseException:
            store.repository.close()
            raise
        return store

    @classmethod
    def open(cls, project_home: Path) -> "ProjectStore":
        if project_home.is_symlink() or not project_home.is_dir():
            raise ProjectStorageConfinementError("project home must be a real directory")
        home = project_home.resolve()
        manifest_path = home / PROJECT_MANIFEST_FILENAME
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ProjectStorageCorruptionError("project home has no regular manifest")
        try:
            manifest = ProjectManifest.model_validate(_read_json(manifest_path))
        except ValueError as error:
            raise ProjectStorageCorruptionError("project manifest does not meet this storage format") from error
        store = cls(home, manifest, create_schema=False)
        try:
            store._validate_opened_project()
        except BaseException:
            store.repository.close()
            raise
        return store

    def _validate_opened_project(self) -> None:
        if not self.database_path.exists() or not self.database_path.is_file():
            raise ProjectStorageCorruptionError("project database is missing or not a regular file")
        try:
            project = self.repository.get_project(self.manifest.project_id)
            heads = self.repository.list_stage_heads(self.manifest.project_id)
        except (NotFoundError, SQLAlchemyError, ValueError) as error:
            raise ProjectStorageCorruptionError("project database cannot satisfy the project repository contract") from error
        if project.id != self.manifest.project_id or len(heads) != len(STAGE_ORDER):
            raise ProjectStorageCorruptionError("manifest and project database identities differ")

    def close(self) -> None:
        self.repository.close()

    def project(self) -> Project:
        try:
            return self.repository.get_project(self.manifest.project_id)
        except NotFoundError as error:
            raise ProjectStorageCorruptionError("project database has no bound project") from error

    def update_brief(self, brief: ProjectBrief, *, expected_revision: int) -> Project:
        if expected_revision < 1:
            raise ValueError("expected_revision must be at least one")
        try:
            return self.repository.update_project(self.manifest.project_id, expected_revision, brief)
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
        """Commit only the exact draft receipt that supplied this brief."""

        if expected_revision < 1:
            raise ValueError("expected_revision must be at least one")
        try:
            return self.repository.update_project_consuming_authoring_draft(
                self.manifest.project_id,
                expected_revision,
                brief,
                entity_id=entity_id,
                expected_draft_revision=expected_draft_revision,
            )
        except RevisionConflictError as error:
            raise ProjectStorageConflictError("canonical save draft receipt is stale") from error

    def update_stage(
        self,
        stage: StageName,
        payload: dict[str, Any],
        *,
        expected_revision: int,
    ) -> StageHead:
        try:
            return self.repository.update_stage(
                self.manifest.project_id,
                stage,
                expected_revision,
                payload,
            )
        except RevisionConflictError as error:
            raise ProjectStorageConflictError(f"{stage.value} revision is stale") from error

    def update_stage_consuming_authoring_draft(
        self,
        stage: StageName,
        payload: dict[str, Any],
        *,
        expected_revision: int,
        entity_id: str,
        expected_draft_revision: int,
    ) -> StageHead:
        """Commit only the exact draft receipt that supplied this stage."""

        try:
            return self.repository.update_stage_consuming_authoring_draft(
                self.manifest.project_id,
                stage,
                expected_revision,
                payload,
                entity_id=entity_id,
                expected_draft_revision=expected_draft_revision,
            )
        except RevisionConflictError as error:
            raise ProjectStorageConflictError("canonical save draft receipt is stale") from error

    def authoring_drafts(self) -> list[AuthoringDraft]:
        return self.repository.list_authoring_drafts(self.manifest.project_id)

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
            return self.repository.upsert_authoring_draft(
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
        return self.repository.discard_authoring_draft(
            self.manifest.project_id,
            editor_scope=editor_scope,
            entity_id=entity_id,
            expected_draft_revision=expected_draft_revision,
        )

    def canonical_stages(self) -> list[StageEnvelope]:
        envelopes = self.repository.list_stage_envelopes(self.manifest.project_id)
        ready = [item for item in envelopes if item.head.status == StageStatus.READY]
        if not ready:
            return []
        if len(ready) != len(STAGE_ORDER):
            raise ProjectStorageCorruptionError("project pipeline has partial canonical heads")
        return ready

    def generation_runs(self) -> list[GenerationRun]:
        return list(reversed(self.repository.list_project_runs(self.manifest.project_id, limit=200)))

    def run_trace(self, run_id: str) -> RunTrace:
        trace = self.repository.get_run_trace(run_id)
        if trace.run.project_id != self.manifest.project_id:
            raise ProjectStorageCorruptionError("run evidence belongs to another project")
        return trace

    def run_execution_trace(self, run_id: str) -> RunExecutionTrace:
        return self.repository.get_run_execution_trace(run_id)

    def repair_scope(self, child_run_id: str) -> WorkUnitRepairScope:
        return self.repository.get_work_unit_repair_scope(child_run_id)

    def fragment_reuse_bindings(self, child_run_id: str) -> list[FragmentReuseBinding]:
        return self.repository.get_fragment_reuse_bindings(child_run_id)

    def read_artifact(self, artifact: OwnedArtifact) -> bytes:
        return self._artifacts.read(artifact)


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
            raise ProjectStorageConflictError(f"project home already exists: {directory_name}") from error
        return home

    def create(self, brief: ProjectBrief) -> ProjectStore:
        project = Project(brief=brief)
        home = self._new_home(project)
        manifest = ProjectManifest(project_id=project.id, created_at=project.created_at)
        _write_new_file(
            home / PROJECT_MANIFEST_FILENAME,
            (_canonical_json(manifest.model_dump(mode="json", by_alias=True)) + "\n").encode("utf-8"),
        )
        return ProjectStore.initialize(home, manifest, project)

    def discover(self) -> list[ProjectHome]:
        homes: list[ProjectHome] = []
        for candidate in sorted(self.outputs_root.iterdir(), key=lambda path: path.name):
            if candidate.name.startswith(".") or candidate.is_symlink() or not candidate.is_dir():
                continue
            manifest_path = candidate / PROJECT_MANIFEST_FILENAME
            if manifest_path.is_symlink() or not manifest_path.is_file():
                continue
            try:
                manifest = ProjectManifest.model_validate(_read_json(manifest_path))
                store = ProjectStore.open(candidate)
                store.close()
            except (ProjectStorageError, ValueError, SQLAlchemyError):
                continue
            homes.append(ProjectHome(path=candidate.resolve(), manifest=manifest))
        return homes

    def open(self, project_id: str) -> ProjectStore:
        matches = [home for home in self.discover() if home.manifest.project_id == project_id]
        if not matches:
            raise ProjectStorageError(f"project not found in outputs root: {project_id}")
        if len(matches) > 1:
            raise ProjectStorageCorruptionError(f"multiple project homes share identity: {project_id}")
        return ProjectStore.open(matches[0].path)


class ProjectFolderStorage:
    """Explicit composition root for the project/application ownership split."""

    def __init__(self, *, outputs_root: Path, application_data_root: Path) -> None:
        resolved_outputs = outputs_root.expanduser().resolve()
        resolved_application = application_data_root.expanduser().resolve()
        if (
            resolved_outputs == resolved_application
            or resolved_outputs.is_relative_to(resolved_application)
            or resolved_application.is_relative_to(resolved_outputs)
        ):
            raise ProjectStorageConfinementError(
                "outputs and application data roots must be separate, non-overlapping directories"
            )
        self.projects = ProjectDirectoryRegistry(outputs_root)
        self.application = ApplicationStore(application_data_root)

    def execute_selected_text_pipeline(
        self,
        project_id: str,
        *,
        provider_resolver: "TextProviderResolver",
        exact_repair: bool = False,
        secret_broker: "RunSecretBroker | None" = None,
        session_api_key: str | None = None,
    ) -> GenerationRun:
        """Run the selected public profile against the project-owned database."""

        from .project_generation_storage import ProjectPipelineExecutor

        return ProjectPipelineExecutor(provider_resolver).execute(
            self.projects.open(project_id),
            profile=self.application.selected_text_profile(),
            exact_repair=exact_repair,
            secret_broker=secret_broker,
            session_api_key=session_api_key,
        )
