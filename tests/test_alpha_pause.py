"""Real SQLite/controller resume ordering; deterministic transport, no provider calls."""
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest

from plotloom import alpha_pause
from plotloom.alpha_campaign import publish_sample_outcome, write_private_json
from plotloom.alpha_pause import (QualificationResume, database_identity, pause_snapshot,
    publish_pause, recorded_duration, require_original_runtime, resume_paused_sample)
from plotloom.alpha_receipts import collect_native_evidence, installed_text_readback
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_service import AutopilotService
from plotloom.autopilot_text_prefix import AutopilotTextPrefix
from plotloom.project_storage import ProjectStorageCorruptionError
from tests.autopilot_controller_fixtures import environment


def sent_pause(tmp_path, monkeypatch):
    storage, registry, original, run, _ = environment(tmp_path, monkeypatch, auto_deliver=False, early_references=True)
    prefix = AutopilotTextPrefix(storage, registry)
    prefix.__enter__()
    host = registry._codex_exec_test_host
    for _ in range(8):
        view = prefix.step(run.project_id)
        if host.admissions:
            break
    assert host.admissions == 1
    view = prefix.service.control(run.project_id,
        RunControlRequest(action="pause", expected_revision=view.revision), expected_run_id=run.id)
    evidence = tmp_path / "evidence/story-01-repeat-01"
    evidence.mkdir(parents=True, mode=0o700)
    snapshot = {"commit": view.policy.code_revision, "profileHash": view.policy.executor_binding.profile_hash}
    with closing(storage.projects.open(run.project_id)) as store:
        receipt, bindings = collect_native_evidence(store, view, snapshot=snapshot,
            contract_hash="b" * 64, sample_id=evidence.name, duration_ms=125)
        identity = snapshot | {"contractHash": "b" * 64, "namespaceBinding": "controlled-fixture-not-native-proof", "databases": {
            "project": database_identity(store.database_path), "application": database_identity(storage.application.path)}}
    write_private_json(evidence / "runtime.json", identity)
    path, digest = publish_pause(evidence, receipt=receipt.model_dump(mode="json", by_alias=True),
        bindings=bindings, runtime_identity=identity, elapsed_ms=125)
    request = QualificationResume(project_id=run.project_id, run_id=run.id,
        revision=view.revision, snapshot_hash=digest)
    return storage, registry, original, prefix, host, run, evidence, path, request, identity, snapshot


def complete_original(storage, host):
    attempt = next(iter(host.statuses.values())).attempt
    with closing(storage.projects.open(str(attempt.project_id))) as store:
        host.complete(store, host.request(store, attempt), attempt)
    return attempt


def test_late_completion_reuses_pause_bytes_and_adopts_exact_attempt_without_duplicate(tmp_path, monkeypatch):
    storage, registry, original, prefix, host, run, evidence, path, request, identity, snapshot = sent_pause(tmp_path, monkeypatch)
    try:
        before = {p.name: p.read_bytes() for p in path.iterdir()}
        attempt = complete_original(storage, host)
        assert recorded_duration(evidence) == 125
        values, digest = pause_snapshot(path)
        _, reused = publish_pause(evidence, receipt=values["receipt.json"] | {"durationMilliseconds": 999},
            bindings=values["bindings.private.json"], runtime_identity=identity, elapsed_ms=999)
        assert reused == digest == request.snapshot_hash
        assert {p.name: p.read_bytes() for p in path.iterdir()} == before
        assert recorded_duration(evidence) == 125
        ordinary = AutopilotService(storage, registry)
        assert not ordinary.acquire_controller()
        resumed = resume_paused_sample(prefix, run.project_id, evidence, request, require_original_runtime(evidence))
        assert resumed.revision == request.revision + 1 and resumed.state == "running"
        assert host.admissions == 1
        view = prefix.step(run.project_id)
        assert next(c for c in view.checkpoints if c["operationKey"] == "outline")["state"] == "delivered"
        assert host.admissions == 1
        view = prefix.step(run.project_id)
        assert next(c for c in view.checkpoints if c["operationKey"] == "outline")["state"] == "adopted"
        with closing(storage.projects.open(run.project_id)) as reopened:
            bound, receipt = reopened.repository.autopilot.exec_attempt_evidence_for_operation(run.id, "outline")
            assert bound.attempt_id == attempt.attempt_id and bound.state == "completed" and receipt is not None
        assert host.admissions == 1
        # Re-observing an acknowledged intent never repeats the control CAS.
        def no_control(*_args, **_kwargs): pytest.fail("acknowledged intent repeated CAS")
        with monkeypatch.context() as repeat:
            repeat.setattr(prefix.service, "control", no_control)
            resume_paused_sample(prefix, run.project_id, evidence, request, identity)
        host.auto_deliver = True
        for _ in range(60):
            view = prefix.step(run.project_id)
            if any(c["operationKey"] == "installation" for c in view.checkpoints): break
        assert host.admissions == 8 and not host.image_calls
        with closing(storage.projects.open(run.project_id)) as store:
            final, _ = collect_native_evidence(store, view, snapshot=snapshot, contract_hash="b" * 64,
                sample_id=evidence.name, duration_ms=recorded_duration(evidence) + 75)
            assert final.status == "installed" and final.duration_milliseconds == 200
            assert sum(op.attempt_count for op in final.operations) == 8
            assert sum(op.first_pass for op in final.operations) == 8
            readback = installed_text_readback(store)
        with closing(storage.projects.open(run.project_id)) as reopened:
            assert installed_text_readback(reopened) == readback
        assert {p.name: p.read_bytes() for p in path.iterdir()} == before
        assert list((evidence / "resumptions" / str(request.revision) / "drains").glob("*.json"))
    finally:
        prefix.__exit__()
        original.close()


@pytest.mark.parametrize("window", ["before-intent", "after-intent", "before-ack", "after-ack"])
def test_resume_fault_windows_reopen_without_second_cas_or_early_dispatch(tmp_path, monkeypatch, window):
    storage, _, original, prefix, host, run, evidence, _, request, identity, _ = sent_pause(tmp_path, monkeypatch)
    try:
        complete_original(storage, host)
        cas = []
        control = prefix.service.control
        def counted(*args, **kwargs):
            cas.append(True)
            return control(*args, **kwargs)
        monkeypatch.setattr(prefix.service, "control", counted)
        write = alpha_pause.write_private_json
        def interrupt(path, value, **kwargs):
            matches = Path(path).name == ("intent.json" if "intent" in window else "ack.json")
            if matches and window.startswith("before"): raise OSError("simulated durable boundary interruption")
            write(path, value, **kwargs)
            if matches: raise OSError("simulated durable boundary interruption")
        with monkeypatch.context() as fault:
            fault.setattr(alpha_pause, "write_private_json", interrupt)
            with pytest.raises(OSError, match="boundary interruption"):
                resume_paused_sample(prefix, run.project_id, evidence, request, identity)
        assert host.admissions == 1
        prefix.__exit__()
        prefix = AutopilotTextPrefix(storage, prefix.service.registry)
        prefix.__enter__()
        control = prefix.service.control
        monkeypatch.setattr(prefix.service, "control", counted)
        resumed = resume_paused_sample(prefix, run.project_id, evidence, request, identity)
        assert resumed.state == "running" and resumed.revision == request.revision + 1
        assert len(cas) == 1 and host.admissions == 1
        prefix.step(run.project_id)
        assert host.admissions == 1
    finally:
        prefix.__exit__()
        original.close()


@pytest.mark.parametrize("mutation", ["project", "run", "revision", "hash", "runtime", "stale-cas", "policy", "unknown", "terminal", "alias", "unrecorded-resume"])
def test_resume_refuses_rebound_unknown_stale_or_terminal_without_dispatch(tmp_path, monkeypatch, mutation):
    storage, _, original, prefix, host, run, evidence, _, request, identity, _ = sent_pause(tmp_path, monkeypatch)
    try:
        if mutation == "project": request = request.model_copy(update={"project_id": uuid4()})
        if mutation == "run": request = request.model_copy(update={"run_id": uuid4()})
        if mutation == "revision": request = request.model_copy(update={"revision": request.revision + 1})
        if mutation == "hash": request = request.model_copy(update={"snapshot_hash": "f" * 64})
        if mutation == "runtime": identity = identity | {"namespaceBinding": "foreign"}
        if mutation in {"stale-cas", "policy"}:
            with closing(storage.projects.open(run.project_id)) as store:
                import sqlite3
                with sqlite3.connect(store.database_path) as connection:
                    if mutation == "stale-cas": connection.execute("UPDATE v2_autopilot_runs SET revision=revision+2")
                    else: connection.execute("UPDATE v2_autopilot_runs SET policy=json_set(policy, '$.textCorrectionLimit', 0)")
        if mutation == "unknown":
            from plotloom.codex_exec_contracts import transition_exec_attempt
            status = next(iter(host.statuses.values()))
            host.statuses[str(status.attempt.attempt_id)] = status.model_copy(update={
                "state": "outcome_unknown", "attempt": transition_exec_attempt(status.attempt, state="outcome_unknown")})
        if mutation == "terminal":
            publish_sample_outcome(evidence, receipt={"status": "blocked"}, bindings={})
        if mutation == "alias":
            foreign = tmp_path / "foreign"
            foreign.mkdir(mode=0o700)
            (evidence / "resumptions").symlink_to(foreign, target_is_directory=True)
        if mutation == "unrecorded-resume":
            prefix.service.control(run.project_id, RunControlRequest(action="resume", expected_revision=request.revision),
                expected_run_id=run.id)
        with pytest.raises(ProjectStorageCorruptionError if mutation == "policy" else ValueError):
            resume_paused_sample(prefix, run.project_id, evidence, request, identity)
        assert host.admissions == 1
        assert not (evidence / "resumptions" / str(request.revision) / "ack.json").exists()
        if mutation == "alias": assert not list(foreign.iterdir())
    finally:
        prefix.__exit__()
        original.close()


@pytest.mark.parametrize("mutation", ["missing", "replaced", "alias"])
def test_missing_or_replaced_databases_are_refused_before_runtime_initialization(tmp_path, mutation):
    database = tmp_path / "project.sqlite3"
    database.write_bytes(b"fixture identity, not a real database")
    identity = {"databases": {"project": database_identity(database)}}
    write_private_json(tmp_path / "runtime.json", identity)
    if mutation == "missing": database.unlink()
    if mutation == "replaced":
        old = tmp_path / "old.sqlite3"
        database.rename(old)
        database.write_bytes(old.read_bytes())
    if mutation == "alias":
        old = tmp_path / "old.sqlite3"
        database.rename(old)
        database.symlink_to(old)
    with pytest.raises(ValueError): require_original_runtime(tmp_path)
    if mutation == "missing": assert not database.exists()


@pytest.mark.parametrize("fail_after", [1, 2, 3])
def test_pause_publication_fault_retains_original_run_and_counts_slice_once(tmp_path, monkeypatch, fail_after):
    storage, _, original, prefix, host, run, evidence, path, request, identity, _ = sent_pause(tmp_path, monkeypatch)
    try:
        values, _ = pause_snapshot(path)
        # A second controlled pause record represents the next real revision;
        # exercise only its atomic evidence publication here, without dispatch.
        view = prefix.service.control(run.project_id,
            RunControlRequest(action="pause", expected_revision=request.revision), expected_run_id=run.id)
        with closing(storage.projects.open(run.project_id)) as store:
            receipt, bindings = collect_native_evidence(store, view,
                snapshot={"commit": view.policy.code_revision, "profileHash": view.policy.executor_binding.profile_hash},
                contract_hash="b" * 64, sample_id=evidence.name, duration_ms=200)
        from plotloom import alpha_campaign
        write = alpha_campaign.write_private_json
        calls = 0
        def fault(*args, **kwargs):
            nonlocal calls
            write(*args, **kwargs)
            calls += 1
            if calls == fail_after: raise OSError("interrupted pause set")
        with monkeypatch.context() as failure:
            failure.setattr(alpha_campaign, "write_private_json", fault)
            with pytest.raises(OSError, match="interrupted pause set"):
                publish_pause(evidence, receipt=receipt.model_dump(mode="json", by_alias=True),
                    bindings=bindings, runtime_identity=identity, elapsed_ms=75)
        assert not (path.parent / str(view.revision)).exists()
        assert recorded_duration(evidence) == 125 and host.admissions == 1
        # A process crash may leave uncommitted staging, which has no authority.
        staging = path.parent / ".outcome-staging-interrupted"
        staging.mkdir(mode=0o700)
        (staging / "partial").write_text("not a snapshot")
        publish_pause(evidence, receipt=receipt.model_dump(mode="json", by_alias=True),
            bindings=bindings, runtime_identity=identity, elapsed_ms=75)
        assert recorded_duration(evidence) == 200
        assert pause_snapshot(path)[0] == values
    finally:
        prefix.__exit__()
        original.close()


def test_packaged_resume_cli_passes_exact_bindings_without_importing_service(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from plotloom import alpha_acceptance
    (tmp_path / "services/creator_workbench").mkdir(parents=True)
    runtime = tmp_path / "services/creator_workbench/alpha_native_runtime.py"
    runtime.touch()
    monkeypatch.setattr(alpha_acceptance, "source_checkout_root", lambda: tmp_path)
    monkeypatch.setattr(alpha_acceptance, "load_campaign", lambda *_a, **_k: None)
    before_isolated = sys.modules.get("isolated")
    invocations = []
    def invoke(command, **kwargs):
        invocations.append((command, kwargs))
        assert sys.modules.get("isolated") is before_isolated
        return SimpleNamespace(returncode=3)
    monkeypatch.setattr(alpha_acceptance.subprocess, "run", invoke)
    project, run = str(uuid4()), str(uuid4())
    args = ["resume", "--campaign", str(tmp_path / "durable"), "--sample", "story-01-repeat-01",
        "--project", project, "--run", run, "--revision", "7", "--pause-hash", "a" * 64]
    assert alpha_acceptance.main(args) == 3
    command, kwargs = invocations[0]
    assert command == [sys.executable, str(runtime), "--campaign", str(tmp_path / "durable"),
        "--sample", "story-01-repeat-01", "--resume-project", project, "--resume-run", run,
        "--resume-revision", "7", "--pause-hash", "a" * 64]
    assert kwargs == {"cwd": tmp_path, "check": False}
    assert alpha_acceptance.main(args[:-1] + ["invalid"]) == 2
    assert len(invocations) == 1


def test_user_pause_cannot_publish_or_replace_terminal_outcome(tmp_path):
    tmp_path.chmod(0o700)
    with pytest.raises(ValueError, match="separate immutable pause"):
        publish_sample_outcome(tmp_path, receipt={"status": "incomplete"}, bindings={"run": {"state": "paused"}})
    assert not (tmp_path / "outcome").exists()
    publish_sample_outcome(tmp_path, receipt={"status": "blocked"}, bindings={"failure": "retained"})
    original = (tmp_path / "outcome/receipt.json").read_bytes()
    with pytest.raises(ValueError, match="bytes differ"):
        publish_sample_outcome(tmp_path, receipt={"status": "installed"}, bindings={"failure": "retained"})
    assert (tmp_path / "outcome/receipt.json").read_bytes() == original


@pytest.mark.parametrize("mutation", ["sample", "elapsed", "revision"])
def test_pause_history_rejects_rebound_or_double_counted_slices(tmp_path, monkeypatch, mutation):
    _, _, original, prefix, host, _, evidence, path, _, _, _ = sent_pause(tmp_path, monkeypatch)
    try:
        values, _ = pause_snapshot(path)
        if mutation == "sample":
            receipt = values["receipt.json"] | {"sampleId": "story-02-repeat-01"}
            write_private_json(path / "receipt.json", receipt, replace=True)
        if mutation == "elapsed":
            metadata = values["pause.json"] | {"elapsedMilliseconds": 250}
            write_private_json(path / "pause.json", metadata, replace=True)
        if mutation == "revision": path.rename(path.with_name(str(int(path.name) + 1)))
        with pytest.raises(ValueError, match="history"):
            recorded_duration(evidence)
        assert host.admissions == 1 and not host.image_calls
    finally:
        prefix.__exit__()
        original.close()
