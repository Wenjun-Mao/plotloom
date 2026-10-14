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
    "image_reference_view_v1",
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


class CodexExecPackageFile(CamelModel):
    """One immutable file identity in a complete frozen package tree."""

    model_config = CamelModel.model_config | {"frozen": True}

    relative_path: str = Field(min_length=1, max_length=512)
    sha256: str = Field(pattern=HASH)
    size_bytes: int = Field(ge=0, le=500_000_000)

    @model_validator(mode="after")
    def canonical_package_path(self):
        if "\\" in self.relative_path:
            raise ValueError("package paths must use canonical POSIX separators")
        parts = self.relative_path.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("package file paths must be confined relative paths")
        return self


def package_manifest_hash(files) -> str:
    files = tuple(files)
    paths = [item.relative_path for item in files]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("package manifest files must be sorted and have unique paths")
    return _canonical_hash({
        "contract": "plotloom.codex-exec-package-manifest.v1",
        "files": [item.model_dump(mode="json", by_alias=True) for item in files],
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
    contract_version: Literal[
        "plotloom.codex-exec.v1", "plotloom.codex-exec.v2", "plotloom.codex-exec.v3",
        "plotloom.codex-exec.v4",
    ] = "plotloom.codex-exec.v4"
    executable_sha256: str = Field(pattern=HASH)
    cli_version: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    reasoning_effort: Literal["minimal", "low", "medium", "high", "xhigh", "max"]
    capabilities: tuple[ExecCapability, ...] = Field(min_length=3, max_length=5)
    instruction_hash: str = Field(pattern=HASH)
    validator_hash: str = Field(pattern=HASH)
    # v1 recorded a label for the legacy --sandbox path. v2 names the
    # invocation-local permission and tool profiles that actually constrain
    # model-generated commands and built-in capabilities.
    sandbox_profile: Literal["read_only_with_delivery_write"] | None = Field(default=None, exclude_if=lambda value: value is None)
    authentication_store: Literal["file"] | None = Field(default=None, exclude_if=lambda value: value is None)
    permission_profile: Literal["plotloom_autopilot_delivery_v2"] | None = Field(default=None, exclude_if=lambda value: value is None)
    tool_profile: Literal[
        "plotloom_autopilot_tools_v2", "plotloom_autopilot_tools_v3", "plotloom_autopilot_tools_v4"
    ] | None = Field(default=None, exclude_if=lambda value: value is None)
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
        if self.contract_version == "plotloom.codex-exec.v1":
            if self.sandbox_profile != "read_only_with_delivery_write" or any(
                value is not None for value in (
                    self.authentication_store, self.permission_profile, self.tool_profile,
                )
            ):
                raise ValueError("legacy Codex Exec profiles must retain their original sandbox contract")
        elif self.contract_version == "plotloom.codex-exec.v2" and (
            self.sandbox_profile is not None
            or self.authentication_store != "file"
            or self.permission_profile != "plotloom_autopilot_delivery_v2"
            or self.tool_profile != "plotloom_autopilot_tools_v2"
        ):
            raise ValueError("Codex Exec v2 requires its pinned auth, permission and tool profiles")
        elif self.contract_version == "plotloom.codex-exec.v3" and (
            self.sandbox_profile is not None
            or self.authentication_store != "file"
            or self.permission_profile != "plotloom_autopilot_delivery_v2"
            or self.tool_profile != "plotloom_autopilot_tools_v3"
        ):
            raise ValueError("Codex Exec v3 requires its pinned auth, permission and tool profiles")
        elif self.contract_version == "plotloom.codex-exec.v4" and (
            self.sandbox_profile is not None
            or self.authentication_store != "file"
            or self.permission_profile != "plotloom_autopilot_delivery_v2"
            or self.tool_profile != "plotloom_autopilot_tools_v4"
        ):
            raise ValueError("Codex Exec v4 requires its pinned auth, permission and reference-view tool profile")
        selected = set(self.capabilities)
        if len(selected) != len(self.capabilities):
            raise ValueError("CLI capability pins must not contain duplicates")
        if not {"exec_json_events_v1", "session_rollout_v1", "delivery_directory_write_v1"} <= selected:
            raise ValueError("CLI profile lacks the serial executor evidence or delivery capability")
        if self.max_image_outputs and "image_gen_event_v1" not in selected:
            raise ValueError("image capacity requires the qualified native ImageGen event capability")
        if self.contract_version == "plotloom.codex-exec.v4" and "image_reference_view_v1" not in selected:
            raise ValueError("Codex Exec v4 requires typed reference-view evidence capability")
        payload = self.model_dump(mode="json", by_alias=True)
        if contains_secret_setting(payload) or contains_secret_value(payload):
            raise ValueError("CLI executor profiles cannot contain credentials")
        return self

    @property
    def profile_hash(self) -> str:
        # Excluding null v2-only fields keeps retained v1 profile hashes stable
        # while fresh profiles bind the actual auth and permission settings.
        canonical = json.dumps(
            self.model_dump(mode="json", by_alias=True, exclude_none=True),
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode()).hexdigest()


class CodexExecReadiness(CamelModel):
    """Dynamic local login readiness; it is deliberately outside the frozen profile."""

    state: Literal["ready", "not_authenticated", "unavailable"]

    @property
    def ready(self) -> bool:
        return self.state == "ready"


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
    image_budget_state: Literal["none", "reserved", "consumed", "released"] = "none"
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
    remote_output_hash: str | None = Field(default=None, pattern=HASH)

    @model_validator(mode="after")
    def owned_process_and_terminal_facts(self):
        if self.domain == "text" and self.reserved_image_outputs != 0:
            raise ValueError("text attempts cannot reserve image output capacity")
        if self.domain == "image" and self.reserved_image_outputs < 1:
            raise ValueError("image attempts must reserve their frozen output count")
        if self.domain == "text" and self.image_budget_state != "none":
            raise ValueError("text attempts cannot reserve image output capacity")
        if self.domain == "image" and self.image_budget_state == "none":
            raise ValueError("image attempts must record their project budget disposition")
        if self.process_group_id is not None and self.process_id != self.process_group_id:
            raise ValueError("isolated Codex executions require their leader PID as process-group ID")
        if self.process_birth_identity is not None and self.process_id is None:
            raise ValueError("process birth identity requires a recorded process ID")
        process_facts = (self.process_id, self.process_group_id, self.process_birth_identity)
        if any(value is not None for value in process_facts) and any(value is None for value in process_facts):
            raise ValueError("process ownership requires PID, process group and birth identity together")
        if self.state in {"reserved", "spawn_intent"} and any(
            value is not None for value in (*process_facts, self.session_id)
        ):
            raise ValueError("pre-spawn attempts cannot claim a process or session identity")
        if self.state in {"completed", "failed", "settled"}:
            if self.terminal_result is None or self.evidence_hash is None or self.remote_tool_state is None:
                raise ValueError("terminal attempts require typed terminal, remote and evidence facts")
        elif any(
            value is not None
            for value in (
                self.terminal_result, self.remote_tool_state, self.process_exit_code,
                self.output_hash, self.remote_output_hash,
            )
        ):
            raise ValueError("nonterminal attempts cannot contain terminal settlement facts")
        if self.domain == "image":
            if self.state not in {"completed", "failed", "settled"} and self.image_budget_state != "reserved":
                raise ValueError("unsettled image attempts must retain their project budget reservation")
            if self.state in {"completed", "failed", "settled"}:
                expected_budget_state = "consumed" if self.remote_tool_state == "completed" else "released"
                if self.image_budget_state != expected_budget_state:
                    raise ValueError("terminal image outcome must settle its reserved project budget")
        if self.domain == "text" and self.remote_tool_state not in {None, "not_applicable"}:
            raise ValueError("text attempts cannot claim a remote ImageGen operation")
        if self.domain == "text" and self.remote_output_hash is not None:
            raise ValueError("text attempts cannot claim a remote image byte hash")
        if self.remote_tool_state in {"completed", "failed"} and self.session_id is None:
            raise ValueError("a confirmed remote operation requires its exact Codex session identity")
        if self.remote_output_hash is not None and (
            self.domain != "image" or self.remote_tool_state != "completed"
        ):
            raise ValueError("remote image bytes require a confirmed completed ImageGen event")
        if self.terminal_result == "not_started":
            if any(value is not None for value in (
                *process_facts, self.session_id, self.process_exit_code,
                self.output_hash, self.remote_output_hash,
            )):
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
            if self.domain == "image" and self.remote_output_hash is None:
                raise ValueError("successful ImageGen requires its exact remote output byte hash")
        if (self.remote_tool_state == "completed" and self.output_hash is None
                and self.terminal_result != "failure"):
            raise ValueError("completed remote work requires a hash of its retained output bytes")
        if (self.state in {"failed", "settled"} and self.terminal_result == "failure"
                and self.remote_tool_state == "completed" and self.remote_output_hash is None):
            raise ValueError("failed CLI work must retain confirmed remote ImageGen byte provenance")
        if self.state == "completed":
            if self.terminal_result != "success":
                raise ValueError("completed attempts require a successful terminal result")
        return self


_ATTEMPT_IDENTITY_FIELDS = (
    "attempt_id",
    "run_id",
    "project_id",
    "job_id",
    "operation_key",
    "domain",
    "request_hash",
    "package_hash",
    "profile_hash",
    "reserved_image_outputs",
)
_ATTEMPT_TRANSITIONS = {
    "reserved": {"spawn_intent", "settled"},
    # The project poller can first observe the host after its short CLI process
    # has already terminally completed; terminal host proof may skip an unseen
    # running snapshot without changing attempt identity.
    "spawn_intent": {"running", "outcome_unknown", "cancel_requested", "completed", "failed", "settled"},
    "running": {"outcome_unknown", "cancel_requested", "completed", "failed"},
    "outcome_unknown": {"running", "cancel_requested", "completed", "failed", "settled"},
    "cancel_requested": {"outcome_unknown", "completed", "failed", "settled"},
    "completed": {"settled"},
    "failed": {"settled"},
    "settled": set(),
}
_ATTEMPT_MUTABLE_FIELDS = {
    "state",
    "session_id",
    "process_id",
    "process_group_id",
    "process_birth_identity",
    "process_exit_code",
    "terminal_result",
    "remote_tool_state",
    "evidence_hash",
    "output_hash",
    "remote_output_hash",
    "image_budget_state",
}
_ATTEMPT_TERMINAL_FIELDS = _ATTEMPT_MUTABLE_FIELDS - {"state"}


def transition_exec_attempt(attempt: CodexExecAttempt, **changes) -> CodexExecAttempt:
    """Create a new validated snapshot without permitting identity replacement."""
    current = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
    if not changes or changes.keys() - _ATTEMPT_MUTABLE_FIELDS:
        raise ValueError("attempt transitions may update only lifecycle and terminal facts")
    candidate = CodexExecAttempt.model_validate(
        current.model_dump(mode="python") | changes
    )
    for field in _ATTEMPT_IDENTITY_FIELDS:
        if getattr(candidate, field) != getattr(current, field):
            raise ValueError("attempt job identity is immutable across transitions")
    if current.state in {"completed", "failed", "settled"} and any(
        getattr(candidate, field) != getattr(current, field)
        for field in _ATTEMPT_TERMINAL_FIELDS
    ):
        raise ValueError("terminal attempt evidence cannot be rewritten")
    if candidate.state != current.state and candidate.state not in _ATTEMPT_TRANSITIONS[current.state]:
        raise ValueError("attempt lifecycle transition is not allowed")
    return candidate


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
        elif len(self.image_evidence) != self.expected_image_outputs or self.remote_tool_state != "completed":
            raise ValueError("image receipt must prove every frozen ImageGen output")
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
        "not_found", "spawn_intent", "running", "outcome_unknown", "cancel_requested",
        "completed", "failed", "settled",
    ]
    attempt: CodexExecAttempt | None = None
    receipt: CodexExecReceipt | None = None

    @model_validator(mode="after")
    def terminal_receipt_is_exact(self):
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
