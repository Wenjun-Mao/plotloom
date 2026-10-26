"""Trusted canonical fragment identity, duration allocation and coverage binding."""

from __future__ import annotations

from typing import Mapping, TypeAlias
from uuid import NAMESPACE_URL, uuid5

from ..canonical_schema import V2CoverageRole
from ..domain import (
    AudioEvent,
    AudioPlan,
    BeatV2,
    DialogueCue,
    DialogueTimingProfile,
    DramaticSceneV2,
    ShotBeatLinkV2,
    ShotV2,
)
from .fragments import SceneBeatsFragment, StageFragment, StoryboardFragment
from plotloom.generation.planning_contracts import GenerationWorkUnit, StagePlan
from .scene_response_contracts import (
    SceneBeatsFragmentOutput,
)
from .scene_timing_allocation import (
    SceneTimingAllocation,
)
from .storyboard_response_contracts import (
    StoryboardFragmentOutput,
)
from .work_unit_contracts import (
    AUDIO_EVENT_ID_BINDING_VERSION,
    FRAGMENT_ID_BINDING_VERSION,
    WorkUnitContractError,
)

FragmentOutput: TypeAlias = SceneBeatsFragmentOutput | StoryboardFragmentOutput


def _bind_fragment(
    output: FragmentOutput,
    *,
    stage_plan: StagePlan,
    work_unit: GenerationWorkUnit,
    dialogue_timing_profile: DialogueTimingProfile | None,
    scene_timing_allocation: SceneTimingAllocation | None,
) -> StageFragment:
    if isinstance(output, SceneBeatsFragmentOutput):
        if dialogue_timing_profile is None:
            raise WorkUnitContractError(
                "Scene Beats binding requires a frozen dialogue timing profile"
            )
        if scene_timing_allocation is None:
            raise WorkUnitContractError(
                "Scene Beats binding requires a frozen scene timing allocation"
            )
        scene_ids = {
            scene.local_scene_id: canonical_fragment_id(
                "scene",
                work_unit.selector.stable_id,
                str(scene.order),
            )
            for scene in output.scenes
        }
        beat_ids = {
            beat.local_beat_id: canonical_fragment_id(
                "beat",
                scene_ids[beat.scene_local_id],
                str(beat.order),
            )
            for beat in output.beats
        }
        bound_beats = tuple(
            BeatV2(
                id=beat_ids[beat.local_beat_id],
                scene_id=scene_ids[beat.scene_local_id],
                order=beat.order,
                description=beat.description,
                purpose=beat.purpose,
                visible_event=beat.visible_event,
                immediate_result=beat.immediate_result,
                dramatic_change=beat.dramatic_change,
                entry_state=beat.entry_state,
                exit_state=beat.exit_state,
                continuity_anchors=beat.continuity_anchors,
                continuity_delta=beat.continuity_delta,
            )
            for beat in output.beats
        )
        scene_local_id_by_beat = {
            beat.local_beat_id: beat.scene_local_id for beat in output.beats
        }
        scene_cue_duration_units: dict[str, int] = {}
        bound_cues: list[DialogueCue] = []
        for cue in output.dialogue_cues:
            duration_units = dialogue_timing_profile.estimate_text_duration_units(
                text=cue.text,
                language=cue.language,
                delivery=cue.delivery,
            )
            if duration_units is None:
                raise WorkUnitContractError(
                    "dialogue timing profile has no exact or wildcard rule"
                )
            scene_local_id = scene_local_id_by_beat[cue.beat_local_id]
            scene_cue_duration_units[scene_local_id] = (
                scene_cue_duration_units.get(scene_local_id, 0) + duration_units
            )
            bound_cues.append(
                DialogueCue(
                    id=canonical_fragment_id(
                        "dialogue-cue",
                        beat_ids[cue.beat_local_id],
                        str(cue.order),
                    ),
                    beat_id=beat_ids[cue.beat_local_id],
                    order=cue.order,
                    speaker_id=cue.speaker_id,
                    voice_over=cue.voice_over,
                    text=cue.text,
                    language=cue.language,
                    delivery=cue.delivery,
                    performance_notes=cue.performance_notes,
                    estimated_duration_units=duration_units,
                )
            )
        node_duration_budget_units = scene_timing_allocation.node_duration_budget(
            work_unit.selector.stable_id
        )
        scene_budgets = _allocate_scene_duration_budgets(
            output=output,
            scene_cue_duration_units=scene_cue_duration_units,
            node_duration_budget_units=node_duration_budget_units,
        )
        bound_scenes = tuple(
            DramaticSceneV2(
                id=scene_ids[scene.local_scene_id],
                story_node_id=work_unit.selector.stable_id,
                order=scene.order,
                title=scene.title,
                objective=scene.objective,
                location_id=scene.location_id,
                character_ids=scene.character_ids,
                beat_ids=[
                    beat_ids[beat.local_beat_id]
                    for beat in sorted(
                        (
                            item
                            for item in output.beats
                            if item.scene_local_id == scene.local_scene_id
                        ),
                        key=lambda item: item.order,
                    )
                ],
                duration_budget_units=scene_budgets[scene.local_scene_id],
                entry_state=scene.entry_state,
                exit_state=scene.exit_state,
            )
            for scene in output.scenes
        )
        return SceneBeatsFragment(
            stage_plan_hash=stage_plan.stage_plan_hash,
            work_unit_id=work_unit.unit_id,
            story_node_id=work_unit.selector.stable_id,
            scenes=bound_scenes,
            beats=bound_beats,
            dialogue_cues=tuple(bound_cues),
        )
    shot_ids = {
        shot.local_shot_id: canonical_fragment_id(
            "shot",
            work_unit.selector.stable_id,
            str(shot.order),
        )
        for shot in output.shots
    }
    return StoryboardFragment(
        stage_plan_hash=stage_plan.stage_plan_hash,
        work_unit_id=work_unit.unit_id,
        scene_id=work_unit.selector.stable_id,
        shots=tuple(
            ShotV2(
                id=shot_ids[shot.local_shot_id],
                scene_id=work_unit.selector.stable_id,
                order=shot.order,
                title=shot.title,
                shot_size=shot.shot_size,
                duration_units=shot.duration_units,
                camera_angle=shot.camera_angle,
                camera_movement=shot.camera_movement,
                composition=shot.composition,
                visual_intent=shot.visual_intent,
                motion_intent=shot.motion_intent,
                action=shot.action,
                transition=shot.transition,
                cue_ids=shot.cue_ids,
                audio_plan=AudioPlan(
                    events=[
                        AudioEvent(
                            id=canonical_audio_event_id(
                                shot_ids[shot.local_shot_id],
                                event_index,
                            ),
                            kind=event.kind,
                            description=event.description,
                            start_offset_units=event.start_offset_units,
                            duration_units=event.duration_units,
                        )
                        for event_index, event in enumerate(
                            shot.audio_plan.events,
                            start=1,
                        )
                    ]
                ),
                character_ids=shot.character_ids,
                location_id=shot.location_id,
                prop_ids=shot.prop_ids,
                required_entity_states=shot.required_entity_states,
                entry_state=shot.entry_state,
                exit_state=shot.exit_state,
            )
            for shot in output.shots
        ),
        shot_beat_links=tuple(
            [
                ShotBeatLinkV2(
                    shot_id=shot_ids[local_shot_id],
                    beat_id=beat_id,
                    role=V2CoverageRole.PRIMARY,
                    coverage_weight=1.0,
                )
                for beat_id, local_shot_id in sorted(
                    output.primary_shot_local_id_by_beat.items()
                )
            ]
            + [
                ShotBeatLinkV2(
                    shot_id=shot_ids[link.shot_local_id],
                    beat_id=link.beat_id,
                    role=V2CoverageRole.SUPPORTING,
                    coverage_weight=link.coverage_weight,
                )
                for link in output.supporting_beat_links
            ]
        ),
    )


def _allocate_scene_duration_budgets(
    *,
    output: SceneBeatsFragmentOutput,
    scene_cue_duration_units: Mapping[str, int],
    node_duration_budget_units: int,
) -> dict[str, int]:
    """Partition one frozen node cap without delegating arithmetic to a model.

    Each scene first receives the greater of one millisecond or its trusted
    dialogue minimum.  Remaining time follows the model's relative
    ``durationWeight`` using integer largest-remainder apportionment with a
    stable authored-order tie break.  Semantic validation proves feasibility
    before this trusted binder runs.
    """

    ordered = sorted(output.scenes, key=lambda scene: scene.order)
    minimums = {
        scene.local_scene_id: max(
            1, scene_cue_duration_units.get(scene.local_scene_id, 0)
        )
        for scene in ordered
    }
    remaining = node_duration_budget_units - sum(minimums.values())
    if remaining < 0:
        raise WorkUnitContractError(
            "dialogue minimums exceed the frozen Story Graph node budget"
        )
    weight_total = sum(scene.duration_weight for scene in ordered)
    allocations = dict(minimums)
    ranked_remainders: list[tuple[int, int, str]] = []
    distributed = 0
    for scene in ordered:
        numerator = remaining * scene.duration_weight
        share, remainder = divmod(numerator, weight_total)
        allocations[scene.local_scene_id] += share
        distributed += share
        ranked_remainders.append((-remainder, scene.order, scene.local_scene_id))
    for _negative_remainder, _order, scene_id in sorted(ranked_remainders)[
        : remaining - distributed
    ]:
        allocations[scene_id] += 1
    if sum(allocations.values()) != node_duration_budget_units:
        raise WorkUnitContractError(
            "scene duration allocation did not conserve node budget"
        )
    return allocations


def canonical_fragment_id(kind: str, *parts: str) -> str:
    """Bind model-local correlation IDs into the canonical UUID namespace.

    Sharded model calls cannot coordinate globally unique identifiers.  The
    trusted binder therefore derives canonical IDs solely from an immutable
    parent selector and an already-validated local order.  Model IDs remain in
    raw response evidence, while candidates and canonical stages contain only
    these reproducible IDs.
    """

    name = ":".join((FRAGMENT_ID_BINDING_VERSION, kind, *parts))
    return str(uuid5(NAMESPACE_URL, f"https://plotloom.local/{name}"))


def canonical_audio_event_id(shot_id: str, event_index: int) -> str:
    """Return the audio-event ID in its own versioned provenance namespace.

    Audio events have a separate binding contract from generic fragment IDs.
    Keeping the version in the UUID name—not merely in the prompt contract—
    ensures a future audio-only migration cannot silently claim a different
    provenance for unchanged identifiers.
    """

    if event_index < 1:
        raise ValueError("audio event index must be one-based and positive")
    name = ":".join(
        (AUDIO_EVENT_ID_BINDING_VERSION, "audio-event", shot_id, str(event_index))
    )
    return str(uuid5(NAMESPACE_URL, f"https://plotloom.local/{name}"))
