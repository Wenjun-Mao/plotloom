import { test, expect } from "./fixture";

test("new incomplete A/B resumes automatically after leave and owned backend restart", async ({ page, browser, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目", exact: true }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const a = new URL(page.url()).searchParams.get("project")!;
  await page.getByLabel("片名", { exact: true }).fill("unfinished A");
  await page.getByRole("spinbutton", { name: "目标游玩时长（秒）", exact: true }).fill("");
  await expect.poll(async () => {
    const response = await fetch(`${workbench.apiOrigin}/api/v2/projects/${a}/authoring-drafts`);
    return (await response.json())[0]?.payload.targetPlaythroughSeconds;
  }).toBe("");
  await page.getByRole("button", { name: "返回首页", exact: true }).click();
  await page.getByRole("button", { name: "创建空白项目", exact: true }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const b = new URL(page.url()).searchParams.get("project")!;
  expect(b).not.toBe(a);
  await page.getByLabel("片名", { exact: true }).fill("unfinished B");
  await page.getByRole("button", { name: "返回首页", exact: true }).click();
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${a}&stage=brief`);
  await expect(page.getByLabel("片名", { exact: true })).toHaveValue("unfinished A");
  await expect(page.getByRole("spinbutton", { name: "目标游玩时长（秒）", exact: true })).toHaveValue("");
  await workbench.restartBackend();
  const context = await browser.newContext();
  const fresh = await context.newPage();
  await fresh.goto(`${workbench.frontendOrigin}/v2/?project=${a}&stage=brief`);
  await expect(fresh.getByLabel("片名", { exact: true })).toHaveValue("unfinished A");
  await expect(fresh.getByRole("spinbutton", { name: "目标游玩时长（秒）", exact: true })).toHaveValue("");
  const project = await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${a}`)).json();
  expect(project.brief).toBeNull();
  expect((await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${a}/runs`)).json()).runs).toEqual([]);
  const status = await (await fetch(`${workbench.providerOrigin}/control/status`)).json();
  expect(status.requests ?? []).toEqual([]);
  await context.close();
});
