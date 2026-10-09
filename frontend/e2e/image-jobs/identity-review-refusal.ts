import type { APIRequestContext, Page, TestInfo } from "@playwright/test";
import { expect } from "../fixture";
import type { VisualWorkbench } from "../../src/types";

/** Real admission endpoints; offline generated-candidate fixture, not native media QA. */
export async function inspectIdentityReviewRefusal(
  page: Page, request: APIRequestContext, apiOrigin: string, projectId: string, info: TestInfo,
) {
  const url = `${apiOrigin}/api/v2/projects/${projectId}`;
  const media: VisualWorkbench = await request.get(`${url}/visual-workbench`).then(response => response.json());
  const binding = media.reviewedKeyframes[0];
  const verify = (body: Record<string, unknown>) => {
    expect(body).toMatchObject({ code: "same_person_review_required", shotId: binding.shotId, bindingId: binding.id });
    expect(body.message).toContain("无法确认身份时不要标记通过");
    expect(body.message).toContain("准备与参考 · 图片、角色、导入");
    expect(body.technicalMessage).toBe("identity-aware keyframe requires a current passing same-person review");
  };
  const production = page.locator("#video-production");
  if (await production.getAttribute("open") === null) await production.locator("summary").first().click();
  await page.getByLabel("H3 时长（已审核）").selectOption("8");
  await page.getByRole("radio", { name: "允许黑边画布（保留当前横幅构图）", exact: true }).check();
  const directions = page.getByTestId("h3-directions-review");
  if (await directions.getAttribute("open") === null) await directions.locator("summary").click();
  const panel = page.getByTestId("same-person-review-panel");
  const preparationDisclosure = page.locator("details.workbench-support").filter({ has: panel });
  await expect(preparationDisclosure.locator("summary").first()).toHaveText("准备与参考 · 图片、角色、导入");
  for (const state of ["missing", "failed"] as const) {
    if (state === "failed") {
      await panel.getByLabel("身份对比说明").fill("Fixture cannot establish the subject identity.");
      await panel.getByLabel("镜头状态说明").fill("Shot state is separate from identity.");
      await panel.getByLabel("复核备注").fill("Explicit failed review; never authorize generation.");
      await panel.getByTestId("same-person-judgment-char_ruanxing").selectOption("fail");
      const saved = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/same-person-reviews"));
      await panel.getByTestId("record-same-person-review").click();
      expect((await saved).status()).toBe(201);
      await expect(panel).toContainText("未通过或已过期的复核");
    }
    const response = page.waitForResponse(item => item.request().method() === "POST" && item.url().endsWith("/video-jobs/prompt-preview"));
    await directions.getByRole("button", { name: "读取当前来源", exact: true }).click();
    const refused = await response;
    expect(refused.status()).toBe(409);
    verify(await refused.json());
    const videoRequest = refused.request().postDataJSON();
    const preparation = await request.post(`${url}/video-jobs`, { data: videoRequest });
    expect(preparation.status()).toBe(409);
    verify(await preparation.json());
    const notice = directions.getByRole("alert");
    await expect(notice).toContainText("跨镜头同一人物视觉复核");
    await expect(directions.getByRole("button", { name: "冻结此说明并准备原片" })).toHaveCount(0);
    if (state === "failed") {
      for (const size of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
        await page.setViewportSize(size);
        await notice.scrollIntoViewIfNeeded();
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
        await page.screenshot({ path: info.outputPath(`identity-refusal-${size.width}x${size.height}.png`) });
      }
    }
    await page.getByTestId("preview-subset-length").selectOption("1");
    await expect(page.getByTestId("create-still-preview")).toBeDisabled();
    const stillRefused = await request.post(`${url}/still-previews`, { data: {
      sceneId: binding.sceneId, shotIds: [binding.shotId],
      expectedSelectionRevision: media.selectionRevision,
      storyboardRevision: videoRequest.storyboardRevision, approvalId: videoRequest.approvalId,
    } });
    expect(stillRefused.status(), await stillRefused.text()).toBe(409);
    verify(await stillRefused.json());
    expect((await request.get(`${url}/video-jobs`).then(item => item.json())).jobs).toEqual([]);
    expect((await request.get(`${url}/still-previews`).then(item => item.json())).previews).toEqual([]);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
}
