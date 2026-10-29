"""One durable candidate-only job through the existing supervised Codex Exec host."""
from contextlib import nullcontext
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecHostStatus,
    transition_exec_attempt,
    CodexExecPackageFile,
    CodexExecProfile,
    assert_receipt_matches_attempt,
    package_manifest_hash,
)
from .codex_exec_runtime import frozen_package_snapshot
from .codex_exec_validation import validation_plan_from_package
from .creative_exchange_files import creative_job_root
from .creative_handoff_contracts import CreativeHandoffRequest
from .creative_handoff_identity import canonical_json, request_hash
from .creative_package_projection import project_creative_package
from .exceptions import InvalidTransitionError
from .language_policy import LANGUAGE_CONTRACT_FILENAME
from .persistence.codec import stable_hash
from .video_directions_contract import bind_draft, render_report
from .video_fidelity import fidelity_reference


def prepare_directions(store, registry, grants, view, *, checking=False, retrying=False, manual_command_id=None, command_session=None):
    if view["manifest"]["blockers"] or view["execution"].get("authorizedManifestHash"):
        raise InvalidTransitionError("制作来源有冲突或已经授权；不能重新准备指令。")
    key = "fidelity" if checking else "draft"
    if not checking and view["state"] != "setup" and not retrying:
        raise InvalidTransitionError("only initial setup can create a drafting attempt")
    previous = view["execution"].get(key)
    if previous and previous["attempt"]["state"] not in {"completed", "failed", "settled"} and not retrying:
        return view
    registry.require_codex_exec_readiness()
    if retrying:
        store.require_recovery_acknowledged()
        if previous:
            grants.require(store, previous.get("grantId", "draft-" + view["id"]), previous["grantHash"])
        from .generation_retry_policy import repeatable_failure
        if (not previous or not previous.get("localExecutionStopped")
                or not repeatable_failure(CodexExecAttempt.model_validate(previous["attempt"]))):
            raise InvalidTransitionError("directions retry requires the exact stopped repeatable predecessor")
        used = previous.get("retry", {}).get("automaticRetriesUsed", 0)
        if not manual_command_id and used >= view["manifest"]["setup"].get("automaticRetryLimit", 0):
            raise InvalidTransitionError("directions automatic retry allowance is exhausted")
    profile = CodexExecProfile.model_validate(registry.codex_exec_profile())
    exchange = store.creative_handoff_exchange()
    pin = exchange.current_execution_pin("video-directions")
    if retrying and (previous["pin"] != pin or previous["profile"] != profile.model_dump(mode="json", by_alias=True)):
        raise InvalidTransitionError("directions retry execution pin or profile changed")
    targets = [target for target in view["manifest"]["targets"] if target["mode"] == "generate"]
    if checking and any(target["directions"] is None for target in targets):
        raise InvalidTransitionError("完整英文候选尚未准备。")
    frozen = [{key: value for key, value in target.items() if key not in {"productionBrief", "fidelity"}}
        for target in targets]
    if checking:
        frozen = [target | {"directions": {key: target["directions"][key] for key in ("sourceHash", "fields")}} for target in frozen]
    binding = stable_hash([{key: item[key] for key in ("shotId", "sourceHash", "directions", "compiledPrompt")} for item in frozen])
    if retrying and binding != previous["candidateBinding"]:
        raise InvalidTransitionError("directions retry candidate or source changed")
    if checking and previous and previous.get("candidateBinding") == binding and previous.get("result"):
        return view
    language = (frozen[0]["snapshot"]["languageContract"] if frozen else view["manifest"]["languageContract"])
    source = {"batchId": view["id"], "manifestHash": view["manifestHash"],
        "operation": "fidelity-check" if checking else "draft", "candidateBinding": binding}
    if retrying:
        source |= {"predecessorJobId": previous["request"]["jobId"], "predecessorAttemptId": previous["attempt"]["attemptId"]}
    if manual_command_id:
        source["manualCommandId"] = str(manual_command_id)
    if checking and view["execution"].get("draft") and not view["execution"].get("candidateEdited"):
        source["draftAttemptId"] = view["execution"]["draft"]["attempt"]["attemptId"]
    request = CreativeHandoffRequest(job_id="ch_" + uuid4().hex, project_id=view["projectId"],
        section_id=view["id"], stage="video-directions", expected_stage_revision=view["revision"],
        source=source, input_artifacts={"video-targets.json": {"targets": frozen}, LANGUAGE_CONTRACT_FILENAME: language},
        creative_brief=("Independently compare every original source, complete English candidate and exact compiled H3 prompt. "
            "Check all semantic dimensions and report actionable omissions, changed negation, invented actions/speech/text/sound, identity, position and unsupported requirements. "
            "Return the typed fidelity verdict; do not edit the candidate, approve creativity, authorize generation or dispatch media."
            if checking else "Draft complete faithful English H3 directions for every frozen target. Follow the native video-directions contract. Do not approve, dispatch, generate media or change canon."))
    if len(canonical_json(request.input_artifacts["video-targets.json"])) > 1_000_000:
        raise InvalidTransitionError("complete directions source exceeds the one-package limit; no source was truncated")
    projected, instructions, _template, _members = project_creative_package(creative_job_root(exchange.root, request.job_id), request, pin, executor_backend="codex_exec", plotloom_code_revision=pin["upstreamRevision"])
    files = {"request.json": canonical_json(projected), "COPY_ASSIGNMENT.txt": instructions,
        **{f"inputs/{name}": canonical_json(value) for name,value in request.input_artifacts.items()}}
    package_hash = package_manifest_hash(tuple(CodexExecPackageFile(relativePath=name, sha256=sha256(content).hexdigest(), sizeBytes=len(content)) for name,content in sorted(files.items())))
    plan = validation_plan_from_package(projected)
    attempt = CodexExecAttempt(attemptId=uuid4(), runId=view["id"], projectId=view["projectId"],
        jobId=request.job_id, operationKey="video-directions", domain="text", requestHash=request_hash(request),
        packageHash=package_hash, profileHash=profile.profile_hash, plotloomCodeRevision=pin["upstreamRevision"],
        validationPlanHash=plan.plan_hash, reservedImageOutputs=0, imageBudgetState="none", state="spawn_intent")
    grant_id = key + "-" + request.job_id
    grants.authorize(store, grant_id, binding)
    def save(row):
        row.state = "checking" if checking else "drafting"
        from .generation_retry_policy import retry_status
        prior_jobs = [*previous.get("retry", {}).get("predecessorJobIds", []), previous["request"]["jobId"]] if retrying else []
        data = {"retry": retry_status(limit=view["manifest"]["setup"].get("automaticRetryLimit", 0),
                    current_job_id=request.job_id, current_attempt_id=str(attempt.attempt_id), predecessors=prior_jobs,
                    automatic_used=previous.get("retry",{}).get("automaticRetriesUsed",len(prior_jobs)-1) + (0 if manual_command_id else 1) if retrying else 0),
            "request": request.model_dump(mode="json", by_alias=True), "pin": pin,
            "profile": profile.model_dump(mode="json", by_alias=True), "attempt": attempt.model_dump(mode="json", by_alias=True),
            "grantHash": binding, "grantId": grant_id, "candidateBinding": binding}
        history = row.execution.get(key + "History", [])
        if previous:
            history = [*history, previous]
        row.execution = row.execution | {key: data, key + "History": history, "error": None}
    with (nullcontext(command_session) if command_session is not None else store.repository.manual_command()) as session:
        from .persistence.project.creative_execution_pins import freeze_execution_pin
        freeze_execution_pin(session, request, pin)
        return store.repository.video_batches.change(view["projectId"], view["id"], expected_revision=view["revision"], mutate=save)


def advance_directions(store, registry, grants, view, *, allow_admission=True, checking=False):
    key = "fidelity" if checking else "draft"
    data = view["execution"][key]
    if data.get("result") and data["attempt"]["state"] == "completed":
        return view
    attempt = CodexExecAttempt.model_validate(data["attempt"])
    profile = CodexExecProfile.model_validate(data["profile"])
    request = CreativeHandoffRequest.model_validate(data["request"])
    if registry.codex_exec_profile() != profile:
        raise InvalidTransitionError("directions executor configuration changed; original attempt retained")
    grants.require(store, data.get("grantId", "draft-" + view["id"]), data["grantHash"])
    exchange = store.creative_handoff_exchange()
    paths = exchange.write_package(request, data["pin"], executor_backend="codex_exec", plotloom_code_revision=attempt.plotloom_code_revision)
    observed_hash, _raw = frozen_package_snapshot(Path(paths["packagePath"]).parent, max_total_bytes=profile.max_output_bytes)
    if observed_hash != attempt.package_hash:
        raise InvalidTransitionError("directions package differs from its durable pre-publication identity")
    status = registry.codex_exec_status(attempt.attempt_id)
    if status.state == "not_found" and allow_admission:
        if attempt.state != "spawn_intent":
            return view
        if data.get("admissionAttempted") and not data.get("admissionDeferred"):
            status = CodexExecHostStatus(state="outcome_unknown", attempt=transition_exec_attempt(attempt, state="outcome_unknown"))
        else:
            def mark_admission(row):
                row.execution = row.execution | {key: row.execution[key] | {"admissionAttempted": True, "admissionDeferred": False}}
            view = store.repository.video_batches.change(view["projectId"], view["id"], expected_revision=view["revision"], mutate=mark_admission)
            data = view["execution"][key]
            try:
                status = registry.codex_exec_admit(attempt)
            except Exception:
                def mark_unknown(row):
                    row.execution = row.execution | {key: row.execution[key] | {"attempt": transition_exec_attempt(attempt, state="outcome_unknown").model_dump(mode="json", by_alias=True)}}
                store.repository.video_batches.change(view["projectId"], view["id"], expected_revision=view["revision"], mutate=mark_unknown)
                raise
            if status.state == "not_found":
                if status.capacity_deferred:
                    def mark_deferred(row):
                        row.execution = row.execution | {key: row.execution[key] | {"admissionDeferred": True}}
                    return store.repository.video_batches.change(view["projectId"], view["id"], expected_revision=view["revision"], mutate=mark_deferred)
                status = CodexExecHostStatus(state="outcome_unknown", attempt=transition_exec_attempt(attempt, state="outcome_unknown"))
    if allow_admission and status.dispatch_enabled is False and attempt.state != "outcome_unknown":
        with store.repository.manual_command():
            current = store.repository.video_batches.current(view["projectId"])
            if current["state"] != ("checking" if checking else "drafting") or current["revision"] != view["revision"]:
                return view
            status = registry.codex_exec_resume(attempt)
    if status.state == "not_found" or status.attempt is None:
        return view
    immutable = ("attempt_id", "run_id", "project_id", "job_id", "request_hash", "package_hash", "profile_hash", "plotloom_code_revision", "validation_plan_hash")
    if any(getattr(attempt,key) != getattr(status.attempt,key) for key in immutable):
        raise InvalidTransitionError("host returned a different directions attempt")
    host_attempt = status.attempt
    receipt = status.receipt
    if receipt:
        assert_receipt_matches_attempt(host_attempt, receipt)
    result = None
    if receipt and host_attempt.state == "completed":
        delivery = store.creative_handoff_exchange().read_delivery(request, data["pin"], executor_backend="codex_exec",
            executor_attempt=host_attempt, executor_profile=profile, executor_receipt=receipt,
            plotloom_code_revision=attempt.plotloom_code_revision)
        if delivery is None:
            raise InvalidTransitionError("completed directions attempt has no verified delivery")
        result = bind_draft(request, delivery.candidate)
        if render_report(request, delivery.candidate) != delivery.report:
            raise InvalidTransitionError("directions report differs from trusted rendering")
    if host_attempt == attempt and result is None and data.get("localExecutionStopped",False) == status.local_execution_stopped:
        return view
    def save(row):
        from .generation_retry_policy import repeatable_failure, retry_status
        prior_retry = data.get("retry", {})
        public_retry = retry_status(limit=prior_retry.get("automaticRetryLimit"), current_job_id=attempt.job_id,
            current_attempt_id=str(attempt.attempt_id), predecessors=prior_retry.get("predecessorJobIds", []),
            automatic_used=prior_retry.get("automaticRetriesUsed",prior_retry.get("retryCount",0)),
            state="stopped" if host_attempt.state in {"failed", "settled", "outcome_unknown"} and (not status.local_execution_stopped or not repeatable_failure(host_attempt)) else
                  "retry_pending" if host_attempt.state in {"failed","outcome_unknown"} and
                  prior_retry.get("automaticRetriesUsed", prior_retry.get("retryCount",0)) < prior_retry.get("automaticRetryLimit",0) else
                  "exhausted" if host_attempt.state in {"failed","outcome_unknown"} else "running",
            possible_cost=host_attempt.state == "outcome_unknown" or bool(prior_retry.get("predecessorJobIds")))
        draft = row.execution[key] | {"retry": public_retry, "localExecutionStopped":status.local_execution_stopped, "attempt": host_attempt.model_dump(mode="json", by_alias=True),
            "receipt": receipt.model_dump(mode="json", by_alias=True) if receipt else None,
            "manifestHash": delivery.manifest_hash if result is not None else data.get("manifestHash")}
        if result is not None:
            draft |= {"result": delivery.candidate, "responseHash": sha256(canonical_json(delivery.candidate)).hexdigest(),
                "deliveryCandidateHash": delivery.manifest.candidate.sha256}
        row.execution = row.execution | {key: draft}
        if result is not None:
            if checking:
                reference = fidelity_reference(row.id, draft, delivery.candidate)
                row.manifest = row.manifest | {"targets": [target | ({"fidelity": result[target["shotId"]],
                    "directions": target["directions"] | {"fidelityCheck": reference}}
                    if target["shotId"] in result else {}) for target in row.manifest["targets"]]}
                passed = all(item["verdict"] == "pass" for item in result.values())
                if row.state == "checking":
                    row.state = "ready" if passed else "translation_rejected"
                if not passed:
                    row.execution = row.execution | {"error": "助手保真检查未通过；请修正列出的来源或英文候选后重新检查。未发送视频。"}
            else:
                row.manifest = row.manifest | {"targets": [target | result.get(target["shotId"], {}) for target in row.manifest["targets"]]}
                if row.state == "drafting":
                    row.state = "checking"
        elif host_attempt.state in {"failed", "settled", "outcome_unknown"}:
            if row.state in {"drafting", "checking"} and status.local_execution_stopped:
                row.state = "blocked"
            row.execution = row.execution | {"error": "指令任务失败或结果不确定；原尝试与可能费用保留，按已冻结的重试上限处理。"}
    updated = store.repository.video_batches.change(view["projectId"], view["id"], expected_revision=view["revision"], mutate=save)
    from .generation_retry_policy import repeatable_failure
    retry = data.get("retry", {})
    if (allow_admission and status.local_execution_stopped and repeatable_failure(host_attempt)
            and retry.get("automaticRetriesUsed",retry.get("retryCount",0)) < retry.get("automaticRetryLimit", 0)):
        return prepare_directions(store, registry, grants, updated, checking=checking, retrying=True)
    return updated
