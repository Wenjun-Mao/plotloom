import { expect, test } from "./fixture";

for (const width of [1440, 1920, 1280]) {
  test(`creator Brief roles and expanded cards remain usable at ${width}px`, async ({ page, workbench }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`${workbench.frontendOrigin}/v2/`);
    await page.getByRole("button", { name: "创建空白项目" }).click();
    const save = page.getByRole("button", { name: "保存并继续到来源" });
    await expect(save).toBeDisabled();
    await expect(page.locator("#brief-save-hint")).toHaveText("填写故事梗概后即可保存；片名可稍后补充。");
    await expect(page.locator("#brief-save-hint")).toBeVisible();
    await expect(page.getByLabel("故事梗概")).toHaveAttribute("aria-required", "true");
    await expect(page.getByLabel("片名")).not.toHaveAttribute("aria-required", "true");
    await expect(page.getByText("REQUIRED INPUT")).toHaveCount(0);
    await expect(page.locator(".brief-alternate-workflow button")).not.toBeVisible();
    const structure = page.locator(".brief-settings details");
    const structureSummary = page.getByText("剧情结构与分镜", { exact: true });
    const decisions = page.getByLabel("每次完整播放的选择次数", { exact: true });
    await expect(structure).toHaveAttribute("open", "");
    await expect(decisions).toBeVisible();
    const initialDecisions = await decisions.inputValue();
    await structureSummary.click();
    await expect(structure).not.toHaveAttribute("open", "");
    await expect(decisions).not.toBeVisible();
    await expect(save).toBeDisabled();
    await structureSummary.click();
    await expect(structure).toHaveAttribute("open", "");
    await expect(decisions).toHaveValue(initialDecisions);
    await page.getByText("其他工作流：旧版故事提案", { exact: true }).click();
    const layout = await page.evaluate(() => {
      const advanced = document.querySelector(".brief-layout")!.getBoundingClientRect();
      const alternate = document.querySelector(".brief-alternate-workflow")!;
      const summary = alternate.querySelector("summary")!;
      const button = alternate.querySelector("button")!;
      const card = alternate.getBoundingClientRect();
      const style = getComputedStyle(document.querySelector(".range-summary strong")!);
      return { overflow: document.documentElement.scrollWidth > innerWidth, gap: card.top - advanced.bottom,
        headingInset: summary.getBoundingClientRect().left - card.left,
        buttonInset: button.getBoundingClientRect().left - card.left,
        font: style.fontFamily, size: style.fontSize, color: style.color };
    });
    expect(layout.overflow).toBe(false);
    expect(layout.gap).toBeGreaterThanOrEqual(20);
    expect(layout.headingInset).toBeGreaterThanOrEqual(16);
    expect(layout.buttonInset).toBeGreaterThanOrEqual(16);
    expect(layout.size).toBe("13px");
    expect(layout.font).not.toContain("monospace");
    const enabled = page.getByRole("button", { name: "生成助手设置" });
    const enabledStyle = await enabled.evaluate(element => ({ color: getComputedStyle(element).color, border: getComputedStyle(element).borderStyle }));
    const disabledStyle = await save.evaluate(element => ({ color: getComputedStyle(element).color, border: getComputedStyle(element).borderStyle }));
    expect(enabledStyle.color).not.toBe(disabledStyle.color);
    expect(disabledStyle.border).toBe("dashed");
    expect(enabledStyle.border).toBe("solid");
    await page.screenshot({ path: testInfo.outputPath(`brief-expanded-${width}.png`), fullPage: true });
    await page.getByLabel("故事梗概").fill("雨停以后，林遥决定赴约还是回家。");
    await expect(save).toBeEnabled();
    // Diagnostics remain useful while authoring, but must never cover Save.
    await page.locator(".topbar-technical-status > summary").click();
    await expect(page.locator(".topbar-technical-status")).toHaveAttribute("open", "");
    await expect(page.getByText("草稿：等待编辑", { exact: true })).toBeVisible();
    await save.click();
    await expect(page.getByRole("heading", { name: "来源与大纲" })).toBeVisible();
    await expect(page.getByLabel("补充创作要求（可选）")).not.toHaveAttribute("aria-required", "true");
    const source = page.getByTestId("source-outline-source");
    expect(await source.evaluate(element => parseFloat(getComputedStyle(element).paddingLeft))).toBeGreaterThanOrEqual(16);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    const marker = source.locator("label").filter({ has: page.getByLabel("故事内容") }).locator("span").first();
    await expect(marker).toHaveText("故事内容 *");
  });
}
