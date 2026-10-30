import { test, expect } from "./vite-only-fixture";
import { authorizeProductionBatch, productionBatch, readyProductionBatch, sourceHash } from "../tests/h3-production-fixtures";
import type { Batch } from "../src/features/video-batch/contracts";
import type { VideoJobPrepareBody } from "../src/api";
import type { Page } from "@playwright/test";
const request: VideoJobPrepareBody = { approvalId: "approval", shotId: "shot", storyboardRevision: 1, expectedSelectionRevision: 1,
  seed: 42, idempotencyKey: "browser-fixture-key", profileId: "h3_vertical_8", aspectPolicy: "reject_mismatch", requestedDurationSeconds: 15,
  resolution: "576x1024", audio: true, playbackIntent: "segment_required" };
async function mockApi(page: Page, initial: Batch | null, qaRequired = false) {
  let batch = initial; const commands: { name: string; body: any }[] = [];
  await page.route("**/api/v2/**", async route => {
    const url = new URL(route.request().url()), name = url.pathname.split("/").at(-1)!;
    let body: unknown;
    if (name === "qa-context") body = { eligible: false, required: qaRequired, attribution: null };
    else if (name === "video-backend") body = { enabled: false };
    else if (url.pathname.endsWith("/prompt-preview")) body = { sourceHash, compiledPrompt: null, sources: [{ path: "shot.action", label: "动作", text: "守灯人把保险丝放回原处。" }] };
    else if (route.request().method() === "POST") {
      const data = route.request().postDataJSON(); commands.push({ name, body: data });
      if (name === "setup") batch = productionBatch(data.singleRequest);
      if (name === "draft") { batch = readyProductionBatch(batch!.manifest.setup.singleRequest!); batch.state = "checking"; }
      if (name === "check") { batch = readyProductionBatch(batch!.manifest.setup.singleRequest!); }
      if (name === "start") batch = authorizeProductionBatch(batch!);
      body = batch;
    } else body = batch;
    await route.fulfill({ json: body });
  });
  return commands;
}

test("complete localized brief, technical directions and rejected checking remain distinct", async ({ page, frontendOrigin }, info) => {
  const batch = readyProductionBatch(request); batch.state = "translation_rejected";
  batch.manifest.targets[0].productionBrief!.sections[0].items![0].value = "精确保留画面文字：KEEP THE LIGHT。画外音只说一次，人物双唇闭合。";
  batch.manifest.targets[0].fidelity = { verdict: "reject", checkedDimensions: [], checkedPaths: [], findings: [{ path: "shot.action", sourcePath: "shot.action", sourceOwner: "镜头编辑", code: "extra_speech", message: "删除新增对白，再交由独立助手检查。" }] };
  const commands = await mockApi(page, batch);
  await page.goto(`${frontendOrigin}/v2/e2e/production-intent-fixture.html`);
  await expect(page.getByText("精确保留画面文字：KEEP THE LIGHT。画外音只说一次，人物双唇闭合。", { exact: true })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "删除新增对白，再交由独立助手检查。" })).toBeVisible();
  await expect(page.getByRole("button", { name: "授权全部制作意图并开始生成" })).toHaveCount(0);
  const rawPrompts = page.getByText("Exact compiled provider prompt. Add no speech.", { exact: true });
  await expect(rawPrompts).toHaveCount(2);
  for (const prompt of await rawPrompts.all()) await expect(prompt).not.toBeVisible();
  for (const viewport of [{ width: 1280, height: 768 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(viewport); expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
    await page.screenshot({ path: info.outputPath(`production-brief-rejection-${viewport.width}.png`) });
    await page.getByRole("alert").filter({ hasText: "删除新增对白，再交由独立助手检查。" }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath(`production-brief-finding-${viewport.width}.png`) });
  }
  expect(commands).toEqual([]);
});

test("single shot preserves exact seed and request key through independent check and explicit generation authorization", async ({ page, frontendOrigin }) => {
  const commands = await mockApi(page, null);
  await page.goto(`${frontendOrigin}/v2/e2e/production-intent-fixture.html?single=1`);
  await page.getByText("审阅制作简报与授权生成", { exact: true }).click();
  await page.getByLabel("H3 随机种子", { exact: true }).fill("00042");
  await page.getByRole("button", { name: "读取当前来源", exact: true }).click();
  await page.getByRole("button", { name: "准备本镜头制作简报", exact: true }).click();
  await page.getByRole("button", { name: "用助手起草并独立检查指令", exact: true }).click();
  await expect(page.getByRole("button", { name: "授权本镜头制作意图并开始生成", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "核对当前候选的助手检查", exact: true }).click();
  await page.getByRole("button", { name: "授权本镜头制作意图并开始生成", exact: true }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { frozen?: unknown }).frozen)).toBeTruthy();
  const setup = commands.find(command => command.name === "setup")!.body;
  const result = await page.evaluate(() => (window as unknown as { frozen: { seed: number; key: string; value: object } }).frozen);
  expect(setup.singleRequest).toEqual({ ...request, automaticRetryLimit: 1, idempotencyKey: result.key });
  expect(setup.shotIds).toEqual(["shot"]); expect(result.seed).toBe(42);
  expect(commands.filter(command => command.name === "start")).toHaveLength(1);
  expect(commands.find(command => command.name === "start")?.body.basis).toBe("production-intent.v2");
  expect(result.value).not.toHaveProperty("reviewedEnglish");
});

test("required QA identity cannot silently become creator authorization", async ({ page, frontendOrigin }) => {
  const commands = await mockApi(page, readyProductionBatch(request), true);
  await page.goto(`${frontendOrigin}/v2/e2e/production-intent-fixture.html`);
  await expect(page.getByText(/不能改为创作者确认/)).toBeVisible();
  await expect(page.getByRole("button", { name: "授权全部制作意图并开始生成", exact: true })).toBeDisabled();
  expect(commands).toEqual([]);
});


test("English creative brief remains English inside Chinese generation controls", async ({ page, frontendOrigin }, info) => {
  const batch = readyProductionBatch(request), brief = batch.manifest.targets[0].productionBrief!;
  brief.contentLocale = "en-US"; brief.sections[0].label = "Picture and action";
  brief.sections[0].items![0].label = "Exact visible words";
  brief.sections[0].items![0].value = 'The sign reads KEEP THE LIGHT. The intentional quoted line is “再见”. Do not add speech.';
  brief.discretion = "Faithful wording only; add no new creative decisions.";
  await mockApi(page, batch); await page.goto(`${frontendOrigin}/v2/e2e/production-intent-fixture.html`);
  await expect(page.getByText("Picture and action", { exact: true })).toBeVisible();
  await expect(page.getByText(brief.sections[0].items![0].value, { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "授权全部制作意图并开始生成", exact: true })).toBeEnabled();
  expect(await page.locator("html").getAttribute("lang")).toBe("zh-CN");
  await page.setViewportSize({ width: 1280, height: 768 });
  await page.screenshot({ path: info.outputPath("english-brief-chinese-controls-1280.png") });
});
