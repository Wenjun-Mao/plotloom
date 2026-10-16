"""Analyze one complete observed pair after capture, retaining workload differences."""
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

from pair_context import CONTROLS, current
WORK = current().campaign
ROOT = current().source
from campaign_guard import profiles_differ_only_in_capacity, require_successful_current_arm
from session_measurements import measure_sessions,image_call_overlap


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def intervals(events):
    observations = defaultdict(list)
    for event in events:
        if event["event"] == "host_state_observed":
            observations[event["attemptId"]].append(event)
    result = []
    for identity, rows in observations.items():
        first = {}
        for row in rows:
            first.setdefault(row["state"], row)
        def bounds(start, end):
            if start not in first or end not in first:
                return None
            left, right = first[start], first[end]
            if left["observationWindowStartNs"] is None or right["observationWindowStartNs"] is None:
                return None
            return {"minimumSeconds": max(0, (right["observationWindowStartNs"] - left["monotonicNs"]) / 1e9),
                "maximumSeconds": (right["monotonicNs"] - left["observationWindowStartNs"]) / 1e9,
                "basis": "passive consecutive sampling windows; intermediate states can be unobserved"}
        result.append({"attemptId": identity, "domain": rows[0]["domain"], "operationKey": rows[0]["operationKey"],
            "observedTransitions": rows, "queuedToGrant": bounds("queued", "spawn_intent"),
            "grantToRunning": bounds("spawn_intent", "running"), "runningToValidating": bounds("running", "validating"),
            "validatingToCompleted": bounds("validating", "completed")})
    return result


def analyze_arm(arm, source):
    target = WORK / arm
    require_successful_current_arm(target, expected_source=source)
    result = json.loads((target / "result.json").read_text())
    if sha(target / "timeline.jsonl") != result["timelineSha256"]:
        raise RuntimeError("arm timeline changed after its result")
    events = [json.loads(line) for line in (target / "timeline.jsonl").read_text().splitlines()]
    start = next(row for row in events if row["event"] == "run_start_requested" and row["role"] == "primary")
    complete = next(row for row in events if row["event"] == "primary_bundle_observed")
    qualified = next(row for row in events if row["event"] == "complete_all_route_pack")
    quiet = next(row for row in events if row["event"] == "quiescent")
    runtime = next(row for row in events if row["event"] == "runtime_ready")
    workload = json.loads((target / "workload.json").read_text())
    sessions = measure_sessions(target)
    overlap=image_call_overlap(sessions)
    steps = [row for row in events if row["event"] == "controller_step_end"]
    vector = {key: workload[key] for key in ("summaryCounts", "topology", "completeRoutes", "filmedNodeIds", "routeOnlyNodeIds", "routeCount", "requiredImages", "requiredByOwner", "artBySubjectType", "uniqueFilmedShotIds", "nativeTextCalls", "nativeImageCalls", "referenceAttachmentCounts", "adoptedFrames", "geometryOperations")}
    return {"arm": arm, "resultSha256": sha(target / "result.json"), "timelineSha256": result["timelineSha256"],
        "primaryStartToCompletePackSeconds": (complete["monotonicNs"] - start["monotonicNs"]) / 1e9,
        "primaryStartToAssignedWorkQuiescentSeconds": (quiet["monotonicNs"] - start["monotonicNs"]) / 1e9,
        "completePackVerificationBookkeepingSeconds": (qualified["monotonicNs"] - complete["monotonicNs"]) / 1e9,
        "runtimeSetupSeconds": runtime["setupDurationNs"] / 1e9,
        "elapsedSecondsIncludingSetupAndSettlement": result["elapsedSecondsIncludingSetupAndSettlement"],
        "controllerStepSeconds": sum(row["durationNs"] for row in steps) / 1e9,
        "controllerSteps": steps, "controllerProgress": [row for row in events if row["event"] == "controller_progress"],
        "checkpointAndGeometryTransitions": [row for row in events if row["event"] == "checkpoint_progress"],
        "observer": [row for row in events if row["event"] == "observer_summary"],
        "processAndQueueObservations": intervals(events),
        **overlap,
        "sessions": sessions, "workloadVector": vector, "completeWorkload": workload,
        "independentSidecarTextCalls": sum(session["domain"] == "text" for session in sessions) - workload["nativeTextCalls"],
        "toolIntervalsIncludeProviderQueueing": True, "remoteComputeThroughputEstablished": False}


def main():
    sealed = json.loads((WORK / "plan.json").read_text())
    if sha(Path(__file__)) != sealed["analysisSha256"] or sha(CONTROLS / "session_measurements.py") != sealed["sessionMeasurementSha256"]:
        raise RuntimeError("measurement source differs from the sealed plan")
    pair = json.loads((WORK / "result.json").read_text())
    if not pair["complete"] or pair["sourceRevision"] != sealed["sourceRevision"]:
        raise RuntimeError("a complete current-source pair is required")
    plans = {arm: json.loads((WORK / arm / "plan.json").read_text()) for arm in sealed["order"]}
    profiles_differ_only_in_capacity(plans["serial"]["profile"], plans["parallel"]["profile"])
    arms = {arm: analyze_arm(arm, sealed["sourceRevision"]) for arm in sealed["order"]}
    seconds = {arm: value["primaryStartToCompletePackSeconds"] for arm, value in arms.items()}
    differences = {key: {arm: value["workloadVector"][key] for arm, value in arms.items()} for key in arms["serial"]["workloadVector"] if arms["serial"]["workloadVector"][key] != arms["parallel"]["workloadVector"][key]}
    result = {"sourceRevision": sealed["sourceRevision"], "sealedPlanSha256": sha(WORK / "plan.json"), "arms": arms,
        "observedPrimaryWallDifferenceSecondsSerialMinusParallel": seconds["serial"] - seconds["parallel"],
        "workloadDifferences": differences, "authorInputMatched": True, "contentEquivalent": False,
        "capacityOnlySpeedupEstablished": False, "statisticalConfidenceEstablished": False,
        "humanAcceptance": False, "dollarCostAvailable": False,
        "interpretation": "One sequential observational pair with newly generated content. Actual workloads and remote queue/load may differ; no capacity-only multiplier is established."}
    with (WORK / "analysis.json").open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"analysis": str(WORK / "analysis.json"), "primaryWallSeconds": seconds, "differingWorkloadFields": list(differences), "capacityOnlySpeedupEstablished": False}))
    return result


if __name__ == "__main__":
    main()
