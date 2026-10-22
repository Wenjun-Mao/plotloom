"""Typed retained batch directions jobs for shared evidence and recovery owners."""
import json
from ..codex_exec_contracts import CodexExecAttempt, CodexExecProfile, CodexExecReceipt, assert_receipt_matches_attempt
from ..creative_handoff_contracts import CreativeHandoffRequest
from ..creative_handoff_exchange import request_hash
from .format import ProjectStorageCorruptionError


def retained_batch_drafts(connection):
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='v2_video_batches'").fetchone():
        return []
    result = []
    for batch_id, project_id, raw in connection.execute("SELECT id,project_id,execution FROM v2_video_batches"):
        data = json.loads(raw).get("draft")
        if not data:
            continue
        request = CreativeHandoffRequest.model_validate(data["request"])
        attempt = CodexExecAttempt.model_validate(data["attempt"])
        profile = CodexExecProfile.model_validate(data["profile"])
        receipt = CodexExecReceipt.model_validate(data["receipt"]) if data.get("receipt") else None
        if (request.stage != "video-directions" or request.project_id != project_id or request.section_id != batch_id
                or request.source.get("batchId") != batch_id or str(attempt.run_id) != batch_id
                or str(attempt.project_id) != project_id or attempt.job_id != request.job_id
                or attempt.operation_key != request.stage or attempt.request_hash != request_hash(request)
                or attempt.profile_hash != profile.profile_hash):
            raise ProjectStorageCorruptionError("retained batch directions identity changed")
        if receipt:
            assert_receipt_matches_attempt(attempt, receipt)
        result.append((request, data, attempt, profile, receipt))
    return result
