import { expect, test } from "./fixture";
import { changeScript, createScriptProject, endpoint, json, writeDelivery } from "./f5a-fixture";

async function acceptStoryboardReview(request: Parameters<typeof createScriptProject>[0], origin: string, id: string) {
  const prepared = await json(request.post(`${endpoint(origin, id)}/candidates`));
  await writeDelivery(prepared);
  await json(request.post(`${endpoint(origin, id)}/candidates/${prepared.jobId}/refresh`));
  await json(request.post(`${endpoint(origin, id)}/accept`, { data: { jobId: prepared.jobId, expectedReviewRevision: prepared.expectedReviewRevision, binding: prepared.binding } }));
}

test("reads the current route-focused storyboard review without writing", async ({ page, request, workbench }, testInfo) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "story-prototype");
  await acceptStoryboardReview(request, workbench.apiOrigin, id);
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
  await expect(prototype.getByTestId("storyboard-reader")).toContainText("sailors can see the channel now.");
  await expect(prototype.getByTestId("storyboard-reader")).not.toContainText("the dock stays on.");
  await expect(prototype.locator(".screenplay-section")).toHaveCount(2);
  await expect(prototype.locator(".screenplay-section").first()).toContainText("第 01 节");
  await expect(prototype.locator(".screenplay-section").last()).toContainText("第 02 节");
  const opening = prototype.locator('[data-section-id="opening"]');
  await expect(opening.getByText("章节目标时长 90 秒", { exact: true })).toBeVisible();
  await expect(opening.locator(".screenplay-scene")).toHaveCount(1);
  await expect(opening).toContainText("Beacon room");
  await expect(opening).toContainText("光线：dawn");
  await expect(opening).toContainText("人物：Mira");
  await expect(opening).toContainText("One cable. Two places need it.");
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
  await expect(prototype.getByText("已确认 F4 剧本 + F5A 分镜评审", { exact: true })).toBeVisible();
  const storyboard = prototype.getByTestId("storyboard-reader");
  await expect(storyboard).toContainText("按路径查看章节、段落与镜头");
  await expect(storyboard).toContainText("分段预计");
  await expect(storyboard).toContainText("未提供参考图像");
  const instructions = storyboard.locator(".generation-instructions").first();
  await expect(instructions.locator("summary")).toHaveText("查看生成说明");
  await expect(instructions.locator("pre")).not.toBeVisible();
  await expect(storyboard).toContainText("The dock stays on.");
  await expect(storyboard).not.toContainText("Sailors can see the channel now.");
  await instructions.locator("summary").click();
  await expect(instructions.locator("pre")).toContainText("How the reference pictures align");
  await instructions.locator("summary").click();
  await expect(instructions.locator("pre")).not.toBeVisible();
  await page.setViewportSize({ width: 768, height: 900 });
  await page.screenshot({ path: testInfo.outputPath("story-prototype-768.png"), fullPage: true });
  expect(writes).toEqual([]);

  await stages.getByRole("link", { name: "来源" }).click();
  await expect(page).toHaveURL(new RegExp(`project=${id}.*stage=source`));
  await expect(page.getByRole("heading", { name: "来源与小说大纲" })).toBeVisible();
  expect(writes).toEqual([]);
});

test("refuses a storyboard review when its accepted script binding becomes stale", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "story-prototype-stale");
  await acceptStoryboardReview(request, workbench.apiOrigin, id);
  await changeScript(request, workbench.apiOrigin, id);

  await page.goto(`${workbench.frontendOrigin}/v2/?view=story-prototype&project=${id}`);
  await expect(page.getByText(/当前没有可阅读的已接受分镜评审|当前剧本不是可阅读的已接受版本|分镜评审绑定的剧本不是当前已接受版本/)).toBeVisible();
  await expect(page.getByTestId("story-prototype")).toHaveCount(0);
});
