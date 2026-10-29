"""Finite execution-retry values and public projections, without an executor."""
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .domain_base import CamelModel


class RetryConfiguration(CamelModel):
    automatic_retry_limit: int = Field(default=1, strict=True, ge=0)


def retry_status(*, limit, current_job_id, current_attempt_id=None, predecessors=(), state="ready", possible_cost=False, automatic_used=None):
    return {"automaticRetriesUsed":len(predecessors) if automatic_used is None else automatic_used,
        "retryCount": len(predecessors), "automaticRetryLimit": limit or 0,
        "currentJobId": current_job_id, "currentAttemptId": current_attempt_id,
        "predecessorJobIds": list(predecessors), "state": state, "possiblePriorCost": possible_cost}


def repeatable_failure(attempt):
    """Semantic rejection and deliberate/configuration stops are not execution retries."""
    return (attempt.content_rejection is None and attempt.state in {"failed", "outcome_unknown"}
            and attempt.terminal_result != "not_started"
            and getattr(attempt, "execution_failure", None) not in {"cancelled", "configuration", "permission", "authorization"})


def exhausted_message(possible_cost=False):
    return ("生成任务已失败，自动重试次数已用完；可在原生成权限与剩余预算内手动重试。"
            + (" 原尝试的远端结果仍不确定，可能已经产生费用。" if possible_cost else ""))

def classify_execution_failure(stdout_path, stderr_path, *, cancelled=False):
    import json
    import re
    if cancelled:
        return "cancelled"
    patterns = {
        "authorization": r"unauthori[sz]ed|authentication.{0,30}fail|not logged in|invalid.api.key|http.{0,5}40[13]",
        "permission": r"permission denied|safety policy|cannot comply|can't comply|unable to comply|policy refusal",
        "configuration": r"invalid.{0,30}config|unsupported.{0,30}model|model.{0,30}not found",
    }
    def inspect(text):
        for kind, pattern in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return kind
        return None
    for path in (stderr_path, stdout_path):
        with path.open("rb") as stream:
            for raw in stream:
                text = raw.decode("utf-8", "replace")
                if path == stdout_path:
                    try:
                        row = json.loads(text)
                        item = row.get("item", {})
                        if row.get("type") not in {"error", "turn.failed"} and item.get("type") != "error":
                            continue
                    except ValueError:
                        continue
                category = inspect(text)
                if category:
                    return category
    return "transient"


class ManualExecutionRetry(CamelModel):
    command_id: UUID
    failed_job_id: str = Field(min_length=1, max_length=80)
    failed_attempt_id: UUID | None = None
    expected_revision: int | None = Field(default=None, strict=True, ge=1)
    expected_run_id: UUID | None = None
