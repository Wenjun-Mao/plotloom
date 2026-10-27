"""Actual eight-operation evidence accounting and closed native Alpha receipts."""
from collections.abc import Iterable
from hashlib import sha256
from typing import Literal

from pydantic import Field, StrictBool, model_validator

from .acceptance_metrics import SAFE_ISSUE_CODE
from .alpha_workloads import ALPHA_ACCEPTANCE_VERSION, NATIVE_OPERATIONS, SAMPLE_KEYS
from .domain_base import CamelModel
from .generation.prompts import canonical_json
from .stage_contracts import STAGE_ORDER, StageStatus
from .text_correction_contracts import logical_checkpoint

HASH = r"^[a-f0-9]{64}$"


class NativeOperationReceipt(CamelModel):
    stage: Literal["outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation"]
    attempt_count: int = Field(strict=True, ge=0)
    accepted: StrictBool
    first_pass: StrictBool
    binding_hash: str = Field(pattern=HASH)

    @model_validator(mode="after")
    def exact_accounting(self):
        if self.first_pass != (self.accepted and self.attempt_count == 1):
            raise ValueError("first pass must represent one accepted actual native attempt")
        if self.attempt_count > (2 if self.stage in {"outline", "characters", "art", "script"} else 1):
            raise ValueError("native Alpha cannot expand the production correction policy")
        return self


class NativeSampleReceipt(CamelModel):
    version: Literal["alpha_native_codex_three_story.v3"] = ALPHA_ACCEPTANCE_VERSION
    commit: str = Field(pattern=r"^[a-f0-9]{40}$")
    contract_hash: str = Field(pattern=HASH)
    profile_hash: str = Field(pattern=HASH)
    sample_id: str
    status: Literal["installed", "blocked", "incomplete", "outcome_unknown"]
    operations: tuple[NativeOperationReceipt, ...]
    content_hash: str | None = Field(default=None, pattern=HASH)
    installation_hash: str | None = Field(default=None, pattern=HASH)
    duration_milliseconds: int = Field(strict=True, ge=0)
    issue_codes: tuple[str, ...]

    @model_validator(mode="after")
    def closed_identity(self):
        if self.sample_id not in SAMPLE_KEYS or tuple(row.stage for row in self.operations) != NATIVE_OPERATIONS:
            raise ValueError("native sample must identify one exact matrix cell and all eight operations")
        if any(not SAFE_ISSUE_CODE.fullmatch(code) for code in self.issue_codes):
            raise ValueError("receipt issue codes must be source-safe identifiers")
        if self.status == "installed" and (self.installation_hash is None or self.content_hash is None or self.issue_codes
                or not all(row.accepted for row in self.operations)):
            raise ValueError("installed receipt requires eight accepted native operations and current readback")
        return self


def native_qualification_issue_codes(receipts: Iterable[dict]):
    issues = set()
    parsed = []
    for raw in receipts:
        try:
            parsed.append(NativeSampleReceipt.model_validate(raw))
        except ValueError:
            issues.add("alpha.receipt.schema")
    if len(parsed) != 9 or {row.sample_id for row in parsed} != set(SAMPLE_KEYS):
        issues.add("alpha.sample_matrix")
    if any(len({getattr(row, field) for row in parsed}) != 1
            for field in ("commit", "contract_hash", "profile_hash")):
        issues.add("alpha.execution_identity")
    if any(row.status != "installed" or row.issue_codes for row in parsed):
        issues.add("alpha.installation")
    if sum(op.first_pass for row in parsed for op in row.operations) < 60:
        issues.add("alpha.first_pass")
    return sorted(issues)


def _hash(value):
    return sha256(canonical_json(value).encode()).hexdigest()


def installed_text_readback(store):
    """Recheck all four current heads and the actual Bridge admission binding."""
    state = store.production_bridge_state()
    installation = state.installation
    heads = store.authoring.list_stage_envelopes(store.manifest.project_id)
    by_stage = {item.head.stage: item for item in heads}
    if (installation is None or installation.status != "current"
            or set(by_stage) != set(STAGE_ORDER)
            or any(item.head.status != StageStatus.READY or item.payload is None for item in heads)):
        raise ValueError("native Alpha requires all four current installed canonical heads")
    result = {"installation": installation.model_dump(mode="json", by_alias=True),
        "heads": {stage.value: by_stage[stage].head.model_dump(mode="json", by_alias=True) for stage in STAGE_ORDER}}
    for stage in STAGE_ORDER:
        if installation.installed_stage_revisions.get(stage.value) != by_stage[stage].head.revision:
            raise ValueError("Bridge installed revisions differ from current heads")
    return result


def collect_native_evidence(store, view, *, snapshot, contract_hash, sample_id, duration_ms):
    """Read exact existing reservation/receipt owners; do not infer provider success."""
    private = {"run": view.model_dump(mode="json", by_alias=True), "operations": {}}
    operations = []
    for stage in NATIVE_OPERATIONS:
        checkpoints = [c for c in view.checkpoints if c["operationKey"] == stage
            or c["operationKey"].startswith(stage + ":correction:")]
        bindings = []
        for checkpoint in checkpoints:
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, checkpoint["operationKey"])
            if attempt is not None:
                bindings.append({"checkpoint": checkpoint,
                    "attempt": attempt.model_dump(mode="json", by_alias=True),
                    "receipt": receipt.model_dump(mode="json", by_alias=True) if receipt else None})
        current = logical_checkpoint(view, stage)
        accepted = bool(current and current["state"] == "adopted" and bindings)
        if accepted:
            last = next((b for b in bindings if b["checkpoint"]["operationKey"] == current["operationKey"]), None)
            accepted = bool(last and last["receipt"] and last["receipt"].get("textValidation")
                and last["attempt"]["state"] == "completed"
                and last["receipt"]["processExitCode"] == 0
                and last["receipt"]["profileHash"] == snapshot["profileHash"]
                and last["receipt"]["plotloomCodeRevision"] == snapshot["commit"])
        private["operations"][stage] = bindings
        operations.append(NativeOperationReceipt(stage=stage, attempt_count=len(bindings), accepted=accepted,
            first_pass=accepted and len(bindings) == 1, binding_hash=_hash(bindings)))
    installed = any(c["operationKey"] == "installation" for c in view.checkpoints)
    private["readback"] = installed_text_readback(store) if installed else None
    status = "installed" if installed else ("outcome_unknown" if any(c["state"] == "outcome_unknown" for c in view.checkpoints)
        else "blocked" if view.state == "blocked" else "incomplete")
    code = (view.blocker or {}).get("code")
    issues = () if installed else ((code if code and SAFE_ISSUE_CODE.fullmatch(code) else "alpha.incomplete"),)
    from .alpha_publication import content_only_review_payload
    content_hash = None
    # Content files include one canonical trailing newline; bind those exact bytes.
    if installed:
        content_hash = sha256((canonical_json(content_only_review_payload(store)) + "\n").encode()).hexdigest()
    receipt = NativeSampleReceipt(commit=snapshot["commit"], contract_hash=contract_hash,
        profile_hash=snapshot["profileHash"], sample_id=sample_id, status=status, operations=tuple(operations),
        installation_hash=_hash(private["readback"]) if installed else None,
        content_hash=content_hash, duration_milliseconds=duration_ms, issue_codes=issues)
    return receipt, private
