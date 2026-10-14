"""Trusted publication of CLI delivery manifests after byte validation."""
from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecProfile,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
    image_arguments_hash,
)
from .codex_exec_files import scan_regular_tree
from .codex_exec_telemetry import CodexSessionEvidence, ImageGenCall, ImageGenEvent
from .creative_handoff_contracts import (
    CreativeDeliveryManifest,
    CreativeExecutorProvenance,
    CreativeHandoffRequest,
)
from .creative_handoff_exchange import canonical_json
from .codex_exec_validation import build_text_validation_plan
from .image_job_contracts import (
    ImageDeliveryManifest,
    ImageExecutorProvenance,
    ImageJobOutput,
    ImageReferenceUse,
    ImageToolEvidence,
)
from .image_job_package import canonical_json as image_canonical_json


def _write_once_in_directory(directory: Path, filename: str, content: bytes) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(directory, flags)
    try:
        descriptor = os.open(
            filename,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=directory_fd,
        )
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def publish_creative_completion(
    *,
    request: CreativeHandoffRequest,
    execution_pin: dict[str, str],
    code_revision: str,
    job_root: Path,
    attempt: CodexExecAttempt,
    profile: CodexExecProfile,
    receipt: CodexExecReceipt,
    publish_marker: bool = True,
) -> CreativeDeliveryManifest:
    """Publish trusted executor facts after one exact candidate/report inventory."""
    try:
        assert_receipt_matches_attempt(attempt, receipt)
    except (TypeError, ValueError) as error:
        raise ValueError("Codex Exec completion requires its exact validated project attempt") from error
    if (attempt.domain != "text" or attempt.job_id != request.job_id
            or attempt.request_hash != sha256(canonical_json(request.model_dump(mode="json", by_alias=True))).hexdigest()
            or attempt.profile_hash != profile.profile_hash
            or attempt.plotloom_code_revision is None
            or code_revision != attempt.plotloom_code_revision
            or receipt.plotloom_code_revision != attempt.plotloom_code_revision):
        raise ValueError("Codex Exec completion does not match the frozen creative request or profile")
    from .creative_handoff_exchange import execution_pin_for_request
    plan = build_text_validation_plan(
        request,
        execution_pin=execution_pin_for_request(request, execution_pin),
        source_revision=code_revision,
    )
    validation = receipt.text_validation
    if (profile.contract_version != "plotloom.codex-exec.v7"
            or attempt.validation_plan_hash != plan.plan_hash
            or receipt.validation_plan_hash != plan.plan_hash
            or validation is None
            or validation.validator_hash != profile.validator_hash
            or validation.candidate_filename != plan.candidate_filename
            or validation.report_filename != plan.report_filename):
        raise ValueError("Codex Exec completion lacks exact trusted validation and renderer proof")
    delivery = job_root / "delivery"
    files = scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes)
    candidate_filename = {
        "branches": "branches.json",
        "outline": "outline.json",
        "characters": "cast.json",
        "art": "art.json",
        "script": "script.json",
        "storyboard": "storyboard.json",
        "bridge-intent": "intent.json",
        "bridge-presentation": "presentation.json",
    }[request.stage]
    expected_names = {candidate_filename, "report.html"}
    if {item.relative_path for item in files} != expected_names:
        raise ValueError("Codex Exec creative delivery must contain only its declared candidate and report")
    output_by_path = {
        item.output_relative_path: item
        for item in receipt.outputs
    }
    identities = {
        f"delivery/{item.relative_path}": item
        for item in files
    }
    if set(output_by_path) != set(identities) or any(
        output_by_path[path].output_hash != item.sha256 or output_by_path[path].size_bytes != item.size_bytes
        for path, item in identities.items()
    ):
        raise ValueError("Codex Exec receipt output inventory differs from exact delivery bytes")
    provenance = CreativeExecutorProvenance(
        codeRevision=code_revision,
        skillVersion=(
            f"plotloom-{request.stage.removeprefix('bridge-')}-specialist.v1"
            if request.stage in {"bridge-intent", "bridge-presentation"}
            else "plotloom-shuohao-specialist.v1"
        ),
        skillHash=execution_pin["specialistSkillHash"],
        upstreamRevision=execution_pin["upstreamRevision"],
        upstreamSkillHash=execution_pin["upstreamSkillHash"],
        model=profile.model,
        reasoningEffort=profile.reasoning_effort,
    )
    manifest = CreativeDeliveryManifest(
        schemaVersion=3,
        executorBackend="codex_exec",
        executorAttemptId=attempt.attempt_id,
        codexSessionId=receipt.session_id,
        executorProfileHash=profile.profile_hash,
        validationPlanHash=plan.plan_hash,
        validationEvidenceHash=validation.evidence_hash,
        jobId=request.job_id,
        requestHash=attempt.request_hash,
        deliveryId=uuid4().hex,
        stage=request.stage,
        candidate={"filename": candidate_filename, "sha256": identities[f"delivery/{candidate_filename}"].sha256},
        report={"filename": "report.html", "sha256": identities["delivery/report.html"].sha256},
        executorProvenance=provenance,
        limitations=[],
    )
    manifest.assert_secret_free()
    if publish_marker:
        _write_once_in_directory(delivery, "completion.json", canonical_json(manifest.model_dump(mode="json", by_alias=True)))
    return manifest


def publish_image_completion(
    *,
    request: dict,
    execution_pin: dict[str, str],
    job_root: Path,
    attempt: CodexExecAttempt,
    profile: CodexExecProfile,
    receipt: CodexExecReceipt,
    session: CodexSessionEvidence,
    call: ImageGenCall,
    event: ImageGenEvent,
    reference_hashes: tuple[str, ...],
    publish_marker: bool = True,
) -> ImageDeliveryManifest:
    """Publish v5 image provenance from exact source-view and built-in event evidence."""
    assert_receipt_matches_attempt(attempt, receipt)
    if (
        attempt.domain != "image"
        or attempt.job_id != request.get("jobId")
        or attempt.request_hash != request.get("requestHash")
        or attempt.profile_hash != profile.profile_hash
        or attempt.plotloom_code_revision is None
        or attempt.plotloom_code_revision != execution_pin.get("codeRevision")
        or receipt.plotloom_code_revision != attempt.plotloom_code_revision
        or attempt.reserved_image_outputs != 1
        or session.session_id != receipt.session_id
        or len(session.image_calls) != 1
        or len(session.image_events) != 1
        or session.image_calls[0] != call
        or session.image_events[0] != event
        or event.call_id != call.call_id
        or event.status != "completed"
    ):
        raise ValueError("Codex Exec image delivery does not match its exact frozen attempt and session")
    package_references = request.get("references")
    if not isinstance(package_references, list):
        raise TypeError("Codex Exec image package has no frozen reference inventory")
    expected_hashes = tuple(item.get("sha256") for item in package_references if isinstance(item, dict))
    expected_views = tuple(
        (item["role"], item["filename"], item["sha256"])
        for item in package_references
        if isinstance(item, dict) and set(item) == {"role", "filename", "sha256"}
    )
    actual_views = tuple(
        (item.role, item.package_relative_path, item.reference_hash)
        for item in receipt.reference_views
    )
    package = job_root / "package"
    session_views = tuple(
        (
            item.call_id,
            item.event_id,
            item.path,
            item.call_ordinal,
            item.event_ordinal,
            item.output_ordinal,
            item.content_sha256,
            item.content_size_bytes,
        )
        for item in session.reference_views
    )
    receipt_views = tuple(
        (
            item.call_id,
            item.event_id,
            str((package / item.package_relative_path).resolve(strict=True)),
            item.call_ordinal,
            item.event_ordinal,
            item.output_ordinal,
            item.content_sha256,
            item.content_size_bytes,
        )
        for item in receipt.reference_views
    )
    if (
        len(expected_hashes) != len(package_references)
        or len(expected_views) != len(package_references)
        or tuple(reference_hashes) != expected_hashes
        or actual_views != expected_views
        or session_views != receipt_views
    ):
        raise ValueError("actual ImageGen references differ from the exact frozen package bytes")
    image_evidence = receipt.image_evidence[0]
    expected_arguments = image_arguments_hash(
        prompt_hash=sha256(call.prompt.encode("utf-8")).hexdigest(),
        reference_hashes=reference_hashes,
        transparent_background=call.transparent_background,
        num_last_images_to_include=call.num_last_images_to_include,
    )
    if (
        image_evidence.call_id != call.call_id
        or image_evidence.call_ordinal != call.ordinal
        or image_evidence.event_id != event.event_id
        or image_evidence.arguments_hash != expected_arguments
        or image_evidence.prompt_hash != sha256(call.prompt.encode("utf-8")).hexdigest()
        or image_evidence.reference_hashes != reference_hashes
        or image_evidence.transparent_background != call.transparent_background
        or image_evidence.output_hash != receipt.outputs[0].output_hash
        or image_evidence.output_relative_path != receipt.outputs[0].output_relative_path
    ):
        raise ValueError("Codex Exec image receipt differs from observed ImageGen arguments or bytes")
    files = scan_regular_tree(job_root, "delivery", max_total_bytes=profile.max_output_bytes)
    expected_path = image_evidence.output_relative_path.removeprefix("delivery/")
    if {item.relative_path for item in files} != {expected_path}:
        raise ValueError("Codex Exec image delivery must contain only its exact generated output")
    output = files[0]
    receipt_outputs = {item.output_relative_path: item for item in receipt.outputs}
    recorded = receipt_outputs.get(f"delivery/{output.relative_path}")
    if recorded is None or (recorded.output_hash, recorded.size_bytes) != (output.sha256, output.size_bytes):
        raise ValueError("Codex Exec image receipt output inventory differs from exact delivery bytes")
    target = request.get("target")
    kind = request.get("kind")
    role = (
        "art_reference" if target == "art_reference_proposal"
        else "keyframe_adaptation" if kind == "keyframe_adaptation"
        else "refinement" if kind == "refinement"
        else "original"
    )
    reference_use = ImageReferenceUse(
        viewedReferenceHashes=[item.reference_hash for item in receipt.reference_views],
        identityNotes=(
            "The trusted host records each exact frozen package reference emitted as image content before ImageGen; "
            "this does not assert interpretation or approval."
        ),
    ) if receipt.reference_views else None
    provenance = ImageExecutorProvenance(
        codeRevision=execution_pin["codeRevision"],
        skillVersion=execution_pin["skillVersion"],
        skillHash=execution_pin["skillHash"],
        model=profile.model,
        reasoningEffort=profile.reasoning_effort,
    )
    manifest = ImageDeliveryManifest(
        schemaVersion=5,
        jobId=attempt.job_id,
        requestHash=attempt.request_hash,
        deliveryId=uuid4().hex,
        actualPrompt=call.prompt,
        outputs=[ImageJobOutput(filename=Path(expected_path).name, sha256=output.sha256, role=role)],
        toolEvidence=ImageToolEvidence(
            tool="codex_imagegen",
            executorAttemptId=attempt.attempt_id,
            codexSessionId=receipt.session_id,
            imageGenCallId=call.call_id,
            imageGenEventId=event.event_id,
            available=True,
        ),
        referenceUse=reference_use,
        executorProvenance=provenance,
        executorProfileHash=profile.profile_hash,
        limitations=[],
    )
    manifest.assert_secret_free()
    if publish_marker:
        _write_once_in_directory(job_root / "delivery", "completion.json", image_canonical_json(
            manifest.model_dump(mode="json", by_alias=True, exclude_none=True)
        ))
    return manifest
