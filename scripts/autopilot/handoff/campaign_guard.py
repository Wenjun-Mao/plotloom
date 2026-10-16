"""Historical material evidence and current-source arm success are distinct gates."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecReceipt, assert_receipt_matches_attempt

HISTORICAL_SOURCE = "4525e3e0a1647e84ed588813eddaf8b46f1b36b4"
HISTORICAL_RESULT_SHA = "b8f8068e1ee7cc47ddaffd393e7a7e294b877bcd9c2ac16d098135e7737101e0"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profiles_differ_only_in_capacity(serial, parallel):
    expected = {"maxProcesses": (1, 4), "maxTextProcesses": (1, 2), "maxImageProcesses": (1, 2)}
    if set(serial) != set(parallel):
        raise RuntimeError("arm profile fields differ")
    for field in serial:
        if field in expected:
            if (serial[field], parallel[field]) != expected[field]:
                raise RuntimeError("arm capacity differs from its approved values")
        elif serial[field] != parallel[field]:
            raise RuntimeError(f"non-capacity profile field differs: {field}")
    if serial["maxQueuedJobs"] != 4 or parallel["maxQueuedJobs"] != 4:
        raise RuntimeError("waiting authorization must remain bounded at four")


def _require_absent_group(group):
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return
    except OSError as error:
        raise RuntimeError("recorded process-group absence is unproved") from error
    raise RuntimeError("recorded process group is still present")


def require_zero_live_original_work(proof_root, *, require_success=False):
    database = proof_root / "private/codex-exec/supervisor.sqlite3"
    if database.is_symlink() or not database.is_file():
        raise RuntimeError("original private ledger must be a regular existing file")
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        for table in ("exec_slot", "exec_validation_process", "exec_queue"):
            if connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]:
                raise RuntimeError(f"original {table} remains unsettled")
        rows = connection.execute("SELECT * FROM exec_attempts").fetchall()
    groups = set()
    for row in rows:
        attempt = CodexExecAttempt.model_validate_json(row["status_json"])
        if attempt.state not in {"completed", "failed", "settled"}:
            raise RuntimeError("original native identity remains unsettled")
        if require_success:
            if attempt.state != "completed" or attempt.terminal_result != "success" or not row["receipt_json"]:
                raise RuntimeError("original successful receipt is missing")
            assert_receipt_matches_attempt(attempt, CodexExecReceipt.model_validate_json(row["receipt_json"]))
        groups.update(group for group in (row["worker_group_id"], attempt.process_group_id) if group is not None)
    for group in groups:
        _require_absent_group(group)
    return {"attempts": len(rows), "groupsAbsent": len(groups), "held": 0, "queue": 0, "validators": 0}


def require_historical_material_and_current_absence(proof_root):
    result = json.loads((proof_root / "result.json").read_text())
    if sha(proof_root / "result.json") != HISTORICAL_RESULT_SHA or result["sourceRevision"] != HISTORICAL_SOURCE:
        raise RuntimeError("historical result identity changed")
    if result["passed"] is not False or result["quiescent"] is not False or result["failure"] is not None:
        raise RuntimeError("historical failed in-process cleanup evidence changed")
    post = json.loads((proof_root / "post_exit_quiescence.json").read_text())
    if (post["sourceRevision"] != HISTORICAL_SOURCE or post["originalResultSha256"] != HISTORICAL_RESULT_SHA
            or post["originalResultUnchanged"] != result or not post["driverAbsent"] or post["groupsPresent"]
            or post["held"] or post["queue"] or post["validators"] or not post["allTerminalSuccess"]):
        raise RuntimeError("additive post-parent-exit evidence differs")
    live = require_zero_live_original_work(proof_root, require_success=True)
    for group in post["recordedGroups"]:
        _require_absent_group(group)
    try:
        os.kill(post["driverPid"], 0)
    except ProcessLookupError:
        pass
    else:
        raise RuntimeError("historical driver PID is present or absence unproved")
    primary = json.loads((proof_root / "latest_primary.json").read_text())
    sidecar = json.loads((proof_root / "latest_sidecar.json").read_text())
    if (primary["run"]["state"] != "awaiting_review" or primary["run"]["bundle"] is None
            or primary["run"]["handoff"] is not None or len(primary["attempts"]) != 24
            or sum(item["domain"] == "image" for item in primary["attempts"]) != 16
            or len(sidecar["attempts"]) != 1 or sidecar["run"]["state"] != "paused"
            or any(item["terminalResult"] != "success" for item in primary["attempts"] + sidecar["attempts"])
            or live["attempts"] != 25 or live["attempts"] != post["attemptCount"]):
        raise RuntimeError("historical complete material/sidecar evidence differs")
    if sha(proof_root / "timeline.jsonl") != result["timelineSha256"]:
        raise RuntimeError("historical timeline changed")
    return {"historicalSource": HISTORICAL_SOURCE, "historicalInProcessPassed": False,
        "historicalInProcessQuiescent": False, "materialComplete": True, "currentOriginalWork": live,
        "newSourceQualification": False, "requiresNewArmsToQualifyReaper": True}


def require_successful_current_arm(proof_root, *, expected_source):
    result = json.loads((proof_root / "result.json").read_text())
    if not result["passed"] or not result["quiescent"] or result["sourceRevision"] != expected_source:
        raise RuntimeError("new arm has not established success and in-process quiescence at this source")
    if (result.get("cleanupOutcome") != "complete_success" or result.get("completeSuccess") is not True
            or result.get("zeroLiveWork") is not True or result.get("allWorkQuiescent") is not True):
        raise RuntimeError("safe parking cannot satisfy the successful complete-arm gate")
    capture = result.get("rpcObservation", {})
    if (not capture.get("recordsEmitted") or capture.get("discardedRecords") != 0
            or capture.get("activeRpcCount") != 0 or capture.get("halted")
            or capture.get("persistenceFailure")
            or capture.get("recordsEmitted") != capture.get("recordsFinished")
            or sha(proof_root / "rpc_observations.jsonl") != capture.get("recordsSha256")):
        raise RuntimeError("successful arm has incomplete or changed original RPC evidence")
    live = require_zero_live_original_work(proof_root, require_success=True)
    if capture.get("frozenJobs") != live["attempts"]:
        raise RuntimeError("successful host rows differ from the complete pre-admission frozen job count")
    if proof_root.name=='parallel':
        from session_measurements import measure_sessions
        proof=require_arm_overlap(result.get('orderedGates',{}),measure_sessions(proof_root))
        if (result.get('overlapQualified') is not True or sha(proof_root/'overlap.json')!=result.get('overlapSha256')
                or json.loads((proof_root/'overlap.json').read_bytes())!=proof):
            raise RuntimeError('parallel arm lacks its unchanged current overlap qualification')
    return live


def require_execution_order(arm_root, plan):
    campaign = arm_root.parent
    marker = json.loads((campaign / "campaign_intent.json").read_text())
    if marker["sourceRevision"] != plan["sourceRevision"] or marker["sealedPlanSha256"] != plan["sealedPlanSha256"]:
        raise RuntimeError("arm lacks the exact one-shot campaign identity")
    require_historical_material_and_current_absence(Path(plan["functionalProofRoot"]))
    if plan["arm"] == "parallel":
        require_successful_current_arm(campaign / "serial", expected_source=plan["sourceRevision"])


def require_arm_overlap(gates,sessions):
    """Parallel success requires both owned process order and positive tool overlap."""
    if (set(gates)!={'cross','images','texts'} or any(type(value) is not int or value<=0 for value in gates.values())
            or not gates['cross']<=gates['images']<=gates['texts']):
        raise RuntimeError('current pair lacks ordered cross-domain/image/independent-text process evidence')
    from session_measurements import image_call_overlap
    overlap=image_call_overlap(sessions)
    if overlap['positiveReceiptBoundOverlap'] is None:
        raise RuntimeError('current pair lacks receipt-bound overlapping ImageGen call intervals')
    return dict(orderedProcessGates=gates,receiptBoundImageOverlap=overlap['positiveReceiptBoundOverlap'],
        capacityOnlySpeedupEstablished=False,statisticalConfidenceEstablished=False,humanAcceptance=False)


def require_pair_overlap(campaign,analysis):
    for arm in ('serial','parallel'):
        require_successful_current_arm(campaign/arm,expected_source=analysis['sourceRevision'])
    return json.loads((campaign/'parallel/overlap.json').read_bytes())
