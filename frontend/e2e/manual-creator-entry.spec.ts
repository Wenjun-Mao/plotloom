import { expect, test } from "./fixture";

test("Brief save continues to an editable Source draft without starting the legacy proposal", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("片名").fill("雨停以后");
  await page.getByLabel("故事梗概").fill("雨刚停，林遥在车站檐下决定去海堤还是旧街。");
  await expect(page.locator(".page-header .button")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "保存修改" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "生成故事提案" })).toBeVisible();
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("Brief save did not create a project");
  await expect(page.getByLabel("标题")).toHaveValue("雨停以后");
  await expect(page.getByLabel("来源正文或 treatment")).toHaveValue("雨刚停，林遥在车站檐下决定去海堤还是旧街。");
  await expect(page.getByLabel("改编意图")).toHaveValue("");
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline`)).json()).source).toBeNull();

  await page.getByLabel("来源正文或 treatment").fill("作者尚未保存的本地来源草稿。");
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(page.getByLabel("来源正文或 treatment")).toHaveValue("作者尚未保存的本地来源草稿。");
  await page.getByLabel("改编意图").fill("保留一个选择和两个结局。");
  await expect(page.getByLabel("归属 / 署名声明")).toHaveCount(0);
  await expect(page.getByLabel("使用权或许可声明")).toHaveCount(0);
  await expect(page.getByText("将以这些内容和创作方向为依据，生成大纲。本次确认不会启动生成。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await expect(page.getByText("来源 r1")).toBeVisible();
  const saved = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline`)).json();
  expect(saved.source.material).toMatchObject({
    title: "雨停以后",
    text: "作者尚未保存的本地来源草稿。",
    attribution: null,
    rightsDeclaration: null,
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
  await expect(page.getByLabel("来源正文或 treatment")).toHaveValue("Existing authored text");
  await page.getByLabel("来源正文或 treatment").fill("Existing authored text, revised");
  await page.getByRole("button", { name: "确认改编内容" }).click();
  const updated = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/source-outline`)).json();
  expect(updated.source.material).toMatchObject({
    title: "Existing source", text: "Existing authored text, revised",
    attribution: "Historical author attribution", rightsDeclaration: "Historical rights declaration",
  });
});

test("saved Brief offers only Save Changes and remains on Brief", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("一个已保存项目仍可编辑简报。");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("project was not saved");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=brief`);
  await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();
  await expect(page.locator(".page-header .button")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "保存并继续到来源" })).toHaveCount(0);
  await expect(page.getByText("若要审阅来源与大纲，请从左侧创作流程打开。", { exact: false })).toBeVisible();
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
  await expect(page.getByRole("button", { name: "生成故事提案" })).toBeDisabled();
  await page.getByLabel("目标游玩时长（秒）").fill("3");
  await expect(page.getByRole("button", { name: "保存并继续到来源" })).toBeEnabled();
});
