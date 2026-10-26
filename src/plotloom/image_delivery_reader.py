"""Observe one confined image delivery and classify final publication failures."""
from __future__ import annotations
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from pydantic import ValidationError

from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecProfile,
    CodexExecReceipt,
)
from .image_job_contracts import (
    ImageDeliveryManifest,
    ImageJobError,
    NativeTaskBinding,
    is_image_job_id,
)
from .image_job_package import canonical_json as _canonical_json
from .managed_media import ManagedMediaLimits, ObservedImage, inspect_import_image

from .image_exchange_files import _open_directory, _directory_names, _read_regular_at
from .image_delivery_manifest import assert_manifest_binding, assert_executor_pin_binding, validated_executor_pin

COMPLETION_FILENAME = "completion.json"
EXECUTOR_PIN_FILENAME = "executor-pin.json"

@dataclass(frozen=True)
class ValidatedOutput:
    filename: str
    role: str
    observed: ObservedImage
    content: bytes


@dataclass(frozen=True)
class ValidatedDelivery:
    manifest: ImageDeliveryManifest
    manifest_hash: str
    outputs: tuple[ValidatedOutput, ...]


def read_executor_pin(delivery_fd: int, **expected) -> dict[str, str]:
    try:
        payload = json.loads(_read_regular_at(delivery_fd, EXECUTOR_PIN_FILENAME, max_bytes=20_000))
    except (json.JSONDecodeError, TypeError) as error:
        raise ImageJobError("delivery_executor_pin_invalid", "executor pin is not valid JSON") from error
    return validated_executor_pin(payload, **expected)


def read_delivery(
    root: Path, limits: ManagedMediaLimits,
    *,
    job_id: str,
    request_hash: str,
    required_reference_hashes: Iterable[str] = (),
    require_executor_provenance: bool = False,
    require_executor_pin: bool = False,
    expected_executor_skill_version: str | None = None,
    expected_executor_contract: str = "codex_specialist.v2",
    expected_native_task_binding: NativeTaskBinding | dict | None = None,
    expected_codex_attempt: CodexExecAttempt | None = None,
    expected_codex_profile: CodexExecProfile | None = None,
    expected_codex_receipt: CodexExecReceipt | None = None,
    expected_codex_references: Iterable[tuple[str, str, str]] = (),
    expected_codex_execution_pin: dict[str, str] | None = None,
    expected_codex_output_role: str | None = None,
) -> ValidatedDelivery | None:
    """Read a completed untrusted package, or report that no delivery exists yet.

    An absent delivery directory, an empty inbox, and staged output before
    ``completion.json`` are all normal pending states after Copy. The
    completion manifest is the specialist's final publication marker: only
    once it exists can an observer classify malformed bytes as a durable
    rejected delivery. This keeps repeated polling from manufacturing
    rejection history while an otherwise valid specialist is still writing.
    """

    if not is_image_job_id(job_id):
        raise ImageJobError("invalid_job_id", "image job identifier is invalid")
    # Descriptor-relative, no-follow reads bind every ancestor and the
    # final file before inspecting it. A delivery writer can change files
    # while preparing, but cannot swap this read outside the exchange root.
    try:
        delivery_fd = _open_directory(root, ("jobs", job_id, "delivery"))
    except ImageJobError as error:
        if error.code == "delivery_incomplete":
            return None
        raise
    completion_marker_observed = False
    try:
        names = _directory_names(
            delivery_fd, allow_disappearing=frozenset({"completion-draft.json"})
        )
        if not names:
            return None
        if COMPLETION_FILENAME not in names:
            # The delivery protocol requires the specialist to publish the
            # manifest last. Outputs, the v4 executor pin, and even a
            # partially written staging set therefore carry no terminal
            # meaning before that marker exists. They remain confined and
            # non-publishing until the next observation sees completion.
            return None
        completion_marker_observed = True
        raw = _read_regular_at(delivery_fd, COMPLETION_FILENAME, max_bytes=1_000_000)
        try:
            payload = json.loads(raw)
            manifest = ImageDeliveryManifest.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            raise ImageJobError("delivery_manifest_invalid", "completion manifest does not match the image-job contract") from error
        assert_manifest_binding(manifest,
            job_id=job_id,
            request_hash=request_hash,
            required_reference_hashes=required_reference_hashes,
            require_executor_pin=require_executor_pin,
            expected_executor_contract=expected_executor_contract,
            expected_codex_references=expected_codex_references,
            expected_codex_execution_pin=expected_codex_execution_pin,
            expected_codex_output_role=expected_codex_output_role,
            expected_codex_attempt=expected_codex_attempt,
            expected_codex_profile=expected_codex_profile,
            expected_codex_receipt=expected_codex_receipt,
            require_executor_provenance=require_executor_provenance,
        )
        if require_executor_pin:
            if not require_executor_provenance:
                raise ImageJobError("delivery_executor_pin_invalid", "executor pin requires executor provenance")
            if EXECUTOR_PIN_FILENAME not in names:
                raise ImageJobError(
                    "delivery_executor_pin_missing",
                    "identity-aware delivery must include the pre-generation executor pin",
                )
            pin = read_executor_pin(
                delivery_fd, job_id=job_id, request_hash=request_hash,
                expected_skill_version=expected_executor_skill_version,
                expected_execution_contract=expected_executor_contract,
            )
            assert_executor_pin_binding(manifest, pin,
                job_id=job_id,
                request_hash=request_hash,
                expected_executor_contract=expected_executor_contract,
                expected_native_task_binding=expected_native_task_binding,
            )
        expected_delivery_names = {COMPLETION_FILENAME, "outputs"}
        if require_executor_pin:
            expected_delivery_names.add(EXECUTOR_PIN_FILENAME)
        if manifest.schema_version == 3 and "completion-draft.json" in names:
            try:
                draft_payload = json.loads(_read_regular_at(
                    delivery_fd, "completion-draft.json", max_bytes=1_000_000
                ))
                draft = ImageDeliveryManifest.model_validate(draft_payload)
            except ImageJobError:
                # The publisher removes this known staging file after the
                # atomic marker link. Recheck the directory to distinguish
                # that cleanup race from a still-present invalid entry.
                current_names = _directory_names(
                    delivery_fd, allow_disappearing=frozenset({"completion-draft.json"})
                )
                if "completion-draft.json" in current_names:
                    raise
                names = current_names
            except (json.JSONDecodeError, ValidationError) as error:
                raise ImageJobError(
                    "delivery_partial", "staged completion draft is invalid", publication_phase="final"
                ) from error
            else:
                if draft.canonical_payload() != manifest.canonical_payload():
                    raise ImageJobError(
                        "delivery_partial", "staged completion draft differs from the published manifest",
                        publication_phase="final",
                    )
                expected_delivery_names.add("completion-draft.json")
        if names != expected_delivery_names:
            raise ImageJobError(
                "delivery_partial", "delivery contains undeclared files", publication_phase="final"
            )

        outputs_fd = _open_directory(root, ("jobs", job_id, "delivery", "outputs"))
        try:
            declared = {item.filename for item in manifest.outputs}
            actual = _directory_names(outputs_fd)
            if actual != declared:
                raise ImageJobError(
                    "delivery_partial", "delivery output set does not exactly match the completion manifest",
                    publication_phase="final",
                )
            outputs: list[ValidatedOutput] = []
            for declaration in manifest.outputs:
                content = _read_regular_at(outputs_fd, declaration.filename, max_bytes=limits.max_import_bytes)
                if sha256(content).hexdigest() != declaration.sha256:
                    raise ImageJobError("delivery_hash_mismatch", "delivery bytes do not match their declared hash")
                try:
                    observed = inspect_import_image(content, limits)
                except Exception as error:  # ManagedMediaError is intentionally normalized for this boundary.
                    code = getattr(error, "code", "delivery_image_invalid")
                    raise ImageJobError(code, "delivery output is not a bounded supported raster") from error
                outputs.append(ValidatedOutput(
                    filename=declaration.filename,
                    role=declaration.role,
                    observed=observed,
                    content=content,
                ))
        finally:
            os.close(outputs_fd)
    except ImageJobError as error:
        # Once the completion marker has been observed, every normalized
        # delivery error is final-publication evidence. The marker is set
        # before parsing because malformed completion bytes are final too.
        if completion_marker_observed and error.publication_phase is None:
            error.publication_phase = "final"
        raise
    finally:
        os.close(delivery_fd)
    return ValidatedDelivery(
        manifest=manifest,
        manifest_hash=sha256(_canonical_json(manifest.canonical_payload())).hexdigest(),
        outputs=tuple(outputs),
    )
