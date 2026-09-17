import { expect, test } from "./fixture";
import type { Route } from "@playwright/test";

test("tests a profile only after saving public settings and keeps its key session-only", async ({ page, workbench }) => {
  const configuration = {
    profileSchemaVersion: 2, profileId: "default", profileVersion: 1, profileHash: "hash",
    textProvider: "openai-compatible", textBaseUrl: "https://provider.example/v1", textModel: "example-model",
    textAuthMode: "bearer", textCapabilities: { chatCompletions: true, jsonObject: false, jsonSchema: false, chatTemplateKwargs: false },
    textContextWindowTokens: 32768, textMaxOutputTokens: 8192, textTemperature: 0.2, textMaxConcurrency: 1,
    textConnectTimeoutSeconds: 10, textAttemptTimeoutSeconds: 300, redirectPolicy: "no_follow",
    requestExtension: "none", reasoningMode: "provider_default", extractionPolicy: { allowJsonFence: false, allowLeadingThinkBlock: false },
    stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 4096, storyboard: 4096 },
    maxSemanticCorrections: 2, presetId: "custom", presetVersion: "1",
  };
  const readiness = { profileId: "default", profileRevision: 1, state: "unverified", reasonCode: "readiness.not_checked", observedAt: null };
  const profile = { profileId: "default", displayName: "Default", configuration, revision: 1, enabled: true, availabilityRevision: 0, adapterId: "openai_compatible", adapterVersion: "1", createdAt: "now", updatedAt: "now", serverKeyAvailable: false, readiness };
  const calls: Array<{ method: string; body: string; sessionKey: string | undefined }> = [];
  await page.route("**/api/v2/text-provider-profiles**", async (route) => {
    const request = route.request();
    calls.push({ method: request.method(), body: request.postData() || "", sessionKey: request.headers()["x-plotloom-session-api-key"] });
    const pathname = new URL(request.url()).pathname;
    if (request.method() === "GET") {
      await route.fulfill({ json: { profiles: [profile], activeProfileId: "default", selectionRevision: 1, presets: {}, trustedAdapters: [{ adapterId: "openai_compatible", adapterVersion: "1" }] } });
    } else if (pathname.endsWith("/probe")) {
      await route.fulfill({ json: { ...readiness, state: "available", reasonCode: "readiness.models_verified", observedAt: "2026-09-10T12:00:00Z" } });
    } else {
      await route.fulfill({ json: { ...profile, revision: 2 } });
    }
  });

  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "供应商与会话 Key" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByLabel("受信任适配器")).toHaveValue("openai_compatible@1");
  await page.getByLabel("此 Profile 的临时 API Key").fill("test-session-secret");
  await page.getByRole("button", { name: "测试连接" }).click();
  await expect(page.getByText("后端已就绪：readiness.models_verified")).toBeVisible();

  // Profile hydration is intentionally eager and React development mode can
  // replay that read; only the action boundary is order-sensitive here.
  const writes = calls.filter((call) => call.method !== "GET");
  expect(calls.some((call) => call.method === "GET")).toBe(true);
  expect(writes.map((call) => call.method)).toEqual(["PUT", "POST"]);
  expect(writes[0].body).not.toContain("test-session-secret");
  expect(JSON.parse(writes[0].body)).toMatchObject({ adapterId: "openai_compatible", adapterVersion: "1" });
  expect(writes[0].sessionKey).toBeUndefined();
  expect(writes[1].body).toBe("");
  expect(writes[1].sessionKey).toBe("test-session-secret");
  await expect.poll(() => page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.getItem("plotloom:provider-session-keys") }))).toEqual({ local: 0, session: JSON.stringify({ default: "test-session-secret" }) });
});

test("keeps a disabled selected profile visible while rejecting new run admission", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "供应商与会话 Key" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();

  const disabled = page.waitForResponse((response) => response.request().method() === "PUT"
    && new URL(response.url()).pathname.endsWith("/text-provider-profiles/default/availability"));
  await page.getByRole("button", { name: "停用后端" }).click();
  expect((await disabled).ok()).toBeTruthy();
  await expect(page.getByText("此后端当前不可用")).toBeVisible();
  await expect(page.getByLabel("活动 Profile")).toHaveValue("default");
  await expect(page.getByRole("button", { name: "设为活动" })).toBeDisabled();

  const project = await request.post(`${workbench.apiOrigin}/api/v2/projects`, {
    data: { brief: { title: "停用 admission", synopsis: "停用 Profile 不应接纳新运行。" } },
  });
  expect(project.ok()).toBeTruthy();
  const projectId = (await project.json()).id as string;
  const rejected = await request.post(
    `${workbench.apiOrigin}/api/v2/projects/${projectId}/pipeline-runs`,
    { data: { stages: ["story_bible"], providerProfileId: "default" } },
  );
  expect(rejected.status()).toBe(409);
  expect((await rejected.json()).message).toContain("disabled");

  // This suite shares the production-shaped profile catalog. Restore the
  // availability mutation after proving admission rejects it so later journeys
  // begin from the fixture's enabled baseline.
  const disabledProfile = await request.get(`${workbench.apiOrigin}/api/v2/text-provider-profiles/default`);
  expect(disabledProfile.ok()).toBeTruthy();
  const { availabilityRevision } = await disabledProfile.json() as { availabilityRevision: number };
  const restored = await request.put(`${workbench.apiOrigin}/api/v2/text-provider-profiles/default/availability`, {
    data: { expectedAvailabilityRevision: availabilityRevision, enabled: true },
  });
  expect(restored.ok()).toBeTruthy();
});

test("merges availability without losing an unsaved profile draft, session key, or conflict state", async ({ page, request, workbench }) => {
  type StoredProfile = {
    revision: number;
    availabilityRevision: number;
    enabled: boolean;
    configuration: { profileHash: string; textModel: string };
  };
  const profileUrl = `${workbench.apiOrigin}/api/v2/text-provider-profiles/default`;
  const readProfile = async (): Promise<StoredProfile> => {
    const response = await request.get(profileUrl);
    expect(response.ok()).toBeTruthy();
    return response.json() as Promise<StoredProfile>;
  };
  let before = await readProfile();
  if (!before.enabled) {
    const reenabledForScenario = await request.put(`${profileUrl}/availability`, {
      data: { expectedAvailabilityRevision: before.availabilityRevision, enabled: true },
    });
    expect(reenabledForScenario.ok()).toBeTruthy();
    before = await readProfile();
  }

  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "供应商与会话 Key" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByLabel("文本认证").selectOption("bearer");
  await page.getByLabel("文本模型").fill("draft-model-before-toggle");
  await page.getByLabel("此 Profile 的临时 API Key").fill("draft-key-before-toggle");

  // The route still forwards the mutation to real FastAPI, but holds its
  // response so this asserts edits made while availability is in flight.
  let releaseAvailabilityResponse!: () => void;
  let upstreamReceived!: () => void;
  const responseHeld = new Promise<void>((resolve) => { releaseAvailabilityResponse = resolve; });
  const upstreamReceivedPromise = new Promise<void>((resolve) => { upstreamReceived = resolve; });
  const holdAvailability = async (route: Route) => {
    const upstream = await route.fetch();
    upstreamReceived();
    await responseHeld;
    await route.fulfill({ response: upstream });
  };
  await page.route("**/api/v2/text-provider-profiles/default/availability", holdAvailability);
  const disabled = page.waitForResponse((response) => response.request().method() === "PUT"
    && new URL(response.url()).pathname.endsWith("/text-provider-profiles/default/availability"));
  await page.getByRole("button", { name: "停用后端" }).click();
  await upstreamReceivedPromise;
  await page.getByLabel("文本模型").fill("draft-model-during-toggle");
  await page.getByLabel("此 Profile 的临时 API Key").fill("draft-key-during-toggle");
  releaseAvailabilityResponse();
  expect((await disabled).ok()).toBeTruthy();
  await page.unroute("**/api/v2/text-provider-profiles/default/availability", holdAvailability);

  await expect(page.getByText("此后端当前不可用")).toBeVisible();
  await expect(page.getByLabel("文本模型")).toHaveValue("draft-model-during-toggle");
  await expect(page.getByLabel("此 Profile 的临时 API Key")).toHaveValue("draft-key-during-toggle");
  const afterDisable = await readProfile();
  expect(afterDisable).toMatchObject({ revision: before.revision, enabled: false });
  expect(afterDisable.configuration.profileHash).toBe(before.configuration.profileHash);
  expect(afterDisable.configuration.textModel).toBe(before.configuration.textModel);

  const reenabled = page.waitForResponse((response) => response.request().method() === "PUT"
    && new URL(response.url()).pathname.endsWith("/text-provider-profiles/default/availability"));
  await page.getByRole("button", { name: "启用后端" }).click();
  expect((await reenabled).ok()).toBeTruthy();
  await expect(page.getByLabel("文本模型")).toHaveValue("draft-model-during-toggle");
  await expect(page.getByLabel("此 Profile 的临时 API Key")).toHaveValue("draft-key-during-toggle");
  const afterReenable = await readProfile();
  expect(afterReenable).toMatchObject({ revision: before.revision, enabled: true });
  expect(afterReenable.configuration.profileHash).toBe(before.configuration.profileHash);
  expect(afterReenable.configuration.textModel).toBe(before.configuration.textModel);

  // Advance availability outside the tab. The stale in-tab toggle must report
  // a 409 without reloading or discarding the still-unsaved public/key draft.
  const externalDisable = await request.put(`${profileUrl}/availability`, {
    data: { expectedAvailabilityRevision: afterReenable.availabilityRevision, enabled: false },
  });
  expect(externalDisable.ok()).toBeTruthy();
  await page.getByLabel("文本模型").fill("draft-model-after-conflict");
  await page.getByLabel("此 Profile 的临时 API Key").fill("draft-key-after-conflict");
  const conflict = page.waitForResponse((response) => response.request().method() === "PUT"
    && new URL(response.url()).pathname.endsWith("/text-provider-profiles/default/availability")
    && response.status() === 409);
  await page.getByRole("button", { name: "停用后端" }).click();
  expect((await conflict).status()).toBe(409);
  await expect(page.getByLabel("文本模型")).toHaveValue("draft-model-after-conflict");
  await expect(page.getByLabel("此 Profile 的临时 API Key")).toHaveValue("draft-key-after-conflict");
  const afterConflict = await readProfile();
  expect(afterConflict).toMatchObject({ revision: before.revision, enabled: false });
  expect(afterConflict.configuration.profileHash).toBe(before.configuration.profileHash);
  expect(JSON.stringify(afterConflict)).not.toContain("draft-key-after-conflict");

  await page.getByRole("button", { name: "保存设置" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  const afterExplicitSave = await readProfile();
  expect(afterExplicitSave.revision).toBe(before.revision + 1);
  expect(afterExplicitSave.configuration.textModel).toBe("draft-model-after-conflict");
  expect(afterExplicitSave.configuration.profileHash).not.toBe(before.configuration.profileHash);
  expect(JSON.stringify(afterExplicitSave)).not.toContain("draft-key-after-conflict");
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("plotloom:provider-session-keys"))).toBe(
    JSON.stringify({ default: "draft-key-after-conflict" }),
  );
  const finalProfile = await readProfile();
  const restored = await request.put(`${profileUrl}/availability`, {
    data: { expectedAvailabilityRevision: finalProfile.availabilityRevision, enabled: true },
  });
  expect(restored.ok()).toBeTruthy();
});

test("persists a copied profile through the real API without persisting its browser key", async ({ page, request, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "供应商与会话 Key" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();

  const promptAnswers = ["e2e_profile", "E2E Profile"];
  page.on("dialog", async (dialog) => {
    await dialog.accept(promptAnswers.shift() ?? "");
  });
  const createdResponse = page.waitForResponse((response) => {
    const request = response.request();
    return request.method() === "POST"
      && new URL(request.url()).pathname === "/api/v2/text-provider-profiles";
  });
  await page.getByRole("button", { name: "复制" }).click();
  expect((await createdResponse).ok()).toBeTruthy();
  await expect(page.getByLabel("活动 Profile")).toHaveValue("e2e_profile");

  await page.getByLabel("文本模型").fill("e2e-model-after-save");
  await page.getByLabel("文本认证").selectOption("bearer");
  await page.getByLabel("此 Profile 的临时 API Key").fill("e2e-browser-only-secret");
  await page.getByRole("button", { name: "保存设置" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();

  const storedResponse = await request.get(
    `${workbench.apiOrigin}/api/v2/text-provider-profiles/e2e_profile`,
  );
  expect(storedResponse.ok()).toBeTruthy();
  const stored = await storedResponse.json() as Record<string, unknown>;
  expect((stored.configuration as Record<string, unknown>).textModel).toBe(
    "e2e-model-after-save",
  );
  expect(JSON.stringify(stored)).not.toContain("e2e-browser-only-secret");
  expect(JSON.stringify(stored)).not.toContain("apiKey");
  await expect.poll(() => page.evaluate(() => ({
    local: localStorage.length,
    session: sessionStorage.getItem("plotloom:provider-session-keys"),
  }))).toEqual({
    local: 0,
    session: JSON.stringify({ e2e_profile: "e2e-browser-only-secret" }),
  });

  await page.getByRole("button", { name: "供应商与会话 Key" }).click();
  // Reopening settings intentionally selects the server's active profile.
  // The copied profile is not active, so select it explicitly before delete.
  await page.getByLabel("活动 Profile").selectOption("e2e_profile");
  await expect(page.getByRole("button", { name: "删除" })).toBeEnabled();
  const deletedResponse = page.waitForResponse((response) => {
    const incoming = response.request();
    return incoming.method() === "DELETE"
      && new URL(incoming.url()).pathname === "/api/v2/text-provider-profiles/e2e_profile";
  });
  await page.getByRole("button", { name: "删除" }).click();
  expect((await deletedResponse).ok()).toBeTruthy();
  await expect.poll(() => page.evaluate(() =>
    sessionStorage.getItem("plotloom:provider-session-keys"),
  )).toBeNull();
});
