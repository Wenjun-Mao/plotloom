"""Deterministic V2 timeline derivation using integer authoring time units."""

from __future__ import annotations

from collections import defaultdict

from pydantic import ConfigDict, Field

from .canonical_schema import (
    SceneBeatPlanV2,
    StoryboardV2,
    StoryGraphV2,
    V2Model,
    V2StoryNodeKind,
)


class TimelineContractError(ValueError):
    """A stable semantic refusal for invalid timeline inputs."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


class Timecode(V2Model):
    model_config = V2Model.model_config | {"frozen": True}

    start_units: int = Field(ge=0)
    duration_units: int = Field(ge=0)

    @property
    def end_units(self) -> int:
        return self.start_units + self.duration_units


class SceneTimecode(V2Model):
    model_config = V2Model.model_config | {"frozen": True}

    scene_id: str
    story_node_id: str
    timecode: Timecode


class NodeTimecode(V2Model):
    model_config = V2Model.model_config | {"frozen": True}

    node_id: str
    timecode: Timecode


class PathTimecode(V2Model):
    model_config = V2Model.model_config | {"frozen": True}

    node_ids: tuple[str, ...]
    nodes: tuple[NodeTimecode, ...]
    scenes: tuple[SceneTimecode, ...]
    duration_units: int = Field(ge=0)


def _ordered_scene_shots(plan: SceneBeatPlanV2, storyboard: StoryboardV2) -> dict[str, list]:
    scene_ids = [scene.id for scene in plan.scenes]
    if len(scene_ids) != len(set(scene_ids)):
        raise TimelineContractError(
            "timeline.duplicate_scene_id", "dramatic scene IDs must be unique"
        )
    known_scene_ids = set(scene_ids)
    scenes_by_node: dict[str, list] = defaultdict(list)
    for scene in plan.scenes:
        scenes_by_node[scene.story_node_id].append(scene)
    for node_id, scenes in scenes_by_node.items():
        orders = sorted(scene.order for scene in scenes)
        if orders != list(range(1, len(scenes) + 1)):
            raise TimelineContractError(
                "timeline.scene_order",
                f"scene order for story node {node_id} must be contiguous from 1",
            )

    shot_ids = [shot.id for shot in storyboard.shots]
    if len(shot_ids) != len(set(shot_ids)):
        raise TimelineContractError(
            "timeline.duplicate_shot_id", "shot IDs must be unique"
        )
    shots_by_scene: dict[str, list] = defaultdict(list)
    for shot in storyboard.shots:
        if shot.scene_id not in known_scene_ids:
            raise TimelineContractError(
                "timeline.unknown_shot_scene", f"unknown shot scene: {shot.scene_id}"
            )
        shots_by_scene[shot.scene_id].append(shot)
    for scene in plan.scenes:
        shots = shots_by_scene.get(scene.id, [])
        if not shots:
            raise TimelineContractError(
                "timeline.scene_without_shots",
                f"dramatic scene {scene.id} has no shots",
            )
        shots.sort(key=lambda shot: shot.order)
        if [shot.order for shot in shots] != list(range(1, len(shots) + 1)):
            raise TimelineContractError(
                "timeline.shot_order",
                f"shot order for dramatic scene {scene.id} must be contiguous from 1",
            )
        duration = sum(shot.duration_units for shot in shots)
        if duration > scene.duration_budget_units:
            raise TimelineContractError(
                "timeline.duration_budget_exceeded",
                f"dramatic scene {scene.id} uses {duration} units but budget is {scene.duration_budget_units}",
            )
    return shots_by_scene


def derive_scene_timecodes(
    plan: SceneBeatPlanV2,
    storyboard: StoryboardV2,
) -> tuple[SceneTimecode, ...]:
    """Derive scene-local node timecodes in stable dramatic-scene order.

    A scene's start is local to its story node, because graph branches do not
    imply one global story order.  ``derive_path_timecode`` resolves a selected
    path into global starts without rounding floats or inventing positions.
    """

    shots_by_scene = _ordered_scene_shots(plan, storyboard)
    scenes_by_node: dict[str, list] = defaultdict(list)
    for scene in plan.scenes:
        scenes_by_node[scene.story_node_id].append(scene)

    result: list[SceneTimecode] = []
    for node_id in sorted(scenes_by_node):
        cursor = 0
        for scene in sorted(scenes_by_node[node_id], key=lambda item: item.order):
            duration = sum(shot.duration_units for shot in shots_by_scene[scene.id])
            result.append(
                SceneTimecode(
                    scene_id=scene.id,
                    story_node_id=node_id,
                    timecode=Timecode(start_units=cursor, duration_units=duration),
                )
            )
            cursor += duration
    return tuple(result)


def derive_node_timecodes(
    plan: SceneBeatPlanV2,
    storyboard: StoryboardV2,
) -> tuple[NodeTimecode, ...]:
    """Return stable node-local durations (start is always zero)."""

    scene_timecodes = derive_scene_timecodes(plan, storyboard)
    duration_by_node: dict[str, int] = defaultdict(int)
    for scene in scene_timecodes:
        duration_by_node[scene.story_node_id] += scene.timecode.duration_units
    return tuple(
        NodeTimecode(node_id=node_id, timecode=Timecode(start_units=0, duration_units=duration))
        for node_id, duration in sorted(duration_by_node.items())
    )


def derive_path_timecode(
    plan: SceneBeatPlanV2,
    storyboard: StoryboardV2,
    node_ids: tuple[str, ...] | list[str],
    *,
    graph: StoryGraphV2,
) -> PathTimecode:
    """Place one validated graph path on a global integer timeline."""

    requested_nodes = tuple(node_ids)
    if not requested_nodes:
        raise TimelineContractError(
            "timeline.empty_path", "a selected story path must not be empty"
        )
    if len(requested_nodes) != len(set(requested_nodes)):
        raise TimelineContractError(
            "timeline.repeated_path_node", "a DAG path cannot repeat a story node"
        )
    graph_node_ids = [node.id for node in graph.nodes]
    if len(graph_node_ids) != len(set(graph_node_ids)):
        raise TimelineContractError(
            "timeline.duplicate_graph_node_id", "story graph node IDs must be unique"
        )
    unknown = set(requested_nodes) - set(graph_node_ids)
    if unknown:
        raise TimelineContractError(
            "timeline.unknown_path_node",
            f"path references unknown story nodes: {', '.join(sorted(unknown))}",
        )
    if requested_nodes[0] != graph.start_node_id:
        raise TimelineContractError(
            "timeline.path_start_mismatch",
            "a selected path must begin at storyGraph.startNodeId",
        )
    nodes_by_id = {node.id: node for node in graph.nodes}
    if nodes_by_id[requested_nodes[-1]].kind != V2StoryNodeKind.ENDING:
        raise TimelineContractError(
            "timeline.path_not_ending",
            "a selected story path must end at an ENDING story node",
        )
    graph_edges = {(edge.source_node_id, edge.target_node_id) for edge in graph.edges}
    for source_id, target_id in zip(requested_nodes, requested_nodes[1:]):
        if (source_id, target_id) not in graph_edges:
            raise TimelineContractError(
                "timeline.non_edge_path_step",
                f"story path step {source_id} -> {target_id} is not a graph edge",
            )
    scene_timecodes = derive_scene_timecodes(plan, storyboard)
    scenes_by_node: dict[str, list[SceneTimecode]] = defaultdict(list)
    for scene in scene_timecodes:
        scenes_by_node[scene.story_node_id].append(scene)

    cursor = 0
    nodes: list[NodeTimecode] = []
    scenes: list[SceneTimecode] = []
    for node_id in requested_nodes:
        if node_id not in scenes_by_node:
            raise TimelineContractError(
                "timeline.path_node_without_scenes",
                f"path references node without dramatic scenes: {node_id}",
            )
        node_scenes = scenes_by_node[node_id]
        duration = sum(scene.timecode.duration_units for scene in node_scenes)
        nodes.append(NodeTimecode(node_id=node_id, timecode=Timecode(start_units=cursor, duration_units=duration)))
        for scene in node_scenes:
            scenes.append(
                SceneTimecode(
                    scene_id=scene.scene_id,
                    story_node_id=node_id,
                    timecode=Timecode(
                        start_units=cursor + scene.timecode.start_units,
                        duration_units=scene.timecode.duration_units,
                    ),
                )
            )
        cursor += duration
    return PathTimecode(
        node_ids=requested_nodes,
        nodes=tuple(nodes),
        scenes=tuple(scenes),
        duration_units=cursor,
    )
