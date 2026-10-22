import { expect, test } from "./fixture";
import { json } from "./f5a-fixture";
import { demoProject } from "../src/demo";

test("archived playback explains restoration instead of missing production", async ({ page, request, workbench }, info) => {
  const project = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, {
    headers: { "Idempotency-Key": `archived-play-${Date.now()}` },
    data: { brief: { ...demoProject.brief, title: "归档播放指引检查" } },
  }));
  const root = `${workbench.apiOrigin}/api/v2/projects/${project.id}`;
  const archived = await json(request.post(`${root}/archive`, {
    data: { expectedLifecycleRevision: project.lifecycleRevision },
  }));
  const writes: string[] = [];
  page.on("request", pending => {
    if (pending.url().includes("/api/v2/") && pending.method() !== "GET") writes.push(pending.method());
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&view=play`);
  await expect(page.getByRole("heading", { name: "项目已归档，暂不能播放故事" })).toBeVisible();
  await expect(page.getByText("原片、片段和审核记录仍保留，可返回工作台查看。", { exact: true })).toBeVisible();
  await expect(page.getByText("继续制作或播放前，请先在项目目录中恢复项目，再核对当前内容与播放片段。", { exact: true })).toBeVisible();
  await expect(page.getByTestId("branching-video-preview")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "前往分镜评审与制作" })).toHaveCount(0);
  for (const [width, height] of [[1700, 900], [1280, 768], [1280, 460]]) {
    await page.setViewportSize({ width, height });
    const bounds = await page.locator(".play-stage").boundingBox();
    expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`archived-play-${width}x${height}.png`) });
  }
  expect(writes).toEqual([]);
  await json(request.post(`${root}/restore`, { data: { expectedLifecycleRevision: archived.lifecycleRevision } }));
  await page.reload();
  await expect(page.getByRole("heading", { name: "故事尚未准备好" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "项目已归档，暂不能播放故事" })).toHaveCount(0);
  expect(writes).toEqual([]);
});
