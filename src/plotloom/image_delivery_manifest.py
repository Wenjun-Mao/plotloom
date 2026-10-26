"""Pure assertions over trusted image attempts, manifests and executor pins."""
from __future__ import annotations
from hashlib import sha256
from uuid import UUID
from pydantic import ValidationError
from .codex_exec_contracts import CodexExecAttempt, CodexExecProfile, CodexExecReceipt, assert_receipt_matches_attempt
from .image_job_contracts import ImageDeliveryManifest, ImageExecutorProvenance, ImageJobError, NativeTaskBinding


def _validate_codex_exec_delivery(
    manifest: ImageDeliveryManifest,
    *,
    job_id: str,
    request_hash: str,
    expected_references: tuple[tuple[str, str, str], ...],
    required_identity_hashes: tuple[str, ...],
    execution_pin: dict[str, str] | None,
    expected_output_role: str | None,
    attempt: CodexExecAttempt | None,
    profile: CodexExecProfile | None,
    receipt: CodexExecReceipt | None,
) -> None:
    expected_package_views = tuple(
        (role, f"references/{filename}", reference_hash)
        for role, filename, reference_hash in expected_references
    )
    if attempt is None or profile is None or receipt is None:
        raise ImageJobError("delivery_executor_evidence_missing", "Codex Exec image delivery requires its exact project attempt and host receipt")
    try:
        assert_receipt_matches_attempt(attempt, receipt)
    except (TypeError, ValueError) as error:
        raise ImageJobError("delivery_executor_evidence_invalid", "Codex Exec image receipt is invalid") from error
    tool = manifest.tool_evidence
    if (
        manifest.schema_version != 5
        or attempt.domain != "image"
        or attempt.job_id != job_id
        or attempt.request_hash != request_hash
        or attempt.profile_hash != profile.profile_hash
        or attempt.plotloom_code_revision != (execution_pin or {}).get("codeRevision")
        or manifest.executor_profile_hash != profile.profile_hash
        or tool.executor_attempt_id != attempt.attempt_id
        or tool.codex_session_id != receipt.session_id
        or receipt.expected_image_outputs != 1
        or len(receipt.image_evidence) != 1
        or tool.image_gen_call_id != receipt.image_evidence[0].call_id
        or tool.image_gen_event_id != receipt.image_evidence[0].event_id
        or manifest.actual_prompt == ""
        or sha256(manifest.actual_prompt.encode("utf-8")).hexdigest()
            != receipt.image_evidence[0].prompt_hash
        or receipt.image_evidence[0].reference_hashes != tuple(item[2] for item in expected_references)
        or tuple((item.role, item.package_relative_path, item.reference_hash) for item in receipt.reference_views)
            != expected_package_views
        or ((manifest.reference_use is not None) != bool(expected_references))
        or (manifest.reference_use is not None and
            manifest.reference_use.viewed_reference_hashes != list(dict.fromkeys(item[2] for item in expected_references)))
        or manifest.executor_provenance is None
        or manifest.executor_provenance.model != profile.model
        or manifest.executor_provenance.reasoning_effort != profile.reasoning_effort
        or execution_pin is None
        or manifest.executor_provenance.code_revision != execution_pin.get("codeRevision")
        or manifest.executor_provenance.skill_version != execution_pin.get("skillVersion")
        or manifest.executor_provenance.skill_hash != execution_pin.get("skillHash")
        or not set(required_identity_hashes) <= {item[2] for item in expected_references}
    ):
        raise ImageJobError("delivery_execution_mismatch", "image delivery differs from its exact Codex Exec attempt, profile or host receipt")
    event = receipt.image_evidence[0]
    if len(manifest.outputs) != 1 or (
        manifest.outputs[0].filename != event.output_relative_path.rsplit("/", 1)[-1]
        or manifest.outputs[0].sha256 != event.output_hash
        or manifest.outputs[0].role != expected_output_role
    ):
        raise ImageJobError("delivery_executor_evidence_invalid", "image output differs from the exact Codex Exec event bytes")

def validated_executor_pin(
    pin, *, job_id: str, request_hash: str,
    expected_skill_version: str | None,
    expected_execution_contract: str = "codex_specialist.v2",
) -> dict[str, str]:
    """Validate the narrow v4 pre-generation marker before accepting waiting."""

    expected_keys = {
        "jobId", "requestHash", "executionContract", "skillVersion",
        "codeRevision", "skillHash",
    }
    if expected_execution_contract == "codex_specialist.v3":
        expected_keys.add("nativeTaskId")
    if not isinstance(pin, dict) or set(pin) != expected_keys:
        raise ImageJobError("delivery_executor_pin_invalid", "executor pin has an unsupported shape")
    if pin.get("jobId") != job_id or pin.get("requestHash") != request_hash:
        raise ImageJobError("delivery_executor_pin_mismatch", "executor pin does not belong to this frozen image job")
    if pin.get("executionContract") != expected_execution_contract:
        raise ImageJobError("delivery_executor_pin_invalid", "executor pin has an unsupported execution contract")
    if expected_skill_version is not None and pin.get("skillVersion") != expected_skill_version:
        raise ImageJobError("delivery_executor_pin_invalid", "executor pin has an unsupported specialist skill version")
    try:
        ImageExecutorProvenance.model_validate({
            "codeRevision": pin["codeRevision"], "skillVersion": pin["skillVersion"],
            "skillHash": pin["skillHash"],
        })
    except (KeyError, ValidationError) as error:
        raise ImageJobError("delivery_executor_pin_invalid", "executor pin provenance is invalid") from error
    if expected_execution_contract == "codex_specialist.v3":
        try:
            pin["nativeTaskId"] = str(UUID(pin["nativeTaskId"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ImageJobError("delivery_executor_pin_invalid", "executor pin native task UUID is invalid") from error
    return pin


def assert_manifest_binding(manifest: ImageDeliveryManifest, *,
    job_id,
    request_hash,
    required_reference_hashes,
    require_executor_pin,
    expected_executor_contract,
    expected_codex_references,
    expected_codex_execution_pin,
    expected_codex_output_role,
    expected_codex_attempt,
    expected_codex_profile,
    expected_codex_receipt,
    require_executor_provenance,
) -> None:
    manifest.assert_secret_free()
    if manifest.job_id != job_id or manifest.request_hash != request_hash:
        raise ImageJobError("delivery_identity_mismatch", "completion manifest does not belong to this frozen image job")
    if manifest.schema_version == 3 and not require_executor_pin:
        raise ImageJobError("delivery_executor_pin_missing", "schema-v3 delivery requires its pre-generation executor pin")
    if manifest.schema_version == 5 and expected_executor_contract != "codex_exec.v1":
        raise ImageJobError("delivery_execution_mismatch", "schema-v5 delivery requires its exact Codex Exec attempt receipt")
    if expected_executor_contract == "codex_exec.v1":
        _validate_codex_exec_delivery(
            manifest,
            job_id=job_id,
            request_hash=request_hash,
            expected_references=tuple(expected_codex_references),
            required_identity_hashes=tuple(required_reference_hashes),
            execution_pin=expected_codex_execution_pin,
            expected_output_role=expected_codex_output_role,
            attempt=expected_codex_attempt,
            profile=expected_codex_profile,
            receipt=expected_codex_receipt,
        )
    elif manifest.schema_version in {4, 5}:
        raise ImageJobError("delivery_execution_mismatch", "Codex Exec delivery requires its exact attempt receipt")
    required_hashes = tuple(required_reference_hashes)
    if required_hashes:
        if manifest.schema_version not in {2, 3, 4, 5} or manifest.reference_use is None:
            raise ImageJobError(
                "delivery_reference_use_missing",
                "identity-aware delivery must attest to every viewed character reference",
            )
        viewed_hashes = set(manifest.reference_use.viewed_reference_hashes)
        required_match = set(required_hashes) <= viewed_hashes if manifest.schema_version == 5 else viewed_hashes == set(required_hashes)
        if not required_match:
            raise ImageJobError(
                "delivery_reference_use_mismatch",
                "identity-aware delivery reference attestation does not match the frozen identity set",
            )
    if require_executor_provenance and manifest.executor_provenance is None:
        raise ImageJobError(
            "delivery_executor_provenance_missing",
            "identity-aware delivery must record the observed code and specialist skill provenance",
        )


def assert_executor_pin_binding(manifest: ImageDeliveryManifest, pin: dict[str, str], *,
    job_id,
    request_hash,
    expected_executor_contract,
    expected_native_task_binding,
) -> None:
    provenance = manifest.executor_provenance
    expected_pin = {
        "jobId": job_id,
        "requestHash": request_hash,
        "executionContract": expected_executor_contract,
        "skillVersion": provenance.skill_version,
        "codeRevision": provenance.code_revision,
        "skillHash": provenance.skill_hash,
    }
    if expected_executor_contract == "codex_specialist.v3":
        try:
            binding = NativeTaskBinding.model_validate(expected_native_task_binding)
        except (TypeError, ValueError) as error:
            raise ImageJobError(
                "delivery_native_task_binding_missing",
                "schema-v3 delivery requires the package's expected native task binding",
            ) from error
        if manifest.schema_version != 3 or manifest.tool_evidence.native_task_id is None:
            raise ImageJobError("delivery_native_task_identity_missing", "schema-v3 delivery must name its native task UUID")
        if pin["nativeTaskId"] != str(manifest.tool_evidence.native_task_id):
            raise ImageJobError("delivery_native_task_identity_mismatch", "completion native task UUID differs from the pre-generation pin")
        if binding.mode == "configured_task" and pin["nativeTaskId"] != str(binding.task_id):
            raise ImageJobError("delivery_native_task_identity_mismatch", "completion native task UUID differs from the configured specialist binding")
        expected_pin["nativeTaskId"] = pin["nativeTaskId"]
    elif manifest.schema_version == 3:
        raise ImageJobError("delivery_executor_pin_invalid", "schema-v3 delivery requires codex_specialist.v3")
    if pin != expected_pin:
        raise ImageJobError(
            "delivery_executor_pin_mismatch",
            "completion provenance must match the pre-generation executor pin",
        )
