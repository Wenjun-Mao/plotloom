"""Strict deterministic aggregation of typed generation work-unit fragments."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import TypeVar

from pydantic import BaseModel

from ..domain import (
    DialogueTimingProfile,
    ProjectBrief,
    StageName,
    SceneBeatPlanV2,
    StoryBibleV2,
    StoryGraphV2,
    StoryboardV2,
)
from ..canonical_schema import V2CoverageRole
from ..validation import DomainValidationError, validate_stage_payload
from .fragments import (
    SceneBeatsFragment,
    StageFragment,
    StoryBibleFragment,
    StoryboardFragment,
    StoryGraphFragment,
)
from .planning import StagePlan, WorkUnitSelectorKind


class AggregateValidationError(ValueError):
    """A candidate set is not the exact, sealed result described by a StagePlan."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "aggregate.contract_invalid",
        stage: StageName | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage


def aggregate_stage_fragments(
    stage_plan: StagePlan,
    fragments: Iterable[StageFragment],
    *,
    brief: ProjectBrief,
    bible: StoryBibleV2 | None = None,
    graph: StoryGraphV2 | None = None,
    scene_beats: SceneBeatPlanV2 | None = None,
    dialogue_timing_profile: DialogueTimingProfile | None = None,
) -> StoryBibleV2 | StoryGraphV2 | SceneBeatPlanV2 | StoryboardV2:
    """Merge exactly the StagePlan's candidates and run the canonical validator.

    Iteration order is evidence: a caller that provides valid unit IDs in a
    different order has not supplied the sealed manifest prescribed by the
    StagePlan.  This rejects an otherwise easy source of nondeterministic JSON
    output and repair lineage.
    """

    try:
        ordered = tuple(fragments)
        _assert_exact_manifest(stage_plan, ordered)
        payload = _merge(stage_plan, ordered, scene_beats=scene_beats)
        _assert_aggregate_size(stage_plan, payload)
        _validate_aggregate_semantics(stage_plan.stage, payload, bible=bible, graph=graph, scene_beats=scene_beats)
        _validate_canonical_parity(
            stage_plan,
            payload,
            brief=brief,
            bible=bible,
            graph=graph,
            scene_beats=scene_beats,
            dialogue_timing_profile=dialogue_timing_profile,
        )
        return payload
    except AggregateValidationError as error:
        if error.stage is not None:
            raise
        raise AggregateValidationError(
            str(error),
            code=error.code,
            stage=stage_plan.stage,
        ) from error


def _assert_exact_manifest(stage_plan: StagePlan, fragments: tuple[StageFragment, ...]) -> None:
    expected = tuple(unit.unit_id for unit in stage_plan.work_units)
    actual = tuple(fragment.work_unit_id for fragment in fragments)
    if len(actual) != len(set(actual)):
        raise AggregateValidationError("aggregate contains duplicate work-unit fragments")
    unexpected = sorted(set(actual) - set(expected))
    missing = sorted(set(expected) - set(actual))
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing units: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected units: {', '.join(unexpected)}")
        raise AggregateValidationError("aggregate manifest does not match StagePlan; " + "; ".join(details))
    if actual != expected:
        raise AggregateValidationError("aggregate fragments must be supplied in StagePlan sequence order")
    wrong_plan = [
        fragment.work_unit_id
        for fragment in fragments
        if fragment.stage_plan_hash != stage_plan.stage_plan_hash
    ]
    if wrong_plan:
        raise AggregateValidationError(
            "aggregate fragments belong to a different StagePlan: " + ", ".join(wrong_plan)
        )


def _merge(
    stage_plan: StagePlan,
    fragments: tuple[StageFragment, ...],
    *,
    scene_beats: SceneBeatPlanV2 | None,
) -> StoryBibleV2 | StoryGraphV2 | SceneBeatPlanV2 | StoryboardV2:
    stage = stage_plan.stage
    if stage == StageName.STORY_BIBLE:
        fragment = _one_fragment(fragments, StoryBibleFragment, stage)
        _assert_whole_stage_selector(stage_plan, fragment.work_unit_id)
        return fragment.payload
    if stage == StageName.STORY_GRAPH:
        fragment = _one_fragment(fragments, StoryGraphFragment, stage)
        _assert_whole_stage_selector(stage_plan, fragment.work_unit_id)
        return fragment.payload
    if stage == StageName.SCENE_BEATS:
        return _merge_scene_beats(stage_plan, fragments)
    if scene_beats is None:
        raise AggregateValidationError("storyboard aggregation requires the sealed SceneBeatPlan")
    return _merge_storyboard(stage_plan, fragments, scene_beats)


FragmentT = TypeVar("FragmentT", bound=StageFragment)


def _one_fragment(
    fragments: tuple[StageFragment, ...],
    expected_type: type[FragmentT],
    stage: StageName,
) -> FragmentT:
    if len(fragments) != 1 or not isinstance(fragments[0], expected_type):
        raise AggregateValidationError(f"{stage.value} requires one {expected_type.__name__}")
    return fragments[0]


def _assert_whole_stage_selector(stage_plan: StagePlan, work_unit_id: str) -> None:
    unit = stage_plan.work_units[0]
    if (
        unit.unit_id != work_unit_id
        or unit.selector.kind != WorkUnitSelectorKind.WHOLE_STAGE
        or unit.selector.stable_id != stage_plan.stage.value
    ):
        raise AggregateValidationError("whole-stage fragment does not match its stable selector")


def _merge_scene_beats(
    stage_plan: StagePlan,
    fragments: tuple[StageFragment, ...],
) -> SceneBeatPlanV2:
    all_scenes = []
    all_beats = []
    all_cues = []
    seen_scene_ids: set[str] = set()
    seen_beat_ids: set[str] = set()
    seen_cue_ids: set[str] = set()
    for unit, fragment in zip(stage_plan.work_units, fragments, strict=True):
        if not isinstance(fragment, SceneBeatsFragment):
            raise AggregateValidationError("scene_beats aggregate requires only SceneBeatsFragment values")
        if (
            unit.selector.kind != WorkUnitSelectorKind.STORY_NODE
            or unit.selector.stable_id != fragment.story_node_id
        ):
            raise AggregateValidationError(
                f"scene-beats fragment {unit.unit_id} does not match its story-node selector"
            )
        fragment_scene_ids = {scene.id for scene in fragment.scenes}
        fragment_beat_ids = {beat.id for beat in fragment.beats}
        fragment_cue_ids = {cue.id for cue in fragment.dialogue_cues}
        duplicate_scenes = seen_scene_ids & fragment_scene_ids
        duplicate_beats = seen_beat_ids & fragment_beat_ids
        duplicate_cues = seen_cue_ids & fragment_cue_ids
        if duplicate_scenes or duplicate_beats or duplicate_cues:
            details = []
            if duplicate_scenes:
                details.append("scene IDs " + ", ".join(sorted(duplicate_scenes)))
            if duplicate_beats:
                details.append("beat IDs " + ", ".join(sorted(duplicate_beats)))
            if duplicate_cues:
                details.append("cue IDs " + ", ".join(sorted(duplicate_cues)))
            raise AggregateValidationError(
                "cross-unit identifier collision: " + "; ".join(details),
                code="aggregate.identifier_collision",
            )
        seen_scene_ids.update(fragment_scene_ids)
        seen_beat_ids.update(fragment_beat_ids)
        seen_cue_ids.update(fragment_cue_ids)
        all_scenes.extend(fragment.scenes)
        all_beats.extend(fragment.beats)
        all_cues.extend(fragment.dialogue_cues)
    return SceneBeatPlanV2(scenes=all_scenes, beats=all_beats, dialogue_cues=all_cues)


def _merge_storyboard(
    stage_plan: StagePlan,
    fragments: tuple[StageFragment, ...],
    scene_beats: SceneBeatPlanV2,
) -> StoryboardV2:
    scenes_by_id = {scene.id: scene for scene in scene_beats.scenes}
    beats_by_id = {beat.id: beat for beat in scene_beats.beats}
    all_shots = []
    all_links = []
    seen_shot_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()

    for unit, fragment in zip(stage_plan.work_units, fragments, strict=True):
        if not isinstance(fragment, StoryboardFragment):
            raise AggregateValidationError("storyboard aggregate requires only StoryboardFragment values")
        if (
            unit.selector.kind != WorkUnitSelectorKind.DRAMATIC_SCENE
            or unit.selector.stable_id != fragment.scene_id
        ):
            raise AggregateValidationError(
                f"storyboard fragment {unit.unit_id} does not match its dramatic-scene selector"
            )
        if fragment.scene_id not in scenes_by_id:
            raise AggregateValidationError(
                f"storyboard fragment targets unknown dramatic scene {fragment.scene_id}"
            )
        shot_ids = {shot.id for shot in fragment.shots}
        collisions = seen_shot_ids & shot_ids
        if collisions:
            raise AggregateValidationError(
                "cross-unit shot ID collision: " + ", ".join(sorted(collisions)),
                code="aggregate.identifier_collision",
            )
        for link in fragment.shot_beat_links:
            beat = beats_by_id.get(link.beat_id)
            if beat is None:
                raise AggregateValidationError(
                    f"storyboard fragment references unknown beat {link.beat_id}"
                )
            if beat.scene_id != fragment.scene_id:
                raise AggregateValidationError(
                    "storyboard fragments may not reference beats from another dramatic-scene unit"
                )
            pair = (link.shot_id, link.beat_id)
            if pair in seen_pairs:
                raise AggregateValidationError(
                    f"cross-unit duplicate shot-to-beat link {link.shot_id}/{link.beat_id}"
                )
            seen_pairs.add(pair)
        seen_shot_ids.update(shot_ids)
        all_shots.extend(fragment.shots)
        all_links.extend(fragment.shot_beat_links)

    storyboard = StoryboardV2(shots=all_shots, shot_beat_links=all_links)
    _assert_exactly_one_primary_per_beat(storyboard, scene_beats)
    return storyboard


def _assert_exactly_one_primary_per_beat(
    storyboard: StoryboardV2,
    scene_beats: SceneBeatPlanV2,
) -> None:
    counts = Counter(
        link.beat_id
        for link in storyboard.shot_beat_links
        if link.role == V2CoverageRole.PRIMARY
    )
    expected = {beat.id for beat in scene_beats.beats}
    missing = sorted(beat_id for beat_id in expected if counts[beat_id] == 0)
    duplicate = sorted(beat_id for beat_id in expected if counts[beat_id] > 1)
    if missing or duplicate:
        details = []
        if missing:
            details.append("beats without PRIMARY coverage: " + ", ".join(missing))
        if duplicate:
            details.append("beats with more than one PRIMARY link: " + ", ".join(duplicate))
        raise AggregateValidationError("; ".join(details))


def _validate_aggregate_semantics(
    stage: StageName,
    payload: StoryBibleV2 | StoryGraphV2 | SceneBeatPlanV2 | StoryboardV2,
    *,
    bible: StoryBibleV2 | None,
    graph: StoryGraphV2 | None,
    scene_beats: SceneBeatPlanV2 | None,
) -> None:
    """Prove V2 cross-record references after deterministic aggregation.

    V1's global validator must stay on the historical read path, so V2
    aggregation owns the small set of relationships that only become visible
    after shards are merged.
    """

    if stage == StageName.STORY_GRAPH:
        assert isinstance(payload, StoryGraphV2)
        node_ids = {node.id for node in payload.nodes}
        if payload.start_node_id not in node_ids or len(node_ids) != len(payload.nodes):
            raise AggregateValidationError("story graph start node or node IDs are invalid", code="aggregate.semantic_invalid")
        return
    if stage == StageName.SCENE_BEATS:
        if not isinstance(payload, SceneBeatPlanV2) or bible is None or graph is None:
            raise AggregateValidationError("scene-beats aggregation requires sealed V2 bible and graph", code="aggregate.semantic_invalid")
        scene_ids = {scene.id for scene in payload.scenes}
        beat_ids = {beat.id for beat in payload.beats}
        graph_node_ids = {node.id for node in graph.nodes}
        known_speakers = {character.id for character in bible.characters}
        if any(scene.story_node_id not in graph_node_ids for scene in payload.scenes):
            raise AggregateValidationError("scene references an unknown story node", code="aggregate.semantic_invalid")
        if any(beat.scene_id not in scene_ids for beat in payload.beats):
            raise AggregateValidationError("beat references an unknown scene", code="aggregate.semantic_invalid")
        if any(cue.beat_id not in beat_ids or (cue.speaker_id is not None and cue.speaker_id not in known_speakers) for cue in payload.dialogue_cues):
            raise AggregateValidationError("cue references an unknown beat or speaker", code="aggregate.semantic_invalid")
        return
    if stage == StageName.STORYBOARD:
        if not isinstance(payload, StoryboardV2) or scene_beats is None:
            raise AggregateValidationError("storyboard aggregation requires sealed V2 scene beats", code="aggregate.semantic_invalid")
        _assert_exactly_one_primary_per_beat(payload, scene_beats)


def _validate_canonical_parity(
    stage_plan: StagePlan,
    payload: StoryBibleV2 | StoryGraphV2 | SceneBeatPlanV2 | StoryboardV2,
    *,
    brief: ProjectBrief,
    bible: StoryBibleV2 | None,
    graph: StoryGraphV2 | None,
    scene_beats: SceneBeatPlanV2 | None,
    dialogue_timing_profile: DialogueTimingProfile | None,
) -> None:
    """Run the exact V2 installation gate before an aggregate receives a seal.

    Fragment-local binding deliberately cannot prove cross-shard ordering,
    coverage, or total timing.  The seal is therefore the first boundary that
    owns the complete candidate.  Reusing ``validate_stage_payload`` keeps
    the pre-seal and atomic-install contracts identical.

    Scene Beats and Storyboard each own the exact profile in the StagePlan
    which bound their own output.  A Storyboard-only run can consume a READY
    Scene Beats revision from an earlier run, whose canonical payload does not
    claim generator-policy provenance.  Neither branch may fall back to the
    mutable process default: accepting with a different timing policy would
    make a sealed artifact fail later during canonical installation.
    """

    timing_profile: DialogueTimingProfile | None = None
    if stage_plan.stage == StageName.SCENE_BEATS:
        timing_profile = stage_plan.dialogue_timing_profile
        if timing_profile is None:
            raise AggregateValidationError(
                "Scene Beats aggregate requires its frozen dialogue timing profile",
                code="aggregate.frozen_dialogue_timing_profile_missing",
            )
    elif stage_plan.stage == StageName.STORYBOARD:
        timing_profile = stage_plan.storyboard_dialogue_timing_profile
        if timing_profile is None:
            raise AggregateValidationError(
                "Storyboard aggregate requires its frozen dialogue timing profile",
                code="aggregate.frozen_dialogue_timing_profile_missing",
            )
        if (
            dialogue_timing_profile is not None
            and stage_plan.storyboard_dialogue_timing_profile is not None
            and dialogue_timing_profile != stage_plan.storyboard_dialogue_timing_profile
        ):
            raise AggregateValidationError(
                "Storyboard aggregate timing profile does not match its frozen StagePlan",
                code="aggregate.frozen_dialogue_timing_profile_mismatch",
            )

    try:
        validate_stage_payload(
            stage_plan.stage,
            payload,
            schema_version=2,
            brief=brief,
            bible=bible,
            graph=graph,
            scene_beats=scene_beats,
            dialogue_timing_profile=timing_profile,
        )
    except DomainValidationError as error:
        issue_codes = ", ".join(sorted({str(issue["code"]) for issue in error.issues}))
        raise AggregateValidationError(
            "aggregate failed canonical validation"
            + (f": {issue_codes}" if issue_codes else ""),
            code="aggregate.canonical_rejected",
        ) from error
    except (TypeError, ValueError) as error:
        # A malformed frozen dependency is a deterministic aggregate contract
        # failure, never a reason to defer validation until installation.
        raise AggregateValidationError(
            "aggregate cannot satisfy the canonical validation contract",
            code="aggregate.canonical_contract_invalid",
        ) from error


def _assert_aggregate_size(
    stage_plan: StagePlan,
    payload: BaseModel,
) -> None:
    item_count = _aggregate_item_count(payload)
    budget = stage_plan.work_units[0].budget
    if item_count > budget.max_aggregate_items:
        raise AggregateValidationError(
            f"aggregate contains {item_count} items, exceeding its max_aggregate_items "
            f"budget of {budget.max_aggregate_items}"
        )


def _aggregate_item_count(payload: BaseModel) -> int:
    if isinstance(payload, SceneBeatPlanV2):
        return len(payload.scenes) + len(payload.beats)
    if isinstance(payload, StoryboardV2):
        return len(payload.shots) + len(payload.shot_beat_links)
    if isinstance(payload, StoryGraphV2):
        return len(payload.nodes) + len(payload.edges) + len(payload.join_contracts)
    return len(payload.characters) + len(payload.locations) + len(payload.props) + 1
