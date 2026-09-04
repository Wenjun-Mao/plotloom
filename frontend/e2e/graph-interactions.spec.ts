import { expect, test } from "./fixture";

test.describe("M1-B1 graph authoring interactions", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("uses the accessible entity navigator and discloses every cascade ID before deletion", async ({ page, workbench }) => {
    await page.goto(`${workbench.frontendOrigin}/v2/?stage=graph`);
    await page.getByRole("button", { name: "打开示例项目" }).click();

    // This is an ordinary pointer click on the stable entity navigator, not a
    // forced canvas click or a synthetic event.
    await page.getByTestId("graph-select-node-memory").click();
    await expect(page.locator(".node-inspector")).toContainText("恢复全城记忆");
    await expect(page.getByLabel("节点 ID")).toHaveValue("memory");

    await page.getByRole("button", { name: "删除节点与关联边" }).click();
    const confirmation = page.getByRole("dialog", { name: "关系影响确认" });
    await expect(confirmation).toContainText("memory");
    await expect(confirmation).toContainText("e2");
    await expect(confirmation).toContainText("e4");
    await expect(confirmation).toContainText("join_contract_1");
    await expect(confirmation).toContainText("scene_memory");
    await expect(confirmation).toContainText("scene_beats.scenes.scene_memory.storyNodeId");
    await expect(confirmation).toContainText("不会被隐藏删除");
    await confirmation.getByRole("button", { name: "取消", exact: true }).click();
    await expect(confirmation).toHaveCount(0);
    await expect(page.getByTestId("graph-select-node-memory")).toBeVisible();
  });
});
