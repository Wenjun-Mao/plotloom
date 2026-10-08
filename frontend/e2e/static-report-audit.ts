import { expect, type Locator, type Page, type TestInfo } from "@playwright/test";

export const reportDesktopViewports = [[1700, 900], [1280, 768], [1280, 460]] as const;

/** Scroll the actual reading target; never substitute a full-page capture. */
export async function captureReportPoint(page: Page, target: Locator, testInfo: TestInfo, name: string) {
  await target.scrollIntoViewIfNeeded();
  if (!await page.getByRole("dialog").isVisible()) {
    const box = await target.boundingBox();
    const toolbarBottom = await page.locator(".topbar").evaluate(element => element.getBoundingClientRect().bottom);
    if (box && box.y < toolbarBottom + 8) {
      await page.evaluate(delta => window.scrollBy(0, -delta), Math.ceil(toolbarBottom + 8 - box.y));
    }
  }
  await expect(target).toBeInViewport();
  const width = page.viewportSize()!.width;
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`) });
}

/** Expose the owning frame before waiting for an embedded target's geometry. */
export async function captureReportFramePoint(page: Page, iframe: Locator, target: Locator, testInfo: TestInfo, name: string) {
  await iframe.scrollIntoViewIfNeeded();
  await expect(iframe).toBeInViewport();
  await captureReportPoint(page, target, testInfo, name);
}

/** A tall paragraph's last line must be read at its end, not at its centre. */
export async function captureReportParagraphEnd(page: Page, iframe: Locator, paragraph: Locator, testInfo: TestInfo, name: string) {
  await iframe.evaluate(element => element.scrollIntoView({ block: "end" }));
  const initialFrame = await iframe.boundingBox();
  const height = page.viewportSize()!.height;
  if (initialFrame && initialFrame.y + initialFrame.height > height - 8) {
    await page.evaluate(delta => window.scrollBy(0, delta), Math.ceil(initialFrame.y + initialFrame.height - height + 8));
  }
  await paragraph.evaluate(element => {
    element.scrollIntoView({ block: "end" });
    // Integral scrolling can leave a fractional edge outside the inner frame.
    // Read with a normal 8px margin; do not weaken exact visibility bounds.
    window.scrollBy(0, Math.max(0, Math.ceil(element.getBoundingClientRect().bottom - window.innerHeight + 8)));
  });
  const paragraphBounds = await paragraph.boundingBox();
  const frameBounds = await iframe.boundingBox();
  expect(paragraphBounds).not.toBeNull();
  expect(frameBounds).not.toBeNull();
  expect(paragraphBounds!.y + paragraphBounds!.height).toBeLessThanOrEqual(frameBounds!.y + frameBounds!.height);
  expect(paragraphBounds!.y + paragraphBounds!.height).toBeGreaterThan(frameBounds!.y);
  expect(paragraphBounds!.y + paragraphBounds!.height).toBeLessThanOrEqual(height);
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`) });
}

/** E22 report reading uses viewport captures, not full-page substitutes. */
export async function auditStaticReport(page: Page, panel: Locator, kind: "script" | "storyboard", testInfo: TestInfo) {
  const subject = kind === "script" ? "剧本" : "分镜";
  const summary = panel.getByText(`阅读原始${subject}报告（只读）`, { exact: true });
  const iframe = panel.locator("iframe");
  const frame = panel.frameLocator("iframe");
  const middle = kind === "script" ? "#sec-script" : "#sec-segments";
  for (const [width, height] of reportDesktopViewports) {
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
