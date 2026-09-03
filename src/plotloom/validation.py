from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

from pydantic import ValidationError

from .domain import (
    CoverageRole,
    ProjectBrief,
    SceneBeatPlan,
    StageName,
    StoryBible,
    Storyboard,
    StoryGraph,
    StoryNodeKind,
)


class ValidationIssue(dict):
    """JSON-ready validation issue with a stable code and data path."""

    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(code=code, path=path, message=message)


class DomainValidationError(ValueError):
    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = list(issues)
        message = "; ".join(issue["message"] for issue in self.issues)
        super().__init__(message or "domain validation failed")


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _issue(code: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=path, message=message)


def validate_story_graph(graph: StoryGraph, brief: ProjectBrief) -> None:
    issues: list[ValidationIssue] = []
    nodes_by_id = {node.id: node for node in graph.nodes}

    for node_id in sorted(_duplicates(node.id for node in graph.nodes)):
        issues.append(_issue("duplicate_node_id", "nodes", f"duplicate story node id: {node_id}"))
    for edge_id in sorted(_duplicates(edge.id for edge in graph.edges)):
        issues.append(_issue("duplicate_edge_id", "edges", f"duplicate story edge id: {edge_id}"))
    for contract_id in sorted(_duplicates(contract.id for contract in graph.join_contracts)):
        issues.append(
            _issue("duplicate_join_contract_id", "joinContracts", f"duplicate join contract id: {contract_id}")
        )

    if graph.start_node_id not in nodes_by_id:
        issues.append(_issue("missing_start_node", "startNodeId", "startNodeId does not reference a node"))
    else:
        start_nodes = [node.id for node in graph.nodes if node.kind == StoryNodeKind.START]
        if start_nodes != [graph.start_node_id]:
            issues.append(
                _issue(
                    "invalid_start_nodes",
                    "nodes",
                    "the graph must have exactly one start node and it must match startNodeId",
                )
            )

    adjacency: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, set[str]] = defaultdict(set)
    for index, edge in enumerate(graph.edges):
        path = f"edges.{index}"
        if edge.source_node_id not in nodes_by_id:
            issues.append(_issue("unknown_edge_source", path, f"unknown source node: {edge.source_node_id}"))
            continue
        if edge.target_node_id not in nodes_by_id:
            issues.append(_issue("unknown_edge_target", path, f"unknown target node: {edge.target_node_id}"))
            continue
        if edge.source_node_id == edge.target_node_id:
            issues.append(_issue("self_loop", path, "story graph self-loops are not allowed"))
        adjacency[edge.source_node_id].append(edge.target_node_id)
        incoming[edge.target_node_id].add(edge.source_node_id)

    if len(graph.nodes) > brief.node_budget:
        issues.append(
            _issue(
                "node_budget_exceeded",
                "nodes",
                f"graph has {len(graph.nodes)} nodes but nodeBudget is {brief.node_budget}",
            )
        )

    for node_id, targets in adjacency.items():
        if len(targets) > brief.max_out_degree:
            issues.append(
                _issue(
                    "max_out_degree_exceeded",
                    f"nodes.{node_id}",
                    f"out-degree {len(targets)} exceeds maxOutDegree {brief.max_out_degree}",
                )
            )

    for node in graph.nodes:
        degree = len(adjacency[node.id])
        if node.kind == StoryNodeKind.ENDING and degree:
            issues.append(_issue("ending_has_outgoing_edge", f"nodes.{node.id}", "ending nodes must be terminal"))
        if node.kind != StoryNodeKind.ENDING and degree == 0:
            issues.append(_issue("dead_end", f"nodes.{node.id}", "non-ending nodes must have an outgoing edge"))
        if node.kind == StoryNodeKind.DECISION and degree < 2:
            issues.append(
                _issue("decision_without_branches", f"nodes.{node.id}", "decision nodes require at least two branches")
            )

    endings = [node for node in graph.nodes if node.kind == StoryNodeKind.ENDING]
    if len(endings) != brief.ending_count:
        issues.append(
            _issue(
                "ending_count_mismatch",
                "nodes",
                f"graph has {len(endings)} endings but endingCount is {brief.ending_count}",
            )
        )

    # Kahn's algorithm verifies the DAG contract independently of reachability.
    indegree = {node_id: 0 for node_id in nodes_by_id}
    for source_id, targets in adjacency.items():
        if source_id not in nodes_by_id:
            continue
        for target_id in targets:
            if target_id in indegree:
                indegree[target_id] += 1
    queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    visited_count = 0
    while queue:
        node_id = queue.popleft()
        visited_count += 1
        for target_id in adjacency[node_id]:
            if target_id not in indegree:
                continue
            indegree[target_id] -= 1
            if indegree[target_id] == 0:
                queue.append(target_id)
    graph_is_dag = visited_count == len(nodes_by_id)
    if not graph_is_dag:
        issues.append(_issue("cycle", "edges", "story graph must be acyclic"))

    reachable: set[str] = set()
    if graph.start_node_id in nodes_by_id:
        frontier = [graph.start_node_id]
        while frontier:
            node_id = frontier.pop()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            frontier.extend(adjacency[node_id])
    unreachable = set(nodes_by_id) - reachable
    if unreachable:
        issues.append(
            _issue(
                "unreachable_nodes",
                "nodes",
                f"nodes are unreachable from startNodeId: {', '.join(sorted(unreachable))}",
            )
        )

    join_node_ids = {node_id for node_id, sources in incoming.items() if len(sources) >= 2}
    if len(join_node_ids) != brief.desired_join_count:
        issues.append(
            _issue(
                "join_count_mismatch",
                "joinContracts",
                f"graph has {len(join_node_ids)} joins but desiredJoinCount is {brief.desired_join_count}",
            )
        )
    contracts_by_node: dict[str, list] = defaultdict(list)
    for contract in graph.join_contracts:
        contracts_by_node[contract.join_node_id].append(contract)
        if contract.join_node_id not in nodes_by_id:
            issues.append(
                _issue(
                    "unknown_join_node",
                    f"joinContracts.{contract.id}",
                    f"unknown join node: {contract.join_node_id}",
                )
            )
            continue
        actual_sources = incoming[contract.join_node_id]
        declared_sources = set(contract.incoming_node_ids)
        if len(actual_sources) < 2:
            issues.append(
                _issue(
                    "not_a_join",
                    f"joinContracts.{contract.id}",
                    "join contract target must have at least two incoming story edges",
                )
            )
        if declared_sources != actual_sources:
            issues.append(
                _issue(
                    "join_sources_mismatch",
                    f"joinContracts.{contract.id}.incomingNodeIds",
                    "incomingNodeIds must exactly match the graph's incoming sources",
                )
            )
    for join_node_id in join_node_ids:
        if len(contracts_by_node[join_node_id]) != 1:
            issues.append(
                _issue(
                    "join_contract_cardinality",
                    "joinContracts",
                    f"join node {join_node_id} requires exactly one join contract",
                )
            )

    # Path counting is only meaningful after the topology is known to be a DAG.
    if graph_is_dag and graph.start_node_id in nodes_by_id:
        path_stack: list[tuple[str, int, tuple[str, ...]]] = [(graph.start_node_id, 0, ())]
        while path_stack:
            node_id, decision_count, path = path_stack.pop()
            node = nodes_by_id[node_id]
            next_count = decision_count + int(node.kind == StoryNodeKind.DECISION)
            next_path = (*path, node_id)
            if node.kind == StoryNodeKind.ENDING:
                if next_count != brief.decision_points_per_path:
                    issues.append(
                        _issue(
                            "decision_points_per_path_mismatch",
                            "edges",
                            f"path {' -> '.join(next_path)} has {next_count} decision points; expected "
                            f"{brief.decision_points_per_path}",
                        )
                    )
                continue
            for target_id in adjacency[node_id]:
                path_stack.append((target_id, next_count, next_path))

    if issues:
        raise DomainValidationError(issues)


def validate_scene_beat_coverage(
    plan: SceneBeatPlan,
    graph: StoryGraph,
    bible: StoryBible,
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

    uncovered_nodes = graph_node_ids - set(scenes_by_node)
    if uncovered_nodes:
        issues.append(
            _issue(
                "uncovered_story_nodes",
                "scenes",
                f"story nodes have no dramatic scene: {', '.join(sorted(uncovered_nodes))}",
            )
        )

    for contract in graph.join_contracts:
        join_scenes = scenes_by_node.get(contract.join_node_id, [])
        for key in contract.required_state_keys:
            if not join_scenes or any(key not in scene.entry_state.facts for scene in join_scenes):
                issues.append(
                    _issue(
                        "join_entry_state_missing",
                        f"joinContracts.{contract.id}.requiredStateKeys",
                        f"join scene entry state is missing required fact: {key}",
                    )
                )
            for incoming_node_id in contract.incoming_node_ids:
                incoming_scenes = scenes_by_node.get(incoming_node_id, [])
                if not incoming_scenes or any(key not in scene.exit_state.facts for scene in incoming_scenes):
                    issues.append(
                        _issue(
                            "join_exit_state_missing",
                            f"joinContracts.{contract.id}.requiredStateKeys",
                            f"incoming node {incoming_node_id} exit state is missing required fact: {key}",
                        )
                    )

    if issues:
        raise DomainValidationError(issues)


def validate_storyboard_coverage(
    storyboard: Storyboard,
    plan: SceneBeatPlan,
    bible: StoryBible,
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
        if not brief.shots_per_scene_min <= count <= brief.shots_per_scene_max:
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
        if link.role == CoverageRole.PRIMARY:
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


def pydantic_issues(error: ValidationError) -> list[ValidationIssue]:
    return [
        _issue(
            "schema_validation",
            ".".join(str(part) for part in item["loc"]),
            item["msg"],
        )
        for item in error.errors()
    ]


def validate_stage_payload(
    stage: StageName,
    payload: StoryBible | StoryGraph | SceneBeatPlan | Storyboard,
    *,
    brief: ProjectBrief,
    bible: StoryBible | None = None,
    graph: StoryGraph | None = None,
    scene_beats: SceneBeatPlan | None = None,
) -> None:
    if stage == StageName.STORY_BIBLE:
        return
    if stage == StageName.STORY_GRAPH:
        if not isinstance(payload, StoryGraph):
            raise TypeError("story_graph requires StoryGraph")
        validate_story_graph(payload, brief)
        return
    if stage == StageName.SCENE_BEATS:
        if not isinstance(payload, SceneBeatPlan) or bible is None or graph is None:
            raise TypeError("scene_beats requires SceneBeatPlan, StoryBible, and StoryGraph")
        validate_scene_beat_coverage(payload, graph, bible)
        return
    if not isinstance(payload, Storyboard) or bible is None or scene_beats is None:
        raise TypeError("storyboard requires Storyboard, StoryBible, and SceneBeatPlan")
    validate_storyboard_coverage(payload, scene_beats, bible, brief)
