import { expect, test } from "./fixture";
import { changeScript, createScriptProject, endpoint, json, writeDelivery } from "./f5a-fixture";

async function expectFragmentAtViewportStart(page: import("@playwright/test").Page, id: string) {
  // The persistent workbench header reserves the first 76px; the target must
  // otherwise be positioned at the viewport start rather than merely exist.
  await expect.poll(async () => page.locator(`#${id}`).evaluate((element) => Math.abs(element.getBoundingClientRect().top))).toBeLessThan(100);
}

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
  await expect(page.getByTestId("art-review")).toBeVisible();
  await expect(page.locator(".source-outline-page")).toHaveAttribute("data-project-id", firstProject);
  await expect(page.locator(".source-outline-page > .page-header span")).toHaveText("来源与大纲");
  await expect(page.locator(".source-outline-source header > span")).toHaveText("已接受的来源");
  await expect(page.locator(".source-outline-candidate header > span")).toHaveText("大纲候选");
  await expect(page.locator(".source-outline-accepted header > span")).toHaveText("已接受的大纲");
  await expect(page.getByTestId("section-map").locator("header > span")).toHaveText("分支章节映射");
  await expect(page.getByTestId("art-review").locator("header > span")).toHaveText("美术参考");
  await expect(page.getByTestId("art-review").locator(":scope > small").first()).toContainText("参考研究在下方单独显示");
  await expect(page.getByTestId("art-review").locator(":scope > small").first()).not.toContainText("F3B");
  await expect(topbarLabel).toHaveText("美术参考");
  await expect(workflow.getByRole("link", { name: "美术参考" })).toHaveAttribute("aria-current", "step");
  await expect(workflow.getByRole("link", { name: "剧本" })).not.toHaveAttribute("aria-current", "step");
  await expectFragmentAtViewportStart(page, "art");

  await workflow.getByRole("link", { name: "剧本" }).click();
  await expect(page).toHaveURL(new RegExp(`project=${firstProject}&stage=source#script$`));
  await expect(page.getByTestId("script-review")).toBeVisible();
  await expect(page.getByTestId("script-review").locator("header > span")).toHaveText("剧本");
  await expect(topbarLabel).toHaveText("剧本");
  await expect(workflow.getByRole("link", { name: "剧本" })).toHaveAttribute("aria-current", "step");
  await expect(workflow.getByRole("link", { name: "美术参考" })).not.toHaveAttribute("aria-current", "step");

  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`project=${firstProject}&stage=source#art$`));
  await expect(page.getByTestId("art-review")).toBeVisible();
  await expect(workflow.getByRole("link", { name: "美术参考" })).toHaveAttribute("aria-current", "step");
  await expectFragmentAtViewportStart(page, "art");
  await page.goForward();
  await expect(page).toHaveURL(new RegExp(`project=${firstProject}&stage=source#script$`));
  await expect(page.getByTestId("script-review")).toBeVisible();

  await workflow.getByRole("link", { name: "分镜评审" }).click();
  await expect(page).toHaveURL(new RegExp(`project=${firstProject}&stage=source#storyboard-review$`));
  await expect(page.getByTestId("storyboard-review")).toBeVisible();
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
});

test("keeps missing and stale F5A review explanations at their source-bound owner", async ({ page, request, workbench }) => {
  const projectId = await createScriptProject(request, workbench.apiOrigin, "workflow-f5a-state");

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#storyboard-review`);
  const review = page.getByTestId("storyboard-review");
  await expect(review).toContainText("尚无 review");
  await expect(review).toContainText("准备并复制 storyboard specialist handoff");
  await expectFragmentAtViewportStart(page, "storyboard-review");

  await acceptStoryboardReview(request, workbench.apiOrigin, projectId);
  await changeScript(request, workbench.apiOrigin, projectId);
  await page.reload();
  await expect(review).toContainText("上下文已过期");
  await expect(review).toContainText("已接受剧本 r");
  await expect(review).not.toContainText("F4 script r");
  await expect(review).toContainText("不是 Plotloom 的 shots、播放内容、媒体提示词或投产许可");
});

test("waits for an earlier source owner before positioning a later embedded target", async ({ page, request, workbench }) => {
  const projectId = await createScriptProject(request, workbench.apiOrigin, "workflow-out-of-order");
  let releaseArt: (() => void) | undefined;
  const artResponse = new Promise<void>((resolve) => { releaseArt = resolve; });
  let heldArtRead = false;
  await page.route(`**/api/v2/projects/${projectId}/art`, async (route) => {
    if (route.request().method() !== "GET" || heldArtRead) return route.continue();
    heldArtRead = true;
    await artResponse;
    await route.continue();
  });

  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source#script`);
  await expect(page.getByTestId("script-review")).toBeVisible();
  await expect.poll(() => heldArtRead).toBeTruthy();
  releaseArt?.();
  await expect(page.getByTestId("art-review")).toBeVisible();
  await expectFragmentAtViewportStart(page, "script");
});

test("returns from the read-only reader to its existing script owner", async ({ page, request, workbench }) => {
  const projectId = await createScriptProject(request, workbench.apiOrigin, "workflow-reader-return");

  await page.goto(`${workbench.frontendOrigin}/v2/?view=story-prototype&project=${projectId}`);
  const returnNavigation = page.getByRole("navigation", { name: "创作流程返回" });
  await expect(returnNavigation.getByRole("link", { name: "返回创作流程" })).toHaveAttribute("href", `?project=${projectId}&stage=source#script`);
  await expect(returnNavigation).toContainText("只读剧本与分镜评审");
});
