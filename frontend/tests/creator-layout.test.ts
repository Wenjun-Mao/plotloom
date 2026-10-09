import { expect, it } from "vitest";
import { creatorLayout, rowConnectionDefaults } from "../src/features/graph/creatorLayout";
import { inspectorBounds } from "../src/features/graph/useCreatorGeometry";
import { graphDraftFixture } from "./graph-workbench-fixture";
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
