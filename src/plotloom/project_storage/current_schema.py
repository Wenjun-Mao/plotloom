"""Exact current project-folder schema and identity admission."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine

from ..persistence.schema import Base, PROJECT_TEXT_PIPELINE_TABLE_NAMES
from .format import ProjectStorageCorruptionError


def schema_objects(connection: object) -> tuple[tuple[str, str, str, str | None], ...]:
    query = getattr(connection, "exec_driver_sql", None)
    statement = (
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    )
    rows = query(statement) if query is not None else connection.execute(statement)  # type: ignore[union-attr]
    return tuple(
        (str(kind), str(name), str(table), sql if isinstance(sql, str) else None)
        for kind, name, table, sql in rows
    )


@lru_cache(maxsize=1)
def expected_project_schema_objects() -> tuple[tuple[str, str, str, str | None], ...]:
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(
            engine,
            tables=[
                Base.metadata.tables[name] for name in PROJECT_TEXT_PIPELINE_TABLE_NAMES
            ],
        )
        with engine.connect() as connection:
            return schema_objects(connection)
    finally:
        engine.dispose()


def assert_current_schema(connection: sqlite3.Connection) -> None:
    """Reject all unsupported layouts before reading application tables."""
    if schema_objects(connection) != expected_project_schema_objects():
        raise ProjectStorageCorruptionError(
            "project database schema is unsupported; current schema required"
        )


def assert_current_project_database(database_path: Path, project_id: str) -> None:
    """Read the live database, including committed WAL rows, without migrating it.

    SQLite may maintain WAL/SHM sidecars for this read-only connection. Immutable
    mode is inappropriate here because it can omit committed WAL authority.
    """
    try:
        connection = sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True)
        try:
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA query_only=ON")
            assert_current_schema(connection)
            projects = list(connection.execute("SELECT id FROM v2_projects"))
            states = list(
                connection.execute(
                    "SELECT project_id, state FROM v2_project_operational_states"
                )
            )
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise ProjectStorageCorruptionError(
            "project database cannot establish its project schema"
        ) from error
    if (
        projects != [(project_id,)]
        or len(states) != 1
        or states[0][0] != project_id
        or states[0][1] not in {"open", "closed"}
    ):
        raise ProjectStorageCorruptionError(
            "project database cannot establish its project identity"
        )
