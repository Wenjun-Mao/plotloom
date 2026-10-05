import { expect, test } from "./fixture";
import { readFile } from "node:fs/promises";
import path from "node:path";

test("first cancelled outline explicitly prepares again with unchanged source and retained package", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("Offline fixture: keep or release a paper plane.");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await expect(page.getByText("改编内容 r1", { exact: true })).toBeVisible();
  const id = new URL(page.url()).searchParams.get("project")!;
  const base = `${workbench.apiOrigin}/api/v2/projects/${id}/source-outline`;
  const prepared = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/source-outline/candidates"));
  await page.getByRole("button", { name: "准备大纲任务", exact: true }).click();
  const old = await (await prepared).json();
  const packageBytes = await readFile(path.join(old.packagePath, "request.json"));
  const source = (await (await request.get(base)).json()).source;
  await page.getByRole("button", { name: "取消此任务", exact: true }).click();
  await expect(page.getByRole("button", { name: "重新准备大纲任务", exact: true })).toBeEnabled();
  const nextResponse = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/source-outline/candidates"));
  await page.getByRole("button", { name: "重新准备大纲任务", exact: true }).click();
  const next = await (await nextResponse).json();
  expect(next.jobId).not.toBe(old.jobId);
  const state = await (await request.get(base)).json();
  expect(state.source).toEqual(source); expect(state.acceptedOutline).toBeNull();
  expect(state.candidate.status).toBe("prepared");
  expect(await readFile(path.join(old.packagePath, "request.json"))).toEqual(packageBytes);
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/specialists`)).json()).busy).toBe(false);
});

test("temporary draft authority failure allows read-only export, retry and exact restore", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const id = new URL(page.url()).searchParams.get("project")!;
  const authority = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json();
  await page.evaluate(({ id, authority }) => {
    const key = `${id}:brief:${authority.revision}`;
    sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({ [key]: { key, projectId: id, scope: "brief", baseRevision: authority.revision, serverDraftRevision: 0, localRevision: 1, payload: { ...authority.brief, title: "Retained offline author title" }, updatedAt: "2026-10-04" } }));
  }, { id, authority });
  const endpoint = `**/api/v2/projects/${id}`;
  await page.route(endpoint, route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "temporary fixture failure" }) }));
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=brief`);
  const dialog = page.getByRole("dialog", { name: "暂时无法核实项目，草稿已保留" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("textbox", { name: "保留的草稿", exact: true })).toHaveAttribute("readonly", "");
  const download = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "导出保留内容" }).click();
  const saved = await download;
  expect(await readFile((await saved.path())!, "utf8")).toContain("Retained offline author title");
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json()).brief.title).toBe(authority.brief.title);
  await page.unroute(endpoint);
  await dialog.getByRole("button", { name: "重试核实项目" }).click();
  await page.getByRole("button", { name: "恢复草稿", exact: true }).click();
  await expect(page.getByLabel("片名")).toHaveValue("Retained offline author title");
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json()).brief.title).toBe(authority.brief.title);
});
