"""Pure, secret-free measurements over already-read acceptance evidence.

Callers retain workload, qualification policy, storage access and receipt disclosure.
"""
from __future__ import annotations
from collections.abc import Sequence
import re
from plotloom.artifact_contracts import ArtifactKind
from plotloom.run_contracts import AttemptStatus, GenerationAttemptKind
from plotloom.run_evidence_contracts import RunExecutionTrace, RunTrace
from plotloom.stage_contracts import StageName

SAFE_ISSUE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")


def public_token_usage(trace: RunTrace) -> dict[str, int]:
    """Aggregate only numeric provider usage recorded in the temporary trace."""

    input_tokens = 0
    output_tokens = 0
    for artifact in trace.artifacts:
        if artifact.kind != ArtifactKind.RESPONSE or not isinstance(artifact.content, dict):
            continue
        usage = artifact.content.get("usage")
        if not isinstance(usage, dict):
            continue
        for field, total_name in (("inputTokens", "input"), ("outputTokens", "output")):
            value = usage.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                if total_name == "input":
                    input_tokens += value
                else:
                    output_tokens += value
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": input_tokens + output_tokens,
    }


def stable_issue_codes(trace: RunTrace) -> set[str]:
    """Extract machine-readable codes without exporting temporary evidence."""

    codes: set[str] = set()
    for artifact in trace.artifacts:
        if artifact.kind != ArtifactKind.VALIDATION or not isinstance(artifact.content, dict):
            continue
        issues = artifact.content.get("issues")
        if not isinstance(issues, list):
            continue
        for issue in issues:
            code = issue.get("code") if isinstance(issue, dict) else None
            if isinstance(code, str) and SAFE_ISSUE_CODE.fullmatch(code):
                codes.add(code)
    # These outcomes are application-owned lifecycle codes.  Include them for
    # a provider failure that has no validation artifact, but never include an
    # arbitrary provider-provided string in the public receipt.
    for attempt in trace.attempts:
        code = attempt.outcome_code
        if (
            attempt.status != AttemptStatus.SUCCEEDED
            and isinstance(code, str)
            and (code.startswith("provider.") or code.startswith("contract."))
            and SAFE_ISSUE_CODE.fullmatch(code)
        ):
            codes.add(code)
    return codes


def first_pass_stats(execution: RunExecutionTrace, trace: RunTrace, *, stage_order: Sequence[StageName]) -> dict[str, int]:
    """Credit a stage only when all its units succeed on their primary attempt."""

    accepted = rejected = outcome_unknown = cancelled = not_run = 0
    for stage in stage_order:
        unit_ids = {
            unit.id for unit in execution.work_units if unit.stage == stage
        }
        stage_attempts = [
            attempt for attempt in trace.attempts if attempt.work_unit_id in unit_ids
        ]
        primary_by_unit = {
            attempt.work_unit_id: attempt
            for attempt in stage_attempts
            if attempt.attempt_kind == GenerationAttemptKind.PRIMARY
        }
        if unit_ids and set(primary_by_unit) == unit_ids and all(
            attempt.status == AttemptStatus.SUCCEEDED
            for attempt in primary_by_unit.values()
        ):
            accepted += 1
        elif any(attempt.outcome_unknown for attempt in stage_attempts):
            outcome_unknown += 1
        elif any(
            attempt.status == AttemptStatus.FAILED and not attempt.outcome_unknown
            for attempt in primary_by_unit.values()
        ):
            rejected += 1
        elif any(
            attempt.status == AttemptStatus.CANCELLED for attempt in stage_attempts
        ):
            cancelled += 1
        else:
            not_run += 1
    return {
        "total": len(stage_order),
        "accepted": accepted,
        "rejected": rejected,
        "outcomeUnknown": outcome_unknown,
        "cancelled": cancelled,
        "notRun": not_run,
    }


def maximum_attempts_per_work_unit(trace: RunTrace) -> int:
    counts: dict[str, int] = {}
    for attempt in trace.attempts:
        if attempt.work_unit_id is not None:
            counts[attempt.work_unit_id] = counts.get(attempt.work_unit_id, 0) + 1
    return max(counts.values(), default=0)
