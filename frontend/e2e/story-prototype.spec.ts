import { expect, test } from "./fixture";
import { changeScript, createScriptProject, endpoint, fixture, json, writeDelivery } from "./f5a-fixture";

async function acceptStoryboardReview(request: Parameters<typeof createScriptProject>[0], origin: string, id: string) {
  const prepared = await json(request.post(`${endpoint(origin, id)}/candidates`));
  await writeDelivery(prepared);
  await json(request.post(`${endpoint(origin, id)}/candidates/${prepared.jobId}/refresh`));
  await json(request.post(`${endpoint(origin, id)}/accept`, { data: { jobId: prepared.jobId, expectedReviewRevision: prepared.expectedReviewRevision, binding: prepared.binding } }));
}

test("reads ordered multi-scene canonical screenplay without a storyboard review", async ({ page, request, workbench }, testInfo) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "story-prototype-f4", await multiSceneCandidates());
  const writes: string[] = [];
  page.on("request", (pending) => { if (pending.url().includes("/api/v2/") && pending.method() !== "GET") writes.push(`${pending.method()} ${pending.url()}`); });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?view=story-prototype&project=${id}`);
  const prototype = page.getByTestId("story-prototype");
  await expect(prototype).toContainText("界面为中文；已确认原文内容按接受版本呈现。");
  await expect(prototype).toContainText("已确认原文");
  await expect(prototype).not.toContainText("英文原文");
  await expect(prototype).not.toContainText("英文源内容保持原样");
  await expect(prototype.getByTestId("route-reader")).toContainText("One cable. Two places need it.");
  const scenes = prototype.locator('[data-section-id="opening"] .screenplay-scene');
  await expect(scenes).toHaveCount(2);
  await expect(scenes.nth(0)).toContainText("Beacon room");
  await expect(scenes.nth(0)).toContainText("One cable. Two places need it.");
  await expect(scenes.nth(1)).toContainText("Dock platform");
  await expect(scenes.nth(1)).toContainText("光线：lantern");
  await expect(scenes.nth(1)).toContainText("人物：Ilan");
  await expect(scenes.nth(1)).toContainText("道具：Signal lamp");
  await expect(scenes.nth(1)).toContainText("The dock keeps the boats together.");
  await expect(prototype.getByRole("button", { name: "分镜 · 当前不可读" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("screenplay-f4-1440.png"), fullPage: true });
  await prototype.getByRole("button", { name: "分镜 · 当前不可读" }).click();
  await expect(prototype.getByTestId("storyboard-unavailable")).toContainText("这不会影响已确认剧本");
  await prototype.getByRole("button", { name: "剧本" }).click();
  await expect(prototype.getByTestId("route-reader")).toContainText("One cable. Two places need it.");
  await page.setViewportSize({ width: 720, height: 900 });
  await page.screenshot({ path: testInfo.outputPath("screenplay-f4-720.png"), fullPage: true });
  expect(writes).toEqual([]);
});

test("switches route-focused screenplay and matching storyboard without appending either reader", async ({ page, request, workbench }, testInfo) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "story-prototype-f5");
  await acceptStoryboardReview(request, workbench.apiOrigin, id);
  const writes: string[] = [];
  page.on("request", (pending) => { if (pending.url().includes("/api/v2/") && pending.method() !== "GET") writes.push(`${pending.method()} ${pending.url()}`); });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?view=story-prototype&project=${id}`);
  const prototype = page.getByTestId("story-prototype");
  await expect(prototype.getByTestId("route-reader")).toContainText("Beacon first.");
  await expect(prototype.getByTestId("storyboard-reader")).toHaveCount(0);
  await prototype.getByRole("button", { name: /选择：Light the dock/ }).click();
  await expect(prototype.getByTestId("route-reader")).toContainText("Dock first.");
  await prototype.getByRole("button", { name: "分镜" }).click();
  const storyboard = prototype.getByTestId("storyboard-reader");
  await expect(storyboard).toContainText("按路径查看章节、段落与镜头");
  await expect(storyboard).toContainText("上游画面提示（原样）");
  await expect(storyboard).not.toContainText("画面 / 动作");
  await expect(storyboard).toContainText("The dock stays on.");
  await expect(storyboard).not.toContainText("Sailors can see the channel now.");
  await expect(prototype.getByTestId("route-reader")).toHaveCount(0);
  await prototype.getByRole("button", { name: /Storm warning/ }).first().click();
  await expect(storyboard).toContainText("The dock stays on.");
  const instructions = storyboard.locator(".generation-instructions").first();
  await expect(instructions.locator("pre")).not.toBeVisible();
  await instructions.locator("summary").click();
  await expect(instructions.locator("pre")).toContainText("How the reference pictures align");
  await page.screenshot({ path: testInfo.outputPath("storyboard-f5-1440.png"), fullPage: true });
  await page.setViewportSize({ width: 1920, height: 1080 });
  await prototype.locator(".branch-map").screenshot({ path: testInfo.outputPath("branch-map-f5-1920.png") });
  await page.screenshot({ path: testInfo.outputPath("storyboard-f5-1920.png"), fullPage: true });
  await page.setViewportSize({ width: 768, height: 900 });
  await prototype.locator(".branch-map").screenshot({ path: testInfo.outputPath("branch-map-f5-768.png") });
  await page.screenshot({ path: testInfo.outputPath("storyboard-f5-768.png"), fullPage: true });
  await page.setViewportSize({ width: 720, height: 900 });
  await prototype.locator(".branch-map").screenshot({ path: testInfo.outputPath("branch-map-f5-720.png") });
  await prototype.getByRole("button", { name: "剧本" }).click();
  await expect(prototype.getByTestId("route-reader")).toContainText("Dock first.");
  expect(writes).toEqual([]);
});

test("refuses a stale storyboard locally while retaining the current screenplay", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "story-prototype-stale");
  await acceptStoryboardReview(request, workbench.apiOrigin, id);
  await changeScript(request, workbench.apiOrigin, id);
  await page.goto(`${workbench.frontendOrigin}/v2/?view=story-prototype&project=${id}`);
  const prototype = page.getByTestId("story-prototype");
  await expect(prototype.getByTestId("route-reader")).toContainText("Deterministic edited route status");
  await prototype.getByRole("button", { name: "分镜 · 当前不可读" }).click();
  await expect(prototype.getByTestId("storyboard-unavailable")).toContainText("当前没有可阅读的已确认分镜评审");
});

async function multiSceneCandidates() {
  const [cast, art, script] = await Promise.all([fixture("cast.json"), fixture("art.json"), fixture("script.json")]);
  cast.characters.push({ id: "watcher", name: "Ilan", persona: { appearance: "Oilskin coat and a harbor lantern", arc: "Keeps the dock visible", motivation: "Bring boats in safely" }, voice: { timbre: "Low and careful" } });
  art.scenes.push({ id: "S02", name: "Dock platform", primary: false, summary: "The harbor watcher protects the landing.", anchors: [{ name: "wet planks", desc: "rain-slick wood" }, { name: "mooring post", desc: "black iron" }, { name: "rope coil", desc: "salt-stiff hemp" }], lighting: [{ state: "lantern", prompt: "amber lantern glow across wet planks" }], image: { prompt: "empty harbor dock platform", negativePrompt: "people, human figures", sheet: "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth", tags: [] } });
  art.props.push({ id: "P01", name: "Signal lamp", summary: "Marks the safe dock approach.", anchors: [{ name: "brass hood", desc: "dented brass" }, { name: "green lens", desc: "ribbed glass" }, { name: "wire handle", desc: "looped steel" }], states: [{ state: "lit", prompt: "green lens glowing" }], scale: "手持级", relatedScenes: ["S02"], usage: { episodes: [1], beats: [] }, image: { prompt: "a brass signal lamp at handheld scale on a pure white background", negativePrompt: "people, human hands, fingers", sheet: "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth, handheld scale, pure white background", tags: [] } });
  art.sectionUsage[0] = { sectionId: "opening", sceneIds: ["S01", "S02"], propIds: ["P01"] };
  const opening = script.episodes[0];
  const [firstScene, secondScene] = [opening.scenes[0], { ...opening.scenes[0], sceneId: "S02", lighting: "lantern", characters: ["watcher"], props: ["P01"], flow: opening.scenes[0].flow.slice(6).map((item: Record<string, unknown>) => item.speaker === "keeper" ? { ...item, speaker: "watcher" } : item) }];
  firstScene.flow = firstScene.flow.slice(0, 6);
  opening.scenes = [firstScene, secondScene];
  return { cast, art, script };
}
