from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
import hashlib
import json
from typing import Literal

from pydantic import ValidationError

from .domain import (
    CoverageRole,
    GateEvaluation,
    GateEvidence,
    GateResult,
    GateSeverity,
    GateStatus,
    ProjectBrief,
    SceneBeatPlan,
    StageName,
    StoryBible,
    Storyboard,
    StoryGraph,
    StoryNodeKind,
)
from .canonical_schema import (
    DialogueCue,
    DialogueTimingProfile,
    EntityType,
    SceneBeatPlanV2,
    StoryBibleV2,
    StoryboardV2,
    StoryGraphV2,
)
from .domain import default_dialogue_timing_profile
from .generation.scene_timing_allocation import plan_scene_timing_allocation


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


def validate_story_graph(
    graph: StoryGraph,
    brief: ProjectBrief,
    *,
    strict_v2: bool = False,
) -> None:
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
    seen_connections: set[tuple[str, str]] = set()
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
        connection = (edge.source_node_id, edge.target_node_id)
        if strict_v2 and connection in seen_connections:
            issues.append(
                _issue(
                    "duplicate_edge_connection",
                    path,
                    "story graph may not contain duplicate directed connections",
                )
            )
            # Duplicate edge rows must never manufacture an additional branch
            # or consume an extra out-degree slot.
            continue
        seen_connections.add(connection)
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
    *,
    strict_v2: bool = False,
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
        if strict_v2 and contract.allowed_differences and not contract.reconciliation.strip():
            issues.append(
                _issue(
                    "join_allowed_difference_without_reconciliation",
                    f"joinContracts.{contract.id}.reconciliation",
                    "allowedDifferences require an explicit reconciliation",
                )
            )
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
            if strict_v2:
                states_with_key = [
                    scene.entry_state.facts[key]
                    for scene in join_scenes
                    if key in scene.entry_state.facts
                ]
                for incoming_node_id in contract.incoming_node_ids:
                    incoming_scenes = scenes_by_node.get(incoming_node_id, [])
                    states_with_key.extend(
                        scene.exit_state.facts[key]
                        for scene in incoming_scenes
                        if key in scene.exit_state.facts
                    )
                if (
                    key not in contract.allowed_differences
                    and states_with_key
                    and any(value != states_with_key[0] for value in states_with_key[1:])
                ):
                    issues.append(
                        _issue(
                            "join_required_state_mismatch",
                            f"joinContracts.{contract.id}.requiredStateKeys",
                            f"required join state {key!r} must agree across incoming exits and join entry",
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
    payload: StoryBible | StoryGraph | SceneBeatPlan | Storyboard | StoryBibleV2 | StoryGraphV2 | SceneBeatPlanV2 | StoryboardV2,
    *,
    schema_version: Literal[1, 2],
    brief: ProjectBrief,
    bible: StoryBible | StoryBibleV2 | None = None,
    graph: StoryGraph | StoryGraphV2 | None = None,
    scene_beats: SceneBeatPlan | SceneBeatPlanV2 | None = None,
    dialogue_timing_profile: DialogueTimingProfile | None = None,
) -> GateEvaluation | None:
    """Validate one explicitly versioned canonical stage.

    Shape inference would let a partly migrated V1 record acquire current
    semantics accidentally.  Every persistence caller therefore supplies the
    revision's schema version, and V2 storyboard installation receives the
    successful immutable gate receipt in the same transaction.
    """

    if schema_version == 2:
        return _validate_stage_payload_v2(
            stage,
            payload,
            brief=brief,
            bible=bible,
            graph=graph,
            scene_beats=scene_beats,
            dialogue_timing_profile=dialogue_timing_profile,
        )
    if schema_version != 1:
        raise ValueError(f"unsupported canonical schema version: {schema_version}")
    if stage == StageName.STORY_BIBLE:
        if not isinstance(payload, StoryBible):
            raise TypeError("V1 story_bible requires StoryBible")
        return
    if stage == StageName.STORY_GRAPH:
        if not isinstance(payload, StoryGraph):
            raise TypeError("V1 story_graph requires StoryGraph")
        validate_story_graph(payload, brief)
        return
    if stage == StageName.SCENE_BEATS:
        if not isinstance(payload, SceneBeatPlan) or bible is None or graph is None:
            raise TypeError("V1 scene_beats requires SceneBeatPlan, StoryBible, and StoryGraph")
        if not isinstance(bible, StoryBible) or not isinstance(graph, StoryGraph):
            raise TypeError("V1 scene_beats requires V1 upstream payloads")
        validate_scene_beat_coverage(payload, graph, bible)
        return
    if not isinstance(payload, Storyboard) or bible is None or scene_beats is None:
        raise TypeError("V1 storyboard requires Storyboard, StoryBible, and SceneBeatPlan")
    if not isinstance(bible, StoryBible) or not isinstance(scene_beats, SceneBeatPlan):
        raise TypeError("V1 storyboard requires V1 upstream payloads")
    validate_storyboard_coverage(payload, scene_beats, bible, brief)


def _validate_stage_payload_v2(
    stage: StageName,
    payload: StoryBible | StoryGraph | SceneBeatPlan | Storyboard | StoryBibleV2 | StoryGraphV2 | SceneBeatPlanV2 | StoryboardV2,
    *,
    brief: ProjectBrief,
    bible: StoryBible | StoryBibleV2 | None,
    graph: StoryGraph | StoryGraphV2 | None,
    scene_beats: SceneBeatPlan | SceneBeatPlanV2 | None,
    dialogue_timing_profile: DialogueTimingProfile | None,
) -> GateEvaluation | None:
    if stage == StageName.STORY_BIBLE:
        if not isinstance(payload, StoryBibleV2):
            raise TypeError("V2 story_bible requires StoryBibleV2")
        return None
    if stage == StageName.STORY_GRAPH:
        if not isinstance(payload, StoryGraphV2):
            raise TypeError("V2 story_graph requires StoryGraphV2")
        # The graph algorithm is schema-neutral and uses only the stable graph
        # contract; the explicit isinstance above prevents a V1/V2 mix.
        validate_story_graph(payload, brief, strict_v2=True)  # type: ignore[arg-type]
        return None
    if stage == StageName.SCENE_BEATS:
        if not isinstance(payload, SceneBeatPlanV2) or not isinstance(bible, StoryBibleV2) or not isinstance(graph, StoryGraphV2):
            raise TypeError("V2 scene_beats requires SceneBeatPlanV2, StoryBibleV2, and StoryGraphV2")
        validate_scene_beat_coverage(payload, graph, bible, strict_v2=True)  # type: ignore[arg-type]
        _validate_v2_scene_order_and_continuity(payload, bible)
        _validate_v2_dialogue_cues(
            payload,
            bible,
            timing_profile=dialogue_timing_profile,
        )
        _validate_v2_scene_timing_allocation(payload, graph, brief)
        return None
    if not isinstance(payload, StoryboardV2) or not isinstance(bible, StoryBibleV2) or not isinstance(scene_beats, SceneBeatPlanV2):
        raise TypeError("V2 storyboard requires StoryboardV2, StoryBibleV2, and SceneBeatPlanV2")
    evaluation = StoryboardGateEvaluator().evaluate(
        payload,
        scene_beats,
        bible,
        brief,
        timing_profile=dialogue_timing_profile or default_dialogue_timing_profile(),
    )
    failed = [result for result in evaluation.results if not result.passed]
    if failed:
        raise DomainValidationError(
            _issue(
                f"gate.{result.gate_id}",
                ".".join(str(part) for part in result.entity_path),
                result.reason or f"V2 gate {result.gate_id} did not pass ({result.status.value})",
            )
            for result in failed
        )
    return evaluation


def _validate_v2_scene_order_and_continuity(
    plan: SceneBeatPlanV2,
    bible: StoryBibleV2,
) -> None:
    """Validate V2-only order and Bible-backed continuity state references.

    The generic V1-compatible scene-beat coverage validator has no entity-state
    vocabulary and deliberately cannot infer it.  Keeping these checks here
    makes the V2 write contract explicit rather than silently accepting state
    labels that only happen to agree with each other.
    """

    issues: list[ValidationIssue] = []
    scenes_by_node: dict[str, list] = defaultdict(list)
    for scene in plan.scenes:
        scenes_by_node[scene.story_node_id].append(scene)
    for node_id in sorted(scenes_by_node):
        orders = sorted(scene.order for scene in scenes_by_node[node_id])
        if orders != list(range(1, len(orders) + 1)):
            issues.append(
                _issue(
                    "non_contiguous_scene_order",
                    f"scenes.{node_id}",
                    "dramatic scene order must be contiguous and start at 1 within a story node",
                )
            )

    for scene in plan.scenes:
        issues.extend(_continuity_state_issues(f"scenes.{scene.id}.entryState", scene.entry_state, bible))
        issues.extend(_continuity_state_issues(f"scenes.{scene.id}.exitState", scene.exit_state, bible))
    for beat in plan.beats:
        issues.extend(_continuity_state_issues(f"beats.{beat.id}.entryState", beat.entry_state, bible))
        issues.extend(_continuity_state_issues(f"beats.{beat.id}.exitState", beat.exit_state, bible))
    beats_by_scene: dict[str, list] = defaultdict(list)
    for beat in plan.beats:
        beats_by_scene[beat.scene_id].append(beat)
    for scene in plan.scenes:
        ordered_beats = sorted(beats_by_scene[scene.id], key=lambda beat: beat.order)
        if not _continuity_sequence_is_compatible(
            scene.entry_state,
            ordered_beats,
            scene.exit_state,
        ):
            issues.append(
                _issue(
                    "continuity_beat_sequence_mismatch",
                    f"scenes.{scene.id}",
                    "scene entry, ordered beat states, and scene exit must be compatible",
                )
            )
    if issues:
        raise DomainValidationError(issues)


def _continuity_state_issues(
    path_prefix: str,
    continuity_state,
    bible: StoryBibleV2,
) -> list[ValidationIssue]:
    allowed_states = _allowed_entity_states(bible)
    issues: list[ValidationIssue] = []
    for index, state in enumerate(continuity_state.entity_states):
        known_states = allowed_states[state.entity_type].get(state.entity_id)
        state_path = f"{path_prefix}.entityStates.{index}"
        if known_states is None:
            issues.append(
                _issue(
                    "unknown_continuity_entity",
                    f"{state_path}.entityId",
                    "continuity state references an entity absent from the story bible",
                )
            )
        elif state.state not in known_states:
            issues.append(
                _issue(
                    "invalid_continuity_entity_state",
                    f"{state_path}.state",
                    "continuity state is not allowed by the story bible",
                )
            )
    return issues


def _allowed_entity_states(
    bible: StoryBibleV2,
) -> dict[EntityType, dict[str, set[str]]]:
    return {
        EntityType.CHARACTER: {
            entity.id: set(entity.allowed_states) for entity in bible.characters
        },
        EntityType.LOCATION: {
            entity.id: set(entity.allowed_states) for entity in bible.locations
        },
        EntityType.PROP: {
            entity.id: set(entity.allowed_states) for entity in bible.props
        },
    }


def _validate_v2_dialogue_cues(
    plan: SceneBeatPlanV2,
    bible: StoryBibleV2,
    *,
    timing_profile: DialogueTimingProfile | None = None,
) -> None:
    """Stage-local cue checks that do not require a storyboard schedule."""

    issues: list[ValidationIssue] = []
    beats_by_id = {beat.id: beat for beat in plan.beats}
    character_ids = {character.id for character in bible.characters}
    duplicate_ids = _duplicates(cue.id for cue in plan.dialogue_cues)
    for cue_id in sorted(duplicate_ids):
        issues.append(_issue("duplicate_dialogue_cue_id", "dialogueCues", f"duplicate dialogue cue id: {cue_id}"))
    cues_by_beat: dict[str, list[DialogueCue]] = defaultdict(list)
    timing_profile = timing_profile or default_dialogue_timing_profile()
    for cue in plan.dialogue_cues:
        cues_by_beat[cue.beat_id].append(cue)
        if cue.beat_id not in beats_by_id:
            issues.append(_issue("unknown_dialogue_cue_beat", f"dialogueCues.{cue.id}.beatId", f"unknown beat: {cue.beat_id}"))
        if cue.speaker_id is not None and cue.speaker_id not in character_ids:
            issues.append(_issue("unknown_dialogue_speaker", f"dialogueCues.{cue.id}.speakerId", f"unknown character: {cue.speaker_id}"))
        minimum = timing_profile.estimate_duration_units(cue)
        if minimum is None or cue.estimated_duration_units < minimum:
            issues.append(
                _issue(
                    "dialogue_duration_underestimated",
                    f"dialogueCues.{cue.id}.estimatedDurationUnits",
                    "dialogue duration must meet the versioned language/delivery minimum",
                )
            )
    for beat_id in sorted(cues_by_beat):
        orders = sorted(cue.order for cue in cues_by_beat[beat_id])
        if orders != list(range(1, len(orders) + 1)):
            issues.append(
                _issue(
                    "non_contiguous_dialogue_cue_order",
                    f"dialogueCues.{beat_id}",
                    "dialogue cue order must be contiguous and start at 1 within a beat",
                )
            )

    scene_budget_by_id = {
        scene.id: scene.duration_budget_units for scene in plan.scenes
    }
    cue_duration_by_scene: dict[str, int] = defaultdict(int)
    for cue in plan.dialogue_cues:
        beat = beats_by_id.get(cue.beat_id)
        if beat is not None:
            cue_duration_by_scene[beat.scene_id] += cue.estimated_duration_units
    for scene_id, cue_duration in sorted(cue_duration_by_scene.items()):
        budget = scene_budget_by_id.get(scene_id)
        if budget is not None and cue_duration > budget:
            issues.append(
                _issue(
                    "dialogue_scene_budget_exceeded",
                    f"scenes.{scene_id}.durationBudgetUnits",
                    f"dialogue requires {cue_duration} units but scene budget is {budget}",
                )
            )
    if issues:
        raise DomainValidationError(issues)


def _validate_v2_scene_timing_allocation(
    plan: SceneBeatPlanV2,
    graph: StoryGraphV2,
    brief: ProjectBrief,
) -> None:
    """Keep manual canonical edits inside the generation-time path cap."""

    allocation = plan_scene_timing_allocation(graph=graph, brief=brief)
    budget_by_node: dict[str, int] = defaultdict(int)
    for scene in plan.scenes:
        budget_by_node[scene.story_node_id] += scene.duration_budget_units
    issues = [
        _issue(
            "scene_node_budget_exceeded",
            f"scenes.{node_id}.durationBudgetUnits",
            "dramatic-scene budgets exceed the versioned Story Graph node cap",
        )
        for node_id, actual in sorted(budget_by_node.items())
        if actual > allocation.node_duration_budget(node_id)
    ]
    if issues:
        raise DomainValidationError(issues)


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
        cues_by_id = {cue.id: cue for cue in plan.dialogue_cues}
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
            record(
                f"shot.count.{scene.id}", count_is_valid, path=("scenes", scene.id), reason=count_reason
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
            continuity_states_are_available = (
                not _continuity_state_issues("", shot.entry_state, bible)
                and not _continuity_state_issues("", shot.exit_state, bible)
            )
            record(
                f"continuity.entity_state.available.shot.{shot.id}",
                continuity_states_are_available,
                path=("shots", shot.id),
                reason="shot continuity states must reference Bible entities and allowed states",
            )

        cues_by_beat: dict[str, list] = defaultdict(list)
        for cue in plan.dialogue_cues:
            cues_by_beat[cue.beat_id].append(cue)
        for beat_id in sorted(cues_by_beat):
            beat_cues = sorted(cues_by_beat[beat_id], key=lambda item: item.order)
            record(
                f"dialogue_cue.ownership.{beat_id}", beat_id in beats_by_id,
                path=("dialogueCues", beat_id), reason="dialogue cues must be owned by a known beat",
            )
            record(
                f"dialogue_cue.order.{beat_id}",
                [cue.order for cue in beat_cues] == list(range(1, len(beat_cues) + 1)),
                path=("dialogueCues", beat_id),
                reason="dialogue cue order must be contiguous and start at 1 within its beat",
            )
            for cue in beat_cues:
                speaker_is_valid = cue.voice_over is not None or cue.speaker_id in character_ids
                record(
                    f"dialogue_cue.speaker.{cue.id}", speaker_is_valid,
                    path=("dialogueCues", cue.id, "speakerId"),
                    reason="a dialogue speaker must be a story-bible character; voice-over is explicit",
                )

        references_by_cue: dict[str, list] = defaultdict(list)
        for shot in storyboard.shots:
            for cue_id in shot.cue_ids:
                references_by_cue[cue_id].append(shot)
        for shot in sorted(storyboard.shots, key=lambda item: item.id):
            record(
                f"dialogue_cue.reference_unique.{shot.id}",
                len(shot.cue_ids) == len(set(shot.cue_ids)),
                path=("shots", shot.id, "cueIds"),
                reason="a shot must not schedule the same dialogue cue more than once",
            )
            references_are_known = all(cue_id in cues_by_id for cue_id in shot.cue_ids)
            record(
                f"dialogue_cue.reference.{shot.id}", references_are_known,
                path=("shots", shot.id, "cueIds"), reason="shots may reference only canonical dialogue cue IDs",
            )
            known_cues = [cues_by_id[cue_id] for cue_id in shot.cue_ids if cue_id in cues_by_id]
            same_scene = all(
                cue.beat_id in beats_by_id and beats_by_id[cue.beat_id].scene_id == shot.scene_id
                for cue in known_cues
            )
            record(
                f"dialogue_cue.scene_reference.{shot.id}", same_scene,
                path=("shots", shot.id, "cueIds"), reason="a shot can schedule only dialogue from its own scene",
            )
            key_by_cue = {
                cue.id: (beats_by_id[cue.beat_id].order, cue.order)
                for cue in known_cues if cue.beat_id in beats_by_id
            }
            record(
                f"dialogue_cue.reference_order.{shot.id}",
                [key_by_cue[cue.id] for cue in known_cues if cue.id in key_by_cue]
                == sorted(key_by_cue[cue.id] for cue in known_cues if cue.id in key_by_cue),
                path=("shots", shot.id, "cueIds"), reason="cue IDs must retain beat/cue order within a shot",
            )
            total_cue_duration = sum(cue.estimated_duration_units for cue in known_cues)
            record(
                f"dialogue_cue.shot_fit.{shot.id}", total_cue_duration <= shot.duration_units,
                path=("shots", shot.id, "cueIds"), reason="scheduled dialogue estimates must fit the shot duration",
            )

        linked_pairs = {
            (link.shot_id, link.beat_id)
            for link in storyboard.shot_beat_links
        }
        for cue in sorted(plan.dialogue_cues, key=lambda item: item.id):
            scheduled_shots = references_by_cue[cue.id]
            record(
                f"dialogue_cue.scheduled.{cue.id}", bool(scheduled_shots),
                path=("dialogueCues", cue.id), reason="every canonical dialogue cue must be scheduled by at least one shot",
            )
            record(
                f"dialogue_cue.schedule_cardinality.{cue.id}",
                len(scheduled_shots) == 1,
                path=("dialogueCues", cue.id),
                reason="a canonical dialogue cue must be scheduled by exactly one shot",
            )
            record(
                f"dialogue_cue.beat_coverage.{cue.id}",
                cue.beat_id in beats_by_id
                and all((shot.id, cue.beat_id) in linked_pairs for shot in scheduled_shots),
                path=("dialogueCues", cue.id),
                reason="the shot scheduling a cue must cover the cue's owning beat",
            )
            scheduled_duration = sum(shot.duration_units for shot in scheduled_shots)
            record(
                f"dialogue_cue.total_fit.{cue.id}", cue.estimated_duration_units <= scheduled_duration,
                path=("dialogueCues", cue.id), reason="a cue estimate must fit its scheduled shot duration",
            )
            if timing_profile is None:
                profile_match: bool | None = None
                profile_reason = "dialogue-fit requires an explicit versioned timing profile"
            else:
                expected = timing_profile.estimate_duration_units(cue)
                profile_match = (
                    expected is not None
                    and cue.estimated_duration_units >= expected
                )
                profile_reason = (
                    "cue estimate must not understate its versioned "
                    "language/delivery timing-profile minimum"
                )
            record(
                f"dialogue_cue.profile_fit.{cue.id}", profile_match,
                path=("dialogueCues", cue.id, "estimatedDurationUnits"), reason=profile_reason,
            )

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

        for scene in sorted(plan.scenes, key=lambda item: item.id):
            scene_beats = sorted(beats_by_scene[scene.id], key=lambda item: item.order)
            scene_shots = sorted(shots_by_scene[scene.id], key=lambda item: item.order)
            scene_continuity_states_are_available = (
                not _continuity_state_issues("", scene.entry_state, bible)
                and not _continuity_state_issues("", scene.exit_state, bible)
            )
            record(
                f"continuity.entity_state.available.scene.{scene.id}",
                scene_continuity_states_are_available,
                path=("scenes", scene.id),
                reason="scene continuity states must reference Bible entities and allowed states",
            )
            record(
                f"continuity.entity_state.unique.scene.{scene.id}",
                _continuity_entity_states_are_unique(scene.entry_state)
                and _continuity_entity_states_are_unique(scene.exit_state),
                path=("scenes", scene.id),
                reason="scene continuity states must not repeat or conflict on an entity",
            )
            for shot in scene_shots:
                record(
                    f"continuity.entity_state.unique.shot.{shot.id}",
                    _continuity_entity_states_are_unique(shot.entry_state)
                    and _continuity_entity_states_are_unique(shot.exit_state),
                    path=("shots", shot.id),
                    reason="shot continuity states must not repeat or conflict on an entity",
                )
            continuity_ok = _continuity_sequence_is_compatible(scene.entry_state, scene_shots, scene.exit_state)
            record(
                f"continuity.shot_sequence.{scene.id}", continuity_ok,
                path=("scenes", scene.id),
                reason="scene and adjacent shot entry/exit states must be compatible",
            )
            beat_continuity_ok = _continuity_sequence_is_compatible(
                scene.entry_state,
                scene_beats,
                scene.exit_state,
            )
            record(
                f"continuity.beat_sequence.{scene.id}", beat_continuity_ok,
                path=("scenes", scene.id),
                reason="scene and ordered beat entry/exit states must be compatible",
            )

        for beat in sorted(plan.beats, key=lambda item: item.id):
            beat_continuity_states_are_available = (
                not _continuity_state_issues("", beat.entry_state, bible)
                and not _continuity_state_issues("", beat.exit_state, bible)
            )
            record(
                f"continuity.entity_state.available.beat.{beat.id}",
                beat_continuity_states_are_available,
                path=("beats", beat.id),
                reason="beat continuity states must reference Bible entities and allowed states",
            )

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


def _continuity_sequence_is_compatible(entry_state, shots, exit_state) -> bool:
    prior = entry_state
    for shot in shots:
        if not _continuity_states_are_compatible(prior, shot.entry_state):
            return False
        prior = shot.exit_state
    return _continuity_states_are_compatible(prior, exit_state)


def _continuity_states_are_compatible(left, right) -> bool:
    if not _continuity_entity_states_are_unique(left) or not _continuity_entity_states_are_unique(right):
        return False
    left_entities = {(state.entity_type, state.entity_id): state.state for state in left.entity_states}
    right_entities = {(state.entity_type, state.entity_id): state.state for state in right.entity_states}
    for key in set(left_entities) & set(right_entities):
        if left_entities[key] != right_entities[key]:
            return False
    for key in set(left.facts) & set(right.facts):
        if left.facts[key] != right.facts[key]:
            return False
    for field in ("screen_direction", "lighting", "sound"):
        left_value = getattr(left, field)
        right_value = getattr(right, field)
        if left_value is not None and right_value is not None and left_value != right_value:
            return False
    return True


def _continuity_entity_states_are_unique(state) -> bool:
    keys = [(item.entity_type, item.entity_id) for item in state.entity_states]
    return len(keys) == len(set(keys))
