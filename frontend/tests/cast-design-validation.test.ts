import { expect, it } from "vitest";
import { hasValidCastDesign } from "../src/pages/cast-design-validation";

it("rejects missing, malformed and marker-only descriptions in any character", () => {
  const valid = { persona: { personality: ["", "审慎（推断）"], appearance: "深蓝外套（推断）" } };
  expect(hasValidCastDesign([valid])).toBe(true);
  expect(hasValidCastDesign([])).toBe(false);
  expect(hasValidCastDesign([valid, {}])).toBe(false);
  for (const personality of [undefined, "审慎", [], [" "], ["（推断）"], ["审慎", null]]) {
    expect(hasValidCastDesign([{ persona: { personality, appearance: "外套" } }])).toBe(false);
  }
  for (const appearance of [undefined, 4, "", "  ", " (推断) "]) {
    expect(hasValidCastDesign([{ persona: { personality: ["审慎"], appearance } }])).toBe(false);
  }
});
