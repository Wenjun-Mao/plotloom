import { expect, test } from "./fixture";

const secondaryTools = ["项目简报", "故事圣经", "剧情 DAG", "场景节拍", "分镜工作台", "运行轨迹", "隔离修复"];

async function expectCompactCreatorGap(page: import("@playwright/test").Page) {
  const workflow = page.getByRole("navigation", { name: "创作流程" });
  const heading = workflow.locator(".creator-workflow-heading");
  const firstLink = workflow.getByRole("link", { name: "来源与大纲" });
  const [headingBox, firstLinkBox] = await Promise.all([heading.boundingBox(), firstLink.boundingBox()]);
  expect(headingBox).not.toBeNull();
  expect(firstLinkBox).not.toBeNull();
  expect(firstLinkBox!.y - (headingBox!.y + headingBox!.height)).toBeGreaterThanOrEqual(0);
  expect(firstLinkBox!.y - (headingBox!.y + headingBox!.height)).toBeLessThanOrEqual(16);
}

test("keeps creator links compact and gives secondary tools one matching heading", async ({ page, workbench }) => {
  await page.goto(`${workbench.frontendOrigin}/v2/?stage=brief`);
  await page.getByRole("button", { name: "打开示例项目" }).click();
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page).toHaveURL(/[?&]project=/);

  const toolsSummary = page.getByText("编辑与工具", { exact: true });
  const tools = page.getByRole("navigation", { name: "编辑与工具" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await expectCompactCreatorGap(page);
  await expect(tools).not.toBeVisible();

  await toolsSummary.click();
  await expect(tools).toBeVisible();
  await expectCompactCreatorGap(page);

  await page.setViewportSize({ width: 1920, height: 1080 });
  await expectCompactCreatorGap(page);
  for (const label of secondaryTools) {
    const tool = tools.getByRole("button", { name: label, exact: true });
    await expect(tool).toHaveText(label);
    await expect(tool.locator(":scope > span")).toHaveCount(0);
    await expect(tool.locator("small")).toHaveCount(0);
    await tool.click();
    await expect(page.getByRole("heading", { name: label, exact: true })).toBeVisible();
    await expect(page.locator(".page-header .eyebrow")).toHaveCount(0);
  }

  await toolsSummary.click();
  await expect(tools).not.toBeVisible();
  await expectCompactCreatorGap(page);
  await page.getByRole("navigation", { name: "创作流程" }).getByRole("link", { name: "来源与大纲" }).click();
  await expect(page.getByRole("heading", { name: "来源与大纲", exact: true })).toBeVisible();
});
