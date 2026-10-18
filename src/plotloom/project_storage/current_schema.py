"""Exact current project-folder schema and identity admission."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import create_engine

from ..persistence.schema import PROJECT_TEXT_PIPELINE_TABLE_NAMES, Base
from ..script_contracts import ScriptBinding
from ..storyboard_review_contracts import StoryboardReviewBinding
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


def assert_current_review_bindings(connection: sqlite3.Connection, *, asset_home: Path | None = None, continuation: bool = True) -> None:
    """Reject unsupported JSON contracts before a folder can be mutated.

    SQL layout alone cannot establish the version of a persisted review binding.
    Validate retained revisions as well as candidates: history/report reads also
    consume these contracts. Never infer new authority from obsolete fields.
    Only an exact frozen prior-layout owner may disable continuation validation;
    current runtime paths never infer feature support from table absence.
    """
    from .autopilot_validation import assert_autopilot_contracts
    from .cross_shot_validation import assert_cross_shot_contracts
    assert_cross_shot_contracts(connection, asset_home=asset_home, continuation=continuation)
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='v2_autopilot_runs'").fetchone():
        assert_autopilot_contracts(connection, asset_home=asset_home, continuation=continuation)
    from .video_batch_validation import assert_video_batch_contracts
    assert_video_batch_contracts(connection)
    assert_review_binding_shapes(connection)


def assert_review_binding_shapes(connection: sqlite3.Connection) -> None:
    """Current JSON schema only; this does not validate review authority."""
    for table, model in (
        ("v2_script_candidates", ScriptBinding),
        ("v2_script_revisions", ScriptBinding),
        ("v2_storyboard_review_candidates", StoryboardReviewBinding),
        ("v2_storyboard_review_revisions", StoryboardReviewBinding),
    ):
        for (binding,) in connection.execute(f'SELECT binding FROM "{table}"'):
            try:
                model.model_validate_json(binding)
            except (ValidationError, TypeError) as error:
                raise ProjectStorageCorruptionError(
                    f"project database review contract is unsupported in {table}; "
                    "an explicit development-data reset is required; no data was rewritten"
                ) from error


def assert_current_project_database(database_path: Path, project_id: str, *, admission: str = "authority") -> None:
    """Read the live database, including committed WAL rows, without migrating it.

    SQLite may maintain WAL/SHM sidecars for this read-only connection. Immutable
    mode is inappropriate here because it can omit committed WAL authority.
    """
    if admission not in {"inspection", "authority"}:
        raise ValueError("unknown project admission contract")
    try:
        connection = sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True)
        try:
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA query_only=ON")
            connection.execute("BEGIN")
            assert_current_schema(connection)
            if admission == "authority":
                from .proof_scope import proof_scope
                with proof_scope():
                    assert_current_review_bindings(connection)
            else:
                assert_review_binding_shapes(connection)
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
