"""Character delivery publication-phase folder transition contract."""
from __future__ import annotations

import sqlite3

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.project_storage.video_candidate_transition import (
    ProjectSchemaTransitionRequiredError,
    expected_project_schema_objects,
    project_schema_status,
)


def test_existing_character_folder_adds_publication_phase_on_admitted_open(tmp_path) -> None:
    """The additive provenance field does not rewrite existing delivery rows."""

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id, database = store.manifest.project_id, store.database_path
    store.close()
    proposal_id = "ij_" + "a" * 20
    delivery_id = "legacy-delivery-row"
    created_at = "2026-09-21 19:00:00.000000"
    with sqlite3.connect(database) as connection:
        # Seed a row from the immediately preceding contract. Its phase is
        # unknowable because that schema did not record completion-marker
        # observation, so transition must retain it as NULL.
        connection.execute(
            """
            INSERT INTO v2_character_reference_proposals
              (id, project_id, character_id, parent_candidate_asset_id, request,
               request_hash, state, exported_at, cancelled_at,
               cancellation_reason, created_at)
            VALUES (?, ?, ?, NULL, ?, ?, ?, NULL, NULL, NULL, ?)
            """,
            (proposal_id, project_id, "legacy-character", "{}", "a" * 64, "exported", created_at),
        )
        connection.execute(
            """
            INSERT INTO v2_character_reference_proposal_deliveries
              (id, proposal_id, delivery_id, manifest, manifest_hash, state,
               diagnostic_code, publication_phase, created_at)
            VALUES (?, ?, NULL, NULL, NULL, ?, ?, NULL, ?)
            """,
            (delivery_id, proposal_id, "rejected", "delivery_partial", created_at),
        )
        connection.execute(
            "ALTER TABLE v2_character_reference_proposal_deliveries DROP COLUMN publication_phase"
        )
        connection.commit()

    assert project_schema_status(database, project_id) == "character_delivery_publication_phase_transition_required"
    with pytest.raises(ProjectSchemaTransitionRequiredError, match="writable project open"):
        storage.projects.inspect(project_id)

    transitioned = storage.projects.open(project_id)
    try:
        assert transitioned.manifest.project_id == project_id
    finally:
        transitioned.close()
    assert project_schema_status(database, project_id) == "current"
    with sqlite3.connect(database) as connection:
        columns = [row[1] for row in connection.execute(
            "PRAGMA table_info(v2_character_reference_proposal_deliveries)"
        )]
        legacy_delivery = connection.execute(
            """
            SELECT id, state, diagnostic_code, created_at, publication_phase
            FROM v2_character_reference_proposal_deliveries WHERE id = ?
            """,
            (delivery_id,),
        ).fetchone()
    assert "publication_phase" in columns
    assert legacy_delivery == (
        delivery_id, "rejected", "delivery_partial", created_at, None,
    )


def test_existing_character_folder_keeps_historic_selection_metadata_when_optional(tmp_path) -> None:
    """The optional-metadata transition preserves prior authored values exactly."""

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id, database = store.manifest.project_id, store.database_path
    store.close()
    created_at = "2026-09-21 20:00:00.000000"
    asset_id = "a" * 36
    decision_id = "d" * 36
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            INSERT INTO v2_managed_assets
              (id, project_id, original_uri, original_hash, display_uri, display_hash,
               mime_type, byte_size, width, height, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (asset_id, project_id, "assets/original.png", "a" * 64,
             "assets/display.png", "b" * 64, "image/png", 1, 1, 1, created_at),
        )
        connection.execute(
            """
            INSERT INTO v2_character_reference_decisions
              (id, project_id, character_id, reference_revision, character_context,
               character_context_hash, primary_asset_id, complementary_asset_ids, asset_hashes,
               reviewer, notes, revoked_at, revoked_by, revocation_reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)
            """,
            (decision_id, project_id, "legacy-character", 1, "{}", "c" * 64,
             asset_id, "[]", "[]", "historic reviewer", "historic reason", created_at),
        )
        connection.execute("DROP INDEX ix_v2_character_reference_decisions_project_character")
        connection.execute("DROP TABLE v2_character_reference_decisions")
        predecessor = next(
            statement for kind, name, _table, statement in expected_project_schema_objects(
                include_video_candidate_selection=True
            ) if kind == "table" and name == "v2_character_reference_decisions"
        )
        assert predecessor is not None
        connection.execute(predecessor.replace(
            "reviewer VARCHAR(160), \n\tnotes TEXT,",
            "reviewer VARCHAR(160) NOT NULL, \n\tnotes TEXT NOT NULL,",
        ))
        connection.execute(
            "CREATE INDEX ix_v2_character_reference_decisions_project_character "
            "ON v2_character_reference_decisions (project_id, character_id, reference_revision)"
        )
        connection.execute(
            """
            INSERT INTO v2_character_reference_decisions
              (id, project_id, character_id, reference_revision, character_context,
               character_context_hash, primary_asset_id, complementary_asset_ids, asset_hashes,
               reviewer, notes, revoked_at, revoked_by, revocation_reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)
            """,
            (decision_id, project_id, "legacy-character", 1, "{}", "c" * 64,
             asset_id, "[]", "[]", "historic reviewer", "historic reason", created_at),
        )
        connection.commit()

    assert project_schema_status(database, project_id) == "character_selection_metadata_transition_required"
    opened = storage.projects.open(project_id)
    opened.close()
    assert project_schema_status(database, project_id) == "current"
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT reviewer, notes FROM v2_character_reference_decisions WHERE id = ?", (decision_id,)
        ).fetchone()
        nullable = {entry[1]: entry[3] for entry in connection.execute(
            "PRAGMA table_info(v2_character_reference_decisions)"
        )}
    assert row == ("historic reviewer", "historic reason")
    assert nullable["reviewer"] == 0
    assert nullable["notes"] == 0
