import { navigateToSecondaryTool, openTechnicalDetails } from "./workbench-controls";
import type { APIRequestContext, Page, Response as PlaywrightResponse, TestInfo } from "@playwright/test";
import { expect, test } from "./fixture";

/**
 * A browser refresh must not treat the current active profile as authority for
 * a previously-created run.  This journey deliberately creates the run via
 * the public API with a separate request context, so the tab begins without
 * its original session key just as it would after a reload/reopen elsewhere.
 */
test("a bearer run waits for its frozen profile key and resumes without switching profiles", async ({ page, request, workbench }, info) => {
  const projectId = await createDemoProject(page, workbench.frontendOrigin);
  const frozenProfileId = "frozen_bearer";
  await configureFrozenBearerProfile(request, workbench.apiOrigin, workbench.providerOrigin, frozenProfileId);

  const held = await request.post(`${workbench.providerOrigin}/control/response-hold`, {
    data: { enabled: true },
  });
  expect(held.ok()).toBeTruthy();

  const initialSessionKey = "seed-key-never-stored-in-browser";
  const started = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/pipeline-runs`, {
    headers: { "X-Plotloom-Session-API-Key": initialSessionKey },
    data: { stages: ["story_bible"], providerProfileId: frozenProfileId },
  });
  expect(started.status()).toBe(202);
  const sourceRun = await started.json() as { id: string; providerSnapshot: { profileId: string } };
  expect(sourceRun.providerSnapshot.profileId).toBe(frozenProfileId);
  await waitForRunStatus(request, workbench.apiOrigin, sourceRun.id, "running");

  let automaticResumeRequests = 0;
  let auditingReads = true;
  let auditWrites = 0;
  page.on("request", (outgoing) => {
    if (auditingReads && !["GET", "HEAD"].includes(outgoing.method()) && new URL(outgoing.url()).pathname.startsWith("/api/v2/")) auditWrites += 1;
    if (outgoing.method() === "POST" && new URL(outgoing.url()).pathname === `/api/v2/runs/${sourceRun.id}/resume`) {
      automaticResumeRequests += 1;
    }
  });

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${encodeURIComponent(projectId)}&stage=trace&run=${encodeURIComponent(sourceRun.id)}`);
  await openTechnicalDetails(page);
  await expect(page.getByRole("alert")).toContainText(`配置标识：${frozenProfileId}`);
  await expect(page.getByRole("alert")).toContainText("补充当前标签页密钥");
  await expect(page.getByText("此任务缺少可用密钥", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看此任务的模型配置" })).toBeVisible();
  await captureCredentialGuidance(page, info, "missing-key");

  // Read-only catalog faults must neither resume the frozen run nor open a
  // different profile. Restore the real catalog before the existing key flow.
  const catalogRoute = "**/api/v2/text-provider-profiles";
  const traceUrl = page.url();
  for (const issue of ["missing-profile", "read-failed"] as const) {
    await page.route(catalogRoute, async route => {
      if (route.request().method() !== "GET") return route.continue();
      if (issue === "read-failed") {
        await route.fulfill({ status: 503, json: { detail: "QA catalog read unavailable" } });
      } else {
        const response = await route.fetch();
        const catalog = await response.json();
        catalog.profiles = catalog.profiles.filter((profile: { profileId: string }) => profile.profileId !== frozenProfileId);
        await route.fulfill({ response, json: catalog });
      }
    });
    await page.goto(traceUrl);
    await expect(page.getByRole("alert")).toContainText(issue === "missing-profile" ? "模型配置已不存在" : "暂时无法读取此任务的模型配置");
    if (issue === "read-failed") await expect(page.getByRole("alert")).toContainText("请刷新页面后重试读取");
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(page.getByText("此任务缺少可用密钥", { exact: true })).not.toBeVisible();
    expect(automaticResumeRequests).toBe(0);
    await captureCredentialGuidance(page, info, issue);
    await page.unroute(catalogRoute);
  }
  await page.goto(traceUrl);
  await openTechnicalDetails(page);
  await expect(page.getByText("此任务缺少可用密钥", { exact: true })).toBeVisible();
  await page.waitForTimeout(250);
  expect(automaticResumeRequests).toBe(0);
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("plotloom:provider-session-keys"))).toBeNull();

  await page.getByRole("button", { name: "查看此任务的模型配置" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByLabel("当前编辑的模型配置")).toHaveValue(frozenProfileId);
  await captureCredentialGuidance(page, info, "frozen-settings");
  expect(auditWrites).toBe(0);
  auditingReads = false;
  await page.getByLabel("当前配置的临时密钥").fill("browser-frozen-profile-key");
  const settingsSaved = page.waitForResponse((response) => response.request().method() === "PUT"
    && new URL(response.url()).pathname === `/api/v2/text-provider-profiles/${frozenProfileId}`);
  await page.getByRole("button", { name: "保存设置" }).click();
  expect((await settingsSaved).ok()).toBeTruthy();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("plotloom:provider-session-keys"))).toBe(
    JSON.stringify({ [frozenProfileId]: "browser-frozen-profile-key" }),
  );

  const manualResume = page.waitForRequest((outgoing) => outgoing.method() === "POST"
    && new URL(outgoing.url()).pathname === `/api/v2/runs/${sourceRun.id}/resume`);
  await page.getByRole("button", { name: "继续运行" }).click();
  expect((await manualResume).headers()["x-plotloom-session-api-key"]).toBe("browser-frozen-profile-key");
  expect(automaticResumeRequests).toBe(1);

  const released = await request.post(`${workbench.providerOrigin}/control/response-hold`, {
    data: { enabled: false },
  });
  expect(released.ok()).toBeTruthy();
  const completed = await waitForRunStatus(request, workbench.apiOrigin, sourceRun.id, "succeeded");
  expect(completed.providerSnapshot.profileId).toBe(frozenProfileId);

  const catalog = await json<{ activeProfileId: string; profiles: Array<{ profileId: string; serverKeyAvailable: boolean }> }>(
    await request.get(`${workbench.apiOrigin}/api/v2/text-provider-profiles`),
  );
  expect(catalog.activeProfileId).toBe("default");
  expect(catalog.profiles.find((profile) => profile.profileId === frozenProfileId)).toMatchObject({ serverKeyAvailable: false });
});

async function captureCredentialGuidance(page: Page, info: TestInfo, state: string) {
  for (const size of [{ width: 1700, height: 900 }, { width: 1280, height: 768 }, { width: 1280, height: 460 }]) {
    await page.setViewportSize(size);
    const target = state === "frozen-settings" ? page.getByRole("dialog").locator(".modal-card") : page.getByRole("alert");
    if (state === "frozen-settings") await page.getByRole("dialog").locator(".modal-body").evaluate(element => { element.scrollTop = 0; });
    else await target.evaluate(element => element.scrollIntoView({ block: "center" }));
    await expect(target).toBeVisible();
    await page.screenshot({ path: info.outputPath(`frozen-${state}-${size.width}x${size.height}.png`) });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);
    if (state === "frozen-settings") {
      await page.getByLabel("当前配置的临时密钥").scrollIntoViewIfNeeded();
      await page.screenshot({ path: info.outputPath(`frozen-settings-key-${size.width}x${size.height}.png`) });
    }
    if (state === "missing-key") {
      const notice = page.locator(".inspector-run .notice");
      await notice.scrollIntoViewIfNeeded();
      await page.screenshot({ path: info.outputPath(`frozen-inspector-${size.width}x${size.height}.png`) });
    }
  }
}

async function configureFrozenBearerProfile(
  request: APIRequestContext,
  apiOrigin: string,
  providerOrigin: string,
  profileId: string,
): Promise<void> {
  const created = await request.post(`${apiOrigin}/api/v2/text-provider-profiles`, {
    data: { profileId, displayName: "Frozen browser-key profile", copyFromProfileId: "default" },
  });
  expect(created.status()).toBe(201);
  const profile = await json<{ revision: number; configuration: Record<string, unknown> }>(created);
  const updated = await request.put(`${apiOrigin}/api/v2/text-provider-profiles/${profileId}`, {
    data: {
      expectedRevision: profile.revision,
      displayName: "Frozen browser-key profile",
      configuration: {
        ...profile.configuration,
        profileId,
        profileHash: "",
        textProvider: "external-openai-fake",
        textBaseUrl: `${providerOrigin}/v1`,
        textModel: "frozen-browser-key-model",
        textAuthMode: "bearer",
        textCapabilities: { chatCompletions: true, jsonObject: false, jsonSchema: true, chatTemplateKwargs: false },
        presetId: "custom",
      },
    },
  });
  expect(updated.ok()).toBeTruthy();
}

async function createDemoProject(page: Page, frontendOrigin: string): Promise<string> {
  await page.goto(`${frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await navigateToSecondaryTool(page, "分镜工作台");
  const created = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === "/api/v2/projects");
  await page.getByRole("button", { name: "保存分镜" }).click();
  expect((await created).ok()).toBeTruthy();
  await expect(page).toHaveURL(/[?&]project=/);
  const projectId = new URL(page.url()).searchParams.get("project");
  expect(projectId).toBeTruthy();
  return projectId!;
}

async function waitForRunStatus(
  request: APIRequestContext,
  apiOrigin: string,
  runId: string,
  expectedStatus: string,
): Promise<{ status: string; providerSnapshot: { profileId: string } }> {
  const deadline = Date.now() + 25_000;
  let latest: { status: string; providerSnapshot: { profileId: string } } | undefined;
  while (Date.now() < deadline) {
    const observed = await json<{ status: string; providerSnapshot: { profileId: string } }>(
      await request.get(`${apiOrigin}/api/v2/runs/${runId}`),
    );
    latest = observed;
    if (observed.status === expectedStatus) return observed;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`run ${runId} did not reach ${expectedStatus}: ${JSON.stringify(latest)}`);
}

async function json<T>(response: PlaywrightResponse | Awaited<ReturnType<APIRequestContext["get"]>>): Promise<T> {
  expect(response.ok()).toBeTruthy();
  return response.json() as Promise<T>;
}
