import { expect, test } from "./fixture";
import { demoProject } from "../src/demo";

for (const height of [900, 600]) {
  test(`durable Brief writes withdraw launch until exact no-op cleanup at 1440x${height}`, async ({ page, request, workbench }, info) => {
    await page.setViewportSize({ width: 1440, height });
    // Availability metadata only; every draft/admission response uses the real
    // project-folder API, and this test never invokes Start or specialist send.
    await page.route("**/api/v2/specialists", route => route.request().method() === "GET"
      ? route.fulfill({ json: { text: { name: "Text availability fixture", taskId: "text-fixture" }, image: { name: "Image availability fixture", taskId: "image-fixture" }, busy: false } })
      : route.continue());
    const created = await (await request.post(`${workbench.apiOrigin}/api/v2/projects`, {
      data: { brief: { ...demoProject.brief, title: "Positive draft admission" }, initialStages: [] },
    })).json();
    const id = created.id, root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
    const canonical = await (await request.get(root)).json();
    const writes: string[] = [];
    page.on("request", req => { if (["POST", "PUT", "PATCH", "DELETE"].includes(req.method())) writes.push(`${req.method()} ${new URL(req.url()).pathname}`); });
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=brief`);
    const launch = page.getByRole("button", { name: "一键准备视频素材", exact: true });
    await expect(launch).toBeVisible(); await launch.click();
    await expect(page.getByRole("button", { name: "开始准备已保存简报的素材", exact: true })).toBeEnabled();
    const before = page.url(), editor = await page.getByLabel("片名", { exact: true }).elementHandle();
    for (const title of ["Temporary title edit", canonical.brief.title]) {
      const saved = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith(`/${id}/authoring-drafts`));
      const admission = page.waitForResponse(r => r.request().method() === "GET" && r.url().endsWith(`/${id}/autopilot/launch-context`));
      await page.getByLabel("片名", { exact: true }).fill(title);
      expect((await saved).status()).toBe(200);
      expect(await (await admission).json()).toEqual({ eligible: false, briefRevision: canonical.revision });
      await expect(launch).toHaveCount(0);
      await expect(page.getByRole("button", { name: "开始准备已保存简报的素材", exact: true })).toHaveCount(0);
    }
    await page.getByLabel("片名", { exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath(`draft-admission-withdrawn-${height}.png`) });
    const drafts = await (await request.get(`${root}/authoring-drafts`)).json();
    const draft = drafts.find((item: any) => item.editorScope === "brief");
    expect(draft).toMatchObject({ draftRevision: 2, baseCanonicalRevision: canonical.revision, payload: canonical.brief });
    const removed = page.waitForResponse(r => r.request().method() === "DELETE" && r.url().endsWith(`/${id}/authoring-drafts`));
    const admitted = page.waitForResponse(r => r.request().method() === "GET" && r.url().endsWith(`/${id}/autopilot/launch-context`));
    await page.getByRole("button", { name: "保存修改", exact: true }).click();
    const receipt = await removed;
    expect(receipt.status()).toBe(204);
    expect(receipt.request().postDataJSON()).toEqual({ editorScope: "brief", entityId: "root", expectedDraftRevision: 2 });
    expect(receipt.headers()["x-plotloom-draft-consumed-revision"]).toBe("2");
    expect(await (await admitted).json()).toEqual({ eligible: true, briefRevision: canonical.revision });
    await expect(launch).toBeVisible();
    await expect(page.getByRole("button", { name: "开始准备已保存简报的素材", exact: true })).toBeEnabled();
    expect(page.url()).toBe(before); expect(await editor!.evaluate(node => node.isConnected)).toBe(true);
    expect(await (await request.get(root)).json()).toEqual(canonical);
    expect(await (await request.get(`${root}/authoring-drafts`)).json()).toEqual([]);
    expect(await (await request.get(`${root}/autopilot`)).json()).toBeNull();
    expect(writes).toEqual([`PUT /api/v2/projects/${id}/authoring-drafts`, `PUT /api/v2/projects/${id}/authoring-drafts`, `DELETE /api/v2/projects/${id}/authoring-drafts`]);
    await launch.scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath(`draft-admission-restored-${height}.png`) });
    await page.getByRole("button", { name: "开始准备已保存简报的素材", exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath(`draft-admission-start-${height}.png`) });
  });
}

test("unchanged restored Brief save refreshes launch admission in place after exact draft cleanup", async ({ page, request, workbench }, info) => {
  const created = await (await request.post(`${workbench.apiOrigin}/api/v2/projects`, {
    data: { brief: { ...demoProject.brief, title: "Unchanged Brief admission" }, initialStages: [] },
  })).json();
  const id = created.id;
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const canonical = await (await request.get(root)).json();
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=brief`);
  await expect(page.getByRole("button", { name: "一键准备视频素材", exact: true })).toBeVisible();
  for (const title of ["Temporary title edit", canonical.brief.title]) {
    const saved = page.waitForResponse(r => r.request().method() === "PUT" && r.url().endsWith(`/${id}/authoring-drafts`));
    const admission = page.waitForResponse(r => r.request().method() === "GET" && r.url().endsWith(`/${id}/autopilot/launch-context`));
    await page.getByLabel("片名", { exact: true }).fill(title);
    expect((await saved).ok()).toBe(true);
    expect((await (await admission).json()).eligible).toBe(false);
  }
  const drafts = await (await request.get(`${root}/authoring-drafts`)).json();
  const draft = drafts.find((item: any) => item.editorScope === "brief");
  expect(draft.payload).toEqual(canonical.brief);
  expect((await (await request.get(`${root}/autopilot/launch-context`)).json()).eligible).toBe(false);
  const reloadAdmission = page.waitForResponse(r => r.request().method() === "GET" && r.url().endsWith(`/${id}/autopilot/launch-context`));
  await page.reload();
  expect((await (await reloadAdmission).json()).eligible).toBe(false);
  const recovery = page.getByRole("dialog", { name: "发现可恢复草稿", exact: true });
  await expect(recovery).toBeVisible();
  const restoredAdmission = page.waitForResponse(r => r.request().method() === "GET" && r.url().endsWith(`/${id}/autopilot/launch-context`));
  await recovery.getByRole("button", { name: "恢复草稿", exact: true }).click();
  expect((await (await restoredAdmission).json()).eligible).toBe(false);
  await expect(recovery).toHaveCount(0);
  await expect(page.getByLabel("片名", { exact: true })).toHaveValue(canonical.brief.title);
  await expect(page.getByRole("button", { name: "一键准备视频素材", exact: true })).toHaveCount(0);
  const before = page.url();
  const editor = await page.getByLabel("片名", { exact: true }).elementHandle();
  const writes: string[] = [];
  page.on("request", req => { if (["POST", "PUT", "PATCH"].includes(req.method())) writes.push(`${req.method()} ${new URL(req.url()).pathname}`); });
  const removed = page.waitForResponse(r => r.request().method() === "DELETE" && r.url().includes(`/${id}/authoring-drafts`));
  const admission = page.waitForResponse(r => r.request().method() === "GET" && r.url().endsWith(`/${id}/autopilot/launch-context`));
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  const receipt = await removed;
  expect(receipt.status()).toBe(204);
  expect(receipt.request().postDataJSON()).toEqual({ editorScope: "brief", entityId: "root", expectedDraftRevision: draft.draftRevision });
  expect(receipt.headers()["x-plotloom-draft-consumed-revision"]).toBe(String(draft.draftRevision));
  expect((await (await admission).json()).eligible).toBe(true);
  await expect(page.getByRole("button", { name: "一键准备视频素材", exact: true })).toBeVisible();
  expect(page.url()).toBe(before);
  expect(await editor!.evaluate(node => node.isConnected)).toBe(true);
  expect(await (await request.get(root)).json()).toEqual(canonical);
  expect(await (await request.get(`${root}/authoring-drafts`)).json()).toEqual([]);
  expect(await (await request.get(`${root}/autopilot`)).json()).toBeNull();
  expect(writes).toEqual([]);
  await page.screenshot({ path: info.outputPath("unchanged-brief-admission.png"), fullPage: true });
});

test("autopilot launch is admitted only for current saved Brief-only data", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await expect(page.getByRole("button", { name: "一键准备视频素材", exact: true })).toHaveCount(0);
  await page.getByLabel("片名").fill("Fresh autopilot admission fixture");
  await page.getByLabel("故事梗概").fill("A keeper considers two endings at the lighthouse.");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  const id = new URL(page.url()).searchParams.get("project")!;
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/autopilot/launch-context`)).json()).eligible).toBe(true);
  await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
  await expect(page.getByRole("button", { name: "一键准备视频素材", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "返回来源与大纲" }).click();
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await expect(page.getByText("改编内容 r1", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
  await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();
  await expect(page.getByRole("button", { name: "一键准备视频素材", exact: true })).toHaveCount(0);
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/autopilot`)).json())).toBeNull();
});

test("Brief save continues to an editable Source draft without starting the legacy proposal", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("片名").fill("雨停以后");
  await page.getByLabel("故事梗概").fill("雨刚停，林遥在车站檐下决定去海堤还是旧街。");
  await expect(page.locator(".page-header .button")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "保存修改" })).toHaveCount(0);
  await page.getByText("其他工作流：旧版故事提案", { exact: true }).click();
  await expect(page.getByRole("button", { name: "生成故事提案" })).toBeVisible();
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("Brief save did not create a project");
  await expect(page.getByLabel("标题")).toHaveValue("雨停以后");
  await expect(page.getByLabel("故事内容")).toHaveValue("雨刚停，林遥在车站檐下决定去海堤还是旧街。");
  await expect(page.getByLabel("补充创作要求（可选）")).toHaveValue("");
  await expect(page.getByRole("button", { name: "确认改编内容" })).toBeEnabled();
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline`)).json()).source).toBeNull();

  await page.getByLabel("故事内容").fill("作者尚未保存的本地来源草稿。");
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(page.getByLabel("故事内容")).toHaveValue("作者尚未保存的本地来源草稿。");
  await expect(page.getByLabel("归属 / 署名声明")).toHaveCount(0);
  await expect(page.getByLabel("使用权或许可声明")).toHaveCount(0);
  await expect(page.getByText("确认只保存故事来源；生成大纲需要下方单独准备并发送任务。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await expect(page.getByText("改编内容 r1", { exact: true })).toBeVisible();
  const saved = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline`)).json();
  expect(saved.source.material).toMatchObject({
    title: "雨停以后",
    text: "作者尚未保存的本地来源草稿。",
    attribution: null,
    rightsDeclaration: null,
    adaptationIntent: "",
  });
});

test("existing Source content and optional declarations survive a later source edit", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("片名").fill("Brief title");
  await page.getByLabel("故事梗概").fill("Brief synopsis that must not replace existing source.");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  await expect(page).toHaveURL(/[?&]project=/);
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("project was not saved");
  const existing = {
    kind: "imported_text", title: "Existing source", text: "Existing authored text",
    attribution: "Historical author attribution", rightsDeclaration: "Historical rights declaration",
    adaptationIntent: "Keep the existing source", inventedAdditions: null,
  };
  const saved = await request.put(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline/source`, {
    data: { expectedSourceRevision: 0, material: existing },
  });
  expect(saved.ok()).toBeTruthy();
  await page.reload();
  await expect(page.getByLabel("标题")).toHaveValue("Existing source");
  await expect(page.getByLabel("故事内容")).toHaveValue("Existing authored text");
  await page.getByLabel("故事内容").fill("Existing authored text, revised");
  const sourceSave = page.waitForResponse((response) => response.request().method() === "PUT"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/source-outline/source`);
  await page.getByRole("button", { name: "确认改编内容" }).click();
  const sourceSaveResponse = await sourceSave;
  expect(sourceSaveResponse.ok()).toBeTruthy();
  expect((await sourceSaveResponse.json()).source).toMatchObject({
    revision: 2,
    material: {
      title: "Existing source", text: "Existing authored text, revised",
      attribution: "Historical author attribution", rightsDeclaration: "Historical rights declaration",
    },
  });
  await expect(page.getByText("改编内容 r2", { exact: true })).toBeVisible();
  const updated = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline`)).json();
  expect(updated.source.material).toMatchObject({
    title: "Existing source", text: "Existing authored text, revised",
    attribution: "Historical author attribution", rightsDeclaration: "Historical rights declaration",
  });
});

test("saved Brief saves in place and offers an explicit return to Source", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("一个已保存项目仍可编辑简报。");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("project was not saved");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=brief`);
  await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();
  await expect(page.getByRole("button", { name: "保存修改", exact: true })).toHaveCount(1);
  await expect(page.getByRole("button", { name: "返回来源与大纲", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "保存并继续到来源" })).toHaveCount(0);
  await page.getByText("其他工作流：旧版故事提案", { exact: true }).click();
  await expect(page.getByText("通常请从左侧“来源与大纲”开始，逐步审阅并确认。", { exact: false })).toBeVisible();
  await page.getByLabel("片名").fill("已保存项目的新片名");
  const patch = page.waitForResponse((response) => response.request().method() === "PATCH"
    && new URL(response.url()).pathname === `/api/v2/projects/${projectId}`);
  await page.getByRole("button", { name: "保存修改" }).click();
  expect((await patch).ok()).toBeTruthy();
  await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`project=${projectId}.*stage=brief`));
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline`)).json()).source).toBeNull();
});

for (const width of [1440, 1920]) {
  test(`Brief select and number controls align at ${width}px`, async ({ page, workbench }) => {
    await page.setViewportSize({ width, height: 1080 });
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "创建空白项目" }).click();
    const language = await page.getByLabel("语言").evaluate((element) => element.getBoundingClientRect().height);
    const aspect = await page.getByLabel("画幅").evaluate((element) => element.getBoundingClientRect().height);
    const duration = await page.getByLabel("目标游玩时长（秒）").evaluate((element) => element.getBoundingClientRect().height);
    expect(duration).toBe(40);
    expect(language).toBeCloseTo(duration, 0);
    expect(aspect).toBeCloseTo(duration, 0);
  });
}

test("Brief actions reject a target below the script workflow minimum", async ({ page, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("一位旅人面临两个结局。");
  await page.getByLabel("目标游玩时长（秒）").fill("2");
  await expect(page.getByRole("button", { name: "保存修改" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "保存并继续到来源" })).toBeDisabled();
  await page.getByText("其他工作流：旧版故事提案", { exact: true }).click();
  await expect(page.getByRole("button", { name: "生成故事提案" })).toBeDisabled();
  await page.getByLabel("目标游玩时长（秒）").fill("3");
  await expect(page.getByRole("button", { name: "保存并继续到来源" })).toBeEnabled();
});
