"""Versioned, strict contracts for future pre-video Codex CLI executions."""
from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .domain import CamelModel, contains_secret_setting, contains_secret_value

HASH = r"^[a-f0-9]{64}$"
JOB_ID = r"^(?:ch_[a-z0-9]{20,64}|ij_[a-z0-9]{20,64})$"
ExecCapability = Literal[
    "exec_json_events_v1",
    "session_rollout_v1",
    "image_gen_event_v1",
    "delivery_directory_write_v1",
]


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


class SpecialistChatExecutor(CamelModel):
    """A true native Codex chat binding, retained for existing workflows."""

    backend: Literal["specialist_chat"]
    text_task_id: UUID
    image_task_id: UUID

    @model_validator(mode="after")
    def distinct_tasks(self):
        if self.text_task_id == self.image_task_id:
            raise ValueError("specialist roles require distinct chat IDs")
        return self


class CodexExecProfile(CamelModel):
    """Frozen non-secret CLI identity and finite per-process capabilities."""

    model_config = CamelModel.model_config | {"frozen": True}

    backend: Literal["codex_exec"] = "codex_exec"
    contract_version: Literal["plotloom.codex-exec.v1"] = "plotloom.codex-exec.v1"
    executable_sha256: str = Field(pattern=HASH)
    cli_version: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    reasoning_effort: Literal["minimal", "low", "medium", "high", "xhigh", "max"]
    capabilities: tuple[ExecCapability, ...] = Field(min_length=3, max_length=4)
    instruction_hash: str = Field(pattern=HASH)
    validator_hash: str = Field(pattern=HASH)
    sandbox_profile: Literal["read_only_with_delivery_write"]
    max_runtime_seconds: int = Field(ge=30, le=7200)
    max_event_bytes: int = Field(ge=1024, le=50_000_000)
    max_output_bytes: int = Field(ge=1024, le=500_000_000)
    max_image_outputs: int = Field(ge=0, le=4)
    max_processes: Literal[1] = 1
    api_fallback: Literal[False] = False
    external_mcp_servers: Literal[False] = False
    nested_dispatch: Literal[False] = False

    @model_validator(mode="after")
    def supported_capability_set(self):
        selected = set(self.capabilities)
        if len(selected) != len(self.capabilities):
            raise ValueError("CLI capability pins must not contain duplicates")
        if not {"exec_json_events_v1", "session_rollout_v1", "delivery_directory_write_v1"} <= selected:
            raise ValueError("CLI profile lacks the serial executor evidence or delivery capability")
        if self.max_image_outputs and "image_gen_event_v1" not in selected:
            raise ValueError("image capacity requires the qualified native ImageGen event capability")
        payload = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise ValueError("CLI executor profiles cannot contain credentials")
        return self

    @property
    def profile_hash(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode()).hexdigest()


ExecutorBinding = Annotated[
    SpecialistChatExecutor | CodexExecProfile,
    Field(discriminator="backend"),
]


class CodexExecAttempt(CamelModel):
    """Project-owned identity and state for exactly one initial host attempt."""

    model_config = CamelModel.model_config | {"frozen": True}

    attempt_id: UUID
    run_id: UUID
    project_id: UUID
    job_id: str = Field(pattern=JOB_ID, max_length=64)
    operation_key: str = Field(min_length=1, max_length=160)
    domain: Literal["text", "image"]
    request_hash: str = Field(pattern=HASH)
    package_hash: str = Field(pattern=HASH)
    profile_hash: str = Field(pattern=HASH)
    reserved_image_outputs: int = Field(ge=0, le=4)
    state: Literal[
        "reserved",
        "spawn_intent",
        "running",
        "outcome_unknown",
        "cancel_requested",
        "completed",
        "failed",
        "settled",
    ]
    session_id: UUID | None = None
    process_id: int | None = Field(default=None, ge=1)
    process_group_id: int | None = Field(default=None, ge=1)
    process_birth_identity: str | None = Field(default=None, min_length=1, max_length=160)
    process_exit_code: int | None = None
    terminal_result: Literal["success", "failure", "not_started"] | None = None
    remote_tool_state: Literal["not_applicable", "completed", "failed"] | None = None
    evidence_hash: str | None = Field(default=None, pattern=HASH)
    output_hash: str | None = Field(default=None, pattern=HASH)

    @model_validator(mode="after")
    def owned_process_and_terminal_facts(self):
        if self.domain == "text" and self.reserved_image_outputs != 0:
            raise ValueError("text attempts cannot reserve image output capacity")
        if self.domain == "image" and self.reserved_image_outputs < 1:
            raise ValueError("image attempts must reserve their frozen output count")
        if self.process_group_id is not None and self.process_id != self.process_group_id:
            raise ValueError("isolated Codex executions require their leader PID as process-group ID")
        if self.process_birth_identity is not None and self.process_id is None:
            raise ValueError("process birth identity requires a recorded process ID")
        process_facts = (self.process_id, self.process_group_id, self.process_birth_identity)
        if any(value is not None for value in process_facts) and any(value is None for value in process_facts):
            raise ValueError("process ownership requires PID, process group and birth identity together")
        if self.state in {"completed", "failed", "settled"}:
            if self.terminal_result is None or self.evidence_hash is None or self.remote_tool_state is None:
                raise ValueError("terminal attempts require typed terminal, remote and evidence facts")
        elif any(
            value is not None
            for value in (self.terminal_result, self.remote_tool_state, self.process_exit_code, self.output_hash)
        ):
            raise ValueError("nonterminal attempts cannot contain terminal settlement facts")
        if self.domain == "text" and self.remote_tool_state not in {None, "not_applicable"}:
            raise ValueError("text attempts cannot claim a remote ImageGen operation")
        if self.remote_tool_state in {"completed", "failed"} and self.session_id is None:
            raise ValueError("a confirmed remote operation requires its exact Codex session identity")
        if self.terminal_result == "not_started":
            if any(value is not None for value in (*process_facts, self.session_id, self.process_exit_code, self.output_hash)):
                raise ValueError("an attempt proven not started cannot contain process, session or output facts")
            if self.remote_tool_state != "not_applicable":
                raise ValueError("an attempt proven not started cannot claim a remote tool outcome")
        if self.terminal_result == "failure":
            if any(value is None for value in process_facts) or self.process_exit_code is None:
                raise ValueError("failed work requires exact process ownership and an exit code")
        if self.state == "failed" and self.terminal_result not in {"failure", "not_started"}:
            raise ValueError("failed attempts require proof of failure or that work never started")
        if self.terminal_result == "success":
            if any(
                value is None
                for value in (*process_facts, self.session_id, self.process_exit_code, self.output_hash)
            ) or self.process_exit_code != 0:
                raise ValueError("completed attempts require exact successful process, session, evidence and output identities")
            if (self.reserved_image_outputs > 0) != (self.remote_tool_state == "completed"):
                raise ValueError("successful terminal outcome must match the reserved image operation")
        if self.remote_tool_state == "completed" and self.output_hash is None:
            raise ValueError("completed remote work requires a hash of its retained output bytes")
        if self.state == "completed":
            if self.terminal_result != "success":
                raise ValueError("completed attempts require a successful terminal result")
        return self


class CodexExecImageEvidence(CamelModel):
    """Typed native ImageGen completion bound to one session and exact bytes."""

    model_config = CamelModel.model_config | {"frozen": True}

    attempt_id: UUID
    session_id: UUID
    call_id: str = Field(min_length=1, max_length=160)
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
        if len(parts) < 3 or parts[:2] != ["delivery", "outputs"] or any(
            part in {"", ".", ".."} for part in parts
        ):
            raise ValueError("outputs must be files below delivery/outputs")
        return self


class CodexExecReceipt(CamelModel):
    """Small settled proof copied from the private host evidence stream."""

    model_config = CamelModel.model_config | {"frozen": True}

    attempt_id: UUID
    session_id: UUID
    profile_hash: str = Field(pattern=HASH)
    request_hash: str = Field(pattern=HASH)
    package_hash: str = Field(pattern=HASH)
    process_id: int = Field(ge=1)
    process_group_id: int = Field(ge=1)
    process_birth_identity: str = Field(min_length=1, max_length=160)
    process_exit_code: int
    expected_image_outputs: int = Field(ge=0, le=4)
    evidence_hash: str = Field(pattern=HASH)
    output_hash: str = Field(pattern=HASH)
    outputs: tuple[CodexExecOutputEvidence, ...] = Field(min_length=1, max_length=128)
    image_evidence: tuple[CodexExecImageEvidence, ...] = Field(default_factory=tuple)
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
            if self.image_evidence or self.remote_tool_state != "not_applicable":
                raise ValueError("text receipts cannot claim ImageGen operations")
        elif len(self.image_evidence) != self.expected_image_outputs or self.remote_tool_state != "completed":
            raise ValueError("image receipt must prove every frozen ImageGen output")
        if len({item.call_id for item in self.image_evidence}) != len(self.image_evidence):
            raise ValueError("ImageGen call IDs must be unique within one attempt")
        if len({item.output_relative_path for item in self.image_evidence}) != len(self.image_evidence):
            raise ValueError("ImageGen output paths must be unique within one attempt")
        output_by_path = {item.output_relative_path: item for item in self.outputs}
        for event in self.image_evidence:
            if event.attempt_id != self.attempt_id or event.session_id != self.session_id:
                raise ValueError("native ImageGen event must belong to the exact attempt session")
            output = output_by_path.get(event.output_relative_path)
            if output is None or output.output_hash != event.output_hash:
                raise ValueError("ImageGen event must bind an exact output path and byte hash")
        if self.process_exit_code != 0:
            raise ValueError("successful execution receipt requires a zero process exit code")
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
        "process_id": attempt.process_id,
        "process_group_id": attempt.process_group_id,
        "process_birth_identity": attempt.process_birth_identity,
        "process_exit_code": attempt.process_exit_code,
        "evidence_hash": attempt.evidence_hash,
        "output_hash": attempt.output_hash,
        "remote_tool_state": attempt.remote_tool_state,
    }
    if any(getattr(receipt, name) != value for name, value in expected.items()):
        raise ValueError("host receipt does not match the exact project attempt facts")
    if attempt.reserved_image_outputs != receipt.expected_image_outputs:
        raise ValueError("host receipt image count differs from the frozen project reservation")
