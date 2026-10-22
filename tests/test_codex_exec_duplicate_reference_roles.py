"""Same pixels in distinct roles retain every exact host view and argument."""
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from plotloom.codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecImageEvidence,
    CodexExecOutputEvidence,
    CodexExecReceipt,
    CodexExecReferenceViewEvidence,
    image_arguments_hash,
    output_manifest_hash,
    transition_exec_attempt,
)
from plotloom.codex_exec_delivery import publish_image_completion
from plotloom.codex_exec_telemetry import read_cli_session
from plotloom.image_job_contracts import ImageJobError
from plotloom.image_job_exchange import ImageJobExchange
from plotloom.managed_media import ManagedMediaLimits
from tests.codex_exec_fixtures import PROFILE
from tests.project_folder_image_delivery_fixtures import png
from tests.test_codex_exec_telemetry import (
    SESSION_ID,
    _extension,
    _image_call,
    _image_view_event,
    _inline_image_output,
    _session_bytes,
    _view_call,
)


def duplicate_role_delivery(tmp_path):
    root, job_id = tmp_path / "exchange", "ij_" + "a" * 32
    job_root = root / "jobs" / job_id
    package = job_root / "package"
    (package / "references").mkdir(parents=True)
    content = png((20, 30, 40))
    digest = sha256(content).hexdigest()
    references = [
        {"role": "character_identity:person", "filename": "references/identity.png", "sha256": digest},
        {"role": "scene_continuity", "filename": "references/continuity.png", "sha256": digest},
    ]
    paths = tuple(str(package / item["filename"]) for item in references)
    for path in (package / item["filename"] for item in references):
        path.write_bytes(content)
    rollout = tmp_path / "rollout.jsonl"
    rollout.write_bytes(_session_bytes(
        _view_call(paths[0], "view-one", ordinal=1),
        _image_view_event(Path(paths[0]).as_uri(), event_id="event-one", ordinal=2),
        _inline_image_output("view-one", ordinal=3),
        _view_call(paths[1], "view-two", ordinal=4),
        _image_view_event(Path(paths[1]).as_uri(), event_id="event-two", ordinal=5),
        _inline_image_output("view-two", ordinal=6),
        _image_call(references=paths, ordinal=7),
        _extension("completed", ordinal=8),
    ))
    session = read_cli_session(rollout, SESSION_ID, max_event_bytes=4096, max_total_bytes=32_768)
    call, event = session.image_calls[0], session.image_events[0]
    assert call.reference_paths == paths
    assert [item.path for item in session.reference_views] == list(paths)
    output_path = job_root / "delivery" / "outputs" / "frame.png"
    output_path.parent.mkdir(parents=True)
    output_path.write_bytes(content)
    output = CodexExecOutputEvidence(outputHash=digest, outputRelativePath="delivery/outputs/frame.png", sizeBytes=len(content))
    request_hash, package_hash, code_revision = "b" * 64, "c" * 64, "d" * 40
    pin = {"codeRevision": code_revision, "skillVersion": "plotloom-image-specialist.v4", "skillHash": "e" * 64}
    attempt = CodexExecAttempt(attemptId=uuid4(), runId=uuid4(), projectId=uuid4(), jobId=job_id,
        operationKey="image:B", domain="image", requestHash=request_hash, packageHash=package_hash,
        profileHash=PROFILE.profile_hash, plotloomCodeRevision=code_revision,
        reservedImageOutputs=1, imageBudgetState="reserved", state="spawn_intent")
    hashes = (digest, digest)
    evidence = CodexExecImageEvidence(attemptId=attempt.attempt_id, sessionId=SESSION_ID,
        callId=call.call_id, callOrdinal=call.ordinal, eventId=event.event_id,
        eventType="image_gen.generation", eventStatus="completed", promptHash=sha256(call.prompt.encode()).hexdigest(),
        argumentsHash=image_arguments_hash(prompt_hash=sha256(call.prompt.encode()).hexdigest(), reference_hashes=hashes,
            transparent_background=False, num_last_images_to_include=None),
        referenceHashes=hashes, transparentBackground=False, outputHash=digest, outputRelativePath=output.output_relative_path)
    views = tuple(CodexExecReferenceViewEvidence(role=reference["role"], packageRelativePath=reference["filename"],
        referenceHash=digest, contentSha256=view.content_sha256, contentSizeBytes=view.content_size_bytes,
        callId=view.call_id, eventId=view.event_id, callOrdinal=view.call_ordinal,
        eventOrdinal=view.event_ordinal, outputOrdinal=view.output_ordinal)
        for reference, view in zip(references, session.reference_views, strict=True))
    attempt = transition_exec_attempt(attempt, state="completed", terminal_result="success", session_id=SESSION_ID,
        process_id=321, process_group_id=321, process_birth_identity="fixture-process", process_exit_code=0,
        evidence_hash="f" * 64, output_hash=output_manifest_hash((output,)), remote_output_hash=digest,
        image_budget_state="consumed", remote_tool_state="completed")
    receipt = CodexExecReceipt(attemptId=attempt.attempt_id, sessionId=SESSION_ID, profileHash=PROFILE.profile_hash,
        requestHash=request_hash, packageHash=package_hash, plotloomCodeRevision=code_revision,
        processId=321, processGroupId=321, processBirthIdentity="fixture-process", processExitCode=0,
        expectedImageOutputs=1, evidenceHash="f" * 64, outputHash=attempt.output_hash,
        outputs=(output,), imageEvidence=(evidence,), referenceViews=views,
        remoteOutputHash=digest, remoteToolState="completed")
    request = {"jobId": job_id, "requestHash": request_hash, "kind": "original", "references": references}
    publish = {"request": request, "execution_pin": pin, "job_root": job_root, "attempt": attempt, "profile": PROFILE,
        "receipt": receipt, "session": session, "call": call, "event": event, "reference_hashes": hashes}
    ingest = {"job_id": job_id, "request_hash": request_hash, "expected_executor_contract": "codex_exec.v1",
        "expected_codex_attempt": attempt, "expected_codex_profile": PROFILE, "expected_codex_receipt": receipt,
        "expected_codex_references": tuple((item["role"], item["filename"].removeprefix("references/"), digest) for item in references),
        "expected_codex_execution_pin": pin, "expected_codex_output_role": "original", "required_reference_hashes": hashes}
    return ImageJobExchange(root, limits=ManagedMediaLimits()), publish, ingest


def test_same_bytes_distinct_roles_survive_telemetry_trusted_publication_and_ingestion(tmp_path):
    exchange, arguments, ingest = duplicate_role_delivery(tmp_path)
    manifest = publish_image_completion(**arguments)
    receipt = arguments["receipt"]
    assert len(receipt.reference_views) == 2
    assert receipt.image_evidence[0].reference_hashes == arguments["reference_hashes"]
    assert manifest.reference_use.viewed_reference_hashes == [arguments["reference_hashes"][0]]
    delivery = exchange.read_delivery(**ingest)
    assert delivery is not None and delivery.manifest.canonical_payload() == manifest.canonical_payload()


@pytest.mark.parametrize("defect", ["path", "call", "event", "ordinal", "order"])
def test_identical_bytes_never_waive_unique_view_identity_or_order(tmp_path, defect):
    _exchange, arguments, _ingest = duplicate_role_delivery(tmp_path)
    receipt = arguments["receipt"]
    views = list(receipt.reference_views)
    fields = {"path": "package_relative_path", "call": "call_id", "event": "event_id", "ordinal": "call_ordinal"}
    if defect == "order":
        views.reverse()
    else:
        field = fields[defect]
        views[1] = views[1].model_copy(update={field: getattr(views[0], field)})
    with pytest.raises(ValidationError, match="unique and ordered"):
        CodexExecReceipt.model_validate(receipt.model_dump(mode="python") | {"reference_views": views})


def test_duplicate_hashes_do_not_hide_changed_role_path_inventory(tmp_path):
    exchange, arguments, ingest = duplicate_role_delivery(tmp_path)
    references = arguments["request"]["references"]
    forged = arguments["request"] | {"references": list(reversed(references))}
    with pytest.raises(ValueError, match="exact frozen package bytes"):
        publish_image_completion(**(arguments | {"request": forged}))
    publish_image_completion(**arguments)
    with pytest.raises(ImageJobError, match="exact Codex Exec attempt"):
        exchange.read_delivery(**(ingest | {"expected_codex_references": tuple(reversed(ingest["expected_codex_references"]))}))
