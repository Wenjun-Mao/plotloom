import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";
import type { APIRequestContext, Page } from "@playwright/test";

const row = (page: Page, id: string) => page.locator(`.directory-item[data-project-id="${id}"]`);

test("abandonment requires exact server preview, title and uncertainty checkbox; pending deletion survives refresh", async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, "明确放弃项目");
  const preview = { projectId: target.id, expectedLifecycleRevision: 1, expectedProjectRevision: 1,
    confirmationTitle: target.brief.title, previewHash: "a".repeat(64), eligible: true, blockers: [], unknownAttemptIds: ["unknown-exact-attempt"] };
  let pending: unknown[] = [];
  await page.route("**/api/v2/project-deletions", route => route.fulfill({ json: pending }));
  await page.route(`**/api/v2/projects/${target.id}/abandonment-preview`, route => route.fulfill({ json: preview }));
  const bodies: Record<string, unknown>[] = [];
  await page.route(`**/api/v2/projects/${target.id}/abandon-and-delete`, route => {
    bodies.push(route.request().postDataJSON());
    pending = [{ ...preview, revoked: true }];
    return route.fulfill({ status: 409, json: { message: "主机发布已撤销；项目删除尚未完成，请重试。" } });
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=brief`);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  await row(page, target.id).getByRole("button", { name: "放弃任务并永久删除", exact: true }).click();
  const dialog = page.getByRole("alertdialog", { name: "放弃任务并永久删除项目" });
  await expect(dialog).toContainText("unknown-exact-attempt");
  await dialog.getByLabel("输入完整片名以确认放弃和删除").fill(target.brief.title);
  const commit = dialog.getByRole("button", { name: "确认放弃任务并永久删除项目" });
  await expect(commit).toBeDisabled();
  await dialog.getByRole("checkbox").check();
  await page.screenshot({ path: "../output/playwright/abandonment-consent.png" });
  await commit.click();
  await expect.poll(() => bodies.length).toBe(1);
  expect(bodies[0]).toMatchObject({ previewHash: preview.previewHash, confirmationTitle: target.brief.title, acknowledgeUnknownRemote: true });
  await page.reload();
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const retry = page.getByRole("region", { name: "待完成项目删除" });
  await expect(retry).toContainText("主机派发和发布权限已撤销");
  const retryAction = retry.getByRole("button", { name: `重试删除「${target.brief.title}」` });
  await expect(retryAction).toBeEnabled();
  await page.screenshot({ path: "../output/playwright/pending-deletion.png" });
  await retryAction.click();
  await expect(page.getByRole("alertdialog", { name: "重试永久删除项目" })).toBeVisible();
  expect(bodies).toHaveLength(1);
});

test("unacknowledged pending deletion rechecks the latest preview before fresh explicit consent", async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, "旧放弃确认");
  const pending = { projectId: target.id, expectedLifecycleRevision: 1, expectedProjectRevision: 1,
    confirmationTitle: target.brief.title, previewHash: "a".repeat(64), revoked: false };
  const fresh = { ...pending, expectedProjectRevision: 2, confirmationTitle: "重新核对后的片名",
    previewHash: "b".repeat(64), eligible: true, blockers: [], unknownAttemptIds: ["exact-unsettled-original"] };
  await page.route("**/api/v2/project-deletions", route => route.fulfill({ json: [pending] }));
  let reads = 0;
  await page.route(`**/api/v2/projects/${target.id}/abandonment-preview`, route => {
    reads += 1; return route.fulfill({ json: fresh });
  });
  const submissions: Record<string, unknown>[] = [];
  await page.route(`**/api/v2/projects/${target.id}/abandon-and-delete`, route => {
    submissions.push(route.request().postDataJSON());
    return route.fulfill({ status: 409, json: { message: "disposable explicit-consent observation" } });
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=brief`);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const retry = page.getByRole("button", { name: `重新核对并删除「${target.brief.title}」` });
  await expect(retry).toBeEnabled();
  expect(reads).toBe(0);
  await retry.click();
  const dialog = page.getByRole("alertdialog", { name: "重试永久删除项目" });
  await expect(dialog).toContainText("已重新核对当前服务器预览");
  await expect(dialog).toContainText("exact-unsettled-original");
  await dialog.getByLabel("输入完整片名以确认重试删除").fill(fresh.confirmationTitle);
  await dialog.getByRole("checkbox").check();
  expect(submissions).toEqual([]);
  await dialog.getByRole("button", { name: "确认重试永久删除项目" }).click();
  await expect.poll(() => submissions.length).toBe(1);
  expect(reads).toBe(1);
  expect(submissions[0]).toMatchObject({ expectedProjectRevision: 2,
    confirmationTitle: fresh.confirmationTitle, previewHash: fresh.previewHash, acknowledgeUnknownRemote: true });
});
async function create(request: APIRequestContext, origin: string, title: string) {
  const response = await request.post(`${origin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title }, initialStages: [] } });
  expect(response.status()).toBe(201); return await response.json();
}
async function confirm(page: Page, id: string, title: string) {
  await row(page, id).getByRole("button", { name: "永久删除", exact: true }).click();
  const dialog = page.getByRole("alertdialog", { name: "永久删除项目" });
  await dialog.getByLabel("输入完整片名以确认删除").fill(title);
  await dialog.getByRole("button", { name: "确认永久删除项目" }).click();
}

for (const state of ["active", "archived", "closed"] as const) test(`deletes a ${state} project directly without archive or reopen`, async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, `直接删除-${state}`);
  if (state === "archived") expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${target.id}/archive`, { data: { expectedLifecycleRevision: 1 } })).ok()).toBeTruthy();
  if (state === "closed") expect((await request.post(`${workbench.apiOrigin}/api/v2/projects/${target.id}/close`)).ok()).toBeTruthy();
  const current = await create(request, workbench.apiOrigin, "另一个当前项目");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${current.id}&stage=brief`);
  await expect(page.getByLabel("片名")).toHaveValue("另一个当前项目");
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  if (state === "archived") await page.getByLabel("显示归档项目").check();
  let transitions = 0;
  page.on("request", request => { if (new RegExp(`/projects/${target.id}/(open|archive|restore|close)$`).test(request.url())) transitions += 1; });
  await confirm(page, target.id, target.brief.title);
  await expect(row(page, target.id)).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: "项目已永久删除" })).toBeVisible();
  expect(transitions).toBe(0);
  await expect(page).toHaveURL(new RegExp(`project=${current.id}`));
  await expect(page.getByLabel("片名")).toHaveValue("另一个当前项目");
  await workbench.restartBackend();
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`)).status()).toBe(404);
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${current.id}`)).ok()).toBeTruthy();
});

test("busy deletion retains partial source input and does not cancel a prepared job", async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, "保留任务和草稿");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=source`);
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await page.getByRole("button", { name: "准备大纲任务" }).click();
  await expect(page.getByText(/^任务尚未交付 · 发送状态见下方 ·/)).toBeVisible();
  const before = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}/source-outline`)).json();
  await page.getByLabel("故事内容").fill("这段尚未确认的编辑必须保留。");
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const deletion = page.waitForResponse(response => response.url().endsWith(`/api/v2/projects/${target.id}/permanent-delete`) && response.request().method() === "POST");
  await confirm(page, target.id, target.brief.title);
  const refused = await deletion;
  expect(refused.status()).toBe(409);
  expect((await refused.json()).code).toBe("project_busy");
  await expect(page.getByRole("alert")).toContainText("项目仍有读取、写入或后台任务占用");
  await expect(page.getByRole("alert")).toContainText("等待占用结束后重试");
  await expect(page.getByRole("alert")).not.toContainText("版本冲突");
  await expect(page.getByLabel("故事内容")).toHaveValue("这段尚未确认的编辑必须保留。");
  const after = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}/source-outline`)).json();
  expect(after.candidate).toEqual(before.candidate);
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`)).ok()).toBeTruthy();
});

test("stale Brief confirmation cannot erase another client's save", async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, "旧确认片名");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=brief`);
  await expect(page.getByLabel("片名")).toHaveValue(target.brief.title);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  await row(page, target.id).getByRole("button", { name: "永久删除", exact: true }).click();
  const changed = await request.patch(`${workbench.apiOrigin}/api/v2/projects/${target.id}`, { data: { expectedRevision: target.revision, brief: { ...target.brief, synopsis: "另一标签页已修改" } } });
  expect(changed.ok()).toBeTruthy();
  await page.getByRole("alertdialog").getByLabel("输入完整片名以确认删除").fill(target.brief.title);
  await page.getByRole("button", { name: "确认永久删除项目" }).click();
  await expect(page.getByRole("alert")).toContainText("revision");
  const retained = await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`);
  expect((await retained.json()).brief.synopsis).toBe("另一标签页已修改");
});

test("deletion waits for an admitted draft but never sends newer typing", async ({ page, request, workbench }) => {
  const target = await create(request, workbench.apiOrigin, "删除传输中草稿");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=brief`);
  let release!: () => void, started!: () => void; let writes = 0;
  const held = new Promise<void>(resolve => { release = resolve; });
  const inFlight = new Promise<void>(resolve => { started = resolve; });
  await page.route(`**/api/v2/projects/${target.id}/authoring-drafts`, async route => {
    if (route.request().method() === "PUT") { writes += 1; started(); await held; }
    await route.continue();
  });
  try {
    await page.getByLabel("片名").fill("已发送的旧草稿"); await inFlight;
    await page.getByLabel("片名").fill("不要再发送的新草稿");
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    await confirm(page, target.id, target.brief.title);
    await expect(page.getByRole("status").filter({ hasText: "正在处理" })).toBeVisible();
    release();
    await expect(page.getByRole("alertdialog")).not.toBeVisible();
    await expect(row(page, target.id)).toHaveCount(0);
    await expect(page.getByLabel("片名")).toHaveValue("");
    expect(writes).toBe(1);
    expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`)).status()).toBe(404);
  } finally { release(); }
});
