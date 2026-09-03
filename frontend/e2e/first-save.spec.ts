import type { APIRequestContext, Page, Request as PlaywrightRequest, Response as PlaywrightResponse, Route } from "@playwright/test";
import { expect, test } from "./fixture";

type InitialStage = { stage: string; payload: unknown };
type ProjectCreateBody = { brief: unknown; initialStages: InitialStage[] };

test.describe("first-save project bootstrap", () => {
  test("creates the Story Bible prefix in one request, hydrates it, and restores it after reload", async ({ page, request, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await expect(page.getByText("教学草案", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "故事圣经" }).click();

    const logline = "E2E：未保存工作台从故事圣经开始建立规范项目。";
    const premise = "E2E：一份作者填写的故事前提必须随首次保存成为规范数据。";
    await page.getByLabel("Logline").fill(logline);
    await page.getByLabel("故事前提").fill(premise);
    const created = captureProjectCreate(page);
    await page.getByRole("button", { name: "保存故事圣经" }).click();
    const createRequest = await created;

    await expect(page).toHaveURL(/\?project=/);
    await expect(page.getByLabel("Logline")).toHaveValue(logline);
    await expect(page.getByLabel("故事前提")).toHaveValue(premise);
    const projectId = currentProjectId(page);
    const requestBody = createRequest.postDataJSON() as ProjectCreateBody;
    const submittedBible = requestBody.initialStages.find((stage) => stage.stage === "story_bible");
    expect(submittedBible).toBeTruthy();
    await expectCanonicalStage(request, workbench.apiOrigin, projectId, "story_bible", submittedBible!.payload);

    await page.reload();
    await expect(page.getByText("API 已连接", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "故事圣经" }).click();
    await expect(page.getByLabel("Logline")).toHaveValue(logline);
    await expect(page.getByLabel("故事前提")).toHaveValue(premise);
  });

  test("keeps the ordinary Brief-first workflow and persists the later Story Bible edit", async ({ page, request, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    const title = "E2E Brief-first project";
    await page.getByLabel("片名").fill(title);
    await page.getByRole("button", { name: "保存简报" }).click();
    await expect(page).toHaveURL(/\?project=/);
    const projectId = currentProjectId(page);

    await page.getByRole("button", { name: "故事圣经" }).click();
    const logline = "E2E：先保存简报，再保存故事圣经。";
    await page.getByLabel("Logline").fill(logline);
    await page.getByLabel("故事前提").fill("先建立项目，再为它写入第一条可追溯的故事规范。");
    // The canonical read below is only valid after the PATCH response: waiting
    // for the request alone races the backend transaction and can read the
    // preceding stage revision.
    const stagePatch = captureStagePatchResponse(page, projectId, "story_bible");
    await page.getByRole("button", { name: "保存故事圣经" }).click();
    const stageResponse = await stagePatch;
    expect(stageResponse.ok()).toBeTruthy();
    const stageRequest = stageResponse.request();
    const submittedPayload = (stageRequest.postDataJSON() as { payload: unknown }).payload;
    await expectCanonicalStage(request, workbench.apiOrigin, projectId, "story_bible", submittedPayload);

    await page.reload();
    await expect(page.getByText("API 已连接", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "故事圣经" }).click();
    await expect(page.getByLabel("Logline")).toHaveValue(logline);
  });

  test("persists a complete storyboard prefix and renders it after a browser refresh", async ({ page, request, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "分镜工作台" }).click();
    const action = "E2E：刷新后仍能看到这条已持久化的分镜动作。";
    await page.getByLabel("动作").fill(action);
    const created = captureProjectCreate(page);
    await page.getByRole("button", { name: "保存分镜" }).click();
    const createRequest = await created;

    await expect(page).toHaveURL(/\?project=/);
    const projectId = currentProjectId(page);
    const requestBody = createRequest.postDataJSON() as ProjectCreateBody;
    expect(requestBody.initialStages.map((stage) => stage.stage)).toEqual([
      "story_bible", "story_graph", "scene_beats", "storyboard",
    ]);
    const submittedStoryboard = requestBody.initialStages.find(
      (stage) => stage.stage === "storyboard",
    );
    expect(submittedStoryboard).toBeTruthy();
    await expectCanonicalStage(
      request,
      workbench.apiOrigin,
      projectId,
      "storyboard",
      submittedStoryboard!.payload,
    );

    await page.reload();
    await expect(page.getByText("API 已连接", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "分镜工作台" }).click();
    await expect(page.getByLabel("动作")).toHaveValue(action);
  });

  test("retains an unsaved Story Bible draft and reuses its idempotency key after a transient create failure", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "故事圣经" }).click();
    const logline = "E2E：失败后仍可安全重试同一份首次保存。";
    await page.getByLabel("Logline").fill(logline);

    const idempotencyKeys: string[] = [];
    let failedOnce = false;
    const failFirstCreate = async (route: Route) => {
      const incoming = route.request();
      if (incoming.method() === "POST" && new URL(incoming.url()).pathname === "/api/v2/projects") {
        const key = incoming.headers()["idempotency-key"];
        if (key) idempotencyKeys.push(key);
        if (!failedOnce) {
          failedOnce = true;
          await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ message: "temporary E2E failure" }) });
          return;
        }
      }
      await route.continue();
    };
    await page.route("**/api/v2/projects", failFirstCreate);
    try {
      await page.getByRole("button", { name: "保存故事圣经" }).click();
      await expect(page.getByRole("alert")).toContainText("temporary E2E failure");
      expect(page.url()).not.toContain("project=");
      await expect(page.getByLabel("Logline")).toHaveValue(logline);

      await page.getByRole("button", { name: "保存故事圣经" }).click();
      await expect(page).toHaveURL(/\?project=/);
      expect(idempotencyKeys).toHaveLength(2);
      expect(idempotencyKeys[1]).toBe(idempotencyKeys[0]);
    } finally {
      await page.unroute("**/api/v2/projects", failFirstCreate);
    }
  });
});

function captureProjectCreate(page: Page): Promise<PlaywrightRequest> {
  return page.waitForRequest((request) => request.method() === "POST" && new URL(request.url()).pathname === "/api/v2/projects");
}

function captureStagePatchResponse(page: Page, projectId: string, stage: string): Promise<PlaywrightResponse> {
  const expectedPath = `/api/v2/projects/${projectId}/stages/${stage}`;
  return page.waitForResponse((response) => {
    const request = response.request();
    return request.method() === "PATCH" && new URL(request.url()).pathname === expectedPath;
  });
}

function currentProjectId(page: Page): string {
  const projectId = new URL(page.url()).searchParams.get("project");
  expect(projectId).toBeTruthy();
  return projectId!;
}

async function expectCanonicalStage(
  request: APIRequestContext,
  apiOrigin: string,
  projectId: string,
  stageName: string,
  expectedPayload: unknown,
): Promise<void> {
  const response = await request.get(`${apiOrigin}/api/v2/projects/${projectId}/stages`);
  expect(response.ok()).toBeTruthy();
  const body = await response.json() as { stages: Array<{ head: { stage: string; status: string; revision: number }; payload: unknown }> };
  const stage = body.stages.find((candidate) => candidate.head.stage === stageName);
  expect(stage?.head).toMatchObject({ stage: stageName, status: "ready", revision: 1 });
  expect(stage?.payload).toEqual(expectedPayload);
}
