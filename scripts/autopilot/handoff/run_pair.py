"""Preflight or execute one ordered, source-frozen observational native pair."""
import argparse
import hashlib
import json
import signal
import subprocess
import sys
from datetime import UTC, datetime

from pair_context import CONTROLS, current
WORK = current().campaign
ROOT = current().source
from campaign_guard import require_successful_current_arm

ACTIVE = None
STOPPED = False


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def stop(_signal, _frame):
    global STOPPED
    if STOPPED:
        return
    STOPPED = True
    if ACTIVE is not None and ACTIVE.poll() is None:
        # Signal only our exact driver. Its finally block pauses new work and
        # retains/reconciles originals; never kill native provider groups here.
        ACTIVE.send_signal(signal.SIGTERM)


def preflight():
    from pair_preflight import preflight_campaign
    sealed = preflight_campaign()
    for arm in sealed['order']:
        completed = subprocess.run([sys.executable, '-B', str(CONTROLS / 'pair_arm_receiver.py'),
            '--arm', arm], cwd=ROOT, capture_output=True, text=True, timeout=120)
        path = WORK / arm / f"preflight-{datetime.now(UTC).strftime('%H%M%S%f')}.log"
        with path.open('x') as stream:
            stream.write(completed.stdout + completed.stderr)
        if completed.returncode != 0:
            raise RuntimeError('arm zero-dispatch preflight failed: ' + arm)
    return sealed


def execute(sealed):
    global ACTIVE
    marker = {"sourceRevision": sealed["sourceRevision"], "sealedPlanSha256": sha(WORK / "plan.json"), "startedUtc": datetime.now(UTC).isoformat(), "oneShot": True}
    write_once(WORK / "campaign_intent.json", marker)
    results, qualified, gate_failures = {}, set(), {}
    for arm in sealed["order"]:
        if STOPPED:
            break
        if arm == "parallel":
            require_successful_current_arm(WORK / "serial", expected_source=sealed["sourceRevision"])
        log = WORK / arm / "capture.log"
        with log.open("x") as stream:
            if STOPPED:
                break
            ACTIVE = subprocess.Popen([sys.executable, "-B", str(CONTROLS / 'pair_arm_receiver.py'), '--arm', arm, '--execute'], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            if STOPPED and ACTIVE.poll() is None:
                ACTIVE.send_signal(signal.SIGTERM)
            print(json.dumps({"arm": arm, "driverPid": ACTIVE.pid, "log": str(log)}), flush=True)
            code = ACTIVE.wait()
        ACTIVE = None
        path = WORK / arm / "result.json"
        results[arm] = json.loads(path.read_text()) if path.exists() else {"passed": False, "quiescent": False, "driverExitCode": code}
        if code != 0 or not results[arm]["passed"] or not results[arm]["quiescent"]:
            break
        try:
            require_successful_current_arm(WORK / arm, expected_source=sealed["sourceRevision"])
        except Exception as error:
            gate_failures[arm] = type(error).__name__ + ": " + str(error)
            break
        qualified.add(arm)
    complete = not STOPPED and qualified == set(sealed["order"])
    result = {"complete": complete, "stopped": STOPPED, "arms": results, "sourceRevision": sealed["sourceRevision"],
        "successfulCurrentArmGates": sorted(qualified), "strictArmGateFailures": gate_failures,
        "authorInputMatched": True, "contentEquivalent": False, "capacityOnlySpeedupEstablished": False,
        "finishedUtc": datetime.now(UTC).isoformat()}
    write_once(WORK / "result.json", result)
    print(json.dumps(result), flush=True)
    return 0 if complete else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    sealed = preflight()
    if STOPPED:
        raise SystemExit(130)
    if args.execute:
        raise SystemExit(execute(sealed))
    print(json.dumps({"preflight": "passed", "generationDispatches": 0, "sealedPlanSha256": sha(WORK / "plan.json"), "profiles": sealed["profiles"]}))
