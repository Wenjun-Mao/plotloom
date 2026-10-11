import { expect, test } from "./fixture";

test("keeps the recommended workflow visible on supported desktops and retains draft navigation protection", async ({ page, workbench }, info) => {
  await page.route("**/api/v2/runtime-capabilities", async route => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...await response.json(), durableProjectDrafts: false } });
  });
  await page.goto(`${workbench.frontendOrigin}/v2/`);
  await page.getByRole("button", { name: "创建空白项目" }).click();
  await page.getByLabel("故事梗概").fill("为这个只用于界面检查的故事建立项目。");
  await page.getByRole("button", { name: "保存并继续到来源" }).click();
  await expect(page).toHaveURL(/[?&]project=/);
  const guide = page.getByTestId("recommended-workflow");
  const sourceText = page.getByLabel("故事内容");
  await expect(sourceText).toBeEnabled();
  await sourceText.fill("为这个只用于界面检查的故事补充一处尚未保存的修改。");
  await expect(guide).toContainText("故事内容有未保存修改");
  await page.getByRole("button", { name: "确认改编内容" }).click();
  await expect(guide).not.toContainText("故事内容有未保存修改");

  await page.getByRole("button", { name: /项目简报与创作设置/ }).click();
  await expect(guide).toBeVisible();
  await expect(guide).toContainText("当前 · 1/6 项目简报");
  await expect(guide.getByRole("button", { name: "打开来源与大纲" })).toBeVisible();

  for (const size of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(size);
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    const top = await guide.evaluate(element => {
      const bar = element.getBoundingClientRect();
      const toolbar = document.querySelector(".topbar")!.getBoundingClientRect();
      return { barTop: bar.top, toolbarBottom: toolbar.bottom, height: bar.height, scrollWidth: document.documentElement.scrollWidth };
    });
    expect(Math.abs(top.barTop - top.toolbarBottom)).toBeLessThanOrEqual(2);
    expect(top.scrollWidth).toBeLessThanOrEqual(size.width);
    expect(top.height).toBeLessThan(size.height - top.toolbarBottom);
    await page.screenshot({ path: info.outputPath(`recommended-workflow-${size.width}x${size.height}-collapsed.png`) });

    await guide.getByText("查看六步状态").click();
    await expect(guide.getByRole("list", { name: "推荐流程步骤" }).getByRole("listitem")).toHaveCount(6);
    await expect(guide.locator('[aria-current="step"]')).toContainText("项目简报");
    await expect(guide).toContainText("静态报告只供阅读");
    const expanded = await guide.evaluate(element => ({
      height: element.getBoundingClientRect().height,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(expanded.height).toBeLessThan(size.height);
    expect(expanded.scrollWidth).toBeLessThanOrEqual(size.width);
    await page.screenshot({ path: info.outputPath(`recommended-workflow-${size.width}x${size.height}-expanded.png`) });
    await guide.getByText("查看六步状态").click();
  }

  await page.setViewportSize({ width: 1280, height: 768 });
  await page.getByLabel("故事梗概").fill("留下一份未保存的简报草稿。 ");
  await guide.getByRole("button", { name: "打开来源与大纲" }).click();
  const draftDialog = page.getByRole("dialog", { name: "保存当前草稿？" });
  await expect(draftDialog).toBeVisible();
  await expect(draftDialog).toContainText("即将离开当前页面");
  await expect(page).toHaveURL(/stage=brief/);
});
