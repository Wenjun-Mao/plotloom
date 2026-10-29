"""Native check envelopes share storage, never creative heads or acceptance."""
from __future__ import annotations

import json
from hashlib import sha256

from sqlalchemy import select

from .codex_exec_attempt_contracts import transition_exec_attempt
from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecProfile,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
)
from .content_language_contract import (
    CHECK_INPUT,
    CHECK_OPERATION,
    bind_language_result,
    freeze_language_candidate,
    identity,
    is_language_check,
)
from .contract_identity import utc_now
from .creative_handoff_contracts import CreativeDeliveryManifest, CreativeHandoffRequest
from .creative_handoff_identity import request_hash
from .exceptions import InvalidTransitionError, NotFoundError
from .language_policy import LANGUAGE_CONTRACT_FILENAME
from .persistence.project.creative_execution_pins import freeze_execution_pin
from .persistence.schema import SourceOutlineCandidateRow


def check_operation_key(request):
    return f"{request.stage}:{CHECK_OPERATION}:{request.source['bindingHash'][:32]}"


def check_rows(session, project_id, candidate_job_id=None):
    query = select(SourceOutlineCandidateRow).where(
        SourceOutlineCandidateRow.project_id == project_id,
        SourceOutlineCandidateRow.request["source"]["operation"].as_string() == CHECK_OPERATION)
    if candidate_job_id is not None:
        query = query.where(SourceOutlineCandidateRow.request["source"]["candidateJobId"].as_string() == candidate_job_id)
    return sorted(session.scalars(query).all(), key=lambda row: (row.request.get("source", {}).get("retryOrdinal", 0), row.created_at, row.job_id), reverse=True)


def verified_check(row):
    """Revalidate the typed envelope and every retained native proof on read."""
    request = CreativeHandoffRequest.model_validate(row.request)
    if not is_language_check(request) or request.job_id != row.job_id or request.project_id != row.project_id:
        raise ValueError("content language row identity changed")
    data = row.outline
    if not isinstance(data, dict) or set(data) - {"profile", "attempt", "receipt", "result", "resultJson", "manifest", "manifestHash", "retryPolicy", "localExecutionStopped", "admissionAttempted", "admissionDeferred", "executionCancelled"}:
        raise ValueError("invalid native language checking envelope")
    policy = data.get("retryPolicy")
    if policy is not None:
        if (set(policy) != {"automaticRetryLimit", "automaticRetriesUsed", "predecessorJobIds"}
                or any(type(policy.get(key)) is not int or policy[key] < 0 for key in ("automaticRetryLimit", "automaticRetriesUsed"))):
            raise ValueError("language retry allowance changed")
        predecessors = policy["predecessorJobIds"]
        ordinal = request.source.get("retryOrdinal", 0)
        if (not isinstance(predecessors, list) or any(not isinstance(identifier, str) for identifier in predecessors)
                or len(predecessors) != len(set(predecessors)) or row.job_id in predecessors
                or type(ordinal) is not int or ordinal != len(predecessors)
                or not 0 <= policy["automaticRetriesUsed"] <= min(ordinal, policy["automaticRetryLimit"])
                or (ordinal and (request.source.get("predecessorCheckJobId") != predecessors[-1]
                                or request.source.get("checkAnchorJobId") != predecessors[0]))):
            raise ValueError("language retry lineage changed")
    for field in ("localExecutionStopped", "executionCancelled", "admissionAttempted", "admissionDeferred"):
        if field in data and type(data[field]) is not bool:
            raise ValueError("language execution control fact changed")
    profile = CodexExecProfile.model_validate(data["profile"])
    attempt = CodexExecAttempt.model_validate(data["attempt"])
    receipt = CodexExecReceipt.model_validate(data["receipt"]) if data.get("receipt") else None
    if (attempt.job_id != row.job_id or str(attempt.project_id) != row.project_id
            or attempt.operation_key != check_operation_key(request)
            or attempt.profile_hash != profile.profile_hash or attempt.request_hash != request_hash(request)
            or request.source.get("profileHash") != profile.profile_hash):
        raise ValueError("language checking attempt differs from its frozen native request")
    result = None
    if receipt:
        assert_receipt_matches_attempt(attempt, receipt)
        proof = receipt.text_validation
        if proof is None or proof.validator_hash != profile.validator_hash:
            raise ValueError("language checker requires trusted deterministic validation evidence")
    if data.get("result") is not None:
        if receipt is None or row.manifest_hash != data.get("manifestHash") or row.manifest_hash is None:
            raise ValueError("language result has no actual completed native receipt")
        result = bind_language_result(request, data["result"], require_current=False)
        raw = data.get("resultJson", "").encode()
        manifest = CreativeDeliveryManifest.model_validate(data.get("manifest"))
        if (not raw or json.loads(raw) != data["result"]
                or sha256(raw).hexdigest() != receipt.text_validation.candidate_hash
                or identity(manifest.model_dump(mode="json", by_alias=True)) != row.manifest_hash
                or manifest.validation_evidence_hash != receipt.text_validation.evidence_hash
                or manifest.candidate.sha256 != receipt.text_validation.candidate_hash
                or manifest.request_hash != attempt.request_hash
                or manifest.job_id != row.job_id or manifest.stage != request.stage
                or manifest.executor_attempt_id != attempt.attempt_id
                or manifest.codex_session_id != attempt.session_id
                or manifest.executor_profile_hash != profile.profile_hash
                or manifest.validation_plan_hash != attempt.validation_plan_hash
                or manifest.executor_provenance.code_revision != attempt.plotloom_code_revision
                or manifest.candidate.filename != receipt.text_validation.candidate_filename
                or manifest.report.filename != receipt.text_validation.report_filename
                or manifest.report.sha256 != receipt.text_validation.report_hash
                or sha256((row.report_html or "").encode()).hexdigest() != receipt.text_validation.report_hash):
            raise ValueError("stored language verdict differs from exact native receipt and immutable result bytes")
        if row.status != "ready":
            raise ValueError("completed language result must be retained independently as ready evidence")
    elif row.status == "ready":
        raise ValueError("ready language checker has no semantic result")
    elif row.status != ("cancelled" if attempt.state in {"failed", "settled"} else "prepared"):
        raise ValueError("unresolved native checker cannot release its publication hold through a creative cancellation")
    return request, data, attempt, profile, receipt, result


def require_language_pass(session, original, candidate):
    """Prospective generated-candidate gate; historical authored bytes remain readable."""
    if LANGUAGE_CONTRACT_FILENAME not in original.input_artifacts:
        raise InvalidTransitionError("旧候选仅保留原始证据；采用新生成内容需重新准备当前语言任务。")
    expected = freeze_language_candidate(original, candidate)
    for row in check_rows(session, original.project_id, original.job_id):
        if row.request["source"].get("bindingHash") == expected["bindingHash"]:
            request, _data, _attempt, _profile, _receipt, result = verified_check(row)
            if request.input_artifacts[CHECK_INPUT] != expected:
                raise InvalidTransitionError("内容语言检查来源已改变，请重新检查。")
            if result is not None and result.verdict == "pass":
                return row.job_id
            raise InvalidTransitionError("内容语言检查未通过或尚未完成；原候选保留，不能采用。")
    raise InvalidTransitionError("候选内容需要独立原生语言检查；元数据或作者/模型标记不能替代检查。")


class ContentLanguagePersistence:
    def __init__(self, access):
        self.access = access

    def find(self, original, candidate):
        expected = freeze_language_candidate(original, candidate)
        with self.access.leases.read() as session:
            for row in check_rows(session, original.project_id, original.job_id):
                if row.request["source"].get("bindingHash") == expected["bindingHash"]:
                    verified_check(row)
                    return row.job_id
        return None

    def load(self, project_id, job_id):
        with self.access.leases.read() as session:
            row = session.get(SourceOutlineCandidateRow, job_id)
            if row is None or row.project_id != project_id or not is_language_check(row.request):
                raise NotFoundError("内容语言检查任务不存在。")
            request, data, _attempt, _profile, _receipt, _result = verified_check(row)
            return request, data

    def prepare(self, request, *, pin, profile, attempt, automatic_retry_limit=1, retry_parent=None, local_execution_stopped=False, manual_command_id=None):
        with self.access.leases.lifecycle_write() as session:
            project = self.access.rows.project(session, request.project_id)
            self.access.guards.active(project)
            binding = request.source["bindingHash"]
            matches = [row for row in check_rows(session, request.project_id, request.source["candidateJobId"])
                       if row.request["source"].get("bindingHash") == binding]
            previous = None
            if matches:
                _old_request, previous, old_attempt, _p, _r, old_result = verified_check(matches[0])
                if retry_parent is None:
                    return matches[0].job_id
                from .generation_retry_policy import repeatable_failure
                if (matches[0].job_id != retry_parent or not local_execution_stopped or old_result is not None
                        or previous.get("executionCancelled") or not repeatable_failure(old_attempt)
                        or request.source.get("retryOrdinal") != matches[0].request["source"].get("retryOrdinal", 0) + 1):
                    raise InvalidTransitionError("语言检查重试的原尝试或本地停止状态已变化。")
                automatic_retry_limit = previous.get("retryPolicy", {}).get("automaticRetryLimit", 0)
                used = previous.get("retryPolicy",{}).get("automaticRetriesUsed",len(previous.get("retryPolicy",{}).get("predecessorJobIds",[])))
                if used + (0 if manual_command_id else 1) > automatic_retry_limit:
                    raise InvalidTransitionError("语言检查自动重试次数已用完。")
            policy = None
            authority = self.access.authority()
            if authority is not None or attempt.run_id is not None:
                from .autopilot_contracts import LaunchPolicy
                from .persistence.project.autopilot_continuation import (
                    project_job_counts,
                )
                from .persistence.schema import AutopilotRunRow
                from .provider_budgets import exceeds_budget
                run = session.get(AutopilotRunRow, str(authority.run_id if authority else attempt.run_id))
                if authority is not None and (run is None or str(attempt.run_id) != run.id):
                    raise InvalidTransitionError("语言检查不属于当前冻结运行。")
                policy = LaunchPolicy.model_validate(run.policy) if run else None
                if policy and exceeds_budget(project_job_counts(session, request.project_id)[0] + 1, policy.max_jobs):
                    raise InvalidTransitionError("内容语言检查超出原冻结任务容量；未提交。")
            if policy is not None:
                automatic_retry_limit = policy.automatic_retry_limit or 0
            freeze_execution_pin(session, request, pin)
            now = utc_now()
            row = SourceOutlineCandidateRow(job_id=request.job_id, project_id=request.project_id,
                source_revision=0, expected_outline_revision=0, request=request.model_dump(mode="json", by_alias=True),
                status="prepared", outline={"profile": profile.model_dump(mode="json", by_alias=True),
                    "attempt": attempt.model_dump(mode="json", by_alias=True),
                    "retryPolicy": {"automaticRetryLimit":automatic_retry_limit,
                        "predecessorJobIds":[*previous.get("retryPolicy", {}).get("predecessorJobIds", []), retry_parent] if previous else [],
                        "automaticRetriesUsed":(previous.get("retryPolicy",{}).get("automaticRetriesUsed",len(previous.get("retryPolicy",{}).get("predecessorJobIds",[]))) + (0 if manual_command_id else 1)) if previous else 0}}, created_at=now)
            session.add(row)
            session.flush()
            verified_check(row)
            return request.job_id

    def cancel_execution(self, project_id, job_id):
        """Fence the current binding before any host cancellation RPC."""
        with self.access.leases.lifecycle_write() as session:
            original = session.get(SourceOutlineCandidateRow, job_id)
            if original is None or original.project_id != project_id:
                raise NotFoundError("language checker row is unavailable")
            request, _data, _attempt, _profile, _receipt, _result = verified_check(original)
            current = next(row for row in check_rows(session, project_id, request.source["candidateJobId"])
                if row.request["source"].get("bindingHash") == request.source["bindingHash"])
            request, data, _attempt, _profile, _receipt, _result = verified_check(current)
            current.outline = data | {"executionCancelled": True}
            return request, current.outline

    def mark_admission(self, project_id, job_id, *, deferred=False):
        """Claim the exact intent once, or record its positively known deferral."""
        with self.access.leases.lifecycle_write() as session:
            row = session.get(SourceOutlineCandidateRow, job_id)
            if row is None or row.project_id != project_id:
                raise NotFoundError("language checker row is unavailable")
            _request, data, attempt, _profile, _receipt, _result = verified_check(row)
            if attempt.state != "spawn_intent" or data.get("executionCancelled"):
                return False
            if not deferred and data.get("admissionAttempted") and not data.get("admissionDeferred"):
                return False
            if deferred and not data.get("admissionAttempted"):
                raise InvalidTransitionError("capacity deferral requires the claimed exact admission intent")
            row.outline = data | {"admissionAttempted": True, "admissionDeferred": deferred}
            return True

    def observe(self, project_id, job_id, *, attempt, receipt=None, delivery=None, result_json=None, local_execution_stopped=None):
        with self.access.leases.lifecycle_write() as session:
            row = session.get(SourceOutlineCandidateRow, job_id)
            if row is None or row.project_id != project_id or not is_language_check(row.request):
                raise NotFoundError("language checker row is unavailable")
            request, data, prior, _profile, _receipt, result = verified_check(row)
            observed = transition_exec_attempt(prior, **{
                key: getattr(attempt, key) for key in (
                    "state", "session_id", "process_id", "process_group_id", "process_birth_identity",
                    "process_exit_code", "terminal_result", "remote_tool_state", "evidence_hash", "output_hash",
                    "remote_output_hash", "content_rejection", "image_budget_state", "execution_failure")})
            # transition_exec_attempt deliberately accepts lifecycle facts only;
            # compare the full immutable identity before saving those facts.
            if observed != attempt:
                raise InvalidTransitionError("原生语言检查回执身份不一致。")
            if (data.get("receipt") is not None and receipt is not None
                    and data["receipt"] != receipt.model_dump(mode="json", by_alias=True)):
                raise InvalidTransitionError("语言检查原始回执不可覆盖。")
            if result is not None:
                return
            updated = data | {"attempt": attempt.model_dump(mode="json", by_alias=True)}
            if local_execution_stopped is not None:
                updated["localExecutionStopped"] = bool(local_execution_stopped)
            if receipt is not None:
                assert_receipt_matches_attempt(attempt, receipt)
                updated["receipt"] = receipt.model_dump(mode="json", by_alias=True)
            if delivery is not None:
                if delivery.request != request or receipt is None:
                    raise InvalidTransitionError("语言检查交付来源不一致。")
                bind_language_result(request, delivery.candidate)
                row.status, row.delivery_id = "ready", delivery.manifest.delivery_id
                row.manifest_hash, row.report_html, row.delivered_at = delivery.manifest_hash, delivery.report.decode(), utc_now()
                updated |= {"result": delivery.candidate, "resultJson": result_json,
                            "manifest": delivery.manifest.model_dump(mode="json", by_alias=True),
                            "manifestHash": delivery.manifest_hash}
            elif attempt.state in {"failed", "settled"}:
                # Terminal infrastructure failures cannot publish, while UNKNOWN
                # and cancelled-but-unsettled work keep their publication hold.
                row.status = "cancelled"
            row.outline = updated
            verified_check(row)
