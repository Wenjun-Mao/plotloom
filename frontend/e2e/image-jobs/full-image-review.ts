import type { Page, TestInfo } from "@playwright/test";
import { expect } from "../fixture";

/** Read-only zoom regression using retained fixtures, not generated-media acceptance. */
export async function inspectFullImageReview(page: Page, candidateId: string, info: TestInfo) {
  const candidate = page.getByTestId(`keep-candidate-${candidateId}`);
  const retained = await candidate.getAttribute("aria-pressed");
  // Prior reviewer observations must finish autosaving before this read-only phase.
  await expect(page.locator(".draft-save-status")).toHaveText("已自动保存");
  const mutations: string[] = [];
  const observe = (request: import("@playwright/test").Request) => {
    if (request.method() !== "GET" && request.url().includes("/api/v2/")) mutations.push(request.url());
  };
  page.on("request", observe);
  try {
    const trigger = page.getByTestId(`view-asset-${candidateId}`);
    await trigger.click();
    const dialog = page.getByRole("dialog", { name: `完整图片 · 候选图片 ${candidateId}`, exact: true });
    await expect(dialog).toBeVisible();
    await expect(dialog.locator("img")).toHaveCSS("object-fit", "contain");
    await expect(dialog).toContainText("仅查看，不改变候选、关键帧或审核决定");
    await expect(page.locator("body")).toHaveCSS("overflow", "hidden");
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
    await expect(candidate).toHaveAttribute("aria-pressed", retained!);
    await trigger.click();
    await expect(dialog).toBeVisible();
    // Outside the bounded image canvas is the actual dismissing backdrop.
    await dialog.click({ position: { x: 8, y: 8 } });
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();

    const comparison = page.getByTestId("frozen-reference-comparison");
    const images = comparison.getByRole("button", { name: "放大查看", exact: true });
    const count = await images.count();
    expect(count).toBeGreaterThan(1);
    for (let index = 0; index < count; index += 1) {
      const image = images.nth(index);
      const src = await image.locator("img").getAttribute("src");
      await image.click();
      const full = page.getByRole("dialog");
      await expect(full.locator("img")).toHaveAttribute("src", src!);
      if (index === 0) {
        for (const size of [{ width: 1280, height: 460 }, { width: 1280, height: 768 }, { width: 1700, height: 900 }]) {
          await page.setViewportSize(size);
          await expect(full.locator("img")).toBeVisible();
          expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
          const bounds = await full.evaluate(element => [...element.querySelectorAll("button, strong, img, small")].map(child => {
            const box = child.getBoundingClientRect();
            return { top: box.top, bottom: box.bottom, left: box.left, right: box.right };
          }));
          for (const box of bounds) {
            expect(box.top).toBeGreaterThanOrEqual(0);
            expect(box.bottom).toBeLessThanOrEqual(size.height);
            expect(box.left).toBeGreaterThanOrEqual(0);
            expect(box.right).toBeLessThanOrEqual(size.width);
          }
          await page.screenshot({ path: info.outputPath(`full-shot-image-${size.width}x${size.height}.png`) });
        }
      }
      await full.getByRole("button", { name: "关闭", exact: true }).click();
      await expect(full).toHaveCount(0);
      await expect(image).toBeFocused();
    }
    expect(mutations).toEqual([]);
  } finally {
    page.off("request", observe);
    await page.setViewportSize({ width: 1440, height: 900 });
  }
}
