"""Explicit local capacity retirement, independent of remote settlement."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .codex_exec_pool_contracts import CodexExecPoolLimits
from .domain import CamelModel


class LocalCapacityReadiness(CamelModel):
    limits: CodexExecPoolLimits
    held_text: int = Field(ge=0)
    held_image: int = Field(ge=0)
    revoked_unknown_image_attempt_ids: list[UUID]
    retired_unknown_image_holds: int = Field(ge=0)
    image_lane_blocked: bool = Field(strict=True)
    operator_action: Literal["exec-capacity-retirement-preview"] | None = None
    remote_uncertainty_and_reservations: Literal["preserved"] = "preserved"

    @model_validator(mode="after")
    def exact_blocker(self):
        expected = (self.held_image >= self.limits.max_image_processes
                    and len(self.revoked_unknown_image_attempt_ids) == self.held_image)
        if (len(self.revoked_unknown_image_attempt_ids) != len(set(self.revoked_unknown_image_attempt_ids))
                or len(self.revoked_unknown_image_attempt_ids) > self.held_image or self.image_lane_blocked != expected
                or self.operator_action != ("exec-capacity-retirement-preview" if expected else None)):
            raise ValueError("local image capacity diagnostic differs from its retained holds")
        return self


class CapacityRetirementRequest(CamelModel):
    project_id: UUID
    attempt_id: UUID
    expected_preview_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(default="", max_length=2000)

    @field_validator("reason")
    @classmethod
    def trimmed_reason(cls, value):
        return value.strip()


class CapacityRetirementReceipt(CamelModel):
    version: Literal["plotloom.exec-local-capacity-retirement.v1"] = "plotloom.exec-local-capacity-retirement.v1"
    id: UUID
    project_id: UUID
    attempt_id: UUID
    preview_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1, max_length=2000)
    created_at: datetime
    maintenance_source_root: str
    maintenance_code_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    retained_facts: dict[str, Any]
    absence_proofs: list[dict[str, Any]]
    remote_outcome: Literal["preserved_unknown"] = "preserved_unknown"
    spending_reservations: Literal["preserved"] = "preserved"


class CapacityRetirementPreview(CamelModel):
    project_id: UUID
    attempt_id: UUID
    preview_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    eligible: bool
    blockers: list[str]
    local_capacity_state: Literal["held", "retired"]
    remote_outcome: Literal["preserved_unknown"] = "preserved_unknown"
    image_budget_state: Literal["reserved", "consumed", "released"]
    reserved_image_outputs: int = Field(ge=1)
    spending_reservations: Literal["preserved"] = "preserved"
    already_retired: bool = False
    receipt: CapacityRetirementReceipt | None = None
