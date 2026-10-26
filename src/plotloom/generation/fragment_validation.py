"""Presence-strict fragment acceptance and current work-unit adapter selection."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, TypeAlias

from pydantic import (
    BaseModel,
    ValidationError,
)

from ..domain import (
    DialogueTimingProfile,
    ProjectBrief,
    StageName,
    StoryBibleV2,
)
from .contracts import ValidationIssue, ValidationReport
from .dialogue_capacity import (
    DialogueCapacityNodeGuidance,
)
from .fragment_binding import _bind_fragment
from .fragment_schema import (
    _bind_fragment_foreign_keys,
)
from .fragments import StageFragment
from .json_schema import (
    _presence_issues,
    explicit_presence_json_schema,
    inline_local_json_references,
)
from plotloom.generation.planning_contracts import GenerationWorkUnit, StagePlan
from .scene_beats_semantics import (
    _scene_beats_semantic_issues,
)
from .scene_response_contracts import (
    SceneBeatsFragmentOutput,
)
from plotloom.generation.story_graph_topology_contracts import StoryGraphTopology
from .story_graph_validation import StoryGraphContentFillValidationAdapter
from .storyboard_response_contracts import (
    StoryboardFragmentOutput,
)
from .storyboard_semantics import (
    _storyboard_semantic_issues,
)
from .storyboard_timing_repair import (
    StoryboardTimingGuidance,
)
from .validation import (
    CanonicalStageValidationAdapter,
    SemanticValidationContext,
    ValidationAdapter,
)
from .work_unit_contracts import (
    SCENE_BEATS_FRAGMENT_SCHEMA_ID,
    STORYBOARD_FRAGMENT_SCHEMA_ID,
    WorkUnitContractError,
)


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
        bible: StoryBibleV2,
        scoped_context: Mapping[str, Any],
        dialogue_timing_profile: DialogueTimingProfile | None,
        dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None,
        storyboard_timing_guidance: StoryboardTimingGuidance | None,
    ) -> None:
        if work_unit.stage not in {StageName.SCENE_BEATS, StageName.STORYBOARD}:
            raise WorkUnitContractError("fragment adapter only supports sharded stages")
        self.stage_plan = stage_plan
        self.work_unit = work_unit
        self.brief = brief
        self.bible = bible
        self.scoped_context = dict(scoped_context)
        self.dialogue_timing_profile = dialogue_timing_profile
        self.dialogue_capacity_guidance = dialogue_capacity_guidance
        self.storyboard_timing_guidance = storyboard_timing_guidance
        self.model_type: type[FragmentOutput]
        if work_unit.stage == StageName.SCENE_BEATS:
            if dialogue_timing_profile is None:
                raise WorkUnitContractError(
                    "Scene Beats fragment adapter requires a dialogue timing profile"
                )
            if stage_plan.scene_timing_allocation is None:
                raise WorkUnitContractError(
                    "Scene Beats fragment adapter requires a frozen scene timing allocation"
                )
            if dialogue_capacity_guidance is None:
                raise WorkUnitContractError(
                    "Scene Beats fragment adapter requires frozen dialogue capacity guidance"
                )
            self.model_type = SceneBeatsFragmentOutput
            self.schema_id = SCENE_BEATS_FRAGMENT_SCHEMA_ID
        else:
            if dialogue_capacity_guidance is not None:
                raise WorkUnitContractError(
                    "dialogue capacity guidance only belongs to Scene Beats"
                )
            if storyboard_timing_guidance is None:
                raise WorkUnitContractError(
                    "Storyboard fragment adapter requires frozen timing guidance"
                )
            self.model_type = StoryboardFragmentOutput
            self.schema_id = STORYBOARD_FRAGMENT_SCHEMA_ID

    def json_schema(self) -> dict[str, Any]:
        schema = explicit_presence_json_schema(
            self.model_type.model_json_schema(by_alias=True)
        )
        _bind_fragment_foreign_keys(
            schema,
            work_unit=self.work_unit,
            brief=self.brief,
            bible=self.bible,
            scoped_context=self.scoped_context,
            dialogue_capacity_guidance=self.dialogue_capacity_guidance,
            storyboard_timing_guidance=self.storyboard_timing_guidance,
        )
        return inline_local_json_references(schema)

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
            parsed = self.model_type.model_validate(
                _canonicalize_model_local_ids(value, stage=self.work_unit.stage),
                by_alias=True,
                by_name=False,
            )
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
            dialogue_timing_profile=self.dialogue_timing_profile,
            dialogue_capacity_guidance=self.dialogue_capacity_guidance,
        )
        if semantic_issues:
            return ValidationReport(accepted=False, issues=semantic_issues)
        # Model-controlled fields are made canonical-compatible by the closed
        # response models and semantic checks above.  Any exception in this
        # trusted binder is therefore a program/plan fault and must cross the
        # runner's fail-closed validation boundary rather than authorize a
        # model correction.
        fragment = _bind_fragment(
            parsed,
            stage_plan=self.stage_plan,
            work_unit=self.work_unit,
            dialogue_timing_profile=self.dialogue_timing_profile,
            scene_timing_allocation=self.stage_plan.scene_timing_allocation,
        )
        return ValidationReport(accepted=True, value=fragment)


def _fragment_semantic_issues(
    output: FragmentOutput,
    *,
    work_unit: GenerationWorkUnit,
    brief: ProjectBrief,
    bible: StoryBibleV2,
    scoped_context: Mapping[str, Any],
    dialogue_timing_profile: DialogueTimingProfile | None,
    dialogue_capacity_guidance: DialogueCapacityNodeGuidance | None,
) -> tuple[ValidationIssue, ...]:
    if isinstance(output, SceneBeatsFragmentOutput):
        if dialogue_timing_profile is None:
            raise WorkUnitContractError(
                "Scene Beats validation requires a frozen dialogue timing profile"
            )
        if dialogue_capacity_guidance is None:
            raise WorkUnitContractError(
                "Scene Beats validation requires frozen dialogue capacity guidance"
            )
        return _scene_beats_semantic_issues(
            output,
            work_unit=work_unit,
            bible=bible,
            scoped_context=scoped_context,
            dialogue_timing_profile=dialogue_timing_profile,
            dialogue_capacity_guidance=dialogue_capacity_guidance,
        )
    return _storyboard_semantic_issues(
        output,
        work_unit=work_unit,
        brief=brief,
        bible=bible,
        scoped_context=scoped_context,
    )


def _canonicalize_model_local_ids(value: Any, *, stage: StageName) -> Any:
    """Keep model-facing local IDs intact for the specialized content models."""

    del stage
    return deepcopy(value)


FragmentOutput: TypeAlias = SceneBeatsFragmentOutput | StoryboardFragmentOutput


def _validator_for_unit(
    *,
    work_unit: GenerationWorkUnit,
    stage_plan: StagePlan,
    brief: ProjectBrief,
    dependencies: Mapping[StageName, BaseModel | Mapping[str, Any]],
    scoped_context: Mapping[str, Any],
    story_graph_topology: StoryGraphTopology | None,
    storyboard_timing_guidance: StoryboardTimingGuidance | None,
) -> ValidationAdapter[Any]:
    if work_unit.stage == StageName.STORY_BIBLE:
        return CanonicalStageValidationAdapter(StageName.STORY_BIBLE, brief=brief)
    bible = dependencies.get(StageName.STORY_BIBLE)
    if not isinstance(bible, StoryBibleV2):
        raise WorkUnitContractError(
            f"{work_unit.stage.value} requires a sealed StoryBible"
        )
    if work_unit.stage == StageName.STORY_GRAPH:
        if story_graph_topology is not None:
            return StoryGraphContentFillValidationAdapter(
                topology=story_graph_topology, brief=brief, bible=bible
            )
        return CanonicalStageValidationAdapter(
            StageName.STORY_GRAPH, brief=brief, bible=bible
        )
    return WorkUnitFragmentValidationAdapter(
        stage_plan=stage_plan,
        work_unit=work_unit,
        brief=brief,
        bible=bible,
        scoped_context=scoped_context,
        dialogue_timing_profile=(
            stage_plan.dialogue_timing_profile
            if work_unit.stage == StageName.SCENE_BEATS
            else None
        ),
        dialogue_capacity_guidance=(
            stage_plan.dialogue_capacity_plan.guidance_for(work_unit.selector.stable_id)
            if work_unit.stage == StageName.SCENE_BEATS
            and stage_plan.dialogue_capacity_plan is not None
            else None
        ),
        storyboard_timing_guidance=storyboard_timing_guidance,
    )
