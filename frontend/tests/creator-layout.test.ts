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
  expect(converging.every((edge, index) => index === 0 || edge.labelX - converging[index - 1].labelX >= 194)).toBe(true);
  expect(rowConnectionDefaults(draft, result.rows[1].nodes)).toEqual({ parent: "opening", target: "ending" });
  draft.mapping.topology.nodes.push({ id: "detached", kind: "scene" });
  expect(rowConnectionDefaults(draft, [...result.rows[1].nodes, "detached"])).toEqual({ parent: null, target: null });
});
it("keeps resizing inside the current desktop chart-space contract", () => {
  expect(inspectorBounds(1000)).toEqual({ min: 300, max: 450, automatic: 300 });
  expect(inspectorBounds(1400)).toEqual({ min: 300, max: 520, automatic: 380 });
});
