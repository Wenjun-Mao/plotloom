import type { Locator, Page, TestInfo } from "@playwright/test";
import { expect } from "../fixture";

/** One viewport slice around its named state owner; not an all-controls capture. */
export async function captureDesktopState(page: Page, info: TestInfo, name: string, anchor: Locator) {
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    await anchor.scrollIntoViewIfNeeded();
    await expect(anchor).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`${name}-${width}x${height}.png`) });
  }
}
