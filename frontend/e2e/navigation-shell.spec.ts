import { expect, test } from "./fixture";

test.describe("M1-B0 query navigation shell", () => {
  test("uses stage/entity query parameters and restores stage on browser back", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/?stage=bible&entity=char_ruanxing`);
    await page.getByRole("button", { name: "打开示例项目" }).click();

    await expect(page.getByRole("heading", { name: "故事圣经" })).toBeVisible();
    // Opening a different workspace owner clears project-scoped selection.
    await expect(page).toHaveURL(/stage=bible$/);
    await page.getByRole("textbox", { name: "叙事职责" }).first().focus();
    await expect(page).toHaveURL(/stage=bible.*entity=char_ruanxing/);
    await expect(page.getByText("char_ruanxing", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "项目简报" }).first().click();
    await expect(page).toHaveURL(/stage=brief/);
    await expect(page.getByRole("heading", { name: "项目简报" })).toBeVisible();

    await page.goBack();
    await expect(page).toHaveURL(/stage=bible.*entity=char_ruanxing/);
    await expect(page.getByRole("heading", { name: "故事圣经" })).toBeVisible();
  });

  test("writes graph selection into entity and restores it with browser history", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/?stage=graph`);
    await page.getByRole("button", { name: "打开示例项目" }).click();
    const node = page.locator(".react-flow__node").filter({ hasText: "诊断双重故障" });
    // React Flow's compact auto-layout can overlap hitboxes. Dispatch on the
    // semantic node so this verifies the selection contract, not geometry.
    await node.dispatchEvent("click");
    await expect(page).toHaveURL(/stage=graph.*entity=diagnose/);
    await expect(page.locator(".node-inspector")).toContainText("诊断双重故障");

    await page.goBack();
    await expect(page).toHaveURL(/stage=graph$/);
    await expect(page.locator(".node-inspector")).toContainText("冲入控制室");
  });
});
