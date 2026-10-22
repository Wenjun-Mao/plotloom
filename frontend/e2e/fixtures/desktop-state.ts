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

/** Action reachability is separate from the notice-only viewport above. */
export async function captureDesktopActions(page: Page, info: TestInfo, name: string,
  actions: readonly { name: string; locator: Locator; enabled: boolean }[]) {
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    for (const action of actions) {
      await action.locator.evaluate(element => element.scrollIntoView({
        block: "center", inline: "nearest", behavior: "instant",
      }));
      await expect(action.locator).toBeInViewport({ ratio: 1 });
      if (action.enabled) await expect(action.locator).toBeEnabled();
      else await expect(action.locator).toBeDisabled();
      const box = await action.locator.boundingBox();
      expect(box).not.toBeNull();
      const toolbarBottom = await page.locator(".topbar").evaluate(element => element.getBoundingClientRect().bottom);
      expect(box!.y).toBeGreaterThanOrEqual(Math.max(0, toolbarBottom));
      expect(box!.y + box!.height).toBeLessThanOrEqual(height);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: info.outputPath(`${name}-action-${action.name}-${width}x${height}.png`) });
    }
  }
}
