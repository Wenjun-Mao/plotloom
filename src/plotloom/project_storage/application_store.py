"""Installation-scoped provider-profile and accounting store."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, model_validator

from ..domain import (
    TERMINAL_RUN_STATUSES,
    CamelModel,
    contains_secret_setting,
    contains_secret_value,
    utc_now,
)
from ..exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from .direct_video_accounting import DirectVideoDispatchAccounting, VideoDispatchLease
from .application_lifecycle import ApplicationProjectLifecycleLedger
from .format import (
    ProjectStorageConflictError,
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
    ProjectStorageError,
    _canonical_json,
    _require_real_directory,
)

if TYPE_CHECKING:
    from ..provider_profiles import (
        TextProviderProfileSnapshot,
        TextProviderProfileSnapshotV3,
    )


class ApplicationProfile(CamelModel):
    """Reusable public provider configuration owned by the installation."""

    profile_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    revision: int = Field(ge=1)
    configuration: dict[str, Any]
    updated_at: datetime

    @model_validator(mode="after")
    def reject_secret_configuration(self) -> "ApplicationProfile":
        if contains_secret_setting(self.configuration) or contains_secret_value(
            self.configuration
        ):
            raise ValueError(
                "application provider profiles must not contain credentials"
            )
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
        if contains_secret_value(self.dispatch_identity) or contains_secret_value(
            self.resource
        ):
            raise ValueError("global accounting identifiers must be public")
        return self


@dataclass(frozen=True)
class ApplicationRunRoute:
    """A rebuildable route and its frozen-profile deletion guard."""

    run_id: str
    project_id: str
    profile_id: str
    status: str


class ApplicationStore:
    """Small installation store for profiles, selection, and global accounting only."""

    def __init__(self, application_data_root: Path) -> None:
        self.root = _require_real_directory(
            application_data_root, label="application data root"
        )
        self.path = self.root / "application.sqlite3"
        if self.path.is_symlink():
            raise ProjectStorageConfinementError(
                "application database must not be a symlink"
            )
        self._video_dispatch = DirectVideoDispatchAccounting(
            read=self._read, write=self._write
        )
        self.project_lifecycle = ApplicationProjectLifecycleLedger(
            read=self._read, write=self._write
        )
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
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS application_profiles (
                    profile_id TEXT PRIMARY KEY, revision INTEGER NOT NULL CHECK (revision >= 1),
                    configuration_json TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS application_preferences (
                    preference_key TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL REFERENCES application_profiles(profile_id));
                CREATE TABLE IF NOT EXISTS global_accounting (
                    dispatch_identity TEXT PRIMARY KEY, resource TEXT NOT NULL,
                    reserved_units INTEGER NOT NULL CHECK (reserved_units >= 0),
                    status TEXT NOT NULL CHECK (status IN ('reserved', 'released', 'consumed')),
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS application_text_profile_metadata (
                    profile_id TEXT PRIMARY KEY REFERENCES application_profiles(profile_id) ON DELETE CASCADE,
                    display_name TEXT NOT NULL,
                    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                    availability_revision INTEGER NOT NULL CHECK (availability_revision >= 0),
                    adapter_id TEXT NOT NULL,
                    adapter_version TEXT NOT NULL,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS application_text_profile_selection (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    profile_id TEXT NOT NULL REFERENCES application_profiles(profile_id),
                    revision INTEGER NOT NULL CHECK (revision >= 0),
                    updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS application_run_routes (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    indexed_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS application_frozen_profile_run_references (
                    run_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL);""")
            self._video_dispatch.initialize_schema(connection)
            self.project_lifecycle.initialize_schema(connection)

    @staticmethod
    def _profile_from_row(row: sqlite3.Row) -> ApplicationProfile:
        return ApplicationProfile(
            profile_id=row["profile_id"],
            revision=row["revision"],
            configuration=json.loads(row["configuration_json"]),
            updated_at=row["updated_at"],
        )

    def _save_profile_in_transaction(
        self,
        connection: sqlite3.Connection,
        profile_id: str,
        configuration: dict[str, Any],
        *,
        expected_revision: int | None,
    ) -> ApplicationProfile:
        """Write a profile with the caller's enclosing transaction.

        Text profiles have companion metadata, so their control-plane record
        must use this primitive rather than committing configuration first and
        metadata later.
        """

        row = connection.execute(
            "SELECT profile_id, revision, configuration_json, updated_at FROM application_profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        existing = self._profile_from_row(row) if row is not None else None
        if existing is None:
            if expected_revision not in {None, 0}:
                raise ProjectStorageConflictError(
                    "provider profile does not exist at expected revision"
                )
            profile = ApplicationProfile(
                profile_id=profile_id,
                revision=1,
                configuration=configuration,
                updated_at=utc_now(),
            )
            connection.execute(
                "INSERT INTO application_profiles (profile_id, revision, configuration_json, updated_at) VALUES (?, ?, ?, ?)",
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
            "UPDATE application_profiles SET revision = ?, configuration_json = ?, updated_at = ? WHERE profile_id = ? AND revision = ?",
            (
                profile.revision,
                _canonical_json(profile.configuration),
                profile.updated_at.isoformat(),
                profile.profile_id,
                existing.revision,
            ),
        )
        return profile

    def save_profile(
        self,
        profile_id: str,
        configuration: dict[str, Any],
        *,
        expected_revision: int | None = None,
    ) -> ApplicationProfile:
        with self._write() as connection:
            return self._save_profile_in_transaction(
                connection,
                profile_id,
                configuration,
                expected_revision=expected_revision,
            )

    def save_text_profile_record(
        self,
        profile_id: str,
        configuration: dict[str, Any],
        *,
        display_name: str,
        adapter_id: str,
        adapter_version: str,
        expected_revision: int | None,
    ) -> ApplicationProfile:
        """Atomically persist a text profile and its required metadata."""

        with self._write() as connection:
            profile = self._save_profile_in_transaction(
                connection,
                profile_id,
                configuration,
                expected_revision=expected_revision,
            )
            metadata = connection.execute(
                "SELECT profile_id FROM application_text_profile_metadata WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            if profile.revision == 1:
                if metadata is not None:
                    raise ProjectStorageCorruptionError(
                        "new text provider profile already has metadata"
                    )
                connection.execute(
                    "INSERT INTO application_text_profile_metadata "
                    "(profile_id, display_name, enabled, availability_revision, adapter_id, adapter_version, created_at) "
                    "VALUES (?, ?, 1, 0, ?, ?, ?)",
                    (
                        profile_id,
                        display_name,
                        adapter_id,
                        adapter_version,
                        profile.updated_at.isoformat(),
                    ),
                )
            else:
                if metadata is None:
                    raise ProjectStorageCorruptionError(
                        "text provider profile metadata is missing"
                    )
                connection.execute(
                    "UPDATE application_text_profile_metadata SET display_name = ?, adapter_id = ?, "
                    "adapter_version = ? WHERE profile_id = ?",
                    (display_name, adapter_id, adapter_version, profile_id),
                )
            return profile

    def select_profile(self, profile_id: str) -> ApplicationProfile:
        with self._write() as connection:
            row = connection.execute(
                "SELECT profile_id, revision, configuration_json, updated_at FROM application_profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
            if row is None:
                raise ProjectStorageError(
                    f"application provider profile not found: {profile_id}"
                )
            connection.execute(
                "INSERT INTO application_preferences (preference_key, profile_id) VALUES ('selected_profile', ?) ON CONFLICT(preference_key) DO UPDATE SET profile_id = excluded.profile_id",
                (profile_id,),
            )
            return self._profile_from_row(row)

    def selected_profile(self) -> ApplicationProfile | None:
        with self._read() as connection:
            row = connection.execute(
                "SELECT profile_id, revision, configuration_json, updated_at FROM application_profiles WHERE profile_id = (SELECT profile_id FROM application_preferences WHERE preference_key = 'selected_profile')"
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

    def selected_text_profile(
        self,
    ) -> "TextProviderProfileSnapshot | TextProviderProfileSnapshotV3":
        from ..provider_profiles import (
            TextProviderProfileSnapshot,
            TextProviderProfileSnapshotV3,
        )

        selected = self.selected_profile()
        if selected is None:
            raise ProjectStorageError(
                "no application text provider profile is selected"
            )
        try:
            if selected.configuration.get("profileSchemaVersion") == 3:
                return TextProviderProfileSnapshotV3.model_validate(
                    selected.configuration
                )
            return TextProviderProfileSnapshot.model_validate(selected.configuration)
        except ValueError as error:
            raise ProjectStorageCorruptionError(
                "selected application profile is not a valid secret-free text profile"
            ) from error

    def reserve_run_route(self, route: ApplicationRunRoute) -> None:
        """Protect a frozen profile before a project transaction creates its run.

        A crash before project creation leaves only disposable ``pending``
        state, which startup reconstructs. Reversing the order could make a
        canonical project run invisible to every run-ID route.
        """

        with self._write() as connection:
            if connection.execute(
                "SELECT 1 FROM application_profiles WHERE profile_id = ?", (route.profile_id,)
            ).fetchone() is None:
                raise NotFoundError(f"text provider profile not found: {route.profile_id}")
            existing_route = connection.execute(
                "SELECT project_id FROM application_run_routes WHERE run_id = ?", (route.run_id,)
            ).fetchone()
            if existing_route is not None and existing_route["project_id"] != route.project_id:
                raise ProjectStorageConflictError("run ID is already routed to another project")
            existing_reference = connection.execute(
                "SELECT profile_id FROM application_frozen_profile_run_references WHERE run_id = ?",
                (route.run_id,),
            ).fetchone()
            if existing_reference is not None and existing_reference["profile_id"] != route.profile_id:
                raise ProjectStorageConflictError("run ID is already bound to another frozen profile")
            now = utc_now().isoformat()
            connection.execute(
                "INSERT INTO application_run_routes (run_id, project_id, indexed_at) VALUES (?, ?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET indexed_at = excluded.indexed_at",
                (route.run_id, route.project_id, now),
            )
            connection.execute(
                "INSERT INTO application_frozen_profile_run_references "
                "(run_id, profile_id, status, updated_at) VALUES (?, ?, 'pending', ?) "
                "ON CONFLICT(run_id) DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at",
                (route.run_id, route.profile_id, now),
            )

    def confirm_run_route(self, run_id: str, *, status: str) -> None:
        """Confirm project-local status once the project transaction commits."""

        with self._write() as connection:
            updated = connection.execute(
                "UPDATE application_frozen_profile_run_references SET status = ?, updated_at = ? "
                "WHERE run_id = ?",
                (status, utc_now().isoformat(), run_id),
            )
            if updated.rowcount != 1:
                raise ProjectStorageCorruptionError("run route has no frozen-profile reservation")

    def discard_pending_run_route(self, run_id: str) -> None:
        """Discard only a reservation that cannot name a project-created run."""

        with self._write() as connection:
            reference = connection.execute(
                "SELECT status FROM application_frozen_profile_run_references WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if reference is None or reference["status"] != "pending":
                return
            connection.execute(
                "DELETE FROM application_frozen_profile_run_references WHERE run_id = ?",
                (run_id,),
            )
            connection.execute("DELETE FROM application_run_routes WHERE run_id = ?", (run_id,))

    def index_run(self, route: ApplicationRunRoute) -> None:
        """Backfill an already-created idempotent run into the application index."""

        self.reserve_run_route(route)
        self.confirm_run_route(route.run_id, status=route.status)

    def project_for_run(self, run_id: str) -> str | None:
        with self._read() as connection:
            row = connection.execute(
                "SELECT project_id FROM application_run_routes WHERE run_id = ?", (run_id,)
            ).fetchone()
        return str(row["project_id"]) if row is not None else None

    def replace_run_index(self, routes: list[ApplicationRunRoute]) -> None:
        """Atomically rebuild routes and frozen-profile evidence from projects."""

        if len({item.run_id for item in routes}) != len(routes):
            raise ProjectStorageCorruptionError("multiple project runs share one run ID")

        with self._write() as connection:
            connection.execute("DELETE FROM application_run_routes")
            connection.execute("DELETE FROM application_frozen_profile_run_references")
            now = utc_now().isoformat()
            connection.executemany(
                "INSERT INTO application_run_routes (run_id, project_id, indexed_at) VALUES (?, ?, ?)",
                [(item.run_id, item.project_id, now) for item in routes],
            )
            connection.executemany(
                "INSERT INTO application_frozen_profile_run_references "
                "(run_id, profile_id, status, updated_at) VALUES (?, ?, ?, ?)",
                [(item.run_id, item.profile_id, item.status, now) for item in routes],
            )

    def delete_text_profile_record(self, profile_id: str, expected_revision: int) -> None:
        """Delete only an inactive profile with no nonterminal frozen run."""

        terminal_statuses = tuple(status.value for status in TERMINAL_RUN_STATUSES)
        with self._write() as connection:
            row = connection.execute(
                "SELECT revision FROM application_profiles WHERE profile_id = ?", (profile_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            if int(row["revision"]) != expected_revision:
                raise RevisionConflictError(
                    "text-provider-profile", expected_revision, int(row["revision"])
                )
            active = connection.execute(
                "SELECT profile_id FROM application_text_profile_selection WHERE id = 1"
            ).fetchone()
            if active is not None and active["profile_id"] == profile_id:
                raise InvalidTransitionError("cannot delete the active text provider profile")
            protected = connection.execute(
                "SELECT run_id FROM application_frozen_profile_run_references "
                "WHERE profile_id = ? AND status NOT IN (?, ?, ?, ?) LIMIT 1",
                (profile_id, *terminal_statuses),
            ).fetchone()
            if protected is not None:
                raise InvalidTransitionError(
                    "cannot delete a text provider profile frozen by a nonterminal run"
                )
            connection.execute(
                "DELETE FROM application_text_profile_metadata WHERE profile_id = ?", (profile_id,)
            )
            connection.execute("DELETE FROM application_profiles WHERE profile_id = ?", (profile_id,))

    def record_accounting(self, entry: GlobalAccountingEntry) -> GlobalAccountingEntry:
        with self._write() as connection:
            try:
                connection.execute(
                    "INSERT INTO global_accounting (dispatch_identity, resource, reserved_units, status, created_at) VALUES (?, ?, ?, ?, ?)",
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
                "SELECT dispatch_identity, resource, reserved_units, status, created_at FROM global_accounting ORDER BY created_at, dispatch_identity"
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

    def initialize_video_accounting(self, *, limit_units: int) -> None:
        """Explicit fixture/bootstrap operation; runtime never invents a cap."""

        self._video_dispatch.initialize(limit_units=limit_units)

    def reserve_video_dispatch(
        self,
        *,
        dispatch_identity: str,
        resource: str,
        reserved_units: int,
        requires_accounting: bool,
    ) -> VideoDispatchLease:
        return self._video_dispatch.reserve(
            dispatch_identity=dispatch_identity,
            resource=resource,
            reserved_units=reserved_units,
            requires_accounting=requires_accounting,
        )

    def record_video_dispatch_claim(self, dispatch_identity: str) -> VideoDispatchLease:
        return self._video_dispatch.record_claim(dispatch_identity)

    def release_video_before_dispatch(self, dispatch_identity: str) -> VideoDispatchLease | None:
        return self._video_dispatch.release_before_dispatch(dispatch_identity)

    def video_accounting_budget(self) -> dict[str, Any]:
        return self._video_dispatch.budget()
