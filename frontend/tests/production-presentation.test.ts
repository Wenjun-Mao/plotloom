import { expect, it } from "vitest";
import { splitPresentationSpans } from "../src/pages/ProductionPresentationReview";
import type { PresentationSpan } from "../src/types";

it("keeps an assigned draft when a different source fragment is split", () => {
  const physical: PresentationSpan = { start: 0, end: 5, role: "physical", rendering: "preserved action draft", reason: "author note" };
  const spans = [physical, { start: 5, end: 10, role: "unassigned" as const, rendering: "", reason: "" }];
  const result = splitPresentationSpans(spans, 7, 9);
  expect(result[0]).toBe(physical);
  expect(result.slice(1).map(span => [span.start, span.end])).toEqual([[5, 7], [7, 9], [9, 10]]);
  expect(result.slice(1).every(span => span.role === "unassigned")).toBe(true);
});

it("only resets fragments actually divided, including an assigned fragment", () => {
  const first: PresentationSpan = { start: 0, end: 5, role: "physical", rendering: "old whole-fragment description", reason: "" };
  const second: PresentationSpan = { start: 5, end: 10, role: "visible_text", rendering: "", reason: "" };
  expect(splitPresentationSpans([first, second], 1, 3)).toEqual([
    { start: 0, end: 1, role: "unassigned", rendering: "", reason: "" },
    { start: 1, end: 3, role: "unassigned", rendering: "", reason: "" },
    { start: 3, end: 5, role: "unassigned", rendering: "", reason: "" }, second,
  ]);
  expect(splitPresentationSpans([first, second], 0, 5)).toEqual([first, second]);
});
