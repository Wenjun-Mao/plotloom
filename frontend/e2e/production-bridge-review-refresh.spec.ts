import { expect, test } from "./fixture";
import { changeScript, createScriptProject, endpoint, json, prepare, refresh, writeDelivery } from "./f5a-fixture";

test("mounted Storyboard replacement requalifies the production bridge without reloading", async ({ page, request, workbench }, testInfo) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "mounted-bridge-review");
  const reviewUrl = endpoint(workbench.apiOrigin, id);
  const first = await json(request.post(`${reviewUrl}/candidates`));
  await writeDelivery(first);
  await json(request.post(`${reviewUrl}/candidates/${first.jobId}/refresh`));
  await json(request.post(`${reviewUrl}/accept`, { data: { jobId: first.jobId, expectedReviewRevision: 0, binding: first.binding } }));
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const panel = page.getByTestId("storyboard-review"), bridge = page.getByTestId("production-bridge");
  await expect(bridge.getByRole("button", { name: "准备投产提案", exact: true })).toBeEnabled();
  // Retain the actual mounted panel identity through upstream invalidation and acceptance.
  await bridge.evaluate(element => { element.setAttribute("data-mount-proof", "retained"); });
  await changeScript(request, workbench.apiOrigin, id);
  await page.getByRole("button", { name: "刷新服务器版本", exact: true }).click();
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("上下文已过期");
  await expect(bridge.getByRole("button", { name: "准备投产提案", exact: true })).toBeDisabled();
  const next = await prepare(page, panel, id);
  await writeDelivery(next); await refresh(page, panel, id, next.jobId);
  await panel.getByRole("button", { name: "确认此分镜评审方案", exact: true }).click();
  await expect(panel).toContainText("已确认评审 r2");
  await expect(bridge).toHaveAttribute("data-mount-proof", "retained");
  await expect(bridge.getByRole("button", { name: "准备投产提案", exact: true })).toBeEnabled();
  const fresh = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/production-bridge`));
  expect(fresh.preparation.status).toBe("available");
  const sent = page.waitForRequest(r => r.method() === "POST" && r.url().endsWith(`/projects/${id}/production-bridge/proposals`));
  await bridge.getByRole("button", { name: "准备投产提案", exact: true }).click();
  expect((await sent).postDataJSON()).toEqual(fresh.preparation.request);
  await expect(bridge).toContainText("提案 r1");
  for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(viewport);
    await bridge.locator(":scope > header").scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
    await page.screenshot({ path: testInfo.outputPath(`mounted-bridge-${viewport.width}x${viewport.height}.png`) });
  }
});
