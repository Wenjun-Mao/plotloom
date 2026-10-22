import { expect, it } from "vitest";
import { formatUiTimestamp } from "../src/ui-time";

it.each(["2026-10-08T05:06:07", "2026-10-08T17:06:07"])("uses Chinese 24-hour local display for %s", value => {
  const formatted = formatUiTimestamp(value);
  expect(formatted).toBe(new Date(value).toLocaleString("zh-CN", { hour12: false }));
  expect(formatted).toContain(value.slice(11));
  expect(formatted).not.toMatch(/AM|PM/);
});
