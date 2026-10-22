"""One complete native arm; shared author inputs, capacities frozen by plan."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from contextlib import ExitStack, closing, contextmanager
from datetime import UTC, datetime

from pair_context import CONTROLS, current
WORK = current().work
ROOT = current().source
from fastapi.testclient import TestClient
from isolated import RuntimeConfig, compose
from canary_evidence import snapshot, current_inventory, prepared_package_snapshot
from campaign_observation import CampaignObservation
from campaign_cleanup import cleanup_snapshot
from parking_observation import CleanupResult
from observe import Observer
from plotloom.image_commands import IMAGE_METHODS
from plotloom.codex_exec_contracts import assert_receipt_matches_attempt

LOCK = threading.Lock()
SEEN = set()
STOP_REQUESTED = False
SETTLING = False


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value, *, exclusive=False):
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def emit(event, **facts):
    with LOCK:
        row = {"event": event, "utc": datetime.now(UTC).isoformat(), "monotonicNs": time.monotonic_ns(), **facts}
        with (WORK / "timeline.jsonl").open("ab") as stream:
            stream.write((json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode())
            stream.flush()


def preflight():
    from pair_preflight import preflight_arm
    return preflight_arm()


def observe(runtime, project, role, plan, capture):
    view = snapshot(runtime, project, capture)
    attempts = view["attempts"]
    limits = plan["primaryEnvelope" if role == "primary" else "sidecarEnvelope"]
    if any(sum(item["domain"] == domain for item in attempts) > limits[domain] for domain in ("text", "image")):
        raise RuntimeError("functional attempt count exceeded its frozen envelope")
    if len({item["jobId"] for item in attempts}) != len(attempts):
        raise RuntimeError("a job acquired a second attempt")
    for item in attempts:
        identity = item["attemptId"]
        if identity in SEEN:
            continue
        SEEN.add(identity)
        emit("attempt_observed", role=role, attempt=item)
    write(WORK / f"latest_{role}.json", view)
    return view


def freeze_prepared(runtime, project, view, role, capture):
    capture.freeze_prepared(project, view, role)


def create(client, role, plan, projects, runtime, service):
    emit("project_create_requested", role=role)
    response = client.post("/api/v2/projects", json={"brief": plan["brief"], "initialStages": []},
                           headers={"Idempotency-Key": plan["projectIdempotency"][role]})
    if response.status_code != 201:
        raise RuntimeError(f"fresh {role} project creation returned {response.status_code}")
    project = response.json()["id"]
    projects[role] = project
    # Persist identity before start, so a refused/uncertain response never causes recreation.
    write(WORK / f"identity_{role}.json", {"projectId": project, "role": role}, exclusive=True)
    emit("run_start_requested", role=role, projectId=project)
    start = client.post(f"/api/v2/projects/{project}/autopilot/start", json=plan["launchRequest"])
    if start.status_code != 201:
        raise RuntimeError(f"fresh {role} launch returned {start.status_code}")
    run = start.json()
    if run["policy"]["executorBinding"] != plan["profile"] or run["policy"]["earlyReferenceLimit"] != 4:
        raise RuntimeError("launch did not freeze the reviewed executor/early-reference policy")
    duplicate = client.post(f"/api/v2/projects/{project}/autopilot/start", json=plan["launchRequest"])
    if duplicate.status_code != 201 or duplicate.json()["id"] != run["id"] or duplicate.json()["policy"] != run["policy"]:
        raise RuntimeError("duplicate start replaced the original frozen run")
    emit("run_started", role=role, projectId=project, runId=run["id"], policy=run["policy"])
    from pair_runtime import register_project
    register_project(runtime,project,role,service.claim)
    return project


def pause(client, project, reason):
    current = client.get(f"/api/v2/projects/{project}/autopilot").json()
    if current["state"] in {"running", "waiting", "blocked"}:
        result = client.post(f"/api/v2/projects/{project}/autopilot/control", json={"expectedRevision": current["revision"], "action": "pause"})
        if result.status_code != 200:
            raise RuntimeError("safe pause refused; retained original run requires inspection")
        emit("run_paused", projectId=project, reason=reason)


def assert_health(view):
    run = view["run"]
    if run["state"] not in {"running", "waiting", "paused", "awaiting_review"}:
        raise RuntimeError(f"unexpected run state {run['state']}: {run.get('blocker')}")
    if run.get("blocker") and run["blocker"]["code"] != "codex_exec_capacity_deferred":
        raise RuntimeError(f"controller blocker: {run['blocker']}")
    if any(item[key] in {"failed", "outcome_unknown", "cancel_requested"} for item in view["attempts"] for key in ("state", "hostState")):
        raise RuntimeError("failed or uncertain attempt retained; no further scheduling authorized")
    if any(item["hostState"] is None and item["admissionObservation"] != "known_capacity_wait" for item in view["attempts"]):
        raise RuntimeError("absent host row has no exact current original admission acknowledgement")


def verify_completed(runtime, project, view):
    storage = runtime.app.state.project_folder_storage
    inventory = current_inventory(runtime, project)
    if len(inventory["subjects"]) > 32 or view["run"]["handoff"] is not None or view["run"]["bundle"] is None:
        raise RuntimeError("complete all-route material/human-review boundary differs")
    if sum(item["domain"] == "text" for item in view["attempts"]) != 8 or sum(item["domain"] == "image" for item in view["attempts"]) != len(inventory["subjects"]):
        raise RuntimeError("complete pack does not account for every required subject exactly once")
    with closing(storage.projects.open(project)) as store:
        for checkpoint in view["run"]["checkpoints"]:
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view["run"]["id"], checkpoint["operationKey"])
            if attempt is None:
                continue
            if attempt.state != "completed" or attempt.terminal_result != "success" or receipt is None:
                raise RuntimeError("complete pack lacks a genuine successful typed receipt")
            assert_receipt_matches_attempt(attempt, receipt)
    early = [item for item in view["run"]["checkpoints"] if item["evidence"]["result"].get("earlyReference")]
    if any(item["imageBudgetState"] != "consumed" or item["reservedImageOutputs"] != 1 for item in view["attempts"] if item["domain"] == "image"):
        raise RuntimeError("image budget was not consumed exactly once per subject")
    if not early or len(early) > 4 or any(item["state"] != "adopted" for item in early):
        raise RuntimeError("early references were not retained and explicitly selected at installation")
    write(WORK / "complete_inventory.json", inventory)
    from pair_workload import record_workload
    record_workload(runtime, project, view, inventory, WORK)
    emit("complete_all_route_pack", projectId=project, requiredImages=len(inventory["subjects"]), earlyJobs=len(early), bundleHash=view["run"]["bundleHash"], humanHandoff=False)


def settle(runtime, client, service, projects, plan, capture, *, material_qualified):
    runtime.bridge.exec_supervisor().halt_qualification('settling_originals')
    for project in projects.values():
        pause(client, project, "capture stopped; fence original queued work only")
    if not service.acquire_controller():
        emit("settlement_lease_unavailable", originalRunsPaused=True)
        return CleanupResult("unresolved", False, False, False)
    from pair_runtime import settlement_deadline
    deadline = settlement_deadline(runtime)
    evidence = None
    while time.monotonic() < deadline:
        for project in projects.values():
            service.step(project)
        result, evidence = cleanup_snapshot(runtime, projects, material_qualified=material_qualified)
        if result.complete_success:
            capture.require_complete()
        if result.outcome in {"complete_success", "material_incomplete", "safe_parked", "empty_unqualified"}:
            write(WORK / "cleanup_observation.json", evidence, exclusive=True)
            if result.complete_success:
                emit("quiescent", attemptCount=evidence["attemptCount"],
                    processGroups=sorted(int(group) for group in evidence["groupObservations"]),
                    held=0, queue=0, validators=0)
            else:
                emit("cleanup_observed", outcome=result.outcome, zeroLiveWork=result.zero_live_work,
                    allWorkQuiescent=result.all_work_quiescent, completeSuccess=False,
                    parkedAttempts=list(result.parked_attempts))
            return result
        time.sleep(1)
    if evidence is not None:
        write(WORK / "cleanup_observation.json", evidence, exclusive=True)
    emit("unsettled_original_work_retained", classification=evidence["classification"] if evidence else None)
    return CleanupResult("unresolved", False, False, False)


@contextmanager
def controlled(plan):
    from pair_runtime import configure_runtime, freeze_attempt
    config = configure_runtime(plan)
    with compose(config) as runtime:
        client = TestClient(runtime.app)
        service = runtime.app.state.autopilot_service
        try:
            if service._thread is not None or service._runtime_owners != 0:
                raise RuntimeError("background controller would compete with proof owner")
            profile = runtime.bridge.exec_supervisor().profile()
            if profile.profile_hash != plan["profileHash"] or not runtime.bridge.exec_supervisor().codex_exec_readiness().ready:
                raise RuntimeError("frozen profile/authentication changed")
            if not service.acquire_controller():
                raise RuntimeError("exclusive controller lease unavailable")
            capture = CampaignObservation(runtime, WORK, emit, prepared_package_snapshot, image_owners=IMAGE_METHODS,
                freeze_attempt=lambda attempt,**options: freeze_attempt(runtime,attempt,**options),
                halt=runtime.bridge.exec_supervisor().halt_qualification)
            with capture.installed():
                yield runtime, client, service, capture
        finally:
            service.close()
            client.close()


def execute(plan):
    global SETTLING
    if any((WORK / name).exists() for name in ("launch_intent.json", "timeline.jsonl", "result.json")):
        raise RuntimeError("one-shot execution already has evidence; do not rerun")
    projects, failure, passed, gates = {}, None, False, {}
    cleanup = CleanupResult("unresolved", False, False, False)
    started = json.loads((WORK/'arm-start.json').read_bytes())['monotonicNs']/1e9
    setup_started = time.monotonic_ns()
    # Reopen qualification belongs to the completed functional proof. Each timing arm has one owner.
    with ExitStack() as resources:
        initial_owner = resources.enter_context(ExitStack())
        runtime, client, service, capture = initial_owner.enter_context(controlled(plan))
        try:
            if runtime.app.state.project_folder_storage.projects.discover():
                raise RuntimeError("fresh functional installation already contains a project")
            write(WORK / "launch_intent.json", {"sourceRevision": plan["sourceRevision"], "planSha256": sha(WORK / "plan.json"), "oneShot": True}, exclusive=True)
            emit("runtime_ready", arm=plan["arm"], setupDurationNs=time.monotonic_ns() - setup_started)
            create(client, "primary", plan, projects, runtime, service)
            from pair_runtime import activate
            activate(runtime)
            with Observer(runtime.bridge.exec_supervisor(), emit) as watcher:
                previous = {}
                primary_qualified = False
                for step in range(plan["maxSteps"]):
                    if time.monotonic() - started > plan["maxWallSeconds"]:
                        raise RuntimeError("functional observer wall-time ceiling reached")
                    if watcher.failure:
                        raise RuntimeError(watcher.failure)
                    trigger = observe(runtime, projects["primary"], "primary", plan, capture)
                    assert_health(trigger)
                    if ("sidecar" not in projects and sum(item["domain"] == "image" for item in trigger["attempts"]) >= 2
                            and any(item["operationKey"] == "art" for item in trigger["attempts"])):
                        create(client, "sidecar", plan, projects, runtime, service)
                    views = {}
                    for role, project in list(projects.items()):
                        before = observe(runtime, project, role, plan, capture)
                        assert_health(before)
                        # Outline-only sidecar never advances to another stage.
                        from pair_sidecar import requires_pause
                        if (role == "sidecar" and requires_pause(before)
                                and before["run"]["state"] != "paused"):
                            pause(client, project, "one independent Outline attempt admitted; retain its late delivery")
                        freeze_prepared(runtime, project, before, role, capture)
                        step_started = time.monotonic_ns()
                        emit("controller_step_begin", role=role, step=step)
                        service.step(project)
                        emit("controller_step_end", role=role, step=step, durationNs=time.monotonic_ns() - step_started)
                        after = observe(runtime, project, role, plan, capture)
                        assert_health(after)
                        if role=='sidecar' and requires_pause(after) and after['run']['state']!='paused':
                            pause(client,project,'original Outline delivered/started; no adopting step')
                            after = observe(runtime,project,role,plan,capture)
                        views[role] = after
                        signature = (after["run"]["revision"], tuple((item["attemptId"], item["state"], item["hostState"]) for item in after["attempts"]))
                        if previous.get(role) != signature:
                            emit("controller_progress", role=role, step=step, state=after["run"]["state"], phase=after["run"]["phase"], revision=after["run"]["revision"], attempts=[{key: item[key] for key in ("attemptId", "domain", "operationKey", "state", "hostState")} for item in after["attempts"]])
                            emit("checkpoint_progress", role=role, revision=after["run"]["revision"], bundleHash=after["run"]["bundleHash"],
                                checkpoints=[{key: item[key] for key in ("operationKey", "state", "evidence")} for item in after["run"]["checkpoints"]],
                                frames=after["run"]["frames"])
                            previous[role] = signature
                    if views["primary"]["run"]["state"] == "awaiting_review":
                        if not primary_qualified:
                            emit("primary_bundle_observed", projectId=projects["primary"], bundleHash=views["primary"]["run"]["bundleHash"])
                            verify_completed(runtime, projects["primary"], views["primary"])
                            primary_qualified = True
                        sidecar = views.get("sidecar")
                        if sidecar and len(sidecar["attempts"]) == 1 and sidecar["attempts"][0]["terminalResult"] == "success":
                            gates = dict(watcher.gates)
                            passed = True
                            break
                    time.sleep(1)
                else:
                    raise RuntimeError("bounded functional controller-step ceiling reached")
        except BaseException as error:
            failure = type(error).__name__ + ": " + str(error)
            runtime.bridge.exec_supervisor().halt_qualification('driver_'+type(error).__name__)
            emit("functional_stop", error=failure)
        finally:
            SETTLING = True
            try:
                cleanup = settle(runtime, client, service, projects, plan, capture, material_qualified=passed and failure is None)
            except BaseException as error:
                emit("settlement_failed", error=type(error).__name__ + ": " + str(error))
            for role, project in projects.items():
                try:
                    observe(runtime, project, role, plan, capture)
                except BaseException as error:
                    detail = f"final_snapshot_failed: {role}: {type(error).__name__}: {error}"
                    failure, passed = failure or detail, False
                    emit("final_snapshot_failed", role=role, error=type(error).__name__)
            if passed and cleanup.complete_success and failure is None:
                try:
                    capture.require_complete()
                except BaseException as error:
                    failure, passed = f"final_rpc_observation_failed: {type(error).__name__}: {error}", False
    for path, digest in plan["priorEvidence"].items():
        if sha(ROOT / path) != digest:
            failure, passed = "retained prior evidence changed", False
    overlap_sha=None
    if passed and cleanup.complete_success and failure is None and plan['arm']=='parallel':
        try:
            from session_measurements import measure_sessions
            from campaign_guard import require_arm_overlap
            overlap=require_arm_overlap(gates,measure_sessions(WORK))
            write(WORK/'overlap.json',overlap,exclusive=True)
            overlap_sha=sha(WORK/'overlap.json')
        except Exception as error:
            failure,passed='parallel_overlap_unqualified: '+type(error).__name__+': '+str(error),False
    if time.monotonic()>started+plan['maxWallSeconds']+plan['maxSettlementSeconds']:
        failure,passed=failure or 'original arm settlement envelope exceeded',False
    from preservation import require_preserved_inputs
    require_preserved_inputs()
    result = {"passed": passed and cleanup.complete_success and failure is None, "failure": failure,
        "quiescent": cleanup.all_work_quiescent, "allWorkQuiescent": cleanup.all_work_quiescent,
        "zeroLiveWork": cleanup.zero_live_work, "cleanupOutcome": cleanup.outcome,
        "completeSuccess": cleanup.complete_success, "rpcObservation": capture.summary(),
        "sourceRevision": plan["sourceRevision"], "profileHash": plan["profileHash"], "projects": projects,
        "orderedGates": gates, "performanceQualification": False, "performanceCapture": True, "humanAcceptance": False,
        "arm": plan["arm"], "elapsedSecondsIncludingSetupAndSettlement": time.monotonic() - started,
        'overlapQualified':overlap_sha is not None,'overlapSha256':overlap_sha,
        "timelineSha256": sha(WORK / "timeline.jsonl"), "finishedUtc": datetime.now(UTC).isoformat()}
    write(WORK / "result.json", result, exclusive=True)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    plan = preflight()
    if not args.execute:
        with controlled(plan) as (runtime, _client, _service, capture):
            if runtime.app.state.project_folder_storage.projects.discover():
                raise RuntimeError("preflight installation is not empty")
            host = runtime.bridge.exec_supervisor()
            with closing(host._connect()) as connection:
                counts = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in ("exec_attempts", "exec_slot", "exec_queue", "exec_validation_process")}
            if any(counts.values()) or capture.summary()["recordsEmitted"]:
                raise RuntimeError("zero-dispatch preflight has native work or RPC capture")
            print(json.dumps({"preflight": "passed", "profileHash": plan["profileHash"],
                "generationDispatches": 0, "ledgerCounts": counts, "projects": 0,
                "noLaunchIntent": not (WORK / "launch_intent.json").exists()}))
        return 0
    from campaign_guard import require_execution_order
    require_execution_order(WORK, plan)
    return execute(plan)


def stop(_signal, _frame):
    global STOP_REQUESTED
    if STOP_REQUESTED or SETTLING:
        return
    STOP_REQUESTED = True
    raise KeyboardInterrupt("owner stopped this timing arm")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    raise SystemExit(main())
