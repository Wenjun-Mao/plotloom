from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from plotloom.artifact_contracts import Artifact
from plotloom.domain_base import CamelModel
from plotloom.run_contracts import (
    AttemptStatus,
    GenerationAttempt,
    GenerationAttemptKind,
    GenerationRun,
    RunStatus,
    WorkUnitStatus,
)
from plotloom.stage_contracts import StageName


class RunTrace(CamelModel):
    run: GenerationRun
    attempts: list[GenerationAttempt] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    snapshot_is_current: bool


class GenerationPlanTrace(CamelModel):
    """Secret-free run-level plan persisted alongside a generation run."""

    run_id: str
    plan_hash: str
    plan: dict[str, Any]


class StagePlanTrace(CamelModel):
    """One immutable stage plan and its resolved dependency fingerprint."""

    id: str
    run_id: str
    stage: StageName
    stage_plan_hash: str
    dependency_hash: str
    plan: dict[str, Any]


class GenerationWorkUnitTrace(CamelModel):
    """Durable work-unit record exposed for diagnosis, not prompt execution."""

    id: str
    run_id: str
    stage_plan_id: str
    stage: StageName
    sequence: Annotated[int, Field(ge=1)]
    selector: dict[str, Any]
    input_hash: str
    dependency_hash: str
    unit_dependency_hash: str
    budget: dict[str, Any]
    estimated_input_tokens: Annotated[int, Field(ge=0)]
    context_window_tokens: Annotated[int, Field(ge=1)]
    status: WorkUnitStatus


class RunProgressAttempt(CamelModel):
    attempt_id: str
    attempt_number: Annotated[int, Field(ge=1)]
    attempt_kind: GenerationAttemptKind
    source_attempt_id: str | None = None
    status: AttemptStatus
    outcome_code: str | None = None
    outcome_unknown: bool = False
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    started_at: datetime
    finished_at: datetime | None = None


class RunProgressUnit(CamelModel):
    work_unit_id: str
    stage: StageName
    sequence: Annotated[int, Field(ge=1)]
    status: WorkUnitStatus
    max_attempts: Annotated[int, Field(ge=1)]
    latest_attempt: RunProgressAttempt | None = None
    sealed: bool
    repair_eligible: bool
    repair_reason_code: str | None = None


class RunProgressStage(CamelModel):
    stage: StageName
    stage_plan_id: str | None = None
    stage_plan_hash: str | None = None
    sealed: bool
    unit_count: Annotated[int, Field(ge=0)]
    completed_unit_count: Annotated[int, Field(ge=0)]
    quarantined_unit_count: Annotated[int, Field(ge=0)]
    repair_eligible_unit_ids: list[str] = Field(default_factory=list)


class RunProgressActions(CamelModel):
    can_resume: bool
    can_cancel: bool
    can_rebuild_stage: bool
    repair_eligible: bool


class RunProgress(CamelModel):
    """Small polling projection; never includes prompt, response, or payload."""

    run_id: str
    status: RunStatus
    failure_code: str | None = None
    failed_stage: StageName | None = None
    stage_progress: list[RunProgressStage] = Field(default_factory=list)
    work_units: list[RunProgressUnit] = Field(default_factory=list)
    actions: RunProgressActions


class SealedStageAggregateTrace(CamelModel):
    """Immutable exact-manifest aggregate eligible for canonical installation."""

    id: str
    run_id: str
    stage_plan_id: str
    stage: StageName
    manifest_hash: str
    manifest: dict[str, Any]
    payload: dict[str, Any]
    created_at: datetime


class StoryGraphTopologyTrace(CamelModel):
    """Frozen deterministic graph structure bound to one generation run."""

    run_id: str
    generation_plan_hash: str
    topology_hash: str
    topology: dict[str, Any]
    created_at: datetime


class RunExecutionTrace(CamelModel):
    """Additive work-unit evidence; the legacy RunTrace remains stable."""

    generation_plan: GenerationPlanTrace | None = None
    story_graph_topology: StoryGraphTopologyTrace | None = None
    stage_plans: list[StagePlanTrace] = Field(default_factory=list)
    work_units: list[GenerationWorkUnitTrace] = Field(default_factory=list)
    sealed_aggregates: list[SealedStageAggregateTrace] = Field(default_factory=list)
