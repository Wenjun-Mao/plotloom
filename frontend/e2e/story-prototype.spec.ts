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
  const stages = prototype.getByRole("navigation", { name: "创作阶段" });
  await expect(stages.getByRole("link", { name: "来源" })).toHaveAttribute("href", new RegExp(`project=${id}.*stage=source`));
  await expect(stages.getByRole("link", { name: "人物、地点、道具" })).toHaveAttribute("href", new RegExp(`project=${id}.*stage=bible`));
  await expect(stages.getByText("美术 · 尚未提供", { exact: true })).toBeVisible();
  await expect(stages.getByText("制作 · 尚未提供", { exact: true })).toBeVisible();
  await expect(stages.getByRole("link", { name: "播放" })).toHaveAttribute("href", new RegExp(`project=${id}.*view=play`));
  await expect(prototype.getByTestId("route-reader")).toContainText("One cable. Two places need it.");
  await expect(prototype.getByTestId("route-reader")).toContainText("Beacon first.");
  await expect(prototype.locator(".screenplay-section")).toHaveCount(2);
  await expect(prototype.locator(".screenplay-section").first()).toContainText("第 01 节");
  await expect(prototype.locator(".screenplay-section").last()).toContainText("第 02 节");
  await expect(prototype.getByText("Beacon room", { exact: true }).first()).toBeVisible();
  await expect(prototype.getByText("光线：dawn", { exact: true }).first()).toBeVisible();
  await expect(prototype.getByText("人物：Mira", { exact: true }).first()).toBeVisible();
  await expect(prototype.getByText("Mira", { exact: true }).first()).toBeVisible();
  await expect(prototype).not.toContainText("StoryGraph");
  await expect(prototype).not.toContainText("state effects");
  await expect(prototype).not.toContainText("U2 的可审阅界面原型");
  await page.screenshot({ path: testInfo.outputPath("story-prototype-1440.png"), fullPage: true });

  await prototype.getByRole("button", { name: /选择：Light the dock/ }).click();
  await expect(prototype.getByTestId("route-reader")).toContainText("Dock first.");
  await expect(prototype.getByTestId("route-reader")).not.toContainText("Beacon first.");
  await prototype.getByRole("button", { name: /Storm warning/ }).first().click();
  await expect(prototype.getByTestId("route-reader")).toContainText("Dock first.");
  await expect(prototype.getByTestId("route-reader")).not.toContainText("Beacon first.");
  await expect(prototype.getByText("已确认剧本", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 768, height: 900 });
  await page.screenshot({ path: testInfo.outputPath("story-prototype-768.png"), fullPage: true });
  expect(writes).toEqual([]);

  await stages.getByRole("link", { name: "来源" }).click();
  await expect(page).toHaveURL(new RegExp(`project=${id}.*stage=source`));
  await expect(page.getByRole("heading", { name: "来源与小说大纲" })).toBeVisible();
  expect(writes).toEqual([]);
});
