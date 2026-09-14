"""Read saved text profiles without opening an application-control writer."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Iterable

from ..domain import contains_secret_setting, contains_secret_value
from ..provider_profiles import TextProviderProfileSnapshot, TextProviderProfileSnapshotV3
from .format import ProjectStorageCorruptionError, ProjectStorageError


def load_saved_text_profiles(
    application_data_root: Path,
    profile_ids: Iterable[str],
) -> list[TextProviderProfileSnapshot]:
    """Return enabled, public profiles from one consistent read-only snapshot.

    Qualification tooling needs the current installation's selected profile
    definitions, but it must neither initialize application schema nor mutate a
    live WAL database.  A read-only transaction supplies one SQLite snapshot;
    each returned configuration is re-derived from the authoritative record
    identity and metadata before it is admitted into a disposable project.
    """

    root = application_data_root.expanduser().resolve()
    if not root.is_dir() or root.is_symlink():
        raise ProjectStorageError("application data root must be a real directory")
    database_path = root / "application.sqlite3"
    if not database_path.is_file() or database_path.is_symlink():
        raise ProjectStorageError("application data has no regular application database")

    database_uri = f"{database_path.as_uri()}?mode=ro"
    try:
        connection = sqlite3.connect(database_uri, uri=True, isolation_level=None)
    except sqlite3.Error as error:
        raise ProjectStorageError("application profile snapshot cannot be opened") from error
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        profiles: list[TextProviderProfileSnapshot] = []
        for profile_id in profile_ids:
            row = connection.execute(
                "SELECT profiles.revision, profiles.configuration_json, metadata.enabled, "
                "metadata.adapter_id, metadata.adapter_version "
                "FROM application_profiles AS profiles "
                "JOIN application_text_profile_metadata AS metadata "
                "ON metadata.profile_id = profiles.profile_id "
                "WHERE profiles.profile_id = ?",
                (profile_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"saved text provider profile not found: {profile_id}")
            if not bool(row[2]):
                raise ValueError(
                    f"disabled text provider profile cannot start qualification: {profile_id}"
                )
            try:
                configuration = json.loads(str(row[1]))
            except (TypeError, json.JSONDecodeError) as error:
                raise ProjectStorageCorruptionError(
                    "application profile has invalid public configuration"
                ) from error
            if not isinstance(configuration, dict):
                raise ProjectStorageCorruptionError(
                    "application profile configuration must be an object"
                )
            if contains_secret_setting(configuration) or contains_secret_value(configuration):
                raise ProjectStorageCorruptionError(
                    "application profile snapshot contains secret configuration"
                )
            configuration.update(
                profileSchemaVersion=3,
                profileId=profile_id,
                profileVersion=int(row[0]),
                profileHash="",
                adapterId=str(row[3]),
                adapterVersion=str(row[4]),
            )
            try:
                profiles.append(TextProviderProfileSnapshotV3.model_validate(configuration))
            except ValueError as error:
                raise ProjectStorageCorruptionError(
                    "application profile is not a valid secret-free V3 profile"
                ) from error
        connection.rollback()
        return profiles
    except sqlite3.Error as error:
        raise ProjectStorageError("application profile snapshot cannot be read") from error
    finally:
        connection.close()
