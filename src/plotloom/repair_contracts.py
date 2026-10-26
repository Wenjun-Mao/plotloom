from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from plotloom.contract_identity import utc_now
from plotloom.domain_base import CamelModel
from plotloom.run_contracts import GenerationRun
from plotloom.stage_contracts import StageName


class FragmentReuseKind(str, Enum):
    """Why a child repair run can reuse a verified parent fragment."""

    UPSTREAM = "upstream"
    SIBLING = "sibling"


class FrozenFragmentReuseSource(CamelModel):
    """One parent candidate frozen into an exact repair scope.

    This is deliberately metadata-only.  The candidate and its complete
    producer evidence remain immutable artifacts owned by the parent run;
    a child may only create a separately-owned, trusted re-binding through a
    corresponding :class:`FragmentReuseBinding`.
    """

    kind: FragmentReuseKind
    stage: StageName
    source_work_unit_id: str = Field(min_length=1)
    source_stage_plan_id: str = Field(min_length=1)
    source_stage_plan_hash: str = Field(min_length=1)
    source_generation_plan_hash: str = Field(min_length=1)
    source_selector: dict[str, Any]
    source_dependency_hash: str = Field(min_length=1)
    source_unit_dependency_hash: str = Field(min_length=1)
    source_input_hash: str = Field(min_length=1)
    source_producer_attempt_id: str = Field(min_length=1)
    source_response_artifact_id: str = Field(min_length=1)
    source_validation_artifact_id: str = Field(min_length=1)
    source_candidate_artifact_id: str = Field(min_length=1)
    source_candidate_content_hash: str = Field(min_length=1)


class WorkUnitRepairScope(CamelModel):
    """Immutable evidence and contract boundary for one exact child repair."""

    child_run_id: str = Field(min_length=1)
    parent_run_id: str = Field(min_length=1)
    target_work_unit_id: str = Field(min_length=1)
    stage: StageName
    source_generation_plan_hash: str = Field(min_length=1)
    source_provider_profile_hash: str = Field(min_length=1)
    source_story_graph_topology_hash: str | None = None
    source_stage_plan_id: str = Field(min_length=1)
    source_stage_plan_hash: str = Field(min_length=1)
    source_canonical_snapshot_hash: str = Field(min_length=1)
    target_selector: dict[str, Any]
    target_dependency_hash: str = Field(min_length=1)
    target_unit_dependency_hash: str = Field(min_length=1)
    target_input_hash: str = Field(min_length=1)
    failed_attempt_id: str = Field(min_length=1)
    response_artifact_id: str = Field(min_length=1)
    validation_artifact_id: str = Field(min_length=1)
    reuse_sources: list[FrozenFragmentReuseSource] = Field(default_factory=list)
    pending_sibling_work_unit_ids: list[str] = Field(default_factory=list)
    scope_hash: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class FragmentReuseBinding(CamelModel):
    """Immutable parent-to-child fragment mapping used only by exact repair."""

    id: str = Field(min_length=1)
    child_run_id: str = Field(min_length=1)
    child_stage_plan_id: str = Field(min_length=1)
    child_stage_plan_hash: str = Field(min_length=1)
    child_work_unit_id: str = Field(min_length=1)
    stage: StageName
    kind: FragmentReuseKind
    source_run_id: str = Field(min_length=1)
    source_work_unit_id: str = Field(min_length=1)
    source_stage_plan_id: str = Field(min_length=1)
    source_candidate_artifact_id: str = Field(min_length=1)
    source_candidate_content_hash: str = Field(min_length=1)
    source_stage_plan_hash: str = Field(min_length=1)
    source_selector: dict[str, Any]
    source_dependency_hash: str = Field(min_length=1)
    source_unit_dependency_hash: str = Field(min_length=1)
    source_input_hash: str = Field(min_length=1)
    source_producer_attempt_id: str = Field(min_length=1)
    source_response_artifact_id: str = Field(min_length=1)
    source_validation_artifact_id: str = Field(min_length=1)
    child_selector: dict[str, Any]
    child_dependency_hash: str = Field(min_length=1)
    child_unit_dependency_hash: str = Field(min_length=1)
    child_input_hash: str = Field(min_length=1)
    binding_hash: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class WorkUnitRepairEligibility(CamelModel):
    """Secret-free server decision; callers never infer repair eligibility."""

    work_unit_id: str = Field(min_length=1)
    stage: StageName
    eligible: bool
    reason_code: str | None = None


class WorkUnitRepairRunCreation(CamelModel):
    """Atomic idempotency result; only a newly-created child may be scheduled."""

    run: GenerationRun
    created: bool
