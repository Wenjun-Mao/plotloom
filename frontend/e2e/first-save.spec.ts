import { expect, test } from "./fixture";

test("explicit teaching copy persists canon, later Bible input autosaves and Apply survives reload", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目", exact: true }).click();
  const create = page.waitForRequest(request => request.method() === "POST" && new URL(request.url()).pathname === "/api/v2/projects");
  await page.getByRole("button", { name: "创建编辑副本", exact: true }).click();
  expect((await create).postDataJSON().initialStages).toHaveLength(4);
  await expect(page).toHaveURL(/[?&]project=/);
  const id = new URL(page.url()).searchParams.get("project")!;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=bible`);
  const logline = page.getByRole("textbox", { name: "一句话概述（Logline）", exact: true });
  await expect(logline).toHaveAccessibleDescription("用一句话概括主角、核心冲突和故事吸引力；详细背景写在“故事前提”中。");
  const original = await logline.inputValue();
  const next = "Explicit copy author input, later applied by its exact receipt.";
  await logline.fill(next);
  await expect.poll(async () => (await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/authoring-drafts`)).json()).find((draft: { editorScope: string }) => draft.editorScope === "story_bible")?.payload.logline).toBe(next);
  const before = (await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/stages`)).json()).stages.find((stage: { head: { stage: string } }) => stage.head.stage === "story_bible");
  expect(before.payload.logline).toBe(original);
  await page.getByRole("button", { name: "应用故事圣经修改", exact: true }).click();
  await expect.poll(async () => (await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/stages`)).json()).stages.find((stage: { head: { stage: string } }) => stage.head.stage === "story_bible").payload.logline).toBe(next);
  await page.reload(); await expect(logline).toHaveValue(next);
});

test("lost New response and double-click intent replay create exactly one persistent draft", async ({ page, request, workbench }) => {
  const keys: string[] = []; let lose = true;
  await page.route("**/api/v2/projects", async route => {
    if (route.request().method() !== "POST") { await route.continue(); return; }
    keys.push(route.request().headers()["idempotency-key"]);
    if (lose) { lose = false; await route.fetch(); await route.abort("failed"); }
    else await route.continue();
  });
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目", exact: true }).click();
  await expect(page.getByText(/新项目尚未确认创建/)).toBeVisible();
  await page.getByRole("button", { name: "创建空白项目", exact: true }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  expect(keys).toHaveLength(2); expect(keys[1]).toBe(keys[0]);
  const projects = (await (await request.get(`${workbench.apiOrigin}/api/v2/projects`)).json()).projects;
  expect(projects).toHaveLength(1); expect(projects[0].brief).toBeNull();
  expect((await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projects[0].id}/runs`)).json()).runs).toEqual([]);
});
