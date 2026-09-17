"""One bounded project-folder transition to video selection authority."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sqlite3
from typing import Literal

from sqlalchemy import create_engine

from ..persistence.schema import (
    Base,
    PROJECT_TEXT_PIPELINE_TABLE_NAMES,
    VideoCandidateSelectionRow,
)
from .format import ProjectStorageCorruptionError


class ProjectSelectionTransitionRequiredError(ProjectStorageCorruptionError):
    """A known pre-selection folder needs an admitted writable open once."""


SchemaStatus = Literal["current", "transition_required"]
_SELECTION_TABLE = VideoCandidateSelectionRow.__tablename__


def _schema_objects(connection: object) -> list[tuple[str, str, str, str | None]]:
    query = getattr(connection, "exec_driver_sql", None)
    rows = (
        query(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        )
        if query is not None
        else connection.execute(  # type: ignore[union-attr]
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        )
    )
    return [
        (str(kind), str(name), str(table_name), sql if isinstance(sql, str) else None)
        for kind, name, table_name, sql in rows
    ]


@lru_cache(maxsize=2)
def expected_project_schema_objects(
    *, include_video_candidate_selection: bool,
) -> tuple[tuple[str, str, str, str | None], ...]:
    """Return the exact current or immediately preceding project schema."""

    table_names = set(PROJECT_TEXT_PIPELINE_TABLE_NAMES)
    if not include_video_candidate_selection:
        table_names.remove(_SELECTION_TABLE)
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(
            engine, tables=[Base.metadata.tables[name] for name in table_names]
        )
        with engine.connect() as connection:
            return tuple(_schema_objects(connection))
    finally:
        engine.dispose()


def selection_schema_status(database_path: Path, project_id: str) -> SchemaStatus:
    """Classify only the exact supported current and pre-selection schemas."""

    try:
        connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
        try:
            actual = tuple(_schema_objects(connection))
            projects = list(connection.execute("SELECT id FROM v2_projects"))
            states = list(
                connection.execute(
                    "SELECT state FROM v2_project_operational_states WHERE project_id = ?",
                    (project_id,),
                )
            )
            user_version = connection.execute("PRAGMA user_version").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise ProjectStorageCorruptionError(
            "project database cannot establish its video selection schema"
        ) from error
    if projects != [(project_id,)] or len(states) != 1 or states[0][0] not in {"open", "closed"}:
        raise ProjectStorageCorruptionError(
            "project database cannot establish its video selection identity"
        )
    if actual == expected_project_schema_objects(include_video_candidate_selection=True):
        return "current"
    if (
        actual
        == expected_project_schema_objects(include_video_candidate_selection=False)
        and user_version == (0,)
    ):
        return "transition_required"
    raise ProjectStorageCorruptionError(
        "project database schema is unsupported for video candidate selection"
    )


def transition_video_candidate_selection(
    database_path: Path,
    project_id: str,
    *,
    allow_closed: bool = False,
) -> bool:
    """Install selection authority once from the exact prior folder schema.

    The source check happens again under ``BEGIN IMMEDIATE``.  This keeps a
    stale caller from creating a table in an arbitrary or concurrently changed
    project database.
    """

    if selection_schema_status(database_path, project_id) == "current":
        return False
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                if selection_schema_status(database_path, project_id) != "transition_required":
                    raise ProjectStorageCorruptionError(
                        "project database changed before video selection transition"
                    )
                state = connection.exec_driver_sql(
                    "SELECT state FROM v2_project_operational_states WHERE project_id = ?",
                    (project_id,),
                ).scalar_one()
                if state != "open" and not allow_closed:
                    raise ProjectSelectionTransitionRequiredError(
                        "video selection transition requires an explicitly reopened project"
                    )
                VideoCandidateSelectionRow.__table__.create(connection)
                connection.exec_driver_sql(
                    """
                    INSERT INTO v2_video_candidate_selections
                      (project_id, shot_id, selected_video_job_id, revision, updated_at)
                    SELECT job.project_id, json_extract(job.snapshot, '$.shot.id'), review.video_job_id, 1, review.created_at
                    FROM v2_video_reviews AS review
                    JOIN v2_video_jobs AS job ON job.id = review.video_job_id
                    WHERE review.decision = 'select'
                      AND review.id = (
                        SELECT newer.id
                        FROM v2_video_reviews AS newer
                        JOIN v2_video_jobs AS newer_job ON newer_job.id = newer.video_job_id
                        WHERE newer_job.project_id = job.project_id
                          AND json_extract(newer_job.snapshot, '$.shot.id') = json_extract(job.snapshot, '$.shot.id')
                        ORDER BY newer.created_at DESC, newer.id DESC LIMIT 1
                      )
                    """
                )
                if tuple(_schema_objects(connection)) != expected_project_schema_objects(
                    include_video_candidate_selection=True
                ):
                    raise ProjectStorageCorruptionError(
                        "video selection transition did not produce the current project schema"
                    )
                if list(connection.exec_driver_sql("PRAGMA foreign_key_check")):
                    raise ProjectStorageCorruptionError(
                        "video selection transition found invalid project references"
                    )
            except BaseException:
                connection.rollback()
                raise
            connection.commit()
            return True
    finally:
        engine.dispose()
