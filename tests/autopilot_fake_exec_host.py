"""One deterministic host lifecycle for source-bound orchestration tests."""
import json
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecHostStatus,
    CodexExecReceipt,
    output_manifest_hash,
    transition_exec_attempt,
)
from plotloom.codex_exec_delivery import (
    publish_creative_completion,
)
from plotloom.codex_exec_files import output_evidence_for_tree
from plotloom.codex_exec_validation import (
    CodexExecTextValidationEvidence,
    CodexExecValidationStepEvidence,
    validation_plan_from_package,
)
from plotloom.creative_handoff_contracts import CREATIVE_CANDIDATE_FILENAMES, CreativeHandoffRequest
from plotloom.creative_handoff_identity import canonical_json
from plotloom.image_job_contracts import ImageJobError
from plotloom.native_bridge_intent_contract import render_native_intent_report
from plotloom.video_directions_contract import render_report as render_video_directions_report
from plotloom.native_bridge_presentation_contract import (
    render_native_presentation_report,
)
from tests.autopilot_fake_image_receipts import FakeCodexImageReceipts, _image_owner


class FakeCodexExecHost(FakeCodexImageReceipts):
    """Deterministic host receipt fixture; it never starts Codex or calls a provider."""

    def __init__(self, storage, registry, *, candidate_factory, auto_deliver=True):
        self.storage = storage
        self.candidate_factory = candidate_factory
        self.registry = registry
        self.auto_deliver = auto_deliver
        self.calls = []
        self.image_calls = []
        self.image_geometry = None
        self.statuses = {}
        self.pending = set()
        self.admissions = 0

    def admit(self, attempt):
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        key = str(attempt.attempt_id)
        retained = self.statuses.get(key)
        if retained is not None:
            return retained
        from plotloom.project_storage.project_home import find_project_home
        home = find_project_home(self.storage.projects.outputs_root, str(attempt.project_id)).path
        if attempt.domain == "text":
            job_root = home / "outputs" / "creative-handoff" / "jobs" / attempt.job_id
        else:
            matches = [
                run / "jobs" / attempt.job_id
                for run in (home / "runs").iterdir()
                if run.name.endswith("__" + attempt.job_id) and not run.is_symlink()
            ]
            if len(matches) != 1:
                raise AssertionError("fake host requires one exact frozen image job")
            job_root = matches[0]
        delivery_root = job_root / "delivery"
        delivery_root.mkdir(mode=0o700, exist_ok=True)
        if next(delivery_root.iterdir(), None) is not None:
            raise ImageJobError("delivery_conflict", "fixture host refuses pre-existing delivery bytes")
        self.admissions += 1
        process_id = 60000 + self.admissions
        running = transition_exec_attempt(
            attempt,
            state="running",
            process_id=process_id,
            process_group_id=process_id,
            process_birth_identity=f"fixture:{attempt.attempt_id}",
        )
        status = CodexExecHostStatus(state="running", attempt=running)
        self.statuses[key] = status
        self.pending.add(key)
        (self.image_calls if attempt.domain == "image" else self.calls).append(attempt.job_id)
        return status

    def status(self, attempt_id):
        key = str(attempt_id)
        retained = self.statuses.get(key)
        if retained is not None and key in self.pending and self.auto_deliver:
            self.pending.discard(key)
            attempt = retained.attempt
            with closing(self.storage.projects.open(str(attempt.project_id))) as store:
                if attempt.domain == "image":
                    from plotloom.image_commands import image_context
                    request = image_context(store, _image_owner(attempt.operation_key), attempt.job_id)
                else:
                    request = self.request(store, attempt)
                return self.complete(store, request, attempt)
        return retained or CodexExecHostStatus(state="not_found")

    def suspend(self, attempt):
        """Typed remote control stand-in; never poll, complete or dispatch."""
        from plotloom.autopilot_exec import _identity

        retained = self.statuses.get(str(attempt.attempt_id))
        if retained is None:
            return CodexExecHostStatus(state="not_found")
        if retained.attempt is None or _identity(retained.attempt) != _identity(attempt):
            raise AssertionError("fixture suspension must use the exact frozen attempt")
        if retained.state in {"queued", "spawn_intent"}:
            current = transition_exec_attempt(retained.attempt, state="queued")
            retained = CodexExecHostStatus(state="queued", attempt=current, dispatchEnabled=False)
            self.statuses[str(attempt.attempt_id)] = retained
        return retained

    def cancel(self, attempt):
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        key = str(attempt.attempt_id)
        retained = self.statuses.get(key)
        if retained is None:
            if attempt.state in {"reserved", "spawn_intent"}:
                cancelled = transition_exec_attempt(
                    attempt,
                    state="settled",
                    terminal_result="not_started",
                    remote_tool_state="not_applicable",
                    evidence_hash=sha256(
                        f"fixture:not-started:{attempt.attempt_id}".encode()
                    ).hexdigest(),
                    image_budget_state=(
                        "released" if attempt.domain == "image" else "none"
                    ),
                )
                status = CodexExecHostStatus(state="settled", attempt=cancelled)
            else:
                cancelled = transition_exec_attempt(attempt, state="outcome_unknown")
                status = CodexExecHostStatus(state="outcome_unknown", attempt=cancelled)
            self.statuses[key] = status
            return status
        if self.statuses[key].attempt is None or (
            self.statuses[key].attempt.attempt_id != attempt.attempt_id
            or self.statuses[key].attempt.run_id != attempt.run_id
            or self.statuses[key].attempt.project_id != attempt.project_id
            or self.statuses[key].attempt.job_id != attempt.job_id
            or self.statuses[key].attempt.operation_key != attempt.operation_key
        ):
            raise AssertionError("fixture cancellation must use the exact frozen attempt")
        attempt = retained.attempt
        if attempt.state in {"completed", "failed", "settled"}:
            return retained
        self.pending.discard(key)
        cancelled = transition_exec_attempt(attempt, state="cancel_requested")
        status = CodexExecHostStatus(state="cancel_requested", attempt=cancelled)
        self.statuses[key] = status
        return status

    def lose_attempt(self, attempt_id):
        key = str(attempt_id)
        status = self.statuses[key]
        unknown = transition_exec_attempt(status.attempt, state="outcome_unknown")
        status = CodexExecHostStatus(state="outcome_unknown", attempt=unknown)
        self.statuses[key] = status
        self.pending.discard(key)
        return status

    def request(self, store, attempt):
        exchange = store.creative_handoff_exchange()
        package_request = exchange.root / "jobs" / attempt.job_id / "package" / "request.json"
        payload = json.loads(package_request.read_text(encoding="utf-8"))
        allowed = {field.alias for field in CreativeHandoffRequest.model_fields.values()}
        return CreativeHandoffRequest.model_validate(
            {key: value for key, value in payload.items() if key in allowed}
        )

    def complete(self, store, request, attempt, *, value=None):
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        if attempt.domain == "image":
            return self.complete_image(store, request, attempt, output_count=1)
        profile = self.registry.codex_exec_profile()
        run = store.repository.autopilot.current(request.project_id)
        pin = store.creative_handoff_exchange().current_execution_pin(request.stage)
        paths = store.creative_handoff_exchange().write_package(
            request, pin, executor_backend="codex_exec",
            plotloom_code_revision=attempt.plotloom_code_revision,
        )
        job_root = Path(paths["packagePath"]).parent
        delivery = Path(paths["deliveryPath"])
        delivery.mkdir(exist_ok=True)
        candidate_filename = CREATIVE_CANDIDATE_FILENAMES[request.stage]
        content = canonical_json(value if value is not None else self.candidate_factory(store, request))
        report = (
            render_native_intent_report(request, json.loads(content))
            if request.stage == "bridge-intent"
            else render_native_presentation_report(request, json.loads(content))
            if request.stage == "bridge-presentation"
            else render_video_directions_report(request, json.loads(content))
            if request.stage == "video-directions"
            else b"<!doctype html><html><body>Deterministic fake Codex Exec evidence.</body></html>"
        )
        (delivery / candidate_filename).write_bytes(content)
        (delivery / "report.html").write_bytes(report)
        outputs = output_evidence_for_tree(
            job_root,
            "delivery",
            output_prefix="delivery",
            max_total_bytes=profile.max_output_bytes,
        )
        output_hash = output_manifest_hash(outputs)
        package_request = json.loads((job_root / "package" / "request.json").read_bytes())
        validation_plan = validation_plan_from_package(package_request)
        text_validation = CodexExecTextValidationEvidence(
            planHash=validation_plan.plan_hash,
            profileHash=profile.profile_hash,
            validatorHash=profile.validator_hash,
            requestHash=attempt.request_hash,
            packageHash=attempt.package_hash,
            sourceRevision=attempt.plotloom_code_revision,
            candidateFilename=candidate_filename,
            candidateHash=sha256(content).hexdigest(),
            candidateSizeBytes=len(content),
            reportFilename="report.html",
            reportHash=sha256(report).hexdigest(),
            reportSizeBytes=len(report),
            steps=(
                CodexExecValidationStepEvidence(
                    stepId="validate", argvHash="1" * 64, exitCode=0,
                    stdoutHash="2" * 64, stdoutSizeBytes=0,
                    stderrHash="3" * 64, stderrSizeBytes=0, durationMs=1,
                ),
                CodexExecValidationStepEvidence(
                    stepId="render", argvHash="4" * 64, exitCode=0,
                    stdoutHash=sha256(report).hexdigest(), stdoutSizeBytes=len(report),
                    stderrHash="5" * 64, stderrSizeBytes=0, durationMs=1,
                ),
            ),
        )
        session_id = uuid5(NAMESPACE_URL, f"plotloom-test-session:{attempt.attempt_id}")
        process_id = attempt.process_id or (40000 + len(self.calls))
        evidence_hash = sha256(
            canonical_json({"attemptId": str(attempt.attempt_id), "sessionId": str(session_id), "terminal": "turn.completed"})
        ).hexdigest()
        completed = transition_exec_attempt(
            attempt,
            state="completed",
            session_id=session_id,
            process_id=process_id,
            process_group_id=process_id,
            process_birth_identity=attempt.process_birth_identity or f"fixture:{attempt.attempt_id}",
            process_exit_code=0,
            terminal_result="success",
            remote_tool_state="not_applicable",
            evidence_hash=evidence_hash,
            output_hash=output_hash,
        )
        receipt = CodexExecReceipt(
            attemptId=completed.attempt_id,
            sessionId=session_id,
            profileHash=completed.profile_hash,
            requestHash=completed.request_hash,
            packageHash=completed.package_hash,
            plotloomCodeRevision=completed.plotloom_code_revision,
            validationPlanHash=completed.validation_plan_hash,
            processId=process_id,
            processGroupId=process_id,
            processBirthIdentity=completed.process_birth_identity,
            processExitCode=0,
            expectedImageOutputs=0,
            evidenceHash=evidence_hash,
            outputHash=output_hash,
            outputs=outputs,
            textValidation=text_validation,
            remoteToolState="not_applicable",
        )
        publish_creative_completion(
            request=request,
            execution_pin=pin,
            code_revision=completed.plotloom_code_revision,
            job_root=job_root,
            attempt=completed,
            profile=profile,
            receipt=receipt,
        )
        status = CodexExecHostStatus(state="completed", attempt=completed, receipt=receipt)
        self.statuses[str(attempt.attempt_id)] = status
        return status
