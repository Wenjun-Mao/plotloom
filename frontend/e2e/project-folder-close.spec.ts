import { expect, saveBriefAndContinue, test } from "./fixture";
import type { Page } from "@playwright/test";

async function teachingCopy(page: Page, origin: string) {
  await page.goto(`${origin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
  await expect(page.getByRole("button", { name: "创建编辑副本", exact: true })).toBeVisible();
  await expect(page.getByLabel("片名", { exact: true })).toBeDisabled();
  await saveBriefAndContinue(page);
  const id = new URL(page.url()).searchParams.get("project")!;
  await page.goto(`${origin}/v2/?project=${id}&stage=brief`);
  await expect(page.getByLabel("片名", { exact: true })).toBeEnabled();
  return id;
}
async function more(page: Page, id: string) {
  await page.getByRole("button", { name: "当前项目 · 切换" }).click();
  const row = page.locator(`.directory-item[data-project-id="${id}"]`);
  await row.getByRole("button", { name: /^更多/ }).click(); return row;
}

test("optional Freeze drains working input, permits readonly loads after restart, and Unfreeze never applies it", async ({ page, workbench }) => {
  const id = await teachingCopy(page, workbench.frontendOrigin);
  const canonicalTitle = await page.getByLabel("片名", { exact: true }).inputValue();
  await page.getByLabel("片名", { exact: true }).fill("working input before Freeze");
  const row = await more(page, id);
  const frozen = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith(`/projects/${id}/freeze`));
  await row.getByRole("button", { name: "冻结项目", exact: true }).click();
  expect((await frozen).ok()).toBeTruthy();
  await expect(row).toContainText("已冻结 · 只读");
  await page.getByRole("button", { name: "关闭窗口", exact: true }).last().click();
  await expect(page.getByLabel("片名", { exact: true })).toBeDisabled();
  await workbench.restartBackend(); await page.reload();
  await expect(page.getByLabel("片名", { exact: true })).toHaveValue("working input before Freeze");
  await expect(page.getByLabel("片名", { exact: true })).toBeDisabled();
  const canonical = await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json();
  expect(canonical.brief.title).toBe(canonicalTitle);
  const refused = await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ editorScope: "brief", entityId: "root", baseCanonicalRevision: canonical.revision, expectedDraftRevision: 1, payload: { title: "late", synopsis: "" } }) });
  expect(refused.status).toBe(409);
  const frozenRow = await more(page, id);
  await frozenRow.getByRole("button", { name: "解除冻结", exact: true }).click();
  await page.getByRole("button", { name: "关闭窗口", exact: true }).last().click();
  await expect(page.getByLabel("片名", { exact: true })).toBeEnabled();
  expect((await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json()).brief.title).toBe(canonicalTitle);
  expect((await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}/runs`)).json()).runs).toEqual([]);
});

test("preview performs no creation; explicit editable copy creates once without run history", async ({ page, workbench }) => {
  const creates: string[] = [];
  page.on("request", request => { if (request.method() === "POST" && new URL(request.url()).pathname === "/api/v2/projects") creates.push(request.url()); });
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
  await expect(page.getByRole("button", { name: "创建编辑副本", exact: true })).toBeVisible();
  expect(creates).toHaveLength(0);
  await page.getByRole("button", { name: "创建编辑副本", exact: true }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  expect(creates).toHaveLength(1);
  const id = new URL(page.url()).searchParams.get("project")!;
  expect((await (await fetch(`${workbench.apiOrigin}/api/v2/projects/${id}/runs`)).json()).runs).toEqual([]);
});
