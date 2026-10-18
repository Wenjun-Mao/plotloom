"""Exact retained-layout and inherited geometry use genuine derivative evidence."""
import json
import sqlite3
from contextlib import closing

import pytest

from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_handoff_contracts import HumanHandoffRequest
from plotloom.persistence.project.autopilot_bindings import assert_frame_binding
from plotloom.persistence.project.autopilot_handoff import (
    record_handoff,
    review_material,
)
from plotloom.persistence.project.image_source_lineage import resolve_image_source
from plotloom.project_storage import ProjectStorageCorruptionError
from plotloom.project_storage.schema_upgrade import (
    assert_prior_database,
    logical_inventory,
    prior_schema_objects,
)
from tests.autopilot_compact_text_fixtures import compact_safety_image_environment
from tests.autopilot_continuation_layout_fixtures import retain_pre_continuation_layout
from tests.autopilot_geometry_fixtures import (
    copy_geometry_frame_seed,
    first_geometry_frame,
    mismatch,
)
from tests.autopilot_image_fixtures import run_pack
from tests.test_autopilot_continuation import origin_rows, request_for
from tests.test_autopilot_handoff import observation
from tests.test_autopilot_schema_upgrade import retained_bytes


def assert_exact_prior(home, project_id):
    before = retained_bytes(home)
    with closing(sqlite3.connect(home / "project.sqlite3")) as connection:
        original = logical_inventory(connection, prior_schema_objects("pre_continuation"))
        trace = []
        connection.set_trace_callback(trace.append)
        assert_prior_database(connection, project_id, layout="pre_continuation")
        assert not any("v2_autopilot_inheritance" in sql for sql in trace)
        assert logical_inventory(connection, prior_schema_objects("pre_continuation")) == original
    assert retained_bytes(home) == before


def test_exact_prior_partial_geometry_validates_without_current_table_reads(tmp_path, geometry_frame_seed):
    storage, view = copy_geometry_frame_seed(geometry_frame_seed, tmp_path / "prior")
    with closing(storage.projects.open(view.project_id)) as store:
        stopped = store.repository.autopilot.control(view.project_id, expected_revision=view.revision, action="cancel")
        home = store.home
    geometry = stopped.frames[0].geometry_preparation
    assert geometry is not None and (geometry.source.asset.width, geometry.source.asset.height) != (geometry.output.width, geometry.output.height)
    retain_pre_continuation_layout(home)
    assert_exact_prior(home, view.project_id)
    with closing(sqlite3.connect(home / "project.sqlite3")) as connection:
        decision_id = connection.execute("SELECT decision_id FROM v2_autopilot_frames WHERE run_id=? AND shot_id=?",
            (view.id, stopped.frames[0].shot_id)).fetchone()[0]
        trace = []
        connection.set_trace_callback(trace.append)
        with pytest.raises(ValueError, match="prior-layout frame cannot inherit"):
            assert_frame_binding(connection, "different-run", view.project_id, decision_id, stopped.frames[0], continuation=False)
        assert not any("v2_autopilot_inheritance" in sql for sql in trace)
    # Prior inspection cannot change the next caller's strict-current default.
    with closing(sqlite3.connect(home / "project.sqlite3")) as connection, pytest.raises(sqlite3.OperationalError, match="v2_autopilot_inheritance"):
        resolve_image_source(connection, view.project_id, stopped.frames[0].asset_id)
    assert_exact_prior(home, view.project_id)
    from plotloom.project_storage.schema_upgrade import upgrade_project
    from plotloom.specialist_settings import SpecialistRegistry
    before = retained_bytes(home)
    upgrade_project(home, SpecialistRegistry(storage.application.root))
    assert retained_bytes(home) == before
    with closing(storage.projects.open(view.project_id)) as store:
        assert store.repository.autopilot.current(view.project_id).frames == stopped.frames


def test_geometry_continuation_reopens_then_finishes_only_missing_work(tmp_path, monkeypatch, compact_two_cut_text_prefix):
    storage, registry, service, view, images, text = compact_safety_image_environment(tmp_path, monkeypatch, compact_two_cut_text_prefix)
    registry._codex_exec_test_host.image_geometry = mismatch
    try:
        partial = first_geometry_frame(storage, service, view)
        stopped = service.control(view.project_id, RunControlRequest(expected_revision=partial.revision, action="cancel"))
        with closing(storage.projects.open(view.project_id)) as store:
            original = origin_rows(store, view.id)
            request = request_for(store, stopped)
        from plotloom.creative_handoff_exchange import CreativeHandoffExchange
        from tests.autopilot_controller_fixtures import PIN, UPSTREAM_PIN
        monkeypatch.setattr(CreativeHandoffExchange, "current_execution_pin", lambda _self, stage:
            (PIN if stage.startswith("bridge-") else UPSTREAM_PIN) | {"upstreamRevision": "b" * 40})
        child = service.continue_material(view.project_id, request)
        assert child.policy.code_revision != stopped.policy.code_revision
        with closing(storage.projects.open(view.project_id)) as store:
            assert store.repository.autopilot.current(view.project_id).frames == stopped.frames
        previous = list(images)
        complete = run_pack(storage, service, child)
        assert len(complete.frames) == 6 and all(frame in complete.frames for frame in stopped.frames)
        assert len(images) == len(set(images)) == 8 and images[:len(previous)] == previous and not text
        with closing(storage.projects.open(view.project_id)) as store:
            assert origin_rows(store, view.id) == original
            handed_off = record_handoff(store, HumanHandoffRequest.model_validate(observation(review_material(store))))
            assert handed_off.state == "handed_off"
        with closing(storage.projects.open(view.project_id)):
            pass
    finally:
        service.close()


@pytest.mark.parametrize("handed_off", [False, True])
def test_exact_prior_geometry_bundle_and_reviewed_sources(tmp_path, monkeypatch, compact_two_cut_text_prefix, handed_off):
    storage, registry, service, view, _images, _text = compact_safety_image_environment(tmp_path, monkeypatch, compact_two_cut_text_prefix)
    registry._codex_exec_test_host.image_geometry = mismatch
    try:
        complete = run_pack(storage, service, view)
        assert complete.state == "awaiting_review" and all(frame.geometry_preparation for frame in complete.frames)
        with closing(storage.projects.open(view.project_id)) as store:
            if handed_off:
                record_handoff(store, HumanHandoffRequest.model_validate(observation(review_material(store))))
                retain_reviewed_geometry_uses(store, view.project_id)
            home = store.home
        service.close()
        retain_pre_continuation_layout(home)
        assert_exact_prior(home, view.project_id)
    finally:
        service.close()


def retain_reviewed_geometry_uses(store, project_id):
    """Real target-use and scene-continuity chains reach the same derivative."""
    from plotloom.persistence.schema import (
        ReviewedShotBindingRow,
        VisualSelectionStateRow,
    )
    frames = review_material(store)["bundle"]["frames"]
    source, target = frames[:2]
    intent = store.media.create_visual_intent(project_id, source["assetId"], {
        "role": "shot_keyframe", "compositionIntent": "Independent target geometry review",
        "sourceRefs": [target["shotId"]], "sourceBindingId": source["sourceId"],
    }, target_shot_id=target["shotId"])
    with store.repository._read() as session:
        binding = session.get(ReviewedShotBindingRow, source["sourceId"])
        revision = session.get(VisualSelectionStateRow, project_id).revision
    store.media.select_reviewed_keyframe(project_id, asset_id=source["assetId"], shot_id=target["shotId"],
        scene_id=target["sceneId"], expected_selection_revision=revision,
        storyboard_revision=binding.storyboard_revision, approval_id=binding.approval_id,
        compatibility_note="Fixture inspected target pixels", visual_intent_id=intent["id"],
        visual_intent_revision=intent["revision"])
    job = store.media.prepare_image_job(project_id, approval_id=binding.approval_id, shot_id=target["shotId"],
        storyboard_revision=binding.storyboard_revision, presentation_change="Independent continuity fixture",
        scene_continuity_binding_id=source["sourceId"], contract_version=3)["job"]
    assert job["request"]["frozenSnapshot"]["sceneContinuity"]["assetId"] == source["assetId"]


@pytest.mark.parametrize("defect", ["missing_link", "evidence", "state", "unlinked_copy", "ambiguous_original"])
def test_geometry_resolver_rejects_every_unproven_inherited_copy(tmp_path, geometry_frame_seed, defect):
    storage, view = copy_geometry_frame_seed(geometry_frame_seed, tmp_path / "tampered")
    with closing(storage.projects.open(view.project_id)) as store:
        stopped = store.repository.autopilot.control(view.project_id, expected_revision=view.revision, action="cancel")
        child = store.repository.autopilot.continue_material(view.project_id, request=request_for(store, stopped), policy=stopped.policy)
        frame = child.frames[0]
        home = store.home
        with store.repository.engine.begin() as connection:
            row = connection.exec_driver_sql("SELECT id,operation_key,evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND json_extract(evidence,'$.geometryPreparation.output.assetId')=?", (child.id, frame.asset_id)).one()
            if defect == "missing_link":
                connection.exec_driver_sql("DELETE FROM v2_autopilot_inheritance WHERE run_id=? AND operation_key=?", (child.id, row[1]))
            elif defect == "evidence":
                raw = json.loads(row[2]); raw["result"]["unproven"] = True
                connection.exec_driver_sql("UPDATE v2_autopilot_checkpoints SET evidence=? WHERE id=?", (json.dumps(raw), row[0]))
            elif defect == "state":
                connection.exec_driver_sql("UPDATE v2_autopilot_checkpoints SET state='delivered' WHERE id=?", (row[0],))
            else:
                owner = child.id if defect == "unlinked_copy" else view.id
                connection.exec_driver_sql("INSERT INTO v2_autopilot_checkpoints SELECT 'unproven-copy',run_id,project_id,operation_key || ':unproven',revision,state,evidence,created_at,updated_at FROM v2_autopilot_checkpoints WHERE run_id=? AND operation_key=?", (owner, row[1]))
    with closing(sqlite3.connect(home / "project.sqlite3")) as connection, pytest.raises(ValueError, match="geometry derivative"):
        resolve_image_source(connection, view.project_id, frame.asset_id, shot_id=frame.shot_id)
    with pytest.raises(ProjectStorageCorruptionError):
        storage.projects.open(view.project_id)
