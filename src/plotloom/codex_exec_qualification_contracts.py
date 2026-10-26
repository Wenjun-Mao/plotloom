"""Finite, opt-in authority for one arm of the audited qualification pair."""
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .codex_exec_constants import HASH
from .codex_exec_contracts import CodexExecProfile
from .codex_exec_namespace_contracts import ExecNamespaceExecutable, ExecNamespacePath
from .codex_exec_pool_contracts import CodexExecPoolLimits
from plotloom.domain_base import CamelModel

TEXT_OPERATIONS = frozenset({
    "outline", "branches", "characters", "art", "script", "storyboard",
    "bridge-intent", "bridge-presentation",
})
IMAGE_PREFIXES = ("character-reference:", "art-reference:scene:", "art-reference:prop:", "image:")


class CodexExecQualificationBinding(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    version: Literal["plotloom.exec-qualification-arm.v1"]
    namespace_id: UUID
    pair_id: UUID
    arm: Literal["serial", "parallel"]
    application_root: ExecNamespacePath
    application_database: ExecNamespacePath
    outputs_root: ExecNamespacePath
    private_root: ExecNamespacePath
    source_root: ExecNamespacePath
    database: ExecNamespacePath
    executable: ExecNamespaceExecutable
    controls_root: ExecNamespacePath
    controls_sha256: str = Field(pattern=HASH)
    source_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    source_tree: str = Field(pattern=r"^[a-f0-9]{40}$")
    qa_pin_sha256: str = Field(pattern=HASH)
    checked_validator_identity: str = Field(pattern=HASH)
    profile: CodexExecProfile
    limits: CodexExecPoolLimits
    max_wall_seconds: Literal[5400] = 5400
    max_settlement_seconds: Literal[600] = 600
    max_text_attempts: Literal[9] = 9
    max_image_outputs: Literal[32] = 32

    @model_validator(mode="after")
    def finite_arm(self):
        expected = (1, 1, 1, 4) if self.arm == "serial" else (4, 2, 2, 4)
        names = ("max_processes", "max_text_processes", "max_image_processes", "max_queued_jobs")
        if tuple(getattr(self.limits, name) for name in names) != expected:
            raise ValueError("qualification arm capacity differs from its finite method")
        if tuple(getattr(self.profile, name) for name in names) != expected:
            raise ValueError("qualification profile differs from its arm capacity")
        roots = (self.application_root, self.outputs_root, self.private_root, self.controls_root)
        if len({root.path for root in roots}) != len(roots):
            raise ValueError("qualification roots must be distinct")
        return self


class QualificationProject(CamelModel):
    """Actual identities registered once, before their first original admission."""
    model_config = CamelModel.model_config | {"frozen": True}

    role: Literal["primary", "sidecar"]
    project_id: UUID
    run_id: UUID
    claim: str = Field(pattern=r"^[a-f0-9]{32}$")
    home: ExecNamespacePath
    database: ExecNamespacePath
    manifest_sha256: str = Field(pattern=HASH)
    policy_hash: str = Field(pattern=HASH)


class QualificationActivation(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    started_wall_ns: int = Field(ge=1, strict=True)
    started_monotonic_ns: int = Field(ge=1, strict=True)
    prior_serial_receipt_sha256: str | None = Field(default=None, pattern=HASH)
