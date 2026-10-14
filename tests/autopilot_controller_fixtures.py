"""Finite fake native packages; every source gate remains the real owner."""
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from plotloom.autopilot_contracts import LaunchRequest, POLICY_VERSION
from plotloom.autopilot_service import AutopilotService
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecImageEvidence,
    CodexExecHostStatus,
    CodexExecReferenceViewEvidence,
    CodexExecReceipt,
    image_arguments_hash,
    output_manifest_hash,
    transition_exec_attempt,
)
from plotloom.codex_exec_validation import (
    CodexExecTextValidationEvidence,
    CodexExecValidationStepEvidence,
    validation_plan_from_package,
)
from plotloom.codex_exec_delivery import publish_creative_completion, publish_image_completion
from plotloom.codex_exec_files import output_evidence_for_tree
from plotloom.codex_exec_telemetry import CodexSessionEvidence, ImageGenCall, ImageGenEvent, ReferenceViewEvidence
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json
from plotloom.image_job_contracts import ImageJobError
from plotloom.native_bridge_intent_contract import render_native_intent_report
from plotloom.native_bridge_presentation_contract import render_native_presentation_report
from plotloom.project_storage import ProjectFolderStorage
from tests.cast_style_fixtures import style_fixture
from tests.creative_delivery_fixtures import _pilot_script
from tests.production_bridge_fixtures import _source_shaped_review_board
from tests.test_creator_branch_suggestions import proposal
from tests.test_native_bridge_presentation import candidate_for
from tests.test_specialist_settings import configured

FIXTURES = Path(__file__).resolve().parents[1] / "frontend/e2e/fixtures/f5a"
PIN = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}
UPSTREAM_PIN = {"upstreamRevision": "d" * 40, "upstreamSkillHash": "e" * 64, "specialistSkillHash": "f" * 64}


def candidate(store, request):
    stage = request.stage
    if stage == "outline":
        return {"source": request.source["title"], "params": {"episodes": 1}, "episodes": []}
    if stage == "branches":
        return proposal(request.source["topology"])
    if stage == "characters":
        return style_fixture(json.loads((FIXTURES / "cast.json").read_text()), request.input_artifacts["cast-style-contract.json"])
    if stage == "art":
        value = json.loads((FIXTURES / "art.json").read_text())
        value["sectionUsage"] = [{"sectionId": item["sectionId"], "sceneIds": ["S01"], "propIds": []}
            for item in request.input_artifacts["section-map.json"]["sections"]]
        return value
    if stage == "script":
        binding = store.script_state().candidate.binding
        value = _pilot_script()
        value["sectionBindings"] = [item.model_dump(mode="json", by_alias=True) for item in binding.section_bindings]
        template = value["episodes"][0]
        template["scenes"][0]["characters"] = ["keeper"]
        value["episodes"] = [dict(deepcopy(template), ep=item.episode) for item in binding.section_bindings]
        return value
    if stage == "storyboard":
        binding = store.storyboard_review_state().candidate.binding
        value = _source_shaped_review_board(episodes=[item.episode for item in binding.section_bindings])
        for episode in value["episodes"]:
            for segment in episode["segments"]:
                for cut in segment["cuts"]:
                    cut["characters"] = ["keeper"]
        return value
    if stage == "bridge-intent":
        return {"entries": [{"id": entry["id"], "suggestedText": "让角色面对不可撤回的选择，并使这一行动改变他人的下一步。"}
            for entry in request.input_artifacts["targets.json"]["entries"]]}
    return candidate_for(request)


def deliver(store, request, value=None, *, host=None):
    value = value if value is not None else candidate(store, request)
    run = store.repository.autopilot.current(request.project_id)
    if run.policy.version != POLICY_VERSION:
        raise AssertionError("fresh autopilot fixtures require the current Codex Exec launch policy")
    if host is None:
        raise AssertionError("Codex Exec delivery fixture requires its exact fake host")
    attempt, _receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, request.stage)
    if attempt is None:
        raise AssertionError("Codex Exec delivery fixture requires its persisted project attempt")
    return host.complete(store, request, attempt, value=value)


class FakeCodexExecHost:
    """Deterministic host receipt fixture; it never starts Codex or calls a provider."""

    def __init__(self, storage, registry, *, auto_deliver=True):
        self.storage = storage
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
            plotloom_code_revision=run.policy.code_revision,
        )
        job_root = Path(paths["packagePath"]).parent
        delivery = Path(paths["deliveryPath"])
        delivery.mkdir(exist_ok=True)
        candidate_filename = CreativeHandoffExchange._candidate_filename(request.stage)
        content = canonical_json(value if value is not None else candidate(store, request))
        report = (
            render_native_intent_report(request, json.loads(content))
            if request.stage == "bridge-intent"
            else render_native_presentation_report(request, json.loads(content))
            if request.stage == "bridge-presentation"
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

    def complete_image(self, store, context, attempt, *, output_count=1, geometry=None):
        from io import BytesIO
        from PIL import Image
        from plotloom.codex_exec_contracts import output_manifest_hash
        from plotloom.image_commands import image_context, image_package

        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        owner = _image_owner(attempt.operation_key)
        if "request" not in context:
            context = image_context(store, owner, attempt.job_id)
        profile = self.registry.codex_exec_profile()
        paths = image_package(store, owner, attempt.job_id)
        job_root = Path(paths["packagePath"]).parent
        package_request = json.loads((Path(paths["packagePath"]) / "request.json").read_text(encoding="utf-8"))
        delivery = Path(paths["deliveryPath"])
        output_directory = delivery / "outputs"
        output_directory.mkdir(parents=True, exist_ok=True)
        run = store.repository.autopilot.current(str(attempt.project_id))
        if geometry is None:
            geometry = self.image_geometry(context=context) if callable(self.image_geometry) else self.image_geometry
        size = geometry or (run.policy.image_width, run.policy.image_height)
        prompt = str(context["request"].get("creatorDirection", {}).get("presentationChange") or "Deterministic fixture prompt; no image generation.")
        reference_hashes = tuple(item["sha256"] for item in package_request.get("references", []))
        reference_paths = tuple(
            str(Path(paths["packagePath"]) / item["filename"])
            for item in package_request.get("references", [])
        )
        session_id = uuid5(NAMESPACE_URL, f"plotloom-test-session:{attempt.attempt_id}")
        call_id = f"fixture-call-{attempt.attempt_id.hex}"
        event_id = f"fixture-event-{attempt.attempt_id.hex}"
        image_call_ordinal = len(reference_paths) * 3 + 1
        session_views = tuple(
            ReferenceViewEvidence(
                call_id=f"fixture-view-call-{index}-{attempt.attempt_id.hex}",
                event_id=f"fixture-view-event-{index}-{attempt.attempt_id.hex}",
                path=reference_paths[index],
                call_ordinal=index * 3 + 1,
                event_ordinal=index * 3 + 2,
                output_ordinal=index * 3 + 3,
                content_sha256=sha256(reference_paths[index].encode()).hexdigest(),
                content_size_bytes=128,
            )
            for index in range(len(reference_paths))
        )
        receipt_views = tuple(
            CodexExecReferenceViewEvidence(
                role=reference["role"],
                packageRelativePath=reference["filename"],
                referenceHash=reference["sha256"],
                contentSha256=session_views[index].content_sha256,
                contentSizeBytes=session_views[index].content_size_bytes,
                callId=session_views[index].call_id,
                eventId=session_views[index].event_id,
                callOrdinal=session_views[index].call_ordinal,
                eventOrdinal=session_views[index].event_ordinal,
                outputOrdinal=session_views[index].output_ordinal,
            )
            for index, reference in enumerate(package_request.get("references", []))
        )
        call = ImageGenCall(
            call_id=call_id,
            prompt=prompt,
            reference_paths=reference_paths,
            transparent_background=False,
            num_last_images_to_include=None,
            ordinal=image_call_ordinal,
        )
        filenames = []
        for index in range(output_count):
            buffer = BytesIO()
            Image.new("RGB", size, (110 + index, 80, 120)).save(buffer, format="PNG")
            filename = f"fixture-{index}.png"
            (output_directory / filename).write_bytes(buffer.getvalue())
            filenames.append(filename)
        output_evidence = output_evidence_for_tree(
            job_root, "delivery", output_prefix="delivery", max_total_bytes=profile.max_output_bytes
        )
        output_hash = output_manifest_hash(output_evidence)
        evidence_hash = sha256(canonical_json({
            "attemptId": str(attempt.attempt_id),
            "sessionId": str(session_id),
            "eventId": event_id,
            "outputHash": output_hash,
            "terminal": "turn.completed",
        })).hexdigest()
        process_id = attempt.process_id or (50000 + len(self.calls) + len(self.image_calls))
        common_changes = {
            "session_id": session_id,
            "process_id": process_id,
            "process_group_id": process_id,
            "process_birth_identity": attempt.process_birth_identity or f"fixture:{attempt.attempt_id}",
            "process_exit_code": 0,
            "remote_tool_state": "completed",
            "evidence_hash": evidence_hash,
            "output_hash": output_hash,
            "remote_output_hash": output_evidence[0].output_hash if output_count else None,
            "image_budget_state": "consumed",
        }
        if output_count != 1:
            failed = transition_exec_attempt(
                attempt, state="failed", terminal_result="failure", **common_changes
            )
            status = CodexExecHostStatus(state="failed", attempt=failed)
            self.statuses[str(attempt.attempt_id)] = status
            return status

        output = output_evidence[0]
        event = ImageGenEvent(
            call_id=call_id,
            event_id=event_id,
            status="completed",
            saved_path=f"/private/fixture/{session_id}/{event_id}.png",
            transparent_background=False,
            ordinal=image_call_ordinal + 1,
        )
        prompt_hash = sha256(prompt.encode("utf-8")).hexdigest()
        argument_hash = image_arguments_hash(
            prompt_hash=prompt_hash,
            reference_hashes=reference_hashes,
            transparent_background=False,
            num_last_images_to_include=None,
        )
        image_evidence = CodexExecImageEvidence(
            attemptId=attempt.attempt_id,
            sessionId=session_id,
            callId=call_id,
            callOrdinal=call.ordinal,
            eventId=event_id,
            eventType="image_gen.generation",
            eventStatus="completed",
            argumentsHash=argument_hash,
            promptHash=prompt_hash,
            referenceHashes=reference_hashes,
            transparentBackground=False,
            outputHash=output.output_hash,
            outputRelativePath=output.output_relative_path,
        )
        completed = transition_exec_attempt(
            attempt, state="completed", terminal_result="success", **common_changes
        )
        receipt = CodexExecReceipt(
            attemptId=completed.attempt_id,
            sessionId=session_id,
            profileHash=completed.profile_hash,
            requestHash=completed.request_hash,
            packageHash=completed.package_hash,
            plotloomCodeRevision=completed.plotloom_code_revision,
            processId=process_id,
            processGroupId=process_id,
            processBirthIdentity=completed.process_birth_identity,
            processExitCode=0,
            expectedImageOutputs=1,
            evidenceHash=evidence_hash,
            outputHash=output_hash,
            outputs=output_evidence,
            imageEvidence=(image_evidence,),
            referenceViews=receipt_views,
            remoteOutputHash=completed.remote_output_hash,
            remoteToolState="completed",
        )
        transcript = canonical_json({"attemptId": str(attempt.attempt_id), "sessionId": str(session_id), "eventId": event_id})
        session = CodexSessionEvidence(
            session_id=session_id,
            image_calls=(call,),
            image_events=(event,),
            transcript_sha256=sha256(transcript).hexdigest(),
            transcript_size_bytes=len(transcript),
            reference_views=session_views,
        )
        publish_image_completion(
            request=package_request,
            execution_pin=package_request["specialistPreflight"],
            job_root=job_root,
            attempt=completed,
            profile=profile,
            receipt=receipt,
            session=session,
            call=call,
            event=event,
            reference_hashes=reference_hashes,
        )
        status = CodexExecHostStatus(state="completed", attempt=completed, receipt=receipt)
        self.statuses[str(attempt.attempt_id)] = status
        self.pending.discard(str(attempt.attempt_id))
        return status


def _image_owner(operation_key):
    """Image attempt keys extend owner names with frozen subject identity."""
    return operation_key.split(":", 1)[0]


def environment(tmp_path, monkeypatch, *, auto_deliver=True, brief=None, limits=None):
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    selected = brief or FIXED_CHINESE_BRIEF.model_copy(update={
        "decision_points_per_path": 1, "ending_count": 2, "desired_join_count": 0})
    with closing(storage.projects.create(selected)) as store:
        project_id = store.manifest.project_id
    registry, _settings = configured(storage.application.root)
    from tests.codex_exec_fixtures import install_profile
    install_profile(registry)
    monkeypatch.setattr(
        CreativeHandoffExchange,
        "current_execution_pin",
        lambda _self, stage: PIN if stage in {"bridge-intent", "bridge-presentation"} else UPSTREAM_PIN,
    )
    host = FakeCodexExecHost(storage, registry, auto_deliver=auto_deliver)
    registry.codex_exec_admit = host.admit
    registry.codex_exec_status = host.status
    registry.codex_exec_cancel = host.cancel
    registry._codex_exec_test_host = host
    service = AutopilotService(storage, registry)
    request = LaunchRequest(expected_brief_revision=1, render_style="realistic", art_render_style="realistic", **(limits or {}))
    view = service.launch(project_id, request)
    return storage, registry, service, view, host.calls


def run_text(service, view, *, steps=40):
    assert service.acquire_controller()
    for _ in range(steps):
        service.step(view.project_id)
        with closing(service.storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
        if any(item["operationKey"] == "installation" for item in current.checkpoints):
            return current
        assert current.state in {"running", "waiting"}, current.blocker
    raise AssertionError("bounded fake text path did not reach installation")
