import { expect, type Locator, type Page, type TestInfo } from "@playwright/test";

/** E22 report reading uses viewport captures, not full-page substitutes. */
export async function auditStaticReport(page: Page, panel: Locator, kind: "script" | "storyboard", testInfo: TestInfo) {
  const subject = kind === "script" ? "剧本" : "分镜";
  const summary = panel.getByText(`阅读原始${subject}报告（只读）`, { exact: true });
  const iframe = panel.locator("iframe");
  const frame = panel.frameLocator("iframe");
  const middle = kind === "script" ? "#sec-script" : "#sec-segments";
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    await summary.scrollIntoViewIfNeeded();
    await expect(summary).toBeInViewport();
    await page.screenshot({ path: testInfo.outputPath(`${kind}-disclosure-${width}x${height}.png`) });
    await iframe.scrollIntoViewIfNeeded();
    await frame.locator("body").evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: testInfo.outputPath(`${kind}-top-${width}x${height}.png`) });
    await frame.locator(middle).scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath(`${kind}-middle-${width}x${height}.png`) });
    await frame.locator("#sec-gates").scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath(`${kind}-bottom-${width}x${height}.png`) });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    expect(await frame.locator("html").evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
  }
}
