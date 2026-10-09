import type { Page, TestInfo } from "@playwright/test";
import { expect } from "../../fixture";

/** Inspect the actual aspect-consent form, including the shortest desktop. */
export async function inspectAspectChoiceLayout(page: Page, info: TestInfo) {
  const originalViewport = page.viewportSize();
  const notice = page.getByTestId("h3-aspect-preparation");
  const labels = notice.locator("label");
  const radios = notice.getByRole("radio");
  await expect(radios).toHaveCount(3);
  const sourceRead = page.getByTestId("h3-directions-review").getByRole("button", { name: "读取当前来源", exact: true });
  for (const size of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(size);
    await notice.scrollIntoViewIfNeeded();
    // Preserve the pre-fix pixels even if a geometry assertion fails.
    await page.screenshot({ path: info.outputPath(`h3-aspect-options-${size.width}x${size.height}.png`) });
    const bounds = await notice.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.y).toBeGreaterThanOrEqual(58);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(size.height);
    let previousBottom = 0;
    for (let index = 0; index < 3; index += 1) {
      const label = await labels.nth(index).boundingBox();
      const radio = await radios.nth(index).boundingBox();
      expect(label!.width).toBeGreaterThan(400);
      expect(label!.y).toBeGreaterThanOrEqual(previousBottom);
      expect(label!.x).toBeGreaterThanOrEqual(bounds!.x);
      expect(label!.x + label!.width).toBeLessThanOrEqual(bounds!.x + bounds!.width);
      expect(radio!.width).toBeGreaterThanOrEqual(16);
      expect(radio!.height).toBeGreaterThanOrEqual(16);
      previousBottom = label!.y + label!.height;
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
    for (const index of [1, 2, 0]) {
      await radios.nth(index).check();
      await expect(radios.nth(index)).toBeChecked();
      if (index === 0) await expect(sourceRead).toBeDisabled();
      else await expect(sourceRead).toBeEnabled();
    }
  }
  if (originalViewport) await page.setViewportSize(originalViewport);
}
