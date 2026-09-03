"""Pure prompt and response contracts for bounded generation work units.

This module is intentionally provider-, repository-, and pipeline-free.  It
turns an immutable ``GenerationWorkUnit`` into a rendered request, and turns a
model's *unbound* fragment response into a fragment safely bound by trusted
runtime metadata.  A model never receives nor returns stage-plan hashes,
work-unit IDs, or input hashes.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..domain import (
    Beat,
    CanonicalSnapshot,
    CamelModel,
    CoverageRole,
    DramaticScene,
    ProjectBrief,
    Shot,
    ShotBeatLink,
    StageName,
    StoryBible,
)
from .contracts import RenderedPrompt, ValidationIssue, ValidationReport
from .fragments import SceneBeatsFragment, StageFragment, StoryboardFragment
from .planning import (
    GenerationPlan,
    GenerationWorkUnit,
    PlanningError,
    StagePlan,
    WorkUnitSelectorKind,
    assert_work_unit_input_contract,
    content_hash,
    work_unit_context,
)
from .prompts import PromptRenderer, canonical_json, sha256_text
from .validation import CanonicalStageValidationAdapter, SemanticValidationContext, ValidationAdapter


WORK_UNIT_PROMPT_CONTRACT_VERSION = "m1-p0.1"
SCENE_BEATS_FRAGMENT_SCHEMA_ID = "scene_beats.fragment.v1"
STORYBOARD_FRAGMENT_SCHEMA_ID = "storyboard.fragment.v1"


class WorkUnitContractError(ValueError):
    """A planned unit cannot be rendered or bound at the trusted boundary."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SceneBeatsFragmentOutput(CamelModel):
    """The only scene-beats payload a model may return for one node unit."""

    story_node_id: str = Field(min_length=1)
    scenes: list[DramaticScene] = Field(min_length=1)
    beats: list[Beat] = Field(min_length=1)


class StoryboardFragmentOutput(CamelModel):
    """The only storyboard payload a model may return for one scene unit."""

    scene_id: str = Field(min_length=1)
    shots: list[Shot] = Field(min_length=1)
    shot_beat_links: list[ShotBeatLink] = Field(min_length=1)


FragmentOutput: TypeAlias = SceneBeatsFragmentOutput | StoryboardFragmentOutput


class WorkUnitPromptContract(_FrozenModel):
    """Hash-only provenance for a compiled unit request.

    The fields identify the exact public prompt/schema contract without
    duplicating user text or server-managed canonical objects into traces.
    """

    contract_version: str = WORK_UNIT_PROMPT_CONTRACT_VERSION
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
    unit_dependency_hash: str = Field(min_length=1)


@dataclass(frozen=True)
class CompiledWorkUnitRequest:
    """Pure hand-off object consumed later by Pipeline/Provider adapters."""

    rendered: RenderedPrompt
    validator: ValidationAdapter[Any]
    contract: WorkUnitPromptContract
    response_schema: dict[str, Any]


class WorkUnitFragmentValidationAdapter(ValidationAdapter[StageFragment]):
    """Presence-strict schema and selector-scoped semantic validation.

    The adapter validates the model-facing fragment first, then the trusted
    binder attaches the immutable StagePlan and work-unit IDs.  The binder is
    deliberately not part of the generated schema.
    """

    def __init__(
        self,
        *,
        stage_plan: StagePlan,
        work_unit: GenerationWorkUnit,
        brief: ProjectBrief,
        bible: StoryBible,
        scoped_context: Mapping[str, Any],
    ) -> None:
        if work_unit.stage not in {StageName.SCENE_BEATS, StageName.STORYBOARD}:
            raise WorkUnitContractError("fragment adapter only supports sharded stages")
        self.stage_plan = stage_plan
        self.work_unit = work_unit
        self.brief = brief
        self.bible = bible
        self.scoped_context = dict(scoped_context)
        self.model_type: type[FragmentOutput]
        if work_unit.stage == StageName.SCENE_BEATS:
            self.model_type = SceneBeatsFragmentOutput
            self.schema_id = SCENE_BEATS_FRAGMENT_SCHEMA_ID
        else:
            self.model_type = StoryboardFragmentOutput
            self.schema_id = STORYBOARD_FRAGMENT_SCHEMA_ID

    def json_schema(self) -> dict[str, Any]:
        schema = deepcopy(self.model_type.model_json_schema(by_alias=True))
        _require_all_declared_fields(schema)
        return schema

    def validate(
        self,
        value: Any,
        *,
        context: SemanticValidationContext,
    ) -> ValidationReport:
        if context.stage != self.work_unit.stage.value:
            raise ValueError(
                f"Validation context stage {context.stage!r} does not match "
                f"work-unit stage {self.work_unit.stage.value!r}"
            )
        issues = _presence_issues(value, self.json_schema())
        if issues:
            return ValidationReport(accepted=False, issues=issues)
        try:
            parsed = self.model_type.model_validate(value, by_alias=True, by_name=False)
        except ValidationError as exc:
            return ValidationReport(
                accepted=False,
                issues=tuple(
                    ValidationIssue(
                        code=f"schema.{error['type']}",
                        message=error["msg"],
                        path=tuple(error.get("loc") or ()),
                    )
                    for error in exc.errors(include_url=False, include_context=False)
                ),
            )
        semantic_issues = _fragment_semantic_issues(
            parsed,
            work_unit=self.work_unit,
            brief=self.brief,
            bible=self.bible,
            scoped_context=self.scoped_context,
        )
        if semantic_issues:
            return ValidationReport(accepted=False, issues=semantic_issues)
        return ValidationReport(
            accepted=True,
            value=_bind_fragment(parsed, stage_plan=self.stage_plan, work_unit=self.work_unit),
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
        raise WorkUnitContractError("canonical_snapshot does not match the generation plan")
    if len(snapshot_json.encode("utf-8")) != generation_plan.canonical_snapshot_bytes:
        raise WorkUnitContractError("canonical_snapshot byte size does not match the generation plan")
    if sha256_text(instructions) != generation_plan.instructions_hash:
        raise WorkUnitContractError("instructions do not match the generation plan")
    if len(instructions.encode("utf-8")) != generation_plan.instructions_bytes:
        raise WorkUnitContractError("instructions byte size does not match the generation plan")

    try:
        scoped_context = work_unit_context(work_unit, dependencies=dependencies)
    except PlanningError as exc:
        raise WorkUnitContractError(str(exc)) from exc
    if content_hash(scoped_context) != work_unit.unit_dependency_hash:
        raise WorkUnitContractError("work-unit context does not match its frozen hash")

    adapter = _validator_for_unit(
        work_unit=work_unit,
        stage_plan=stage_plan,
        brief=brief,
        dependencies=dependencies,
        scoped_context=scoped_context,
    )
    schema = adapter.json_schema()
    prompt_id, variables = _prompt_variables(
        work_unit=work_unit,
        canonical_snapshot=_json_value(canonical_snapshot),
        scoped_context=scoped_context,
        stage_constraints=dict(stage_constraints or {}),
        schema=schema,
    )
    active_renderer = renderer or PromptRenderer()
    rendered = active_renderer.render(prompt_id, variables)
    contract = WorkUnitPromptContract(
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
    )
    return CompiledWorkUnitRequest(
        rendered=rendered,
        validator=adapter,
        contract=contract,
        response_schema=schema,
    )


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
        raise WorkUnitContractError("work unit dependency hash does not match the StagePlan")
    try:
        assert_work_unit_input_contract(generation_plan, work_unit)
    except PlanningError as exc:
        raise WorkUnitContractError(str(exc)) from exc


def _validator_for_unit(
    *,
    work_unit: GenerationWorkUnit,
    stage_plan: StagePlan,
    brief: ProjectBrief,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
    scoped_context: Mapping[str, Any],
) -> ValidationAdapter[Any]:
    if work_unit.stage == StageName.STORY_BIBLE:
        return CanonicalStageValidationAdapter(StageName.STORY_BIBLE, brief=brief)
    bible = dependencies.get(StageName.STORY_BIBLE)
    if not isinstance(bible, StoryBible):
        raise WorkUnitContractError(f"{work_unit.stage.value} requires a sealed StoryBible")
    if work_unit.stage == StageName.STORY_GRAPH:
        return CanonicalStageValidationAdapter(StageName.STORY_GRAPH, brief=brief, bible=bible)
    return WorkUnitFragmentValidationAdapter(
        stage_plan=stage_plan,
        work_unit=work_unit,
        brief=brief,
        bible=bible,
        scoped_context=scoped_context,
    )


def _prompt_variables(
    *,
    work_unit: GenerationWorkUnit,
    canonical_snapshot: Any,
    scoped_context: Mapping[str, Any],
    stage_constraints: Mapping[str, Any],
    schema: Mapping[str, Any],
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
        return "story_graph", {
            "story_bible": scoped_context["story_bible"],
            "graph_constraints": stage_constraints,
            "json_schema": schema,
        }
    if work_unit.stage == StageName.SCENE_BEATS:
        return "scene_beats_fragment", {
            "story_bible": scoped_context["story_bible"],
            "story_node": scoped_context["story_node"],
            "incident_edges": scoped_context["incident_edges"],
            "join_contracts": scoped_context["join_contracts"],
            "beat_constraints": stage_constraints,
            "json_schema": schema,
        }
    return "storyboard_fragment", {
        "story_bible": scoped_context["story_bible"],
        "story_node": scoped_context["story_node"],
        "dramatic_scene": scoped_context["dramatic_scene"],
        "beats": scoped_context["beats"],
        "storyboard_constraints": stage_constraints,
        "json_schema": schema,
    }


def _bind_fragment(
    output: FragmentOutput,
    *,
    stage_plan: StagePlan,
    work_unit: GenerationWorkUnit,
) -> StageFragment:
    if isinstance(output, SceneBeatsFragmentOutput):
        return SceneBeatsFragment(
            stage_plan_hash=stage_plan.stage_plan_hash,
            work_unit_id=work_unit.unit_id,
            story_node_id=output.story_node_id,
            scenes=output.scenes,
            beats=output.beats,
        )
    return StoryboardFragment(
        stage_plan_hash=stage_plan.stage_plan_hash,
        work_unit_id=work_unit.unit_id,
        scene_id=output.scene_id,
        shots=output.shots,
        shot_beat_links=output.shot_beat_links,
    )


def _fragment_semantic_issues(
    output: FragmentOutput,
    *,
    work_unit: GenerationWorkUnit,
    brief: ProjectBrief,
    bible: StoryBible,
    scoped_context: Mapping[str, Any],
) -> tuple[ValidationIssue, ...]:
    if isinstance(output, SceneBeatsFragmentOutput):
        return _scene_beats_semantic_issues(output, work_unit=work_unit, bible=bible, scoped_context=scoped_context)
    return _storyboard_semantic_issues(output, work_unit=work_unit, brief=brief, bible=bible, scoped_context=scoped_context)


def _scene_beats_semantic_issues(
    output: SceneBeatsFragmentOutput,
    *,
    work_unit: GenerationWorkUnit,
    bible: StoryBible,
    scoped_context: Mapping[str, Any],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    target = work_unit.selector.stable_id
    if output.story_node_id != target:
        issues.append(_issue("selector.story_node", "storyNodeId", "fragment must target its selected story node"))
    target_node = scoped_context.get("story_node", {})
    if target_node.get("id") != target:
        issues.append(_issue("context.selector", "storyNodeId", "trusted context does not match unit selector"))
    scene_ids = [scene.id for scene in output.scenes]
    if len(scene_ids) != len(set(scene_ids)):
        issues.append(_issue("semantic.duplicate_scene_id", "scenes", "fragment contains duplicate scene IDs"))
    beat_ids = [beat.id for beat in output.beats]
    if len(beat_ids) != len(set(beat_ids)):
        issues.append(_issue("semantic.duplicate_beat_id", "beats", "fragment contains duplicate beat IDs"))
    known_characters = {item.id for item in bible.characters}
    known_locations = {item.id for item in bible.locations}
    beats_by_scene: dict[str, list[Beat]] = {}
    for beat in output.beats:
        beats_by_scene.setdefault(beat.scene_id, []).append(beat)
        if beat.scene_id not in scene_ids:
            issues.append(_issue("semantic.cross_unit_beat", "beats", "beat belongs to a scene outside this fragment"))
    for index, scene in enumerate(output.scenes):
        if scene.story_node_id != target:
            issues.append(_issue("semantic.cross_unit_scene", ("scenes", index, "storyNodeId"), "scene belongs to another story node"))
        if scene.location_id is not None and scene.location_id not in known_locations:
            issues.append(_issue("semantic.unknown_location", ("scenes", index, "locationId"), "scene references an unknown location"))
        unknown_characters = set(scene.character_ids) - known_characters
        if unknown_characters:
            issues.append(_issue("semantic.unknown_characters", ("scenes", index, "characterIds"), "scene references unknown characters"))
        ordered = sorted(beats_by_scene.get(scene.id, []), key=lambda beat: beat.order)
        if scene.beat_ids != [beat.id for beat in ordered]:
            issues.append(_issue("semantic.scene_beat_order", ("scenes", index, "beatIds"), "scene beatIds must exactly match fragment beats in order"))
        if [beat.order for beat in ordered] != list(range(1, len(ordered) + 1)):
            issues.append(_issue("semantic.beat_order", ("scenes", index, "beatIds"), "beat order must be contiguous from 1"))
    for contract in scoped_context.get("join_contracts", []):
        required_keys = set(contract.get("requiredStateKeys", []))
        if target == contract.get("joinNodeId"):
            if any(not required_keys <= set(scene.entry_state.facts) for scene in output.scenes):
                issues.append(_issue("semantic.join_entry_state", "scenes", "join fragment is missing required entry-state facts"))
        if target in set(contract.get("incomingNodeIds", [])):
            if any(not required_keys <= set(scene.exit_state.facts) for scene in output.scenes):
                issues.append(_issue("semantic.join_exit_state", "scenes", "incoming fragment is missing required exit-state facts"))
    return tuple(issues)


def _storyboard_semantic_issues(
    output: StoryboardFragmentOutput,
    *,
    work_unit: GenerationWorkUnit,
    brief: ProjectBrief,
    bible: StoryBible,
    scoped_context: Mapping[str, Any],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    target = work_unit.selector.stable_id
    if output.scene_id != target:
        issues.append(_issue("selector.scene", "sceneId", "fragment must target its selected dramatic scene"))
    scene = scoped_context.get("dramatic_scene", {})
    if scene.get("id") != target:
        issues.append(_issue("context.selector", "sceneId", "trusted context does not match unit selector"))
    beat_ids = {beat["id"] for beat in scoped_context.get("beats", [])}
    shot_ids = [shot.id for shot in output.shots]
    if len(shot_ids) != len(set(shot_ids)):
        issues.append(_issue("semantic.duplicate_shot_id", "shots", "fragment contains duplicate shot IDs"))
    known_characters = {item.id for item in bible.characters}
    known_locations = {item.id for item in bible.locations}
    known_props = {item.id for item in bible.props}
    for index, shot in enumerate(output.shots):
        if shot.scene_id != target:
            issues.append(_issue("semantic.cross_unit_shot", ("shots", index, "sceneId"), "shot belongs to another dramatic scene"))
        if shot.location_id is not None and shot.location_id not in known_locations:
            issues.append(_issue("semantic.unknown_location", ("shots", index, "locationId"), "shot references an unknown location"))
        if set(shot.character_ids) - known_characters:
            issues.append(_issue("semantic.unknown_characters", ("shots", index, "characterIds"), "shot references unknown characters"))
        if set(shot.prop_ids) - known_props:
            issues.append(_issue("semantic.unknown_props", ("shots", index, "propIds"), "shot references unknown props"))
    ordered = sorted(output.shots, key=lambda shot: shot.order)
    if [shot.order for shot in ordered] != list(range(1, len(ordered) + 1)):
        issues.append(_issue("semantic.shot_order", "shots", "shot order must be contiguous from 1"))
    if not brief.shots_per_scene_min <= len(output.shots) <= brief.shots_per_scene_max:
        issues.append(_issue("semantic.shot_count", "shots", "shot count falls outside the project scene budget"))
    linked_shots: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    primary_counts: dict[str, int] = {}
    for index, link in enumerate(output.shot_beat_links):
        pair = (link.shot_id, link.beat_id)
        if pair in pairs:
            issues.append(_issue("semantic.duplicate_link", ("shotBeatLinks", index), "duplicate shot-to-beat link"))
        pairs.add(pair)
        if link.shot_id not in shot_ids:
            issues.append(_issue("semantic.unknown_link_shot", ("shotBeatLinks", index), "link references a shot outside this fragment"))
        else:
            linked_shots.add(link.shot_id)
        if link.beat_id not in beat_ids:
            issues.append(_issue("semantic.cross_unit_beat", ("shotBeatLinks", index, "beatId"), "link references a beat outside this fragment"))
        if link.role == CoverageRole.PRIMARY:
            primary_counts[link.beat_id] = primary_counts.get(link.beat_id, 0) + 1
    if set(shot_ids) - linked_shots:
        issues.append(_issue("semantic.unlinked_shots", "shotBeatLinks", "each shot must cover a selected beat"))
    for beat_id in sorted(beat_ids):
        if primary_counts.get(beat_id, 0) != 1:
            issues.append(_issue("semantic.primary_coverage", "shotBeatLinks", "each selected beat needs exactly one PRIMARY link"))
    return tuple(issues)


def _issue(code: str, path: str | tuple[str | int, ...], message: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=(path,) if isinstance(path, str) else path, message=message)


def _json_value(value: BaseModel | Mapping[str, Any]) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    return value


def _require_all_declared_fields(schema_node: Any) -> None:
    if isinstance(schema_node, dict):
        properties = schema_node.get("properties")
        if isinstance(properties, dict):
            schema_node["required"] = list(properties)
        for nested in schema_node.values():
            _require_all_declared_fields(nested)
    elif isinstance(schema_node, list):
        for nested in schema_node:
            _require_all_declared_fields(nested)


def _resolve_schema(schema_node: Any, root: Mapping[str, Any]) -> Any:
    if not isinstance(schema_node, Mapping):
        return schema_node
    reference = schema_node.get("$ref")
    if not isinstance(reference, str) or not reference.startswith("#/"):
        return schema_node
    resolved: Any = root
    for segment in reference[2:].split("/"):
        if not isinstance(resolved, Mapping):
            return schema_node
        resolved = resolved.get(segment.replace("~1", "/").replace("~0", "~"))
    return resolved


def _schema_matches_value(schema_node: Any, value: Any, root: Mapping[str, Any]) -> bool:
    resolved = _resolve_schema(schema_node, root)
    if not isinstance(resolved, Mapping):
        return True
    kind = resolved.get("type")
    return {
        "null": value is None,
        "object": isinstance(value, Mapping),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
    }.get(str(kind), True)


def _presence_issues(value: Any, schema: Mapping[str, Any]) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    def visit(current: Any, schema_node: Any, path: tuple[str | int, ...]) -> None:
        resolved = _resolve_schema(schema_node, schema)
        if not isinstance(resolved, Mapping):
            return
        variants = resolved.get("anyOf") or resolved.get("oneOf")
        if isinstance(variants, list):
            selected = next((item for item in variants if _schema_matches_value(item, current, schema)), None)
            if selected is not None:
                visit(current, selected, path)
            return
        properties = resolved.get("properties")
        if isinstance(properties, Mapping) and isinstance(current, Mapping):
            for name, child in properties.items():
                if name not in current:
                    issues.append(ValidationIssue(code="schema.missing", message="Field required for generated fragment output", path=(*path, str(name))))
                else:
                    visit(current[name], child, (*path, str(name)))
            return
        items = resolved.get("items")
        if items is not None and isinstance(current, list):
            for index, item in enumerate(current):
                visit(item, items, (*path, index))

    visit(value, schema, ())
    return tuple(issues)
