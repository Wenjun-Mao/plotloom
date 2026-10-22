"""Strict data allocation for the fixed serial-first qualification entry."""
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator
from plotloom.codex_exec_namespace_contracts import ExecNamespacePath
from plotloom.codex_exec_qualification_contracts import CodexExecQualificationBinding
from plotloom.domain import CamelModel
if __package__ == 'handoff':
    # Source-only offline builder package; sealed entries use the flat fixed B.
    from .paid_outline_contracts import PaidFileIdentity, PaidSourceIdentity, PaidValidatorRuntime
elif __package__ in {None, ''}:
    from paid_outline_contracts import PaidFileIdentity, PaidSourceIdentity, PaidValidatorRuntime
else:
    raise RuntimeError('unregistered pair contract package origin')

HASH = r"^[a-f0-9]{64}$"


class PairArmAllocation(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    work_root: ExecNamespacePath
    namespace: CodexExecQualificationBinding
    namespace_binding_sha256: str = Field(pattern=HASH)


class QualificationPairAllocation(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}
    version: Literal["plotloom.qualification-pair-once.v1"]
    authority: Literal["qualification_pair_once"]
    allocation_id: UUID
    nonce: str = Field(pattern=r"^[a-z0-9-]{16,100}$")
    work_root: ExecNamespacePath
    bundle_root: ExecNamespacePath
    phase_root: ExecNamespacePath
    owner_marker: PaidFileIdentity
    source: PaidSourceIdentity
    validator_runtime: PaidValidatorRuntime
    inputs: tuple[PaidFileIdentity, ...] = Field(min_length=3)
    serial: PairArmAllocation
    parallel: PairArmAllocation
    text_attempt_ceiling: Literal[18] = 18
    image_output_ceiling: Literal[64] = 64
    retries: Literal[0] = 0
    extra_arms: Literal[0] = 0

    @model_validator(mode="after")
    def finite_locations(self):
        work, bundle, phase = map(Path, (self.work_root.path, self.bundle_root.path, self.phase_root.path))
        roots = (work, bundle, phase)
        if any(a == b or a in b.parents or b in a.parents for i,a in enumerate(roots) for b in roots[i+1:]):
            raise ValueError("pair code/work/transport roots must be distinct and non-nested")
        if Path(self.owner_marker.path)!=work/'owner.json':
            raise ValueError('pair owner marker must be its fixed work-root file')
        for arm in ("serial", "parallel"):
            item = getattr(self, arm)
            ns = item.namespace
            target = work / arm
            if (Path(item.work_root.path) != target or ns.arm != arm or ns.pair_id != self.allocation_id
                    or ns.controls_root != self.bundle_root or ns.source_revision != self.source.revision
                    or ns.source_tree != self.source.tree
                    or ns.qa_pin_sha256 != self.validator_runtime.qa_pin_sha256
                    or ns.checked_validator_identity != self.validator_runtime.identity_hash
                    or Path(ns.application_root.path) != target / "installation/application"
                    or Path(ns.outputs_root.path) != target / "installation/outputs"
                    or Path(ns.private_root.path) != target / "private/codex-exec"
                    or Path(ns.database.path) != target / "private/codex-exec/supervisor.sqlite3"):
                raise ValueError("pair arm source/work/namespace bindings differ")
        allowed = {work / name for name in ("plan.json", "prepared_inputs.json", "preservation_inputs.json", "current_source.json")}
        allowed.update(work / arm / "plan.json" for arm in ("serial", "parallel"))
        if {Path(item.path) for item in self.inputs} != allowed or len(self.inputs) != len(allowed):
            raise ValueError("pair inputs require the exact fixed data inventory")
        return self
