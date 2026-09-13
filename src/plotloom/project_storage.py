"""Project-folder storage construction seam.

This module deliberately does not wire the retained shared-database runtime.
It establishes the format and ownership boundary that the later cutover will
use: every project owns one SQLite file and its immutable bytes, while reusable
provider profiles and global accounting belong to the installation.
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

from .domain import (
    Artifact,
    CamelModel,
    EntityRevision,
    FragmentReuseBinding,
    GenerationAttempt,
    GenerationPlanTrace,
    GenerationRun,
    GenerationWorkUnitTrace,
    Project,
    ProjectBrief,
    RunExecutionTrace,
    RunTrace,
    SealedStageAggregateTrace,
    STAGE_ORDER,
    StageEnvelope,
    StageHead,
    StagePlanTrace,
    WorkUnitRepairScope,
    contains_secret_setting,
    contains_secret_value,
    utc_now,
)

if TYPE_CHECKING:
    from .project_generation_storage import ProjectGenerationEvidence


# Checkpoint 2A replaces checkpoint 1's synthetic run schema with canonical
# revisions and durable generation lineage. It is intentionally a fresh,
# incompatible project-home format rather than an implicit migration or a
# dual-read compatibility path.
PROJECT_STORAGE_FORMAT_VERSION = 2
PROJECT_DATABASE_RELATIVE_PATH = "project.sqlite3"
PROJECT_MANIFEST_FILENAME = "project.json"


class ProjectStorageError(RuntimeError):
    """Base error for the isolated project-folder storage boundary."""


class ProjectStorageConflictError(ProjectStorageError):
    """Raised when a project edit is based on a stale project revision."""


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

    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # The path was allocated exclusively, so retaining a partial immutable
        # file would turn a retry into a false success. Remove only that exact
        # just-created file.
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
        existing: ApplicationProfile | None = None
        with self._write() as connection:
            row = connection.execute(
                "SELECT profile_id, revision, configuration_json, updated_at "
                "FROM application_profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            if row is not None:
                existing = self._profile_from_row(row)
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
        """Persist only public text-profile configuration in application storage."""

        return self.save_profile(
            profile.profile_id,
            profile.model_dump(mode="json", by_alias=True),
            expected_revision=expected_revision,
        )

    def selected_text_profile(self) -> "TextProviderProfileSnapshot | TextProviderProfileSnapshotV3":
        """Resolve the selected public profile; credentials stay outside storage."""

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
    """Project-local content-addressed bytes with a no-escape read contract."""

    def __init__(self, project_home: Path) -> None:
        self.project_home = project_home
        self.root = _require_real_directory(project_home / "assets", label="project assets root")

    def _path_for(self, relative_path: PurePosixPath, *, final_must_exist: bool) -> Path:
        """Resolve an artifact component-by-component without following links."""

        if relative_path.parts[:1] != ("assets",):
            raise ProjectStorageConfinementError("owned artifacts must live below assets/")
        if self.project_home.is_symlink() or not self.project_home.is_dir():
            raise ProjectStorageConfinementError("project home must remain a real directory")
        current = self.project_home
        for index, component in enumerate(relative_path.parts):
            current = current / component
            if current.is_symlink():
                raise ProjectStorageConfinementError("owned artifact path contains a symlink")
            is_final = index == len(relative_path.parts) - 1
            if not is_final and current.exists() and not current.is_dir():
                raise ProjectStorageConfinementError("owned artifact parent is not a directory")
        if final_must_exist and not current.exists():
            raise ProjectStorageCorruptionError("owned artifact is missing")
        return current

    def put(self, contents: bytes, *, media_type: str) -> OwnedArtifact:
        content_hash = _sha256(contents)
        relative_path = PurePosixPath("assets") / content_hash[:2] / content_hash
        directory = self._path_for(relative_path.parent, final_must_exist=False)
        directory.mkdir(parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise ProjectStorageConfinementError("asset hash directory must be a real directory")
        path = self._path_for(relative_path, final_must_exist=False)
        if path.exists():
            if path.is_symlink() or not path.is_file():
                raise ProjectStorageConfinementError("existing asset path is not a regular file")
            if path.stat(follow_symlinks=False).st_nlink != 1:
                raise ProjectStorageConfinementError("owned assets must not be hard linked")
            existing = path.read_bytes()
            if _sha256(existing) != content_hash:
                raise ProjectStorageCorruptionError("asset path does not match its content hash")
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
        if path.is_symlink() or not path.is_file():
            raise ProjectStorageCorruptionError("owned artifact is missing or not a regular file")
        if path.stat(follow_symlinks=False).st_nlink != 1:
            raise ProjectStorageConfinementError("owned assets must not be hard linked")
        contents = path.read_bytes()
        if len(contents) != artifact.size_bytes or _sha256(contents) != artifact.content_hash:
            raise ProjectStorageCorruptionError("owned artifact bytes do not match stored identity")
        return contents


class ProjectStore:
    """One project database plus assets beneath one validated project home."""

    def __init__(self, project_home: Path, manifest: ProjectManifest) -> None:
        self.home = project_home.resolve()
        self.manifest = manifest
        self.database_path = self.home / manifest.database_path
        if self.database_path.is_symlink():
            raise ProjectStorageConfinementError("project database must not be a symlink")
        self._artifacts = _OwnedArtifactStore(self.home)

    @classmethod
    def initialize(cls, project_home: Path, manifest: ProjectManifest, project: Project) -> "ProjectStore":
        if project.id != manifest.project_id:
            raise ProjectStorageCorruptionError("manifest and initial project identity differ")
        store = cls(project_home, manifest)
        store._initialize_schema()
        with store._write() as connection:
            connection.execute(
                "INSERT INTO project_state "
                "(singleton, project_id, revision, lifecycle_revision, lifecycle_status, archived_at, brief_json, created_at, updated_at) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project.id,
                    project.revision,
                    project.lifecycle_revision,
                    project.lifecycle_status.value,
                    project.archived_at.isoformat() if project.archived_at else None,
                    _canonical_json(project.brief.model_dump(mode="json", by_alias=True)),
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                ),
            )
        return store

    @classmethod
    def open(cls, project_home: Path) -> "ProjectStore":
        home = project_home.resolve()
        if project_home.is_symlink() or not home.is_dir():
            raise ProjectStorageConfinementError("project home must be a real directory")
        manifest_path = home / PROJECT_MANIFEST_FILENAME
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise ProjectStorageCorruptionError("project manifest is missing or not a regular file")
        try:
            manifest = ProjectManifest.model_validate(_read_json(manifest_path))
        except ValueError as error:
            raise ProjectStorageCorruptionError("project manifest does not match this format") from error
        store = cls(home, manifest)
        store._validate_opened_project()
        return store

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, isolation_level=None)
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
                CREATE TABLE IF NOT EXISTS project_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    project_id TEXT NOT NULL UNIQUE,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    lifecycle_revision INTEGER NOT NULL CHECK (lifecycle_revision >= 1),
                    lifecycle_status TEXT NOT NULL CHECK (lifecycle_status IN ('active', 'archived')),
                    archived_at TEXT,
                    brief_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS canonical_entity_revisions (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES project_state(project_id) ON DELETE RESTRICT,
                    stage TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    evidence_json TEXT NOT NULL,
                    UNIQUE(project_id, stage, revision)
                );
                CREATE TABLE IF NOT EXISTS canonical_stage_heads (
                    project_id TEXT NOT NULL REFERENCES project_state(project_id) ON DELETE RESTRICT,
                    stage TEXT NOT NULL,
                    entity_revision_id TEXT REFERENCES canonical_entity_revisions(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL,
                    PRIMARY KEY(project_id, stage)
                );
                CREATE TABLE IF NOT EXISTS generation_run_evidence (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES project_state(project_id) ON DELETE RESTRICT,
                    parent_run_id TEXT REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS generation_attempt_evidence (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS generation_artifact_evidence (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS generation_plan_evidence (
                    run_id TEXT PRIMARY KEY REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS generation_stage_plan_evidence (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS generation_work_unit_evidence (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    stage_plan_id TEXT NOT NULL REFERENCES generation_stage_plan_evidence(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sealed_stage_aggregate_evidence (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    stage_plan_id TEXT NOT NULL REFERENCES generation_stage_plan_evidence(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS work_unit_repair_scope_evidence (
                    child_run_id TEXT PRIMARY KEY REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    parent_run_id TEXT NOT NULL REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS generation_fragment_reuse_binding_evidence (
                    id TEXT PRIMARY KEY,
                    child_run_id TEXT NOT NULL REFERENCES generation_run_evidence(id) ON DELETE RESTRICT,
                    evidence_json TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _project_from_row(row: sqlite3.Row) -> Project:
        return Project(
            id=row["project_id"],
            revision=row["revision"],
            lifecycle_revision=row["lifecycle_revision"],
            lifecycle_status=row["lifecycle_status"],
            archived_at=row["archived_at"],
            brief=json.loads(row["brief_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _validate_opened_project(self) -> None:
        if not self.database_path.exists() or not self.database_path.is_file():
            raise ProjectStorageCorruptionError("project database is missing or not a regular file")
        try:
            with self._read() as connection:
                row = connection.execute(
                    "SELECT project_id, revision, lifecycle_revision, lifecycle_status, archived_at, brief_json, created_at, updated_at "
                    "FROM project_state WHERE singleton = 1"
                ).fetchone()
                if row is not None:
                    mismatched_run = connection.execute(
                        "SELECT id FROM generation_run_evidence WHERE project_id != ? LIMIT 1",
                        (self.manifest.project_id,),
                    ).fetchone()
        except sqlite3.DatabaseError as error:
            raise ProjectStorageCorruptionError("project database cannot be opened") from error
        if row is None:
            raise ProjectStorageCorruptionError("project database has no project state")
        project = self._project_from_row(row)
        if project.id != self.manifest.project_id:
            raise ProjectStorageCorruptionError("manifest and project database identities differ")
        if mismatched_run is not None:
            raise ProjectStorageCorruptionError("project database contains a run for another project")

    def project(self) -> Project:
        with self._read() as connection:
            row = connection.execute(
                "SELECT project_id, revision, lifecycle_revision, lifecycle_status, archived_at, brief_json, created_at, updated_at "
                "FROM project_state WHERE singleton = 1"
            ).fetchone()
        if row is None:
            raise ProjectStorageCorruptionError("project database has no project state")
        return self._project_from_row(row)

    def update_brief(self, brief: ProjectBrief, *, expected_revision: int) -> Project:
        if expected_revision < 1:
            raise ValueError("expected_revision must be at least one")
        now = utc_now()
        with self._write() as connection:
            row = connection.execute(
                "SELECT project_id, revision, lifecycle_revision, lifecycle_status, archived_at, brief_json, created_at, updated_at "
                "FROM project_state WHERE singleton = 1"
            ).fetchone()
            if row is None:
                raise ProjectStorageCorruptionError("project database has no project state")
            current = self._project_from_row(row)
            if current.revision != expected_revision:
                raise ProjectStorageConflictError("project revision is stale")
            next_project = current.model_copy(
                update={"brief": brief, "revision": current.revision + 1, "updated_at": now}
            )
            changed = connection.execute(
                "UPDATE project_state SET revision = ?, brief_json = ?, updated_at = ? "
                "WHERE singleton = 1 AND revision = ?",
                (
                    next_project.revision,
                    _canonical_json(next_project.brief.model_dump(mode="json", by_alias=True)),
                    next_project.updated_at.isoformat(),
                    expected_revision,
                ),
            ).rowcount
            if changed != 1:
                raise ProjectStorageConflictError("project revision changed during update")
        return next_project

    def install_generation_evidence(self, evidence: "ProjectGenerationEvidence") -> GenerationRun:
        """Atomically install only a complete, current canonical pipeline result.

        The existing durable runner executes in a disposable harness so this
        new-format seam can remain unwired.  This projection is deliberately
        strict: a result is copied to its project home only after the same
        domain contracts have produced every sealed stage and its full
        secret-free lineage.  The transaction is the only canonical commit
        point in this storage format.
        """

        current = self.project()
        evidence.validate_for_install(project=current)
        with self._write() as connection:
            existing = connection.execute(
                "SELECT 1 FROM canonical_stage_heads WHERE project_id = ? LIMIT 1",
                (current.id,),
            ).fetchone()
            if existing is not None:
                raise ProjectStorageConflictError("canonical pipeline evidence is already installed")
            row = connection.execute(
                "SELECT project_id, revision, lifecycle_revision, lifecycle_status, archived_at, brief_json, created_at, updated_at "
                "FROM project_state WHERE singleton = 1"
            ).fetchone()
            if row is None:
                raise ProjectStorageCorruptionError("project database has no project state")
            latest = self._project_from_row(row)
            evidence.validate_for_install(project=latest)
            self._insert_generation_evidence(connection, evidence)
        return evidence.install_run

    def _insert_generation_evidence(
        self,
        connection: sqlite3.Connection,
        evidence: "ProjectGenerationEvidence",
    ) -> None:
        for revision in evidence.entity_revisions:
            connection.execute(
                "INSERT INTO canonical_entity_revisions (id, project_id, stage, revision, evidence_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    revision.id,
                    revision.project_id,
                    revision.stage.value,
                    revision.revision,
                    _canonical_json(revision.model_dump(mode="json", by_alias=False)),
                ),
            )
        for envelope in evidence.stages:
            connection.execute(
                "INSERT INTO canonical_stage_heads (project_id, stage, entity_revision_id, evidence_json) "
                "VALUES (?, ?, ?, ?)",
                (
                    self.manifest.project_id,
                    envelope.head.stage.value,
                    envelope.head.entity_revision_id,
                    _canonical_json(envelope.head.model_dump(mode="json", by_alias=False)),
                ),
            )
        for trace in evidence.run_traces:
            run = trace.run
            connection.execute(
                "INSERT INTO generation_run_evidence (id, project_id, parent_run_id, evidence_json) VALUES (?, ?, ?, ?)",
                (
                    run.id,
                    run.project_id,
                    run.parent_run_id,
                    _canonical_json(run.model_dump(mode="json", by_alias=False)),
                ),
            )
            for attempt in trace.attempts:
                connection.execute(
                    "INSERT INTO generation_attempt_evidence (id, run_id, evidence_json) VALUES (?, ?, ?)",
                    (attempt.id, attempt.run_id, _canonical_json(attempt.model_dump(mode="json", by_alias=False))),
                )
            for artifact in trace.artifacts:
                connection.execute(
                    "INSERT INTO generation_artifact_evidence (id, run_id, evidence_json) VALUES (?, ?, ?)",
                    (artifact.id, artifact.run_id, _canonical_json(artifact.model_dump(mode="json", by_alias=False))),
                )
        for item in evidence.execution_traces:
            trace = item.trace
            if trace.generation_plan is not None:
                connection.execute(
                    "INSERT INTO generation_plan_evidence (run_id, evidence_json) VALUES (?, ?)",
                    (item.run_id, _canonical_json(trace.generation_plan.model_dump(mode="json", by_alias=False))),
                )
            for stage_plan in trace.stage_plans:
                connection.execute(
                    "INSERT INTO generation_stage_plan_evidence (id, run_id, evidence_json) VALUES (?, ?, ?)",
                    (stage_plan.id, item.run_id, _canonical_json(stage_plan.model_dump(mode="json", by_alias=False))),
                )
            for unit in trace.work_units:
                connection.execute(
                    "INSERT INTO generation_work_unit_evidence (id, run_id, stage_plan_id, evidence_json) VALUES (?, ?, ?, ?)",
                    (unit.id, item.run_id, unit.stage_plan_id, _canonical_json(unit.model_dump(mode="json", by_alias=False))),
                )
            for seal in trace.sealed_aggregates:
                connection.execute(
                    "INSERT INTO sealed_stage_aggregate_evidence (id, run_id, stage_plan_id, evidence_json) VALUES (?, ?, ?, ?)",
                    (seal.id, item.run_id, seal.stage_plan_id, _canonical_json(seal.model_dump(mode="json", by_alias=False))),
                )
        for scope in evidence.repair_scopes:
            connection.execute(
                "INSERT INTO work_unit_repair_scope_evidence (child_run_id, parent_run_id, evidence_json) VALUES (?, ?, ?)",
                (scope.child_run_id, scope.parent_run_id, _canonical_json(scope.model_dump(mode="json", by_alias=False))),
            )
        for binding in evidence.fragment_reuse_bindings:
            connection.execute(
                "INSERT INTO generation_fragment_reuse_binding_evidence (id, child_run_id, evidence_json) VALUES (?, ?, ?)",
                (binding.id, binding.child_run_id, _canonical_json(binding.model_dump(mode="json", by_alias=False))),
            )

    def canonical_stages(self) -> list[StageEnvelope]:
        with self._read() as connection:
            rows = {
                row["stage"]: row
                for row in connection.execute(
                    "SELECT stage, entity_revision_id, evidence_json FROM canonical_stage_heads WHERE project_id = ?",
                    (self.manifest.project_id,),
                ).fetchall()
            }
            if not rows:
                return []
            envelopes: list[StageEnvelope] = []
            for stage in STAGE_ORDER:
                row = rows.get(stage.value)
                if row is None:
                    raise ProjectStorageCorruptionError("canonical stage evidence is incomplete")
                head = StageHead.model_validate(json.loads(row["evidence_json"]))
                revision_row = connection.execute(
                    "SELECT evidence_json FROM canonical_entity_revisions WHERE id = ?",
                    (row["entity_revision_id"],),
                ).fetchone()
                if revision_row is None:
                    raise ProjectStorageCorruptionError("canonical stage head references a missing revision")
                revision = EntityRevision.model_validate(json.loads(revision_row["evidence_json"]))
                envelopes.append(StageEnvelope(head=head, payload=revision.payload))
        return envelopes

    def generation_runs(self) -> list[GenerationRun]:
        with self._read() as connection:
            rows = connection.execute(
                "SELECT evidence_json FROM generation_run_evidence ORDER BY rowid"
            ).fetchall()
        runs = [GenerationRun.model_validate(json.loads(row["evidence_json"])) for row in rows]
        if any(run.project_id != self.manifest.project_id for run in runs):
            raise ProjectStorageCorruptionError("project database contains a run for another project")
        return runs

    def run_trace(self, run_id: str) -> RunTrace:
        with self._read() as connection:
            run_row = connection.execute(
                "SELECT evidence_json FROM generation_run_evidence WHERE id = ?", (run_id,)
            ).fetchone()
            if run_row is None:
                raise ProjectStorageError(f"generation run not found: {run_id}")
            run = GenerationRun.model_validate(json.loads(run_row["evidence_json"]))
            attempts = [
                GenerationAttempt.model_validate(json.loads(row["evidence_json"]))
                for row in connection.execute(
                    "SELECT evidence_json FROM generation_attempt_evidence WHERE run_id = ? ORDER BY rowid",
                    (run_id,),
                ).fetchall()
            ]
            artifacts = [
                Artifact.model_validate(json.loads(row["evidence_json"]))
                for row in connection.execute(
                    "SELECT evidence_json FROM generation_artifact_evidence WHERE run_id = ? ORDER BY rowid",
                    (run_id,),
                ).fetchall()
            ]
        return RunTrace(run=run, attempts=attempts, artifacts=artifacts, snapshot_is_current=True)

    def run_execution_trace(self, run_id: str) -> RunExecutionTrace:
        with self._read() as connection:
            if connection.execute(
                "SELECT 1 FROM generation_run_evidence WHERE id = ?", (run_id,)
            ).fetchone() is None:
                raise ProjectStorageError(f"generation run not found: {run_id}")
            plan_row = connection.execute(
                "SELECT evidence_json FROM generation_plan_evidence WHERE run_id = ?", (run_id,)
            ).fetchone()
            topology = None
            stage_plans = [
                StagePlanTrace.model_validate(json.loads(row["evidence_json"]))
                for row in connection.execute(
                    "SELECT evidence_json FROM generation_stage_plan_evidence WHERE run_id = ? ORDER BY rowid",
                    (run_id,),
                ).fetchall()
            ]
            units = [
                GenerationWorkUnitTrace.model_validate(json.loads(row["evidence_json"]))
                for row in connection.execute(
                    "SELECT evidence_json FROM generation_work_unit_evidence WHERE run_id = ? ORDER BY rowid",
                    (run_id,),
                ).fetchall()
            ]
            seals = [
                SealedStageAggregateTrace.model_validate(json.loads(row["evidence_json"]))
                for row in connection.execute(
                    "SELECT evidence_json FROM sealed_stage_aggregate_evidence WHERE run_id = ? ORDER BY rowid",
                    (run_id,),
                ).fetchall()
            ]
        return RunExecutionTrace(
            generation_plan=(
                GenerationPlanTrace.model_validate(json.loads(plan_row["evidence_json"]))
                if plan_row is not None
                else None
            ),
            story_graph_topology=topology,
            stage_plans=stage_plans,
            work_units=units,
            sealed_aggregates=seals,
        )

    def repair_scope(self, child_run_id: str) -> WorkUnitRepairScope:
        with self._read() as connection:
            row = connection.execute(
                "SELECT evidence_json FROM work_unit_repair_scope_evidence WHERE child_run_id = ?",
                (child_run_id,),
            ).fetchone()
        if row is None:
            raise ProjectStorageError(f"repair scope not found: {child_run_id}")
        return WorkUnitRepairScope.model_validate(json.loads(row["evidence_json"]))

    def fragment_reuse_bindings(self, child_run_id: str) -> list[FragmentReuseBinding]:
        with self._read() as connection:
            rows = connection.execute(
                "SELECT evidence_json FROM generation_fragment_reuse_binding_evidence "
                "WHERE child_run_id = ? ORDER BY rowid",
                (child_run_id,),
            ).fetchall()
        return [FragmentReuseBinding.model_validate(json.loads(row["evidence_json"])) for row in rows]

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
            # A UUID collision must never be repaired by reusing or replacing a
            # folder. The caller can explicitly retry creation with a new ID.
            raise ProjectStorageConflictError(f"project home already exists: {directory_name}") from error
        return home

    def create(self, brief: ProjectBrief) -> ProjectStore:
        project = Project(brief=brief)
        home = self._new_home(project)
        manifest = ProjectManifest(project_id=project.id, created_at=project.created_at)
        manifest_path = home / PROJECT_MANIFEST_FILENAME
        _write_new_file(
            manifest_path,
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
                ProjectStore.open(candidate)
            except (ProjectStorageError, ValueError):
                # Registration is rebuildable. An invalid folder is not
                # silently treated as another project's data.
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
    ) -> GenerationRun:
        """Run a selected public profile through the unwired project-folder seam.

        The resolver receives only the snapshot frozen in each run.  Any
        credential lookup remains its ephemeral broker concern and cannot be
        persisted by this composition root.
        """

        from .project_generation_storage import ProjectPipelineExecutor

        return ProjectPipelineExecutor(provider_resolver).execute(
            self.projects.open(project_id),
            profile=self.application.selected_text_profile(),
            exact_repair=exact_repair,
        )
