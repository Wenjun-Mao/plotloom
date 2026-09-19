import { expect, test } from "./fixture";
import { createScriptProject } from "./f5a-fixture";

test("reads the canonical branch graph and accepted screenplay without writing", async ({ page, request, workbench }, testInfo) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "story-prototype");
  const writes: string[] = [];
  page.on("request", (pending) => {
    if (pending.url().includes("/api/v2/") && pending.method() !== "GET") writes.push(`${pending.method()} ${pending.url()}`);
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?view=story-prototype&project=${id}`);
  const prototype = page.getByTestId("story-prototype");
  await expect(prototype).toContainText("从一个开场，抵达两个不同后果");
  await expect(prototype).toContainText("英文原文");
  await expect(prototype.getByTestId("route-reader")).toContainText("One cable. Two places need it.");
  await expect(prototype.getByTestId("route-reader")).toContainText("Beacon first.");
  await page.screenshot({ path: testInfo.outputPath("story-prototype-1440.png"), fullPage: true });

  await prototype.getByRole("button", { name: /选择：Light the dock/ }).click();
  await expect(prototype.getByTestId("route-reader")).toContainText("Dock first.");
  await expect(prototype.getByTestId("route-reader")).not.toContainText("Beacon first.");
  await prototype.getByRole("button", { name: /Storm warning/ }).first().click();
  await expect(prototype.getByTestId("route-reader")).toContainText("Dock first.");
  await expect(prototype.getByTestId("route-reader")).not.toContainText("Beacon first.");
  await expect(prototype.getByText("已接受剧本 r1")).toBeVisible();
  await page.setViewportSize({ width: 768, height: 900 });
  await page.screenshot({ path: testInfo.outputPath("story-prototype-768.png"), fullPage: true });
  expect(writes).toEqual([]);
});
