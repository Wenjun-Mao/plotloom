import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";
import { readdir } from "node:fs/promises";

test("one deletion entry erases only the idle disposable home through real API and persistence", async ({ page, request, workbench }) => {
  const create = async (title: string) => {
    const response = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title }, initialStages: [] } });
    expect(response.status()).toBe(201); return response.json();
  };
  const target = await create("统一删除空闲项目"), neighbor = await create("保留相邻项目");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${neighbor.id}&stage=brief`);
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const row = page.locator(`[data-project-id="${target.id}"]`);
  await expect(row.locator(".directory-actions").getByRole("button", { name: /删除/ })).toHaveCount(1);
  await row.getByRole("button", { name: "删除项目…", exact: true }).click();
  const consent = page.getByRole("alertdialog", { name: "永久删除项目" });
  await expect(consent.getByRole("checkbox")).toHaveCount(0);
  await consent.getByLabel("输入完整片名以确认删除").fill(target.brief.title);
  await page.screenshot({ path: "../output/playwright/unified-delete-idle.png" });
  await consent.getByRole("button", { name: "确认永久删除项目", exact: true }).click();
  await expect(row).toHaveCount(0);
  expect((await readdir(workbench.outputsRoot)).some(name => name.endsWith(`__${target.id}`))).toBe(false);
  await workbench.restartBackend();
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${target.id}`)).status()).toBe(404);
  expect((await request.get(`${workbench.apiOrigin}/api/v2/projects/${neighbor.id}`)).status()).toBe(200);
});

for (const outcome of ["deleted", "scope_changed", "stop_lost_ack", "delete_lost_ack"] as const) {
  test(`paused automatic task has one consent and truthful ${outcome} outcome without replay`, async ({ page, request, workbench }) => {
    const response = await request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: { brief: { ...demoProject.brief, title: "暂停自动项目" }, initialStages: [] } });
    const target = await response.json();
    const prepared = { projectId: target.id, confirmationTitle: target.brief.title, expectedProjectRevision: 1,
      expectedLifecycleRevision: 1, scopeHash: "a".repeat(64), mode: "stop", run: { id: "exact-run", revision: 7, state: "paused" },
      blockers: [], unknownAttemptIds: ["original-unknown"], previewHash: "b".repeat(64) };
    let stops = 0, deletions = 0;
    await page.route(`**/projects/${target.id}/deletion-preview`, route => route.fulfill({ json: prepared }));
    await page.route(`**/projects/${target.id}/stop-for-deletion`, async route => {
      stops++;
      expect(route.request().postDataJSON()).toMatchObject({ expectedRunId: "exact-run", expectedRunRevision: 7, scopeHash: prepared.scopeHash });
      if (outcome === "stop_lost_ack") return route.abort("failed");
      return route.fulfill({ json: { runId: "exact-run", state: "cancelled", deletionPreview: { ...prepared, run: null,
        mode: "abandon", scopeHash: outcome === "scope_changed" ? "c".repeat(64) : prepared.scopeHash } } });
    });
    await page.route(`**/projects/${target.id}/abandon-and-delete`, async route => {
      deletions++;
      expect(route.request().postDataJSON()).toMatchObject({ scopeHash: prepared.scopeHash, acknowledgeUnknownRemote: true });
      if (outcome === "delete_lost_ack") return route.abort("failed");
      return route.fulfill({ status: 204 });
    });
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${target.id}&stage=brief`);
    await page.getByRole("button", { name: "当前项目 · 切换" }).click();
    const row = page.locator(`[data-project-id="${target.id}"]`);
    await row.getByRole("button", { name: "删除项目…", exact: true }).click();
    const consent = page.getByRole("alertdialog", { name: "停止任务并删除项目" });
    await expect(consent).toContainText("paused（exact-run）");
    await expect(consent).toContainText("original-unknown");
    await consent.getByLabel("输入完整片名以确认删除").fill(target.brief.title);
    await expect(consent.getByRole("button", { name: "确认停止任务并删除项目" })).toBeDisabled();
    await consent.getByRole("checkbox").check();
    await consent.getByRole("button", { name: "确认停止任务并删除项目" }).click();
    await expect(consent).toHaveCount(0);
    expect(stops).toBe(1);
    expect(deletions).toBe(["deleted", "delete_lost_ack"].includes(outcome) ? 1 : 0);
    if (outcome === "deleted") await expect(page.getByRole("status").filter({ hasText: "项目已永久删除" })).toBeVisible();
    else {
      await expect(row.getByRole("alert")).toContainText(outcome === "stop_lost_ack" ? "停止或删除结果未确认" : "自动运行已取消后续派发，但项目未确认删除");
      await expect(page.getByRole("status").filter({ hasText: "项目已永久删除" })).toHaveCount(0);
      await page.screenshot({ path: `../output/playwright/unified-delete-${outcome}.png` });
    }
  });
}
