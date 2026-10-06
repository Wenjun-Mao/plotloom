import { navigateToSecondaryTool, openServiceStatus } from "./workbench-controls";
import type { APIRequestContext, Page, Response as PlaywrightResponse } from "@playwright/test";
import { expect, test } from "./fixture";

type StageName = "story_bible" | "story_graph" | "scene_beats" | "storyboard";

/**
 * This is deliberately a browser-first contract test.  It uses the ordinary
 * demo authoring path and the real FastAPI server; no stage or review fixture
 * is created through an internal endpoint.
 */
test.describe("M1-B1 canonical workbench journey", () => {
  // M1-B0's visual baseline and Alpha acceptance target this authoring
  // workstation size.  It also keeps the three-column inspector usable while
  // exercising the ordinary pointer controls below.
  test.use({ viewport: { width: 1440, height: 900 } });

  test("authors, persists, reloads, deep-links, and approves a canonical project", async ({ page, request, workbench }) => {
    test.setTimeout(90_000);
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await expect(page.getByText("编辑与工具", { exact: true })).toBeVisible();

    const logline = "E2E：作者保留当前规范路线，编辑节拍与分镜并批准同一份故事。";
    const visualAnchors = "短黑发、旧工作服、右手绝缘手套\n琥珀读数映在护目镜上";
    const allowedStates = "focused\nstrained\nresolved";
    // Bootstrap the valid current prefix. Source-less Graph remains read-only.
    // Bible changes follow approval to prove their real downstream staleness.
    await navigateToStage(page, "05 分镜工作台");
    const created = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === "/api/v2/projects");
    await page.getByRole("button", { name: "保存分镜" }).click();
    expect((await created).ok()).toBeTruthy();
    await expect(page).toHaveURL(/[?&]project=/);
    const projectId = currentProjectId(page);

    await navigateToStage(page, "03 剧情 DAG");
    await expect(page.locator(".canonical-graph-reader")).toContainText("join_contract_1");
    await expect(page.getByRole("button", { name: "保存剧情图", exact: true })).toHaveCount(0);

    await navigateToStage(page, "04 场景节拍");
    // Author an explicit scene continuity state through the existing editor.
    await page.getByTestId("scene-card-scene_memory").click();
    const memoryEntry = page.getByTestId("continuity-场景入口连续性");
    await memoryEntry.getByRole("button", { name: "＋ 实体状态" }).click();
    await memoryEntry.getByLabel("实体", { exact: true }).selectOption("char_ruanxing");
    await memoryEntry.getByLabel("状态").fill("focused");
    await expect(memoryEntry.getByLabel("实体", { exact: true })).toHaveValue("char_ruanxing");
    await expect(memoryEntry.getByLabel("状态")).toHaveValue("focused");

    await page.getByTestId("scene-card-scene_arrival").click();
    const sceneTitle = "E2E M1-B1：抵达控制室";
    await page.getByLabel("场景标题").fill(sceneTitle);
    const beat = page.getByTestId("beat-card-b1");
    const beatDescription = "E2E：阮星撞开控制室气密门，读取新的琥珀证据。";
    await beat.getByLabel("节拍描述").fill(beatDescription);
    const cue = page.getByTestId("cue-card-cue_b1");
    const cueText = "安迪，琥珀读数还在。";
    await cue.getByLabel("对白文本").fill(cueText);
    await cue.getByLabel("预估时长（毫秒）").fill("4200");

    // Parent migration is explicit.  The confirmation names both stable IDs;
    // the cue's scene remains the same, so the downstream schedule stays
    // meaningful while the beat relationship is deliberately changed.
    await cue.getByLabel("迁移 cue 到节拍").selectOption("b2");
    const migration = page.getByTestId("relationship-migration-impact");
    await expect(migration).toContainText("cue_b1");
    await expect(migration).toContainText("b1");
    await expect(migration).toContainText("b2");
    await migration.getByTestId("confirm-relationship-migration").click();

    await savePatchedStage(page, projectId, "scene_beats", "保存节拍计划");
    await page.reload();
    await expect(page.getByLabel("场景标题")).toHaveValue(sceneTitle);
    await expect(page.getByTestId("beat-card-b1").getByLabel("节拍描述")).toHaveValue(beatDescription);
    await expect(page.getByTestId("cue-card-cue_b1").getByLabel("迁移 cue 到节拍")).toHaveValue("b2");
    await expect(page.getByTestId("cue-card-cue_b1").getByLabel("对白文本")).toHaveValue(cueText);
    await expect(page.getByTestId("cue-card-cue_b1").getByLabel("预估时长（毫秒）")).toHaveValue("4200");

    await navigateToStage(page, "05 分镜工作台");
    const action = "E2E M1-B1：阮星跨过气密门，确认控制室仍有一条可审计的选择。";
    await page.getByRole("button", { name: "编辑镜头细节", exact: true }).click();
    await page.getByRole("textbox", { name: "动作", exact: true }).fill(action);
    await expect(page.getByLabel("镜头 ID")).toHaveValue("shot_01");
    await page.getByLabel("镜头 ID").press("Tab");

    // AudioPlan, scheduled DialogueCue, required entity state, continuity,
    // and a ShotBeatLink are all mutable authored fields of a real shot.
    const audioPlan = page.getByRole("group", { name: "AudioPlan" });
    await audioPlan.getByLabel("描述").fill("E2E：气密门密封声与通风系统低鸣");
    const cueSchedule = page.getByRole("group", { name: "对白调度" });
    const scheduledCue = cueSchedule.getByRole("checkbox", { name: /琥珀读数/ });
    await scheduledCue.uncheck();
    await scheduledCue.check();
    await page.getByLabel("新增覆盖的节拍").selectOption("b2");
    await page.getByRole("button", { name: "添加覆盖" }).click();
    await expect(page.locator('[data-entity-key="link:shot_01:b2"]')).toBeVisible();
    const requiredStates = page.getByRole("group", { name: "镜头要求的实体状态" });
    await requiredStates.getByRole("button", { name: "＋ 添加实体状态" }).click();
    await requiredStates.getByLabel("状态").selectOption("focused");
    const entryState = page.getByText("镜头入口连续性", { exact: true });
    await entryState.click();
    await page.getByRole("textbox", { name: "备注（每行一条）" }).first().fill("E2E：右手绝缘手套与琥珀读数连续可见");
    const coverageWeight = page.locator('[data-entity-key="link:shot_01:b1"]').getByLabel("覆盖权重");
    await coverageWeight.fill("0.9");

    // A relationship migration previews every cross-scene reference.  Move a
    // shot away and back through two explicit confirmations so the verified
    // final canonical graph remains valid.
    await page.getByRole("button", { name: "编辑镜头 压力下坠" }).click();
    await expect(page.getByLabel("镜头 ID")).toHaveValue("shot_02");
    await page.getByLabel("迁移镜头到场景").selectOption("scene_diagnose");
    const shotMigration = page.getByTestId("shot-scene-migration-impact");
    await expect(shotMigration).toContainText("shot_02");
    await expect(shotMigration).toContainText("b2");
    await shotMigration.getByRole("button", { name: "确认迁移" }).click();
    await page.getByLabel("迁移镜头到场景").selectOption("scene_arrival");
    await expect(page.getByTestId("shot-scene-migration-impact")).toContainText("shot_02");
    await page.getByTestId("shot-scene-migration-impact").getByRole("button", { name: "确认迁移" }).click();

    // Deletion must disclose the exact Shot and the Cue/coverage consequences
    // before an author can decide.  This one is intentionally cancelled.
    await page.getByRole("button", { name: "编辑镜头 门开" }).click();
    await page.getByRole("button", { name: "删除镜头" }).click();
    const shotDeletion = page.getByTestId("shot-deletion-impact");
    await expect(shotDeletion).toContainText("shot_01");
    await expect(shotDeletion).toContainText("cue_b1");
    await expect(shotDeletion).toContainText("b1");
    await shotDeletion.getByRole("button", { name: "取消" }).click();
    await savePatchedStage(page, projectId, "storyboard", "保存分镜");
    await page.reload();
    await expect(page.getByLabel("镜头 ID")).toHaveValue("shot_01");
    await expect(page.getByRole("textbox", { name: "动作", exact: true })).toHaveValue(action);
    await expect(page.getByRole("group", { name: "AudioPlan" }).getByLabel("描述")).toHaveValue("E2E：气密门密封声与通风系统低鸣");
    await expect(page.getByRole("group", { name: "镜头要求的实体状态" }).getByLabel("状态")).toHaveValue("focused");
    await expect(page.locator('[data-entity-key="link:shot_01:b1"]').getByLabel("覆盖权重")).toHaveValue("0.9");

    // Saving each upstream stage marks the old local projection stale.  A
    // normal browser reload is the public way to obtain the server's complete
    // resulting dependency projection before a review decision is offered.
    await page.reload();
    await openServiceStatus(page);
    await expect(page.getByText("Plotloom 服务：已连接", { exact: true })).toBeVisible();
    await expectCanonicalHeads(request, workbench.apiOrigin, projectId);

    await navigateToStage(page, "02 故事圣经");
    await page.getByTestId("select-character-char_ruanxing").click();
    await expect(page).toHaveURL(/entity=bible%3Acharacter%3Achar_ruanxing/);
    await expect(page.getByRole("heading", { name: "角色检查器" })).toBeVisible();
    await page.reload();
    await expect(page).toHaveURL(/entity=bible%3Acharacter%3Achar_ruanxing/);
    await expect(page.getByLabel("姓名")).toHaveValue("阮星");

    await navigateToStage(page, "05 分镜工作台");
    await expect(page.getByRole("textbox", { name: "动作", exact: true })).toHaveValue(action);
    await page.getByLabel("审核人标签").fill("E2E local workbench reviewer");
    const approval = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === `/api/v2/projects/${projectId}/storyboard-approval`);
    await expect(page.getByRole("button", { name: "批准当前分镜" })).toBeEnabled();
    await page.getByRole("button", { name: "批准当前分镜" }).click();
    expect((await approval).status()).toBe(201);
    await expect(page.getByText("当前批准：E2E local workbench reviewer", { exact: true })).toBeVisible();

    const review = await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/storyboard-review`);
    expect(review.ok()).toBeTruthy();
    const reviewBody = await review.json() as {
      gateEvaluation: { results: Array<{ required: boolean; status: string }> } | null;
      activeApproval: { reviewer: string; decision: string; subjectRevision: number } | null;
      decisions: Array<{ active: boolean; decision: { decision: string; reviewer: string } }>;
    };
    expect(reviewBody.gateEvaluation).not.toBeNull();
    expect(reviewBody.gateEvaluation!.results.every((gate) => !gate.required || gate.status === "pass")).toBeTruthy();
    expect(reviewBody.activeApproval).toMatchObject({ reviewer: "E2E local workbench reviewer", decision: "approve", subjectRevision: 2 });
    expect(reviewBody.decisions).toContainEqual(expect.objectContaining({
      active: true,
      decision: expect.objectContaining({ decision: "approve", reviewer: "E2E local workbench reviewer" }),
    }));

    await navigateToStage(page, "02 故事圣经");
    await page.getByLabel("Logline").fill(logline);
    await page.getByTestId("select-character-char_ruanxing").click();
    await page.getByTestId("character-visual-anchors").fill(visualAnchors);
    await page.getByTestId("character-allowed-states").fill(allowedStates);
    await savePatchedStage(page, projectId, "story_bible", "保存故事圣经");
    await page.reload();
    await expect(page.getByLabel("Logline")).toHaveValue(logline);
    await expect(page.getByTestId("character-visual-anchors")).toHaveValue(visualAnchors);
    await expect(page.getByTestId("character-allowed-states")).toHaveValue(allowedStates);
    await expect(page.getByLabel("稳定 ID")).toHaveValue("char_ruanxing");
    const staleReview = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/storyboard-review`)).json();
    expect(staleReview.activeApproval).toBeNull();
    expect(staleReview.decisions).toContainEqual(expect.objectContaining({ decision: expect.objectContaining({ reviewer: "E2E local workbench reviewer" }) }));

    const stages = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`)).json();
    const graph = stages.stages.find((item: { head: { stage: string } }) => item.head.stage === "story_graph");
    const rejected = await request.patch(`${workbench.apiOrigin}/api/v2/projects/${projectId}/stages/story_graph`, { data: { expectedRevision: graph.head.revision, payload: graph.payload } });
    expect(rejected.status()).toBe(409);
    expect(await rejected.json()).toMatchObject({ code: "invalid_transition", message: expect.stringContaining("当前来源图草稿") });
    expect(await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/stages`)).json()).toEqual(stages);
  });
});

async function navigateToStage(page: Page, name: string): Promise<void> {
  const label = name.replace(/^\d+\s+/, "");
  await navigateToSecondaryTool(page, label);
}

async function savePatchedStage(page: Page, projectId: string, stage: StageName, label: string): Promise<void> {
  const saved = captureStagePatchResponse(page, projectId, stage);
  await page.getByRole("button", { name: label }).click();
  const response = await saved;
  expect(response.ok(), await response.text()).toBeTruthy();
}

function captureStagePatchResponse(page: Page, projectId: string, stage: StageName): Promise<PlaywrightResponse> {
  const path = `/api/v2/projects/${projectId}/stages/${stage}`;
  return page.waitForResponse((response) => response.request().method() === "PATCH"
    && new URL(response.url()).pathname === path);
}

function currentProjectId(page: Page): string {
  const projectId = new URL(page.url()).searchParams.get("project");
  expect(projectId).toBeTruthy();
  return projectId!;
}

async function expectCanonicalHeads(request: APIRequestContext, apiOrigin: string, projectId: string): Promise<void> {
  const response = await request.get(`${apiOrigin}/api/v2/projects/${projectId}/stages`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json() as { stages: Array<{ head: { stage: StageName; status: string; revision: number; schemaVersion: number } }> };
  expect(body.stages).toHaveLength(4);
  for (const stage of ["story_bible", "story_graph", "scene_beats", "storyboard"] as const) {
    expect(body.stages.find((candidate) => candidate.head.stage === stage)?.head).toMatchObject({
      stage,
      status: "ready",
      revision: stage === "story_bible" || stage === "story_graph" ? 1 : 2,
      schemaVersion: 2,
    });
  }
}
