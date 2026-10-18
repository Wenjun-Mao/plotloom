import { test, expect } from "./vite-only-fixture";
import type { BulkHandoff } from "../src/features/autopilot/contracts";

test("concurrent preparation shows durable states, retained count and unknown inventory at desktop sizes", async ({ page, frontendOrigin }, info) => {
  for (const height of [900, 600]) {
    await page.setViewportSize({ width: 1440, height });
    await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=concurrent`);
    const activity = page.getByRole("region", { name: "当前素材任务" });
    await expect(activity.getByText("正在生成", { exact: true })).toBeVisible();
    await expect(activity.getByText("正在校验", { exact: true })).toBeVisible();
    await expect(activity.getByText("排队", { exact: true })).toBeVisible();
    await expect(activity.getByText("结果待核对", { exact: true })).toBeVisible();
    await expect(page.getByText("本次生成：Codex · gpt-6.1-sol · 最多同时运行 4 项任务", { exact: true })).toBeVisible();
    const sticky = page.locator(".autopilot-progress");
    await expect(sticky).toContainText("候选已保留 1 张 · 图片总量待完整发现 · 生成 1 · 校验 1 · 排队 1");
    await expect(page.getByRole("button", { name: "接管手动编辑", exact: true })).toBeVisible();
    await page.screenshot({ path: info.outputPath(`concurrent-progress-${height}.png`), fullPage: true });
    expect(await page.locator("#fixture-writes").textContent()).toBe("[]");
  }
});

for (const height of [900, 600]) {
  test(`complete review displays source-bound limitations and separate adaptation history at 1440x${height}`, async ({ page, frontendOrigin }, info) => {
    await page.setViewportSize({ width: 1440, height });
    await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html`);
    await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "审阅完整素材" });
    for (const text of ["主参考：服装细节仍须人工核查。", "补充参考：侧脸仍须人工核查。", "额外椅子、花瓶与植物偏离冻结要求。",
      "原始输出为 941×1672，尺寸与冻结目标不符。", "适配输出仍需实际检查手部与构图；不代表质量改善。"]) await expect(dialog.getByText(text, { exact: true })).toBeVisible();
    const originalDisclosure = dialog.locator("details").filter({ has: page.locator('a[href$="frame-original/original"]') }).last();
    await originalDisclosure.locator("summary").click();
    const history = dialog.getByRole("img", { name: /适配来源原图 1/ });
    await expect(history).toBeVisible(); await expect(originalDisclosure.getByRole("link", { name: "打开完整原图" })).toHaveAttribute("href", /frame-original\/original$/);
    const declarations = dialog.locator(".autopilot-delivery-disclosure");
    await declarations.first().locator("summary").click();
    await expect(declarations.first()).toContainText("hero-job"); await expect(declarations.first()).toContainText("e".repeat(64));
    await declarations.first().scrollIntoViewIfNeeded(); await page.screenshot({ path: info.outputPath(`reference-disclosures-${height}.png`) });
    await history.scrollIntoViewIfNeeded(); await page.screenshot({ path: info.outputPath(`original-adaptation-disclosures-${height}.png`) });
    await expect(dialog.getByRole("button", { name: "确认全部素材并继续" })).toBeEnabled();
    expect(await page.locator("#fixture-writes").textContent()).toBe("[]");
  });
}

test("failed disclosure reads remain unknown and retry preserves authored observations", async ({ page, frontendOrigin }) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=evidence-failure`);
  await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "审阅完整素材" });
  await expect(dialog.getByText("图片交付说明读取失败", { exact: false })).toBeVisible();
  await expect(dialog).not.toContainText("未声明局限");
  const observation = page.getByRole("textbox", { name: "shot-1 画面意图", exact: true });
  await dialog.getByText("查看意图与处理例外 · shot-1", { exact: true }).click();
  await observation.fill("保留作者在读取失败期间填写的观察。");
  await page.getByRole("button", { name: "重试读取图片交付说明" }).click();
  await expect(dialog.getByText("额外椅子、花瓶与植物偏离冻结要求。", { exact: true })).toBeVisible();
  await expect(observation).toHaveValue("保留作者在读取失败期间填写的观察。");
  expect(await page.locator("#fixture-writes").textContent()).toBe("[]");
});

test.beforeEach(async ({ page }) => {
  // Local thumbnail fixture. No retained installation or native specialist.
  await page.route("**/managed-assets/**", route => route.fulfill({ contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#1d344c"/><path d="M290 330V90h60v240M275 90h90L320 50z" fill="#f5cb82"/><circle cx="320" cy="130" r="14" fill="#fff"/></svg>' }));
});

test("one saved-Brief Start freezes explicit styles and ceilings without videos", async ({ page, frontendOrigin }) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=fresh`);
  await page.getByRole("button", { name: "自动准备素材", exact: true }).click();
  await expect(page.getByText("由 Codex 执行文字与图片任务", { exact: false })).toBeVisible();
  await expect(page.getByText("2D 动画；水彩；低饱和", { exact: true })).toBeVisible();
  await page.getByLabel("最多图片数").fill("40"); await page.getByLabel("最多任务数").fill("56");
  await page.getByRole("button", { name: "开始准备已保存简报的素材" }).click();
  await expect(page.getByRole("button", { name: "暂停", exact: true })).toBeVisible();
  const writes = JSON.parse(await page.locator("#fixture-writes").textContent() || "[]");
  expect(writes).toEqual([["start", { styleAuthority: "brief", maxImages: 40, maxJobs: 56, expectedBriefRevision: 1 }]]);
});

test("pause and resume use original run controls; takeover retains review entrance", async ({ page, frontendOrigin }) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=running`);
  await page.getByRole("button", { name: "暂停", exact: true }).click();
  await expect(page.getByText("已暂停", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "继续原任务" }).click();
  await page.getByRole("button", { name: "接管手动编辑" }).click();
  await expect(page.getByRole("button", { name: "审阅完整素材", exact: true })).toBeVisible();
  expect(JSON.parse(await page.locator("#fixture-writes").textContent() || "[]")).toEqual([["control", "pause"], ["control", "resume"], ["control", "takeover"]]);
});

test("fresh Start observes same-project server progress through review without navigation", async ({ page, frontendOrigin }) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=fresh-progress`);
  const originalUrl = page.url();
  await page.getByRole("button", { name: "自动准备素材", exact: true }).click();
  await page.getByRole("button", { name: "开始准备已保存简报的素材" }).click();
  await expect(page.getByText("故事大纲", { exact: true })).toBeVisible();
  await expect(page.getByText("参考图片", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "审阅完整素材", exact: true })).toBeVisible();
  expect(page.url()).toBe(originalUrl);
  const writes = JSON.parse(await page.locator("#fixture-writes").textContent() || "[]");
  expect(writes).toHaveLength(1); expect(writes[0][0]).toBe("start");
});

test("transient progress read failure retries original observation without dispatch", async ({ page, frontendOrigin }) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=running-retry`);
  const status = page.locator(".autopilot-progress");
  await expect(status).toContainText("文字 1/8");
  await expect(page.getByText("Disposable transient read failure", { exact: false })).toBeVisible();
  await expect(status).not.toContainText("文字 1/8");
  await expect(status).not.toContainText("图片 0/2");
  await expect(page.getByRole("button", { name: "审阅完整素材", exact: true })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(status).toContainText("文字 1/8", { timeout: 7000 });
  expect(await page.locator("#fixture-writes").textContent()).toBe("[]");
});

test("long blocker remains readable at desktop, narrow and short viewports", async ({ page, frontendOrigin }, info) => {
  for (const size of [{ width: 1440, height: 900 }, { width: 390, height: 844 }, { width: 390, height: 600 }]) {
    await page.setViewportSize(size);
    await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=blocked-long`);
    const status = page.locator(".autopilot-progress");
    await expect(status).toContainText("需要处理");
    await expect(status).toContainText("active workflow revision");
    const layout = await page.evaluate(() => ({ viewportWidth: innerWidth, documentWidth: document.documentElement.scrollWidth,
      statusWidth: document.querySelector(".autopilot-progress")!.getBoundingClientRect().width,
      statusHeight: document.querySelector(".autopilot-progress")!.getBoundingClientRect().height }));
    expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewportWidth);
    expect(layout.statusWidth).toBeLessThanOrEqual(layout.viewportWidth);
    expect(layout.statusHeight).toBeGreaterThan(45);
    await page.screenshot({ path: info.outputPath(`long-blocker-${size.width}x${size.height}.png`) });
  }
});

for (const outcome of ["normal", "handoff-unknown", "handoff-uncommitted"]) test(outcome === "normal" ? "whole review confirms once and records separate uncertain identity authorization" : outcome === "handoff-unknown" ? "lost handoff acknowledgment reconciles durable result without resending confirmation" : "uncommitted handoff retains authored edits through failed read reconciliation", async ({ page, frontendOrigin }, testInfo) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html${outcome === "normal" ? "" : `?state=${outcome}`}`);
  await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "审阅完整素材" });
  const confirm = dialog.getByRole("button", { name: "确认全部素材并继续" });
  await expect(confirm).toBeEnabled();
  await expect(dialog.getByRole("heading", { name: "守塔人 · 2 张参考" })).toBeVisible();
  await expect(dialog.getByRole("img", { name: "守塔人主参考", exact: true })).toBeVisible();
  await expect(dialog.getByRole("img", { name: "守塔人补充参考 1", exact: true })).toBeVisible();
  await expect(dialog.locator('a[href$="/hero-side/original"]')).toHaveCount(1);
  await dialog.getByText("完整故事与全部路线", { exact: true }).click();
  await expect(dialog.getByText("灯塔 → 点亮", { exact: true })).toBeVisible(); await expect(dialog.getByText("灯塔 → 熄灭", { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("whole-review-desktop.png"), fullPage: true });
  await dialog.locator(".autopilot-gallery").scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("reference-gallery-desktop.png"), fullPage: true });
  await dialog.locator(".autopilot-frame").first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("frame-observations-desktop.png"), fullPage: true });
  await expect(dialog.getByRole("checkbox")).toHaveCount(0);
  await dialog.getByText("查看意图与处理例外 · shot-1", { exact: true }).click();
  await expect(dialog.getByRole("textbox", { name: "shot-1 画面意图", exact: true })).toHaveValue("背影中景，动作清晰可见。");
  if (outcome === "handoff-uncommitted") await dialog.getByRole("textbox", { name: "shot-1 画面意图", exact: true }).fill("清楚展示当前动作与环境关系。");
  await expect(dialog.getByRole("textbox", { name: "审阅人", exact: true })).toHaveCount(0);
  if (outcome !== "normal") await dialog.getByLabel("备注（可选）").fill("  已检查全部故事路线与图片。\n");
  await dialog.getByLabel("shot-1 hero 身份判断").selectOption("unassessable");
  await expect(confirm).toBeDisabled();
  await dialog.getByLabel("shot-1 hero 不确定原因").fill("此镜头有意使用背影，接受身份不确定性。");
  await dialog.getByLabel("shot-1 hero 制作授权").selectOption("hold"); await expect(confirm).toBeDisabled();
  await dialog.getByLabel("shot-1 hero 制作授权").selectOption("authorize"); await expect(confirm).toBeEnabled();
  await expect(dialog.getByLabel("备注（可选）")).not.toHaveAttribute("required", "");
  await dialog.locator("footer").scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath(`creator-confirmation-footer-${outcome}.png`) });
  await confirm.click();
  if (outcome === "handoff-uncommitted") {
    await expect(confirm).toBeDisabled();
    await expect(dialog.getByRole("alert")).toContainText("Disposable handoff not committed");
    await expect(confirm).toBeEnabled();
    await expect(dialog.getByRole("textbox", { name: "shot-1 画面意图", exact: true })).toHaveValue("清楚展示当前动作与环境关系。");
    await expect(dialog.getByLabel("备注（可选）")).toHaveValue("  已检查全部故事路线与图片。\n");
    await expect(page.getByRole("button", { name: "进入手动视频制作" })).toHaveCount(0);
  } else { await expect(dialog).not.toBeVisible(); await expect(page.getByRole("button", { name: "进入手动视频制作" })).toBeVisible(); }
  if (outcome === "handoff-unknown") {
    await expect(page.getByRole("alert")).toContainText("Disposable handoff acknowledgment lost");
    await expect(page.getByRole("button", { name: "审阅完整素材", exact: true })).toHaveCount(0);
    await expect(page.getByText("已记录完整人工审阅", { exact: false })).toBeVisible();
  }
  const writes = JSON.parse(await page.locator("#fixture-writes").textContent() || "[]") as Array<[string, BulkHandoff]>;
  expect(writes).toHaveLength(1); expect(writes[0][0]).toBe("handoff");
  expect(writes[0][1]).not.toHaveProperty("reviewer");
  expect(writes[0][1].basis).toBe("whole-pack-material.v1");
  expect(writes[0][1].frames[0].comparisons[0]).not.toHaveProperty("identityNotes");
  if (outcome === "normal") expect(writes[0][1]).not.toHaveProperty("notes");
  else expect(writes[0][1].notes).toBe("  已检查全部故事路线与图片。\n");
  expect(writes[0][1].frames[0].comparisons[0].judgment).toBe("unassessable"); expect(writes[0][1].frames[0].comparisons[0].productionDecision).toBe("authorize");
  expect(writes[0][1].frames[1].comparisons).toEqual([]);
  expect(page.url()).toContain("/v2/e2e/autopilot-fixture.html");
});

test("closing and reloading review never fabricates completed judgments", async ({ page, frontendOrigin }) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html`);
  await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  await page.getByText("查看意图与处理例外 · shot-1", { exact: true }).click();
  await page.getByLabel("shot-1 hero 身份判断").selectOption("fail");
  await page.getByRole("button", { name: "关闭审阅" }).click();
  await page.reload(); await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  await expect(page.getByRole("button", { name: "确认全部素材并继续" })).toBeEnabled();
  expect(await page.locator("#fixture-writes").textContent()).toBe("[]");
});

test("42-frame five-reference gallery approves with one explicit final action and zero typing", async ({ page, frontendOrigin }, info) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=pack42`);
  await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "审阅完整素材" });
  await expect(dialog).toContainText("5 项参考（6 张图片） · 42 个镜头首帧");
  await expect(dialog.locator(".autopilot-frame")).toHaveCount(42);
  await expect(dialog.locator(".autopilot-frame details[open]")).toHaveCount(0);
  await expect(dialog.getByRole("checkbox")).toHaveCount(0);
  const first = dialog.locator(".autopilot-frame").first(); await first.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("whole-pack-42-gallery.png") });
  const confirm = dialog.getByRole("button", { name: "确认全部素材并继续" });
  await expect(confirm).toBeEnabled(); await confirm.click();
  await expect(dialog).not.toBeVisible();
  const writes = JSON.parse(await page.locator("#fixture-writes").textContent() || "[]") as Array<[string, BulkHandoff]>;
  expect(writes).toHaveLength(1); expect(writes[0][1].frames).toHaveLength(42); expect(writes[0][1].endorsedReferenceIds).toHaveLength(5);
  expect(writes[0][1].frames.every(frame => frame.compatibility === "pass")).toBe(true);
  expect(writes[0][1]).not.toHaveProperty("notes");
});

for (const assetId of ["frame-1", "frame-original"]) test(`known failed image ${assetId} blocks whole-pack action and retry restores only observation`, async ({ page, frontendOrigin }) => {
  const pattern = `**/managed-assets/${assetId}/**`;
  await page.route(pattern, route => route.fulfill({ status: 503, body: "Disposable missing pixels" }));
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html`);
  await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "审阅完整素材" });
  const confirm = dialog.getByRole("button", { name: "确认全部素材并继续" });
  if (assetId === "frame-original") await dialog.getByText("查看保留原图", { exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("保留原图无法读取"); await expect(confirm).toBeDisabled();
  await page.unroute(pattern); await dialog.getByRole("button", { name: "重试读取图片", exact: true }).click();
  await expect(confirm).toBeEnabled(); expect(await page.locator("#fixture-writes").textContent()).toBe("[]");
});

for (const height of [900, 600]) test(`local geometry keeps original evidence and genuine review at 1440x${height}`, async ({ page, frontendOrigin }, testInfo) => {
  await page.setViewportSize({ width: 1440, height });
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=geometry`);
  await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  const disclosure = page.getByRole("region", { name: "确定性几何处理说明" });
  await expect(disclosure.getByText("当前所选几何处理图 · 720×1280", { exact: true })).toBeVisible();
  await expect(disclosure.getByText("保留的原始生成输出 · 941×1672", { exact: true })).toBeVisible();
  await expect(disclosure.getByText("原始输出为 941×1672，尺寸与冻结目标不符。", { exact: true })).toBeVisible();
  await disclosure.getByText("查看裁剪与来源身份", { exact: true }).click();
  await disclosure.scrollIntoViewIfNeeded();
  await expect(disclosure.getByText("EXIF 方向：1 · 居中裁剪框：0.25, 0, 940.75, 1672", { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath(`geometry-disclosure-${height}.png`), fullPage: true });
  await expect(page.getByRole("button", { name: "确认全部素材并继续" })).toBeEnabled();
  expect(await page.locator("#fixture-writes").textContent()).toBe("[]");
});
