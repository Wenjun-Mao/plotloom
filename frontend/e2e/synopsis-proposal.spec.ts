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
  await expect(page.getByText("Story Bible 与剧情 DAG 已审阅", { exact: true })).toBeVisible();
  const stageResponse = await readJson<{ stages: Array<{ head: { stage: string; revision: number; status: string } }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`);
  const stages = stageResponse.stages;
  expect(stages.map((item) => item.head.stage)).toEqual(["story_bible", "story_graph", "scene_beats", "storyboard"]);
  expect(stages.filter((item) => ["story_bible", "story_graph"].includes(item.head.stage)).every((item) => item.head.status === "ready" && item.head.revision === 1)).toBeTruthy();
  expect(stages.filter((item) => ["scene_beats", "storyboard"].includes(item.head.stage)).every((item) => item.head.status === "missing" && item.head.revision === 0)).toBeTruthy();
  const proposalGraph = (await readJson<{ stages: Array<{ head: { stage: string }; payload: { nodes: Array<{ id: string; title: string; kind: string }>; edges: Array<{ kind: string; choiceText: string | null; targetNodeId: string }> } }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`)).stages.find((stage) => stage.head.stage === "story_graph")!.payload;
  const choice = proposalGraph.edges.find((edge) => edge.kind === "choice");
  const choiceTarget = proposalGraph.nodes.find((node) => node.id === choice?.targetNodeId);
  expect(choice).toBeTruthy();
  expect(choiceTarget).toBeTruthy();
  await expect(page.getByTestId("story-proposal-review")).toContainText(choice!.choiceText!);
  await expect(page.getByTestId("story-proposal-review")).toContainText(`${choiceTarget!.kind === "ending" ? "结局：" : "节点："}${choiceTarget!.title}`);

  const initialBrief = await readJson<{ revision: number }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}`);
  const readyRunCount = await requestCount(request, workbench.apiOrigin, projectId);
  await page.getByRole("button", { name: "生成故事提案" }).click();
  await expect(page.getByText("当前故事提案已经是最新版本；可直接细化内容或进入分镜规划。", { exact: true })).toBeVisible();
  expect(await requestCount(request, workbench.apiOrigin, projectId)).toBe(readyRunCount);
  expect((await readJson<{ revision: number }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}`)).revision).toBe(initialBrief.revision);

  await page.getByRole("button", { name: "细化人物与设定" }).click();
  await page.getByLabel("Logline").fill("夜班气象员要在亲人与整座岛之间决定哪一种真相得以留下。");
  const bibleSave = page.waitForResponse((response) => response.request().method() === "PATCH"
    && /\/api\/v2\/projects\/[^/]+\/stages\/story_bible$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "保存故事圣经" }).click();
  expect((await bibleSave).ok()).toBeTruthy();
  const authoredBible = (await readJson<{ stages: Array<{ head: { stage: string; revision: number }; payload: unknown }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`)).stages.find((stage) => stage.head.stage === "story_bible");
  expect(authoredBible).toMatchObject({ head: { revision: 2 }, payload: { logline: "夜班气象员要在亲人与整座岛之间决定哪一种真相得以留下。" } });
  await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /项目简报/ }).click();
  await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("story-proposal-review")).toContainText("夜班气象员要在亲人与整座岛之间决定哪一种真相得以留下。");
  await expect(page.getByText("提案的上游内容已变更。请重新生成 Story Bible 与剧情 DAG 后，再进入分镜规划；不会覆盖任何下游内容。", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "进入场景编辑" })).toBeDisabled();
  const graphOnly = page.waitForResponse((response) => response.request().method() === "POST"
    && /\/api\/v2\/projects\/[^/]+\/pipeline-runs$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "生成故事提案" }).click();
  const graphOnlyRun = await graphOnly;
  expect(graphOnlyRun.request().postDataJSON()).toMatchObject({ stages: ["story_graph"] });
  await pollRun(request, workbench.apiOrigin, (await graphOnlyRun.json() as { id: string }).id, "succeeded");
  const refreshedStages = await readJson<{ stages: Array<{ head: { stage: string; status: string } }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`);
  expect(refreshedStages.stages.filter((item) => ["story_bible", "story_graph"].includes(item.head.stage)).map((item) => ({ stage: item.head.stage, status: item.head.status }))).toEqual([
    { stage: "story_bible", status: "ready" }, { stage: "story_graph", status: "ready" },
  ]);
  const savedBible = (await readJson<{ stages: Array<{ head: { stage: string; revision: number }; payload: unknown }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`)).stages.find((stage) => stage.head.stage === "story_bible");
  expect(savedBible).toEqual(authoredBible);

  await page.getByLabel("片名").fill("风暴回声");
  await page.getByRole("button", { name: "保存简报" }).click();
  await expect(page.getByText("提案的上游内容已变更。请重新生成 Story Bible 与剧情 DAG 后，再进入分镜规划；不会覆盖任何下游内容。", { exact: true })).toBeVisible();
  const refreshed = page.waitForResponse((response) => response.request().method() === "POST"
    && /\/api\/v2\/projects\/[^/]+\/pipeline-runs$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "生成故事提案" }).click();
  const refreshedRun = await refreshed;
  expect(refreshedRun.request().postDataJSON()).toMatchObject({ stages: ["story_bible", "story_graph"] });
  await pollRun(request, workbench.apiOrigin, (await refreshedRun.json() as { id: string }).id, "succeeded");
  await page.getByRole("button", { name: "刷新服务器版本" }).click();
  await expect(page.getByRole("button", { name: "进入场景编辑" })).toBeEnabled({ timeout: 20_000 });

  const pipelineCount = await requestCount(request, workbench.apiOrigin, projectId);
  await page.getByRole("button", { name: "进入场景编辑" }).click();
  await expect(page.getByRole("heading", { name: "场景节拍" })).toBeVisible();
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

test("keeps an authored Bible intact when its graph-only proposal regeneration is rejected", async ({ page, request, workbench }) => {
  await configurePublicNoAuthProfile(request, workbench.apiOrigin, workbench.providerOrigin);
  await page.goto(`${workbench.frontendOrigin}/v2/?stage=brief`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("一位海关译员发现一封未寄出的信能改写港口的潮汐。 ");
  const initialRun = page.waitForResponse((response) => response.request().method() === "POST"
    && /\/api\/v2\/projects\/[^/]+\/pipeline-runs$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "生成故事提案" }).click();
  const initial = await initialRun;
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("proposal creation did not bind a project ID");
  await pollRun(request, workbench.apiOrigin, (await initial.json() as { id: string }).id, "succeeded");

  await page.getByRole("button", { name: "细化人物与设定" }).click();
  const authoredLogline = "海关译员必须决定让港口记住真相，还是让她失踪的弟弟回家。";
  await page.getByLabel("Logline").fill(authoredLogline);
  const bibleSave = page.waitForResponse((response) => response.request().method() === "PATCH"
    && /\/api\/v2\/projects\/[^/]+\/stages\/story_bible$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "保存故事圣经" }).click();
  expect((await bibleSave).ok()).toBeTruthy();
  await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /项目简报/ }).click();
  await page.reload();
  await expect(page.getByText("提案的上游内容已变更。请重新生成 Story Bible 与剧情 DAG 后，再进入分镜规划；不会覆盖任何下游内容。", { exact: true })).toBeVisible();
  await page.route("**/api/v2/projects/*/pipeline-runs", async (route) => {
    await route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ message: "文本后端尚未就绪；请稍后重试。" }) });
  });
  await page.getByRole("button", { name: "生成故事提案" }).click();
  await expect(page.getByText("文本后端尚未就绪；请稍后重试。", { exact: true })).toBeVisible();
  const bible = (await readJson<{ stages: Array<{ head: { stage: string; revision: number }; payload: { logline?: string } }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`)).stages.find((stage) => stage.head.stage === "story_bible");
  expect(bible).toMatchObject({ head: { revision: 2 }, payload: { logline: authoredLogline } });
});

test("continues a current proposal through the smallest editable storyboard range without replacing its upstream", async ({ page, request, workbench }) => {
  await configurePublicNoAuthProfile(request, workbench.apiOrigin, workbench.providerOrigin);
  await page.goto(`${workbench.frontendOrigin}/v2/?stage=brief`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("一名港口口译员发现潮汐会抹去未被说出的证词，她必须在弟弟归来前公开真相。 ");
  const proposalRequest = page.waitForResponse((response) => response.request().method() === "POST"
    && /\/api\/v2\/projects\/[^/]+\/pipeline-runs$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "生成故事提案" }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const projectId = new URL(page.url()).searchParams.get("project");
  if (!projectId) throw new Error("proposal creation did not bind a project ID");
  const proposal = await proposalRequest;
  await pollRun(request, workbench.apiOrigin, (await proposal.json() as { id: string }).id, "succeeded");
  const upstream = await readJson<{ revision: number; stages: Array<{ head: { stage: string; revision: number }; payload: unknown }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`);
  const canonicalProject = await readJson<{ revision: number }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}`);
  const bible = upstream.stages.find((stage) => stage.head.stage === "story_bible");
  const graph = upstream.stages.find((stage) => stage.head.stage === "story_graph");

  // An admission failure must leave the reviewed proposal intact and offer no
  // client-side fallback that could re-request its upstream stages.
  await page.route("**/api/v2/projects/*/pipeline-runs", async (route) => {
    await route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ message: "文本后端暂不可用；请检查设置后使用隔离修复或重新运行。" }) });
  });
  await page.getByRole("button", { name: "生成可编辑场景与分镜" }).click();
  await expect(page.getByText("文本后端暂不可用；请检查设置后使用隔离修复或重新运行。", { exact: true })).toBeVisible();
  expect(await readJson(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`)).toEqual(upstream);
  await page.unroute("**/api/v2/projects/*/pipeline-runs");

  const continuationRequest = page.waitForResponse((response) => response.request().method() === "POST"
    && /\/api\/v2\/projects\/[^/]+\/pipeline-runs$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "生成可编辑场景与分镜" }).click();
  const continuation = await continuationRequest;
  expect(continuation.request().postDataJSON()).toMatchObject({ stages: ["scene_beats", "storyboard"] });
  await pollRun(request, workbench.apiOrigin, (await continuation.json() as { id: string }).id, "succeeded");
  const afterContinuation = await readJson<{ stages: Array<{ head: { stage: string; revision: number; status: string }; payload: unknown }> }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`);
  expect(afterContinuation.stages.find((stage) => stage.head.stage === "story_bible")).toEqual(bible);
  expect(afterContinuation.stages.find((stage) => stage.head.stage === "story_graph")).toEqual(graph);
  expect(afterContinuation.stages.filter((stage) => ["scene_beats", "storyboard"].includes(stage.head.stage)).every((stage) => stage.head.status === "ready" && stage.head.revision === 1)).toBeTruthy();
  expect((await readJson<{ revision: number }>(request, `${workbench.apiOrigin}/api/v2/projects/${projectId}`)).revision).toBe(canonicalProject.revision);

  await page.reload();
  await page.getByRole("button", { name: "进入场景编辑" }).click();
  await expect(page.getByTestId("scene-beats-page")).toBeVisible();
  await page.getByLabel("场景标题").first().fill("港口的潮声证词");
  const sceneSave = page.waitForResponse((response) => response.request().method() === "PATCH"
    && /\/api\/v2\/projects\/[^/]+\/stages\/scene_beats$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "保存节拍计划" }).click();
  expect((await sceneSave).ok()).toBeTruthy();
  await page.getByRole("navigation", { name: "工作台阶段" }).getByRole("button", { name: /项目简报/ }).click();
  const storyboardOnlyRequest = page.waitForResponse((response) => response.request().method() === "POST"
    && /\/api\/v2\/projects\/[^/]+\/pipeline-runs$/.test(new URL(response.url()).pathname));
  await page.getByRole("button", { name: "生成可编辑场景与分镜" }).click();
  const storyboardOnly = await storyboardOnlyRequest;
  expect(storyboardOnly.request().postDataJSON()).toMatchObject({ stages: ["storyboard"] });
  await pollRun(request, workbench.apiOrigin, (await storyboardOnly.json() as { id: string }).id, "succeeded");

  const runCount = await requestCount(request, workbench.apiOrigin, projectId);
  await page.getByRole("button", { name: "生成可编辑场景与分镜" }).click();
  await expect(page.getByText("场景与分镜已经是最新版本；不会创建替换运行。", { exact: true })).toBeVisible();
  expect(await requestCount(request, workbench.apiOrigin, projectId)).toBe(runCount);
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
