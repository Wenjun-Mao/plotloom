import { expect, type Locator } from "@playwright/test";

/** Required marks share the label's inline baseline, not its line-box top. */
export async function expectInlineRequiredMark(label: Locator) {
  const mark = label.locator("span[aria-hidden='true']");
  await expect(mark).toHaveCSS("display", "inline");
  await expect(mark).toHaveCSS("vertical-align", "baseline");
  const labelBox = await label.boundingBox();
  const markBox = await mark.boundingBox();
  expect(labelBox).not.toBeNull();
  expect(markBox).not.toBeNull();
  // Font ascent/leading differ across platforms. The inline text box must
  // still fit on the label's line and follow its text, without wrapping.
  expect(markBox!.y).toBeGreaterThanOrEqual(labelBox!.y);
  expect(markBox!.y + markBox!.height).toBeLessThanOrEqual(labelBox!.y + labelBox!.height);
  expect(markBox!.x).toBeGreaterThan(labelBox!.x);
}
