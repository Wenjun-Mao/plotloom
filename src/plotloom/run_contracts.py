from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator

from plotloom.contract_identity import new_id, utc_now
from plotloom.domain_base import CamelModel
from plotloom.provider_snapshot import validate_public_provider_snapshot
from plotloom.stage_contracts import STAGE_ORDER, CanonicalSnapshot, StageName


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    QUARANTINED = "quarantined"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_RUN_STATUSES: frozenset[RunStatus] = frozenset(
    {
        RunStatus.SUCCEEDED,
        RunStatus.QUARANTINED,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    }
)


class RunKind(str, Enum):
    PIPELINE = "pipeline"
    REBUILD = "rebuild"
    REPAIR = "repair"


class AttemptStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationAttemptKind(str, Enum):
    """Why a durable provider attempt exists within one frozen work unit."""

    PRIMARY = "primary"
    CORRECTION = "correction"


class WorkUnitStatus(str, Enum):
    """Lifecycle of one bounded provider work unit.

    This is deliberately separate from ``AttemptStatus``: a unit may have
    several attempts over its lifetime, while an ambiguous dispatched attempt
    leaves the unit in ``OUTCOME_UNKNOWN`` and must not be replayed blindly.
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    CANCELLED = "cancelled"
    OUTCOME_UNKNOWN = "outcome_unknown"


TERMINAL_WORK_UNIT_STATUSES: frozenset[WorkUnitStatus] = frozenset(
    {
        WorkUnitStatus.SUCCEEDED,
        WorkUnitStatus.FAILED,
        WorkUnitStatus.QUARANTINED,
        WorkUnitStatus.CANCELLED,
        WorkUnitStatus.OUTCOME_UNKNOWN,
    }
)


class WorkUnitFailureDisposition(str, Enum):
    """Explicit terminal meaning of a known failed work-unit attempt.

    Stable outcome codes explain what happened, but they are deliberately not
    parsed as an implicit state classifier. The application boundary must say
    whether it rejected model content for review or recorded an execution
    failure.
    """

    FAILED = "failed"
    QUARANTINED = "quarantined"


class LatestRunSummary(CamelModel):
    id: str
    kind: RunKind
    status: RunStatus
    requested_stages: list[StageName]
    created_at: datetime
    finished_at: datetime | None = None


class RepairSource(CamelModel):
    """Exact immutable evidence selected when an explicit repair is enqueued."""

    failed_attempt_id: Annotated[str, Field(min_length=1)]
    response_artifact_id: Annotated[str, Field(min_length=1)]
    validation_artifact_id: Annotated[str, Field(min_length=1)]
    reused_candidate_artifact_ids: dict[StageName, str] = Field(default_factory=dict)

    @field_validator("reused_candidate_artifact_ids")
    @classmethod
    def validate_candidate_ids(
        cls, value: dict[StageName, str]
    ) -> dict[StageName, str]:
        if any(not artifact_id.strip() for artifact_id in value.values()):
            raise ValueError("reused candidate artifact IDs must not be blank")
        return value


class GenerationRun(CamelModel):
    id: str = Field(default_factory=new_id)
    project_id: str
    kind: RunKind
    parent_run_id: str | None = None
    repair_stage: StageName | None = None
    repair_source: RepairSource | None = None
    work_unit_repair_scope_id: str | None = None
    provider_snapshot: dict[str, Any] = Field(default_factory=dict)
    requested_stages: list[StageName]
    status: RunStatus = RunStatus.QUEUED
    canonical_snapshot: CanonicalSnapshot
    instructions: str | None = None
    legacy_unsealed: bool = False
    result_revision_ids: list[str] = Field(default_factory=list)
    error: str | None = None
    failure_code: str | None = None
    failed_stage: StageName | None = None
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("provider_snapshot", mode="before")
    @classmethod
    def validate_provider_snapshot(cls, value: Any) -> dict[str, Any]:
        return validate_public_provider_snapshot(value)

    @model_validator(mode="after")
    def validate_repair_lineage(self) -> GenerationRun:
        if not self.requested_stages:
            raise ValueError("generation runs require at least one requested stage")
        if len(self.requested_stages) != len(set(self.requested_stages)):
            raise ValueError("requested_stages must not contain duplicates")
        if self.requested_stages != [
            stage for stage in STAGE_ORDER if stage in self.requested_stages
        ]:
            raise ValueError("requested_stages must follow canonical stage order")
        first_index = STAGE_ORDER.index(self.requested_stages[0])
        expected_range = list(
            STAGE_ORDER[first_index : first_index + len(self.requested_stages)]
        )
        if self.requested_stages != expected_range:
            raise ValueError(
                "requested_stages must form one contiguous canonical stage range"
            )
        if self.kind == RunKind.REPAIR:
            if self.parent_run_id is None or self.repair_stage is None:
                raise ValueError("repair runs require parentRunId and repairStage")
            if self.repair_stage not in self.requested_stages:
                raise ValueError("repairStage must belong to requestedStages")
            if self.work_unit_repair_scope_id is not None:
                if self.repair_source is not None:
                    raise ValueError(
                        "exact work-unit repairs cannot carry legacy repairSource"
                    )
                return self
            if self.repair_source is None:
                if self.status not in TERMINAL_RUN_STATUSES:
                    raise ValueError("non-terminal repair runs require repairSource")
                return self
            reused_stages = set(self.repair_source.reused_candidate_artifact_ids)
            repair_index = self.requested_stages.index(self.repair_stage)
            expected_reused = set(self.requested_stages[:repair_index])
            if reused_stages != expected_reused:
                raise ValueError(
                    "repairSource must freeze one candidate for every reused requested stage"
                )
        elif (
            self.parent_run_id is not None
            or self.repair_stage is not None
            or self.repair_source is not None
            or self.work_unit_repair_scope_id is not None
        ):
            raise ValueError("only repair runs may carry repair lineage")
        return self


class GenerationAttempt(CamelModel):
    id: str = Field(default_factory=new_id)
    run_id: str
    work_unit_id: str | None = None
    stage: StageName
    attempt_number: Annotated[int, Field(ge=1)]
    attempt_kind: GenerationAttemptKind = GenerationAttemptKind.PRIMARY
    source_attempt_id: str | None = None
    status: AttemptStatus
    provider: str | None = None
    model: str | None = None
    error: str | None = None
    dispatched_at: datetime | None = None
    response_persisted_at: datetime | None = None
    provider_request_id: str | None = None
    outcome_unknown: bool = False
    outcome_code: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None


class StartupRecoveryPlan(CamelModel):
    """One-shot durable reconciliation actions for the local process runners."""

    resubmit_run_ids: list[str] = Field(default_factory=list)
    resubmit_media_task_ids: list[str] = Field(default_factory=list)
    resume_media_poll_task_ids: list[str] = Field(default_factory=list)
    terminated_run_ids: list[str] = Field(default_factory=list)
    terminated_media_task_ids: list[str] = Field(default_factory=list)
