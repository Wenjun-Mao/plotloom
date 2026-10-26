"""Strict immutable allocation for one separately released Outline admission."""
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from plotloom.codex_exec_namespace_contracts import (
    CodexExecNamespaceBinding,
    ExecNamespacePath,
)
from plotloom.domain_base import CamelModel

HASH = r"^[a-f0-9]{64}$"


class PaidSourceIdentity(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    tree: str = Field(pattern=r"^[a-f0-9]{40}$")
    workflow_closure_sha256: str = Field(pattern=HASH)
    bundle_source_identity_sha256: str = Field(pattern=HASH)


class PaidFileIdentity(ExecNamespacePath):
    sha256: str = Field(pattern=HASH)
    size: int = Field(ge=1, strict=True)


class PaidClaimEdges(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    paused_claim: str = Field(pattern=r"^[a-f0-9]{32}$")
    receiver_claim: str = Field(pattern=r"^[a-f0-9]{32}$")
    paused_revision: int = Field(ge=1, strict=True)
    claimed_revision: int = Field(ge=2, strict=True)
    resumed_revision: int = Field(ge=3, strict=True)

    @model_validator(mode="after")
    def exact_edges(self):
        if (self.paused_claim == self.receiver_claim
                or self.claimed_revision != self.paused_revision + 1
                or self.resumed_revision != self.claimed_revision + 1):
            raise ValueError("paid Outline requires distinct known claim and resume revision edges")
        return self


class PaidValidatorRuntime(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    root: str
    interpreter: str
    identity_hash: str = Field(pattern=HASH)
    qa_pin_sha256: str = Field(pattern=HASH)


class PaidOutlineAllocation(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    version: Literal["plotloom.paid-outline-once.v1"]
    authority: Literal["paid_outline_once"]
    allocation_id: UUID
    nonce: str = Field(pattern=r"^[a-z0-9-]{16,100}$")
    data_root: ExecNamespacePath
    owner_marker: PaidFileIdentity
    bundle_root: ExecNamespacePath
    phase_root: ExecNamespacePath
    project_home: ExecNamespacePath
    project_manifest: PaidFileIdentity
    project_database: ExecNamespacePath
    application_database: ExecNamespacePath
    namespace: CodexExecNamespaceBinding
    namespace_binding_sha256: str = Field(pattern=HASH)
    source: PaidSourceIdentity
    validator_runtime: PaidValidatorRuntime
    claim_edges: PaidClaimEdges
    expected_checkpoint_revision: int = Field(ge=1, strict=True)
    policy_hash: str = Field(pattern=HASH)
    brief_hash: str = Field(pattern=HASH)
    material_closure: str = Field(pattern=HASH)
    brief_revision: int = Field(ge=1, strict=True)
    lifecycle_revision: int = Field(ge=1, strict=True)
    application_entries: tuple[str, ...]
    initial_admissions: Literal[1]
    image_admissions: Literal[0]
    retries: Literal[0]
    settlement_authority: Literal["hold_only"]
    canonical_adoption: Literal[False]
    later_stages: Literal[False]

    @model_validator(mode="before")
    @classmethod
    def strict_permissions(cls, value):
        if isinstance(value, dict):
            for camel, snake, expected in (("initialAdmissions", "initial_admissions", 1),
                    ("imageAdmissions", "image_admissions", 0), ("retries", "retries", 0)):
                actual = value.get(camel, value.get(snake))
                if type(actual) is not int or actual != expected:
                    raise ValueError("strict one-admission, zero-image, zero-retry permission required")
            for camel, snake in (("canonicalAdoption", "canonical_adoption"), ("laterStages", "later_stages")):
                if value.get(camel, value.get(snake)) is not False:
                    raise ValueError("paid Outline cannot authorize adoption or continuation")
        return value

    @model_validator(mode="after")
    def only_outline(self):
        attempt = self.namespace.attempt
        if self.namespace.namespace_id != self.allocation_id:
            raise ValueError("allocation and supervisor namespace identity differ")
        if (attempt.domain != "text" or attempt.operation_key != "outline"
                or attempt.reserved_image_outputs != 0 or attempt.image_budget_state != "none"
                or attempt.plotloom_code_revision != self.source.revision
                or attempt.validation_plan_hash is None):
            raise ValueError("paid allocation requires its exact source-bound reserved text Outline")
        from pathlib import Path
        data = Path(self.data_root.path)
        for name, root in (("application", self.namespace.application_root),
                ("outputs", self.namespace.outputs_root), ("private", self.namespace.private_root)):
            if Path(root.path) != data / name:
                raise ValueError("paid allocation roots must be direct disposable-data children")
        if Path(self.project_home.path).parent != Path(self.namespace.outputs_root.path):
            raise ValueError("paid allocation project home escapes its outputs root")
        if self.validator_runtime.interpreter == self.namespace.executable.path:
            raise ValueError("validator interpreter cannot be the native execution executable")
        if (Path(self.owner_marker.path) != data / "owner.json"
                or Path(self.project_manifest.path) != Path(self.project_home.path) / "project.json"
                or Path(self.project_database.path) != Path(self.project_home.path) / "project.sqlite3"
                or Path(self.application_database.path) != data / "application/application.sqlite3"):
            raise ValueError("paid allocation metadata/database paths differ")
        return self
