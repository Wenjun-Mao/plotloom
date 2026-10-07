import { expect, test } from "./fixture";
import { createScriptProject, json } from "./f5a-fixture";
import type { Page } from "@playwright/test";

function gate() {
  let release!: () => void, start!: () => void;
  return { held: new Promise<void>(done => { release = done; }), started: new Promise<void>(done => { start = done; }), release: () => release(), start: () => start() };
}
const row = (page: Page, id: string) => page.locator(`.directory-item[data-project-id="${id}"]`);

for (const kind of ["JSON", "HTML"] as const) test(`Save-and-close settles an owned ${kind} read and resumes projections after the exclusive response`, async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, `held-close-${kind}`);
  const held = gate(); let closes = 0, reports = 0;
  const pattern = kind === "JSON" ? "**/api/v2/projects/*/script" : "**/api/v2/projects/*/script/candidates/*/report?presentation=static";
  await page.route(pattern, async route => {
    const response = await route.fetch();
    if (kind === "HTML") { reports += 1; expect(response.headers()["content-security-policy"]).toContain("default-src 'none'"); }
    held.start(); await held.held; await route.fulfill({ response });
  });
  await page.route("**/api/v2/projects/*/close", async route => { closes += 1; await route.continue(); });
  try {
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
    const textbox = page.getByRole("textbox", { name: "剧情摘要", exact: true });
    await expect(textbox).toBeEditable(); await held.started;
    const ack = page.waitForResponse(response => response.request().method() === "PUT" && response.url().endsWith(`/${id}/authoring-drafts`));
    const text = `保存并关闭时保留 ${kind} 读取中的图正文。`;
    await textbox.fill(text); await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
    expect((await ack).ok()).toBe(true);
    await expect(page.getByRole("heading", { name: "项目目录", exact: true })).toBeVisible();
    expect(closes).toBe(0);
    held.release();
    await expect(row(page, id)).toContainText("已关闭 · 可安全复制"); expect(closes).toBe(1);
    if (kind === "HTML") expect(reports).toBe(1);
    // The held-read exercise ends at Close. Reopen uses the ordinary network
    // owner, so fixture teardown cannot race another intercepted fetch.
    await page.unroute(pattern);
    await row(page, id).getByRole("button", { name: "重新打开", exact: true }).click();
    await expect(textbox).toHaveValue(text);
    const draft = (await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`))).find((item: any) => item.editorScope === "story_graph");
    expect(draft.payload.mapping.sections[0].summary).toBe(text);
  } finally { held.release(); }
});

test("busy close fails truthfully and resumes owned report and JSON reads for an explicit retry", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "busy-close-resume");
  let closes = 0;
  await page.route("**/api/v2/projects/*/close", async route => {
    closes += 1;
    if (closes === 1) await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ code: "project_busy", message: "another local writer is active" }) });
    else await route.continue();
  });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  const textbox = page.getByRole("textbox", { name: "剧情摘要", exact: true });
  await expect(textbox).toBeEditable(); await textbox.fill("失败后仍保留这份未确认图草稿。");
  await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("占用");
  await expect(page.getByRole("alert")).not.toContainText("版本冲突");
  await expect(textbox).toHaveValue("失败后仍保留这份未确认图草稿。");
  await page.getByRole("dialog", { name: "项目目录", exact: true }).locator("footer").getByRole("button", { name: "关闭窗口", exact: true }).click();
  await page.reload(); await expect(textbox).toHaveValue("失败后仍保留这份未确认图草稿。");
  await expect(page.frameLocator('iframe[title="static derived upstream script report"]').locator("body")).toContainText("Deterministic upstream-context fixture report");
  await page.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
  await expect(row(page, id)).toContainText("已关闭 · 可安全复制"); expect(closes).toBe(2);
});
