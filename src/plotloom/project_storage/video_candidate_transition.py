"""Bounded additive transitions for the immediately preceding folder schemas."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sqlite3
from typing import Literal

from sqlalchemy import create_engine

from ..persistence.schema import (
    ArtReferenceDecisionRow,
    ArtReferenceDecisionStateRow,
    ArtReferenceProposalCandidateRow,
    ArtReferenceProposalDeliveryRow,
    ArtReferenceProposalRow,
    Base,
    CharacterImportedAppearanceRow,
    CharacterReferenceDecisionRow,
    CharacterReferenceProposalDeliveryRow,
    PROJECT_TEXT_PIPELINE_TABLE_NAMES,
    VideoCandidateSelectionRow,
)
from .format import ProjectStorageCorruptionError


class ProjectSchemaTransitionRequiredError(ProjectStorageCorruptionError):
    """A known immediately preceding folder needs an admitted writable open."""


class ProjectSelectionTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A known pre-selection folder needs an admitted writable open once."""


class ProjectArtReferenceTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A current F3A folder needs the empty F3B proposal tables once."""


class ProjectCharacterDeliveryPublicationPhaseTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A prior Characters folder needs final-publication provenance once."""


class ProjectCharacterSelectionMetadataTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A prior Characters folder requires optional creator-selection metadata."""


class ProjectCharacterImportedAppearanceTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A current Characters folder needs the additive imported-appearance table."""


class ProjectArtReferenceDecisionTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A current F3B folder needs explicit subject-reference decision tables."""


SchemaStatus = Literal[
    "current", "selection_transition_required", "art_reference_transition_required",
    "character_delivery_publication_phase_transition_required",
    "character_selection_metadata_transition_required",
    "character_imported_appearance_transition_required",
    "art_reference_decision_transition_required",
]
_SELECTION_TABLE = VideoCandidateSelectionRow.__tablename__
_CHARACTER_REFERENCE_DELIVERY_TABLE = CharacterReferenceProposalDeliveryRow.__tablename__
_CHARACTER_REFERENCE_DECISION_TABLE = CharacterReferenceDecisionRow.__tablename__
_CHARACTER_IMPORTED_APPEARANCE_TABLE = CharacterImportedAppearanceRow.__tablename__
_ART_REFERENCE_TABLES = (
    ArtReferenceProposalRow.__table__,
    ArtReferenceProposalDeliveryRow.__table__,
    ArtReferenceProposalCandidateRow.__table__,
)
_ART_REFERENCE_DECISION_TABLES = (
    ArtReferenceDecisionStateRow.__table__,
    ArtReferenceDecisionRow.__table__,
)


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


@lru_cache(maxsize=4)
def expected_project_schema_objects(
    *, include_video_candidate_selection: bool,
    include_art_reference_proposals: bool = True,
    include_character_delivery_publication_phase: bool = True,
    append_character_delivery_publication_phase: bool = False,
    include_character_imported_appearances: bool = True,
    include_art_reference_decisions: bool = True,
) -> tuple[tuple[str, str, str, str | None], ...]:
    """Return the exact current schema or one permitted immediate predecessor."""

    table_names = set(PROJECT_TEXT_PIPELINE_TABLE_NAMES)
    if not include_video_candidate_selection:
        table_names.remove(_SELECTION_TABLE)
    if not include_art_reference_proposals:
        table_names.difference_update(table.name for table in _ART_REFERENCE_TABLES)
    if not include_character_imported_appearances:
        table_names.remove(_CHARACTER_IMPORTED_APPEARANCE_TABLE)
    if not include_art_reference_decisions:
        table_names.difference_update(table.name for table in _ART_REFERENCE_DECISION_TABLES)
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(
            engine, tables=[Base.metadata.tables[name] for name in table_names]
        )
        with engine.connect() as connection:
            if not include_character_delivery_publication_phase:
                connection.exec_driver_sql(
                    f"ALTER TABLE {_CHARACTER_REFERENCE_DELIVERY_TABLE} "
                    "DROP COLUMN publication_phase"
                )
            elif append_character_delivery_publication_phase:
                # SQLite additive transitions append a column. Accept that
                # physical ordering as the same current contract as a fresh
                # table, without rebuilding retained delivery/candidate rows.
                connection.exec_driver_sql(
                    f"ALTER TABLE {_CHARACTER_REFERENCE_DELIVERY_TABLE} "
                    "DROP COLUMN publication_phase"
                )
                connection.exec_driver_sql(
                    f"ALTER TABLE {_CHARACTER_REFERENCE_DELIVERY_TABLE} "
                    "ADD COLUMN publication_phase VARCHAR(24)"
                )
            return tuple(_schema_objects(connection))
    finally:
        engine.dispose()


def _is_current_schema_objects(actual: tuple[tuple[str, str, str, str | None], ...]) -> bool:
    return actual in {
        expected_project_schema_objects(include_video_candidate_selection=True),
        expected_project_schema_objects(
            include_video_candidate_selection=True,
            append_character_delivery_publication_phase=True,
        ),
        _metadata_rebuilt_schema(
            expected_project_schema_objects(include_video_candidate_selection=True)
        ),
        _metadata_rebuilt_schema(
            expected_project_schema_objects(
                include_video_candidate_selection=True,
                append_character_delivery_publication_phase=True,
            )
        ),
    }


def _metadata_rebuilt_schema(
    schema: tuple[tuple[str, str, str, str | None], ...],
) -> tuple[tuple[str, str, str, str | None], ...]:
    """Match SQLite's deterministic quoting after the required table rename."""

    result: list[tuple[str, str, str, str | None]] = []
    for kind, name, table_name, statement in schema:
        if name == _CHARACTER_REFERENCE_DECISION_TABLE and statement is not None:
            statement = statement.replace(
                f"CREATE TABLE {_CHARACTER_REFERENCE_DECISION_TABLE}",
                f'CREATE TABLE "{_CHARACTER_REFERENCE_DECISION_TABLE}"',
                1,
            )
        result.append((kind, name, table_name, statement))
    return tuple(result)


def _required_character_selection_metadata_schema(
    schema: tuple[tuple[str, str, str, str | None], ...],
) -> tuple[tuple[str, str, str, str | None], ...]:
    """Describe the direct predecessor with required reviewer and notes fields."""

    result: list[tuple[str, str, str, str | None]] = []
    for kind, name, table_name, statement in schema:
        if name == _CHARACTER_REFERENCE_DECISION_TABLE and statement is not None:
            statement = statement.replace(
                "reviewer VARCHAR(160), \n\tnotes TEXT,",
                "reviewer VARCHAR(160) NOT NULL, \n\tnotes TEXT NOT NULL,",
            )
        result.append((kind, name, table_name, statement))
    return tuple(result)


def _requires_character_selection_metadata_transition(
    actual: tuple[tuple[str, str, str, str | None], ...],
) -> bool:
    return actual in {
        _required_character_selection_metadata_schema(
            expected_project_schema_objects(include_video_candidate_selection=True)
        ),
        _required_character_selection_metadata_schema(
            expected_project_schema_objects(
                include_video_candidate_selection=True,
                append_character_delivery_publication_phase=True,
            )
        ),
    }


def _requires_character_imported_appearance_transition(
    actual: tuple[tuple[str, str, str, str | None], ...],
) -> bool:
    """Recognize exactly the last admitted schema before the additive table."""

    return actual in {
        expected_project_schema_objects(
            include_video_candidate_selection=True,
            include_character_imported_appearances=False,
        ),
        expected_project_schema_objects(
            include_video_candidate_selection=True,
            append_character_delivery_publication_phase=True,
            include_character_imported_appearances=False,
        ),
        _metadata_rebuilt_schema(expected_project_schema_objects(
            include_video_candidate_selection=True,
            include_character_imported_appearances=False,
        )),
        _metadata_rebuilt_schema(expected_project_schema_objects(
            include_video_candidate_selection=True,
            append_character_delivery_publication_phase=True,
            include_character_imported_appearances=False,
        )),
    }


def _requires_art_reference_decision_transition(
    actual: tuple[tuple[str, str, str, str | None], ...],
) -> bool:
    """Recognize exactly the last admitted schema before F3B selection state."""

    return actual in {
        expected_project_schema_objects(
            include_video_candidate_selection=True,
            include_art_reference_decisions=False,
        ),
        expected_project_schema_objects(
            include_video_candidate_selection=True,
            append_character_delivery_publication_phase=True,
            include_art_reference_decisions=False,
        ),
        _metadata_rebuilt_schema(expected_project_schema_objects(
            include_video_candidate_selection=True,
            include_art_reference_decisions=False,
        )),
        _metadata_rebuilt_schema(expected_project_schema_objects(
            include_video_candidate_selection=True,
            append_character_delivery_publication_phase=True,
            include_art_reference_decisions=False,
        )),
    }


def project_schema_status(database_path: Path, project_id: str) -> SchemaStatus:
    """Classify only exact current and immediately preceding folder schemas."""

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
            "project database cannot establish its project schema"
        ) from error
    if projects != [(project_id,)] or len(states) != 1 or states[0][0] not in {"open", "closed"}:
        raise ProjectStorageCorruptionError(
            "project database cannot establish its project identity"
        )
    if _is_current_schema_objects(actual):
        return "current"
    if _requires_art_reference_decision_transition(actual) and user_version == (0,):
        return "art_reference_decision_transition_required"
    if _requires_character_imported_appearance_transition(actual) and user_version == (0,):
        return "character_imported_appearance_transition_required"
    if _requires_character_selection_metadata_transition(actual) and user_version == (0,):
        return "character_selection_metadata_transition_required"
    if (
        actual
        == expected_project_schema_objects(
            include_video_candidate_selection=True,
            include_character_delivery_publication_phase=False,
        )
        and user_version == (0,)
    ):
        return "character_delivery_publication_phase_transition_required"
    if (
        actual
        == expected_project_schema_objects(include_video_candidate_selection=False)
        and user_version == (0,)
    ):
        return "selection_transition_required"
    if (
        actual
        == expected_project_schema_objects(
            include_video_candidate_selection=True,
            include_art_reference_proposals=False,
        )
        and user_version == (0,)
    ):
        return "art_reference_transition_required"
    raise ProjectStorageCorruptionError(
        "project database schema is unsupported for the current project contract"
    )


def transition_required_error(
    status: SchemaStatus, *, reason: str = "an explicitly reopened project"
) -> ProjectSchemaTransitionRequiredError:
    if status == "selection_transition_required":
        return ProjectSelectionTransitionRequiredError(
            f"video selection transition requires {reason}"
        )
    if status == "art_reference_transition_required":
        return ProjectArtReferenceTransitionRequiredError(
            f"art reference transition requires {reason}"
        )
    if status == "character_delivery_publication_phase_transition_required":
        return ProjectCharacterDeliveryPublicationPhaseTransitionRequiredError(
            f"character delivery publication-phase transition requires {reason}"
        )
    if status == "character_selection_metadata_transition_required":
        return ProjectCharacterSelectionMetadataTransitionRequiredError(
            f"character selection metadata transition requires {reason}"
        )
    if status == "character_imported_appearance_transition_required":
        return ProjectCharacterImportedAppearanceTransitionRequiredError(
            f"character imported-appearance transition requires {reason}"
        )
    if status == "art_reference_decision_transition_required":
        return ProjectArtReferenceDecisionTransitionRequiredError(
            f"art reference decision transition requires {reason}"
        )
    raise AssertionError(f"current project schema does not need a transition: {status}")


def transition_project_schema(
    database_path: Path,
    project_id: str,
    *,
    allow_closed: bool = False,
) -> bool:
    """Install the one matching additive schema change from an exact prior schema.

    The source check happens again under ``BEGIN IMMEDIATE``.  This keeps a
    stale caller from creating a table in an arbitrary or concurrently changed
    project database.
    """

    status = project_schema_status(database_path, project_id)
    if status == "current":
        return False
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                current_status = project_schema_status(database_path, project_id)
                if current_status == "current":
                    return False
                if current_status != status:
                    raise ProjectStorageCorruptionError(
                        "project database changed before project schema transition"
                    )
                state = connection.exec_driver_sql(
                    "SELECT state FROM v2_project_operational_states WHERE project_id = ?",
                    (project_id,),
                ).scalar_one()
                if state != "open" and not allow_closed:
                    raise transition_required_error(status)
                if status == "selection_transition_required":
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
                elif status == "art_reference_transition_required":
                    for table in _ART_REFERENCE_TABLES:
                        table.create(connection)
                elif status == "character_delivery_publication_phase_transition_required":
                    connection.exec_driver_sql(
                        f"ALTER TABLE {_CHARACTER_REFERENCE_DELIVERY_TABLE} "
                        "ADD COLUMN publication_phase VARCHAR(24)"
                    )
                elif status == "character_selection_metadata_transition_required":
                    current_schema = expected_project_schema_objects(
                        include_video_candidate_selection=True
                    )
                    create_statement = next(
                        statement for _kind, name, _table, statement in current_schema
                        if name == _CHARACTER_REFERENCE_DECISION_TABLE and statement is not None
                    )
                    temporary_table = f"{_CHARACTER_REFERENCE_DECISION_TABLE}_metadata_transition"
                    connection.exec_driver_sql(
                        create_statement.replace(
                            f"CREATE TABLE {_CHARACTER_REFERENCE_DECISION_TABLE}",
                            f"CREATE TABLE {temporary_table}",
                            1,
                        )
                    )
                    columns = (
                        "id, project_id, character_id, reference_revision, character_context, "
                        "character_context_hash, primary_asset_id, complementary_asset_ids, asset_hashes, "
                        "reviewer, notes, revoked_at, revoked_by, revocation_reason, created_at"
                    )
                    connection.exec_driver_sql(
                        f"INSERT INTO {temporary_table} ({columns}) "
                        f"SELECT {columns} FROM {_CHARACTER_REFERENCE_DECISION_TABLE}"
                    )
                    connection.exec_driver_sql(
                        "DROP INDEX ix_v2_character_reference_decisions_project_character"
                    )
                    connection.exec_driver_sql(f"DROP TABLE {_CHARACTER_REFERENCE_DECISION_TABLE}")
                    connection.exec_driver_sql(
                        f"ALTER TABLE {temporary_table} RENAME TO {_CHARACTER_REFERENCE_DECISION_TABLE}"
                    )
                    connection.exec_driver_sql(
                        "CREATE INDEX ix_v2_character_reference_decisions_project_character "
                        "ON v2_character_reference_decisions (project_id, character_id, reference_revision)"
                    )
                elif status == "character_imported_appearance_transition_required":
                    CharacterImportedAppearanceRow.__table__.create(connection)
                elif status == "art_reference_decision_transition_required":
                    for table in _ART_REFERENCE_DECISION_TABLES:
                        table.create(connection)
                else:  # pragma: no cover - kept exhaustive as SchemaStatus grows.
                    raise AssertionError(f"unsupported project transition: {status}")
                if not _is_current_schema_objects(tuple(_schema_objects(connection))):
                    raise ProjectStorageCorruptionError(
                        "project schema transition did not produce the current project schema"
                    )
                if list(connection.exec_driver_sql("PRAGMA foreign_key_check")):
                    raise ProjectStorageCorruptionError(
                        "project schema transition found invalid project references"
                    )
            except BaseException:
                connection.rollback()
                raise
            connection.commit()
            return True
    finally:
        engine.dispose()
