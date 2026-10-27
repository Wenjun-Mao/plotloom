"""Bounded public failure reading and explicit creator correction commands."""
import json
import re
from hashlib import sha256

from .autopilot_launch import assert_frozen_execution, require_job_capacity
from .codex_exec_files import read_confined_regular_file
from .creative_commands import current_creative_candidate
from .creative_handoff_contracts import (
    CREATIVE_CANDIDATE_FILENAMES,
    CreativeHandoffRequest,
)
from plotloom.public_values import contains_secret_value
from .exceptions import InvalidTransitionError
from .text_correction_contracts import MANUAL_CORRECTION_CONTRACTS, MANUAL_CORRECTION_STAGES, automatic_correction_limit, logical_checkpoint

STAGES = {"outline": "故事大纲", "characters": "角色设定", "art": "美术方向", "script": "剧本", "storyboard": "分镜"}


def prior_candidate(store, request, rejection):
    root = store.creative_handoff_exchange().root / "jobs" / request.job_id
    raw = read_confined_regular_file(root, "delivery/" + CREATIVE_CANDIDATE_FILENAMES[request.stage], max_bytes=500_000)
    if sha256(raw).hexdigest() != rejection.candidate_hash:
        raise InvalidTransitionError("rejected candidate bytes changed")
    return raw.decode("utf-8")


def literal(value):
    text = str(value)
    return "[redacted]" if contains_secret_value(text) else text[:1000]


def issue_details(rejection, raw):
    candidate = json.loads(raw)
    details = []
    for issue in rejection.issues:
        for path in issue.field_paths:
            value = None
            match = re.fullmatch(r"props\[(\d+)\]\.image\.(prompt|sheet)", path)
            item = "整份候选"
            if match:
                prop = candidate["props"][int(match[1])]
                value = prop.get("image", {}).get(match[2])
                item = literal(f'{prop.get("id", "")} {prop.get("name", "")}').strip()
            details.append({"code": issue.code, "field": path, "item": item,
                "rule": (f'该字段必须包含原始尺度短语「{issue.repair_facts["requiredPhrase"]}」。'
                    if issue.code == "art_prop_scale" else "候选未通过来源内容验证；具体说明见下方。"),
                "excerpt": literal(value) if match else None})
    return details


def comparison(previous, current):
    if previous is None or current is None:
        return "unknown"
    # Legacy Node explanations can be truncated at 16 messages / 500 UTF-16 units.
    # Retained receipts lack a truncation flag; stay conservative even for a
    # newer complete Art shape result. Equal prefixes do not prove equal errors.
    def bounded(rejection):
        return len(rejection.display_diagnostics) >= 16 or any(
            len(item.encode("utf-16-le", errors="surrogatepass")) // 2 >= 500
            for item in rejection.display_diagnostics)
    if bounded(previous) or bounded(current):
        return "unknown"
    # Generic code+$ cannot establish the same problem. Compare actual normal
    # validator explanations when present, otherwise only specific typed facts.
    if previous.display_diagnostics and current.display_diagnostics and "[redacted]" not in (*previous.display_diagnostics, *current.display_diagnostics):
        return "repeated" if previous.display_diagnostics == current.display_diagnostics else "changed"
    specific = lambda rejection: [issue.model_dump(mode="json", by_alias=True) for issue in rejection.issues
        if issue.code != "candidate_content_invalid"]
    left, right = specific(previous), specific(current)
    return ("repeated" if left == right else "changed") if left and right else "unknown"


def failure_context(store, registry, *, stage=None):
    view = store.repository.autopilot.current(store.manifest.project_id)
    if view is None:
        return None
    stage = stage or view.phase
    if stage not in STAGES:
        return None
    checkpoint = logical_checkpoint(view, stage)
    if checkpoint is None:
        return None
    history_view = view
    from .autopilot_contracts import CheckpointEvidence
    from .persistence.project.autopilot_continuation import inherited_origin
    from .persistence.schema import AutopilotRunRow
    with store.repository._read() as session:
        origin = inherited_origin(session.connection().connection.driver_connection, view.id,
            checkpoint["operationKey"], CheckpointEvidence.model_validate(checkpoint["evidence"]))
        if origin:
            history_view = store.repository.autopilot.view_in_session(session, session.get(AutopilotRunRow, origin))
    history = []
    previous = None
    latest_attempt = latest_request = rejected_request = None
    checkpoints = sorted([c for c in history_view.checkpoints if c["evidence"]["owner"] == stage],
        key=lambda c: c["evidence"]["result"].get("correctionOrdinal", 0))
    from .persistence.project.creative_terminal import CANDIDATE_ROWS
    for item in checkpoints:
        attempt = store.repository.autopilot.exec_attempt_for_operation(history_view.id, item["operationKey"])
        with store.repository._read() as session:
            row = session.get(CANDIDATE_ROWS[stage], item["evidence"]["jobId"])
            request = CreativeHandoffRequest.model_validate(row.request)
        rejection = attempt.content_rejection if attempt else None
        history.append({"ordinal": request.text_correction.ordinal if request.text_correction else 0,
            "mode": "manual" if request.text_correction and request.text_correction.manual_grant else "automatic" if request.text_correction else "original",
            "state": item["state"], "outcome": attempt.terminal_result if attempt else None,
            "comparison": comparison(previous, rejection)})
        if rejection:
            previous = rejection
            rejected_request = request
        if item["operationKey"] == checkpoint["operationKey"]:
            latest_attempt, latest_request = attempt, request
    rejection = latest_attempt.content_rejection if latest_attempt else None
    resolved = checkpoint["state"] == "adopted" and previous is not None
    if rejection is None and not resolved and checkpoint["state"] != "failed" and view.state not in {"blocked", "waiting"}:
        return None
    reason = "只有完成来源内容验证的明确失败可以追加修正；原任务不会重新发送。"
    can_retry = False
    details = []
    display_rejection = rejection or previous if resolved else rejection
    if display_rejection is not None:
        display_request = rejected_request if resolved else latest_request
        details = issue_details(display_rejection, prior_candidate(store, display_request, display_rejection))
    if rejection is not None:
        try:
            if stage not in MANUAL_CORRECTION_STAGES:
                raise InvalidTransitionError("本阶段未授予手动追加修正；请保留当前失败证据。")
            if view.state != "blocked" or not view.material_current or view.phase != stage:
                raise InvalidTransitionError("本次运行未处于可追加修正的当前失败状态。")
            if view.id in store.repository.autopilot.recovered_run_ids():
                raise InvalidTransitionError("恢复的证据副本不能重新发送原生任务。")
            if view.policy.executor_binding.text_correction_contract not in MANUAL_CORRECTION_CONTRACTS:
                raise InvalidTransitionError("本次冻结运行未授予额外修正能力；请保留证据并接管。")
            assert_frozen_execution(store, registry, view.policy)
            require_job_capacity(view)
            current_creative_candidate(store, stage, latest_request.job_id, require_fresh=True)
            can_retry, reason = True, "只追加一次当前失败阶段的修正；已完成阶段保持采用结果。"
        except (InvalidTransitionError, ValueError) as error:
            reason = literal(error)
    if resolved:
        reason = "本阶段已修正并采用；以下保留失败说明与尝试历史。"
    return {"runId": view.id, "runRevision": view.revision, "stage": stage, "stageLabel": STAGES[stage],
        "failedAttemptId": str(latest_attempt.attempt_id) if rejection else None,
        "rejectionHash": rejection.rejection_hash if rejection else None,
        "terminalContentFailure": rejection is not None, "resolved": resolved, "canRetry": can_retry, "reason": reason,
        "automaticUsed": store.repository.autopilot.automatic_corrections_used(history_view.id, stage),
        "automaticLimit": automatic_correction_limit(history_view.policy, stage), "issues": details,
        "diagnostics": [literal(item) for item in display_rejection.display_diagnostics] if display_rejection else [], "history": history}


def retry_text(store, registry, grant):
    with store.repository.text_retry_command():
        view = store.repository.autopilot.current(store.manifest.project_id)
        if view is None or view.id != str(grant.expected_run_id):
            raise InvalidTransitionError("text retry run changed")
        assert_frozen_execution(store, registry, view.policy)
        checkpoint = next((item for item in view.checkpoints
            if item["evidence"].get("executorAttemptId") == str(grant.failed_attempt_id)), None)
        if checkpoint is None or checkpoint["evidence"]["owner"] not in MANUAL_CORRECTION_STAGES:
            raise InvalidTransitionError("text retry failed identity is unavailable")
        attempt = store.repository.autopilot.exec_attempt_for_operation(view.id, checkpoint["operationKey"])
        if attempt.content_rejection is None or attempt.content_rejection.rejection_hash != grant.rejection_hash:
            raise InvalidTransitionError("text retry requires the exact current typed rejection")
        from .persistence.project.creative_terminal import CANDIDATE_ROWS
        with store.repository._read() as session:
            request = CreativeHandoffRequest.model_validate(session.get(CANDIDATE_ROWS[attempt.content_rejection.stage], attempt.job_id).request)
        store.repository.autopilot.grant_text_retry(view.project_id, grant, request,
            attempt.content_rejection, prior_candidate(store, request, attempt.content_rejection))
    return store.repository.autopilot.current(view.project_id)
