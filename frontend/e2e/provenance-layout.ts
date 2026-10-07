import type { Locator, Page, TestInfo } from "@playwright/test";
import { expect } from "./fixture";

/** Presentation-only fixture: never persists or claims a real rights declaration. */
export async function inspectLongProvenanceLayout(
  page: Page, projectId: string, assetId: string, details: Locator,
  owner: string, testInfo: TestInfo, reopen: () => Promise<void>,
) {
  const originalViewport = page.viewportSize();
  const url = `**/api/v2/projects/${projectId}/visual-workbench`;
  const note = "LAYOUT FIXTURE ONLY — declared license evidence remains subject to separate creator review. Long retained rights notes must wrap without obscuring the exact asset identity or the source label. 中文权利说明仅测试排版，不构成授权或创作者确认。";
  await page.route(url, async route => {
    const response = await route.fetch();
    const body = await response.json();
    for (const asset of body.assets) if (asset.id === assetId) {
      asset.provenance = { ...asset.provenance, rights: "known", rightsNote: note };
    }
    await route.fulfill({ response, json: body });
  });
  try {
    await page.reload(); await reopen();
    await expect(details).toContainText(note);
    const noteValue = details.locator("dl div").filter({ has: page.getByText("权利说明", { exact: true }) }).locator("dd");
    for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }]) {
      await page.setViewportSize(viewport);
      const cards = page.getByLabel("候选图像比较", { exact: true }).locator(".media-candidate");
      const heights = () => cards.evaluateAll(elements => elements.map(card => ({
        top: card.getBoundingClientRect().top,
        disclosure: card.querySelector("details")!.getBoundingClientRect().height,
        pick: card.querySelector(":scope > button")!.getBoundingClientRect().height,
        action: card.querySelector(".selection-toggle")!.getBoundingClientRect().height,
        selected: card.querySelector(".selection-toggle")!.getAttribute("aria-pressed"),
      })));
      const baseline = owner === "shot" ? await heights() : [];
      if (owner === "shot") expect(baseline.filter(card => Math.abs(card.top - baseline[0].top) < 1).length).toBeGreaterThanOrEqual(2);
      await details.locator("summary").click();
      await noteValue.scrollIntoViewIfNeeded();
      const geometry = await details.evaluate(element => {
        const box = element.getBoundingClientRect();
        return { width: box.width, client: element.clientWidth, scroll: element.scrollWidth,
          rows: [...element.querySelectorAll("dl div")].map(row => {
            const label = row.querySelector("dt")!.getBoundingClientRect();
            const value = row.querySelector("dd")!.getBoundingClientRect();
            return { gap: value.left - label.right, right: value.right - box.right };
          }) };
      });
      expect(geometry.scroll).toBeLessThanOrEqual(geometry.client + 1);
      for (const row of geometry.rows) { expect(row.gap).toBeGreaterThanOrEqual(0); expect(row.right).toBeLessThanOrEqual(0); }
      expect(await noteValue.evaluate(element => element.scrollHeight)).toBe(await noteValue.evaluate(element => element.clientHeight));
      if (owner === "shot") {
        const expanded = await heights();
        for (let index = 0; index < baseline.length; index++) {
          expect(expanded[index].action).toBeCloseTo(baseline[index].action, 0);
          expect(expanded[index].pick).toBeCloseTo(baseline[index].pick, 0);
          expect(expanded[index].selected).toBe(baseline[index].selected);
          if (await cards.nth(index).locator("details").getAttribute("open") === null) expect(expanded[index].disclosure).toBeCloseTo(baseline[index].disclosure, 0);
        }
      }
      await page.screenshot({ path: testInfo.outputPath(`${owner}-long-rights-${viewport.width}.png`) });
      await details.locator("summary").click();
      if (owner === "shot") expect((await heights()).map(({ top: _top, ...height }) => height)).toEqual(baseline.map(({ top: _top, ...height }) => height));
    }
  } finally {
    await page.unroute(url);
    if (originalViewport) await page.setViewportSize(originalViewport);
    await page.reload(); await reopen();
  }
}
