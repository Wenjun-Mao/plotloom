import { expect, it } from "vitest";
import { demoProject } from "../src/demo";
import { graphEntityKey, graphFocusKey, graphIssueTarget } from "../src/graph-editor";
import { bypassUnavailableReason } from "../src/features/graph/deletionEligibility";
import { graphDraftFixture } from "./graph-workbench-fixture";

it("binds current canonical validation paths to stable identities", () => {
  const graph = demoProject.storyGraph;
  const target = graphIssueTarget(graph, { code: "TITLE", path: "nodes.0.title", message: "missing" })!;
  expect(graphEntityKey(target.entity)).toBe(`graph-node:${graph.nodes[0].id}`);
  expect(graphFocusKey(target.entity, target.field)).toBe(`graph:node:${graph.nodes[0].id}:title`);
  expect(graphIssueTarget(graph, { code: "ENDPOINT", path: `edges.${graph.edges[0].id}.targetNodeId`, message: "missing" })?.entity).toEqual({ kind: "edge", id: graph.edges[0].id });
});
it("does not offer bypass when any input or continuation cannot be preserved", () => {
  const draft = graphDraftFixture();
  expect(bypassUnavailableReason(draft, "opening")).toContain("开场");
  draft.mapping.topology.nodes.push({ id: "step", kind: "scene" });
  draft.mapping.sections.push({ sectionId: "step", title: "step", summary: "step", ending: false, footageMode: "footage" });
  draft.mapping.topology.edges[0].targetNodeId = "step";
  draft.mapping.topology.edges.push({ id: "step-end", sourceNodeId: "step", targetNodeId: "ending", kind: "continuation", stateEffects: {}, entityStateEffects: [] });
  expect(bypassUnavailableReason(draft, "step")).toBeNull();
  draft.fieldBuffers["edge:step-end:stateEffects"] = '{"pending":';
  expect(bypassUnavailableReason(draft, "step")).toContain("未完成输入");
  draft.fieldBuffers = {}; draft.mapping.topology.edges[0].sourceNodeId = null;
  expect(bypassUnavailableReason(draft, "step")).toContain("明确的输入");
});
