import { expect, test } from "./fixture";
import { createScriptProject, endpoint, json, writeDelivery } from "./f5a-fixture";
import type { Page } from "@playwright/test";

async function fitsViewport(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  for (const card of await page.locator(".modal-card, .confirmation-dialog").all()) {
    if (!await card.isVisible()) continue;
    const bounds = await card.boundingBox();
    const viewport = page.viewportSize()!;
    expect(bounds!.x).toBeGreaterThanOrEqual(0); expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(viewport.width);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(viewport.height);
  }
  const readability = await page.evaluate(() => {
    const luminance = (value: string) => {
      const channels = value.match(/[\d.]+/g)!.slice(0, 3).map(Number).map(n => {
        const s = n / 255; return s <= .04045 ? s / 12.92 : ((s + .055) / 1.055) ** 2.4;
      });
      return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2];
    };
    return [...document.querySelectorAll(".page-header p, .field, .source-outline-grid label, .structural-setting > div, .stage-guide-content")]
      .filter(el => el.getClientRects().length).map(el => {
        const style = getComputedStyle(el);
        let surface: Element | null = el;
        while (surface && getComputedStyle(surface).backgroundColor === "rgba(0, 0, 0, 0)") surface = surface.parentElement;
        const foreground = luminance(style.color);
        const background = luminance(getComputedStyle(surface || document.body).backgroundColor);
        return { size: parseFloat(style.fontSize), contrast: (Math.max(foreground, background) + .05) / (Math.min(foreground, background) + .05) };
      });
  });
  for (const role of readability) { expect(role.size).toBeGreaterThanOrEqual(12); expect(role.contrast).toBeGreaterThanOrEqual(4.5); }
}

for (const width of [1920, 1280, 390]) {
  test(`sketch visual journey and protected review states at ${width}px`, async ({ page, request, workbench }, info) => {
    test.setTimeout(120_000);
    await page.setViewportSize({ width, height: 900 });
    const capture = async (name: string) => {
      await fitsViewport(page);
      await page.screenshot({ path: info.outputPath(`${name}-${width}.png`), fullPage: true });
      if (width === 390) await page.screenshot({ path: info.outputPath(`${name}-${width}-viewport.png`) });
    };
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
    await capture("onboarding");
    await page.getByRole("button", { name: "打开项目目录" }).click();
    await expect(page.getByRole("dialog", { name: "项目目录" })).toBeVisible();
    await capture("directory");
    await page.locator(".directory-dialog > footer").getByRole("button", { name: "关闭窗口", exact: true }).click();
    await page.getByRole("button", { name: "创建空白项目" }).click();
    await capture("brief");
    if (width === 390) {
      const disclosure = await page.locator(".preset-custom-disclosure > summary").first().boundingBox();
      expect(disclosure!.height).toBeGreaterThanOrEqual(44);
    }
    const help = page.getByRole("button", { name: "说明：每次完整播放的选择次数", exact: true });
    await page.keyboard.press("Tab");
    await help.focus();
    const tip = page.getByRole("tooltip").filter({ visible: true });
    await expect(tip).toHaveCount(1);
    const box = await tip.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0); expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    expect(await help.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe("none");
    if (width === 390) { const hit = await help.boundingBox(); expect(hit!.width).toBeGreaterThanOrEqual(44); expect(hit!.height).toBeGreaterThanOrEqual(44); }
    await capture("help-focus");
    await help.press("Escape"); await expect(tip).toHaveCount(0);

    // Accepted fixture content is installed through real API contracts, never sent to a provider.
    const id = await createScriptProject(request, workbench.apiOrigin, `sketch-${width}`);
    const prepared = await json(request.post(`${endpoint(workbench.apiOrigin, id)}/candidates`));
    await writeDelivery(prepared);
    await json(request.post(`${endpoint(workbench.apiOrigin, id)}/candidates/${prepared.jobId}/refresh`));
    await json(request.post(`${endpoint(workbench.apiOrigin, id)}/accept`, { data: { jobId: prepared.jobId, expectedReviewRevision: prepared.expectedReviewRevision, binding: prepared.binding } }));
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开项目目录" }).click();
    await expect(page.locator(".directory-item")).toHaveCount(1);
    await capture("directory-populated");
    await page.locator(".directory-dialog > footer").getByRole("button", { name: "关闭窗口", exact: true }).click();
    for (const [name, route, heading] of [
      ["source-accepted", "stage=source#source", "来源与大纲"],
      ["characters", "stage=characters", "角色"],
      ["art", "stage=source#art", "美术参考"],
      ["script", "stage=source#script", "剧本"],
      ["storyboard-production", "stage=source#storyboard-review", "分镜评审"],
    ]) {
      await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&${route}`);
      await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
      await capture(name);
    }
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&view=story-prototype`);
    await expect(page.getByTestId("route-reader")).toBeVisible();
    await capture("reader");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&view=play`);
    await expect(page.locator(".play-stage")).toBeVisible();
    await capture("player");

    // Reopening preserves acceptance and exposes the waiting task without dispatch.
    const root = `${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`;
    await json(request.post(`${root}/reopen`, { data: { expectedOutlineRevision: 1 } }));
    await json(request.post(`${root}/candidates`));
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#source`);
    await expect(page.getByTestId("source-outline-accepted")).toContainText("已确认 r1");
    await expect(page.locator(".specialist-task-actions")).toBeVisible();
    await capture("waiting-retained-acceptance");
    const failedRead = `**/api/v2/projects/${id}/source-outline`;
    await page.route(failedRead, route => route.fulfill({ status: 503, json: { detail: "Visual fixture read failure" } }));
    await page.getByRole("button", { name: "刷新", exact: true }).click();
    await expect(page.getByRole("alert").first()).toBeVisible();
    await capture("failed-read");
    await page.unroute(failedRead);
    const previous = await json(request.get(root));
    await json(request.post(`${root}/candidates/${previous.candidate.jobId}/cancel`));
    await json(request.put(`${root}/source`, { data: { expectedSourceRevision: 1, material: { ...previous.source.material, text: previous.source.material.text + " A changed source basis." } } }));
    await page.getByRole("button", { name: "刷新", exact: true }).click();
    await expect(page.getByTestId("source-outline-accepted")).toContainText("已确认 r1");
    await capture("stale-retained-acceptance");
    await page.getByLabel("故事内容", { exact: false }).fill("未保存的长篇草稿。".repeat(120));
    await capture("dirty-source");
  });
}

test("long existing graph keeps selected dirty detail reachable beside its canvas", async ({ page, workbench }, info) => {
  await page.setViewportSize({ width: 1920, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?stage=graph`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  for (let i = 0; i < 18; i++) await page.getByTestId("graph-node-add").click();
  await page.getByTestId("graph-select-node-memory").click();
  const title = page.getByLabel("标题", { exact: true });
  await title.fill("长图中的未保存标题");
  const summary = page.getByLabel("剧情摘要");
  await summary.fill("长内容保留当前选择与作者输入。".repeat(150));
  await expect(page.locator(".react-flow__node").first()).toBeVisible();
  expect((await page.locator(".react-flow").boundingBox())!.height).toBeGreaterThan(400);
  const canvas = await page.locator(".flow-shell").boundingBox();
  const inspector = await page.locator(".node-inspector").boundingBox();
  expect(inspector!.x).toBeGreaterThanOrEqual(canvas!.x + canvas!.width - 1);
  await page.locator(".graph-entity-navigator").evaluate(el => { el.scrollTop = el.scrollHeight; });
  await expect(title).toHaveValue("长图中的未保存标题");
  await expect(page.getByLabel("节点 ID")).toHaveValue("memory");
  await fitsViewport(page);
  await page.screenshot({ path: info.outputPath("long-graph-side-detail.png"), fullPage: true });
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(await title.evaluate(el => parseFloat(getComputedStyle(el).transitionDuration))).toBeLessThan(0.01);
  await page.getByRole("button", { name: "删除节点与关联边" }).click();
  await expect(page.getByRole("dialog", { name: "关系影响确认" })).toBeVisible();
  await page.screenshot({ path: info.outputPath("graph-confirmation.png"), fullPage: true });
  await page.getByRole("button", { name: "取消", exact: true }).click();
  await expect(title).toHaveValue("长图中的未保存标题");
});

test("professional tools and media consent retain the same responsive vocabulary", async ({ page, workbench }, info) => {
  test.setTimeout(90_000);
  await page.goto(`${workbench.frontendOrigin}/v2/?stage=graph`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByText("编辑与工具", { exact: true }).click();
  for (const width of [1920, 1280, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (const label of ["故事圣经", "剧情 DAG", "场景节拍", "分镜工作台", "运行轨迹", "隔离修复"]) {
      await page.getByRole("navigation", { name: "编辑与工具" }).getByRole("button", { name: label, exact: false }).click();
      await expect(page.getByRole("heading", { name: label, exact: true })).toBeVisible();
      await fitsViewport(page);
      await page.screenshot({ path: info.outputPath(`${label}-${width}.png`), fullPage: true });
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("button", { name: "生成助手设置", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 900 });
  await fitsViewport(page);
  await page.screenshot({ path: info.outputPath("assistant-settings-390.png"), fullPage: true });
  // Existing real controls with a test-only mutation recorder exercise DOM consent.
  await page.goto(`${workbench.frontendOrigin}/v2/e2e/creator-confirmation-fixture.html`);
  await page.getByRole("region", { name: "Rejection fixture" }).getByRole("button", { name: "拒绝此原片并撤销选择" }).click();
  const consent = page.getByRole("alertdialog");
  await expect(consent).toBeVisible();
  await expect(consent.getByRole("button", { name: "取消", exact: true })).toBeFocused();
  await fitsViewport(page);
  await page.screenshot({ path: info.outputPath("media-consent-390.png"), fullPage: true });
  await page.keyboard.press("Escape");
  await expect(page.locator("#fixture-writes")).toHaveText("[]");
});
