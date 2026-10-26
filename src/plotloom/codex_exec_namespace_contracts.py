"""Opt-in physical identity contract for one frozen supervisor attempt."""
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .codex_exec_constants import HASH
from .codex_exec_contracts import CodexExecAttempt, CodexExecProfile
from .codex_exec_pool_contracts import CodexExecPoolLimits
from plotloom.domain_base import CamelModel


class ExecNamespacePath(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    path: str = Field(min_length=1)
    device: int = Field(ge=0, strict=True)
    inode: int = Field(ge=1, strict=True)
    uid: int = Field(ge=0, strict=True)
    mode: int = Field(ge=0, le=0o777, strict=True)


class ExecNamespaceExecutable(ExecNamespacePath):
    sha256: str = Field(pattern=HASH)
    size: int = Field(ge=1, strict=True)


class CodexExecNamespaceBinding(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    version: Literal["plotloom.exec-one-attempt.v1"]
    namespace_id: UUID
    application_root: ExecNamespacePath
    outputs_root: ExecNamespacePath
    private_root: ExecNamespacePath
    source_root: ExecNamespacePath
    database: ExecNamespacePath
    executable: ExecNamespaceExecutable
    profile: CodexExecProfile
    limits: CodexExecPoolLimits
    attempt: CodexExecAttempt

    @model_validator(mode="after")
    def one_reserved_identity(self):
        if self.attempt.state != "reserved" or self.attempt.profile_hash != self.profile.profile_hash:
            raise ValueError("namespace requires its exact reserved attempt and profile")
        limits = self.limits
        if (limits.max_processes, limits.max_text_processes,
                limits.max_image_processes, limits.max_queued_jobs) != (1, 1, 1, 1):
            raise ValueError("one-attempt namespace requires limits 1/1/1/1")
        if (self.profile.max_processes, self.profile.max_text_processes,
                self.profile.max_image_processes, self.profile.max_queued_jobs) != (1, 1, 1, 1):
            raise ValueError("namespace profile differs from its frozen pool limits")
        roots = (self.application_root, self.outputs_root, self.private_root)
        if len({root.path for root in roots}) != 3:
            raise ValueError("namespace data roots must be distinct")
        return self
