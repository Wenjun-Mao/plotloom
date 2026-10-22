import { expect, it } from "vitest";
import { blankStructure, mapsEqual } from "../src/pages/sourceStructureModel";
import type { SectionMap, SourceTopology } from "../src/types";

it("compares saved maps by content while preserving meaningful ordered prose", () => {
  const seed: SourceTopology = { plannerVersion: "story_graph_topology.v3", projectId: "fixture", startNodeId: "opening", topologyHash: "a".repeat(64), structuralParameters: {}, nodes: [{ id: "opening", kind: "start", footageMode: "footage" }], edges: [], joins: [] };
  const left: SectionMap = { ...blankStructure(seed), sections: [{ sectionId: "opening", title: "开场", summary: "先行动。", ending: false, footageMode: "footage" }] };
  const reordered: SectionMap = { ...left, sections: [{ footageMode: "footage", ending: false, summary: "先行动。", title: "开场", sectionId: "opening" }] };
  expect(mapsEqual(left, reordered)).toBe(true);
  expect(mapsEqual({ ...left, sections: [{ ...left.sections[0], summary: "另一种行动。" }] }, reordered)).toBe(false);
});
