from __future__ import annotations

from collections import defaultdict
from .canonical_schema import SceneBeatPlanV2, StoryBibleV2, StoryGraphV2, StoryboardV2, V2CoverageRole
from .domain import ProjectBrief
from .json_value_contract import CanonicalJsonValueError, finite_json_values_equal
from .join_state_values import JoinStateValueContractError, compile_join_state_value_contract
from .edge_entry_states import EdgeEntryStateContractError, compile_edge_entry_state_contract
from .validation_issues import DomainValidationError, ValidationIssue, _duplicates, _issue

def validate_scene_beat_coverage(
    plan: SceneBeatPlanV2,
    graph: StoryGraphV2,
    bible: StoryBibleV2,
) -> None:
    issues: list[ValidationIssue] = []
    scenes_by_id = {scene.id: scene for scene in plan.scenes}
    graph_node_ids = {node.id for node in graph.nodes}
    character_ids = {character.id for character in bible.characters}
    location_ids = {location.id for location in bible.locations}

    for scene_id in sorted(_duplicates(scene.id for scene in plan.scenes)):
        issues.append(_issue("duplicate_scene_id", "scenes", f"duplicate scene id: {scene_id}"))
    for beat_id in sorted(_duplicates(beat.id for beat in plan.beats)):
        issues.append(_issue("duplicate_beat_id", "beats", f"duplicate beat id: {beat_id}"))

    scenes_by_node: dict[str, list] = defaultdict(list)
    beats_by_scene: dict[str, list] = defaultdict(list)
    for beat in plan.beats:
        beats_by_scene[beat.scene_id].append(beat)
        if beat.scene_id not in scenes_by_id:
            issues.append(_issue("unknown_beat_scene", f"beats.{beat.id}", f"unknown scene: {beat.scene_id}"))

    for scene in plan.scenes:
        scenes_by_node[scene.story_node_id].append(scene)
        if scene.story_node_id not in graph_node_ids:
            issues.append(
                _issue("unknown_story_node", f"scenes.{scene.id}", f"unknown story node: {scene.story_node_id}")
            )
        if scene.location_id is not None and scene.location_id not in location_ids:
            issues.append(
                _issue("unknown_location", f"scenes.{scene.id}.locationId", f"unknown location: {scene.location_id}")
            )
        unknown_characters = set(scene.character_ids) - character_ids
        if unknown_characters:
            issues.append(
                _issue(
                    "unknown_characters",
                    f"scenes.{scene.id}.characterIds",
                    f"unknown characters: {', '.join(sorted(unknown_characters))}",
                )
            )
        actual_beats = sorted(beats_by_scene[scene.id], key=lambda beat: beat.order)
        actual_ids = [beat.id for beat in actual_beats]
        if scene.beat_ids != actual_ids:
            issues.append(
                _issue(
                    "scene_beat_order_mismatch",
                    f"scenes.{scene.id}.beatIds",
                    "beatIds must exactly match the scene's beats in order",
                )
            )
        expected_order = list(range(1, len(actual_beats) + 1))
        actual_order = [beat.order for beat in actual_beats]
        if actual_order != expected_order:
            issues.append(
                _issue(
                    "non_contiguous_beat_order",
                    f"scenes.{scene.id}.beatIds",
                    "beat order must be contiguous and start at 1",
                )
            )

    footage_node_ids = {node.id for node in graph.nodes if node.footage_mode == "footage"}
    uncovered_nodes = footage_node_ids - set(scenes_by_node)
    unexpected_footage = set(scenes_by_node) & (graph_node_ids - footage_node_ids)
    if unexpected_footage:
        issues.append(_issue("route_only_has_scene", "scenes", "route-only nodes cannot have scenes: " + ", ".join(sorted(unexpected_footage))))
    from .node_footage import route_only_state_issues
    issues.extend(ValidationIssue(**issue) for issue in route_only_state_issues(graph))
    if uncovered_nodes:
        issues.append(
            _issue(
                "uncovered_story_nodes",
                "scenes",
                f"story nodes have no dramatic scene: {', '.join(sorted(uncovered_nodes))}",
            )
        )

    join_state_values = None
    try:
        join_state_values = compile_join_state_value_contract(graph)
    except JoinStateValueContractError as error:
        issues.extend(
            _issue(issue.code, issue.path, issue.message)
            for issue in error.issues
        )
    edge_entry_states = None
    try:
        edge_entry_states = compile_edge_entry_state_contract(graph)
    except EdgeEntryStateContractError as error:
        issues.extend(
            _issue(issue.code, issue.path, issue.message)
            for issue in error.issues
        )
    join_values_by_contract = (
        {
            (entry.join_contract_id, entry.state_key): entry.expected_join_entry_value
            for entry in join_state_values.entries
        }
        if join_state_values is not None
        else {}
    )
    for contract in graph.join_contracts:
        join_scenes = scenes_by_node.get(contract.join_node_id, [])
        for key in contract.required_state_keys:
            expected_key = (contract.id, key)
            if expected_key not in join_values_by_contract:
                continue
            expected = join_values_by_contract[expected_key]
            if not join_scenes:
                issues.append(
                    _issue(
                        "join_entry_state_value_missing",
                        f"joinContracts.{contract.id}.requiredStateKeys",
                        f"join scene entry state is missing required fact: {key}",
                    )
                )

            for scene in join_scenes:
                if key not in scene.entry_state.facts:
                    issues.append(
                        _issue(
                            "join_entry_state_value_missing",
                            f"scenes.{scene.id}.entryState.facts.{key}",
                            f"join entry must contain exact required fact {key!r}",
                        )
                    )
                else:
                    try:
                        matches = finite_json_values_equal(
                            scene.entry_state.facts[key],
                            expected,
                        )
                    except CanonicalJsonValueError:
                        issues.append(
                            _issue(
                                "join_entry_state_value_not_json",
                                f"scenes.{scene.id}.entryState.facts.{key}",
                                "join entry facts must be finite canonical JSON values",
                            )
                        )
                    else:
                        if not matches:
                            issues.append(
                                _issue(
                                    "join_entry_state_value_mismatch",
                                    f"scenes.{scene.id}.entryState.facts.{key}",
                                    f"join entry fact {key!r} does not match the sealed edge-transition contract",
                                )
                            )

    if edge_entry_states is not None:
        for node_id, requirements in edge_entry_states.requirements_by_target.items():
            first_scenes = [
                scene for scene in scenes_by_node.get(node_id, []) if scene.order == 1
            ]
            for scene in first_scenes:
                states = {
                    (state.entity_type, state.entity_id): state.state
                    for state in scene.entry_state.entity_states
                }
                for requirement in requirements:
                    path = (
                        f"scenes.{scene.id}.entryState.entityStates."
                        f"{requirement.entity_type.value}.{requirement.entity_id}"
                    )
                    actual = states.get((requirement.entity_type, requirement.entity_id))
                    if actual is None:
                        issues.append(
                            _issue(
                                "edge_entry_entity_state_missing",
                                path,
                                "first target-scene entry is missing a typed direct-edge state",
                            )
                        )
                    elif actual != requirement.state:
                        issues.append(
                            _issue(
                                "edge_entry_entity_state_mismatch",
                                path,
                                "first target-scene entry differs from its typed direct-edge state",
                            )
                        )

    if issues:
        raise DomainValidationError(issues)


def validate_storyboard_coverage(
    storyboard: StoryboardV2,
    plan: SceneBeatPlanV2,
    bible: StoryBibleV2,
    brief: ProjectBrief,
) -> None:
    issues: list[ValidationIssue] = []
    scenes_by_id = {scene.id: scene for scene in plan.scenes}
    beats_by_id = {beat.id: beat for beat in plan.beats}
    shots_by_id = {shot.id: shot for shot in storyboard.shots}
    character_ids = {character.id for character in bible.characters}
    location_ids = {location.id for location in bible.locations}
    prop_ids = {prop.id for prop in bible.props}

    for shot_id in sorted(_duplicates(shot.id for shot in storyboard.shots)):
        issues.append(_issue("duplicate_shot_id", "shots", f"duplicate shot id: {shot_id}"))

    shots_by_scene: dict[str, list] = defaultdict(list)
    for shot in storyboard.shots:
        shots_by_scene[shot.scene_id].append(shot)
        if shot.scene_id not in scenes_by_id:
            issues.append(_issue("unknown_shot_scene", f"shots.{shot.id}", f"unknown scene: {shot.scene_id}"))
        if shot.location_id is not None and shot.location_id not in location_ids:
            issues.append(_issue("unknown_location", f"shots.{shot.id}.locationId", "shot references unknown location"))
        unknown_characters = set(shot.character_ids) - character_ids
        if unknown_characters:
            issues.append(
                _issue(
                    "unknown_characters",
                    f"shots.{shot.id}.characterIds",
                    f"unknown characters: {', '.join(sorted(unknown_characters))}",
                )
            )
        unknown_props = set(shot.prop_ids) - prop_ids
        if unknown_props:
            issues.append(
                _issue(
                    "unknown_props",
                    f"shots.{shot.id}.propIds",
                    f"unknown props: {', '.join(sorted(unknown_props))}",
                )
            )

    for scene_id in scenes_by_id:
        scene_shots = sorted(shots_by_scene[scene_id], key=lambda shot: shot.order)
        count = len(scene_shots)
        if brief.shot_count_is_strict and not brief.shots_per_scene_min <= count <= brief.shots_per_scene_max:
            issues.append(
                _issue(
                    "shots_per_scene_out_of_range",
                    f"scenes.{scene_id}",
                    f"scene has {count} shots; expected {brief.shots_per_scene_min}..{brief.shots_per_scene_max}",
                )
            )
        if [shot.order for shot in scene_shots] != list(range(1, count + 1)):
            issues.append(
                _issue(
                    "non_contiguous_shot_order",
                    f"scenes.{scene_id}",
                    "shot order must be contiguous and start at 1",
                )
            )

    linked_shots: set[str] = set()
    primary_count_by_beat: dict[str, int] = defaultdict(int)
    link_pairs: set[tuple[str, str]] = set()
    for index, link in enumerate(storyboard.shot_beat_links):
        path = f"shotBeatLinks.{index}"
        pair = (link.shot_id, link.beat_id)
        if pair in link_pairs:
            issues.append(_issue("duplicate_shot_beat_link", path, "duplicate shot-to-beat link"))
        link_pairs.add(pair)
        if link.shot_id not in shots_by_id:
            issues.append(_issue("unknown_link_shot", path, f"unknown shot: {link.shot_id}"))
            continue
        if link.beat_id not in beats_by_id:
            issues.append(_issue("unknown_link_beat", path, f"unknown beat: {link.beat_id}"))
            continue
        if shots_by_id[link.shot_id].scene_id != beats_by_id[link.beat_id].scene_id:
            issues.append(_issue("cross_scene_link", path, "a shot can only cover a beat from the same scene"))
        linked_shots.add(link.shot_id)
        if link.role == V2CoverageRole.PRIMARY:
            primary_count_by_beat[link.beat_id] += 1

    unlinked_shots = set(shots_by_id) - linked_shots
    if unlinked_shots:
        issues.append(
            _issue("unlinked_shots", "shotBeatLinks", f"shots cover no beat: {', '.join(sorted(unlinked_shots))}")
        )
    uncovered_beats = {
        beat_id for beat_id in beats_by_id if primary_count_by_beat[beat_id] == 0
    }
    if uncovered_beats:
        issues.append(
            _issue(
                "beats_without_primary_coverage",
                "shotBeatLinks",
                f"beats lack primary shot coverage: {', '.join(sorted(uncovered_beats))}",
            )
        )
    multiply_primary_beats = {
        beat_id: count
        for beat_id, count in primary_count_by_beat.items()
        if beat_id in beats_by_id and count > 1
    }
    for beat_id, count in sorted(multiply_primary_beats.items()):
        issues.append(
            _issue(
                "multiple_primary_shot_coverage",
                "shotBeatLinks",
                f"beat {beat_id} has {count} PRIMARY shot links; expected exactly one",
            )
        )

    if issues:
        raise DomainValidationError(issues)
