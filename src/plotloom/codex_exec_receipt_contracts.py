"""Receipts and output evidence for exact Codex Exec attempts."""
from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .codex_exec_attempt_contracts import CodexExecAttempt
from .codex_exec_constants import HASH
from .codex_exec_validation import CodexExecTextValidationEvidence
from .domain import CamelModel


def _canonical_hash(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def image_arguments_hash(*, prompt_hash, reference_hashes, transparent_background, num_last_images_to_include):
    return _canonical_hash({
        "contract": "plotloom.imagegen-arguments.v1",
        "promptHash": prompt_hash,
        "referenceHashes": list(reference_hashes),
        "transparentBackground": transparent_background,
        "numLastImagesToInclude": num_last_images_to_include,
    })


def output_manifest_hash(outputs) -> str:
    return _canonical_hash({
        "contract": "plotloom.codex-exec-output-manifest.v1",
        "outputs": [item.model_dump(mode="json", by_alias=True) for item in outputs],
    })


class CodexExecImageEvidence(CamelModel):
    """Typed native ImageGen completion bound to one session and exact bytes."""

    model_config = CamelModel.model_config | {"frozen": True}

    attempt_id: UUID
    session_id: UUID
    call_id: str = Field(min_length=1, max_length=160)
    call_ordinal: int = Field(ge=1)
    event_id: str = Field(min_length=1, max_length=160)
    event_type: Literal["image_gen.generation"]
    event_status: Literal["completed"]
    arguments_hash: str = Field(pattern=HASH)
    prompt_hash: str = Field(pattern=HASH)
    reference_hashes: tuple[str, ...] = Field(default_factory=tuple, max_length=16)
    transparent_background: bool
    num_last_images_to_include: int | None = Field(default=None, ge=0, le=0)
    output_hash: str = Field(pattern=HASH)
    output_relative_path: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def confined_output_path(self):
        if "\\" in self.output_relative_path:
            raise ValueError("ImageGen output paths must use canonical POSIX separators")
        parts = self.output_relative_path.split("/")
        if len(parts) < 3 or any(part in {"", ".", ".."} for part in parts) or parts[:2] != ["delivery", "outputs"]:
            raise ValueError("ImageGen output must be confined to the attempt delivery outputs directory")
        if len(self.reference_hashes) != len(set(self.reference_hashes)):
            raise ValueError("ImageGen reference hashes must be distinct")
        if any(re.fullmatch(HASH, value) is None for value in self.reference_hashes):
            raise ValueError("ImageGen reference evidence must use SHA-256 content hashes")
        if self.arguments_hash != image_arguments_hash(
            prompt_hash=self.prompt_hash,
            reference_hashes=self.reference_hashes,
            transparent_background=self.transparent_background,
            num_last_images_to_include=self.num_last_images_to_include,
        ):
            raise ValueError("ImageGen argument hash must bind the normalized actual arguments")
        return self


class CodexExecOutputEvidence(CamelModel):
    """One byte-verified file in the attempt's declared output inventory."""

    model_config = CamelModel.model_config | {"frozen": True}

    output_hash: str = Field(pattern=HASH)
    output_relative_path: str = Field(min_length=1, max_length=512)
    size_bytes: int = Field(ge=1, le=500_000_000)

    @model_validator(mode="after")
    def canonical_output_path(self):
        if "\\" in self.output_relative_path:
            raise ValueError("output paths must use canonical POSIX separators")
        parts = self.output_relative_path.split("/")
        if len(parts) < 2 or parts[0] != "delivery" or any(
            part in {"", ".", ".."} for part in parts
        ):
            raise ValueError("outputs must be files confined below delivery")
        return self


class CodexExecReferenceViewEvidence(CamelModel):
    """One host-verified frozen package reference emitted as image input before ImageGen."""

    model_config = CamelModel.model_config | {"frozen": True}

    role: str = Field(min_length=1, max_length=160)
    package_relative_path: str = Field(min_length=1, max_length=512)
    reference_hash: str = Field(pattern=HASH)
    content_sha256: str = Field(pattern=HASH)
    content_size_bytes: int = Field(ge=1, le=50_000_000)
    call_id: str = Field(min_length=1, max_length=160)
    event_id: str = Field(min_length=1, max_length=160)
    call_ordinal: int = Field(ge=1)
    event_ordinal: int = Field(ge=1)
    output_ordinal: int = Field(ge=1)

    @model_validator(mode="after")
    def canonical_view_identity(self):
        if "\\" in self.package_relative_path:
            raise ValueError("reference-view package paths must use canonical POSIX separators")
        parts = self.package_relative_path.split("/")
        if len(parts) < 2 or parts[0] != "references" or any(
            part in {"", ".", ".."} for part in parts
        ):
            raise ValueError("reference-view path must name one confined package reference")
        if not self.call_ordinal < self.event_ordinal < self.output_ordinal:
            raise ValueError("reference-view call, event and image output ordinals must be ordered")
        return self


class CodexExecReceipt(CamelModel):
    """Small settled proof copied from the private host evidence stream."""

    model_config = CamelModel.model_config | {"frozen": True}

    attempt_id: UUID
    session_id: UUID
    profile_hash: str = Field(pattern=HASH)
    request_hash: str = Field(pattern=HASH)
    package_hash: str = Field(pattern=HASH)
    plotloom_code_revision: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{7,64}$",
        exclude_if=lambda value: value is None,
    )
    validation_plan_hash: str | None = Field(default=None, pattern=HASH, exclude_if=lambda value: value is None)
    process_id: int = Field(ge=1)
    process_group_id: int = Field(ge=1)
    process_birth_identity: str = Field(min_length=1, max_length=160)
    process_exit_code: int
    expected_image_outputs: int = Field(ge=0, le=4)
    evidence_hash: str = Field(pattern=HASH)
    output_hash: str = Field(pattern=HASH)
    remote_output_hash: str | None = Field(default=None, pattern=HASH)
    outputs: tuple[CodexExecOutputEvidence, ...] = Field(min_length=1, max_length=128)
    image_evidence: tuple[CodexExecImageEvidence, ...] = Field(default_factory=tuple)
    reference_views: tuple[CodexExecReferenceViewEvidence, ...] = Field(default_factory=tuple, max_length=24)
    text_validation: CodexExecTextValidationEvidence | None = Field(default=None, exclude_if=lambda value: value is None)
    remote_tool_state: Literal["not_applicable", "completed"]

    @model_validator(mode="after")
    def image_proof_matches_receipt(self):
        if self.process_id != self.process_group_id:
            raise ValueError("isolated Codex receipts require their leader PID as process-group ID")
        output_paths = [item.output_relative_path for item in self.outputs]
        if output_paths != sorted(output_paths) or len(output_paths) != len(set(output_paths)):
            raise ValueError("receipt output inventory must be sorted and have unique canonical paths")
        if output_manifest_hash(self.outputs) != self.output_hash:
            raise ValueError("receipt output hash must bind the canonical output inventory")
        if self.expected_image_outputs == 0:
            if self.image_evidence or self.reference_views or self.remote_tool_state != "not_applicable" or self.remote_output_hash is not None:
                raise ValueError("text receipts cannot claim image or reference-view operations")
            if (self.validation_plan_hash is None) != (self.text_validation is None):
                raise ValueError("trusted text validation requires both its plan and evidence hashes")
            if self.text_validation is not None:
                proof = self.text_validation
                if proof.plan_hash != self.validation_plan_hash:
                    raise ValueError("trusted text evidence must bind the exact frozen plan")
                outputs = {item.output_relative_path: item for item in self.outputs}
                expected_paths = {
                    f"delivery/{proof.candidate_filename}",
                    f"delivery/{proof.report_filename}",
                }
                if set(outputs) != expected_paths:
                    raise ValueError("trusted text receipt must contain only the candidate and host report")
                candidate_output = outputs[f"delivery/{proof.candidate_filename}"]
                report_output = outputs[f"delivery/{proof.report_filename}"]
                if (candidate_output.output_hash, candidate_output.size_bytes) != (
                    proof.candidate_hash, proof.candidate_size_bytes,
                ) or (report_output.output_hash, report_output.size_bytes) != (
                    proof.report_hash, proof.report_size_bytes,
                ):
                    raise ValueError("trusted text evidence must bind exact receipt output bytes")
        elif len(self.image_evidence) != self.expected_image_outputs or self.remote_tool_state != "completed":
            raise ValueError("image receipt must prove every frozen ImageGen output")
        elif self.validation_plan_hash is not None or self.text_validation is not None:
            raise ValueError("image receipts cannot claim text validation proof")
        elif len(self.image_evidence) != 1 or self.remote_output_hash != self.image_evidence[0].output_hash:
            raise ValueError("serial image receipt must bind its exact remote output byte hash")
        if len({item.call_id for item in self.image_evidence}) != len(self.image_evidence):
            raise ValueError("ImageGen call IDs must be unique within one attempt")
        view_paths = [item.package_relative_path for item in self.reference_views]
        view_hashes = [item.reference_hash for item in self.reference_views]
        view_call_ids = [item.call_id for item in self.reference_views]
        view_event_ids = [item.event_id for item in self.reference_views]
        view_call_ordinals = [item.call_ordinal for item in self.reference_views]
        view_event_ordinals = [item.event_ordinal for item in self.reference_views]
        view_output_ordinals = [item.output_ordinal for item in self.reference_views]
        view_timeline = [
            ordinal
            for item in self.reference_views
            for ordinal in (item.call_ordinal, item.event_ordinal, item.output_ordinal)
        ]
        if (
            len(view_paths) != len(set(view_paths))
            or len(view_hashes) != len(set(view_hashes))
            or len(view_call_ids) != len(set(view_call_ids))
            or len(view_event_ids) != len(set(view_event_ids))
            or view_call_ordinals != sorted(view_call_ordinals)
            or view_event_ordinals != sorted(view_event_ordinals)
            or view_output_ordinals != sorted(view_output_ordinals)
            or view_timeline != sorted(view_timeline)
            or len(view_timeline) != len(set(view_timeline))
            or any(len(values) != len(set(values)) for values in (
                view_call_ordinals, view_event_ordinals, view_output_ordinals,
            ))
        ):
            raise ValueError("reference-view receipt entries must be unique and ordered")
        if len({item.output_relative_path for item in self.image_evidence}) != len(self.image_evidence):
            raise ValueError("ImageGen output paths must be unique within one attempt")
        output_by_path = {item.output_relative_path: item for item in self.outputs}
        for event in self.image_evidence:
            if event.attempt_id != self.attempt_id or event.session_id != self.session_id:
                raise ValueError("native ImageGen event must belong to the exact attempt session")
            output = output_by_path.get(event.output_relative_path)
            if output is None or output.output_hash != event.output_hash:
                raise ValueError("ImageGen event must bind an exact output path and byte hash")
            if tuple(view.reference_hash for view in self.reference_views) != event.reference_hashes:
                raise ValueError("ImageGen references must match the exact host-recorded view order")
            if any(view.output_ordinal >= event.call_ordinal for view in self.reference_views):
                raise ValueError("every frozen reference image must be emitted before its ImageGen call")
        if self.process_exit_code != 0:
            raise ValueError("successful execution receipt requires a zero process exit code")
        return self


class CodexExecHostStatus(CamelModel):
    """Bounded status response returned by the private Mac supervisor."""

    model_config = CamelModel.model_config | {"frozen": True}

    state: Literal[
        "not_found", "queued", "spawn_intent", "running", "validating", "outcome_unknown", "cancel_requested",
        "completed", "failed", "settled",
    ]
    attempt: CodexExecAttempt | None = None
    receipt: CodexExecReceipt | None = None
    capacity_deferred: bool = Field(default=False, exclude_if=lambda value: value is False)
    dispatch_enabled: bool | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def terminal_receipt_is_exact(self):
        if self.capacity_deferred and (self.state not in {"not_found", "queued", "spawn_intent"} or self.receipt is not None):
            raise ValueError("capacity deferral cannot claim running or terminal work")
        if self.dispatch_enabled is not None and self.state not in {"queued", "spawn_intent"}:
            raise ValueError("dispatch authorization belongs only to unstarted host work")
        if self.state == "not_found":
            if self.attempt is not None or self.receipt is not None:
                raise ValueError("not-found host status cannot contain attempt evidence")
            return self
        if self.attempt is None or self.attempt.state != self.state:
            raise ValueError("host status must contain its exact lifecycle attempt snapshot")
        if self.attempt.state in {"completed", "settled"} and self.attempt.terminal_result == "success":
            if self.receipt is None:
                raise ValueError("successful host status requires its exact receipt")
            assert_receipt_matches_attempt(self.attempt, self.receipt)
        elif self.receipt is not None:
            raise ValueError("host receipt can exist only for a successful terminal attempt")
        return self


def assert_receipt_matches_attempt(attempt: CodexExecAttempt, receipt: CodexExecReceipt) -> None:
    """Bind successful private host proof to the exact project-owned attempt."""
    # Revalidate serialized snapshots at this trust boundary. Pydantic's
    # model_copy(update=...) deliberately skips validation, so frozen models
    # alone do not make a forged or stale snapshot safe to admit.
    attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
    receipt = CodexExecReceipt.model_validate(receipt.model_dump(mode="python"))
    if attempt.state not in {"completed", "settled"} or attempt.terminal_result != "success":
        raise ValueError("only a successfully settled project attempt can admit a receipt")
    expected = {
        "attempt_id": attempt.attempt_id,
        "session_id": attempt.session_id,
        "profile_hash": attempt.profile_hash,
        "request_hash": attempt.request_hash,
        "package_hash": attempt.package_hash,
        "plotloom_code_revision": attempt.plotloom_code_revision,
        "validation_plan_hash": attempt.validation_plan_hash,
        "process_id": attempt.process_id,
        "process_group_id": attempt.process_group_id,
        "process_birth_identity": attempt.process_birth_identity,
        "process_exit_code": attempt.process_exit_code,
        "evidence_hash": attempt.evidence_hash,
        "output_hash": attempt.output_hash,
        "remote_output_hash": attempt.remote_output_hash,
        "remote_tool_state": attempt.remote_tool_state,
    }
    if any(getattr(receipt, name) != value for name, value in expected.items()):
        raise ValueError("host receipt does not match the exact project attempt facts")
    if attempt.reserved_image_outputs != receipt.expected_image_outputs:
        raise ValueError("host receipt image count differs from the frozen project reservation")
    if attempt.remote_output_hash != (
        receipt.image_evidence[0].output_hash if receipt.image_evidence else None
    ):
        raise ValueError("host receipt remote image byte hash differs from its exact event")
    if attempt.validation_plan_hash is None:
        if receipt.text_validation is not None or receipt.validation_plan_hash is not None:
            raise ValueError("host receipt cannot add validation evidence absent from the frozen attempt")
    else:
        proof = receipt.text_validation
        if (proof is None or proof.plan_hash != attempt.validation_plan_hash
                or receipt.validation_plan_hash != attempt.validation_plan_hash
                or proof.profile_hash != attempt.profile_hash
                or proof.request_hash != attempt.request_hash
                or proof.package_hash != attempt.package_hash
                or proof.source_revision != attempt.plotloom_code_revision):
            raise ValueError("trusted text validation evidence differs from its frozen project attempt")
