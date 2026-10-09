import { expect, test } from "./fixture";
import { createScriptProject, json } from "./f5a-fixture";
import { captureDesktopState } from "./fixtures/desktop-state";
import type { Page } from "@playwright/test";

async function selectBeacon(page: Page, url: string) {
  await page.goto(url);
  await expect(page.getByRole("heading", { name: "剧情图与结构规则" })).toBeVisible();
  await page.getByText("全部稳定身份与待连接关系", { exact: true }).click();
  await page.getByRole("button", { name: "Beacon lit", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "剧情摘要", exact: true })).toBeEditable();
}

test("typed graph conflict explicitly recovers the exact retained tab prose on current authority", async ({ page, request, workbench }, info) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "typed-graph-recovery", {}, []);
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const draftPath = `/api/v2/projects/${id}/authoring-drafts`;
  const url = `${workbench.frontendOrigin}/v2/?project=${id}&stage=graph`;
  const canonical = await json(request.get(`${root}/source-outline`));
  const second = await page.context().newPage();
  try {
    await selectBeacon(page, url); await selectBeacon(second, url);
    const firstAck = page.waitForResponse(r => r.request().method() === "PUT" && new URL(r.url()).pathname === draftPath);
    await page.getByRole("textbox", { name: "剧情摘要", exact: true }).fill("Other tab graph prose");
    expect((await firstAck).ok()).toBe(true);
    const before = await json(request.get(`${root}/graph-workbench`));
    const retained = "Exact retained graph prose from stale tab";
    const refused = second.waitForResponse(r => r.request().method() === "PUT" && new URL(r.url()).pathname === draftPath);
    await second.getByRole("textbox", { name: "剧情摘要", exact: true }).fill(retained);
    expect((await refused).status()).toBe(409);
    const dialog = second.getByRole("dialog", { name: "草稿版本已过期", exact: true });
    await expect(dialog).toContainText("原图草稿仍保留");
    await expect(dialog).toContainText("最初的结构方案");
    await expect(dialog).toContainText("不会恢复之前的确认或安装状态");
    await captureDesktopState(second, info, "graph-conflict-ready", dialog.locator(".modal-card"));
    expect((await json(request.get(`${root}/graph-workbench`))).draft).toEqual(before.draft);
    const recovery = second.waitForResponse(r => r.request().method() === "POST"
      && new URL(r.url()).pathname === `/api/v2/projects/${id}/graph-workbench/recover`);
    await dialog.getByRole("button", { name: "在当前版本恢复图草稿", exact: true }).click();
    const response = await recovery;
    expect(response.ok()).toBe(true);
    expect(response.request().postDataJSON()).toMatchObject({ expectedDraftRevision: before.draft.draftRevision, expectedBindingHash: before.bindingHash });
    const receipt = await response.json();
    await expect(dialog).toHaveCount(0);
    await expect(second.getByRole("textbox", { name: "剧情摘要", exact: true })).toHaveValue(retained);
    const restored = await json(request.get(`${root}/graph-workbench`));
    expect(restored.draft.draftRevision).toBe(receipt.draftRevision);
    expect(restored.draft.payload.mapping.sections.find((s: { sectionId: string }) => s.sectionId === "beacon").summary).toBe(retained);
    expect(await json(request.get(`${root}/source-outline`))).toEqual(canonical);
    expect((await json(request.get(`${root}/runs`))).runs).toEqual([]);
    await captureDesktopState(second, info, "graph-conflict-recovered", second.getByRole("textbox", { name: "剧情摘要", exact: true }));
  } finally { await second.close(); }
});
