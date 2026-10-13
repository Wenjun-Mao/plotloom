import { expect, it } from "vitest";
import { humanReviewLabel } from "../src/human-review-attribution";

it("shows known manual names and explicitly unnamed creator actions without inventing an actor", () => {
  expect(humanReviewLabel({ reviewer: "实际署名" })).toBe("实际署名");
  expect(humanReviewLabel({ reviewer: "", attribution: { kind: "unnamed_creator" } })).toBe("创作者确认（未署名）");
  expect(humanReviewLabel({ reviewer: "" })).toBe("署名信息待核实");
});
