"""Exact admitted project schema transitions, separate from classification."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from ..persistence.schema import (
    CharacterImportedAppearanceRow,
    CreativeHandoffExecutionPinRow,
    ProductionBridgeIntentJobRow,
    ShotPresentationRow,
    VideoCandidateSelectionRow,
    VideoEndFrameDecisionRow,
    VideoSegmentRow,
)
from .format import ProjectStorageCorruptionError

if TYPE_CHECKING:
    from .video_candidate_transition import (
        ProjectSchemaTransitionRequiredError,
        SchemaStatus,
    )

def transition_required_error(
    status: SchemaStatus, *, reason: str = "an explicitly reopened project"
) -> ProjectSchemaTransitionRequiredError:
    from .video_candidate_transition import (
        ProjectArtReferenceDecisionTransitionRequiredError,
        ProjectArtReferenceTransitionRequiredError,
        ProjectBridgeIntentJobTransitionRequiredError,
        ProjectCharacterDeliveryPublicationPhaseTransitionRequiredError,
        ProjectCharacterImportedAppearanceTransitionRequiredError,
        ProjectCharacterSelectionMetadataTransitionRequiredError,
        ProjectCreativeExecutionPinTransitionRequiredError,
        ProjectProductionBridgeTransitionRequiredError,
        ProjectSelectionTransitionRequiredError,
        ProjectShotPresentationTransitionRequiredError,
        ProjectVideoEndFrameTransitionRequiredError,
        ProjectVideoSegmentTransitionRequiredError,
    )
    if status == "shot_presentation_transition_required":
        return ProjectShotPresentationTransitionRequiredError(f"shot presentation transition requires {reason}")
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
    if status == "production_bridge_transition_required":
        return ProjectProductionBridgeTransitionRequiredError(
            f"production bridge transition requires {reason}"
        )
    if status == "bridge_intent_job_transition_required":
        return ProjectBridgeIntentJobTransitionRequiredError(
            f"bridge intent job transition requires {reason}"
        )
    if status == "video_segment_transition_required":
        return ProjectVideoSegmentTransitionRequiredError(
            f"video segment transition requires {reason}"
        )
    if status == "video_end_frame_transition_required":
        return ProjectVideoEndFrameTransitionRequiredError(
            f"video end-frame transition requires {reason}"
        )
    if status == "creative_execution_pin_transition_required":
        return ProjectCreativeExecutionPinTransitionRequiredError(
            f"creative execution-pin transition requires {reason}"
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

    from .video_candidate_transition import (
        _ART_REFERENCE_DECISION_TABLES,
        _ART_REFERENCE_TABLES,
        _CHARACTER_REFERENCE_DECISION_TABLE,
        _CHARACTER_REFERENCE_DELIVERY_TABLE,
        _PRODUCTION_BRIDGE_TABLES,
        _is_current_schema_objects,
        _recognized_current_or_predecessor,
        _schema_objects,
        expected_project_schema_objects,
        project_schema_status,
    )
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
                elif status == "production_bridge_transition_required":
                    for table in _PRODUCTION_BRIDGE_TABLES:
                        table.create(connection)
                    connection.exec_driver_sql(
                        "INSERT INTO v2_production_bridge_heads "
                        "(project_id, revision, status, updated_at) "
                        "SELECT id, 0, 'missing', updated_at FROM v2_projects"
                    )
                elif status == "bridge_intent_job_transition_required":
                    ProductionBridgeIntentJobRow.__table__.create(connection)
                elif status == "video_segment_transition_required":
                    VideoSegmentRow.__table__.create(connection)
                elif status == "video_end_frame_transition_required":
                    VideoEndFrameDecisionRow.__table__.create(connection)
                elif status == "creative_execution_pin_transition_required":
                    CreativeHandoffExecutionPinRow.__table__.create(connection)
                elif status == "shot_presentation_transition_required":
                    ShotPresentationRow.__table__.create(connection)
                else:  # pragma: no cover - kept exhaustive as SchemaStatus grows.
                    raise AssertionError(f"unsupported project transition: {status}")
                after = tuple(_schema_objects(connection))
                if not (_is_current_schema_objects(after) or
                        status == "video_end_frame_transition_required" and _recognized_current_or_predecessor(after)):
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
            if status == "video_end_frame_transition_required" and project_schema_status(database_path, project_id) != "current":
                # Continue the already-supported preceding transition. Each
                # step rechecks exact schema and project identity under lock.
                transition_project_schema(database_path, project_id, allow_closed=allow_closed)
            return True
    finally:
        engine.dispose()
