"""Retained creative bytes, explicit prior restore and portable non-resumption."""
from contextlib import closing
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.autopilot_contracts import OperationScope
from plotloom.codex_exec_contracts import CodexExecProfile
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.exceptions import InvalidTransitionError
from plotloom.project_storage import (
    ProjectBusyError,
    ProjectFolderStorage,
    ProjectStorageConfinementError,
    ProjectStorageCorruptionError,
)
from plotloom.project_storage.creative_evidence_inventory import (
    _retained_codex_request_projection,
)
from plotloom.project_storage.snapshot_contract import (
    ProjectSnapshotManifest,
    SnapshotFile,
)
from plotloom.source_outline_contracts import OutlineAcceptRequest
from tests.autopilot_controller_fixtures import UPSTREAM_PIN
from tests.autopilot_fixtures import authority, make_prior_layout, start_run
from tests.codex_exec_fixtures import PROFILE
from tests.source_outline_fixtures import _deliver, _material, _request


def storage_at(root):
    return ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")


def accepted_outline(storage):
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = _request(store.manifest.project_id, source)
        store.prepare_outline_candidate(request)
        store.admit_outline_delivery(_deliver(store, request))
        store.accept_outline_candidate(OutlineAcceptRequest(job_id=request.job_id, expected_source_revision=1, expected_outline_revision=0))
        return store.manifest.project_id, store.home


def test_snapshot_and_closed_folder_restore_preserve_all_retained_creative_files(tmp_path):
    storage = storage_at(tmp_path / "source")
    project_id, home = accepted_outline(storage)
    original = {path.relative_to(home).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in (home / "outputs" / "creative-handoff").rglob("*") if path.is_file()}
    assert sum(not name.endswith(".lock") for name in original) == 8
    snapshot = storage.recovery.create_snapshot(project_id)
    assert original.items() <= {(item.relative_path, item.content_hash) for item in snapshot.manifest.files}
    restored = storage_at(tmp_path / "snapshot-restored").recovery.restore(Path(snapshot.location))
    for name, digest in original.items():
        assert sha256((restored / name).read_bytes()).hexdigest() == digest
    storage.projects.close_project(project_id)
    restored_folder = storage_at(tmp_path / "folder-restored").recovery.restore(home)
    for name, digest in original.items():
        assert sha256((restored_folder / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("mutation", ["foreign", "secret", "ancestor_symlink", "missing_job", "missing_tree", "missing_package", "missing_request", "missing_input", "missing_assignment", "missing_template"])
def test_creative_evidence_inventory_remains_confined_and_secret_free(tmp_path, mutation):
    storage = storage_at(tmp_path / "source")
    project_id, home = accepted_outline(storage)
    jobs = home / "outputs" / "creative-handoff" / "jobs"
    job = next(jobs.iterdir())
    if mutation == "foreign":
        (job / "delivery" / "unowned.txt").write_text("foreign")
    elif mutation == "secret":
        (job / "delivery" / "report.html").write_text("<!doctype html><html>Bearer sk-abcdefghijklmnopqrstuvwxyz123456</html>")
    elif mutation == "ancestor_symlink":
        # A symlink ancestor must be refused before reading files outside root.
        import shutil
        moved = tmp_path / "outside"
        shutil.move(home / "outputs", moved)
        (home / "outputs").symlink_to(moved, target_is_directory=True)
    elif mutation in {"missing_tree", "missing_job", "missing_package"}:
        import shutil
        shutil.rmtree(job if mutation == "missing_job" else job / "package" if mutation == "missing_package" else home / "outputs")
    else:
        missing = {"missing_request": job / "package/request.json", "missing_assignment": job / "package/COPY_ASSIGNMENT.txt",
            "missing_template": job / "package/completion-manifest.example.json", "missing_input": next((job / "package/inputs").iterdir())}
        missing[mutation].unlink()
    with pytest.raises((ProjectStorageCorruptionError, ProjectStorageConfinementError)):
        storage.recovery.create_snapshot(project_id)


def test_retained_v4_codex_package_inventory_uses_revisionless_v2_shape(tmp_path):
    value = PROFILE.model_dump(mode="json", by_alias=True)
    value.update(
        contractVersion="plotloom.codex-exec.v4",
        maxProcesses=1, maxTextProcesses=None, maxImageProcesses=None, maxQueuedJobs=None,
        permissionProfile="plotloom_autopilot_delivery_v2",
        textValidatorRuntimeProfile=None,
    )
    profile = CodexExecProfile.model_validate(value)
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        source = _material()
        request = _request(str(store.manifest.project_id), source)
        projection = _retained_codex_request_projection(
            request,
            UPSTREAM_PIN,
            profile,
            CreativeHandoffExchange(tmp_path / "creative-handoff"),
        )

    assert projection["packageVersion"] == 2
    assert projection["executorBackend"] == "codex_exec"
    assert projection["executionPin"]["upstreamRevision"] == UPSTREAM_PIN["upstreamRevision"]
    assert "plotloomCodeRevision" not in projection


def test_portable_autopilot_cannot_resume_after_acknowledgement(tmp_path):
    storage = storage_at(tmp_path / "source")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        run = start_run(store)
        project_id = store.manifest.project_id
        current = store.repository.autopilot.current(project_id)
        store.repository.autopilot.control(project_id, expected_revision=current.revision, action="pause")
    snapshot = storage.recovery.create_snapshot(project_id)
    restored = storage_at(tmp_path / "restored")
    restored.recovery.restore(Path(snapshot.location))
    restored.recovery.acknowledge_recovery(project_id)
    with closing(restored.projects.open(project_id)) as store:
        current = store.repository.autopilot.current(project_id)
        with pytest.raises(InvalidTransitionError, match="portable"):
            store.repository.autopilot.control(project_id, expected_revision=current.revision, action="resume")
        with pytest.raises(InvalidTransitionError, match="portable"):
            store.repository.autopilot.claim(project_id, "destination")
        with pytest.raises(InvalidTransitionError, match="portable"):
            with store.repository.autopilot_command(authority(run, OperationScope.TEXT)):
                pytest.fail("portable command admitted")


def test_active_autopilot_blocks_snapshot_until_safe_pause(tmp_path):
    storage = storage_at(tmp_path)
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        start_run(store)
        project_id = store.manifest.project_id
    with pytest.raises(ProjectBusyError, match="autopilot"):
        storage.recovery.create_snapshot(project_id)


def test_explicit_previous_snapshot_restore_upgrades_only_destination(tmp_path):
    storage = storage_at(tmp_path / "source")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id = store.manifest.project_id
    snapshot = storage.recovery.create_snapshot(project_id)
    root = Path(snapshot.location)
    # Build the exact immediately-prior snapshot representation on disposable
    # bytes, then freeze its declared hashes and recovery control.
    make_prior_layout(root)
    manifest_path = root / "snapshot.json"
    manifest = ProjectSnapshotManifest.model_validate_json(manifest_path.read_bytes())
    files = []
    for item in manifest.files:
        content = (root / item.relative_path).read_bytes()
        files.append(SnapshotFile(relative_path=item.relative_path, content_hash=sha256(content).hexdigest(), size_bytes=len(content)))
    manifest = manifest.model_copy(update={"files": files, "database_hash": next(item.content_hash for item in files if item.relative_path == "project.sqlite3")})
    manifest_path.write_text(manifest.model_dump_json(by_alias=True))
    frozen = {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest() for path in root.rglob("*") if path.is_file()}
    restored = storage_at(tmp_path / "restored")
    with pytest.raises(ProjectStorageCorruptionError, match="unsupported"):
        restored.recovery.restore(root)
    destination = restored.recovery.restore(root, upgrade_previous=True)
    assert (destination / "schema-transition.json").is_file()
    assert sha256((destination / "project.sqlite3").read_bytes()).hexdigest() != frozen["project.sqlite3"]
    assert {path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest() for path in root.rglob("*") if path.is_file()} == frozen
    with closing(restored.projects.open(project_id)) as store:
        assert store.project().brief == FIXED_CHINESE_BRIEF


def test_prior_snapshot_package_omission_is_explicit_and_not_a_current_snapshot_bypass(tmp_path):
    import json
    import shutil
    storage = storage_at(tmp_path / "source")
    project_id, _home = accepted_outline(storage)
    snapshot = storage.recovery.create_snapshot(project_id)
    root = Path(snapshot.location)
    make_prior_layout(root)
    shutil.rmtree(root / "outputs")
    manifest = snapshot.manifest
    files = []
    for item in manifest.files:
        if item.relative_path.startswith("outputs/"):
            continue
        content = (root / item.relative_path).read_bytes()
        files.append(SnapshotFile(relative_path=item.relative_path, content_hash=sha256(content).hexdigest(), size_bytes=len(content)))
    manifest = manifest.model_copy(update={"files": files, "database_hash": next(item.content_hash for item in files if item.relative_path == "project.sqlite3")})
    (root / "snapshot.json").write_text(manifest.model_dump_json(by_alias=True))
    restored = storage_at(tmp_path / "restored")
    destination = restored.recovery.restore(root, upgrade_previous=True)
    transition = json.loads((destination / "schema-transition.json").read_text())
    assert len(transition["omittedCreativeManifests"]) == 1
    restored.recovery.acknowledge_recovery(project_id)
    retained = restored.recovery.create_snapshot(project_id)
    assert any(item.relative_path == "schema-transition.json" for item in retained.manifest.files)


def test_completed_branch_package_restores_original_location_sensitive_bytes(tmp_path):
    from tests.creative_delivery_fixtures import _deliver_stage
    from tests.test_creator_branch_suggestions import proposal
    storage = storage_at(tmp_path / "source")
    project_id, home = accepted_outline(storage)
    with closing(storage.projects.open(project_id)) as store:
        store.prepare_branch_candidate()
        job = store.branch_state().candidate.job_id
        request = store.branch_candidate_request(job)
        store.admit_branch_delivery(_deliver_stage(store, request, "branches.json", proposal(request.source["topology"]), "portable-branch"))
    original_package = home / "outputs/creative-handoff/jobs" / job / "package"
    instructions = (original_package / "COPY_ASSIGNMENT.txt").read_bytes()
    assert str(original_package).encode() in instructions
    frozen = {path.relative_to(home).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in original_package.rglob("*") if path.is_file()}
    snapshot = storage.recovery.create_snapshot(project_id)
    restored = storage_at(tmp_path / "destination")
    destination = restored.recovery.restore(Path(snapshot.location))
    for name, digest in frozen.items():
        assert sha256((destination / name).read_bytes()).hexdigest() == digest
    assert (destination / "outputs/creative-handoff/jobs" / job / "package/COPY_ASSIGNMENT.txt").read_bytes() == instructions
    with closing(restored.projects.open(project_id)) as store:
        assert store.branch_state().candidate.status == "ready"
