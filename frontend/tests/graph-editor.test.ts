import { describe, expect, it } from "vitest";
import type { StoryEdge, StoryGraph } from "../src/types";
import {
  addEdgeWithContractSync,
  addNode,
  graphEntityKey,
  graphFocusKey,
  graphIssueTarget,
  issueFocusTarget,
  parseGraphEntityIdentity,
  relationshipImpactForEdgeRemoval,
  relationshipImpactForEdgeReconnect,
  reconnectEdgeWithContractSync,
  relationshipImpactForNodeKindChange,
  relationshipImpactForNodeRemoval,
  relationshipImpactGroups,
  retainedSceneReferencesForNode,
  removeEdgeWithCascade,
  removeNodeWithCascade,
  setStartNode,
  stateEffectRowsToValue,
  stateEffectsToRows,
} from "../src/graph-editor";

const graph: StoryGraph = {
  startNodeId: "start",
  nodes: [
    { id: "start", kind: "start", title: "Start", summary: "Open" },
    { id: "left", kind: "scene", title: "Left", summary: "Left path" },
    { id: "right", kind: "scene", title: "Right", summary: "Right path" },
    { id: "join", kind: "join", title: "Join", summary: "Converge" },
  ],
  edges: [
    { id: "start-left", sourceNodeId: "start", targetNodeId: "left", kind: "continuation", choiceText: null, stateEffects: {} },
    { id: "left-join", sourceNodeId: "left", targetNodeId: "join", kind: "choice", choiceText: "Follow left", stateEffects: { trust: 1 } },
    { id: "right-join", sourceNodeId: "right", targetNodeId: "join", kind: "choice", choiceText: "Follow right", stateEffects: {} },
  ],
  joinContracts: [{
    id: "join-contract", joinNodeId: "join", incomingNodeIds: ["left", "right"],
    requiredStateKeys: ["trust"], allowedDifferences: ["route"], reconciliation: "Merge memories", notes: "Required convergence",
  }],
};

describe("graph editor pure contract helpers", () => {
  it("uses namespaced URL identities while still reading old bare node links", () => {
    expect(parseGraphEntityIdentity("left", graph)).toEqual({ kind: "node", id: "left" });
    expect(parseGraphEntityIdentity("graph-edge:left-join", graph)).toEqual({ kind: "edge", id: "left-join" });
    expect(parseGraphEntityIdentity("graph-contract:join-contract", graph)).toEqual({ kind: "contract", id: "join-contract" });
    expect(parseGraphEntityIdentity("graph-node:missing", graph)).toBeUndefined();
    expect(graphEntityKey({ kind: "node", id: "left" })).toBe("graph-node:left");
  });

  it("adds stable nodes and moves the sole start role transactionally without mutation", () => {
    const added = addNode(graph, { id: "ending", kind: "ending", title: "End", summary: "Close" });
    const switched = setStartNode(added, "left");
    expect(graph.nodes).toHaveLength(4);
    expect(switched.startNodeId).toBe("left");
    expect(switched.nodes.filter((node) => node.kind === "start").map((node) => node.id)).toEqual(["left"]);
    expect(switched.nodes.find((node) => node.id === "start")?.kind).toBe("scene");
    const malformed = { ...graph, nodes: graph.nodes.map((node) => node.id === "right" ? { ...node, kind: "start" as const } : node) };
    expect(setStartNode(malformed, "left").nodes.filter((node) => node.kind === "start").map((node) => node.id)).toEqual(["left"]);
  });

  it("reports and applies edge cascades deterministically", () => {
    const impact = relationshipImpactForEdgeRemoval(graph, "right-join");
    expect(impact.removedEdgeIds).toEqual(["right-join"]);
    expect(impact.removedContractIds).toEqual(["join-contract"]);
    const removed = removeEdgeWithCascade(graph, "right-join");
    expect(removed.edges.map((edge) => edge.id)).not.toContain("right-join");
    expect(removed.joinContracts).toEqual([]);
    expect(graph.joinContracts).toHaveLength(1);
  });

  it("keeps an existing join contract synchronized when an incoming edge is added", () => {
    const withThird = addNode(graph, { id: "third", kind: "scene", title: "Third", summary: "Third path" });
    const edge: StoryEdge = { id: "third-join", sourceNodeId: "third", targetNodeId: "join", kind: "continuation", choiceText: null, stateEffects: {} };
    const synced = addEdgeWithContractSync(withThird, edge);
    expect(synced.joinContracts[0].incomingNodeIds).toEqual(["left", "right", "third"]);
    expect(withThird.joinContracts[0].incomingNodeIds).toEqual(["left", "right"]);
  });

  it("reconnects a stable edge only through an explicit join-contract impact", () => {
    const impact = relationshipImpactForEdgeReconnect(graph, "right-join", { sourceNodeId: "start", targetNodeId: "join" });
    expect(impact).toMatchObject({ affectedContractIds: ["join-contract"], updatedContractIds: ["join-contract"] });
    const reconnected = reconnectEdgeWithContractSync(graph, "right-join", { sourceNodeId: "start", targetNodeId: "join" });
    expect(reconnected.edges.find((edge) => edge.id === "right-join")).toMatchObject({ id: "right-join", sourceNodeId: "start", targetNodeId: "join" });
    expect(reconnected.joinContracts[0].incomingNodeIds).toEqual(["left", "start"]);
    expect(graph.edges.find((edge) => edge.id === "right-join")?.sourceNodeId).toBe("right");
  });

  it("computes node cascades and refuses to delete the sole start node", () => {
    const impact = relationshipImpactForNodeRemoval(graph, "right");
    expect(impact.removedEdgeIds).toEqual(["right-join"]);
    expect(impact.removedContractIds).toEqual(["join-contract"]);
    expect(relationshipImpactGroups(impact)).toEqual([
      { key: "removed-nodes", label: "将删除节点", ids: ["right"] },
      { key: "removed-edges", label: "将删除关系", ids: ["right-join"] },
      { key: "affected-contracts", label: "受影响汇合合同", ids: ["join-contract"] },
      { key: "removed-contracts", label: "将删除汇合合同", ids: ["join-contract"] },
    ]);
    expect(removeNodeWithCascade(graph, "right").nodes.map((node) => node.id)).not.toContain("right");
    expect(() => removeNodeWithCascade(graph, "start")).toThrow("select another start node");
  });

  it("keeps downstream scene references visible rather than cascading them", () => {
    expect(retainedSceneReferencesForNode([
      { id: "scene_rescue", storyNodeId: "right", title: "Rescue" },
      { id: "scene_start", storyNodeId: "start", title: "Start" },
      { id: "scene_right_b", storyNodeId: "right", title: "Second rescue" },
    ], "right")).toEqual([
      { sceneId: "scene_rescue", title: "Rescue", path: "scene_beats.scenes.scene_rescue.storyNodeId" },
      { sceneId: "scene_right_b", title: "Second rescue", path: "scene_beats.scenes.scene_right_b.storyNodeId" },
    ]);
  });

  it("requires an explicit relationship decision before turning a join into a non-join", () => {
    expect(relationshipImpactForNodeKindChange(graph, "join", "scene")).toMatchObject({
      affectedContractIds: ["join-contract"],
      removedContractIds: ["join-contract"],
    });
    expect(relationshipImpactForNodeKindChange(graph, "left", "join").removedContractIds).toEqual([]);
  });

  it("round-trips typed state effects and rejects bad editor rows", () => {
    const rows = stateEffectsToRows({ title: "awake", count: 3, ready: true, closed: null, data: { scene: 2 } });
    expect(stateEffectRowsToValue(rows)).toEqual({ value: { closed: null, count: 3, data: { scene: 2 }, ready: true, title: "awake" }, errors: [] });
    const invalid = stateEffectRowsToValue([{ key: "", kind: "string", value: "x" }, { key: "mode", kind: "json", value: "not json" }, { key: "mode", kind: "number", value: "2" }]);
    expect(invalid.errors.map((error) => error.code)).toEqual(["blank_key", "invalid_json", "duplicate_key"]);
  });

  it("maps backend issue paths to exact graph entities", () => {
    expect(issueFocusTarget(graph, [{ code: "node", path: "nodes.left.title", message: "required" }])).toEqual({ kind: "node", id: "left" });
    expect(issueFocusTarget(graph, [{ code: "edge", path: "edges.1.choiceText", message: "required" }])).toEqual({ kind: "edge", id: "left-join" });
    expect(issueFocusTarget(graph, [{ code: "join", path: "joinContracts.join-contract.notes", message: "required" }])).toEqual({ kind: "contract", id: "join-contract" });
    expect(graphIssueTarget(graph, { code: "node", path: "nodes.1.title", message: "required" })).toEqual({ entity: { kind: "node", id: "left" }, field: "title" });
    expect(graphIssueTarget(graph, { code: "join", path: "joinContracts.0.requiredStateKeys.0", message: "required" })).toEqual({ entity: { kind: "contract", id: "join-contract" }, field: "requiredStateKeys" });
    expect(graphIssueTarget(graph, { code: "effect", path: "edges.left-join.stateEffects.trust", message: "invalid" })).toEqual({ entity: { kind: "edge", id: "left-join" }, field: "stateEffects.trust" });
    expect(graphFocusKey({ kind: "node", id: "left" }, "title")).toBe("graph:node:left:title");
  });
});
