import { expect, test } from "./fixture";
import { createAcceptedCastProject } from "./art-review-fixture";

test("reads clean errors and cancels a stale branch task without replacing source or graph", async ({ page, request, workbench }, info) => {
  const projectId = await createAcceptedCastProject(request, workbench.apiOrigin, "branch-recovery");
  const base = `${workbench.apiOrigin}/api/v2/projects/${projectId}`;
  const branchUrl = `**/api/v2/projects/${projectId}/branch-suggestions`;
  await page.route(branchUrl, route => route.request().method() === "GET"
    ? route.fulfill({ status: 503, json: { detail: "服务暂不可用，请稍后重试。" } }) : route.continue());
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
  const panel = page.getByRole("region", { name: "助手剧情分支建议", exact: true });
  await expect(panel.getByRole("alert")).toContainText("服务请求失败（HTTP 503）");
  await expect(panel).not.toContainText("ApiError:");
  const capture = async (state: string, target = panel) => {
    for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
      await page.setViewportSize({ width, height });
      await target.evaluate(el => { el.scrollIntoView({ block: "start" }); window.scrollBy(0, -80); });
      await expect(target).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await page.screenshot({ path: info.outputPath(`${state}-${width}x${height}.png`) });
    }
  };
  await capture("failed-read");
  await page.unroute(branchUrl);
  await panel.getByRole("button", { name: "重试读取建议", exact: true }).click();
  await panel.getByRole("button", { name: "准备剧情分支建议", exact: true }).click();
  await expect(panel.getByRole("button", { name: "放弃此建议任务", exact: true })).toBeEnabled();
  const prepared = await (await request.get(`${base}/branch-suggestions`)).json();
  expect(prepared.candidate.status).toBe("prepared");
  expect(prepared.staleReasons).toEqual([]);

  await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
  await page.getByLabel("类型细节（可选）", { exact: false }).fill("分支建议准备后，改为悬疑故事。");
  const saved = page.waitForResponse(response => response.request().method() === "PATCH" && new URL(response.url()).pathname === `/api/v2/projects/${projectId}`);
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  expect((await saved).ok()).toBe(true);
  await page.getByRole("button", { name: "返回来源与大纲", exact: true }).click();
  await expect(panel.locator(".notice.warning")).toContainText("简报");
  const sourceBefore = await (await request.get(`${base}/source-outline`)).json();
  const localSource = `${sourceBefore.source.material.text} 尚未保存的本地补充。`;
  await page.getByLabel("故事内容", { exact: false }).fill(localSource);
  await expect(panel.getByRole("button", { name: "放弃此建议任务", exact: true })).toBeEnabled();
  await capture("stale-cancellable");
  await capture("stale-cancel-controls", panel.getByRole("button", { name: "放弃此建议任务", exact: true }));
  // Source text has its own draft owner; cancellation must not change the graph.
  const graphBefore = await (await request.get(`${base}/graph-workbench`)).json();
  const writes: string[] = [];
  const record = (req: import("@playwright/test").Request) => {
    if (req.method() === "POST" && req.url().includes("/branch-suggestions")) writes.push(new URL(req.url()).pathname);
  };
  page.on("request", record);
  await panel.getByRole("button", { name: "放弃此建议任务", exact: true }).click();
  await expect(panel.getByRole("button", { name: "准备剧情分支建议", exact: true })).toBeDisabled();
  page.off("request", record);
  expect(writes).toEqual([`/api/v2/projects/${projectId}/branch-suggestions/${prepared.candidate.jobId}/cancel`]);
  const cancelled = await (await request.get(`${base}/branch-suggestions`)).json();
  expect(cancelled.candidate.status).toBe("cancelled");
  expect(cancelled.candidate.jobId).toBe(prepared.candidate.jobId);
  expect(await (await request.get(`${base}/source-outline`)).json()).toEqual(sourceBefore);
  expect(await (await request.get(`${base}/graph-workbench`)).json()).toEqual(graphBefore);
  await expect(page.getByLabel("故事内容", { exact: false })).toHaveValue(localSource);
  await capture("cancelled-draft-retained");
});
