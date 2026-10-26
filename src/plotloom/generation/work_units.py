"""Compile frozen generation work units into model requests and provenance.

Compilation checks immutable inputs, derives frozen prompt guidance and renders
through actual schema/validation owners. Canonical binding, stage semantics and
repair derivation are independently owned lower-level responsibilities.
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import (
    BaseModel,
)

from ..domain import (
    CanonicalSnapshot,
    ProjectBrief,
    StageName,
    StoryGraphV2,
)
from .correction_contract import (
    CORRECTION_DIRECTIVE_REGISTRY_VERSION,
    CORRECTION_EVIDENCE_PROJECTION_VERSION,
    CORRECTION_ISSUE_SELECTION_VERSION,
    CORRECTION_POLICY_VERSION,
    CORRECTION_RESPONSE_SCHEMA_VERSION,
)
from .dialogue_capacity import (
    DialogueCapacityPlanningError,
    dialogue_timing_profile_hash,
    plan_dialogue_capacity,
)
from .fragment_validation import (
    WorkUnitFragmentValidationAdapter,
    _validator_for_unit,
)
from .frozen_join_requirements import (
    _continuity_requirements,
)
from plotloom.generation.planning_contracts import GenerationPlan, GenerationWorkUnit, PlanningError, StagePlan, assert_work_unit_input_contract, content_hash
from plotloom.generation.planning_context import work_unit_context
from .prompts import PromptRenderer, canonical_json, sha256_text
from .scene_beats_edge_entry import (
    edge_entry_state_requirements,
)
from .scene_timing_allocation import (
    SceneTimingAllocationError,
    plan_scene_timing_allocation,
)
from plotloom.generation.story_graph_topology_contracts import StoryGraphTopology
from plotloom.generation.story_graph_content_contracts import story_graph_content_fill_manifest
from .storyboard_timing_repair import (
    StoryboardTimingGuidance,
    StoryboardTimingInfeasibleError,
    build_storyboard_timing_guidance,
)
from .work_unit_contracts import (
    AUDIO_EVENT_ID_BINDING_VERSION,
    FRAGMENT_ID_BINDING_VERSION,
    STORYBOARD_PRIMARY_COVERAGE_BINDING_VERSION,
    WORK_UNIT_PROMPT_CONTRACT_VERSION,
    CompiledWorkUnitRequest,
    WorkUnitContractError,
    WorkUnitPromptContract,
)


def compile_work_unit_request(
    *,
    generation_plan: GenerationPlan,
    stage_plan: StagePlan,
    work_unit: GenerationWorkUnit,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
    brief: ProjectBrief,
    canonical_snapshot: BaseModel | Mapping[str, Any],
    instructions: str = "",
    stage_constraints: Mapping[str, Any] | None = None,
    story_graph_topology: StoryGraphTopology | None = None,
    renderer: PromptRenderer | None = None,
) -> CompiledWorkUnitRequest:
    """Compile one immutable work unit without a provider or persistence call.

    ``canonical_snapshot`` and ``instructions`` are checked against the
    enqueue-time GenerationPlan.  ``dependencies`` are rebuilt through
    ``planning.work_unit_context`` and checked against the unit hash.  Thus a
    prompt cannot quietly widen from one node/scene into a full later-stage
    aggregate.
    """

    _assert_unit_membership(generation_plan, stage_plan, work_unit)
    if work_unit.stage == StageName.SCENE_BEATS:
        graph = dependencies.get(StageName.STORY_GRAPH)
        if not isinstance(graph, StoryGraphV2):
            raise WorkUnitContractError(
                "Scene Beats compilation requires a sealed StoryGraph"
            )
        try:
            expected_timing = plan_scene_timing_allocation(graph=graph, brief=brief)
        except SceneTimingAllocationError as exc:
            raise WorkUnitContractError(str(exc)) from exc
        if stage_plan.scene_timing_allocation != expected_timing:
            raise WorkUnitContractError(
                "Scene Beats timing allocation does not match the frozen graph and brief"
            )
        if (
            stage_plan.dialogue_timing_profile is None
            or stage_plan.dialogue_capacity_plan is None
        ):
            raise WorkUnitContractError(
                "Scene Beats compilation requires frozen dialogue capacity inputs"
            )
        try:
            expected_capacity = plan_dialogue_capacity(
                scene_timing_allocation=expected_timing,
                dialogue_timing_profile=stage_plan.dialogue_timing_profile,
                authoring_language=stage_plan.dialogue_capacity_plan.authoring_language,
            )
        except DialogueCapacityPlanningError as exc:
            raise WorkUnitContractError(str(exc)) from exc
        if stage_plan.dialogue_capacity_plan != expected_capacity:
            raise WorkUnitContractError(
                "Scene Beats dialogue capacity does not match the frozen timing inputs"
            )
    snapshot_json = canonical_json(_json_value(canonical_snapshot))
    # Repository-backed plans use CanonicalSnapshot.snapshot_hash as their
    # immutable identity fingerprint.  The serialized byte count remains a
    # separate guard against passing a different snapshot representation.  Pure
    # callers without the domain object retain the content-hash contract used
    # by create_generation_plan(canonical_snapshot=...).
    snapshot_identity = (
        canonical_snapshot.snapshot_hash
        if isinstance(canonical_snapshot, CanonicalSnapshot)
        else sha256_text(snapshot_json)
    )
    if snapshot_identity != generation_plan.canonical_snapshot_hash:
        raise WorkUnitContractError(
            "canonical_snapshot does not match the generation plan"
        )
    if len(snapshot_json.encode("utf-8")) != generation_plan.canonical_snapshot_bytes:
        raise WorkUnitContractError(
            "canonical_snapshot byte size does not match the generation plan"
        )
    if sha256_text(instructions) != generation_plan.instructions_hash:
        raise WorkUnitContractError("instructions do not match the generation plan")
    if len(instructions.encode("utf-8")) != generation_plan.instructions_bytes:
        raise WorkUnitContractError(
            "instructions byte size does not match the generation plan"
        )

    try:
        scoped_context = work_unit_context(
            work_unit,
            dependencies=dependencies,
            scene_timing_allocation=stage_plan.scene_timing_allocation,
            dialogue_timing_profile=stage_plan.dialogue_timing_profile,
            dialogue_capacity_plan=stage_plan.dialogue_capacity_plan,
        )
    except PlanningError as exc:
        raise WorkUnitContractError(str(exc)) from exc
    if content_hash(scoped_context) != work_unit.unit_dependency_hash:
        raise WorkUnitContractError("work-unit context does not match its frozen hash")

    storyboard_timing_guidance = (
        _storyboard_timing_guidance(scoped_context, brief=brief)
        if work_unit.stage == StageName.STORYBOARD
        else None
    )

    adapter = _validator_for_unit(
        work_unit=work_unit,
        stage_plan=stage_plan,
        brief=brief,
        dependencies=dependencies,
        scoped_context=scoped_context,
        story_graph_topology=story_graph_topology,
        storyboard_timing_guidance=storyboard_timing_guidance,
    )
    schema = adapter.json_schema()
    prompt_id, variables = _prompt_variables(
        work_unit=work_unit,
        canonical_snapshot=_json_value(canonical_snapshot),
        scoped_context=scoped_context,
        stage_constraints=dict(stage_constraints or {}),
        schema=schema,
        story_graph_topology=story_graph_topology,
    )
    if work_unit.stage == StageName.STORY_BIBLE:
        variables["project_input"] = brief.generation_input()

    active_renderer = renderer or PromptRenderer()
    rendered = active_renderer.render(prompt_id, variables)
    join_state_requirements = (
        _continuity_requirements(scoped_context)
        if work_unit.stage == StageName.SCENE_BEATS
        else None
    )
    compiled_edge_entry_requirements = (
        edge_entry_state_requirements(scoped_context)
        if work_unit.stage == StageName.SCENE_BEATS
        else None
    )
    if work_unit.stage == StageName.SCENE_BEATS:
        if (
            stage_plan.join_state_value_contract_version is None
            or stage_plan.join_state_value_contract_hash is None
            or join_state_requirements is None
            or stage_plan.edge_entry_state_contract_version is None
            or stage_plan.edge_entry_state_contract_hash is None
            or compiled_edge_entry_requirements is None
        ):
            raise WorkUnitContractError(
                "current Scene Beats StagePlan has no frozen join state value contract"
            )
        if (
            join_state_requirements["contractVersion"]
            != stage_plan.join_state_value_contract_version
            or join_state_requirements["contractHash"]
            != stage_plan.join_state_value_contract_hash
        ):
            raise WorkUnitContractError(
                "Scene Beats context does not match the StagePlan join state value contract"
            )
        if (
            compiled_edge_entry_requirements["contractVersion"]
            != stage_plan.edge_entry_state_contract_version
            or compiled_edge_entry_requirements["contractHash"]
            != stage_plan.edge_entry_state_contract_hash
        ):
            raise WorkUnitContractError(
                "Scene Beats context does not match the StagePlan typed edge-entry contract"
            )
    contract = WorkUnitPromptContract(
        contract_version=WORK_UNIT_PROMPT_CONTRACT_VERSION,
        correction_policy_version=CORRECTION_POLICY_VERSION,
        correction_directive_registry_version=CORRECTION_DIRECTIVE_REGISTRY_VERSION,
        correction_evidence_projection_version=CORRECTION_EVIDENCE_PROJECTION_VERSION,
        correction_issue_selection_version=CORRECTION_ISSUE_SELECTION_VERSION,
        correction_response_schema_version=CORRECTION_RESPONSE_SCHEMA_VERSION,
        correction_ordinal=None,
        correction_strategy=None,
        stage_plan_hash=stage_plan.stage_plan_hash,
        work_unit_id=work_unit.unit_id,
        stage=work_unit.stage,
        selector_kind=work_unit.selector.kind,
        selector_id=work_unit.selector.stable_id,
        prompt_id=prompt_id,
        prompt_version=rendered.trace.prompt_version,
        prompt_spec_hash=rendered.trace.spec_hash,
        schema_id=adapter.schema_id,
        schema_hash=sha256_text(canonical_json(schema)),
        variables_hash=rendered.trace.input_hash,
        rendered_hash=rendered.trace.rendered_hash,
        work_unit_input_hash=work_unit.input_hash,
        dependency_hash=work_unit.dependency_hash,
        unit_dependency_hash=work_unit.unit_dependency_hash,
        fragment_id_binding_version=FRAGMENT_ID_BINDING_VERSION,
        dialogue_timing_profile_version=(
            adapter.dialogue_timing_profile.version
            if isinstance(adapter, WorkUnitFragmentValidationAdapter)
            and adapter.dialogue_timing_profile is not None
            else None
        ),
        dialogue_timing_profile_hash=(
            dialogue_timing_profile_hash(adapter.dialogue_timing_profile)
            if isinstance(adapter, WorkUnitFragmentValidationAdapter)
            and adapter.dialogue_timing_profile is not None
            else None
        ),
        scene_timing_allocation_version=(
            stage_plan.scene_timing_allocation.allocation_version
            if stage_plan.scene_timing_allocation is not None
            else None
        ),
        scene_timing_allocation_hash=(
            stage_plan.scene_timing_allocation.allocation_hash
            if stage_plan.scene_timing_allocation is not None
            else None
        ),
        node_duration_budget_units=(
            stage_plan.scene_timing_allocation.node_duration_budget(
                work_unit.selector.stable_id
            )
            if stage_plan.scene_timing_allocation is not None
            else None
        ),
        dialogue_capacity_policy_version=(
            stage_plan.dialogue_capacity_plan.policy_version
            if stage_plan.dialogue_capacity_plan is not None
            else None
        ),
        dialogue_capacity_plan_hash=(
            stage_plan.dialogue_capacity_plan.capacity_plan_hash
            if stage_plan.dialogue_capacity_plan is not None
            else None
        ),
        dialogue_capacity_guidance=(
            stage_plan.dialogue_capacity_plan.guidance_for(work_unit.selector.stable_id)
            if stage_plan.dialogue_capacity_plan is not None
            else None
        ),
        join_state_value_contract_version=(
            str(join_state_requirements["contractVersion"])
            if join_state_requirements is not None
            else None
        ),
        join_state_value_contract_hash=(
            str(join_state_requirements["contractHash"])
            if join_state_requirements is not None
            else None
        ),
        edge_entry_state_contract_version=(
            str(compiled_edge_entry_requirements["contractVersion"])
            if compiled_edge_entry_requirements is not None
            else None
        ),
        edge_entry_state_contract_hash=(
            str(compiled_edge_entry_requirements["contractHash"])
            if compiled_edge_entry_requirements is not None
            else None
        ),
        storyboard_timing_guidance=storyboard_timing_guidance,
        audio_event_id_binding_version=(
            AUDIO_EVENT_ID_BINDING_VERSION
            if work_unit.stage == StageName.STORYBOARD
            else None
        ),
        storyboard_primary_coverage_binding_version=(
            STORYBOARD_PRIMARY_COVERAGE_BINDING_VERSION
            if work_unit.stage == StageName.STORYBOARD
            else None
        ),
    )
    return CompiledWorkUnitRequest(
        rendered=rendered,
        validator=adapter,
        contract=contract,
        response_schema=schema,
    )


def _storyboard_timing_guidance(
    scoped_context: Mapping[str, Any],
    *,
    brief: ProjectBrief,
) -> StoryboardTimingGuidance:
    """Freeze all text-free timing identities before schema or provider work."""

    scene = scoped_context.get("dramatic_scene")
    beats = scoped_context.get("beats")
    cues = scoped_context.get("dialogue_cues")
    if (
        not isinstance(scene, Mapping)
        or not isinstance(beats, list)
        or not isinstance(cues, list)
    ):
        raise WorkUnitContractError("Storyboard context has no valid timing scope")
    scene_id = scene.get("id")
    scene_budget = scene.get("durationBudgetUnits")
    if (
        not isinstance(scene_id, str)
        or not scene_id
        or not isinstance(scene_budget, int)
        or isinstance(scene_budget, bool)
        or scene_budget < 1
    ):
        raise WorkUnitContractError(
            "Storyboard context has no valid frozen scene duration budget"
        )
    try:
        return build_storyboard_timing_guidance(
            scene_id=scene_id,
            scene_duration_budget_units=scene_budget,
            min_shots=brief.shots_per_scene_min if brief.shot_count_is_strict else 1,
            # In advisory mode only executable timing limits, not the creative
            # preference, constrain the response schema's shot count.
            configured_max_shots=brief.shots_per_scene_max
            if brief.shot_count_is_strict
            else scene_budget,
            beats=beats,
            cues=cues,
        )
    except StoryboardTimingInfeasibleError as exc:
        raise WorkUnitContractError(
            "sealed Storyboard timing cannot fit the frozen dramatic-scene budget",
            code=exc.code,
        ) from exc
    except (KeyError, ValueError) as exc:
        raise WorkUnitContractError(
            "Storyboard context has invalid frozen timing identities"
        ) from exc


def _assert_unit_membership(
    generation_plan: GenerationPlan,
    stage_plan: StagePlan,
    work_unit: GenerationWorkUnit,
) -> None:
    if generation_plan.plan_hash != stage_plan.generation_plan_hash:
        raise WorkUnitContractError("StagePlan does not belong to the GenerationPlan")
    if work_unit not in stage_plan.work_units:
        raise WorkUnitContractError("work unit does not belong to the StagePlan")
    if work_unit.stage != stage_plan.stage:
        raise WorkUnitContractError("work unit stage does not match the StagePlan")
    if work_unit.dependency_hash != stage_plan.dependency_hash:
        raise WorkUnitContractError(
            "work unit dependency hash does not match the StagePlan"
        )
    try:
        assert_work_unit_input_contract(generation_plan, work_unit)
    except PlanningError as exc:
        raise WorkUnitContractError(str(exc)) from exc


def _prompt_variables(
    *,
    work_unit: GenerationWorkUnit,
    canonical_snapshot: Any,
    scoped_context: Mapping[str, Any],
    stage_constraints: Mapping[str, Any],
    schema: Mapping[str, Any],
    story_graph_topology: StoryGraphTopology | None,
) -> tuple[str, dict[str, Any]]:
    if work_unit.stage == StageName.STORY_BIBLE:
        # The full snapshot remains the identity checked above, but the model
        # needs only the public creative input.  Stage heads, project IDs,
        # hashes, and capture timestamps are execution provenance, not prompt
        # material.
        project_input = canonical_snapshot.get("brief", canonical_snapshot)
        return "story_bible", {
            "project_input": project_input,
            "creative_constraints": stage_constraints,
            "json_schema": schema,
        }
    if work_unit.stage == StageName.STORY_GRAPH:
        variables = {
            "story_bible": scoped_context["story_bible"],
            "graph_constraints": stage_constraints,
            "json_schema": schema,
        }
        if story_graph_topology is not None:
            variables["story_graph_topology"] = story_graph_content_fill_manifest(
                story_graph_topology
            )
            return "story_graph_content_fill", variables
        return "story_graph", variables
    if work_unit.stage == StageName.SCENE_BEATS:
        return "scene_beats_fragment", {
            "story_bible": scoped_context["story_bible"],
            "story_node": scoped_context["story_node"],
            "incident_edges": scoped_context["incident_edges"],
            "join_contracts": scoped_context["join_contracts"],
            "continuity_requirements": _continuity_requirements(scoped_context),
            "edge_entry_state_requirements": edge_entry_state_requirements(
                scoped_context
            ),
            "beat_constraints": stage_constraints,
            "node_timing_allocation": scoped_context["scene_timing_allocation"],
            "dialogue_capacity_guidance": scoped_context["dialogue_capacity_guidance"],
            "json_schema": schema,
        }
    return "storyboard_fragment", {
        "story_bible": scoped_context["story_bible"],
        "story_node": scoped_context["story_node"],
        "dramatic_scene": scoped_context["dramatic_scene"],
        "beats": scoped_context["beats"],
        "dialogue_cues": scoped_context["dialogue_cues"],
        "storyboard_constraints": stage_constraints,
        "json_schema": schema,
    }


def _json_value(value: BaseModel | Mapping[str, Any]) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    return value

    # Native strict JSON-Schema providers require every declared root property.
    # Supporting coverage is semantically optional, but its wire representation
    # is always an array; models return [] when no supporting link is needed.
