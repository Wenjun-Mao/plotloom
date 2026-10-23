import { expect, it } from "vitest";
import { CARD_HEIGHT, CARD_WIDTH, COLUMN_GAP, EDITABLE_EDGE_LABEL_MAX_HEIGHT, creatorLayout, graphTopologyLayout, rowConnectionDefaults } from "../src/features/graph/creatorLayout";
import { inspectorBounds } from "../src/features/graph/useCreatorGeometry";
import { graphDraftFixture } from "./graph-workbench-fixture";

type LayoutTopology = { startNodeId: string; nodes: Array<{ id: string }>; edges: Array<{ id: string; sourceNodeId: string; targetNodeId: string }> };
it("reserves the row insertion lane below an editable label including its focus outline", () => {
  const layout = creatorLayout(graphDraftFixture(), 700);
  const source = layout.nodes.find(node => node.id === "opening")!;
  const label = layout.edges[0];
  expect(label.labelY + EDITABLE_EDGE_LABEL_MAX_HEIGHT / 2 + 5).toBeLessThan(source.y + CARD_HEIGHT + 106);
});
const topology = (nodes: string[], edges: Array<[string, string, string]>): LayoutTopology => ({
  startNodeId: "start",
  nodes: nodes.map(id => ({ id })),
  edges: edges.map(([id, sourceNodeId, targetNodeId]) => ({ id, sourceNodeId, targetNodeId })),
});

it.each([
  { name: "chain", graph: topology(["ending", "start", "scene"], [["scene-ending", "scene", "ending"], ["start-scene", "start", "scene"]]), expected: { start: 0, scene: 1, ending: 2 } },
  { name: "split", graph: topology(["right", "start", "left"], [["start-left", "start", "left"], ["start-right", "start", "right"]]), expected: { start: 0, left: 1, right: 1 } },
  { name: "diamond", graph: topology(["join", "right", "start", "left"], [["left-join", "left", "join"], ["start-right", "start", "right"], ["right-join", "right", "join"], ["start-left", "start", "left"]]), expected: { start: 0, left: 1, right: 1, join: 2 } },
  { name: "unequal-depth join", graph: topology(["join", "deep", "right", "left", "middle", "start"], [
    ["left-join", "left", "join"], ["middle-deep", "middle", "deep"], ["start-skip", "start", "join"],
    ["deep-join", "deep", "join"], ["right-middle", "right", "middle"], ["start-right", "start", "right"], ["start-left", "start", "left"],
  ]), expected: { start: 0, left: 1, right: 1, middle: 2, deep: 3, join: 4 } },
])("shares downward topology ranks for a $name", ({ graph, expected }) => {
  const layout = graphTopologyLayout(graph, 0);
  const ranks = Object.fromEntries(layout.nodes.map(node => [node.id, node.rank]));
  expect(ranks).toEqual(expected);
  expect(new Set(layout.nodes.map(node => node.id))).toEqual(new Set(graph.nodes.map(node => node.id)));
  expect(layout.edges.map(item => item.edge.id)).toEqual(graph.edges.map(edge => edge.id));
  for (const node of layout.nodes) expect(node.y).toBe(32 + node.rank * 256);
});

it("reserves distinct in-bounds label lanes for converging and skip edges", () => {
  const graph = topology(["join", "branch-3", "start", "branch-1", "branch-4", "branch-2"], [
    ["skip", "start", "join"], ["branch-4-join", "branch-4", "join"], ["start-branch-4", "start", "branch-4"],
    ["branch-2-join", "branch-2", "join"], ["start-branch-1", "start", "branch-1"], ["branch-1-join", "branch-1", "join"],
    ["start-branch-3", "start", "branch-3"], ["branch-3-join", "branch-3", "join"], ["start-branch-2", "start", "branch-2"],
  ]);
  const layout = graphTopologyLayout(graph, 0);
  const labels = layout.edges.filter(item => item.edge.targetNodeId === "join");
  const labelXs = labels.map(item => item.labelX).sort((left, right) => left - right);
  expect(new Set(labelXs).size).toBe(labels.length);
  expect(labelXs.every(x => x - 101 > 0 && x + 101 < layout.width)).toBe(true);
  expect(labelXs.every((x, index) => index === 0 || x - labelXs[index - 1] >= CARD_WIDTH + COLUMN_GAP)).toBe(true);
  expect(labels.map(item => item.labelY)).toEqual(Array(labels.length).fill(layout.nodes.find(node => node.id === "join")!.y - 68));
  expect(layout.edges.find(item => item.edge.id === "skip")?.path).toContain(" L ");
  expect(layout.height).toBeGreaterThan(layout.nodes.find(node => node.id === "join")!.y + CARD_HEIGHT);
});
it("keeps six siblings on one row and routes skip edges outside cards", () => {
  const draft = graphDraftFixture();
  draft.mapping.topology.nodes[0].kind = "decision";
  draft.mapping.topology.nodes.splice(1, 0, ...Array.from({ length: 6 }, (_, index) => ({ id: `branch-${index}`, kind: "scene" as const })));
  draft.mapping.topology.edges = Array.from({ length: 6 }, (_, index) => ({ id: `in-${index}`, sourceNodeId: "opening", targetNodeId: `branch-${index}`, kind: "choice" as const, stateEffects: {}, entityStateEffects: [] }));
  draft.mapping.topology.edges.push(...Array.from({ length: 6 }, (_, index) => ({ id: `out-${index}`, sourceNodeId: `branch-${index}`, targetNodeId: "ending", kind: "continuation" as const, stateEffects: {}, entityStateEffects: [] })));
  draft.mapping.topology.edges.push({ id: "skip", sourceNodeId: "opening", targetNodeId: "ending", kind: "choice", stateEffects: {}, entityStateEffects: [] });
  const result = creatorLayout(draft, 600);
  expect(result.rows[1].nodes).toHaveLength(6); expect(new Set(result.nodes.filter(node => node.id.startsWith("branch")).map(node => node.y)).size).toBe(1);
  expect(result.width).toBeGreaterThan(1400); expect(result.edges.find(edge => edge.edge.id === "skip")?.path).toContain(" L ");
  const converging = result.edges.filter(edge => edge.edge.targetNodeId === "ending");
  expect(new Set(converging.map(edge => `${edge.labelX}:${edge.labelY}`)).size).toBe(7);
  const labelPositions = converging.map(edge => edge.labelX).sort((a, b) => a - b);
  expect(labelPositions.every((x, index) => index === 0 || x - labelPositions[index - 1] >= 194)).toBe(true);
  expect(rowConnectionDefaults(draft, result.rows[1].nodes)).toEqual({ parent: "opening", target: "ending" });
  draft.mapping.topology.nodes.push({ id: "detached", kind: "scene" });
  expect(rowConnectionDefaults(draft, [...result.rows[1].nodes, "detached"])).toEqual({ parent: null, target: null });
});
it("orders split option labels by visible targets after an appended middle node", () => {
  const draft = graphDraftFixture();
  draft.mapping.topology.nodes = [
    { id: "opening", kind: "decision" }, { id: "east", kind: "ending" },
    { id: "west", kind: "ending" }, { id: "inserted", kind: "scene" },
  ];
  const edge = (id: string, sourceNodeId: string, targetNodeId: string, kind: "choice" | "continuation") => ({ id, sourceNodeId, targetNodeId, kind, stateEffects: {}, entityStateEffects: [] });
  draft.mapping.topology.edges = [edge("east-option", "opening", "inserted", "choice"), edge("west-option", "opening", "west", "choice"), edge("after", "inserted", "east", "continuation")];
  const result = creatorLayout(draft, 1000);
  const west = result.nodes.find(node => node.id === "west")!;
  const inserted = result.nodes.find(node => node.id === "inserted")!;
  expect(west.rank).toBe(inserted.rank);
  expect(west.x).toBeLessThan(inserted.x);
  expect(result.edges.find(item => item.edge.id === "west-option")!.labelX).toBeLessThan(result.edges.find(item => item.edge.id === "east-option")!.labelX);
  expect(result.edges.map(item => item.edge)).toEqual(draft.mapping.topology.edges);
});
it("keeps resizing inside the current desktop chart-space contract", () => {
  expect(inspectorBounds(1000)).toEqual({ min: 300, max: 450, automatic: 300 });
  expect(inspectorBounds(1400)).toEqual({ min: 300, max: 520, automatic: 380 });
});
