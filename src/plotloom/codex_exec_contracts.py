"""Versioned, strict contracts for future pre-video Codex CLI executions."""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .codex_exec_constants import HASH
from .codex_exec_constants import JOB_ID as JOB_ID
from plotloom.domain_base import CamelModel
from plotloom.public_values import contains_secret_setting, contains_secret_value
from .codex_exec_capacity_contracts import LocalCapacityReadiness

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
        "plotloom.codex-exec.v4", "plotloom.codex-exec.v5", "plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8",
    ] = "plotloom.codex-exec.v4"
    executable_sha256: str = Field(pattern=HASH)
    # Observed provenance only; executable/source/evidence checks own compatibility.
    cli_version: str | None = Field(default=None, min_length=1, max_length=80)
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
    permission_profile: Literal[
        "plotloom_autopilot_delivery_v2", "plotloom_autopilot_delivery_v3", "plotloom_autopilot_delivery_v4",
        "plotloom_autopilot_delivery_v5",
    ] | None = Field(default=None, exclude_if=lambda value: value is None)
    tool_profile: Literal[
        "plotloom_autopilot_tools_v2", "plotloom_autopilot_tools_v3", "plotloom_autopilot_tools_v4"
    ] | None = Field(default=None, exclude_if=lambda value: value is None)
    text_validator_runtime_profile: Literal[
        "node_openssl_and_private_zsh_tmp_v1",
        "node_openssl_private_zsh_tmp_and_validator_aliases_v2",
        "node_openssl_private_zsh_tmp_and_checked_python_v3",
    ] | None = Field(default=None, exclude_if=lambda value: value is None)
    max_runtime_seconds: int = Field(ge=30, le=7200)
    max_event_bytes: int = Field(ge=1024, le=50_000_000)
    max_output_bytes: int = Field(ge=1024, le=500_000_000)
    max_image_outputs: int = Field(ge=0, le=4)
    max_processes: int = Field(default=1, ge=1, le=4, strict=True)
    max_text_processes: int | None = Field(default=None, ge=1, le=2, strict=True, exclude_if=lambda value: value is None)
    max_image_processes: int | None = Field(default=None, ge=1, le=2, strict=True, exclude_if=lambda value: value is None)
    max_queued_jobs: int | None = Field(default=None, ge=1, le=4, strict=True, exclude_if=lambda value: value is None)
    api_fallback: Literal[False] = False
    external_mcp_servers: Literal[False] = False
    nested_dispatch: Literal[False] = False
    text_correction_limit: int | None = Field(default=None, strict=True, ge=1, le=1, exclude_if=lambda value: value is None)
    text_correction_contract: Literal["plotloom.text-correction.v2", "plotloom.text-correction.v3"] | None = Field(default=None, exclude_if=lambda value: value is None)

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
            or self.text_validator_runtime_profile is not None
        ):
            raise ValueError("Codex Exec v4 requires its pinned auth, permission and reference-view tool profile")
        elif self.contract_version == "plotloom.codex-exec.v5" and (
            self.sandbox_profile is not None
            or self.authentication_store != "file"
            or self.permission_profile != "plotloom_autopilot_delivery_v3"
            or self.tool_profile != "plotloom_autopilot_tools_v4"
            or self.text_validator_runtime_profile != "node_openssl_and_private_zsh_tmp_v1"
        ):
            raise ValueError("Codex Exec v5 requires its exact Node and private zsh runtime profile")
        elif self.contract_version == "plotloom.codex-exec.v6" and (
            self.sandbox_profile is not None
            or self.authentication_store != "file"
            or self.permission_profile != "plotloom_autopilot_delivery_v4"
            or self.tool_profile != "plotloom_autopilot_tools_v4"
            or self.text_validator_runtime_profile != "node_openssl_private_zsh_tmp_and_validator_aliases_v2"
        ):
            raise ValueError("Codex Exec v6 requires its pinned validator evidence, runtime and permission profile")
        elif self.contract_version in {"plotloom.codex-exec.v7", "plotloom.codex-exec.v8"} and (
            self.sandbox_profile is not None
            or self.authentication_store != "file"
            or self.permission_profile != "plotloom_autopilot_delivery_v5"
            or self.tool_profile != "plotloom_autopilot_tools_v4"
            or self.text_validator_runtime_profile != "node_openssl_private_zsh_tmp_and_checked_python_v3"
        ):
            raise ValueError("Codex Exec v7/v8 require the isolated checked-lock runtime and permission profile")
        if self.contract_version == "plotloom.codex-exec.v8":
            from .codex_exec_pool_contracts import CodexExecPoolLimits
            CodexExecPoolLimits(maxProcesses=self.max_processes, maxTextProcesses=self.max_text_processes,
                maxImageProcesses=self.max_image_processes, maxQueuedJobs=self.max_queued_jobs)
        elif self.max_processes != 1 or any(value is not None for value in (
            self.max_text_processes, self.max_image_processes, self.max_queued_jobs,
        )):
            raise ValueError("retained serial profiles cannot contain pool capacity")
        selected = set(self.capabilities)
        if len(selected) != len(self.capabilities):
            raise ValueError("CLI capability pins must not contain duplicates")
        if not {"exec_json_events_v1", "session_rollout_v1", "delivery_directory_write_v1"} <= selected:
            raise ValueError("CLI profile lacks the serial executor evidence or delivery capability")
        if self.max_image_outputs and "image_gen_event_v1" not in selected:
            raise ValueError("image capacity requires the qualified native ImageGen event capability")
        if self.contract_version in {"plotloom.codex-exec.v4", "plotloom.codex-exec.v5", "plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"} and "image_reference_view_v1" not in selected:
            raise ValueError("Codex Exec v4 through v8 require typed reference-view evidence capability")
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
    """Dynamic local runtime/login readiness, separate from the frozen profile."""

    state: Literal["ready", "not_authenticated", "unavailable"]
    local_capacity: LocalCapacityReadiness | None = Field(default=None, exclude_if=lambda value: value is None)

    @property
    def ready(self) -> bool:
        return self.state == "ready"


ExecutorBinding = Annotated[
    SpecialistChatExecutor | CodexExecProfile,
    Field(discriminator="backend"),
]


from .codex_exec_attempt_contracts import (
    CodexExecAttempt as CodexExecAttempt,
)
from .codex_exec_attempt_contracts import (
    transition_exec_attempt as transition_exec_attempt,
)
from .codex_exec_receipt_contracts import (
    CodexExecHostStatus as CodexExecHostStatus,
)
from .codex_exec_receipt_contracts import (
    CodexExecImageEvidence as CodexExecImageEvidence,
)
from .codex_exec_receipt_contracts import (
    CodexExecOutputEvidence as CodexExecOutputEvidence,
)
from .codex_exec_receipt_contracts import (
    CodexExecReceipt as CodexExecReceipt,
)
from .codex_exec_receipt_contracts import (
    CodexExecReferenceViewEvidence as CodexExecReferenceViewEvidence,
)
from .codex_exec_receipt_contracts import (
    assert_receipt_matches_attempt as assert_receipt_matches_attempt,
)
from .codex_exec_receipt_contracts import (
    image_arguments_hash as image_arguments_hash,
)
from .codex_exec_receipt_contracts import (
    output_manifest_hash as output_manifest_hash,
)
