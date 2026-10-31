import type { APIRequestContext, Page, TestInfo } from "@playwright/test";
import { expect } from "../fixture";
import type { VisualWorkbench } from "../../src/types";
import { inspectUnassessableReview } from "./unassessable-review";

/** Real technical admission; optional observations never imply identity PASS. */
export async function inspectIdentityObservationEligibility(
  page: Page, request: APIRequestContext, apiOrigin: string, projectId: string, info: TestInfo,
) {
  const url = `${apiOrigin}/api/v2/projects/${projectId}`;
  const media: VisualWorkbench = await request.get(`${url}/visual-workbench`).then(response => response.json());
  const binding = media.reviewedKeyframes[0];
  const production = page.locator("#video-production");
  if (await production.getAttribute("open") === null) await production.locator("summary").first().click();
  await page.getByLabel("H3 时长（已审核）").selectOption("8");
  await page.getByRole("radio", { name: "允许黑边画布（完整保留已审核图）", exact: true }).check();
  const directions = page.getByTestId("h3-directions-review");
  if (await directions.getAttribute("open") === null) await directions.locator("summary").click();
  const panel = page.getByTestId("same-person-review-panel");
  await expect(panel.getByTestId("same-person-judgment-char_ruanxing")).toHaveValue("");
  await expect(panel.getByTestId("record-same-person-review")).toBeDisabled();
  let sourceBody: Record<string, unknown> = {};
  for (const state of ["missing", "failed"] as const) {
    if (state === "failed") {
      await panel.getByLabel("身份对比说明").fill("Fixture cannot establish the subject identity.");
      await panel.getByLabel("镜头状态说明").fill("Shot state is separate from identity.");
      await panel.getByLabel("复核备注").fill("Explicit failed observation; no identity pass or dispatch authority.");
      await panel.getByTestId("same-person-judgment-char_ruanxing").selectOption("fail");
      const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/same-person-reviews"));
      await panel.getByTestId("record-same-person-review").click();
      const response = await saved;
      expect(response.status()).toBe(201);
      expect(await response.json()).toMatchObject({ productionEligible: false, comparisons: [expect.objectContaining({ judgment: "fail" })] });
      await expect(panel).toContainText("此观察不决定视频生成或连续静帧预览的技术资格。");
    }
    const response = page.waitForResponse(item => item.request().method() === "POST" && item.url().endsWith("/video-jobs/prompt-preview"));
    await directions.getByRole("button", { name: "读取当前来源", exact: true }).click();
    const preview = await response;
    expect(preview.status(), await preview.text()).toBe(200);
    sourceBody = preview.request().postDataJSON();
    await page.getByTestId("preview-subset-length").selectOption("1");
    await expect(page.getByTestId("create-still-preview")).toBeEnabled();
    const still = await request.post(`${url}/still-previews`, { data: {
      sceneId: binding.sceneId, shotIds: [binding.shotId], expectedSelectionRevision: media.selectionRevision,
      storyboardRevision: sourceBody.storyboardRevision, approvalId: sourceBody.approvalId,
    } });
    expect(still.status(), await still.text()).toBe(201);
    expect((await still.json()).manifest.frames[0]).not.toHaveProperty("identityReviewId");
    expect((await request.get(`${url}/video-jobs`).then(item => item.json())).jobs).toEqual([]);
    if (state === "failed") for (const size of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
      await page.setViewportSize(size);
      await panel.scrollIntoViewIfNeeded();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
      await page.screenshot({ path: info.outputPath(`identity-observation-${size.width}x${size.height}.png`) });
    }
  }
  await inspectUnassessableReview(page, request, url, sourceBody, media, info);
  await page.setViewportSize({ width: 1440, height: 900 });
}
