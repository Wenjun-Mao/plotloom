"""Retained proof reuse never substitutes for independently requested file bytes."""
from contextlib import closing
import json
import sqlite3

import pytest

from plotloom.autopilot_handoff_contracts import BulkHumanHandoffRequest
from plotloom.persistence.project.autopilot_handoff import record_handoff, review_material
from plotloom.persistence.project.image_source_lineage import assert_geometry
from plotloom.project_storage import ProjectStorageCorruptionError
from plotloom.project_storage.handoff_validation import assert_handoff
from plotloom.project_storage.proof_scope import proof_scope
from tests.autopilot_geometry_fixtures import copy_geometry_frame_seed
from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed
from tests.test_bulk_material_handoff import bulk_observation


def assert_requested_bytes_reject_same_scope_mutation(store, uri):
    # Fill the retained proof first, then mutate exactly its content-addressed
    # file. The ordinary requested-byte reader must independently hash it.
    path = store.home / uri.removeprefix("project-file:")
    content = path.read_bytes()
    try:
        path.write_bytes(b"x" * len(content))
        with pytest.raises(ProjectStorageCorruptionError):
            store.artifacts.get(uri)
    finally:
        path.write_bytes(content)


def test_geometry_proof_rechecks_sql_mutation_and_rollback_and_requested_bytes(tmp_path, geometry_frame_seed):
    storage, view = copy_geometry_frame_seed(geometry_frame_seed, tmp_path / "geometry-proof")
    record = view.frames[0].geometry_preparation
    with closing(storage.projects.open(view.project_id)) as store, sqlite3.connect(store.database_path) as connection:
        def validate():
            assert_geometry(connection, record, project_id=view.project_id, run_id=record.run_id, asset_home=store.home)
        with proof_scope():
            connection.execute("BEGIN")
            validate(); validate()
            connection.execute("UPDATE v2_managed_assets SET original_hash=? WHERE id=?", ("f" * 64, record.output.asset_id))
            with pytest.raises(ValueError, match="geometry preparation differs"):
                validate()
            connection.rollback()
            validate()
            uri = connection.execute("SELECT original_uri FROM v2_managed_assets WHERE id=?", (record.output.asset_id,)).fetchone()[0]
            assert_requested_bytes_reject_same_scope_mutation(store, uri)
        with proof_scope():
            validate()


def test_handoff_proof_rechecks_sql_mutation_and_rollback_and_requested_bytes(tmp_path, awaiting_handoff_seed):
    storage, view, _ = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "handoff-proof")
    with closing(storage.projects.open(view.project_id)) as store:
        record_handoff(store, BulkHumanHandoffRequest.model_validate(bulk_observation(review_material(store))))
        with sqlite3.connect(store.database_path) as connection:
            identifier, run_id, project_id, approval_id, raw, digest = connection.execute(
                "SELECT id,run_id,project_id,approval_id,receipt,receipt_hash FROM v2_autopilot_handoffs").fetchone()
            receipt = json.loads(raw)
            def validate():
                return assert_handoff(connection, identifier, run_id, project_id, approval_id, receipt, digest, asset_home=store.home)
            with proof_scope():
                connection.execute("BEGIN")
                assert validate().id == identifier
                assert validate().id == identifier
                connection.execute("UPDATE v2_approval_decisions SET note=? WHERE id=?", ("Changed retained note", approval_id))
                with pytest.raises(ValueError, match="human approval attribution changed"):
                    validate()
                connection.rollback()
                assert validate().id == identifier
                uri = connection.execute("SELECT original_uri FROM v2_managed_assets WHERE id=?", (receipt["bundle"]["frames"][0]["assetId"],)).fetchone()[0]
                assert_requested_bytes_reject_same_scope_mutation(store, uri)
            with proof_scope():
                assert validate().id == identifier
