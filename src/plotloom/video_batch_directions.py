"""One durable candidate-only job through the existing supervised Codex Exec host."""
from pathlib import Path
from uuid import uuid4
from .codex_exec_contracts import CodexExecAttempt, CodexExecProfile, CodexExecPackageFile, package_manifest_hash, assert_receipt_matches_attempt
from hashlib import sha256
from .codex_exec_runtime import frozen_package_snapshot
from .codex_exec_validation import validation_plan_from_package
from .creative_handoff_contracts import CreativeHandoffRequest
from .creative_handoff_identity import canonical_json, request_hash
from .exceptions import InvalidTransitionError
from .video_directions_contract import bind_draft, render_report


def prepare_directions(store, registry, grants, view):
    if view["state"] != "setup" or view["manifest"]["blockers"]:
        raise InvalidTransitionError("batch setup has unresolved exceptions or already owns a draft")
    registry.require_codex_exec_readiness()
    profile = CodexExecProfile.model_validate(registry.codex_exec_profile())
    exchange = store.creative_handoff_exchange()
    pin = exchange.current_execution_pin("video-directions")
    targets = [target for target in view["manifest"]["targets"] if target["mode"] == "generate"]
    request = CreativeHandoffRequest(job_id="ch_" + uuid4().hex, project_id=view["projectId"],
        section_id=view["id"], stage="video-directions", expected_stage_revision=view["revision"],
        source={"batchId": view["id"], "manifestHash": view["manifestHash"]},
        input_artifacts={"video-targets.json": {"targets": targets}},
        creative_brief="Draft complete faithful English H3 directions for every frozen target. Follow the native video-directions contract. Do not approve, dispatch, generate media or change canon.")
    if len(canonical_json(request.input_artifacts["video-targets.json"])) > 1_000_000:
        raise InvalidTransitionError("complete directions source exceeds the one-package limit; no source was truncated")
    projected, instructions, _template, _members = exchange._projection(request, pin, executor_backend="codex_exec", plotloom_code_revision=pin["upstreamRevision"])
    files = {"request.json": canonical_json(projected), "COPY_ASSIGNMENT.txt": instructions,
        **{f"inputs/{name}": canonical_json(value) for name,value in request.input_artifacts.items()}}
    package_hash = package_manifest_hash(tuple(CodexExecPackageFile(relativePath=name, sha256=sha256(content).hexdigest(), sizeBytes=len(content)) for name,content in sorted(files.items())))
    plan = validation_plan_from_package(projected)
    attempt = CodexExecAttempt(attemptId=uuid4(), runId=view["id"], projectId=view["projectId"],
        jobId=request.job_id, operationKey="video-directions", domain="text", requestHash=request_hash(request),
        packageHash=package_hash, profileHash=profile.profile_hash, plotloomCodeRevision=pin["upstreamRevision"],
        validationPlanHash=plan.plan_hash, reservedImageOutputs=0, imageBudgetState="none", state="spawn_intent")
    grants.authorize(store, "draft-" + view["id"], view["manifestHash"])
    def save(row):
        row.state = "drafting"
        row.execution = row.execution | {"draft": {"request": request.model_dump(mode="json", by_alias=True), "pin": pin,
            "profile": profile.model_dump(mode="json", by_alias=True), "attempt": attempt.model_dump(mode="json", by_alias=True),
            "grantHash": view["manifestHash"]}}
    with store.repository.manual_command() as session:
        from .persistence.project.creative_execution_pins import freeze_execution_pin
        freeze_execution_pin(session, request, pin)
        return store.repository.video_batches.change(view["projectId"], view["id"], expected_revision=view["revision"], mutate=save)


def advance_directions(store, registry, grants, view, *, allow_admission=True):
    data = view["execution"]["draft"]
    attempt = CodexExecAttempt.model_validate(data["attempt"])
    profile = CodexExecProfile.model_validate(data["profile"])
    request = CreativeHandoffRequest.model_validate(data["request"])
    if registry.codex_exec_profile() != profile:
        raise InvalidTransitionError("directions executor configuration changed; original attempt retained")
    grants.require(store, "draft-" + view["id"], data["grantHash"])
    exchange = store.creative_handoff_exchange()
    paths = exchange.write_package(request, data["pin"], executor_backend="codex_exec", plotloom_code_revision=attempt.plotloom_code_revision)
    observed_hash, _raw = frozen_package_snapshot(Path(paths["packagePath"]).parent, max_total_bytes=profile.max_output_bytes)
    if observed_hash != attempt.package_hash:
        raise InvalidTransitionError("directions package differs from its durable pre-publication identity")
    status = registry.codex_exec_status(attempt.attempt_id)
    if status.state == "not_found" and allow_admission:
        # Host admission is idempotent by the exact persisted attempt identity.
        # Reconcile only that intent, never create a replacement paid attempt.
        if attempt.state != "spawn_intent":
            raise InvalidTransitionError("directions outcome is unknown; retained attempt cannot be replaced")
        status = registry.codex_exec_admit(attempt)
    if allow_admission and status.dispatch_enabled is False:
        with store.repository.manual_command():
            current = store.repository.video_batches.current(view["projectId"])
            if current["state"] != "drafting" or current["revision"] != view["revision"]:
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
    if host_attempt == attempt and result is None:
        return view
    def save(row):
        draft = row.execution["draft"] | {"attempt": host_attempt.model_dump(mode="json", by_alias=True),
            "receipt": receipt.model_dump(mode="json", by_alias=True) if receipt else None,
            "manifestHash": delivery.manifest_hash if result is not None else data.get("manifestHash")}
        row.execution = row.execution | {"draft": draft}
        if result is not None:
            row.manifest = row.manifest | {"targets": [target | result.get(target["shotId"], {}) for target in row.manifest["targets"]]}
            if row.state == "drafting":
                row.state = "ready"
        elif host_attempt.state in {"failed", "settled", "outcome_unknown"}:
            if row.state == "drafting":
                row.state = "blocked"
            row.execution = row.execution | {"error": "英文方向任务失败或结果不确定；保留原任务，不会自动重发。"}
    return store.repository.video_batches.change(view["projectId"], view["id"], expected_revision=view["revision"], mutate=save)
