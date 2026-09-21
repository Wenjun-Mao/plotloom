"""Character delivery publication-phase folder transition contract."""
from __future__ import annotations

import sqlite3

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.project_storage.video_candidate_transition import (
    ProjectSchemaTransitionRequiredError,
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
