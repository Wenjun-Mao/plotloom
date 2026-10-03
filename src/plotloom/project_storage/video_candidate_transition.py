"""Bounded additive transitions for the immediately preceding folder schemas."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Literal

from sqlalchemy import create_engine

from ..persistence.schema import (
    PROJECT_TEXT_PIPELINE_TABLE_NAMES,
    ArtReferenceDecisionRow,
    ArtReferenceDecisionStateRow,
    ArtReferenceProposalCandidateRow,
    ArtReferenceProposalDeliveryRow,
    ArtReferenceProposalRow,
    Base,
    CharacterImportedAppearanceRow,
    CharacterReferenceDecisionRow,
    CharacterReferenceProposalDeliveryRow,
    CreativeHandoffExecutionPinRow,
    ProductionBridgeAdmissionRow,
    ProductionBridgeHeadRow,
    ProductionBridgeIntentJobRow,
    ProductionBridgeRevisionRow,
    ShotPresentationRow,
    VideoCandidateSelectionRow,
    VideoEndFrameDecisionRow,
    VideoSegmentRow,
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


class ProjectProductionBridgeTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A retained project needs empty F5 production-bridge tables."""


class ProjectBridgeIntentJobTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A current bridge project needs its durable inference-job table."""


class ProjectVideoSegmentTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A current video project needs its reviewed-playback-segment table."""


class ProjectVideoEndFrameTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A current video project needs its additive end-frame decision table."""


class ProjectCreativeExecutionPinTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A retained project needs its trusted creative execution-pin table."""


class ProjectShotPresentationTransitionRequiredError(ProjectSchemaTransitionRequiredError):
    """A current project needs the additive shot presentation decision table."""


SchemaStatus = Literal[
    "current", "selection_transition_required", "art_reference_transition_required",
    "character_delivery_publication_phase_transition_required",
    "character_selection_metadata_transition_required",
    "character_imported_appearance_transition_required",
    "art_reference_decision_transition_required",
    "production_bridge_transition_required",
    "bridge_intent_job_transition_required", "video_segment_transition_required",
    "video_end_frame_transition_required",
    "creative_execution_pin_transition_required",
    "shot_presentation_transition_required",
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
_PRODUCTION_BRIDGE_TABLES = (
    ProductionBridgeHeadRow.__table__, ProductionBridgeRevisionRow.__table__,
    ProductionBridgeAdmissionRow.__table__, ProductionBridgeIntentJobRow.__table__,
)
_CREATIVE_EXECUTION_PIN_TABLE = CreativeHandoffExecutionPinRow.__tablename__


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
    include_production_bridge: bool = True,
    include_bridge_intent_jobs: bool = True,
    include_video_segments: bool = True,
    include_video_end_frames: bool = True,
    include_creative_execution_pins: bool = True,
    include_shot_presentations: bool = True,
) -> tuple[tuple[str, str, str, str | None], ...]:
    """Return the exact current schema or one permitted immediate predecessor."""

    table_names = set(PROJECT_TEXT_PIPELINE_TABLE_NAMES)
    if not include_shot_presentations:
        table_names.remove(ShotPresentationRow.__tablename__)
    if not include_video_candidate_selection:
        table_names.remove(_SELECTION_TABLE)
    if not include_art_reference_proposals:
        table_names.difference_update(table.name for table in _ART_REFERENCE_TABLES)
    if not include_character_imported_appearances:
        table_names.remove(_CHARACTER_IMPORTED_APPEARANCE_TABLE)
    if not include_art_reference_decisions:
        table_names.difference_update(table.name for table in _ART_REFERENCE_DECISION_TABLES)
    if not include_production_bridge:
        table_names.difference_update(table.name for table in _PRODUCTION_BRIDGE_TABLES)
    if not include_bridge_intent_jobs:
        table_names.remove(ProductionBridgeIntentJobRow.__tablename__)
    if not include_video_segments:
        table_names.remove(VideoSegmentRow.__tablename__)
    if not include_video_end_frames:
        table_names.remove(VideoEndFrameDecisionRow.__tablename__)
    if not include_creative_execution_pins:
        table_names.remove(_CREATIVE_EXECUTION_PIN_TABLE)
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


def _requires_production_bridge_transition(actual: tuple[tuple[str, str, str, str | None], ...]) -> bool:
    """Recognize every already-supported physical layout without bridge tables."""
    base = expected_project_schema_objects(
        include_video_candidate_selection=True, include_production_bridge=False,
    )
    appended = expected_project_schema_objects(
        include_video_candidate_selection=True, include_production_bridge=False,
        append_character_delivery_publication_phase=True,
    )
    return actual in {base, appended, _metadata_rebuilt_schema(base), _metadata_rebuilt_schema(appended)}


def _requires_bridge_intent_job_transition(actual: tuple[tuple[str, str, str, str | None], ...]) -> bool:
    base = expected_project_schema_objects(
        include_video_candidate_selection=True, include_bridge_intent_jobs=False,
    )
    appended = expected_project_schema_objects(
        include_video_candidate_selection=True, include_bridge_intent_jobs=False,
        append_character_delivery_publication_phase=True,
    )
    return actual in {base, appended, _metadata_rebuilt_schema(base), _metadata_rebuilt_schema(appended)}


def _requires_video_segment_transition(actual: tuple[tuple[str, str, str, str | None], ...]) -> bool:
    base = expected_project_schema_objects(
        include_video_candidate_selection=True, include_video_segments=False,
    )
    appended = expected_project_schema_objects(
        include_video_candidate_selection=True, include_video_segments=False,
        append_character_delivery_publication_phase=True,
    )
    return actual in {base, appended, _metadata_rebuilt_schema(base), _metadata_rebuilt_schema(appended)}


def _requires_video_end_frame_transition(actual: tuple[tuple[str, str, str, str | None], ...]) -> bool:
    # This additive table may be absent from any already-admitted predecessor,
    # including the immediately previous pre-segment layout. Reconstitute
    # only this table's known SQLite objects, then reuse the strict existing
    # classifiers instead of admitting a broad partial-schema shape.
    table = VideoEndFrameDecisionRow.__tablename__
    if any(name == table and kind == "table" for kind, name, _owner, _sql in actual):
        return False
    end_objects = tuple(item for item in expected_project_schema_objects(
        include_video_candidate_selection=True,
    ) if item[2] == table)
    augmented = tuple(sorted((*actual, *end_objects), key=lambda item: (item[0], item[1])))
    return _recognized_current_or_predecessor(augmented)


def _requires_creative_execution_pin_transition(actual: tuple[tuple[str, str, str, str | None], ...]) -> bool:
    base = expected_project_schema_objects(
        include_video_candidate_selection=True, include_creative_execution_pins=False,
    )
    return actual in {base, _metadata_rebuilt_schema(base)}


def _recognized_current_or_predecessor(actual: tuple[tuple[str, str, str, str | None], ...]) -> bool:
    return bool(
        _is_current_schema_objects(actual)
        or _requires_video_segment_transition(actual)
        or _requires_creative_execution_pin_transition(actual)
        or _requires_bridge_intent_job_transition(actual)
        or _requires_art_reference_decision_transition(actual)
        or _requires_production_bridge_transition(actual)
        or _requires_character_imported_appearance_transition(actual)
        or _requires_character_selection_metadata_transition(actual)
        or actual == expected_project_schema_objects(
            include_video_candidate_selection=True,
            include_character_delivery_publication_phase=False,
        )
        or actual == expected_project_schema_objects(include_video_candidate_selection=False)
        or actual == expected_project_schema_objects(
            include_video_candidate_selection=True, include_art_reference_proposals=False,
        )
    )


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
    prior = expected_project_schema_objects(include_video_candidate_selection=True, include_shot_presentations=False)
    appended = expected_project_schema_objects(include_video_candidate_selection=True,
        include_shot_presentations=False, append_character_delivery_publication_phase=True)
    if actual in {prior, appended, _metadata_rebuilt_schema(prior), _metadata_rebuilt_schema(appended)} and user_version == (0,):
        return "shot_presentation_transition_required"
    if _requires_creative_execution_pin_transition(actual) and user_version == (0,):
        return "creative_execution_pin_transition_required"
    if _requires_video_end_frame_transition(actual) and user_version == (0,):
        return "video_end_frame_transition_required"
    if _requires_video_segment_transition(actual) and user_version == (0,):
        return "video_segment_transition_required"
    if _requires_bridge_intent_job_transition(actual) and user_version == (0,):
        return "bridge_intent_job_transition_required"
    if _requires_art_reference_decision_transition(actual) and user_version == (0,):
        return "art_reference_decision_transition_required"
    if _requires_production_bridge_transition(actual) and user_version == (0,):
        return "production_bridge_transition_required"
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


from .project_schema_transition import (  # noqa: F401
    transition_project_schema,
    transition_required_error,
)
