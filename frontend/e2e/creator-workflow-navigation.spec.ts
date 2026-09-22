import { expect, test } from "./fixture";
import { changeScript, createScriptProject, endpoint, json, writeDelivery } from "./f5a-fixture";

async function acceptStoryboardReview(request: import("@playwright/test").APIRequestContext, origin: string, projectId: string) {
  const prepared = await json(request.post(`${endpoint(origin, projectId)}/candidates`));
  await writeDelivery(prepared);
  await json(request.post(`${endpoint(origin, projectId)}/candidates/${prepared.jobId}/refresh`));
  await json(request.post(`${endpoint(origin, projectId)}/accept`, { data: { jobId: prepared.jobId, expectedReviewRevision: prepared.expectedReviewRevision, binding: prepared.binding } }));
}

test("keeps source-owned workflow targets project-scoped and separate from legacy shot media", async ({ page, request, workbench }) => {
  const firstProject = await createScriptProject(request, workbench.apiOrigin, "workflow-navigation-a");
  const secondProject = await createScriptProject(request, workbench.apiOrigin, "workflow-navigation-b");

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${firstProject}&stage=source#art`);
  const workflow = page.getByRole("navigation", { name: "创作流程" });
  const topbarLabel = page.locator(".topbar > div").first().locator("strong");
  await expect(workflow.getByRole("link", { name: "美术参考" })).toHaveAttribute("href", `?project=${firstProject}&stage=source#art`);
  await expect(page.getByRole("heading", { name: "美术参考", exact: true })).toBeVisible();
  await expect(page.getByTestId("art-review")).toBeVisible();
  await expect(page.locator(".source-outline-page")).toHaveAttribute("data-project-id", firstProject);
  await expect(page.getByTestId("source-outline-source")).not.toBeVisible();
  await expect(page.getByLabel("来源正文或 treatment")).not.toBeVisible();
  await expect(page.getByTestId("art-review").locator("header > span")).toHaveText("美术参考");
  await expect(page.getByTestId("art-review").locator(":scope > small").first()).toContainText("参考研究在下方单独显示");
  await expect(page.getByTestId("art-review").locator(":scope > small").first()).not.toContainText("F3B");
  await expect(topbarLabel).toHaveText("美术参考");
  await expect(workflow.getByRole("link", { name: "美术参考" })).toHaveAttribute("aria-current", "step");
  await expect(workflow.getByRole("link", { name: "剧本" })).not.toHaveAttribute("aria-current", "step");

  await workflow.getByRole("link", { name: "剧本" }).click();
  await expect(page).toHaveURL(new RegExp(`project=${firstProject}&stage=source#script$`));
  await expect(page.getByRole("heading", { name: "剧本", exact: true })).toBeVisible();
  await expect(page.getByTestId("script-review")).toBeVisible();
  await expect(page.getByTestId("source-outline-source")).not.toBeVisible();
  await expect(page.getByTestId("script-review").locator("header > span")).toHaveText("剧本");
  await expect(topbarLabel).toHaveText("剧本");
  await expect(workflow.getByRole("link", { name: "剧本" })).toHaveAttribute("aria-current", "step");
  await expect(workflow.getByRole("link", { name: "美术参考" })).not.toHaveAttribute("aria-current", "step");

  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`project=${firstProject}&stage=source#art$`));
  await expect(page.getByRole("heading", { name: "美术参考", exact: true })).toBeVisible();
  await expect(page.getByTestId("art-review")).toBeVisible();
  await expect(workflow.getByRole("link", { name: "美术参考" })).toHaveAttribute("aria-current", "step");
  await page.goForward();
  await expect(page).toHaveURL(new RegExp(`project=${firstProject}&stage=source#script$`));
  await expect(page.getByRole("heading", { name: "剧本", exact: true })).toBeVisible();
  await expect(page.getByTestId("script-review")).toBeVisible();

  await workflow.getByRole("link", { name: "分镜评审" }).click();
  await expect(page).toHaveURL(new RegExp(`project=${firstProject}&stage=source#storyboard-review$`));
  await expect(page.getByRole("heading", { name: "分镜评审", exact: true })).toBeVisible();
  await expect(page.getByTestId("storyboard-review")).toBeVisible();
  await expect(page.getByTestId("source-outline-source")).not.toBeVisible();
  await expect(page.getByTestId("storyboard-review").locator("header > span")).toHaveText("分镜评审");
  await expect(topbarLabel).toHaveText("分镜评审");
  await page.getByText("编辑与工具", { exact: true }).click();
  await page.getByRole("button", { name: /镜头与媒体工作台/ }).click();
  await expect(page).toHaveURL(new RegExp(`project=${firstProject}&stage=storyboard$`));
  await expect(page.getByRole("heading", { name: "分镜工作台" })).toBeVisible();

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${secondProject}&stage=source#art`);
  await expect(page.locator(".source-outline-page")).toHaveAttribute("data-project-id", secondProject);
  await expect(page.locator(".source-outline-page")).not.toContainText("F5A workflow-navigation-a");
  await expect(page.getByTestId("art-review")).toBeVisible();

  await workflow.getByRole("link", { name: "来源与大纲" }).click();
  await expect(page).toHaveURL(new RegExp(`project=${secondProject}&stage=source#source$`));
  await expect(page.getByRole("heading", { name: "来源与小说大纲", exact: true })).toBeVisible();
  const sourceText = page.getByLabel("来源正文或 treatment");
  await sourceText.fill("保留的未保存来源草稿");
  await workflow.getByRole("link", { name: "美术参考" }).click();
  await expect(sourceText).not.toBeVisible();
  await workflow.getByRole("link", { name: "来源与大纲" }).click();
  await expect(sourceText).toHaveValue("保留的未保存来源草稿");

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${secondProject}&stage=source#not-a-source-owner`);
  await expect(page.getByRole("heading", { name: "来源与小说大纲", exact: true })).toBeVisible();
  await expect(page.getByTestId("source-outline-source")).toBeVisible();
  await expect(workflow.getByRole("link", { name: "来源与大纲" })).toHaveAttribute("aria-current", "step");
});

test("keeps missing and stale F5A review explanations at their source-bound owner", async ({ page, request, workbench }) => {
  const projectId = await createScriptProject(request, workbench.apiOrigin, "workflow-f5a-state");

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#storyboard-review`);
  const review = page.getByTestId("storyboard-review");
  await expect(review).toContainText("尚无 review");
  await expect(review).toContainText("准备并复制 storyboard specialist handoff");
  await expect(page.getByRole("heading", { name: "分镜评审", exact: true })).toBeVisible();

  await acceptStoryboardReview(request, workbench.apiOrigin, projectId);
  await changeScript(request, workbench.apiOrigin, projectId);
  await page.reload();
  await expect(review).toContainText("上下文已过期");
  await expect(review).toContainText("已接受剧本 r");
  await expect(review).not.toContainText("F4 script r");
  await expect(review).toContainText("不是 Plotloom 的 shots、播放内容、媒体提示词或投产许可");
});

test("keeps an independent owner usable when the aggregate source read fails", async ({ page, request, workbench }) => {
  const projectId = await createScriptProject(request, workbench.apiOrigin, "workflow-independent-owner");
  await page.route(`**/api/v2/projects/${projectId}/source-outline`, async (route) => {
    if (route.request().method() === "GET") return route.abort("failed");
    await route.continue();
  });

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#script`);
  await expect(page.getByRole("heading", { name: "剧本", exact: true })).toBeVisible();
  await expect(page.getByTestId("script-review")).toBeVisible();
  await expect(page.getByTestId("script-review")).toContainText("已接受 r1");
  await expect(page.getByTestId("source-outline-source")).not.toBeVisible();
});

test("clears an owner-local load error after its retry succeeds", async ({ page, request, workbench }) => {
  const projectId = await createScriptProject(request, workbench.apiOrigin, "workflow-owner-retry");
  let failScriptReads = true;
  await page.route(`**/api/v2/projects/${projectId}/script`, async (route) => {
    if (route.request().method() === "GET" && failScriptReads) {
      return route.abort("failed");
    }
    await route.continue();
  });

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#script`);
  const script = page.getByTestId("script-review");
  await expect(script.getByRole("alert")).toBeVisible();
  failScriptReads = false;
  await script.getByRole("button", { name: "重试加载剧本" }).click();
  await expect(script).toContainText("已接受 r1");
  await expect(script.getByRole("alert")).toHaveCount(0);
});

test("returns from the secondary workbench after an awaited offline project load and retries canonically", async ({ page, request, workbench }) => {
  const projectId = await createScriptProject(request, workbench.apiOrigin, "workflow-offline-return");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#art`);
  const workflow = page.getByRole("navigation", { name: "创作流程" });
  await expect(page.getByTestId("art-review")).toBeVisible();

  await page.getByText("编辑与工具", { exact: true }).click();
  await page.getByRole("button", { name: /镜头与媒体工作台/ }).click();
  await expect(page.getByRole("heading", { name: "分镜工作台" })).toBeVisible();

  let rejectedLoads = 0;
  await page.route(`**/api/v2/projects/${projectId}`, async (route) => {
    if (route.request().method() === "GET") {
      rejectedLoads += 1;
      await route.abort("failed");
      return;
    }
    await route.continue();
  });

  await page.getByRole("button", { name: "刷新服务器版本" }).click();
  await expect.poll(() => rejectedLoads).toBe(1);
  await expect(page.getByRole("alert")).toContainText(`无法加载项目 ${projectId}`);
  await expect(page.getByTestId("workspace-hydrating")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "分镜工作台" })).toBeVisible();
  await expect(page.locator(".project-switcher strong")).toHaveText("F5A workflow-offline-return");
  await expect(page.locator(".editor-host")).toHaveAttribute("disabled", "");

  let releaseRetry: (() => void) | undefined;
  const retryRequest = new Promise<void>((resolve) => { releaseRetry = resolve; });
  let heldRetry = false;
  await page.unroute(`**/api/v2/projects/${projectId}`);
  await page.route(`**/api/v2/projects/${projectId}`, async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    heldRetry = true;
    await retryRequest;
    await route.continue();
  });
  await workflow.getByRole("link", { name: "美术参考" }).click();
  await expect(page).toHaveURL(new RegExp(`project=${projectId}&stage=source#art$`));
  await expect.poll(() => heldRetry).toBeTruthy();
  await expect(page.locator(".project-switcher strong")).toHaveText("F5A workflow-offline-return");
  await expect(page.locator(".source-outline-page")).toHaveAttribute("data-project-id", projectId);
  await expect(page.getByTestId("workspace-hydrating")).toHaveCount(0);
  await expect(page.getByTestId("art-review")).toBeVisible();
  await expect(page.locator(".editor-host")).toHaveAttribute("disabled", "");

  releaseRetry?.();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.locator(".editor-host")).not.toHaveAttribute("disabled", "");
  await page.unroute(`**/api/v2/projects/${projectId}`);
  await workflow.getByRole("link", { name: "剧本" }).click();
  await expect(page).toHaveURL(new RegExp(`project=${projectId}&stage=source#script$`));
  await expect(page.getByTestId("script-review")).toBeVisible();
});

test("returns from the read-only reader to its existing script owner", async ({ page, request, workbench }) => {
  const projectId = await createScriptProject(request, workbench.apiOrigin, "workflow-reader-return");

  await page.goto(`${workbench.frontendOrigin}/v2/?view=story-prototype&project=${projectId}`);
  const returnNavigation = page.getByRole("navigation", { name: "创作流程返回" });
  await expect(returnNavigation.getByRole("link", { name: "返回创作流程" })).toHaveAttribute("href", `?project=${projectId}&stage=source#script`);
  await expect(returnNavigation).toContainText("只读剧本与分镜评审");
});
