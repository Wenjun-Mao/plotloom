"""Physical allocation, frozen run and known claim/resume state checks."""
import json
import os
import stat
from pathlib import Path

from handoff_files import canonical, digest, parse, read_owned, require
from handoff_source import require_committed_profile_sources, source_identity

from plotloom.autopilot_contracts import OperationScope
from plotloom.autopilot_launch import assert_frozen_execution
from plotloom.autopilot_text_controller import AutopilotTextController
from plotloom.codex_exec_python_environment import inspect_checked_python_environment
from plotloom.persistence.project.autopilot_closure import material_closure


def path_identity(path, *, file_hash=False):
    path = Path(path).absolute()
    require(path.resolve(strict=True) == path and not path.is_symlink(), "physical allocation path required")
    info = path.lstat()
    require(info.st_uid == os.getuid() and not info.st_mode & 0o022, "unsafe allocation owner/mode")
    value = {"path": str(path), "device": info.st_dev, "inode": info.st_ino,
        "uid": info.st_uid, "mode": stat.S_IMODE(info.st_mode)}
    if file_hash:
        value.update(sha256=digest(read_owned(path)), size=info.st_size)
    return value


def assert_path(expected, *, file_hash=False):
    actual = path_identity(expected.path, file_hash=file_hash)
    require(actual == expected.model_dump(mode="json", by_alias=False), "allocation physical/file identity drift")


def assert_allocation_files(allocation, qa):
    ns = allocation.namespace
    for item in (allocation.data_root, allocation.bundle_root, allocation.phase_root,
            allocation.project_home, allocation.project_database, allocation.application_database,
            ns.application_root, ns.outputs_root, ns.private_root, ns.source_root, ns.database):
        assert_path(item)
    for item in (allocation.owner_marker, allocation.project_manifest):
        assert_path(item, file_hash=True)
    owner = parse(read_owned(Path(allocation.owner_marker.path)))
    require(owner == {"version": 1, "purpose": "paid_outline_once", "allocationId": str(allocation.allocation_id),
        "nonce": allocation.nonce}, "disposable allocation owner marker differs")
    require({p.name for p in Path(allocation.data_root.path).iterdir()} == {"owner.json", "application", "outputs", "private"},
        "disposable data root contains foreign state")
    require({p.name for p in Path(ns.outputs_root.path).iterdir()} == {Path(allocation.project_home.path).name},
        "disposable outputs contain foreign projects or paths")
    require(tuple(sorted(p.name for p in Path(ns.application_root.path).iterdir())) == allocation.application_entries,
        "disposable application inventory differs")
    raw = read_owned(Path(ns.private_root.path) / "namespace-binding.json")
    require(digest(raw) == allocation.namespace_binding_sha256
        and canonical(parse(raw)) == canonical(ns.model_dump(mode="json", by_alias=True)), "namespace allocation binding differs")
    qa_raw = read_owned(Path(allocation.bundle_root.path) / "qa-interpreter.json")
    require(digest(qa_raw) == allocation.validator_runtime.qa_pin_sha256 and json.loads(qa_raw) == qa
        and qa["projectRoot"] == ns.source_root.path, "QA allocation role/root binding differs")
    source = source_identity(Path(ns.source_root.path), require_committed=True)
    require(source["revision"] == allocation.source.revision and source["tree"] == allocation.source.tree
        and source["closureSha256"] == allocation.source.workflow_closure_sha256
        and digest(canonical(source)) == allocation.source.bundle_source_identity_sha256, "paid source identity drift")
    require_committed_profile_sources(Path(ns.source_root.path))
    runtime = inspect_checked_python_environment(Path(ns.source_root.path))
    require((str(runtime.root), str(runtime.interpreter), runtime.identity_hash) == (
        allocation.validator_runtime.root, allocation.validator_runtime.interpreter, allocation.validator_runtime.identity_hash),
        "checked validator runtime identity drift")
    require(str(runtime.root) != qa["prefix"] and str(runtime.interpreter) != qa["entrypoint"],
        "QA interpreter cannot substitute for checked validator runtime")


def checkpoint_for(view):
    require({item["operationKey"] for item in view.checkpoints} == {"source", "outline"}, "paid run contains continuation stages")
    source = next(item for item in view.checkpoints if item["operationKey"] == "source")
    outline = next(item for item in view.checkpoints if item["operationKey"] == "outline")
    require(source["state"] == "adopted" and outline["state"] in {"prepared", "sent", "outcome_unknown"},
        "paid run crossed its prepared/receipt-only stage boundary")
    return outline


def assert_paused_owner(store, session, allocation, registry):
    attempt = allocation.namespace.attempt
    row = store.repository.autopilot.row(session, str(attempt.project_id))
    edges = allocation.claim_edges
    require(row is not None and row.id == str(attempt.run_id) and row.claim == edges.paused_claim
        and row.revision == edges.paused_revision and row.state == "paused", "paused run/claim/revision drift")
    project = store.project()
    from plotloom.persistence.codec import stable_hash
    require(row.policy_hash == allocation.policy_hash and row.policy_hash == stable_hash(row.policy)
        and row.brief_hash == allocation.brief_hash and row.brief_hash == stable_hash(project.brief)
        and row.brief_revision == project.revision == allocation.brief_revision
        and row.lifecycle_revision == project.lifecycle_revision == allocation.lifecycle_revision
        and row.expected_closure == allocation.material_closure == material_closure(session, str(attempt.project_id)),
        "frozen policy/Brief/material currentness drift")
    view = store.repository.autopilot.current(str(attempt.project_id))
    assert_frozen_execution(store, registry, view.policy)
    checkpoint = checkpoint_for(view)
    require(checkpoint["state"] == "prepared" and checkpoint["revision"] == allocation.expected_checkpoint_revision,
        "paid checkpoint revision drift")
    retained = store.repository.autopilot.exec_attempt_for_operation(view.id, "outline")
    require(retained == attempt, "paid project reservation drift or already spent")
    return view


def claim_and_resume(store, allocation, registry):
    """One existing manual owner transaction; every self-owned increment is known."""
    edges, attempt = allocation.claim_edges, allocation.namespace.attempt
    with store.repository.manual_command() as session:
        assert_paused_owner(store, session, allocation, registry)
        claimed = store.repository.autopilot.claim(str(attempt.project_id), edges.receiver_claim)
        require(claimed.revision == edges.claimed_revision, "unexpected owned claim revision edge")
        resumed = store.repository.autopilot.control(str(attempt.project_id),
            expected_revision=edges.claimed_revision, action="resume")
        require(resumed.revision == edges.resumed_revision and resumed.state == "running",
            "unexpected owned resume revision edge")
    return resumed


def frozen_request(store, view, claim):
    with AutopilotTextController.command(store, view, claim, OperationScope.EVIDENCE):
        request = store.repository.creative_terminal.run_request(view.project_id, "outline",
            checkpoint_for(view)["evidence"]["jobId"])
    return request
