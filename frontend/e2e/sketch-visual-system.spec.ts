import { expect, test } from "./fixture";
import { createScriptProject, endpoint, json, writeDelivery } from "./f5a-fixture";
import type { Page } from "@playwright/test";
import { createCreatorGraph } from "./fixtures/creator-graph";

async function fitsViewport(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  for (const card of await page.locator(".modal-card, .confirmation-dialog").all()) {
    if (!await card.isVisible()) continue;
    const bounds = await card.boundingBox();
    const viewport = page.viewportSize()!;
    expect(bounds!.x).toBeGreaterThanOrEqual(0); expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(viewport.width);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(viewport.height);
    // Geometry alone misses dialogs trapped beneath a sibling sticky surface.
    for (const control of await card.locator("header h2, footer button").all()) {
      expect(await control.evaluate(element => {
        const bounds = element.getBoundingClientRect();
        const painted = document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
        return element.contains(painted);
      })).toBe(true);
    }
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

const desktopViewports = [
  { width: 1700, height: 900 },
  { width: 1280, height: 768 },
  { width: 1280, height: 460 },
];

for (const viewport of desktopViewports) {
  const { width, height } = viewport;
  test(`desktop visual journey and protected review states at ${width}x${height}`, async ({ page, request, workbench }, info) => {
    test.setTimeout(120_000);
    await page.setViewportSize(viewport);
    const capture = async (name: string) => {
      await fitsViewport(page);
      await page.screenshot({ path: info.outputPath(`${name}-${width}x${height}.png`), fullPage: true });
      await page.screenshot({ path: info.outputPath(`${name}-${width}x${height}-viewport.png`) });
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
    const help = page.getByRole("button", { name: "说明：每次完整播放的选择次数", exact: true });
    await page.keyboard.press("Tab");
    await help.focus();
    const tip = page.getByRole("tooltip").filter({ visible: true });
    await expect(tip).toHaveCount(1);
    await tip.evaluate(element => element.scrollIntoView({ block: "center", inline: "nearest" }));
    const box = await tip.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0); expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    expect(box!.y).toBeGreaterThanOrEqual(0); expect(box!.y + box!.height).toBeLessThanOrEqual(height);
    expect(await help.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe("none");
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
    const updatedAt = page.locator(".directory-item time");
    await expect(updatedAt).toHaveAttribute("datetime", /\d{4}-\d{2}-\d{2}T/);
    await expect(updatedAt).not.toContainText(/AM|PM/);
    await capture("directory-populated");
    await page.locator(".directory-dialog > footer").getByRole("button", { name: "关闭窗口", exact: true }).click();
    for (const [name, route, heading, owner, readyText] of [
      ["source-accepted", "stage=source#source", "来源与大纲", "source-outline-accepted", "已确认 r1"],
      ["characters", "stage=characters", "角色", "cast-review", "已确认角色设定 r1"],
      ["art", "stage=source#art", "美术参考", "art-review", "已确认美术设定 r1"],
      ["script", "stage=source#script", "剧本", "script-review", "已确认 r1"],
      ["storyboard-production", "stage=source#storyboard-review", "分镜评审", "storyboard-review", "已确认评审 r1"],
    ]) {
      await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&${route}`);
      await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
      // A painted heading is not evidence that its async review read settled.
      await expect(page.getByTestId(owner)).toContainText(readyText);
      await capture(name);
    }
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&view=story-prototype`);
    await expect(page.getByTestId("route-reader")).toBeVisible();
    await capture("reader");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&view=play`);
    // This fixture has confirmed reviews, not an installed production storyboard.
    await expect(page.getByRole("heading", { name: "故事尚未准备好", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "前往分镜评审与制作", exact: true })).toHaveAttribute("href", `?project=${id}&stage=source#storyboard-review`);
    await expect(page.getByRole("alert")).toHaveCount(0);
    await capture("player-before-production");

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

test("long current source graph retains selected dirty detail and explicit deletion preview", async ({ page, request, workbench }, info) => {
  await page.setViewportSize({ width: 1700, height: 900 });
  const id = await createCreatorGraph(request, workbench.apiOrigin, "visual-long", 6, 12);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await page.getByRole("button", { name: "选择节点 step-6", exact: true }).click();
  const title = page.getByLabel("章节标题", { exact: true });
  await title.fill("长图中的未保存标题");
  const summary = page.getByLabel("剧情摘要");
  await summary.fill("长内容保留当前选择与作者输入。".repeat(150));
  await expect(page.locator("[data-creator-node]")).toHaveCount(24);
  expect((await page.locator(".creator-chart-scroll").boundingBox())!.height).toBeGreaterThan(2000);
  const canvas = await page.locator(".creator-chart-scroll").boundingBox();
  const inspector = await page.locator(".creator-inspector").boundingBox();
  expect(inspector!.x).toBeGreaterThanOrEqual(canvas!.x + canvas!.width - 1);
  await page.getByRole("tab", { name: "制作", exact: true }).click();
  await page.getByRole("tab", { name: "故事", exact: true }).click();
  await expect(title).toHaveValue("长图中的未保存标题");
  await expect(page.locator('.graph-node-details[data-node-id="step-6"]')).toBeVisible();
  await fitsViewport(page);
  await page.screenshot({ path: info.outputPath("long-graph-side-detail.png"), fullPage: true });
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(await title.evaluate(el => parseFloat(getComputedStyle(el).transitionDuration))).toBeLessThan(0.01);
  await page.getByRole("button", { name: "删除节点…", exact: true }).click();
  await page.getByRole("button", { name: "仅删除，保留待连接", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "确认结构修改" })).toBeVisible();
  await page.screenshot({ path: info.outputPath("graph-confirmation.png"), fullPage: true });
  await page.getByRole("button", { name: "取消", exact: true }).click();
  await expect(title).toHaveValue("长图中的未保存标题");
});

test("professional tools and media consent retain the supported desktop vocabulary", async ({ page, request, workbench }, info) => {
  test.setTimeout(90_000);
  const id = await createCreatorGraph(request, workbench.apiOrigin, "visual-tools");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=graph`);
  await page.getByText("编辑与工具", { exact: true }).click();
  for (const viewport of desktopViewports) {
    const { width, height } = viewport;
    await page.setViewportSize(viewport);
    for (const label of ["故事圣经", "剧情 DAG", "场景节拍", "分镜工作台", "运行轨迹", "隔离修复"]) {
      await page.getByRole("navigation", { name: "编辑与工具" }).getByRole("button", { name: label, exact: false }).click();
      await expect(page.getByRole("heading", { name: label === "剧情 DAG" ? "剧情图与结构规则" : label, exact: true })).toBeVisible();
      if (label === "场景节拍") {
        const addScene = page.getByRole("button", { name: "＋ 添加场景", exact: true });
        expect(await addScene.evaluate(element => getComputedStyle(element).gridTemplateColumns)).toBe("none");
        const textHeight = await addScene.evaluate(element => {
          const range = document.createRange(); range.selectNodeContents(element);
          return { height: range.getBoundingClientRect().height, lineHeight: parseFloat(getComputedStyle(element).lineHeight) };
        });
        expect(textHeight.height).toBeLessThanOrEqual(textHeight.lineHeight + 1);
      }
      await fitsViewport(page);
      await page.screenshot({ path: info.outputPath(`${label}-${width}x${height}.png`), fullPage: true });
      await page.screenshot({ path: info.outputPath(`${label}-${width}x${height}-viewport.png`) });
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("button", { name: "生成助手设置", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  const settings = page.getByRole("dialog", { name: "生成助手设置", exact: true });
  await settings.getByRole("textbox", { name: "聊天 ID", exact: true }).nth(1).waitFor();
  for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(viewport);
    await settings.locator(".modal-body").evaluate(element => { element.scrollTop = 0; });
    await expect(settings.locator("legend").filter({ hasText: "文字创作助手" })).toBeInViewport();
    await fitsViewport(page);
    await page.screenshot({ path: info.outputPath(`assistant-settings-${viewport.width}x${viewport.height}-top.png`) });
    await settings.getByRole("textbox", { name: "聊天 ID", exact: true }).nth(0).scrollIntoViewIfNeeded();
    await expect(settings.getByRole("textbox", { name: "聊天 ID", exact: true }).nth(0)).toBeInViewport();
    await fitsViewport(page);
    await page.screenshot({ path: info.outputPath(`assistant-settings-${viewport.width}x${viewport.height}-text.png`) });
    await fitsViewport(page);
    await settings.getByRole("textbox", { name: "聊天 ID", exact: true }).nth(1).scrollIntoViewIfNeeded();
    await expect(settings.getByRole("textbox", { name: "聊天 ID", exact: true }).nth(1)).toBeInViewport();
    await fitsViewport(page);
    await page.screenshot({ path: info.outputPath(`assistant-settings-${viewport.width}x${viewport.height}.png`) });
  }
  await settings.getByRole("button", { name: "关闭", exact: true }).click();
  await expect(settings).toHaveCount(0);
  // Existing real controls with a test-only mutation recorder exercise DOM consent.
  await page.goto(`${workbench.frontendOrigin}/v2/e2e/creator-confirmation-fixture.html`);
  await page.getByRole("region", { name: "Rejection fixture" }).getByRole("button", { name: "拒绝此原片并撤销选择" }).click();
  const consent = page.getByRole("alertdialog");
  await expect(consent).toBeVisible();
  await expect(consent.getByRole("button", { name: "取消", exact: true })).toBeFocused();
  await fitsViewport(page);
  await page.screenshot({ path: info.outputPath("media-consent-1280.png") });
  await page.keyboard.press("Escape");
  await expect(page.locator("#fixture-writes")).toHaveText("[]");
});
