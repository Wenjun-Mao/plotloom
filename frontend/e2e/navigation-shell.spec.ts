import { expect, test } from "./fixture";

test.describe("M1-B0 query navigation shell", () => {
  test("uses stage/entity query parameters and restores stage on browser back", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/?stage=bible&entity=char_ruanxing`);
    await page.getByRole("button", { name: "打开示例项目" }).click();

    await expect(page.getByRole("heading", { name: "故事圣经" })).toBeVisible();
    // Opening a different workspace owner clears project-scoped selection.
    await expect(page).toHaveURL(/stage=bible$/);
    await page.getByRole("button", { name: "编辑此角色" }).first().click();
    await expect(page).toHaveURL(/stage=bible.*entity=bible%3Acharacter%3Achar_ruanxing/);
    await expect(page.getByText("char_ruanxing", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "项目简报" }).first().click();
    await expect(page).toHaveURL(/stage=brief/);
    await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();

    await page.goBack();
    await expect(page).toHaveURL(/stage=bible.*entity=bible%3Acharacter%3Achar_ruanxing/);
    await expect(page.getByRole("heading", { name: "故事圣经" })).toBeVisible();
  });

  test("writes graph selection into entity and restores it with browser history", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/?stage=graph`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    // The entity navigator is a normal, keyboard-accessible pointer path; it
    // intentionally does not depend on compact canvas hitbox geometry.
    await page.getByTestId("graph-select-node-diagnose").click();
    await expect(page).toHaveURL(/stage=graph.*entity=graph-node%3Adiagnose/);
    await expect(page.locator(".node-inspector")).toContainText("诊断双重故障");

    await page.goBack();
    await expect(page).toHaveURL(/stage=graph$/);
    await expect(page.locator(".node-inspector")).toContainText("冲入控制室");
  });

  test("keeps the URL project identity when a stage is clicked before refresh hydration completes", async ({ page, workbench }) => {
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

    await page.reload();
    await expect(page.getByText("Plotloom 服务：连接中", { exact: true })).toBeVisible();
    await page
      .getByRole("navigation", { name: "工作台阶段" })
      .getByRole("button", { name: /故事圣经/ })
      .click();
    await expect(page).toHaveURL(new RegExp(`project=${escapeRegex(projectId)}&stage=bible`));

    releaseProjectResponse?.();
    await expect(page.getByRole("heading", { name: "故事圣经" })).toBeVisible();
    await expect(page.locator(".project-switcher")).toContainText("月城余晖");
    await expect(page.locator(".project-switcher")).toContainText(projectId);
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

    await page.reload();
    await expect(page.getByTestId("workspace-hydrating")).toBeVisible();
    await expect(page.getByLabel("审核人标签")).not.toBeVisible();

    releaseProjectResponse?.();
    await expect(page.getByTestId("workspace-hydrating")).not.toBeVisible();
    await expect(page.getByRole("heading", { name: "分镜工作台" })).toBeVisible();
    await expect(page.getByLabel("审核人标签")).toBeVisible();
  });
});

async function persistSampleProject(page: import("@playwright/test").Page, frontendOrigin: string): Promise<string> {
  await page.goto(`${frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page
    .getByRole("navigation", { name: "工作台阶段" })
    .getByRole("button", { name: /分镜工作台/ })
    .click();
  const created = page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === "/api/v2/projects");
  await page.getByRole("button", { name: "保存分镜" }).click();
  await expect((await created).ok()).toBeTruthy();
  await expect(page).toHaveURL(/[?&]project=/);
  const projectId = new URL(page.url()).searchParams.get("project");
  expect(projectId).toBeTruthy();
  return projectId!;
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
