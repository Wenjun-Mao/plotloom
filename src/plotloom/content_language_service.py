"""One durable independent check through the existing supervised native host."""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecPackageFile,
    CodexExecProfile,
    assert_receipt_matches_attempt,
    package_manifest_hash,
)
from .codex_exec_runtime import frozen_package_snapshot
from .codex_exec_validation import validation_plan_from_package
from .content_language_contract import (
    CHECK_INPUT,
    CHECK_OPERATION,
    ContentLanguageResult,
    freeze_language_candidate,
    language_check_instructions,
    render_language_report,
)
from .content_language_persistence import check_operation_key
from .creative_exchange_files import creative_job_root
from .creative_handoff_contracts import CreativeHandoffRequest
from .creative_handoff_identity import canonical_json, request_hash
from .creative_package_projection import project_creative_package
from .exceptions import InvalidTransitionError
from .language_policy import LANGUAGE_CONTRACT_FILENAME, assert_language_current


class ContentLanguageService:
    def __init__(self, registry):
        self.registry = registry

    def prepare(self, store, original, candidate, *, code_revision=None, run_id=None, automatic_retry_limit=1, retry_parent=None, local_execution_stopped=False, manual_command_id=None):
        assert_language_current(original.input_artifacts, store.project().require_brief().language)
        frozen = freeze_language_candidate(original, candidate)
        owner = store.repository.content_language
        profile = CodexExecProfile.model_validate(self.registry.codex_exec_profile())
        previous = owner.find(original, candidate)
        if previous is not None and retry_parent is None:
            _retained, data = owner.load(original.project_id, previous)
            if CodexExecProfile.model_validate(data["profile"]) != profile:
                raise InvalidTransitionError("语言检查执行设置已变化；原结果不再适用，保留原检查且不重复提交。")
            return previous  # Same inputs never create a duplicate failed/UNKNOWN check.
        self.registry.require_codex_exec_readiness()
        exchange = store.creative_handoff_exchange()
        pin = exchange.current_execution_pin(original.stage)
        if pin != store.creative_handoff_execution_pin(original):
            raise InvalidTransitionError("生成来源执行版本已变化；保留候选，请重新准备。")
        revision = code_revision or exchange.current_execution_pin("bridge-intent")["upstreamRevision"]
        ordinal = 0
        if retry_parent:
            prior_request, _data = owner.load(original.project_id, retry_parent)
            ordinal = prior_request.source.get("retryOrdinal", 0) + 1
        suffix = f":retry:{ordinal}" if ordinal else ""
        token = uuid5(NAMESPACE_URL, f"plotloom:content-language:{original.project_id}:{original.job_id}:{frozen['bindingHash']}{suffix}")
        request = CreativeHandoffRequest(job_id="ch_" + token.hex, project_id=original.project_id,
            section_id=original.section_id, stage=original.stage, expected_stage_revision=original.expected_stage_revision,
            source={"operation": CHECK_OPERATION, "candidateJobId": original.job_id,
                    "bindingHash": frozen["bindingHash"], "profileHash": profile.profile_hash,
                    **({"retryOrdinal":ordinal, "predecessorCheckJobId":retry_parent,
                        "checkAnchorJobId":prior_request.source.get("checkAnchorJobId", retry_parent),
                        **({"manualCommandId":str(manual_command_id)} if manual_command_id else {})} if retry_parent else {})},
            input_artifacts={CHECK_INPUT: frozen, LANGUAGE_CONTRACT_FILENAME: frozen["languageContract"],
                             "content-language-schema.json": ContentLanguageResult.model_json_schema(by_alias=True)},
            creative_brief=language_check_instructions())
        request.assert_secret_free()
        projected, instructions, _template, _members = project_creative_package(
            creative_job_root(exchange.root, request.job_id), request, pin,
            executor_backend="codex_exec", plotloom_code_revision=revision)
        files = {"request.json": canonical_json(projected), "COPY_ASSIGNMENT.txt": instructions,
                 **{f"inputs/{name}": canonical_json(value) for name, value in request.input_artifacts.items()}}
        from .creative_handoff_package_exchange import _json_file_limit
        if any(name.endswith(".json") and len(content) > _json_file_limit(request) for name, content in files.items()):
            raise InvalidTransitionError("完整语言检查包超过现有单文件容量；未截断来源或提交任务。")
        package_hash = package_manifest_hash(tuple(CodexExecPackageFile(relative_path=name,
            sha256=sha256(content).hexdigest(), size_bytes=len(content)) for name, content in sorted(files.items())))
        attempt = CodexExecAttempt(attempt_id=uuid5(token, "native-attempt"), run_id=run_id or token,
            project_id=original.project_id, job_id=request.job_id, operation_key=check_operation_key(request), domain="text",
            request_hash=request_hash(request), package_hash=package_hash, profile_hash=profile.profile_hash,
            plotloom_code_revision=revision, validation_plan_hash=validation_plan_from_package(projected).plan_hash,
            reserved_image_outputs=0, image_budget_state="none", state="spawn_intent")
        return owner.prepare(request, pin=pin, profile=profile, attempt=attempt,
            automatic_retry_limit=automatic_retry_limit, retry_parent=retry_parent, local_execution_stopped=local_execution_stopped, manual_command_id=manual_command_id)

    def advance(self, store, job_id, *, allow_admission=True):
        owner = store.repository.content_language
        job_id = _current_check_job(store, job_id)
        request, data = owner.load(store.manifest.project_id, job_id)
        if data.get("result") is not None or (allow_admission and data.get("executionCancelled")):
            return self.status(store, job_id)
        attempt = CodexExecAttempt.model_validate(data["attempt"])
        profile = CodexExecProfile.model_validate(data["profile"])
        if CodexExecProfile.model_validate(self.registry.codex_exec_profile()) != profile:
            raise InvalidTransitionError("语言检查执行设置已变化；原尝试保留，不会重复提交。")
        original = CreativeHandoffRequest.model_validate(request.input_artifacts[CHECK_INPUT]["originalRequest"])
        if allow_admission:
            from .content_language_candidates import load_generated_candidate
            retained, _candidate = load_generated_candidate(store, original.stage, original.job_id,
                request.input_artifacts[CHECK_INPUT]["candidate"])
            if retained != original:
                raise InvalidTransitionError("原生成请求已变化；未发送语言检查。")
            assert_language_current(original.input_artifacts, store.project().require_brief().language)
            from .project_storage.recovery_control import read_recovery_control
            recovery = read_recovery_control(store.home, original.project_id)
            if recovery and any(item.kind == "codex_exec_attempt" and item.operation_id == str(attempt.attempt_id)
                                for item in recovery.operations):
                raise InvalidTransitionError("恢复的原检查尝试仅保留证据；不能重放原生检查。")
        exchange = store.creative_handoff_exchange()
        pin = store.creative_handoff_execution_pin(request)
        if exchange.current_execution_pin(request.stage) != pin:
            raise InvalidTransitionError("语言检查来源执行锁定已变化；原尝试保留。")
        paths = exchange.write_package(request, pin, executor_backend="codex_exec",
                                       plotloom_code_revision=attempt.plotloom_code_revision)
        package_hash, _raw = frozen_package_snapshot(Path(paths["packagePath"]).parent,
                                                    max_total_bytes=profile.max_output_bytes)
        if package_hash != attempt.package_hash:
            raise InvalidTransitionError("语言检查包与持久化身份不一致；未提交。")
        status = self.registry.codex_exec_status(attempt.attempt_id)
        if status.state == "not_found" and allow_admission:
            if attempt.state != "spawn_intent":
                raise InvalidTransitionError("语言检查结果不确定；不能创建或重发尝试。")
            if not owner.mark_admission(store.manifest.project_id, job_id):
                # Another caller owns this exact durable admission. Observation
                # cannot prove whether its RPC began, so never resend or reopen.
                return self.status(store, job_id)
            called = False
            try:
                with _check_admission(store, request, attempt):
                    called = True
                    status = self.registry.codex_exec_admit(attempt)
            except Exception:
                if called:
                    _hold_check_unknown(store, attempt)
                raise
            if status.state == "not_found" and status.capacity_deferred:
                owner.mark_admission(store.manifest.project_id, job_id, deferred=True)
            if status.state == "not_found" and not status.capacity_deferred:
                _hold_check_unknown(store, attempt)
                return self.status(store, job_id)
        if allow_admission and status.dispatch_enabled is False and attempt.state != "outcome_unknown":
            called = False
            try:
                with _check_admission(store, request, attempt):
                    called = True
                    status = self.registry.codex_exec_resume(attempt)
            except Exception:
                if called:
                    _hold_check_unknown(store, attempt)
                raise
        if status.state == "not_found" or status.attempt is None:
            return self.status(store, job_id)
        observed, receipt = status.attempt, status.receipt
        if allow_admission:
            from .generation_retry_policy import repeatable_failure
            if repeatable_failure(observed) and status.local_execution_stopped:
                owner.observe(store.manifest.project_id, job_id, attempt=observed, receipt=receipt, local_execution_stopped=status.local_execution_stopped, admission_acknowledged=True)
                limit = data.get("retryPolicy", {}).get("automaticRetryLimit", 0)
                if data.get("retryPolicy", {}).get("automaticRetriesUsed",request.source.get("retryOrdinal",0)) < limit:
                    frozen = request.input_artifacts[CHECK_INPUT]
                    successor = self.prepare(store, original, frozen["candidate"],
                        code_revision=attempt.plotloom_code_revision, run_id=attempt.run_id,
                        retry_parent=job_id, local_execution_stopped=True)
                    return self.status(store, successor)

        if attempt.state == "outcome_unknown" and observed.state in {"queued", "spawn_intent"}:
            return self.status(store, job_id)
        delivery = None
        result_json = None
        if receipt:
            assert_receipt_matches_attempt(observed, receipt)
            delivery = exchange.read_delivery(request, pin, executor_backend="codex_exec",
                executor_attempt=observed, executor_profile=profile, executor_receipt=receipt,
                plotloom_code_revision=attempt.plotloom_code_revision)
            if delivery is None or render_language_report(request, delivery.candidate) != delivery.report:
                raise InvalidTransitionError("已完成语言检查缺少完整且可信的交付。")
            from .codex_exec_files import read_confined_regular_file
            from .creative_handoff_contracts import CREATIVE_CANDIDATE_FILENAMES
            result_json = read_confined_regular_file(Path(paths["packagePath"]).parent,
                "delivery/" + CREATIVE_CANDIDATE_FILENAMES[request.stage], max_bytes=2_000_000).decode()
        owner.observe(store.manifest.project_id, job_id, attempt=observed, receipt=receipt,
                      delivery=delivery, result_json=result_json, local_execution_stopped=status.local_execution_stopped, admission_acknowledged=True)
        return self.status(store, job_id)

    @staticmethod
    def status(store, job_id):
        job_id = _current_check_job(store, job_id)
        request, data = store.repository.content_language.load(store.manifest.project_id, job_id)
        result = data.get("result")
        state = "completed" if result is not None else data["attempt"]["state"]
        if (state == "spawn_intent" and data.get("admissionAttempted")
                and not data.get("admissionDeferred") and not data.get("admissionAcknowledged")):
            state = "outcome_unknown"  # An unacknowledged claim never proves non-dispatch.
        from .content_language_rejection import _language_issues
        issues = (_language_issues(request, ContentLanguageResult.model_validate(result))
                  if result is not None and result["verdict"] == "reject" else ())
        from .generation_retry_policy import repeatable_failure, retry_status
        policy = data.get("retryPolicy", {})
        unresolved = state in {"failed", "outcome_unknown"} and not data.get("result")
        allowance = policy.get("automaticRetriesUsed", 0) < policy.get("automaticRetryLimit", 0)
        pending = (unresolved and allowance and not data.get("executionCancelled")
                   and not data.get("localExecutionStopped")
                   and (repeatable_failure(CodexExecAttempt.model_validate(data["attempt"]))
                        or data["attempt"]["state"] == "spawn_intent"))
        return {"retry":retry_status(limit=policy.get("automaticRetryLimit"), current_job_id=job_id,
                    current_attempt_id=data["attempt"]["attemptId"], predecessors=policy.get("predecessorJobIds", []),
                    automatic_used=policy.get("automaticRetriesUsed",len(policy.get("predecessorJobIds",[]))),
                    state="retry_pending" if pending else "stopped" if data.get("executionCancelled") or data["attempt"].get("executionFailure") in {"cancelled","configuration","permission","authorization"} else
                          ("stopped" if not data.get("localExecutionStopped") else
                           "retry_pending" if policy.get("automaticRetriesUsed",len(policy.get("predecessorJobIds",[]))) < policy.get("automaticRetryLimit",0) else "exhausted") if state in {"failed","outcome_unknown"} else "running" if state in {"running","validating"} else "ready",
                    possible_cost=state == "outcome_unknown" or bool(policy.get("predecessorJobIds"))),
            "executionPending": bool(pending),
            "checkJobId": request.source.get("checkAnchorJobId",job_id), "candidateJobId": request.source["candidateJobId"],
            "candidateHash": request.input_artifacts[CHECK_INPUT]["candidateHash"],
            "bindingHash": request.source["bindingHash"], "state": state,
            "verdict": result["verdict"] if result else None,
            "coverage": result["coverage"] if result else [], "findings": result["findings"] if result else [],
            "issues": [item.model_dump(mode="json", by_alias=True) for item in issues],
            "blocker": (None if result and result["verdict"] == "pass" else
                "内容语言检查未通过或未完成；原候选与原尝试保留，尚未采用。")}

    def retry(self, store, job_id, command):
        store.require_recovery_acknowledged()
        owner = store.repository.content_language
        with store.repository.manual_command():
            current = _current_check_job(store, job_id)
            request, data = owner.load(store.manifest.project_id, current)
            if request.source.get("manualCommandId") == str(command.command_id):
                predecessor = request.source.get("predecessorCheckJobId")
                _prior_request, prior_data = owner.load(store.manifest.project_id,predecessor)
                if command.failed_job_id != predecessor or str(command.failed_attempt_id) != prior_data["attempt"]["attemptId"]:
                    raise InvalidTransitionError("重试命令不能替换原始失败身份。")
                return self.status(store, current)
            if data.get("executionCancelled"):
                raise InvalidTransitionError("原检查已取消；原重试权限已停止。")
            attempt = CodexExecAttempt.model_validate(data["attempt"])
            if command.failed_job_id != current or command.failed_attempt_id != attempt.attempt_id:
                raise InvalidTransitionError("手动重试的原任务已变化。")
            status = self.registry.codex_exec_status(attempt.attempt_id)
            from .generation_retry_policy import repeatable_failure
            if status.attempt != attempt or not status.local_execution_stopped or not repeatable_failure(attempt):
                raise InvalidTransitionError("原任务仍在执行、已取消或不适合重试。")
            original = CreativeHandoffRequest.model_validate(request.input_artifacts[CHECK_INPUT]["originalRequest"])
            with _check_admission(store, request, attempt):
                successor = self.prepare(store, original, request.input_artifacts[CHECK_INPUT]["candidate"],
                    code_revision=attempt.plotloom_code_revision, run_id=attempt.run_id,
                    retry_parent=current, local_execution_stopped=True, manual_command_id=command.command_id)
        return self.advance(store, successor)

    def ensure(self, store, original, candidate, *, code_revision=None, run_id=None, automatic_retry_limit=1):
        job = self.prepare(store, original, candidate, code_revision=code_revision, run_id=run_id, automatic_retry_limit=automatic_retry_limit)
        return self.advance(store, job)


def reconcile_language_checks(store, registry, run_id, *, cancel=False):
    from .content_language_persistence import check_rows, verified_check
    with store.repository._read() as session:
        pending = [(row.job_id, verified_check(row)[2]) for row in check_rows(session, store.manifest.project_id)
                   if str(verified_check(row)[2].run_id) == str(run_id)]
    service = ContentLanguageService(registry)
    for job, attempt in pending:
        if attempt.state in {"completed", "failed", "settled"}:
            continue
        if cancel:
            status = registry.codex_exec_cancel(attempt)
            if status.attempt is not None:
                store.repository.content_language.observe(store.manifest.project_id, job,
                    attempt=status.attempt, receipt=status.receipt)
        else:
            service.advance(store, job, allow_admission=False)


def _hold_check_unknown(store, attempt):
    from .codex_exec_contracts import transition_exec_attempt
    store.repository.content_language.observe(str(attempt.project_id), attempt.job_id,
        attempt=transition_exec_attempt(attempt, state="outcome_unknown"))


@contextmanager
def _check_admission(store, request, attempt):
    from .persistence.project.autopilot_closure import material_closure
    from .persistence.schema import AutopilotRunRow
    with store.repository._lifecycle_write() as session:
        access = store.repository.content_language.access
        access.guards.active(access.rows.project(session, request.project_id))
        _current, data = store.repository.content_language.load(request.project_id, request.job_id)
        if data.get("executionCancelled"):
            raise InvalidTransitionError("原检查已取消；未发送任务。")
        run = session.get(AutopilotRunRow, str(attempt.run_id))
        if run is not None and (run.project_id != request.project_id or run.state not in {"running", "waiting"}
                or run.expected_closure != material_closure(session, request.project_id)
                or run.id in store.repository.autopilot.recovered_run_ids()):
            raise InvalidTransitionError("原自动运行已暂停、停止或来源改变；未发送语言检查。")
        from .content_language_candidates import load_generated_candidate
        original = CreativeHandoffRequest.model_validate(request.input_artifacts[CHECK_INPUT]["originalRequest"])
        retained, _candidate = load_generated_candidate(store, original.stage, original.job_id,
            request.input_artifacts[CHECK_INPUT]["candidate"])
        if retained != original:
            raise InvalidTransitionError("语言检查原始请求已变化；未发送。")
        assert_language_current(original.input_artifacts, store.project().require_brief().language)
        yield


def suspend_language_checks(store, registry, run_id):
    from .autopilot_exec import _identity
    from .content_language_persistence import check_rows, verified_check
    with store.repository._read() as session:
        attempts = [verified_check(row)[2] for row in check_rows(session, store.manifest.project_id)]
    for attempt in attempts:
        if str(attempt.run_id) != str(run_id) or attempt.state not in {"spawn_intent", "queued", "outcome_unknown"}:
            continue
        status = registry.codex_exec_suspend(attempt)
        if (status.attempt is None or _identity(status.attempt) != _identity(attempt)
                or status.state in {"queued", "spawn_intent"} and status.dispatch_enabled is not False):
            raise InvalidTransitionError("语言检查暂停未得到原任务的确切确认；保留占用。")


def _current_check_job(store, job_id):
    from .content_language_persistence import check_rows
    request, _data = store.repository.content_language.load(store.manifest.project_id, job_id)
    with store.repository._read() as session:
        for row in check_rows(session, request.project_id, request.source["candidateJobId"]):
            if row.request["source"].get("bindingHash") == request.source["bindingHash"]:
                return row.job_id
    return job_id
