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
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    await expect(page.getByRole("navigation", { name: "工作台阶段" })).toBeVisible();

    // Bootstrap through the final stage so the server receives a contiguous,
    // valid canonical prefix.  Subsequent writes exercise each individual
    // editor's ordinary PATCH path rather than relying on API setup.
    await navigateToStage(page, "05 分镜工作台");
    const created = page.waitForResponse((response) => response.request().method() === "POST"
      && new URL(response.url()).pathname === "/api/v2/projects");
    await page.getByRole("button", { name: "保存分镜" }).click();
    expect((await created).ok()).toBeTruthy();
    await expect(page).toHaveURL(/[?&]project=/);
    const projectId = currentProjectId(page);

    await navigateToStage(page, "02 故事圣经");
    const logline = "E2E M1-B1：作者在四个规范阶段连续完成并批准同一份故事。";
    await page.getByLabel("Logline").fill(logline);
    // The entities remain authored only in the Bible.  Exercise anchors and
    // the allowed-state vocabulary through its ordinary inspector, then
    // prove that the selected stable identity survives a document reload.
    await page.getByTestId("select-character-char_ruanxing").click();
    const visualAnchors = "短黑发、旧工作服、右手绝缘手套\n琥珀读数映在护目镜上";
    const allowedStates = "focused\nstrained\nresolved";
    await page.getByTestId("character-visual-anchors").fill(visualAnchors);
    await page.getByTestId("character-allowed-states").fill(allowedStates);
    await savePatchedStage(page, projectId, "story_bible", "保存故事圣经");
    await page.reload();
    await expect(page.getByTestId("character-visual-anchors")).toHaveValue(visualAnchors);
    await expect(page.getByTestId("character-allowed-states")).toHaveValue(allowedStates);
    await expect(page.getByLabel("稳定 ID")).toHaveValue("char_ruanxing");

    await navigateToStage(page, "03 剧情 DAG");
    // A relationship edit is first made on the durable edge identity.  The
    // selected edge is a genuine ReactFlow edge, rather than a test-only
    // backdoor.  It receives a second typed state effect.
    await selectGraphEntity(page, "edge", "e2");
    await expect(page.getByLabel("边 ID")).toHaveValue("e2");
    await page.getByRole("button", { name: "添加效果" }).click();
    await page.getByLabel("状态键 2").fill("authorProof");
    await page.getByLabel("状态值 2").fill("retained");
    await page.getByRole("button", { name: "添加实体状态" }).click();
    await page.getByLabel("实体状态类型 1").selectOption("character");
    await page.getByLabel("实体状态 ID 1").fill("char_ruanxing");
    await page.getByLabel("实体状态值 1").fill("focused");

    // The corresponding join contract is separately addressable and retains
    // its immutable ID while its authored reconciliation note changes.
    await selectGraphEntity(page, "node", "join");
    await page.getByRole("button", { name: "编辑合同 join_contract_1" }).click();
    await expect(page.getByLabel("合同 ID")).toHaveValue("join_contract_1");
    const contractNotes = "E2E：合同 ID 保持不变，作者已审阅两条来路。";
    await page.getByLabel("备注").fill(contractNotes);
    await savePatchedStage(page, projectId, "story_graph", "保存剧情图");
    await page.reload();
    await selectGraphEntity(page, "edge", "e2");
    const authorProof = page.locator('[data-focus-key="graph:edge:e2:stateEffects.authorProof"]');
    await expect(authorProof).toHaveValue("authorProof");
    await expect(authorProof.locator("xpath=following-sibling::input")).toHaveValue("retained");
    await expect(page.getByLabel("实体状态类型 1")).toHaveValue("character");
    await expect(page.getByLabel("实体状态 ID 1")).toHaveValue("char_ruanxing");
    await expect(page.getByLabel("实体状态值 1")).toHaveValue("focused");
    await selectGraphEntity(page, "node", "join");
    await page.getByRole("button", { name: "编辑合同 join_contract_1" }).click();
    await expect(page.getByLabel("备注")).toHaveValue(contractNotes);

    await navigateToStage(page, "04 场景节拍");
    // The graph's newly authored typed effect is a post-edge assignment.  Its
    // target is scene_memory's first entry, so make that direct boundary
    // explicit through the ordinary scene editor before saving the aggregate.
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
    await page.getByLabel("动作").fill(action);
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
    await expect(page.getByLabel("动作")).toHaveValue(action);
    await expect(page.getByRole("group", { name: "AudioPlan" }).getByLabel("描述")).toHaveValue("E2E：气密门密封声与通风系统低鸣");
    await expect(page.getByRole("group", { name: "镜头要求的实体状态" }).getByLabel("状态")).toHaveValue("focused");
    await expect(page.locator('[data-entity-key="link:shot_01:b1"]').getByLabel("覆盖权重")).toHaveValue("0.9");

    // Saving each upstream stage marks the old local projection stale.  A
    // normal browser reload is the public way to obtain the server's complete
    // resulting dependency projection before a review decision is offered.
    await page.reload();
    await expect(page.getByText("Plotloom 服务：已连接", { exact: true })).toBeVisible();
    await expectCanonicalHeads(request, workbench.apiOrigin, projectId);

    await navigateToStage(page, "02 故事圣经");
    await expect(page.getByLabel("Logline")).toHaveValue(logline);
    await page.getByTestId("select-character-char_ruanxing").click();
    await expect(page).toHaveURL(/entity=bible%3Acharacter%3Achar_ruanxing/);
    await expect(page.getByRole("heading", { name: "角色检查器" })).toBeVisible();
    await page.reload();
    await expect(page).toHaveURL(/entity=bible%3Acharacter%3Achar_ruanxing/);
    await expect(page.getByLabel("姓名")).toHaveValue("阮星");

    await navigateToStage(page, "05 分镜工作台");
    await expect(page.getByLabel("动作")).toHaveValue(action);
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

    // A genuinely invalid author edit must return the server's structured
    // domain issues to the editor.  This is deliberately after approval so it
    // cannot be mistaken for a test-only project bootstrap or alter the
    // approved canonical revision.
    await navigateToStage(page, "03 剧情 DAG");
    await page.getByTestId("graph-node-add").click();
    const invalidGraphSave = captureStagePatchResponse(page, projectId, "story_graph");
    await page.getByRole("button", { name: "保存剧情图" }).click();
    expect((await invalidGraphSave).status()).toBe(422);
    await expect(page.getByText("合同问题", { exact: true })).toBeVisible();
    const issueButton = page.getByRole("button", { name: /non-ending nodes must have an outgoing edge/ });
    await expect(issueButton).toBeVisible();
    await issueButton.click();
    await expect(page.getByLabel("节点 ID")).toBeVisible();
  });
});

async function navigateToStage(page: Page, name: string): Promise<void> {
  const label = name.replace(/^\d+\s+/, "");
  await page.getByRole("navigation", { name: "工作台阶段" })
    .getByRole("button", { name: new RegExp(escapeRegex(label)) }).click();
}

async function selectGraphEntity(page: Page, kind: "node" | "edge", id: string): Promise<void> {
  await page.getByTestId(`graph-select-${kind}-${id}`).click();
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
      revision: 2,
      schemaVersion: 2,
    });
  }
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
