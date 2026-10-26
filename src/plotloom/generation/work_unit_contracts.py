"""Frozen work-unit prompt provenance and compiled request handoff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain import StageName
from .contracts import RenderedPrompt
from .correction_contract import (
    CORRECTION_DIRECTIVE_REGISTRY_VERSION,
    CORRECTION_EVIDENCE_PROJECTION_VERSION,
    CORRECTION_ISSUE_SELECTION_VERSION,
    CORRECTION_POLICY_VERSION,
    CORRECTION_RESPONSE_SCHEMA_VERSION,
)
from .dialogue_capacity import DialogueCapacityNodeGuidance
from plotloom.generation.planning_contracts import WorkUnitSelectorKind
from .repair_facts import SemanticRepairFact
from .storyboard_timing_repair import StoryboardTimingGuidance
from .validation import ValidationAdapter

WORK_UNIT_PROMPT_CONTRACT_VERSION = "m1.15"

FRAGMENT_ID_BINDING_VERSION = "fragment_ids.v1"

AUDIO_EVENT_ID_BINDING_VERSION = "audio_event_ids.v1"

STORYBOARD_PRIMARY_COVERAGE_BINDING_VERSION = "storyboard_primary_coverage.v1"

SCENE_BEATS_FRAGMENT_SCHEMA_ID = "scene_beats.fragment.v13"

STORYBOARD_FRAGMENT_SCHEMA_ID = "storyboard.fragment.v6"


class WorkUnitContractError(ValueError):
    """A planned unit cannot be rendered or bound at the trusted boundary."""

    def __init__(
        self, message: str, *, code: str = "contract.work_unit_invalid"
    ) -> None:
        self.code = code
        super().__init__(message)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WorkUnitPromptContract(_FrozenModel):
    """Compact public provenance for a compiled unit request.

    The fields identify the exact public prompt/schema contract without
    duplicating user text or server-managed canonical objects into traces.
    Scene Beats additionally carries its small deterministic capacity guidance
    so a later bounded correction can obey the same frozen limits.
    """

    contract_version: str
    correction_policy_version: str
    correction_directive_registry_version: str
    correction_evidence_projection_version: str
    correction_issue_selection_version: str
    correction_response_schema_version: str
    # These hashes are correction-variant provenance.  Primary attempts have
    # no selected directives/evidence overlay; correction attempts require all
    # four and bind the exact issue selection, prompt projection, and narrowed
    # response schema.
    correction_directive_set_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    correction_evidence_projection_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    correction_issue_selection_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    correction_response_schema_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    correction_ordinal: int | None = Field(default=None, ge=1, le=2)
    correction_strategy: (
        Literal["repair_previous_final", "reconstruct_from_schema"] | None
    ) = None
    stage_plan_hash: str = Field(min_length=1)
    work_unit_id: str = Field(min_length=1)
    stage: StageName
    selector_kind: WorkUnitSelectorKind
    selector_id: str = Field(min_length=1)
    prompt_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    prompt_spec_hash: str = Field(min_length=1)
    schema_id: str = Field(min_length=1)
    schema_hash: str = Field(min_length=1)
    variables_hash: str = Field(min_length=1)
    rendered_hash: str = Field(min_length=1)
    work_unit_input_hash: str = Field(min_length=1)
    dependency_hash: str = Field(min_length=1)
    dialogue_timing_profile_version: str | None = None
    dialogue_timing_profile_hash: str | None = None
    scene_timing_allocation_version: str | None = None
    scene_timing_allocation_hash: str | None = None
    node_duration_budget_units: int | None = Field(default=None, ge=1)
    dialogue_capacity_policy_version: str | None = None
    dialogue_capacity_plan_hash: str | None = None
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None = None
    join_state_value_contract_version: str | None = None
    join_state_value_contract_hash: str | None = None
    edge_entry_state_contract_version: str | None = None
    edge_entry_state_contract_hash: str | None = None
    # Current Storyboard corrections require a tiny projection of sealed cue
    # timings and the selected scene cap.  It contains no dialogue text,
    # provider response, secret, or mutable project data.
    storyboard_timing_guidance: StoryboardTimingGuidance | None = None
    unit_dependency_hash: str = Field(min_length=1)
    fragment_id_binding_version: str = FRAGMENT_ID_BINDING_VERSION
    audio_event_id_binding_version: str | None
    storyboard_primary_coverage_binding_version: str | None = None

    def snapshot_dump(self) -> dict[str, Any]:
        """Serialize the complete current prompt contract."""
        return self.model_dump(mode="json", by_alias=True)

    @model_validator(mode="after")
    def validate_correction_schedule(self) -> WorkUnitPromptContract:
        """Keep primary and correction provenance structurally unambiguous."""

        if self.contract_version != WORK_UNIT_PROMPT_CONTRACT_VERSION:
            raise ValueError("unsupported work-unit prompt contract version")
        has_ordinal = self.correction_ordinal is not None
        has_strategy = self.correction_strategy is not None
        if has_ordinal != has_strategy:
            raise ValueError(
                "correction_ordinal and correction_strategy must be set together"
            )
        if has_ordinal:
            expected_strategy = {
                1: "repair_previous_final",
                2: "reconstruct_from_schema",
            }[self.correction_ordinal]
            if self.correction_strategy != expected_strategy:
                raise ValueError(
                    "correction_strategy does not match correction_ordinal"
                )
        correction_versions = (
            self.correction_directive_registry_version,
            self.correction_evidence_projection_version,
            self.correction_issue_selection_version,
            self.correction_response_schema_version,
        )
        if self.correction_policy_version != CORRECTION_POLICY_VERSION:
            raise ValueError(
                "current work-unit contracts require the current correction policy"
            )
        expected_versions = (
            CORRECTION_DIRECTIVE_REGISTRY_VERSION,
            CORRECTION_EVIDENCE_PROJECTION_VERSION,
            CORRECTION_ISSUE_SELECTION_VERSION,
            CORRECTION_RESPONSE_SCHEMA_VERSION,
        )
        if correction_versions != expected_versions:
            raise ValueError(
                "current work-unit contracts require the current correction compiler versions"
            )
        correction_hashes = (
            self.correction_directive_set_hash,
            self.correction_evidence_projection_hash,
            self.correction_issue_selection_hash,
            self.correction_response_schema_hash,
        )
        has_all_correction_hashes = all(
            value is not None for value in correction_hashes
        )
        if (
            any(value is not None for value in correction_hashes)
            != has_all_correction_hashes
        ):
            raise ValueError("correction compiler hashes must be set together")
        if has_ordinal != has_all_correction_hashes:
            raise ValueError(
                "correction attempts and correction compiler hashes must be set together"
            )
        has_timing_version = self.dialogue_timing_profile_version is not None
        has_timing_hash = self.dialogue_timing_profile_hash is not None
        if has_timing_version != has_timing_hash:
            raise ValueError(
                "dialogue timing profile version and hash must be set together"
            )
        if self.stage == StageName.SCENE_BEATS and not has_timing_version:
            raise ValueError("Scene Beats contracts require a dialogue timing profile")
        if self.stage != StageName.SCENE_BEATS and has_timing_version:
            raise ValueError("dialogue timing profiles only belong to Scene Beats")
        timing_allocation_values = (
            self.scene_timing_allocation_version,
            self.scene_timing_allocation_hash,
            self.node_duration_budget_units,
        )
        has_timing_allocation = all(
            value is not None for value in timing_allocation_values
        )
        if (
            any(value is not None for value in timing_allocation_values)
            != has_timing_allocation
        ):
            raise ValueError("scene timing allocation fields must be set together")
        if self.stage == StageName.SCENE_BEATS and not has_timing_allocation:
            raise ValueError("Scene Beats contracts require a scene timing allocation")
        if self.stage != StageName.SCENE_BEATS and has_timing_allocation:
            raise ValueError("scene timing allocations only belong to Scene Beats")
        capacity_values = (
            self.dialogue_capacity_policy_version,
            self.dialogue_capacity_plan_hash,
            self.dialogue_capacity_guidance,
        )
        has_capacity = all(value is not None for value in capacity_values)
        if any(value is not None for value in capacity_values) != has_capacity:
            raise ValueError("dialogue capacity fields must be set together")
        if self.stage == StageName.SCENE_BEATS and not has_capacity:
            raise ValueError("Scene Beats contracts require dialogue capacity")
        if self.stage != StageName.SCENE_BEATS and has_capacity:
            raise ValueError("dialogue capacity only belongs to Scene Beats")
        if has_capacity:
            assert self.dialogue_capacity_guidance is not None
            if self.dialogue_capacity_guidance.node_id != self.selector_id:
                raise ValueError(
                    "dialogue capacity guidance must match the selected Story Graph node"
                )
        has_join_version = self.join_state_value_contract_version is not None
        has_join_hash = self.join_state_value_contract_hash is not None
        if has_join_version != has_join_hash:
            raise ValueError(
                "join state value contract version and hash must be set together"
            )
        has_join_contract = has_join_version and has_join_hash
        if self.stage == StageName.SCENE_BEATS and not has_join_contract:
            raise ValueError(
                "current Scene Beats contracts require exact join state values"
            )
        if self.stage != StageName.SCENE_BEATS and has_join_contract:
            raise ValueError("join state value contracts only belong to Scene Beats")
        has_edge_entry_version = self.edge_entry_state_contract_version is not None
        has_edge_entry_hash = self.edge_entry_state_contract_hash is not None
        if has_edge_entry_version != has_edge_entry_hash:
            raise ValueError(
                "edge entry state contract version and hash must be set together"
            )
        has_edge_entry_contract = has_edge_entry_version and has_edge_entry_hash
        if self.stage == StageName.SCENE_BEATS and not has_edge_entry_contract:
            raise ValueError(
                "current Scene Beats contracts require exact typed edge-entry states"
            )
        if self.stage != StageName.SCENE_BEATS and has_edge_entry_contract:
            raise ValueError("edge entry state contracts only belong to Scene Beats")
        if (
            self.stage == StageName.STORYBOARD
            and self.storyboard_timing_guidance is None
        ):
            raise ValueError("current Storyboard contracts require timing guidance")
        if (
            self.stage != StageName.STORYBOARD
            and self.storyboard_timing_guidance is not None
        ):
            raise ValueError("Storyboard timing guidance only belongs to Storyboard")
        if (
            self.storyboard_timing_guidance is not None
            and self.storyboard_timing_guidance.scene_id != self.selector_id
        ):
            raise ValueError("Storyboard timing guidance must match the selected scene")
        has_audio_event_binding = self.audio_event_id_binding_version is not None
        if self.stage == StageName.STORYBOARD and not has_audio_event_binding:
            raise ValueError(
                "current Storyboard contracts require audio event ID provenance"
            )
        if self.stage != StageName.STORYBOARD and has_audio_event_binding:
            raise ValueError("audio event ID provenance only belongs to Storyboard")
        if (
            has_audio_event_binding
            and self.audio_event_id_binding_version != AUDIO_EVENT_ID_BINDING_VERSION
        ):
            raise ValueError("unsupported audio event ID binding version")
        return self


@dataclass(frozen=True)
class CompiledWorkUnitRequest:
    """Pure hand-off object consumed later by Pipeline/Provider adapters."""

    rendered: RenderedPrompt
    validator: ValidationAdapter[Any]
    contract: WorkUnitPromptContract
    response_schema: dict[str, Any]
    # Audit-only correction selection. The runner persists this beside the
    # rendered messages but never sends it through a provider adapter.
    audit_issue_selection: dict[str, Any] | None = None
    # Executable exact facts are retained only in memory so trusted
    # application validation can enforce them even when a provider does not
    # support native JSON Schema. Recovery re-derives them from immutable
    # validation evidence; they are never silently reconstructed from prose.
    correction_repair_facts: tuple[SemanticRepairFact, ...] = ()
