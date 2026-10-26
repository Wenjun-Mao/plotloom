"""Real folder admission and explicit serial-layout preservation on disposable data."""
import sqlite3
from contextlib import closing

import pytest

from plotloom.autopilot_contracts import (
    CommandAuthority,
    OperationScope,
    RunControlRequest,
)
from plotloom.codex_exec_contracts import CodexExecProfile
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.project_storage import (
    ProjectBusyError,
    ProjectFolderStorage,
    ProjectStorageCorruptionError,
)
from plotloom.project_storage.current_schema import schema_objects
from plotloom.project_storage.schema_upgrade import (
    SERIAL_EXEC_LAYOUT_HASH,
    classify_layout,
    logical_inventory,
    prior_schema_objects,
    upgrade_project,
)
from plotloom.source_outline_contracts import OutlineAcceptRequest
from plotloom.specialist_settings import SpecialistRegistry
from tests.autopilot_controller_fixtures import environment
from tests.autopilot_fixtures import policy_for
from tests.codex_exec_fixtures import PROFILE
from tests.source_outline_fixtures import _deliver, _material, _request
from tests.test_autopilot_schema_upgrade import retained_bytes


def _serial_layout(home):
    """Construct exact frozen SQL, copying every existing typed fixture row."""
    source_path = home / "project.sqlite3"
    destination = home / "serial-layout-transfer.sqlite3"
    with closing(sqlite3.connect(source_path)) as source, closing(sqlite3.connect(destination)) as target:
        objects = prior_schema_objects("serial_exec")
        for kind, _name, _table, sql in objects:
            if kind == "table":
                target.execute(sql)
        for kind, name, _table, sql in objects:
            if kind == "table":
                columns = [row[1] for row in target.execute(f'PRAGMA table_info("{name}")')]
                projection = ",".join(f'"{column}"' for column in columns)
                rows = source.execute(f'SELECT {projection} FROM "{name}"').fetchall()
                if rows:
                    target.executemany(f'INSERT INTO "{name}" ({projection}) VALUES ({",".join("?" for _ in columns)})', rows)
            elif kind == "index":
                target.execute(sql)
        target.commit()
    source_path.unlink()
    for suffix in ("-wal", "-shm"):
        source_path.with_name(source_path.name + suffix).unlink(missing_ok=True)
    destination.rename(source_path)


def _valued_serial_fixture(tmp_path, *, closed=False, convert_serial=True):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    from plotloom.managed_media import (
        ImportDeclaration,
        ManagedMediaLimits,
        inspect_import_image,
        publish_import,
    )
    from tests.test_project_storage_recovery import _png
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id, home = store.manifest.project_id, store.home
        retained = CodexExecProfile.model_validate(PROFILE.model_dump(mode="python") | {
            "contract_version": "plotloom.codex-exec.v7", "max_processes": 1,
            "max_text_processes": None, "max_image_processes": None, "max_queued_jobs": None,
        })
        policy = policy_for(store).model_copy(update={"executor_binding": retained})
        run = store.repository.autopilot.start(project_id, expected_brief_revision=store.project().revision, policy=policy)
        store.repository.autopilot.control(project_id, expected_revision=run.revision, action="takeover")
        # Explicit takeover stops the fresh run before manual rebuild. The
        # fixture preserves that authority and both admission/quiescence guards.
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = _request(project_id, source)
        store.prepare_outline_candidate(request)
        store.admit_outline_delivery(_deliver(store, request))
        store.accept_outline_candidate(OutlineAcceptRequest(job_id=request.job_id,
            expected_source_revision=1, expected_outline_revision=0))
        content = _png()
        observed = inspect_import_image(content, ManagedMediaLimits())
        store.media.record_managed_import(project_id, original_hash=observed.content_hash,
            display_hash=observed.display_hash, mime_type=observed.mime_type, byte_size=observed.byte_size,
            width=observed.width, height=observed.height,
            declaration=ImportDeclaration(origin="preserving serial-layout fixture", rights="unknown").model_dump(mode="json", by_alias=True),
            publish=lambda: publish_import(store.artifacts, content, observed))
    if closed:
        storage.projects.close_project(project_id)
    if convert_serial:
        _serial_layout(home)
    return storage, project_id, home


@pytest.mark.parametrize("closed", [False, True])
def test_serial_folder_requires_explicit_upgrade_and_preserves_valued_rows_bytes_and_v7_metadata(tmp_path, closed):
    storage, project_id, home = _valued_serial_fixture(tmp_path, closed=closed)
    before_bytes = retained_bytes(home)
    assert len(before_bytes) >= 9
    with sqlite3.connect(home / "project.sqlite3") as connection:
        assert classify_layout(connection) == "serial_exec"
        before_rows = logical_inventory(connection, prior_schema_objects("serial_exec"))
    with pytest.raises(ProjectStorageCorruptionError, match="unsupported"):
        storage.projects.open(project_id)
    receipt = upgrade_project(home, SpecialistRegistry(storage.application.root))
    assert receipt["priorLayoutHash"] == SERIAL_EXEC_LAYOUT_HASH
    assert receipt["changed"] is True
    assert retained_bytes(home) == before_bytes
    with sqlite3.connect(home / "project.sqlite3") as connection:
        from plotloom.persistence.codec import stable_hash
        for name, original in before_rows.items():
            projection = ",".join(f'"{column}"' for column in original["columns"])
            rows = connection.execute(f'SELECT {projection} FROM "{name}"').fetchall()
            assert (len(rows), stable_hash(sorted(rows, key=stable_hash))) == (original["count"], original["hash"])
        assert connection.execute("SELECT predecessor_run_id FROM v2_autopilot_runs").fetchall() == [(None,)]
        assert connection.execute("SELECT count(*) FROM v2_autopilot_inheritance").fetchone() == (0,)
    with closing(storage.projects.inspect(project_id)) as store:
        assert store.repository.operational_state()[0] == ("closed" if closed else "open")
        assert store.source_outline_state().accepted_outline is not None
        run = store.repository.autopilot.current(project_id)
        assert run.state == "taken_over" and run.policy.executor_binding.contract_version == "plotloom.codex-exec.v7"
    assert upgrade_project(home, SpecialistRegistry(storage.application.root))["changed"] is False


def test_serial_folder_upgrade_failure_rolls_back_exact_layout_rows_and_payloads(tmp_path):
    storage, project_id, home = _valued_serial_fixture(tmp_path)
    before_bytes = retained_bytes(home)
    with sqlite3.connect(home / "project.sqlite3") as connection:
        before_schema = schema_objects(connection)
        before_rows = logical_inventory(connection, prior_schema_objects("serial_exec"))
    def crash(_connection):
        raise RuntimeError("serial-layout DDL failure")
    with pytest.raises(RuntimeError, match="serial-layout DDL failure"):
        upgrade_project(home, SpecialistRegistry(storage.application.root), after_ddl=crash)
    assert retained_bytes(home) == before_bytes
    with sqlite3.connect(home / "project.sqlite3") as connection:
        assert schema_objects(connection) == before_schema
        assert logical_inventory(connection, prior_schema_objects("serial_exec")) == before_rows


def test_serial_sql_transition_preserves_exact_terminal_attempt_receipt_and_native_fixture_files(tmp_path, monkeypatch):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch)
    try:
        assert service.acquire_controller()
        for _ in range(5):
            service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, "outline")
            assert attempt.state == "completed" and receipt is not None
            home = store.home
        service.control(view.project_id, RunControlRequest(expected_revision=current.revision, action="pause"))
        service.close()
        _serial_layout(home)
        before_bytes = retained_bytes(home)
        with sqlite3.connect(home / "project.sqlite3") as connection:
            exact_before = connection.execute("SELECT snapshot,receipt FROM v2_autopilot_exec_attempts").fetchall()
        upgrade_project(home, registry)
        assert retained_bytes(home) == before_bytes
        with sqlite3.connect(home / "project.sqlite3") as connection:
            assert connection.execute("SELECT snapshot,receipt FROM v2_autopilot_exec_attempts").fetchall() == exact_before
        with closing(storage.projects.open(view.project_id)) as store:
            after_attempt, after_receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, "outline")
            assert after_attempt == attempt and after_receipt == receipt
            assert store.source_outline_state().accepted_outline is not None
        assert len(calls) == 1
    finally:
        service.close()


@pytest.mark.parametrize("state", ["running", "outcome_unknown"])
def test_serial_folder_upgrade_refuses_unsettled_attempt_without_rebinding_or_replay(tmp_path, monkeypatch, state):
    storage, registry, service, view, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        assert service.acquire_controller()
        for _ in range(3):
            service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
        service.control(view.project_id, RunControlRequest(expected_revision=current.revision, action="pause"))
        with closing(storage.projects.open(view.project_id)) as store:
            if state == "outcome_unknown":
                attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, "outline")
                with store.repository.autopilot_command(CommandAuthority(view.id, service.claim, OperationScope.EVIDENCE)):
                    store.repository.autopilot.update_exec_attempt(attempt.attempt_id, state="outcome_unknown")
            home = store.home
        service.close()
        _serial_layout(home)
        with sqlite3.connect(home / "project.sqlite3") as connection:
            before = logical_inventory(connection, prior_schema_objects("serial_exec"))
        with pytest.raises(ProjectBusyError, match="unresolved Codex Exec"):
            upgrade_project(home, registry)
        with sqlite3.connect(home / "project.sqlite3") as connection:
            assert classify_layout(connection) == "serial_exec"
            assert logical_inventory(connection, prior_schema_objects("serial_exec")) == before
        assert len(calls) == 1
    finally:
        service.close()


def test_serial_closed_folder_restore_records_actual_source_layout_and_keeps_stopped_authority(tmp_path):
    storage, project_id, home = _valued_serial_fixture(tmp_path / "source", closed=True)
    before_bytes = retained_bytes(home)
    destination = ProjectFolderStorage(outputs_root=tmp_path / "destination", application_data_root=tmp_path / "application")
    restored = destination.recovery.restore(home, upgrade_previous=True)
    assert retained_bytes(restored) == before_bytes
    import json
    transition = json.loads((restored / "schema-transition.json").read_text())
    assert transition["priorLayoutHash"] == SERIAL_EXEC_LAYOUT_HASH
    with closing(destination.projects.inspect(project_id)) as store:
        assert store.source_outline_state().accepted_outline is not None
        run = store.repository.autopilot.current(project_id)
        assert run.policy.executor_binding.contract_version == "plotloom.codex-exec.v7"
        assert run.state == "taken_over"
        assert store.repository.operational_state()[0] == "closed"


def test_serial_portable_snapshot_upgrade_preserves_source_and_restored_run_quarantine(tmp_path):
    from hashlib import sha256
    from pathlib import Path

    from plotloom.exceptions import InvalidTransitionError
    from plotloom.project_storage.snapshot_contract import (
        ProjectSnapshotManifest,
        SnapshotFile,
    )

    storage, project_id, _home = _valued_serial_fixture(tmp_path / "source", convert_serial=False)
    snapshot = storage.recovery.create_snapshot(project_id)
    root = Path(snapshot.location)
    # Construct a disposable old-layout snapshot representation, then freeze
    # its declared bytes. No retained native or historical evidence is edited.
    _serial_layout(root)
    manifest_path = root / "snapshot.json"
    manifest = ProjectSnapshotManifest.model_validate_json(manifest_path.read_bytes())
    declared = [SnapshotFile(relative_path=item.relative_path,
        content_hash=sha256((root / item.relative_path).read_bytes()).hexdigest(),
        size_bytes=(root / item.relative_path).stat().st_size) for item in manifest.files]
    manifest = manifest.model_copy(update={"files": declared,
        "database_hash": next(item.content_hash for item in declared if item.relative_path == "project.sqlite3")})
    manifest_path.write_text(manifest.model_dump_json(by_alias=True))
    frozen = {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*") if path.is_file()}
    destination = ProjectFolderStorage(outputs_root=tmp_path / "destination", application_data_root=tmp_path / "application")
    restored = destination.recovery.restore(root, upgrade_previous=True)
    assert {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*") if path.is_file()} == frozen
    import json
    assert json.loads((restored / "schema-transition.json").read_text())["priorLayoutHash"] == SERIAL_EXEC_LAYOUT_HASH
    destination.recovery.acknowledge_recovery(project_id)
    with closing(destination.projects.open(project_id)) as store:
        assert store.source_outline_state().accepted_outline is not None
        assert not store.repository.autopilot.controller_execution_eligible(project_id)
        with pytest.raises(InvalidTransitionError, match="portable"):
            store.repository.autopilot.claim(project_id, "restored-controller")
