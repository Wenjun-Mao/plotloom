import { execFileSync } from "node:child_process";
import path from "node:path";
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

test("an optional review pauses production authority and cancellation restores it without rebuilding", async ({ page, request, workbench }, info) => {
  test.setTimeout(120_000);
  const id = execFileSync("uv", ["run", "python", "-m", "frontend.e2e.fixtures.bridge_handoff_project", "--outputs", workbench.outputsRoot, "--application", workbench.applicationDataRoot], {
    cwd: path.resolve(".."), encoding: "utf8",
  }).trim();
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const before = await json(request.get(`${root}/production-bridge`));
  const stages = await json(request.get(`${root}/stages`));
  const reviewBefore = await json(request.get(`${root}/storyboard-source-review`));
  const writes: string[] = [];
  page.on("request", req => { if (req.url().includes("/api/v2/") && req.method() !== "GET") writes.push(new URL(req.url()).pathname); });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const review = page.getByTestId("storyboard-review"), installed = page.getByTestId("installed-production");
  const bridge = page.getByTestId("production-bridge");
  await expect(installed).toContainText("当前有效");
  await bridge.evaluate(element => element.setAttribute("data-mount-proof", "retained"));
  await review.getByRole("button", { name: "准备分镜任务", exact: true }).click();
  await expect(installed).toContainText("分镜评审待确认");
  await expect(bridge.locator(":scope > header strong")).toHaveText("分镜评审待确认");
  await expect(installed).not.toContainText("需要重建");
  await expect(bridge).not.toContainText("故事来源或制作版本已变化");
  await expect(bridge.getByRole("button", { name: "准备重建提案", exact: true })).toBeDisabled();
  await expect(bridge.getByRole("button", { name: "继续：打开第一个镜头", exact: true })).toHaveCount(0);
  const paused = await json(request.get(`${root}/production-bridge`));
  expect(paused.installation.status).toBe("outdated");
  expect(paused.installation.admissionId).toBe(before.installation.admissionId);
  expect(paused.installation.cuts).toEqual(before.installation.cuts);
  expect(await json(request.get(`${root}/stages`))).toEqual(stages);
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    await installed.scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath(`installed-review-paused-${width}x${height}.png`) });
  }
  await review.getByRole("button", { name: "取消此任务", exact: true }).click();
  await expect(installed).toContainText("当前有效");
  await expect(bridge).toHaveAttribute("data-mount-proof", "retained");
  expect(await json(request.get(`${root}/production-bridge`))).toEqual(before);
  expect(await json(request.get(`${root}/stages`))).toEqual(stages);
  expect((await json(request.get(`${root}/storyboard-source-review`))).acceptedReview).toEqual(reviewBefore.acceptedReview);
  expect(writes).toHaveLength(2);
  expect(writes[0]).toBe(`/api/v2/projects/${id}/storyboard-source-review/candidates`);
  expect(writes[1]).toMatch(new RegExp(`^/api/v2/projects/${id}/storyboard-source-review/candidates/[^/]+/cancel$`));
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    await installed.scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath(`installed-review-restored-${width}x${height}.png`) });
  }
});
