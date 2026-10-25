import { openProjectManagement } from "./project-directory-controls";
import { expect, checkedStaticTest as test } from "./fixture";
import { demoProject } from "../src/demo";

for (const [width, height] of [[1280, 768], [1280, 460], [1700, 900]]) {
  test(`state-aware directory actions stay reachable at ${width}x${height}`, async ({ page, request, workbench }, testInfo) => {
    await page.setViewportSize({ width, height });
    const create = async (title: string) => {
      const response = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title }, initialStages: [] } });
      expect(response.status()).toBe(201); return (await response.json()).id as string;
    };
    const current = await create("当前项目 A"), other = await create("其他项目 B");
    const dispatches: string[] = [];
    page.on("request", req => { if (req.method() === "POST" && /\/(runs|generate|dispatch|launch)$/.test(new URL(req.url()).pathname)) dispatches.push(req.url()); });
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${current}&stage=brief`);
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    const directory = page.getByRole("dialog", { name: "项目目录" });
    const a = directory.locator(`[data-project-id="${current}"]`), b = directory.locator(`[data-project-id="${other}"]`);
    await expect(a.getByRole("button", { name: "保存并关闭项目", exact: true })).toHaveCount(0);
    await expect(a.getByRole("button", { name: "退出工作区", exact: true })).toHaveCount(0);
    await expect(a).not.toContainText("未关闭");
    await expect(b.getByRole("button", { name: "保存并关闭项目", exact: true })).toHaveCount(0);
    await expect(b.getByRole("button", { name: "退出工作区", exact: true })).toHaveCount(0);
    await expect(b.getByRole("button", { name: "打开", exact: true })).toBeVisible();
    const more = b.getByRole("button", { name: "更多 · 其他项目 B", exact: true });
    await more.focus(); await page.keyboard.press("Enter");
    await expect(more).toHaveAttribute("aria-expanded", "true");
    const deletion = b.getByRole("button", { name: "删除项目…", exact: true });
    await deletion.scrollIntoViewIfNeeded(); await expect(deletion).toBeInViewport();
    await page.screenshot({ path: testInfo.outputPath(`directory-more-${width}x${height}.png`) });
    await page.keyboard.press("Escape");
    await expect(more).toHaveAttribute("aria-expanded", "false"); await expect(more).toBeFocused(); await expect(directory).toBeVisible();
    await more.click(); await directory.getByRole("heading", { name: "项目目录" }).click();
    await expect(more).toHaveAttribute("aria-expanded", "false");
    await more.click();
    const close = page.waitForResponse(response => response.url().endsWith(`/${other}/freeze`) && response.request().method() === "POST");
    await b.getByRole("button", { name: "冻结项目", exact: true }).click(); expect((await close).ok()).toBeTruthy();
    await expect(b).toContainText("已冻结"); await expect(more).toBeFocused(); await expect(page).toHaveURL(new RegExp(`project=${current}`));
    const reopen = page.waitForResponse(response => response.url().endsWith(`/${other}/unfreeze`) && response.request().method() === "POST");
    await openProjectManagement(b); await b.getByRole("button", { name: "解除冻结", exact: true }).click(); expect((await reopen).ok()).toBeTruthy();
    await expect(page).toHaveURL(new RegExp(`project=${current}`));
    await b.getByRole("button", { name: "打开", exact: true }).click();
    await expect(directory).toBeHidden(); await expect(page).toHaveURL(new RegExp(`project=${other}`));
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    await expect(b.getByRole("button", { name: "更多 · 其他项目 B" })).toHaveAttribute("aria-expanded", "false");
    await a.getByRole("button", { name: "打开", exact: true }).click();
    await expect(directory).toBeHidden(); await expect(page).toHaveURL(new RegExp(`project=${current}`));
    expect(dispatches).toEqual([]);
    expect((await (await request.get(`${workbench.providerOrigin}/control/status`)).json()).totalRequests).toBe(0);
  });
}

test("archived closed projects restore before reopening", async ({ page, request, workbench }) => {
  const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title: "归档且关闭" }, initialStages: [] } });
  expect(created.status()).toBe(201); const project = await created.json();
  expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${project.id}/freeze`)).ok()).toBeTruthy();
  expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${project.id}/archive`, { data: { expectedLifecycleRevision: project.lifecycleRevision } })).ok()).toBeTruthy();
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开项目目录" }).click();
  const directory = page.getByRole("dialog", { name: "项目目录" });
  await directory.getByLabel("显示归档项目").check();
  const row = directory.locator(`[data-project-id="${project.id}"]`);
  await expect(row).toContainText("已归档 · 只读");
  await expect(row.locator(".directory-open")).toBeEnabled();
  await expect(row.getByRole("button", { name: "重新打开", exact: true })).toHaveCount(0);
  await row.getByRole("button", { name: "恢复", exact: true }).click();
  await expect(row).toContainText("已冻结");
  await openProjectManagement(row); await row.getByRole("button", { name: "解除冻结", exact: true }).click();
  await row.locator(".directory-open").click();
  await expect(directory).toBeHidden(); await expect(page).toHaveURL(new RegExp(`project=${project.id}`));
  await expect(page.locator(".project-switcher")).toContainText("归档且关闭");

});

test("archived closed titles require Restore even when explicit Reopen capability is unavailable", async ({ page, request, workbench }) => {
  const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title: "归档关闭且无重开能力" }, initialStages: [] } });
  expect(created.status()).toBe(201); const project = await created.json();
  expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${project.id}/freeze`)).ok()).toBeTruthy();
  expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${project.id}/archive`, { data: { expectedLifecycleRevision: project.lifecycleRevision } })).ok()).toBeTruthy();
  await page.route("**/api/v2/runtime-capabilities", async route => {
    const response = await route.fetch(); await route.fulfill({ response, json: { ...await response.json(), explicitProjectClose: false } });
  });
  let opens = 0;
  page.on("request", sent => { if (sent.url().endsWith(`/${project.id}/unfreeze`)) opens++; });
  await page.goto(`${workbench.frontendOrigin}/v2/`); await page.getByRole("button", { name: "打开项目目录", exact: true }).click();
  const directory = page.getByRole("dialog", { name: "项目目录" }); await directory.getByLabel("显示归档项目").check();
  const row = directory.locator(`[data-project-id="${project.id}"]`);
  await expect(row.locator(".directory-open")).toBeEnabled();
  await row.getByRole("button", { name: "恢复", exact: true }).click();
  await expect(row).not.toContainText("已归档");
  await openProjectManagement(row); await expect(row.getByRole("button", { name: /^更多/ })).toHaveAttribute("aria-expanded", "true");
  await expect(row.getByRole("button", { name: "解除冻结", exact: true })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await row.getByRole("button", { name: "打开", exact: true }).click(); await expect(directory).toBeHidden();
  await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
  await expect(page.getByLabel("片名", { exact: true })).toBeDisabled();
  expect(opens).toBe(0);
});

test("current archived open project keeps read-only title access and Restore without workspace exit", async ({ page, request, workbench }) => {
  const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title: "当前归档只读项目" }, initialStages: [] } });
  expect(created.status()).toBe(201); const project = await created.json();
  expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${project.id}/archive`, { data: { expectedLifecycleRevision: project.lifecycleRevision } })).ok()).toBeTruthy();
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${project.id}&stage=brief`);
  await expect(page.getByText("归档只读", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const directory = page.getByRole("dialog", { name: "项目目录" }); await directory.getByLabel("显示归档项目").check();
  const row = directory.locator(`[data-project-id="${project.id}"]`);
  await expect(row.getByRole("button", { name: "恢复", exact: true })).toBeVisible();
  await expect(row.getByRole("button", { name: "退出工作区", exact: true })).toHaveCount(0);
  await expect(row.locator(".directory-open")).toBeEnabled();
  await row.locator(".directory-open").click(); await expect(directory).toBeHidden();
  await expect(page.getByText("归档只读", { exact: true })).toBeVisible();
});

test("two-row keyboard focus keeps internal Tab navigation and gives Escape to the focused disclosure", async ({ page, request, workbench }) => {
  const create = async (title: string) => {
    const response = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title }, initialStages: [] } });
    expect(response.status()).toBe(201); return (await response.json()).id as string;
  };
  const current = await create("键盘项目 A"); await create("键盘项目 B");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${current}&stage=brief`);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const directory = page.getByRole("dialog", { name: "项目目录" });
  const rows = directory.locator(".directory-item"); await expect(rows).toHaveCount(2);
  const a = rows.nth(0), b = rows.nth(1), moreA = a.getByRole("button", { name: /^更多 · / }), moreB = b.getByRole("button", { name: /^更多 · / });
  await moreA.focus(); await page.keyboard.press("Enter");
  await page.keyboard.press("Tab"); await expect(a.getByRole("button", { name: "复制简报与规范内容", exact: true })).toBeFocused();
  await expect(moreA).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Tab"); await expect(a.getByRole("button", { name: "冻结项目", exact: true })).toBeFocused();
  await page.keyboard.press("Tab"); await expect(a.getByRole("button", { name: "归档", exact: true })).toBeFocused();
  await expect(moreA).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Tab"); await expect(a.getByRole("button", { name: "删除项目…", exact: true })).toBeFocused();
  await page.keyboard.press("Tab"); await expect(b.locator(".directory-open")).toBeFocused();
  await expect(moreA).toHaveAttribute("aria-expanded", "false");
  for (let step = 0; step < 4 && !await moreB.evaluate(element => element === document.activeElement); step++) await page.keyboard.press("Tab");
  await expect(moreB).toBeFocused(); await page.keyboard.press("Enter"); await expect(moreB).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(moreB).toHaveAttribute("aria-expanded", "false"); await expect(moreB).toBeFocused();
  await expect(moreA).toHaveAttribute("aria-expanded", "false"); await expect(directory).toBeVisible();
});
