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
  await page.route(endpoint, route => route.request().method() === "GET"
    ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "temporary fixture failure" }) }) : route.continue());
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

for (const viewport of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
  test(`conflict reload preserves exact drafts through held failure and retry at ${viewport.width}x${viewport.height}`, async ({ page, request, workbench }, testInfo) => {
    await page.setViewportSize(viewport);
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await page.getByLabel("片名", { exact: true }).fill("Disposable conflict visual audit");
    await page.getByRole("button", { name: "保存并继续到来源" }).click();
    await expect(page).toHaveURL(/[?&]project=/);
    const id = new URL(page.url()).searchParams.get("project")!;
    const url = `${workbench.frontendOrigin}/v2/?project=${id}&stage=brief`;
    await page.goto(url);
    await expect(page.getByLabel("片名", { exact: true })).toHaveValue("Disposable conflict visual audit");
    const second = await page.context().newPage();
    try {
      await second.setViewportSize(viewport);
      await second.goto(url); await expect(second.getByLabel("片名", { exact: true })).toHaveValue("Disposable conflict visual audit");
      const winner = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/authoring-drafts"));
      await page.getByLabel("片名", { exact: true }).fill("Server-saved winning draft");
      expect((await winner).ok()).toBe(true);
      const loser = second.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/authoring-drafts"));
      await second.getByLabel("片名", { exact: true }).fill("Exact retained conflicting draft");
      expect((await loser).status()).toBe(409);
      const conflict = second.getByRole("dialog", { name: "草稿版本已过期" });
      await expect(conflict).toBeVisible();
      const original = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json();
      const originalDrafts = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`)).json();
      const retained = await second.evaluate(() => sessionStorage.getItem("plotloom:workbench-drafts:v1"));
      const writes: string[] = [];
      second.on("request", req => { if (req.url().includes("/api/v2/") && !["GET", "HEAD"].includes(req.method())) writes.push(`${req.method()} ${new URL(req.url()).pathname}`); });
      const capture = async (state: string) => {
        expect(await second.getByRole("dialog").count()).toBe(1);
        const dialog = second.getByRole("dialog"), heading = dialog.getByRole("heading");
        await expect(heading).toBeInViewport();
        const box = await dialog.locator("section").boundingBox();
        expect(box).not.toBeNull(); expect(box!.x).toBeGreaterThanOrEqual(0); expect(box!.y).toBeGreaterThanOrEqual(0);
        expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width); expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height);
        await second.screenshot({ path: testInfo.outputPath(`recovery-${state}.png`) });
      };
      await capture("conflict");
      let release!: () => void, markStarted!: () => void;
      const released = new Promise<void>(resolve => { release = resolve; });
      const started = new Promise<void>(resolve => { markStarted = resolve; });
      const endpoint = `**/api/v2/projects/${id}`;
      await second.route(endpoint, async route => {
        if (route.request().method() !== "GET") { await route.continue(); return; }
        markStarted(); await released;
        await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "GET-only held authority failure" }) });
      });
      try {
        await conflict.getByRole("button", { name: "重新加载服务器版本", exact: true }).click(); await started;
        await expect(conflict.getByRole("button", { name: "正在重新加载…" })).toBeDisabled();
        for (const name of ["复制草稿为新项目", "丢弃冲突草稿"]) await expect(conflict.getByRole("button", { name })).toBeDisabled();
        await expect(conflict).not.toContainText("已重新加载服务器"); await capture("pending");
      } finally { release(); }
      const unsafe = second.getByRole("dialog", { name: "暂时无法核实项目，草稿已保留" });
      await expect(unsafe).toBeVisible(); await expect(conflict).toHaveCount(0); await capture("failed");
      await expect(unsafe.getByRole("textbox", { name: "保留的草稿", exact: true })).toHaveAttribute("readonly", "");
      expect(await second.evaluate(() => sessionStorage.getItem("plotloom:workbench-drafts:v1"))).toBe(retained);
      expect(writes).toEqual([]);
      await second.unroute(endpoint);
      await unsafe.getByRole("button", { name: "重试核实项目" }).click();
      await expect(conflict).toBeVisible(); await expect(unsafe).toHaveCount(0);
      await expect(conflict.getByRole("button", { name: "重新加载服务器版本", exact: true })).toBeEnabled();
      await capture("retry-verified");
      await conflict.getByRole("button", { name: "重新加载服务器版本", exact: true }).click();
      await expect(conflict.getByRole("button", { name: "已加载服务器版本", exact: true })).toBeDisabled();
      await expect(second.getByLabel("片名", { exact: true })).toHaveValue(original.brief.title);
      await capture("loaded");
      expect(writes).toEqual([]);
      expect(await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json()).toEqual(original);
      expect(await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`)).json()).toEqual(originalDrafts);
      const create = second.waitForRequest(req => req.method() === "POST" && new URL(req.url()).pathname === "/api/v2/projects");
      await conflict.getByRole("button", { name: "复制草稿为新项目" }).click();
      const copiedRequest = (await create).postDataJSON();
      expect(copiedRequest).toMatchObject({ brief: { title: "Exact retained conflicting draft（冲突副本）" } });
      expect(copiedRequest).not.toHaveProperty("initialStages");
      await expect(second.getByLabel("片名", { exact: true })).toHaveValue("Exact retained conflicting draft（冲突副本）");
      expect(writes).toEqual(["POST /api/v2/projects"]);
      expect(await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}`)).json()).toEqual(original);
    } finally { await second.close(); }
  });
}

test("unsafe conflict discard removes only the selected retained input without resurrecting its workflow", async ({ page, request, workbench }, testInfo) => {
  await page.setViewportSize({ width: 1280, height: 460 });
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const id = new URL(page.url()).searchParams.get("project")!;
  const endpoint = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const url = `${workbench.frontendOrigin}/v2/?project=${id}&stage=brief`;
  await page.goto(url); await expect(page.getByLabel("片名", { exact: true })).toHaveValue("月城余晖");
  const second = await page.context().newPage();
  try {
    await second.setViewportSize({ width: 1280, height: 460 });
    await second.goto(url); await expect(second.getByLabel("片名", { exact: true })).toHaveValue("月城余晖");
    const winner = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/authoring-drafts"));
    await page.getByLabel("片名", { exact: true }).fill("Winning retained server input"); expect((await winner).ok()).toBe(true);
    const loser = second.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith("/authoring-drafts"));
    let markStarted!: () => void, release!: () => void;
    const started = new Promise<void>(resolve => { markStarted = resolve; });
    const released = new Promise<void>(resolve => { release = resolve; });
    await second.route(`**/api/v2/projects/${id}/authoring-drafts`, async route => {
      if (route.request().method() === "PUT") { markStarted(); await released; }
      await route.continue();
    });
    try {
      await second.getByLabel("片名", { exact: true }).fill("Older submitted input"); await started;
      await second.getByLabel("片名", { exact: true }).fill("Latest retained conflicting input");
    } finally { release(); }
    expect((await loser).status()).toBe(409);
    await second.unroute(`**/api/v2/projects/${id}/authoring-drafts`);
    const conflict = second.getByRole("dialog", { name: "草稿版本已过期" }); await expect(conflict).toBeVisible();
    expect(await second.evaluate(() => sessionStorage.getItem("plotloom:workbench-drafts:v1"))).toContain("Latest retained conflicting input");
    const unrelated = await second.evaluate(() => {
      const key = "unrelated-local-owner:brief:1";
      const all = JSON.parse(sessionStorage.getItem("plotloom:workbench-drafts:v1")!);
      const record = { ...Object.values(all)[0] as object, key, projectId: "unrelated-local-owner", payload: { title: "Other retained input" } };
      sessionStorage.setItem("plotloom:workbench-drafts:v1", JSON.stringify({ ...all, [key]: record })); return record;
    });
    const original = await (await request.get(endpoint)).json(), drafts = await (await request.get(`${endpoint}/authoring-drafts`)).json();
    const writes: string[] = [];
    second.on("request", req => { if (req.url().includes("/api/v2/") && !["GET", "HEAD"].includes(req.method())) writes.push(req.method()); });
    await second.route(`**/api/v2/projects/${id}`, route => route.request().method() === "GET"
      ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "GET-only unsafe discard fault" }) }) : route.continue());
    await conflict.getByRole("button", { name: "重新加载服务器版本", exact: true }).click();
    const unsafe = second.getByRole("dialog", { name: "暂时无法核实项目，草稿已保留" }); await expect(unsafe).toBeVisible();
    await second.screenshot({ path: testInfo.outputPath("discard-before.png") });
    await unsafe.getByRole("button", { name: "丢弃不可用草稿" }).click();
    await expect(second.getByRole("dialog")).toHaveCount(0);
    await expect(second.getByRole("button", { name: "复制草稿为新项目" })).toHaveCount(0);
    expect(await second.evaluate(() => JSON.parse(sessionStorage.getItem("plotloom:workbench-drafts:v1")!))).toEqual({ [unrelated.key]: unrelated });
    const notice = second.getByRole("status").filter({ hasText: "已丢弃本标签页选中的保留草稿" });
    await expect(notice).toContainText("项目中已保存的草稿和已确认内容未删除");
    const readError = second.getByRole("alert");
    await expect(readError).toContainText("暂时无法读取项目");
    const details = second.locator(".project-load-details");
    await details.getByText("查看读取详情", { exact: true }).click();
    await expect(details).toContainText(id);
    await expect(details.locator("pre")).toContainText("GET-only unsafe discard fault");
    await details.getByText("查看读取详情", { exact: true }).click();
    await expect(readError).toBeInViewport(); await expect(notice).toBeInViewport();
    await second.screenshot({ path: testInfo.outputPath("discard-after.png") });
    await second.unroute(`**/api/v2/projects/${id}`); await second.goto(url);
    await expect(second.getByRole("dialog", { name: "发现可恢复草稿" })).toBeVisible();
    await expect(second.getByRole("dialog")).toContainText("此草稿已保存在项目中");
    await expect(second.getByRole("button", { name: "复制草稿为新项目" })).toHaveCount(0);
    await expect(second.getByLabel("片名", { exact: true })).toHaveValue(original.brief.title);
    await expect(second.getByText("已丢弃本标签页选中的保留草稿", { exact: false })).toHaveCount(0);
    await second.screenshot({ path: testInfo.outputPath("discard-reverified.png") });
    expect(writes).toEqual([]);
    expect(await (await request.get(endpoint)).json()).toEqual(original);
    expect(await (await request.get(`${endpoint}/authoring-drafts`)).json()).toEqual(drafts);
  } finally { await second.close(); }
});
