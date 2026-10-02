import { expect, it } from "vitest";
import { sourceSecondsToMilliseconds } from "../src/production-timing";

it.each([[2.5, 2500], [1.001, 1001], [0.001, 1], [8, 8000], [1e3, 1_000_000]])(
  "preserves exact decimal source seconds %s as %s integer milliseconds", (seconds, milliseconds) => {
    expect(sourceSecondsToMilliseconds(seconds)).toBe(milliseconds);
  },
);

it.each([1.0004, 0.0001, 1e-7, true, false, NaN, Infinity, -Infinity, 0, -1, "2.5", null, 1e20])(
  "refuses unrepresentable source seconds %s without rounding", (seconds) => {
    expect(sourceSecondsToMilliseconds(seconds)).toBeUndefined();
  },
);
