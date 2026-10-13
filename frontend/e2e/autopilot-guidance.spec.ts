import { test, expect } from "./fixture";
import { createScriptProject, json } from "./f5a-fixture";
import { fixtureRun } from "../tests/autopilot-fixture";

test("actual stage workspaces distinguish automatic ownership while keeping manual controls and read-only reports", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "automatic-guidance");
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const [source, cast, art, script] = await Promise.all([json(request.get(`${root}/source-outline`)), json(request.get(`${root}/cast`)), json(request.get(`${root}/art`)), json(request.get(`${root}/script`))]);
  // Presentation-only actor fixture: real retained stage reads/report routes,
  // no synthetic canonical mutation or native dispatch from the browser.
  await page.route(`**/api/v2/projects/${id}/autopilot`, route => route.fulfill({ json: {
    ...fixtureRun, projectId: id, state: "running", phase: "art", checkpoints: [
      ["outline", source.acceptedOutline], ["characters", cast.acceptedCast], ["art", art.acceptedArt], ["script", script.acceptedScript],
    ].map(([operationKey, value]) => ({ operationKey, state: "adopted", evidence: { owner: operationKey,
      result: { revision: value.revision, contentHash: value.contentHash } } })),
  } }));
  const writes: string[] = [];
  page.on("request", req => { if (["POST", "PUT", "PATCH", "DELETE"].includes(req.method())) writes.push(req.url()); });
  const guide = page.getByTestId("recommended-workflow").locator(".recommended-workflow-next");
  for (const target of ["source#source", "characters", "source#art", "source#script"]) {
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=${target}`);
    await expect(guide).toContainText("当前自动阶段：美术设定");
    await expect(guide).toContainText("保存手动修改将接管自动运行");
    const stageGuide = page.locator(".stage-guide-content:visible").first();
    await expect(stageGuide).toContainText("一次完整人工审阅");
    await expect(stageGuide).not.toContainText("下一步准备");
    if (target === "source#source") {
      const open = page.getByRole("button", { name: "阅读AI 已采用大纲", exact: true });
      await expect(open).toBeEnabled(); await open.click();
      const report = page.getByRole("dialog");
      await expect(report.getByRole("heading")).toContainText(`AI 已采用大纲 r${source.acceptedOutline.revision}`);
      await expect(report).toContainText("阅读与关闭不会确认、接管");
      await page.getByRole("button", { name: "关闭阅读" }).click();
      await expect(page.getByRole("button", { name: "确认改编内容", exact: true })).toBeEnabled();
    }
    if (target === "characters") {
      await expect(page.getByRole("button", { name: "编辑角色设定", exact: true })).toBeEnabled();
      const gallery = page.getByTestId("character-reference-gallery");
      await expect(gallery.locator(".reference-gallery-cast-state strong")).toHaveText(`AI 已采用角色设定 r${cast.acceptedCast.revision}`);
      await expect(gallery.getByRole("navigation", { name: "角色主体" })).toContainText("设定中的角色");
      await expect(gallery.getByRole("navigation", { name: "角色主体" })).not.toContainText("已确认角色");
      for (const height of [900, 600]) {
        await page.setViewportSize({ width: 1440, height });
        await gallery.locator(".reference-gallery-intro").scrollIntoViewIfNeeded();
        await page.screenshot({ path: `../.local/native97-repair/pixels/native97-repair-character-${height}.png` });
      }
      await page.setViewportSize({ width: 1440, height: 900 });
    }
    if (target === "source#art") {
      const gallery = page.getByTestId("art-reference-studies");
      await expect(gallery.locator("header strong").first()).toHaveText("按AI 已采用的美术设定生成图片");
      await gallery.locator("header").first().scrollIntoViewIfNeeded();
      await page.screenshot({ path: "../.local/native97-repair/pixels/native97-repair-art-900.png" });
    }
  }
  // Observe admitted first-frame work before selection; this is an actor fixture,
  // with actual retained stage reads and no preparation or dispatch from navigation.
  await page.unroute(`**/api/v2/projects/${id}/autopilot`);
  await page.route(`**/api/v2/projects/${id}/autopilot`, route => route.fulfill({ json: { ...fixtureRun, projectId: id, state: "waiting", phase: "first-frames", frames: [], checkpoints: [] } }));
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=characters`);
  await expect(guide).toContainText("当前自动阶段：镜头首帧");
  await expect(page.getByTestId("character-reference-gallery").locator(".reference-gallery-cast-state strong")).toContainText("来源待核实");
  await page.screenshot({ path: "../.local/native97-repair/pixels/native97-repair-phase.png", fullPage: false });
  expect(writes).toEqual([]);
  expect(await json(request.get(`${root}/autopilot`))).toBeNull();
});
