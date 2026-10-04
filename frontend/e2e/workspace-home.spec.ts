import { expect, test } from "./fixture";
import type { ProjectListResponse } from "../src/types";

for (const start of ["创建空白项目", "打开示例项目"]) {
  test(`Home returns a clean ${start} workspace to onboarding by keyboard`, async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: start, exact: true }).click();
    const home = page.getByRole("button", { name: "返回首页", exact: true });
    await expect(home).toContainText("首页");
    await home.focus();
    await home.press("Enter");
    await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
    await expect(page).toHaveURL(/\/v2\/\?stage=brief$/);
    await expect(page.getByRole("button", { name: "打开项目目录", exact: true })).toBeVisible();
  });
}

test("Home protects an unsaved blank Brief with Cancel and explicit Save", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目", exact: true }).click();
  await page.getByLabel("片名").fill("回家前留住的故事");
  await page.getByRole("textbox", { name: "故事梗概", exact: true }).fill("一个女孩发现一架带有陌生地址的纸飞机，决定找到它的主人。");
  await page.getByRole("button", { name: "返回首页", exact: true }).click();
  const consent = page.getByRole("dialog", { name: "保存当前草稿？", exact: true });
  await expect(consent).toBeVisible();
  await consent.getByRole("button", { name: "取消", exact: true }).click();
  await expect(page.getByLabel("片名")).toHaveValue("回家前留住的故事");
  await page.getByRole("button", { name: "返回首页", exact: true }).click();
  await consent.getByRole("button", { name: "保存并切换", exact: true }).click();
  await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
  const { projects } = await (await request.get(`${workbench.apiOrigin}/api/v2/projects`)).json() as ProjectListResponse;
  expect(projects).toHaveLength(1);
  expect(projects[0].brief.title).toBe("回家前留住的故事");
  expect(projects[0].operationalState).not.toBe("closed");
});

test("Home retains durable Brief drafts, lifecycle and saved-project history", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
  await page.getByRole("button", { name: "保存并继续到来源", exact: true }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const id = new URL(page.url()).searchParams.get("project")!;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=brief`);
  await expect(page.getByRole("button", { name: "保存修改", exact: true })).toBeVisible();
  const before = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json();
  const lifecycleWrites: string[] = [];
  page.on("request", item => {
    if (item.method() !== "GET" && /\/(close|open|archive|restore|permanent-delete|cancel|resume|runs)(?:\?|$)/.test(item.url())) lifecycleWrites.push(item.url());
  });
  await page.getByLabel("片名").fill("只留在草稿里的新片名");
  await page.getByRole("button", { name: "返回首页", exact: true }).click();
  await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
  const after = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json();
  expect(after).toEqual(before);
  const drafts = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`)).json();
  expect(drafts[0].payload.title).toBe("只留在草稿里的新片名");
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`project=${id}&stage=brief$`));
  await page.getByRole("button", { name: "恢复草稿", exact: true }).click();
  await expect(page.getByLabel("片名")).toHaveValue("只留在草稿里的新片名");
  await page.goForward();
  await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
  expect(lifecycleWrites).toEqual([]);
});

test("Home retains unconfirmed source input for explicit recovery", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
  await page.getByRole("button", { name: "保存并继续到来源", exact: true }).click();
  await expect(page.getByLabel("故事内容")).toBeEditable();
  const id = new URL(page.url()).searchParams.get("project")!;
  await page.getByLabel("故事内容").fill("尚未确认的故事内容，先回首页，稍后继续。");
  await page.getByRole("button", { name: "返回首页", exact: true }).click();
  await expect(page.getByRole("heading", { name: "从一个项目开始" })).toBeVisible();
  await page.goBack();
  await page.getByRole("button", { name: "恢复编辑草稿", exact: true }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue("尚未确认的故事内容，先回首页，稍后继续。");
  const source = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`)).json();
  expect(source.source).toBeNull();
});
