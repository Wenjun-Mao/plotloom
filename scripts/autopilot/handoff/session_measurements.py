"""Post-run reads of only receipt-named sessions; emit timestamps and numeric usage."""
import hashlib
import json
import os
import stat
from pathlib import Path
import sqlite3
from datetime import datetime

from plotloom.codex_exec_auth import resolve_codex_home
from plotloom.codex_exec_contracts import CodexExecAttempt, CodexExecProfile, CodexExecReceipt, assert_receipt_matches_attempt
from plotloom.codex_exec_runtime import locate_exact_session
from plotloom.codex_exec_telemetry import read_cli_session



def measurement_rows(path, profile, session):
    """The scalar pass must read the exact bounded bytes already qualified."""
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != session.transcript_size_bytes or before.st_size > profile.max_output_bytes:
            raise RuntimeError("measurement transcript is not the qualified bounded regular file")
        digest, total = hashlib.sha256(), 0
        while raw := stream.readline(profile.max_event_bytes + 1):
            total += len(raw)
            if len(raw) > profile.max_event_bytes or total > profile.max_output_bytes or total > session.transcript_size_bytes:
                raise RuntimeError("measurement transcript exceeds its qualified byte bounds")
            digest.update(raw)
            yield json.loads(raw)
        after = os.fstat(stream.fileno())
        current = path.stat(follow_symlinks=False)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
        if (not stat.S_ISREG(current.st_mode) or identity(before) != identity(after) or identity(after) != identity(current)
                or total != session.transcript_size_bytes or digest.hexdigest() != session.transcript_sha256):
            raise RuntimeError("measurement transcript differs from the qualified immutable bytes")


def admit_receipt_measurements(arm_root,row,receipt,session,profile):
    """Bind fresh measurement bytes to the successful owner's original evidence."""
    from codex_exec_supervisor import CodexExecSupervisor
    private=arm_root/'private/codex-exec/attempts'/str(receipt.attempt_id)
    if Path(row['private_dir'])!=private:
        raise RuntimeError('measurement private evidence path differs from original attempt')
    paths=(private/'stdout.jsonl',private/'stderr.log')
    identity=lambda path:(lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns))(path.lstat())
    before={path:identity(path) for path in paths}
    for path in paths:
        CodexExecSupervisor._namespace_regular_file(path)
        CodexExecSupervisor._read_regular(path,max_bytes=profile.max_output_bytes)
    evidence=CodexExecSupervisor._evidence_hash(*paths,session.transcript_sha256,receipt.process_exit_code)
    if receipt.text_validation is not None:
        evidence=hashlib.sha256(f'{evidence}:{receipt.text_validation.evidence_hash}'.encode('ascii')).hexdigest()
    if evidence!=receipt.evidence_hash or any(identity(path)!=before[path] for path in paths):
        raise RuntimeError('measurement transcript/private streams differ from successful receipt evidence')
    return dict(receiptEvidenceHash=receipt.evidence_hash,receiptEvidenceHashVerified=True)


def measure_sessions(arm_root):
    plan = json.loads((arm_root / "plan.json").read_text())
    profile = CodexExecProfile.model_validate(plan["profile"])
    with sqlite3.connect(f"file:{arm_root / 'private/codex-exec/supervisor.sqlite3'}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM exec_attempts ORDER BY attempt_id").fetchall()
    home = resolve_codex_home(forbidden_roots=(arm_root,))
    result = []
    for row in rows:
        attempt = CodexExecAttempt.model_validate_json(row["status_json"])
        receipt = CodexExecReceipt.model_validate_json(row["receipt_json"])
        assert_receipt_matches_attempt(attempt, receipt)
        if attempt.profile_hash!=profile.profile_hash:
            raise RuntimeError('measurement profile differs from frozen attempt')
        path = locate_exact_session(home, receipt.session_id)
        session = read_cli_session(path, receipt.session_id, max_event_bytes=profile.max_event_bytes, max_total_bytes=profile.max_output_bytes)
        measurement=admit_receipt_measurements(arm_root,row,receipt,session,profile)
        ordinals = set()
        image_calls = []
        for evidence in receipt.image_evidence:
            call = next(item for item in session.image_calls if item.call_id == evidence.call_id and item.ordinal == evidence.call_ordinal)
            event = next(item for item in session.image_events if item.call_id == evidence.call_id and item.event_id == evidence.event_id and item.status == "completed")
            ordinals.update((call.ordinal, event.ordinal))
            image_calls.append({"callId": call.call_id, "eventId": event.event_id, "callOrdinal": call.ordinal, "completionOrdinal": event.ordinal})
        timestamps, boundaries, usage = {}, [], []
        for event in measurement_rows(path, profile, session):
            ordinal = event.get("ordinal")
            timestamp = event.get("timestamp")
            if ordinal in ordinals:
                if not isinstance(timestamp, str):
                    raise RuntimeError("qualified tool ordinal lacks recorded UTC timestamp")
                timestamps[ordinal] = timestamp
            payload = event.get("payload", {})
            if event["type"] == "event_msg" and payload.get("type") in {"task_started", "task_complete", "turn_aborted"}:
                boundaries.append({"ordinal": ordinal, "type": payload["type"], "utc": timestamp})
            if event["type"] == "event_msg" and payload.get("type") == "token_count":
                total = (payload.get("info") or {}).get("total_token_usage") or {}
                numeric = {key: value for key, value in total.items() if key in {"input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens"} and type(value) is int and value >= 0}
                if numeric:
                    usage.append({"ordinal": ordinal, "utc": timestamp, "totalTokenUsage": numeric})
        for image in image_calls:
            image.update(callUtc=timestamps[image["callOrdinal"]], completionUtc=timestamps[image["completionOrdinal"]])
        result.append({"attemptId": str(attempt.attempt_id), "projectId": str(attempt.project_id),
            "operationKey": attempt.operation_key, "domain": attempt.domain, "sessionId": str(receipt.session_id),
            "transcriptSha256": session.transcript_sha256, "transcriptSizeBytes": session.transcript_size_bytes,
            **measurement,
            "imageCalls": image_calls, "recordedTaskBoundaries": boundaries,
            "lastRecordedCumulativeTokenUsage": usage[-1] if usage else None,
            "validationSteps": [item.model_dump(mode="json", by_alias=True) for item in receipt.text_validation.steps] if receipt.text_validation else [],
            "remoteComputeTimeEstablished": False, "dollarCostAvailable": False})
    return result


def image_call_overlap(sessions):
    """Strictly positive overlap from distinct receipt-bound original attempts."""
    intervals=[]
    for session in sessions:
        if session['domain']!='image':continue
        if session.get('receiptEvidenceHashVerified') is not True:
            raise RuntimeError('image interval lacks successful receipt-bound transcript evidence')
        for call in session['imageCalls']:
            begin=datetime.fromisoformat(call['callUtc'].replace('Z','+00:00'))
            end=datetime.fromisoformat(call['completionUtc'].replace('Z','+00:00'))
            if begin.tzinfo is None or end.tzinfo is None or end<begin:
                raise RuntimeError('image interval has missing timezone or reversed boundaries')
            if end==begin:continue
            facts={key:session[key] for key in ('attemptId','sessionId','transcriptSha256','receiptEvidenceHash')}
            intervals.append((begin.timestamp(),end.timestamp(),facts|call))
    boundaries=sorted([(begin,1) for begin,_end,_facts in intervals]+[(end,-1) for _begin,end,_facts in intervals])
    active,maximum=0,0
    for _stamp,change in boundaries:
        active+=change
        maximum=max(maximum,active)
    witness=None
    for index,(begin,end,left) in enumerate(intervals):
        for other_begin,other_end,right in intervals[index+1:]:
            duration=min(end,other_end)-max(begin,other_begin)
            if left['attemptId']!=right['attemptId'] and left['sessionId']!=right['sessionId'] and duration>0:
                witness=dict(left=left,right=right,positiveOverlapSeconds=duration)
                break
        if witness is not None:break
    return dict(maximumOutstandingImageGenCalls=maximum,
        recordedOutstandingImageGenCallSecondsSum=sum(end-begin for begin,end,_facts in intervals),
        positiveReceiptBoundOverlap=witness)
