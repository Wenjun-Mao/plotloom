import { expect, test } from "./fixture";
import { createAcceptedCastProject } from "./art-review-fixture";

test("owns a held branch cancellation across Source Brief Source remount", async ({ page, request, workbench }, info) => {
  const projectId = await createAcceptedCastProject(request, workbench.apiOrigin, "branch-remount");
  const base = `${workbench.apiOrigin}/api/v2/projects/${projectId}`;
  const preparation = await request.post(`${base}/branch-suggestions`);
  expect(preparation.ok()).toBe(true);
  const prepared = await preparation.json();
  expect(prepared.candidate.status).toBe("prepared");
  const sourceBefore = await (await request.get(`${base}/source-outline`)).json();
  const graphBefore = await (await request.get(`${base}/graph-workbench`)).json();
  const cancelPath = `/api/v2/projects/${projectId}/branch-suggestions/${prepared.candidate.jobId}/cancel`;
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let mutations = 0;
  await page.route(`**${cancelPath}`, async route => { mutations++; await gate; await route.continue(); });
  try {
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
    const panel = page.getByRole("region", { name: "助手剧情分支建议", exact: true });
    const cancel = panel.getByRole("button", { name: "放弃此建议任务", exact: true });
    await cancel.click();
    await expect.poll(() => mutations).toBe(1);
    await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
    await page.getByRole("button", { name: "返回来源与大纲", exact: true }).click();
    await expect(cancel).toBeDisabled();
    const capture = async (state: string) => {
      for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
        await page.setViewportSize({ width, height });
        await panel.evaluate(element => { element.scrollIntoView({ block: "start" }); window.scrollBy(0, -80); });
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
        await page.screenshot({ path: info.outputPath(`${state}-${width}x${height}.png`) });
      }
    };
    await capture("remounted-pending");
    release();
    await expect(cancel).toHaveCount(0);
    await expect(panel.getByRole("button", { name: "准备剧情分支建议", exact: true })).toBeEnabled();
    expect(mutations).toBe(1);
    const cancelled = await (await request.get(`${base}/branch-suggestions`)).json();
    expect(cancelled.candidate.status).toBe("cancelled");
    expect(cancelled.candidate.jobId).toBe(prepared.candidate.jobId);
    expect(await (await request.get(`${base}/source-outline`)).json()).toEqual(sourceBefore);
    expect(await (await request.get(`${base}/graph-workbench`)).json()).toEqual(graphBefore);
    await capture("remounted-cancelled");
  } finally { release(); }
});

for (const lifecycle of ["close", "snapshots"] as const) {
  test(`${lifecycle} joins branch cancellation without suspended-read deadlock`, async ({ page, request, workbench }) => {
    const projectId = await createAcceptedCastProject(request, workbench.apiOrigin, `branch-${lifecycle}`);
    const base = `${workbench.apiOrigin}/api/v2/projects/${projectId}`;
    const preparation = await request.post(`${base}/branch-suggestions`);
    expect(preparation.ok()).toBe(true);
    const prepared = await preparation.json();
    expect(prepared.candidate.status).toBe("prepared");
    const cancelPath = `/api/v2/projects/${projectId}/branch-suggestions/${prepared.candidate.jobId}/cancel`;
    let release!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    let mutationStarted = false;
    let lifecycleRequests = 0;
    await page.route(`**${cancelPath}`, async route => { mutationStarted = true; await gate; await route.continue(); });
    page.on("request", req => { if (req.method() === "POST" && new URL(req.url()).pathname === `/api/v2/projects/${projectId}/${lifecycle}`) lifecycleRequests++; });
    try {
      await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
      const panel = page.getByRole("region", { name: "助手剧情分支建议", exact: true });
      await panel.getByRole("button", { name: "放弃此建议任务", exact: true }).click();
      await expect.poll(() => mutationStarted).toBe(true);
      await page.getByRole("button", { name: lifecycle === "close" ? "保存并关闭项目" : "创建恢复快照", exact: true }).click();
      await expect(page.getByText(lifecycle === "close" ? "正在关闭项目" : "正在创建恢复快照", { exact: true })).toBeVisible();
      expect(lifecycleRequests).toBe(0);
      const acknowledgment = page.waitForResponse(response => response.request().method() === "POST" && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/${lifecycle}`);
      release();
      expect((await acknowledgment).ok()).toBe(true);
      expect(lifecycleRequests).toBe(1);
      if (lifecycle === "snapshots") {
        await expect(page.getByRole("status").filter({ hasText: "恢复快照已完成" })).toBeVisible();
        await expect(panel.getByRole("button", { name: "准备剧情分支建议", exact: true })).toBeEnabled();
      } else await expect(page.getByRole("button", { name: "新建空白项目", exact: true })).toBeVisible();
    } finally { release(); }
  });
}
