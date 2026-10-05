import { expect, it } from "vitest";
import { mapsEqual } from "../src/pages/sourceStructureModel";
import type { SectionMap } from "../src/types";

it("compares saved maps by content while preserving meaningful ordered prose", () => {
  const left: SectionMap = { sections: [{ sectionId: "opening", title: "开场", summary: "先行动。", ending: false }], choice: null };
  const reordered: SectionMap = { choice: null, sections: [{ ending: false, summary: "先行动。", title: "开场", sectionId: "opening" }], choices: [], joinReconciliations: {}, topology: null };
  expect(mapsEqual(left, reordered)).toBe(true);
  expect(mapsEqual({ ...left, sections: [{ ...left.sections[0], summary: "另一种行动。" }] }, reordered)).toBe(false);
});
