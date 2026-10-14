"""Immutable project attempt identity and lifecycle transitions."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .codex_exec_constants import HASH, JOB_ID
from .domain import CamelModel


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
    plotloom_code_revision: str | None = Field(default=None, pattern=r"^[a-f0-9]{7,64}$")
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
                expected = "consumed" if self.remote_tool_state == "completed" else "released"
                if self.image_budget_state != expected:
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
        if self.state == "completed" and self.terminal_result != "success":
            raise ValueError("completed attempts require a successful terminal result")
        return self


_ATTEMPT_IDENTITY_FIELDS = (
    "attempt_id", "run_id", "project_id", "job_id", "operation_key", "domain",
    "request_hash", "package_hash", "profile_hash", "plotloom_code_revision",
    "reserved_image_outputs",
)
_ATTEMPT_TRANSITIONS = {
    "reserved": {"spawn_intent", "settled"},
    "spawn_intent": {"running", "outcome_unknown", "cancel_requested", "completed", "failed", "settled"},
    "running": {"outcome_unknown", "cancel_requested", "completed", "failed"},
    "outcome_unknown": {"running", "cancel_requested", "completed", "failed", "settled"},
    "cancel_requested": {"outcome_unknown", "completed", "failed", "settled"},
    "completed": {"settled"},
    "failed": {"settled"},
    "settled": set(),
}
_ATTEMPT_MUTABLE_FIELDS = {
    "state", "session_id", "process_id", "process_group_id", "process_birth_identity",
    "process_exit_code", "terminal_result", "remote_tool_state", "evidence_hash",
    "output_hash", "remote_output_hash", "image_budget_state",
}
_ATTEMPT_TERMINAL_FIELDS = _ATTEMPT_MUTABLE_FIELDS - {"state"}


def transition_exec_attempt(attempt: CodexExecAttempt, **changes) -> CodexExecAttempt:
    """Create a new validated snapshot without permitting identity replacement."""
    current = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
    if not changes or changes.keys() - _ATTEMPT_MUTABLE_FIELDS:
        raise ValueError("attempt transitions may update only lifecycle and terminal facts")
    candidate = CodexExecAttempt.model_validate(current.model_dump(mode="python") | changes)
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
