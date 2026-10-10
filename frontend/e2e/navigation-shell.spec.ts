import { expect, test } from "./fixture";
import { navigateToSecondaryTool } from "./workbench-controls";
import { createCreatorGraph } from "./fixtures/creator-graph";

test.describe("M1-B0 query navigation shell", () => {
  test("uses stage/entity query parameters and restores stage on browser back", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/?stage=bible&entity=char_ruanxing`);
    await page.getByRole("button", { name: "打开示例项目" }).click();

    await expect(page.getByRole("heading", { name: "故事圣经" })).toBeVisible();
    // Opening a different workspace owner clears project-scoped selection.
    await expect(page).toHaveURL(/stage=bible$/);
    await page.getByRole("button", { name: "查看此角色" }).first().click();
    await expect(page).toHaveURL(/stage=bible.*entity=bible%3Acharacter%3Achar_ruanxing/);
    await expect(page.getByText("char_ruanxing", { exact: true })).toBeVisible();

    const toolsNavigation = page.getByRole("navigation", { name: "编辑与工具" });
    if (!(await toolsNavigation.isVisible())) {
      await page.getByText("编辑与工具", { exact: true }).click();
    }
    await page.getByRole("button", { name: "项目简报与创作设置", exact: false }).click();
    await expect(page).toHaveURL(/stage=brief/);
    await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();

    await page.goBack();
    await expect(page).toHaveURL(/stage=bible.*entity=bible%3Acharacter%3Achar_ruanxing/);
    await expect(page.getByRole("heading", { name: "故事圣经" })).toBeVisible();
  });

  test("retains shared graph selection through mode navigation, history and reload without authoring it", async ({ page, request, workbench }) => {
    const id = await createCreatorGraph(request, workbench.apiOrigin, "navigation-selection");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=graph`);
    await page.getByText("全部稳定身份与待连接关系", { exact: true }).click();
    await page.getByRole("button", { name: "结局 B", exact: true }).click();
    await expect(page.getByLabel("章节标题", { exact: true })).toHaveValue("结局 B");
    const before = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`)).json();
    await page.getByRole("button", { name: "创作工作台", exact: true }).click();
    await expect(page).toHaveURL(/stage=creator$/);
    await expect(page.getByLabel("章节标题", { exact: true })).toHaveValue("结局 B");
    await page.goBack();
    await expect(page).toHaveURL(/stage=graph$/);
    await page.reload();
    await expect(page.getByLabel("章节标题", { exact: true })).toHaveValue("结局 B");
    const after = await (await request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`)).json();
    expect(after.draft.draftRevision).toBe(before.draft.draftRevision);
  });

  test("preserves project identity and withdraws stage navigation until refresh hydration completes", async ({ page, workbench }) => {
    const projectId = await persistSampleProject(page, workbench.frontendOrigin);
    let releaseProjectResponse: (() => void) | undefined;
    const projectResponseGate = new Promise<void>((resolve) => {
      releaseProjectResponse = resolve;
    });
    let heldInitialProjectRequest = false;

    await page.route(`**/api/v2/projects/${projectId}`, async (route) => {
      if (route.request().method() !== "GET" || heldInitialProjectRequest) {
        await route.continue();
        return;
      }
      heldInitialProjectRequest = true;
      await projectResponseGate;
      await route.continue();
    });

    try {
      await page.reload();
      await expect(page.getByTestId("workspace-hydrating")).toBeVisible();
      await page.getByText("编辑与工具", { exact: true }).click();
      await expect(page.getByRole("navigation", { name: "编辑与工具" }).getByRole("button", { name: "故事圣经", exact: true })).toBeDisabled();
      await expect(page).toHaveURL((url) => url.searchParams.get("project") === projectId
        && url.searchParams.get("stage") === "storyboard");
    } finally {
      releaseProjectResponse?.();
    }
    await expect(page.getByTestId("workspace-hydrating")).not.toBeVisible();
    await navigateToSecondaryTool(page, "故事圣经");
    await expect(page).toHaveURL((url) => url.searchParams.get("project") === projectId
      && url.searchParams.get("stage") === "bible");
    await expect(page.getByRole("heading", { name: "故事圣经" })).toBeVisible();
    await expect(page.locator(".project-switcher")).toContainText("月城余晖");
    await expect(page.locator(".project-switcher")).not.toContainText(projectId);
  });

  test("does not expose a provisional teaching editor during persisted-project hydration", async ({ page, workbench }) => {
    const projectId = await persistSampleProject(page, workbench.frontendOrigin);
    let releaseProjectResponse: (() => void) | undefined;
    const projectResponseGate = new Promise<void>((resolve) => {
      releaseProjectResponse = resolve;
    });

    await page.route(`**/api/v2/projects/${projectId}`, async (route) => {
      if (route.request().method() !== "GET") {
        await route.continue();
        return;
      }
      await projectResponseGate;
      await route.continue();
    });

    try {
      await page.reload();
      await expect(page.getByTestId("workspace-hydrating")).toBeVisible();
      await expect(page.getByLabel("审核人标签")).not.toBeVisible();
    } finally {
      releaseProjectResponse?.();
    }
    await expect(page.getByTestId("workspace-hydrating")).not.toBeVisible();
    await expect(page.getByRole("heading", { name: "分镜工作台" })).toBeVisible();
    await expect(page.getByLabel("审核人标签")).toBeVisible();
  });
});

async function persistSampleProject(page: import("@playwright/test").Page, frontendOrigin: string): Promise<string> {
  await page.goto(`${frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await navigateToSecondaryTool(page, "分镜工作台");
  const created = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === "/api/v2/projects");
  await page.getByRole("button", { name: "保存分镜" }).click();
  await expect((await created).ok()).toBeTruthy();
  await expect(page).toHaveURL(/[?&]project=/);
  const projectId = new URL(page.url()).searchParams.get("project");
  expect(projectId).toBeTruthy();
  return projectId!;
}
