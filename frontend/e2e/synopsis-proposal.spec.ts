import type { APIRequestContext } from "@playwright/test";
import { expect, test } from "./fixture";

test("turns a synopsis into a reviewable Bible/Graph proposal without entering downstream production", async ({ page, request, workbench }) => {
  await configurePublicNoAuthProfile(request, workbench.apiOrigin, workbench.providerOrigin);
  await page.goto(`${workbench.frontendOrigin}/v2/?stage=brief`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("一名夜班气象员发现每一次改写暴风预报，都会让一座海岛从地图上消失；她必须决定公布真相还是保护岛上的家人。");

  const created = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === "/api/v2/projects");
  const started = page.waitForResponse((response) => response.request().method() === "POST"
    && /\/api\/v2\/projects\/[^/]+\/pipeline-runs$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "生成故事提案" }).click();
  const creation = await created;
  expect(creation.ok()).toBeTruthy();
  expect(creation.request().postDataJSON()).toMatchObject({
    brief: { title: "未命名故事", synopsis: expect.stringContaining("夜班气象员") },
  });
  await expect(page).toHaveURL(/[?&]project=/);
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("proposal creation did not bind a project ID");
  const runResponse = await started;
  expect(runResponse.ok()).toBeTruthy();
  expect(runResponse.request().postDataJSON()).toMatchObject({
    stages: ["story_bible", "story_graph"],
  });
  const run = await runResponse.json() as { id: string };
  await pollRun(request, workbench.apiOrigin, run.id, "succeeded");

  await expect(page.getByTestId("story-proposal-review")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("仅 Story Bible 与剧情 DAG", { exact: true })).toBeVisible();
  const stageResponse = await readJson<{ stages: Array<{ head: { stage: string; revision: number; status: string } }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`);
  const stages = stageResponse.stages;
  expect(stages.map((item) => item.head.stage)).toEqual(["story_bible", "story_graph", "scene_beats", "storyboard"]);
  expect(stages.filter((item) => ["story_bible", "story_graph"].includes(item.head.stage)).every((item) => item.head.status === "ready" && item.head.revision === 1)).toBeTruthy();
  expect(stages.filter((item) => ["scene_beats", "storyboard"].includes(item.head.stage)).every((item) => item.head.status === "missing" && item.head.revision === 0)).toBeTruthy();

  await page.getByLabel("片名").fill("风暴回声");
  await page.getByRole("button", { name: "保存简报" }).click();
  await expect(page.getByText("提案的上游内容已变更。请重新生成 Story Bible 与剧情 DAG 后，再进入分镜规划；不会覆盖任何下游内容。", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "接受提案，进入分镜规划" })).toBeDisabled();

  await page.getByRole("button", { name: "细化人物与设定" }).click();
  await page.getByLabel("Logline").fill("夜班气象员要在亲人与整座岛之间决定哪一种真相得以留下。");
  await page.getByRole("button", { name: "保存故事圣经" }).click();
  await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /^01 项目简报/ }).click();
  await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("story-proposal-review")).toContainText("夜班气象员要在亲人与整座岛之间决定哪一种真相得以留下。");
  await expect(page.getByText("提案的上游内容已变更。请重新生成 Story Bible 与剧情 DAG 后，再进入分镜规划；不会覆盖任何下游内容。", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "接受提案，进入分镜规划" })).toBeDisabled();
  const refreshed = page.waitForResponse((response) => response.request().method() === "POST"
    && /\/api\/v2\/projects\/[^/]+\/pipeline-runs$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "生成故事提案" }).click();
  const refreshedRun = await refreshed;
  expect(refreshedRun.request().postDataJSON()).toMatchObject({ stages: ["story_bible", "story_graph"] });
  await pollRun(request, workbench.apiOrigin, (await refreshedRun.json() as { id: string }).id, "succeeded");
  const refreshedStages = await readJson<{ stages: Array<{ head: { stage: string; status: string } }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`);
  expect(refreshedStages.stages.filter((item) => ["story_bible", "story_graph"].includes(item.head.stage)).map((item) => ({ stage: item.head.stage, status: item.head.status }))).toEqual([
    { stage: "story_bible", status: "ready" }, { stage: "story_graph", status: "ready" },
  ]);
  await page.getByRole("button", { name: "刷新服务器版本" }).click();
  await expect(page.getByRole("button", { name: "接受提案，进入分镜规划" })).toBeEnabled({ timeout: 20_000 });

  const pipelineCount = await requestCount(request, workbench.apiOrigin, projectId);
  await page.getByRole("button", { name: "接受提案，进入分镜规划" }).click();
  await expect(page.getByRole("heading", { name: "场景、节拍与对白" })).toBeVisible();
  expect(await requestCount(request, workbench.apiOrigin, projectId)).toBe(pipelineCount);
});

test("keeps the saved synopsis and shows an actionable proposal-admission failure", async ({ page, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/?stage=brief`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  const synopsis = "一名调音师在停电的剧院里听见未来演出的回声。";
  await page.getByLabel("故事梗概").fill(synopsis);
  await page.route("**/api/v2/projects/*/pipeline-runs", async (route) => {
    await route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ message: "文本后端尚未就绪；请在供应商与会话 Key 中测试连接后重试。" }) });
  });
  await page.getByRole("button", { name: "生成故事提案" }).click();
  await expect(page.getByText("文本后端尚未就绪；请在供应商与会话 Key 中测试连接后重试。", { exact: true })).toBeVisible();
  await expect(page.getByLabel("故事梗概")).toHaveValue(synopsis);
});

async function configurePublicNoAuthProfile(request: APIRequestContext, apiOrigin: string, providerOrigin: string): Promise<void> {
  const catalog = await readJson<{ profiles: Array<{ profileId: string; revision: number; configuration: Record<string, unknown> }> }>(request, `${apiOrigin}/api/v2/text-provider-profiles`);
  const profile = catalog.profiles.find((candidate) => candidate.profileId === "default");
  expect(profile).toBeTruthy();
  const response = await request.put(`${apiOrigin}/api/v2/text-provider-profiles/default`, {
    data: {
      expectedRevision: profile!.revision,
      displayName: "External E2E fake",
      configuration: {
        ...profile!.configuration,
        textProvider: "external-openai-fake", textBaseUrl: `${providerOrigin}/v1`, textModel: "external-fake-v1", textAuthMode: "none",
        textCapabilities: { chatCompletions: true, jsonObject: false, jsonSchema: true, chatTemplateKwargs: false }, presetId: "custom", profileHash: "",
      },
    },
  });
  expect(response.ok()).toBeTruthy();
}

async function pollRun(request: APIRequestContext, apiOrigin: string, runId: string, expected: string): Promise<void> {
  await expect.poll(async () => (await readJson<{ status: string }>(request, `${apiOrigin}/api/v2/runs/${runId}/progress`)).status, { timeout: 20_000 }).toBe(expected);
}

async function requestCount(request: APIRequestContext, apiOrigin: string, projectId: string): Promise<number> {
  return (await readJson<{ runs: unknown[] }>(request, `${apiOrigin}/api/v2/projects/${projectId}/runs`)).runs.length;
}

async function readJson<T>(request: APIRequestContext, url: string): Promise<T> {
  const response = await request.get(url);
  expect(response.ok()).toBeTruthy();
  return response.json() as Promise<T>;
}
