"""Deterministic image-tool receipts for controller fixtures; never a provider."""
import json
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecHostStatus,
    CodexExecImageEvidence,
    CodexExecReceipt,
    CodexExecReferenceViewEvidence,
    image_arguments_hash,
    output_manifest_hash,
    transition_exec_attempt,
)
from plotloom.codex_exec_delivery import (
    publish_image_completion,
)
from plotloom.codex_exec_files import output_evidence_for_tree
from plotloom.codex_exec_telemetry import (
    CodexSessionEvidence,
    ImageGenCall,
    ImageGenEvent,
    ReferenceViewEvidence,
)
from plotloom.creative_handoff_identity import canonical_json


class FakeCodexImageReceipts:
    def complete_image(self, store, context, attempt, *, output_count=1, geometry=None):
        from io import BytesIO

        from PIL import Image

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
