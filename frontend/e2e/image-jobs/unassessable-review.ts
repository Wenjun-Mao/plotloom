import type { APIRequestContext, Page, TestInfo } from "@playwright/test";
import { expect } from "../fixture";
import type { VisualWorkbench } from "../../src/types";

/** Real disposable runtime; accepted uncertainty is explicit and reversible. */
export async function inspectUnassessableReview(page: Page, request: APIRequestContext, url: string,
  videoBody: Record<string, unknown>, media: VisualWorkbench, info: TestInfo) {
  const panel = page.getByTestId("same-person-review-panel");
  const binding = media.reviewedKeyframes[0];
  const judgment = panel.getByTestId("same-person-judgment-char_ruanxing");
  const record = panel.getByTestId("record-same-person-review");
  const identityNotes = panel.getByLabel("身份对比说明");
  const stateNotes = panel.getByLabel("镜头状态说明");
  await identityNotes.fill("");
  await stateNotes.fill("");
  await judgment.selectOption("unassessable");
  const production = panel.getByTestId("same-person-production-char_ruanxing");
  await expect(production).toHaveValue("");
  await panel.getByLabel("复核备注").fill("Offline review fixture accepts intentional framing, not identity PASS.");
  await expect(record).toBeDisabled();
  await production.selectOption("authorize");
  await expect(record).toBeDisabled();
  await panel.getByLabel("构图与身份不确定性说明").fill("此镜头有意只显示双手；无法观察面貌，审阅者接受身份无法辨认的不确定性。测试沿用保留图片，不作原生媒体验收。");
  await production.selectOption("hold");
  await expect(record).toBeDisabled();
  await stateNotes.fill("此例仅记录手部首帧，身份仍无法观察。");
  await expect(record).toBeDisabled();
  await stateNotes.fill("");
  await identityNotes.fill("仅双手取景不显示面貌，不能比较角色身份；未判断通过。此为离线功能夹具。");
  await expect(record).toBeDisabled();
  await stateNotes.fill("此例单独记录手部与袖口的首帧状态，不推断面貌；不是原生媒体或创作质量验收。");
  await expect(record).toBeEnabled();
  const save = async () => {
    const pending = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/same-person-reviews"));
    await record.click();
    const response = await pending;
    expect(response.status(), await response.text()).toBe(201);
    return response.json();
  };
  const held = await save();
  expect(held).toMatchObject({ current: true, latest: true, productionEligible: false });
  await expect(panel).toContainText("无法判断 · 暂缓投产");
  await expect(page.getByTestId("create-still-preview")).toBeDisabled();
  expect((await request.post(`${url}/video-jobs/prompt-preview`, { data: videoBody })).status()).toBe(409);

  await production.selectOption("authorize");
  await panel.getByLabel("复核备注").fill("Human explicitly accepts unobservable identity for the frozen framing.");
  for (const size of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(size);
    await production.scrollIntoViewIfNeeded();
    await expect(production).toBeVisible();
    await expect(record).toBeEnabled();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
    await page.screenshot({ path: info.outputPath(`unassessable-choice-${size.width}x${size.height}.png`) });
  }
  const authorized = await save();
  expect(authorized).toMatchObject({ current: true, latest: true, productionEligible: true });
  expect(authorized.comparisons[0].judgment).toBe("unassessable");
  await expect(panel).toContainText("已明确授权投产（接受身份不确定性）");
  await expect(page.getByTestId("create-still-preview")).toBeEnabled();
  expect((await request.post(`${url}/video-jobs/prompt-preview`, { data: videoBody })).status()).toBe(200);
  const previewBody = { sceneId: binding.sceneId, shotIds: [binding.shotId], expectedSelectionRevision: media.selectionRevision,
    storyboardRevision: videoBody.storyboardRevision, approvalId: videoBody.approvalId };
  const previewResponse = await request.post(`${url}/still-previews`, { data: previewBody });
  expect(previewResponse.status()).toBe(201);
  const preview = await previewResponse.json();
  expect(preview.manifest.frames[0].identityReviewId).toBe(authorized.id);
  for (const size of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(size);
    const status = panel.getByText("当前复核", { exact: false });
    await status.scrollIntoViewIfNeeded();
    await expect(status).toContainText("无法判断");
    await page.screenshot({ path: info.outputPath(`unassessable-authorized-${size.width}x${size.height}.png`) });
  }
  await judgment.selectOption("fail");
  await expect(production).toHaveCount(0);
  await panel.getByLabel("复核备注").fill("New explicit refusal supersedes accepted uncertainty and every older approval.");
  await save();
  await expect(panel).toContainText("此决定阻止生成视频或创建连续静帧预览");
  await expect(page.getByTestId("create-still-preview")).toBeDisabled();
  expect((await request.post(`${url}/video-jobs/prompt-preview`, { data: videoBody })).status()).toBe(409);
  const previews = (await request.get(`${url}/still-previews`).then(response => response.json())).previews;
  const old = previews.find((item: { id: string }) => item.id === preview.id);
  expect(old.state).toBe("stale");
  expect(old.manifest).toEqual(preview.manifest);
  expect((await request.get(`${url}/video-jobs`).then(response => response.json())).jobs).toEqual([]);
}
