from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from .canonical_schema import DialogueTimingProfile, EntityType, SceneBeatPlanV2, StoryBibleV2, StoryboardV2
from plotloom.brief_contracts import ProjectBrief
from plotloom.gate_contracts import GateEvaluation, GateResult, GateEvidence, GateStatus, GateSeverity
from .validation_state import _allowed_entity_states
from .validation_storyboard_dialogue import dialogue_observations
from .validation_storyboard_continuity import shot_continuity_observations, sequence_continuity_observations

STORYBOARD_GATE_SET_VERSION = "storyboard.v2"


class StoryboardGateEvaluator:
    """Evaluate the deterministic, V2 authoring gates without side effects.

    This is intentionally not a validator which raises at the first error:
    callers receive an immutable complete decision set for review, and a
    required gate which could not run is represented as ``SKIPPED`` and fails
    the aggregate result.
    """

    def __init__(self, gate_set_version: str = STORYBOARD_GATE_SET_VERSION) -> None:
        if not gate_set_version.strip():
            raise ValueError("gate_set_version must not be blank")
        self.gate_set_version = gate_set_version

    def evaluate(
        self,
        storyboard: StoryboardV2,
        plan: SceneBeatPlanV2,
        bible: StoryBibleV2,
        brief: ProjectBrief | None = None,
        *,
        timing_profile: DialogueTimingProfile | None = None,
    ) -> GateEvaluation:
        evaluated_input_hash = _v2_gate_input_hash(storyboard, plan, bible, brief, timing_profile)
        results: list[GateResult] = []

        def record(
            gate_id: str,
            passed: bool | None,
            *,
            path: tuple[str | int, ...] = (),
            reason: str = "",
            evidence: tuple[tuple[str, object], ...] = (),
            required: bool = True,
        ) -> None:
            status = (
                GateStatus.PASS
                if passed is True
                else GateStatus.FAIL
                if passed is False
                else GateStatus.SKIPPED
            )
            results.append(
                GateResult(
                    id=f"{self.gate_set_version}:{gate_id}",
                    gate_set_version=self.gate_set_version,
                    gate_id=gate_id,
                    evaluated_input_hash=evaluated_input_hash,
                    required=required,
                    status=status,
                    severity=GateSeverity.INFO if passed is True else GateSeverity.ERROR,
                    entity_path=path,
                    evidence=tuple(GateEvidence(key=key, value=str(value)) for key, value in evidence),
                    reason=reason,
                )
            )

        scenes_by_id = {scene.id: scene for scene in plan.scenes}
        beats_by_id = {beat.id: beat for beat in plan.beats}
        shots_by_id = {shot.id: shot for shot in storyboard.shots}
        scene_ids = [scene.id for scene in plan.scenes]
        beat_ids = [beat.id for beat in plan.beats]
        shot_ids = [shot.id for shot in storyboard.shots]
        cue_ids = [cue.id for cue in plan.dialogue_cues]

        record(
            "scene.id.unique",
            len(scene_ids) == len(set(scene_ids)),
            path=("scenes",),
            reason="dramatic scene ids must be unique",
        )
        record(
            "beat.id.unique",
            len(beat_ids) == len(set(beat_ids)),
            path=("beats",),
            reason="beat ids must be unique",
        )
        record(
            "shot.id.unique",
            len(shot_ids) == len(set(shot_ids)),
            path=("shots",),
            reason="shot ids must be unique",
        )
        record(
            "dialogue_cue.id.unique",
            len(cue_ids) == len(set(cue_ids)),
            path=("dialogueCues",),
            reason="dialogue cue ids must be unique",
        )
        record(
            "scene.present",
            bool(plan.scenes),
            path=("scenes",),
            reason="a production storyboard requires at least one dramatic scene",
        )
        record(
            "beat.present",
            bool(plan.beats),
            path=("beats",),
            reason="a production storyboard requires at least one beat",
        )
        record(
            "shot.present",
            bool(storyboard.shots),
            path=("shots",),
            reason="a production storyboard requires at least one shot",
        )

        scenes_by_node: dict[str, list] = defaultdict(list)
        for scene in plan.scenes:
            scenes_by_node[scene.story_node_id].append(scene)
        for node_id in sorted(scenes_by_node):
            group = scenes_by_node[node_id]
            orders = sorted(scene.order for scene in group)
            record(
                f"scene.order.{node_id}",
                orders == list(range(1, len(group) + 1)),
                path=("scenes", node_id),
                reason="dramatic scene order must be contiguous and start at 1 within a story node",
                evidence=(("orders", orders),),
            )

        beats_by_scene: dict[str, list] = defaultdict(list)
        for beat in plan.beats:
            beats_by_scene[beat.scene_id].append(beat)
        for scene in sorted(plan.scenes, key=lambda item: item.id):
            scene_beats = sorted(beats_by_scene[scene.id], key=lambda item: item.order)
            record(
                f"beat.scene_reference.{scene.id}",
                all(beat.scene_id == scene.id for beat in scene_beats),
                path=("scenes", scene.id, "beatIds"),
                reason="beats must belong to their declared dramatic scene",
            )
            record(
                f"beat.order.{scene.id}",
                [beat.order for beat in scene_beats] == list(range(1, len(scene_beats) + 1)),
                path=("scenes", scene.id, "beatIds"),
                reason="beat order must be contiguous and start at 1",
            )
            record(
                f"beat.scene_membership.{scene.id}",
                scene.beat_ids == [beat.id for beat in scene_beats],
                path=("scenes", scene.id, "beatIds"),
                reason="scene beatIds must exactly match its ordered beats",
            )

        shots_by_scene: dict[str, list] = defaultdict(list)
        for shot in storyboard.shots:
            shots_by_scene[shot.scene_id].append(shot)
        for scene in sorted(plan.scenes, key=lambda item: item.id):
            scene_beats = sorted(beats_by_scene[scene.id], key=lambda item: item.order)
            scene_shots = sorted(shots_by_scene[scene.id], key=lambda item: item.order)
            if brief is None:
                count_is_valid: bool | None = None
                count_reason = "shot-count budget requires a ProjectBrief"
            else:
                count_is_valid = brief.shots_per_scene_min <= len(scene_shots) <= brief.shots_per_scene_max
                count_reason = "shot count must be inside ProjectBrief bounds"
            if brief is not None and not brief.shot_count_is_strict:
                results.append(GateResult(
                    id=f"{self.gate_set_version}:shot.count.{scene.id}",
                    gate_set_version=self.gate_set_version,
                    gate_id=f"shot.count.{scene.id}",
                    evaluated_input_hash=evaluated_input_hash,
                    required=False,
                    status=GateStatus.PASS if count_is_valid else GateStatus.NOT_APPLICABLE,
                    severity=GateSeverity.INFO if count_is_valid else GateSeverity.WARNING,
                    entity_path=("scenes", scene.id),
                    evidence=(
                        GateEvidence(key="actual", value=str(len(scene_shots))),
                        GateEvidence(key="preferredMin", value=str(brief.shots_per_scene_min)),
                        GateEvidence(key="preferredMax", value=str(brief.shots_per_scene_max)),
                    ),
                    reason="shot-count preference is advisory",
                ))
            else:
                record(
                    f"shot.count.{scene.id}", count_is_valid,
                    path=("scenes", scene.id), reason=count_reason,
                )
            record(
                f"shot.order.{scene.id}",
                [shot.order for shot in scene_shots] == list(range(1, len(scene_shots) + 1)),
                path=("scenes", scene.id),
                reason="shot order must be contiguous and start at 1",
            )
            duration = sum(shot.duration_units for shot in scene_shots)
            record(
                f"duration.budget.{scene.id}",
                duration <= scene.duration_budget_units,
                path=("scenes", scene.id, "durationBudgetUnits"),
                reason="ordered shot durations must not exceed the dramatic scene duration budget",
                evidence=(("actualUnits", duration), ("budgetUnits", scene.duration_budget_units)),
            )

        unknown_shot_scenes = sorted(set(shots_by_scene) - set(scenes_by_id))
        record(
            "shot.scene_reference",
            not unknown_shot_scenes,
            path=("shots",),
            reason="shots must reference a known dramatic scene",
            evidence=(("unknownSceneIds", unknown_shot_scenes),),
        )
        unknown_beat_scenes = sorted(set(beats_by_scene) - set(scenes_by_id))
        record(
            "beat.scene_reference.all",
            not unknown_beat_scenes,
            path=("beats",),
            reason="beats must reference a known dramatic scene",
            evidence=(("unknownSceneIds", unknown_beat_scenes),),
        )

        character_ids = {entity.id for entity in bible.characters}
        location_ids = {entity.id for entity in bible.locations}
        prop_ids = {entity.id for entity in bible.props}
        allowed_states = _allowed_entity_states(bible)
        for shot in sorted(storyboard.shots, key=lambda item: item.id):
            entity_references_are_unique = (
                len(shot.character_ids) == len(set(shot.character_ids))
                and len(shot.prop_ids) == len(set(shot.prop_ids))
            )
            record(
                f"entity.reference_unique.{shot.id}",
                entity_references_are_unique,
                path=("shots", shot.id),
                reason="shot characterIds and propIds must not contain duplicates",
            )
            record(
                f"entity.reference.{shot.id}",
                set(shot.character_ids) <= character_ids
                and (shot.location_id is None or shot.location_id in location_ids)
                and set(shot.prop_ids) <= prop_ids,
                path=("shots", shot.id),
                reason="shot entities must be present in the story bible",
            )
            state_keys = [
                (state.entity_type, state.entity_id)
                for state in shot.required_entity_states
            ]
            record(
                f"entity.required_state.unique.{shot.id}",
                len(state_keys) == len(set(state_keys)),
                path=("shots", shot.id, "requiredEntityStates"),
                reason="a shot must require at most one state for each entity",
            )
            states_are_valid = True
            states_are_in_scope = True
            for state in shot.required_entity_states:
                states_are_valid = states_are_valid and state.entity_id in allowed_states[state.entity_type] and state.state in allowed_states[state.entity_type].get(state.entity_id, set())
                if state.entity_type == EntityType.CHARACTER:
                    states_are_in_scope = states_are_in_scope and state.entity_id in shot.character_ids
                elif state.entity_type == EntityType.LOCATION:
                    states_are_in_scope = states_are_in_scope and state.entity_id == shot.location_id
                else:
                    states_are_in_scope = states_are_in_scope and state.entity_id in shot.prop_ids
            record(
                f"entity.required_state.available.{shot.id}", states_are_valid,
                path=("shots", shot.id, "requiredEntityStates"),
                reason="required entity states must be allowed by the story bible",
            )
            record(
                f"entity.required_state.scope.{shot.id}", states_are_in_scope,
                path=("shots", shot.id, "requiredEntityStates"),
                reason="required entity states must belong to an entity present in the shot",
            )
            audio_event_ids = [event.id for event in shot.audio_plan.events]
            record(
                f"audio.event_id.unique.{shot.id}",
                len(audio_event_ids) == len(set(audio_event_ids)),
                path=("shots", shot.id, "audioPlan", "events"),
                reason="audio event IDs must be unique within a shot",
            )
            audio_in_bounds = all(
                event.start_offset_units + event.duration_units <= shot.duration_units
                for event in shot.audio_plan.events
            )
            record(
                f"audio.timing.{shot.id}", audio_in_bounds,
                path=("shots", shot.id, "audioPlan"),
                reason="structured audio events must fit inside their shot duration",
            )
            for observation in shot_continuity_observations(shot, bible):
                record(observation.gate_id, observation.passed, path=observation.path, reason=observation.reason, evidence=observation.evidence, required=observation.required)

        for observation in dialogue_observations(storyboard, plan, bible, timing_profile):
            record(observation.gate_id, observation.passed, path=observation.path, reason=observation.reason, evidence=observation.evidence, required=observation.required)

        primary_count_by_beat: dict[str, int] = defaultdict(int)
        linked_shots: set[str] = set()
        seen_links: set[tuple[str, str]] = set()
        for index, link in enumerate(storyboard.shot_beat_links):
            pair = (link.shot_id, link.beat_id)
            duplicate_link = pair in seen_links
            references_exist = link.shot_id in shots_by_id and link.beat_id in beats_by_id
            if not references_exist:
                link_identity = f"invalid-{index}"
            elif duplicate_link:
                link_identity = f"duplicate-{index}"
            else:
                # StableId excludes dots, so this maps exactly one link pair to
                # one durable gate identity regardless of JSON list ordering.
                link_identity = f"{link.shot_id}.{link.beat_id}"
            record(
                f"coverage.link.unique.{link_identity}", not duplicate_link,
                path=("shotBeatLinks", index), reason="shot-to-beat links must not be duplicated",
            )
            seen_links.add(pair)
            record(
                f"coverage.link.reference.{link_identity}", references_exist,
                path=("shotBeatLinks", index), reason="shot-to-beat links must reference known records",
            )
            if not references_exist:
                continue
            linked_shots.add(link.shot_id)
            same_scene = shots_by_id[link.shot_id].scene_id == beats_by_id[link.beat_id].scene_id
            record(
                f"coverage.link.scene.{link_identity}", same_scene,
                path=("shotBeatLinks", index), reason="a shot can cover only a beat in the same scene",
            )
            if link.role.value == "primary":
                primary_count_by_beat[link.beat_id] += 1
        for beat_id in sorted(beats_by_id):
            record(
                f"coverage.primary.{beat_id}", primary_count_by_beat[beat_id] == 1,
                path=("shotBeatLinks", beat_id), reason="each beat requires exactly one PRIMARY shot link",
            )
        record(
            "coverage.shot.linked", set(shots_by_id) == linked_shots,
            path=("shotBeatLinks",), reason="every shot must cover at least one beat",
        )

        for observation in sequence_continuity_observations(storyboard, plan, bible):
            record(observation.gate_id, observation.passed, path=observation.path, reason=observation.reason, evidence=observation.evidence, required=observation.required)

        return GateEvaluation(
            gate_set_version=self.gate_set_version,
            evaluated_input_hash=evaluated_input_hash,
            results=tuple(results),
        )


def _v2_gate_input_hash(
    storyboard: StoryboardV2,
    plan: SceneBeatPlanV2,
    bible: StoryBibleV2,
    brief: ProjectBrief | None,
    timing_profile: DialogueTimingProfile | None,
) -> str:
    payload = {
        "storyboard": storyboard.model_dump(mode="json", by_alias=True),
        "sceneBeats": plan.model_dump(mode="json", by_alias=True),
        "storyBible": bible.model_dump(mode="json", by_alias=True),
        "brief": None if brief is None else brief.model_dump(mode="json", by_alias=True),
        "timingProfile": None if timing_profile is None else timing_profile.model_dump(mode="json", by_alias=True),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
