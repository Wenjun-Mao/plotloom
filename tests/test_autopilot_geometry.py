"""Deterministic geometry is local authority, never another native generation."""
from contextlib import closing
from io import BytesIO

import pytest
from PIL import Image

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.geometry_preparation import prepare_geometry
from plotloom.geometry_preparation_contracts import GeometryRecipe
from plotloom.persistence.project.image_source_lineage import source_in_session
from tests.autopilot_image_fixtures import image_environment
from tests.test_autopilot_images import current


def test_recipe_is_exif_transposed_centered_cover_at_exact_dimensions():
    source = BytesIO()
    image = Image.new("RGB", (1672, 941), "blue")
    exif = image.getexif(); exif[274] = 6
    image.save(source, format="JPEG", exif=exif)
    raw = source.getvalue()
    output, observed, recipe = prepare_geometry(raw, width=720, height=1280)
    assert (observed.width, observed.height) == (720, 1280)
    assert (recipe.oriented_width, recipe.oriented_height, recipe.exif_orientation) == (941, 1672, 6)
    assert source.getvalue() == raw and output != raw
    with pytest.raises(ValueError):
        GeometryRecipe.model_validate(recipe.model_dump() | {"crop_box": (0, 0, 941, 1672)})


def first_geometry_frame(storage, service, view):
    for _ in range(30):
        service.step(view.project_id)
        result = current(storage, view)
        if result.frames:
            return result
        assert result.state in {"running", "waiting"}, result.blocker
    raise AssertionError("first geometry frame not selected")


def mismatch(*, context):
    return (941, 1672) if "shot" in context["request"]["frozenSnapshot"] else None


@pytest.mark.parametrize("version", ["plotloom.pre-video.v2", "plotloom.pre-video.v3"])
def test_geometry_policy_assertion_accepts_retained_v2_and_current_v3(version):
    from types import SimpleNamespace
    from plotloom.geometry_preparation import geometry_policy
    from plotloom.persistence.codec import stable_hash
    from plotloom.persistence.project.image_source_lineage import geometry_policy_matches

    geometry = geometry_policy()
    policy = {"version": version, "geometryPreparation": geometry.model_dump(mode="json", by_alias=True),
        "imageWidth": 720, "imageHeight": 1280}
    if version == "plotloom.pre-video.v2":
        policy.update(renderStyle="realistic", artRenderStyle="realistic")
    else:
        policy["styleAuthority"] = "brief"
    frozen_bytes = dict(policy)
    policy_hash = stable_hash(policy)
    record = SimpleNamespace(policy_hash=policy_hash,
        recipe=SimpleNamespace(version=geometry.recipe_version, target_width=720, target_height=1280),
        runtime=geometry.runtime)

    assert geometry_policy_matches(policy, record, policy_hash)
    assert policy == frozen_bytes
    policy["imageWidth"] = 1024
    assert not geometry_policy_matches(policy, record, policy_hash)


def test_geometry_derivative_retains_original_and_no_native_job_increment(tmp_path, monkeypatch):
    storage, registry, service, view, calls, _ = image_environment(tmp_path, monkeypatch, geometry=mismatch, brief=FIXED_CHINESE_BRIEF.model_copy(update={"aspect_ratio": "9:16", "decision_points_per_path": 1, "ending_count": 2, "desired_join_count": 0}))
    try:
        assert view.policy.version == "plotloom.pre-video.v3"
        result = first_geometry_frame(storage, service, view)
        frame = result.frames[0]; record = frame.geometry_preparation
        assert record and (frame.width, frame.height) == (720, 1280)
        assert (record.source.asset.width, record.source.asset.height) == (941, 1672)
        assert len(calls) == 3 and not registry.view()["busy"]
        assert len([item for item in result.checkpoints if item["evidence"].get("jobId")]) == 11
        assert len([item for item in result.checkpoints if item["evidence"]["owner"] == "geometry-preparation"]) == 1
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository._read() as session:
                from plotloom.persistence.schema import ManagedAssetRow
                raw = session.get(ManagedAssetRow, record.source.asset.asset_id)
                assert store.artifacts.get(raw.original_uri)
                lineage = source_in_session(session, view.project_id, frame.asset_id, shot_id=frame.shot_id)
                assert lineage.kind == "managed_geometry_derivative" and lineage.job_id == frame.job_id
                assert lineage.geometry == record
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_image_jobs").scalar() == 1
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_approval_decisions").scalar() == 0
    finally:
        service.close()


def original_ready(storage, service, view):
    for _ in range(30):
        service.step(view.project_id)
        result = current(storage, view)
        original = next((item for item in result.checkpoints if item["evidence"]["owner"] == "image"
            and item["state"] == "adopted" and item["evidence"]["result"].get("geometryCompatible") is False), None)
        if original:
            return result, original
        assert result.state in {"running", "waiting"}, result.blocker
    raise AssertionError("original receipt not selected")


def geometry_context(store, view, original):
    from plotloom.autopilot_materials import initial_inventory
    inventory = initial_inventory(store, view.policy)
    subject = next(item for item in inventory.subjects if item.operation_key == original["operationKey"])
    return subject, inventory


def test_concurrent_local_preparation_is_idempotent_and_does_not_dispatch(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from plotloom.autopilot_geometry_preparation import prepare_first_frame_geometry
    storage, _registry, service, view, calls, _ = image_environment(tmp_path, monkeypatch, geometry=mismatch)
    try:
        retained, original = original_ready(storage, service, view)
        count = len(calls)
        def prepare():
            with closing(storage.projects.open(view.project_id)) as store:
                subject, inventory = geometry_context(store, retained, original)
                prepare_first_frame_geometry(store, retained, service.claim, subject, inventory, original)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: prepare(), range(2)))
        result = current(storage, view)
        assert len(result.frames) == 1 and len(calls) == count
        assert len([item for item in result.checkpoints if item["evidence"]["owner"] == "geometry-preparation"]) == 1
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_autopilot_decisions WHERE scope='geometry_preparation'").scalar() == 1
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_autopilot_decisions WHERE scope='provisional_selection' AND checkpoint_id IN (SELECT id FROM v2_autopilot_checkpoints WHERE operation_key LIKE '%:geometry')").scalar() == 1
    finally:
        service.close()


@pytest.mark.parametrize("failure", ["transaction", "selection"])
def test_failure_then_restart_reuses_local_identity_without_regeneration(tmp_path, monkeypatch, failure):
    import plotloom.autopilot_geometry_preparation as geometry
    from plotloom.autopilot_contracts import RunControlRequest
    from plotloom.autopilot_service import AutopilotService
    from plotloom.persistence.project.autopilot import AutopilotPersistence
    storage, registry, service, view, calls, _ = image_environment(tmp_path, monkeypatch, geometry=mismatch)
    resumed = None
    try:
        retained, original = original_ready(storage, service, view)
        count = len(calls)
        if failure == "selection":
            original_method = geometry.select_geometry_frame
            def crash(*args, **kwargs): raise RuntimeError("injected crash after local commit")
            monkeypatch.setattr(geometry, "select_geometry_frame", crash)
        else:
            original_method = AutopilotPersistence.checkpoint
            def crash(self, key, **kwargs):
                if key.endswith(":geometry"): raise RuntimeError("injected rollback before checkpoint")
                return original_method(self, key, **kwargs)
            monkeypatch.setattr(AutopilotPersistence, "checkpoint", crash)
        with pytest.raises(RuntimeError, match="injected"):
            service.step(view.project_id)
        blocked = current(storage, view)
        assert blocked.state in {"running", "waiting"} and not blocked.frames and len(calls) == count
        records = [item for item in blocked.checkpoints if item["evidence"]["owner"] == "geometry-preparation"]
        assert len(records) == (1 if failure == "selection" else 0)
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_managed_asset_provenance WHERE json_extract(declaration,'$.origin')='plotloom_geometry_preparation'").scalar() == len(records)
        if failure == "selection": monkeypatch.setattr(geometry, "select_geometry_frame", original_method)
        else: monkeypatch.setattr(AutopilotPersistence, "checkpoint", original_method)
        service.close(); resumed = AutopilotService(storage, registry)
        assert resumed.acquire_controller()
        result = first_geometry_frame(storage, resumed, view)
        assert len(calls) == count and len(result.frames) == 1
        if records:
            assert result.frames[0].geometry_preparation.preparation_hash == records[0]["evidence"]["geometryPreparation"]["preparationHash"]
    finally:
        service.close()
        if resumed: resumed.close()


@pytest.mark.parametrize("defect", ["source", "candidate", "recipe", "output", "missing-decision", "missing-source", "missing-output"])
def test_tampered_or_missing_lineage_refuses_ordinary_open(tmp_path, monkeypatch, defect):
    from copy import deepcopy
    from pathlib import Path

    from plotloom.persistence.schema import AutopilotCheckpointRow, ManagedAssetRow
    from plotloom.project_storage import (
        ProjectStorageConfinementError,
        ProjectStorageCorruptionError,
    )
    storage, _registry, service, view, _calls, _ = image_environment(tmp_path, monkeypatch, geometry=mismatch)
    try:
        result = first_geometry_frame(storage, service, view); frame = result.frames[0]; record = frame.geometry_preparation
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository._write() as session:
                if defect.startswith("missing-") and defect != "missing-decision":
                    asset = session.get(ManagedAssetRow, record.source.asset.asset_id if defect == "missing-source" else frame.asset_id)
                    (store.home / asset.original_uri.removeprefix("project-file:")).unlink()
                elif defect == "missing-decision":
                    from sqlalchemy import delete

                    from plotloom.persistence.schema import AutopilotDecisionRow
                    session.execute(delete(AutopilotDecisionRow).where(AutopilotDecisionRow.scope == "geometry_preparation"))
                else:
                    from sqlalchemy import select
                    row = session.scalar(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == view.id, AutopilotCheckpointRow.operation_key.like("%:geometry")))
                    evidence = deepcopy(row.evidence); value = evidence["geometryPreparation"]
                    if defect == "source": value["source"]["jobId"] = "foreign-job"
                    elif defect == "candidate": value["source"]["candidateId"] = "foreign-candidate"
                    elif defect == "recipe": value["recipe"]["cropBox"] = [0, 0, 941, 1672]
                    else: value["output"]["originalHash"] = "a"*64
                    row.evidence = evidence
        with pytest.raises((ProjectStorageCorruptionError, ProjectStorageConfinementError)):
            with closing(storage.projects.open(view.project_id)): pass
    finally:
        service.close()


@pytest.mark.parametrize("action", ["pause", "cancel", "takeover"])
def test_stopped_run_cannot_create_geometry(tmp_path, monkeypatch, action):
    from plotloom.autopilot_contracts import RunControlRequest
    from plotloom.autopilot_geometry_preparation import prepare_first_frame_geometry
    from plotloom.exceptions import InvalidTransitionError
    storage, _registry, service, view, calls, _ = image_environment(tmp_path, monkeypatch, geometry=mismatch)
    try:
        retained, original = original_ready(storage, service, view); count = len(calls)
        service.control(view.project_id, RunControlRequest(expected_revision=retained.revision, action=action))
        with closing(storage.projects.open(view.project_id)) as store:
            subject, inventory = geometry_context(store, retained, original)
            with pytest.raises(InvalidTransitionError):
                prepare_first_frame_geometry(store, retained, service.claim, subject, inventory, original)
        assert not current(storage, view).frames and len(calls) == count
    finally:
        service.close()


def test_partial_derivative_snapshot_preserves_lineage_and_never_resumes_native(tmp_path, monkeypatch):
    from pathlib import Path

    from plotloom.autopilot_contracts import RunControlRequest
    from plotloom.exceptions import InvalidTransitionError
    from plotloom.project_storage import ProjectFolderStorage
    storage, _registry, service, view, _calls, _ = image_environment(tmp_path, monkeypatch, geometry=mismatch)
    try:
        result = first_geometry_frame(storage, service, view); frame = result.frames[0]
        service.control(view.project_id, RunControlRequest(expected_revision=result.revision, action="pause")); service.close()
        snapshot = storage.recovery.create_snapshot(view.project_id)
        restored = ProjectFolderStorage(outputs_root=tmp_path / "restore-outputs", application_data_root=tmp_path / "restore-application")
        restored.recovery.restore(Path(snapshot.location)); restored.recovery.acknowledge_recovery(view.project_id)
        with closing(restored.projects.open(view.project_id)) as store:
            current_view = store.repository.autopilot.current(view.project_id)
            assert current_view.frames[0] == frame
            with pytest.raises(InvalidTransitionError, match="portable"):
                store.repository.autopilot.claim(view.project_id, "new-runtime")
    finally:
        service.close()


def test_human_handoff_binds_derivative_bytes_and_source_v3_identity_then_withdraws(tmp_path, monkeypatch):
    from plotloom.autopilot_handoff_contracts import HumanHandoffRequest
    from plotloom.persistence.project.autopilot_authority import video_eligible
    from plotloom.persistence.project.autopilot_handoff import (
        record_handoff,
        review_material,
    )
    from plotloom.persistence.schema import ImageJobRow, SamePersonReviewRow
    from tests.autopilot_image_fixtures import (
        assert_compact_handoff_pack,
        handoff_image_environment,
        run_pack,
    )
    from tests.test_autopilot_handoff import observation
    first = True
    def geometry(*, context):
        nonlocal first
        if "shot" in context["request"]["frozenSnapshot"] and first:
            first = False; return 941, 1672
        return None
    storage, _registry, service, view, calls, _ = handoff_image_environment(tmp_path, monkeypatch, geometry=geometry)
    try:
        result = run_pack(storage, service, view)
        assert_compact_handoff_pack(storage, view, result, calls)
        frame = next(frame for frame in result.frames if frame.geometry_preparation)
        assert len([f for f in result.frames if f.geometry_preparation]) == 1
        with closing(storage.projects.open(view.project_id)) as store:
            review = review_material(store)
            assert next(item for item in review["bundle"]["frames"] if item["assetId"] == frame.asset_id)["geometryPreparation"]["preparationHash"] == frame.geometry_preparation.preparation_hash
            complete = record_handoff(store, HumanHandoffRequest.model_validate(observation(review)))
            from sqlalchemy import select
            with store.repository._read() as session:
                assert video_eligible(session, view.project_id)
                rows = session.scalars(select(SamePersonReviewRow)).all()
                derived_review = next(row for row in rows if any(item.get("geometryPreparationHash") for item in row.reference_bindings))
                assert all(item["frameHash"] == frame.original_hash and item["geometryPreparationHash"] == frame.geometry_preparation.preparation_hash
                    and "comparisonOrigin" not in item for item in derived_review.reference_bindings)
                assert store.repository._media.same_person.same_person_review_is_current_in_session(session, view.project_id, derived_review)
            with store.repository.manual_command() as session:
                session.get(ImageJobRow, frame.job_id).state = "cancelled"
            with store.repository._read() as session:
                assert not video_eligible(session, view.project_id)
                assert not store.repository._media.same_person.same_person_review_is_current_in_session(session, view.project_id, derived_review)
        with closing(storage.projects.open(view.project_id)): pass
    finally:
        service.close()


@pytest.mark.parametrize("target", [(720, 1280), (1280, 720), (1024, 1024)])
def test_each_frozen_target_is_exact_and_original_is_preserved(target):
    from hashlib import sha256
    source = BytesIO(); Image.new("RGB", (941, 1672), "orange").save(source, format="PNG")
    raw = source.getvalue(); digest = sha256(raw).hexdigest()
    output, observed, recipe = prepare_geometry(raw, width=target[0], height=target[1])
    assert (observed.width, observed.height) == target
    assert (recipe.target_width, recipe.target_height) == target
    assert sha256(source.getvalue()).hexdigest() == digest and output != raw


def test_matching_aspect_keeps_raw_candidate_bytes_and_dimensions(tmp_path, monkeypatch):
    def geometry(*, context):
        return (960, 540) if "shot" in context["request"]["frozenSnapshot"] else None
    storage, _registry, service, view, calls, _ = image_environment(tmp_path, monkeypatch, geometry=geometry)
    try:
        result = first_geometry_frame(storage, service, view); frame = result.frames[0]
        assert frame.geometry_preparation is None and (frame.width, frame.height) == (960, 540)
        assert not any(item["evidence"]["owner"] == "geometry-preparation" for item in result.checkpoints)
        assert len(calls) == 3
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository._read() as session:
                source = source_in_session(session, view.project_id, frame.asset_id, shot_id=frame.shot_id)
                assert source.kind == "native_output" and source.source_hash == frame.original_hash
    finally:
        service.close()


def test_standalone_geometry_import_has_no_persistence_cycle_and_hashes_are_canonical():
    import subprocess
    import sys

    from plotloom.contract_hash import stable_hash
    from plotloom.persistence.codec import stable_hash as persisted_hash
    assert stable_hash({"说明": [1, 0.25, {"x": None}]}) == persisted_hash({"说明": [1, 0.25, {"x": None}]})
    result = subprocess.run([sys.executable, "-c", "from plotloom.geometry_preparation import geometry_policy; import sys; assert 'plotloom.persistence' not in sys.modules; assert geometry_policy().runtime.transform_hash"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_retained_v1_policy_does_not_acquire_geometry_permission():
    from plotloom.autopilot_contracts import LaunchPolicy
    from plotloom.geometry_preparation import geometry_policy
    raw = {"version": "plotloom.pre-video.v1", "renderStyle": "realistic", "artRenderStyle": "realistic",
        "maxImages": 80, "maxJobs": 96, "imageWidth": 720, "imageHeight": 1280,
        "codeRevision": "a"*40, "specialistBindings": {"text": "text", "image": "image"}, "executionPins": {}, "brief": {}}
    retained = LaunchPolicy.model_validate(raw)
    assert retained.geometry_preparation is None and retained.model_dump(mode="json", by_alias=True) == raw
    with pytest.raises(ValueError, match="only to policy v2"):
        LaunchPolicy.model_validate(raw | {"geometryPreparation": geometry_policy().model_dump(mode="json", by_alias=True)})


def test_retired_policy_is_refused_at_domain_resume_and_machine_command_boundary(tmp_path):
    from plotloom.autopilot_contracts import OperationScope
    from plotloom.contract_hash import stable_hash
    from plotloom.exceptions import InvalidTransitionError
    from plotloom.persistence.schema import AutopilotRunRow
    from plotloom.project_storage import ProjectFolderStorage
    from tests.autopilot_fixtures import authority, start_run
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        run = start_run(store)
        with store.repository._write() as session:
            row = session.get(AutopilotRunRow, run.id)
            policy = dict(row.policy); policy.pop("geometryPreparation"); policy["version"] = "plotloom.pre-video.v1"
            row.policy = policy; row.policy_hash = stable_hash(policy)
        for scope in [OperationScope.SOURCE, OperationScope.TEXT, OperationScope.INSTALL, OperationScope.IMAGE, OperationScope.GEOMETRY, OperationScope.SELECT]:
            with pytest.raises(InvalidTransitionError, match="retired"):
                with store.repository.autopilot_command(authority(run, scope)): pytest.fail("retired policy admitted new machine work")
        with store.repository.autopilot_command(authority(run, OperationScope.EVIDENCE)): pass
        with store.repository._write() as session:
            row = session.get(AutopilotRunRow, run.id); row.state = "paused"
        current_run = store.repository.autopilot.current(store.manifest.project_id)
        with pytest.raises(InvalidTransitionError, match="retired"):
            store.repository.autopilot.control(store.manifest.project_id, expected_revision=current_run.revision, action="resume")
        assert store.repository.autopilot.current(store.manifest.project_id).state == "paused"
