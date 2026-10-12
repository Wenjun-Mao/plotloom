import { test, expect } from "./vite-only-fixture";
import type { Handoff } from "../src/features/autopilot/contracts";

test.beforeEach(async ({ page }) => {
  // Local thumbnail fixture. No retained installation or native specialist.
  await page.route("**/managed-assets/**", route => route.fulfill({ contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#1d344c"/><path d="M290 330V90h60v240M275 90h90L320 50z" fill="#f5cb82"/><circle cx="320" cy="130" r="14" fill="#fff"/></svg>' }));
});

test("one saved-Brief Start freezes explicit styles and ceilings without videos", async ({ page, frontendOrigin }) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html?state=fresh`);
  await page.getByRole("button", { name: "一键准备视频素材", exact: true }).click();
  await expect(page.getByText("文字助手：文字测试助手", { exact: false })).toBeVisible();
  await page.getByLabel("角色与美术图像风格").selectOption("realistic");
  await page.getByLabel("最多图片数").fill("40"); await page.getByLabel("最多任务数").fill("56");
  await page.getByRole("button", { name: "开始准备已保存简报的素材" }).click();
  await expect(page.getByRole("button", { name: "暂停", exact: true })).toBeVisible();
  const writes = JSON.parse(await page.locator("#fixture-writes").textContent() || "[]");
  expect(writes).toEqual([["start", { renderStyle: "realistic", artRenderStyle: "realistic", maxImages: 40, maxJobs: 56, expectedBriefRevision: 1 }]]);
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
  await page.getByRole("button", { name: "一键准备视频素材", exact: true }).click();
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
  await expect(page.getByText("Disposable transient read failure", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "审阅完整素材", exact: true })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(await page.locator("#fixture-writes").textContent()).toBe("[]");
});

test("whole review requires real observations and separate uncertain identity authorization", async ({ page, frontendOrigin }, testInfo) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html`);
  await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "审阅完整素材" });
  const confirm = dialog.getByRole("button", { name: "确认素材，进入视频制作" });
  await expect(confirm).toBeDisabled(); await expect(dialog.getByLabel("shot-1 hero 身份判断")).toHaveValue("");
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
  await dialog.getByLabel("我已检查并采用 守塔人").check(); await dialog.getByLabel("我已检查并采用 灯塔").check();
  for (const shot of ["shot-1", "shot-2"]) {
    await dialog.getByRole("textbox", { name: `${shot} 画面意图`, exact: true }).fill("清楚展示当前动作与环境关系。");
    await dialog.getByRole("textbox", { name: `${shot} 意图依据`, exact: true }).fill(shot);
    await dialog.getByRole("textbox", { name: `${shot} 镜头兼容性观察`, exact: true }).fill("实际看过此帧，构图与镜头动作相符。");
  }
  await dialog.getByRole("textbox", { name: "审阅人", exact: true }).fill("测试审阅人"); await dialog.getByLabel("整包审阅意见").fill("已检查全部故事路线与图片。");
  await dialog.getByLabel("shot-1 hero 身份判断").selectOption("unassessable");
  await dialog.getByLabel("shot-1 hero 身份观察").fill("人物背对镜头，脸部不可见。");
  await dialog.getByLabel("shot-1 hero 状态观察").fill("外衣与伸手姿态符合当前动作。");
  await dialog.getByLabel("shot-1 hero 不确定原因").fill("此镜头有意使用背影，接受身份不确定性。");
  await dialog.getByLabel("shot-1 hero 制作授权").selectOption("hold"); await expect(confirm).toBeDisabled();
  await dialog.getByLabel("shot-1 hero 制作授权").selectOption("authorize"); await expect(confirm).toBeEnabled();
  await confirm.click(); await expect(dialog).not.toBeVisible(); await expect(page.getByRole("button", { name: "进入手动视频制作" })).toBeVisible();
  const writes = JSON.parse(await page.locator("#fixture-writes").textContent() || "[]") as Array<[string, Handoff]>;
  expect(writes).toHaveLength(1); expect(writes[0][0]).toBe("handoff");
  expect(writes[0][1].frames[0].comparisons[0].judgment).toBe("unassessable"); expect(writes[0][1].frames[0].comparisons[0].productionDecision).toBe("authorize");
  expect(writes[0][1].frames[1].comparisons).toEqual([]);
});

test("closing and reloading review never fabricates completed judgments", async ({ page, frontendOrigin }) => {
  await page.goto(`${frontendOrigin}/v2/e2e/autopilot-fixture.html`);
  await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  await page.getByLabel("shot-1 hero 身份判断").selectOption("fail");
  await page.getByRole("button", { name: "关闭审阅" }).click();
  await page.reload(); await page.getByRole("button", { name: "审阅完整素材", exact: true }).click();
  await expect(page.getByLabel("shot-1 hero 身份判断")).toHaveValue("");
  await expect(page.getByRole("button", { name: "确认素材，进入视频制作" })).toBeDisabled();
  expect(await page.locator("#fixture-writes").textContent()).toBe("[]");
});
