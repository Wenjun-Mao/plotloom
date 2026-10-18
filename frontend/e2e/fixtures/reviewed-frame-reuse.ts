import { expect, type APIRequestContext, type Page } from "@playwright/test";
import type { ReviewedKeyframe, VisualIntent, VisualWorkbench } from "../../src/types";

export async function reviewedFixtureSource(request: APIRequestContext, apiOrigin: string, projectId: string) {
  const response = await request.get(`${apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(response.ok(), await response.text()).toBeTruthy();
  const state = await response.json() as VisualWorkbench;
  const binding = state.reviewedKeyframes.find(item => item.shotId === "shot_01")!;
  const intent = state.visualIntents.find(item => item.id === binding.visualIntentId)!;
  expect(binding).toBeTruthy();
  expect(intent.intent.targetUse).toBeUndefined();
  return { binding, intent };
}

type Source = { binding: ReviewedKeyframe; intent: VisualIntent };

export async function saveFixtureTargetIntent(
  page: Page, request: APIRequestContext, apiOrigin: string, projectId: string,
  source: Source, targetShotId: string,
): Promise<VisualIntent> {
  await page.getByTestId("cross-shot-use-source").selectOption(source.binding.id);
  await page.getByTestId("visual-intent-source-refs").fill(`Explicit offline fixture reuse from shot_01; independently inspected ${targetShotId}.`);
  const saved = page.waitForResponse(response => response.request().method() === "POST"
    && response.url().endsWith(`/managed-assets/${source.binding.assetId}/visual-intents`));
  await page.getByTestId("save-visual-intent").click();
  const response = await saved;
  expect(response.status(), await response.text()).toBe(201);
  const intent = await response.json() as VisualIntent;
  expect(intent.id).not.toBe(source.intent.id);
  expect(intent.intent.targetUse).toMatchObject({ targetShotId, source: { bindingId: source.binding.id } });
  await expect(page.getByText(`已保存 r${intent.revision}；审核选择会固定这一版本。`, { exact: true })).toBeVisible();
  await assertSourceUnchanged(request, apiOrigin, projectId, source);
  return intent;
}

export async function reviewFixtureTarget(
  page: Page, request: APIRequestContext, apiOrigin: string, projectId: string,
  source: Source, targetIntent: VisualIntent,
): Promise<void> {
  await expect(page.getByTestId("current-reviewed-keyframe")).toContainText(`画面意图 r${targetIntent.revision}`);
  // Typed reuse needs the target's current visible-character review, not the
  // source's reference decision or any inherited approval.
  const panel = page.getByTestId("same-person-review-panel");
  await expect(panel).toBeVisible();
  await panel.getByLabel("审阅者（姓名或 Codex）").fill("Codex");
  for (const field of await panel.getByLabel("身份对比说明").all()) {
    await field.fill("Offline browser fixture comparison: stable visible identity anchors inspected against the current reference.");
  }
  for (const field of await panel.getByLabel("镜头状态说明").all()) {
    await field.fill("Target shot action, wardrobe and lighting inspected separately from identity.");
  }
  for (const judgment of await panel.locator('[data-testid^="same-person-judgment-"]').all()) {
    await judgment.selectOption("pass");
  }
  await panel.getByLabel("复核备注").fill("Codex offline fixture review only; not human creative acceptance.");
  const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/same-person-reviews"));
  await panel.getByTestId("record-same-person-review").click();
  const response = await saved;
  expect(response.status(), await response.text()).toBe(201);
  const review = await response.json();
  expect(review.productionEligible).toBe(true);
  await expect(panel.getByText("当前复核", { exact: false })).toContainText(review.id.slice(0, 8));
  const state = await assertSourceUnchanged(request, apiOrigin, projectId, source);
  const binding = state.reviewedKeyframes.find(item => item.shotId === targetIntent.intent.targetUse!.targetShotId)!;
  expect(binding.visualIntentId).toBe(targetIntent.id);
  expect(binding.visualIntentId).not.toBe(source.binding.visualIntentId);
  expect(review.bindingId).toBe(binding.id);
}

async function assertSourceUnchanged(request: APIRequestContext, apiOrigin: string, projectId: string, source: Source) {
  const response = await request.get(`${apiOrigin}/api/v2/projects/${projectId}/visual-workbench`);
  expect(response.ok(), await response.text()).toBeTruthy();
  const state = await response.json() as VisualWorkbench;
  expect(state.reviewedKeyframes.find(item => item.id === source.binding.id)).toEqual(source.binding);
  expect(state.visualIntents.find(item => item.id === source.intent.id)).toEqual(source.intent);
  return state;
}
