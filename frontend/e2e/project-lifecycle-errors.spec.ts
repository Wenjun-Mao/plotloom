import type { APIRequestContext, Page } from "@playwright/test";
import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";

const row = (page: Page, id: string) => page.locator(`.directory-item[data-project-id="${id}"]`);
const busyMessage = "项目仍有读取、写入或后台任务占用";

async function create(request: APIRequestContext, origin: string, title: string) {
  const response = await request.post(`${origin}/api/v2/projects`, {
    data: { brief: { ...demoProject.brief, title }, initialStages: [] },
  });
  expect(response.status()).toBe(201);
  return await response.json() as { id: string; brief: { title: string } };
}

async function openDirectory(page: Page) {
  await page.getByRole("button", { name: /当前项目 · 切换/ }).click();
  await expect(page.getByRole("dialog", { name: "项目目录" })).toBeVisible();
}

for (const action of ["archive", "restore"] as const) {
  test(`${action} retries retire the previous command error, not on reads or cancelled confirmation`, async ({ page, request, workbench }) => {
    const target = await create(request, workbench.apiOrigin, `目录重试-${action}`);
    if (action === "restore") {
      expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${target.id}/archive`, {
        data: { expectedLifecycleRevision: 1 },
      })).ok()).toBeTruthy();
    }
    const current = await create(request, workbench.apiOrigin, "保留当前项目");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${current.id}&stage=brief`);
    await expect(page.getByLabel("片名")).toHaveValue(current.brief.title);
    await openDirectory(page);
    await page.getByLabel("显示归档项目").check();

    let attempts = 0;
    let release!: () => void;
    let started!: () => void;
    const held = new Promise<void>(resolve => { release = resolve; });
    const retryStarted = new Promise<void>(resolve => { started = resolve; });
    await page.route(`**/api/v2/projects/${target.id}/${action}`, async route => {
      attempts += 1;
      if (attempts === 1) {
        await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ code: "project_busy", message: "held project" }) });
        return;
      }
      started();
      await held;
      await route.continue();
    });
    const command = row(page, target.id).getByRole("button", { name: action === "archive" ? "归档" : "恢复", exact: true });
    const previousError = page.getByRole("alert").filter({ hasText: busyMessage });
    try {
      await command.click();
      await expect(previousError).toBeVisible();
      await page.getByLabel("显示归档项目").uncheck();
      await page.getByLabel("显示归档项目").check();
      await expect(previousError).toBeVisible();
      for (const title of ["复制简报与规范内容", "永久删除"] as const) {
        await row(page, target.id).getByRole("button", { name: title, exact: true }).click();
        await page.getByRole("alertdialog").getByRole("button", { name: "取消", exact: true }).click();
        await expect(previousError).toBeVisible();
      }
      await command.click();
      await retryStarted;
      // A real new command owns the banner even before its response settles.
      await expect(previousError).toHaveCount(0);
      release();
      await expect(row(page, target.id)).toContainText(action === "archive" ? "已归档 · 只读" : "可打开");
      await expect(previousError).toHaveCount(0);
      expect(attempts).toBe(2);
      await expect(page).toHaveURL(new RegExp(`project=${current.id}`));
    } finally { release(); }
  });
}

test("only a confirmed delete retry clears its previous error and erases its disposable target", async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, "删除重试目标");
  const current = await create(request, workbench.apiOrigin, "另一个保留项目");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${current.id}&stage=brief`);
  await expect(page.getByLabel("片名")).toHaveValue(current.brief.title);
  await openDirectory(page);
  let attempts = 0;
  await page.route(`**/api/v2/projects/${target.id}/permanent-delete`, async route => {
    if (++attempts === 1) {
      await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ code: "project_busy", message: "held project" }) });
    } else await route.continue();
  });
  const consent = page.getByRole("alertdialog", { name: "永久删除项目" });
  const openConsent = async () => {
    await row(page, target.id).getByRole("button", { name: "永久删除", exact: true }).click();
    await expect(consent).toBeVisible();
  };
  const confirm = async () => {
    await consent.getByLabel("输入完整片名以确认删除").fill(target.brief.title);
    await consent.getByRole("button", { name: "确认永久删除项目", exact: true }).click();
  };
  await openConsent(); await confirm();
  const previousError = page.getByRole("alert").filter({ hasText: busyMessage });
  await expect(previousError).toBeVisible();
  await openConsent();
  await consent.getByRole("button", { name: "取消", exact: true }).click();
  await expect(previousError).toBeVisible();
  expect(attempts).toBe(1);
  await openConsent(); await confirm();
  await expect(row(page, target.id)).toHaveCount(0);
  await expect(previousError).toHaveCount(0);
  expect(attempts).toBe(2);
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`)).status()).toBe(404);
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${current.id}`)).ok()).toBeTruthy();
});

test("an unavailable folder-open command does not erase a previous failure", async ({ page, request, workbench }) => {
  const closed = await create(request, workbench.apiOrigin, "不可重新打开的目标");
  expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${closed.id}/close`)).ok()).toBeTruthy();
  const target = await create(request, workbench.apiOrigin, "保留失败反馈");
  await page.route("**/api/v2/runtime-capabilities", async route => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...await response.json(), explicitProjectClose: false } });
  });
  await page.route(`**/api/v2/projects/${target.id}/archive`, route => route.fulfill({
    status: 409, json: { code: "project_busy", message: "held project" },
  }));
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=brief`);
  await expect(page.getByLabel("片名")).toHaveValue(target.brief.title);
  await openDirectory(page);
  await row(page, target.id).getByRole("button", { name: "归档", exact: true }).click();
  const previousError = page.getByRole("alert").filter({ hasText: busyMessage });
  await expect(previousError).toBeVisible();
  let opens = 0;
  page.on("request", req => { if (req.url().endsWith(`/projects/${closed.id}/open`)) opens += 1; });
  await row(page, closed.id).getByRole("button", { name: "重新打开", exact: true }).click();
  await expect(previousError).toBeVisible();
  expect(opens).toBe(0);
  await expect(page).toHaveURL(new RegExp(`project=${target.id}`));
});
