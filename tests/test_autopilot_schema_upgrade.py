"""Exact immediate-prior admission and transactional preservation on fixtures."""
from contextlib import closing
import sqlite3

import pytest

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage, ProjectStorageCorruptionError
from plotloom.project_storage.schema_upgrade import inventory_layouts, logical_inventory, prior_schema_objects, upgrade_project
from plotloom.specialist_settings import SpecialistRegistry
from tests.autopilot_fixtures import make_prior_layout
from tests.project_storage_fixtures import FixtureResolver, fixture_profile


def test_immediate_prior_upgrade_preserves_cancelled_run_and_all_material_bytes(tmp_path, awaiting_handoff_seed):
    from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed
    from tests.autopilot_continuation_layout_fixtures import retain_pre_continuation_layout
    storage, view, _calls = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "preserved")
    with closing(storage.projects.open(view.project_id)) as store:
        store.repository.autopilot.control(view.project_id, expected_revision=view.revision, action="cancel")
        home = store.home
    retain_pre_continuation_layout(home)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        before = logical_inventory(connection, prior_schema_objects("pre_continuation"))
    files = retained_bytes(home)
    upgrade_project(home, SpecialistRegistry(storage.application.root))
    with sqlite3.connect(home / "project.sqlite3") as connection:
        from plotloom.persistence.codec import stable_hash
        for name, original in before.items():
            projection = ",".join(f'"{column}"' for column in original["columns"])
            rows = connection.execute(f'SELECT {projection} FROM "{name}"').fetchall()
            assert len(rows) == original["count"] and stable_hash(sorted(rows, key=stable_hash)) == original["hash"]
    assert retained_bytes(home) == files
    with closing(storage.projects.open(view.project_id)) as store:
        assert store.repository.autopilot.current(view.project_id).state == "cancelled"


def prior_fixture(tmp_path, *, closed=False):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        ProjectPipelineExecutor(FixtureResolver()).execute(store, profile=fixture_profile())
        project_id, home = store.manifest.project_id, store.home
        head = store.authoring.get_stage_head(project_id, StageName.STORYBOARD)
        approval = store.authoring.decide_storyboard_approval(project_id, expected_revision=head.revision,
            expected_content_hash=head.content_hash, decision="approve", reviewer="fixture owner", gate_set_version="storyboard.v2")
        board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
        result = store.media.prepare_image_job(project_id, approval_id=approval.id, shot_id=board.shots[0].id,
            storyboard_revision=head.revision, presentation_change="Offline preservation unit")
        store.media.cancel_image_job(project_id, result["job"]["id"], "never sent fixture")
    if closed:
        storage.projects.close_project(project_id)
    make_prior_layout(home)
    return storage, project_id, home


@pytest.mark.parametrize("closed", [False, True])
def test_explicit_upgrade_preserves_every_original_column_and_operational_state(tmp_path, closed):
    storage, project_id, home = prior_fixture(tmp_path, closed=closed)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        before = logical_inventory(connection, prior_schema_objects())
    with pytest.raises(ProjectStorageCorruptionError, match="unsupported"):
        storage.projects.inspect(project_id)
    assert inventory_layouts(storage.projects.outputs_root)[0]["layout"] == "prior"
    registry = SpecialistRegistry(storage.application.root)
    receipt = upgrade_project(home, registry)
    assert receipt["changed"] is True
    with sqlite3.connect(home / "project.sqlite3") as connection:
        for name, original in before.items():
            projection = ",".join(f'"{column}"' for column in original["columns"])
            rows = connection.execute(f'SELECT {projection} FROM "{name}"').fetchall()
            from plotloom.persistence.codec import stable_hash
            assert (len(rows), stable_hash(sorted(rows, key=stable_hash))) == (original["count"], original["hash"])
        assert connection.execute("SELECT count(*) FROM v2_production_units WHERE machine_decision_id IS NOT NULL").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM v2_autopilot_runs").fetchone()[0] == 0
    with closing(storage.projects.inspect(project_id)) as store:
        assert store.repository.operational_state()[0] == ("closed" if closed else "open")
        assert len(store.authoring.list_approval_decisions(project_id)) == 1
    assert upgrade_project(home, registry)["changed"] is False


def test_upgrade_crash_rolls_back_ddl_and_all_retained_rows(tmp_path):
    storage, project_id, home = prior_fixture(tmp_path)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        before = logical_inventory(connection, prior_schema_objects())
    def crash(_connection):
        raise RuntimeError("injected after DDL")
    with pytest.raises(RuntimeError, match="injected"):
        upgrade_project(home, SpecialistRegistry(storage.application.root), after_ddl=crash)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        from plotloom.project_storage.schema_upgrade import classify_layout
        assert classify_layout(connection) == "prior"
        assert logical_inventory(connection, prior_schema_objects()) == before


def test_unknown_layout_is_not_a_migration_input(tmp_path):
    storage, project_id, home = prior_fixture(tmp_path)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        connection.execute("CREATE TABLE unknown_authority (id TEXT)")
    assert inventory_layouts(storage.projects.outputs_root)[0]["layout"] == "unsupported"
    with pytest.raises(ProjectStorageCorruptionError, match="immediate-prior"):
        upgrade_project(home, SpecialistRegistry(storage.application.root))


def test_active_native_reservation_blocks_upgrade_without_clearing_it(tmp_path):
    storage, project_id, home = prior_fixture(tmp_path)
    registry = SpecialistRegistry(storage.application.root)
    root = registry.root / "dispatch" / "fixture"
    root.mkdir(parents=True)
    import json
    registry.path.write_text(json.dumps({"settings": {"text": {"name": "text", "taskId": None}, "image": {"name": "image", "taskId": None}}, "roots": {"fixture": str(root)}}))
    inflight = root / "inflight.json"
    inflight.write_text('{"jobId":"unknown","taskId":"fixture"}')
    from plotloom.image_job_contracts import ImageJobError
    with pytest.raises(ImageJobError, match="不能升级"):
        upgrade_project(home, registry)
    assert inflight.exists()


def valued_prior_fixture(tmp_path):
    from tests.test_autopilot_recovery import accepted_outline
    from tests.test_project_storage_recovery import _png
    from plotloom.managed_media import inspect_import_image, ManagedMediaLimits, publish_import, ImportDeclaration
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    project_id, home = accepted_outline(storage)
    with closing(storage.projects.open(project_id)) as store:
        content = _png()
        observed = inspect_import_image(content, ManagedMediaLimits())
        store.media.record_managed_import(project_id, original_hash=observed.content_hash,
            display_hash=observed.display_hash, mime_type=observed.mime_type, byte_size=observed.byte_size,
            width=observed.width, height=observed.height,
            declaration=ImportDeclaration(origin="valued preservation fixture", rights="unknown").model_dump(mode="json", by_alias=True),
            publish=lambda: publish_import(store.artifacts, content, observed))
    make_prior_layout(home)
    return storage, project_id, home


def retained_bytes(home):
    from hashlib import sha256
    return {path.relative_to(home).as_posix(): sha256(path.read_bytes()).hexdigest()
        for base in (home / "assets", home / "outputs") for path in base.rglob("*") if path.is_file()}


def test_upgrade_retains_valued_assets_and_native_package_bytes_even_on_rollback(tmp_path):
    storage, project_id, home = valued_prior_fixture(tmp_path)
    before = retained_bytes(home)
    assert len(before) >= 9
    registry = SpecialistRegistry(storage.application.root)
    def crash(_connection):
        raise RuntimeError("valued rollback")
    with pytest.raises(RuntimeError, match="valued rollback"):
        upgrade_project(home, registry, after_ddl=crash)
    assert retained_bytes(home) == before
    upgrade_project(home, registry)
    assert retained_bytes(home) == before
    with closing(storage.projects.open(project_id)) as store:
        assert store.source_outline_state().accepted_outline is not None


@pytest.mark.parametrize("mutation", ["asset", "package", "secret", "symlink", "missing_package", "missing_request", "missing_input", "missing_assignment", "missing_template"])
def test_upgrade_refuses_unsafe_or_corrupt_retained_files_before_ddl(tmp_path, mutation):
    storage, project_id, home = valued_prior_fixture(tmp_path)
    if mutation == "asset":
        next(path for path in (home / "assets").rglob("*") if path.is_file()).write_bytes(b"changed")
    elif mutation == "package":
        next((home / "outputs").rglob("report.html")).write_text("changed report")
    elif mutation == "secret":
        next((home / "outputs").rglob("COPY_ASSIGNMENT.txt")).write_text("Bearer sk-abcdefghijklmnopqrstuvwxyz123456")
    elif mutation == "symlink":
        import shutil
        outside = tmp_path / "outside"
        shutil.move(home / "outputs", outside)
        (home / "outputs").symlink_to(outside, target_is_directory=True)
    else:
        import shutil
        job = next((home / "outputs/creative-handoff/jobs").iterdir())
        if mutation == "missing_package":
            shutil.rmtree(job / "package")
        else:
            missing = {"missing_request": job / "package/request.json", "missing_assignment": job / "package/COPY_ASSIGNMENT.txt",
                "missing_template": job / "package/completion-manifest.example.json", "missing_input": next((job / "package/inputs").iterdir())}
            missing[mutation].unlink()
    from plotloom.project_storage import ProjectStorageConfinementError
    with pytest.raises((ProjectStorageCorruptionError, ProjectStorageConfinementError)):
        upgrade_project(home, SpecialistRegistry(storage.application.root))
    with sqlite3.connect(home / "project.sqlite3") as connection:
        from plotloom.project_storage.schema_upgrade import classify_layout
        assert classify_layout(connection) == "prior"


def test_upgrade_rechecks_retained_files_after_last_ddl_hook_and_rolls_back(tmp_path):
    storage, project_id, home = valued_prior_fixture(tmp_path)
    def mutate(_connection):
        next((home / "outputs").rglob("report.html")).write_text("racing output change")
    with pytest.raises(ProjectStorageCorruptionError, match="payload hash"):
        upgrade_project(home, SpecialistRegistry(storage.application.root), after_ddl=mutate)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        from plotloom.project_storage.schema_upgrade import classify_layout
        assert classify_layout(connection) == "prior"
