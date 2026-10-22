"""Bounded scenarios for the actual arm/pair control functions; never spawn work."""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import importlib.util
import json
import time
from pathlib import Path
from types import SimpleNamespace as Namespace

from parking_observation import CleanupResult
from admission_observation import ObservationError
from observation_fixtures import receipt_bound_sessions

WORK = Path(__file__).resolve().parents[1] / "scripts/autopilot/handoff"
SOURCE = "a" * 40  # Explicit synthetic source label; no native qualification.


def load_control(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def successful_arm_path(tmp_path, monkeypatch, failure):
    arm = load_control("successful_arm_control", WORK / "run_arm.py")
    owned = tmp_path / "arm"
    owned.mkdir()
    monkeypatch.setattr(arm, "WORK", owned)
    (owned / "arm-start.json").write_text(json.dumps({"monotonicNs": time.monotonic_ns()}))
    observed = Namespace(material=[], verified=[], final=[], completeness=0, steps=[], halts=[])
    def complete():
        observed.completeness += 1
        if failure == "rpc" and observed.completeness == 2:
            raise ObservationError("synthetic final RPC uncertainty")
    capture = Namespace(freeze_prepared=lambda *_args: None, require_complete=complete,
        summary=lambda: {"recordsEmitted": 1, "recordsFinished": 1})
    service = Namespace(step=observed.steps.append, acquire_controller=lambda: True)
    runtime = Namespace(app=Namespace(state=Namespace(project_folder_storage=Namespace(
        projects=Namespace(discover=lambda: [])))), bridge=Namespace(exec_supervisor=lambda: Namespace(halt_qualification=observed.halts.append)))
    @contextmanager
    def controlled(_plan):
        yield runtime, None, service, capture
    @contextmanager
    def watcher(*_args):
        yield Namespace(failure=None, gates={"syntheticControlOnly": True})
    def create(_client, role, _plan, projects, *_setup):
        projects[role] = role
    def attempt(key, domain):
        return {"attemptId": key, "jobId": key, "operationKey": key, "domain": domain,
            "state": "completed", "hostState": "completed", "processId": 123,
            "terminalResult": "success"}
    primary = {"attempts": [attempt("art", "text"), attempt("image-a", "image"), attempt("image-b", "image")],
        "run": {"state": "awaiting_review", "revision": 1, "phase": "complete",
            "checkpoints": [], "frames": [], "bundleHash": "b" * 64}}
    sidecar = {"attempts": [attempt("outline", "text")], "run": dict(primary["run"], state="paused")}
    def snapshot(actual_runtime, project, actual_capture):
        assert actual_runtime is runtime and actual_capture is capture
        if arm.SETTLING:
            observed.final.append(project)
            if failure == project:
                raise RuntimeError("synthetic mandatory final snapshot loss")
        return primary if project == "primary" else sidecar
    complete_cleanup = CleanupResult("complete_success", True, True, True)
    def cleanup(*_args, material_qualified):
        observed.material.append(material_qualified)
        assert material_qualified is True  # The real runner already reached passed=True.
        return complete_cleanup, {"classification": asdict(complete_cleanup), "attemptCount": 4,
            "groupObservations": {}}
    monkeypatch.setattr(arm, "controlled", controlled)
    monkeypatch.setattr(arm, "Observer", watcher)
    monkeypatch.setattr(arm, "create", create)
    monkeypatch.setattr(arm, "snapshot", snapshot)
    monkeypatch.setattr(arm, "verify_completed", lambda *_args: observed.verified.append(True))
    monkeypatch.setattr(arm, "pause", lambda *_args: None)
    monkeypatch.setattr(arm, "cleanup_snapshot", cleanup)
    monkeypatch.setattr("preservation.require_preserved_inputs", lambda: {})
    plan = {"sourceRevision": SOURCE, "profileHash": "3" * 64, "arm": "serial",
        "maxSteps": 1, "maxWallSeconds": 60, "maxSettlementSeconds": 10,
        "primaryEnvelope": {"text": 8, "image": 32}, "sidecarEnvelope": {"text": 1, "image": 0}, "priorEvidence": {}}
    (owned / "plan.json").write_text(json.dumps(plan))
    return arm, plan, observed


def successful_pair_path(tmp_path, monkeypatch, failure):
    pair = load_control("successful_pair_control", WORK / "run_pair.py")
    import campaign_guard
    owned = tmp_path / "pair"
    owned.mkdir()
    monkeypatch.setattr(pair, "WORK", owned)
    observed = Namespace(gates=[], children=[])
    sealed = {"sourceRevision": SOURCE, "order": ["serial", "parallel"]}
    (owned / "plan.json").write_text(json.dumps(sealed))
    for arm in sealed["order"]:
        target = owned / arm
        target.mkdir()
        rpc = target / "rpc_observations.jsonl"
        rpc.write_text("{}\n")
        result = {"passed": True, "quiescent": True, "sourceRevision": SOURCE,
            "cleanupOutcome": "complete_success", "completeSuccess": True,
            "zeroLiveWork": True, "allWorkQuiescent": True,
            "rpcObservation": {"recordsEmitted": 1, "recordsFinished": 1,
                "discardedRecords": 0, "activeRpcCount": 0, "halted": False,
                "persistenceFailure": None, "frozenJobs": 1,
                "recordsSha256": hashlib.sha256(rpc.read_bytes()).hexdigest()}}
        if arm=='parallel':
            import campaign_guard
            import session_measurements
            sessions=receipt_bound_sessions()
            monkeypatch.setattr(session_measurements,'measure_sessions',lambda _root:sessions)
            gates=dict(cross=1,images=2,texts=3)
            proof=campaign_guard.require_arm_overlap(gates,sessions)
            (target/'overlap.json').write_text(json.dumps(proof))
            result.update(orderedGates=gates,overlapQualified=True,
                overlapSha256=hashlib.sha256((target/'overlap.json').read_bytes()).hexdigest())
        if arm == "parallel" and failure == "rpc":
            result["rpcObservation"]["activeRpcCount"] = 1
        if arm == "parallel" and failure == "parked":
            result.update(cleanupOutcome="safe_parked", completeSuccess=False, allWorkQuiescent=False)
        (target / "result.json").write_text(json.dumps(result))
    original_gate = campaign_guard.require_successful_current_arm
    def gate(path, *, expected_source):
        observed.gates.append(path.name)
        return original_gate(path, expected_source=expected_source)
    monkeypatch.setattr(pair, "require_successful_current_arm", gate)
    monkeypatch.setattr(campaign_guard, "require_zero_live_original_work", lambda *_a, **_k: {"attempts": 1})
    class Child:
        def __init__(self, argv, **_kwargs):
            observed.children.append(argv[argv.index("--arm") + 1])
            self.pid = 123
        def wait(self):
            return 0
        def poll(self):
            return 0
    monkeypatch.setattr(pair.subprocess, "Popen", Child)
    return pair, sealed, observed
