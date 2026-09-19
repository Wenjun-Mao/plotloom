import { expect, test } from "./fixture";
import { createScriptProject, fixture } from "./f5a-fixture";

test("reads ordered multi-scene canonical screenplay without writing", async ({ page, request, workbench }, testInfo) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "story-prototype", await multiSceneCandidates());
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
  const opening = prototype.locator('[data-section-id="opening"]');
  await expect(opening.getByText("章节目标时长 90 秒", { exact: true })).toBeVisible();
  const scenes = opening.locator(".screenplay-scene");
  await expect(scenes).toHaveCount(2);
  await expect(scenes.nth(0)).toContainText("Beacon room");
  await expect(scenes.nth(0)).toContainText("光线：dawn");
  await expect(scenes.nth(0)).toContainText("人物：Mira");
  await expect(scenes.nth(0)).toContainText("One cable. Two places need it.");
  await expect(scenes.nth(1)).toContainText("Dock platform");
  await expect(scenes.nth(1)).toContainText("光线：lantern");
  await expect(scenes.nth(1)).toContainText("人物：Ilan");
  await expect(scenes.nth(1)).toContainText("道具：Signal lamp");
  await expect(scenes.nth(1)).toContainText("The dock keeps the boats together.");
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

async function multiSceneCandidates() {
  const [cast, art, script] = await Promise.all([fixture("cast.json"), fixture("art.json"), fixture("script.json")]);
  cast.characters.push({
    id: "watcher",
    name: "Ilan",
    persona: { appearance: "Oilskin coat and a harbor lantern", arc: "Keeps the dock visible", motivation: "Bring boats in safely" },
    voice: { timbre: "Low and careful" },
  });
  art.scenes.push({
    id: "S02",
    name: "Dock platform",
    primary: false,
    summary: "The harbor watcher protects the landing.",
    anchors: [{ name: "wet planks", desc: "rain-slick wood" }, { name: "mooring post", desc: "black iron" }, { name: "rope coil", desc: "salt-stiff hemp" }],
    lighting: [{ state: "lantern", prompt: "amber lantern glow across wet planks" }],
    image: { prompt: "empty harbor dock platform", negativePrompt: "people, human figures", sheet: "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth", tags: [] },
  });
  art.props.push({
    id: "P01",
    name: "Signal lamp",
    summary: "Marks the safe dock approach.",
    anchors: [{ name: "brass hood", desc: "dented brass" }, { name: "green lens", desc: "ribbed glass" }, { name: "wire handle", desc: "looped steel" }],
    states: [{ state: "lit", prompt: "green lens glowing" }],
    scale: "手持级",
    relatedScenes: ["S02"],
    usage: { episodes: [1], beats: [] },
    image: { prompt: "a brass signal lamp at handheld scale on a pure white background", negativePrompt: "people, human hands, fingers", sheet: "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth, handheld scale, pure white background", tags: [] },
  });
  art.sectionUsage[0] = { sectionId: "opening", sceneIds: ["S01", "S02"], propIds: ["P01"] };

  const opening = script.episodes[0];
  const [firstScene, secondScene] = [opening.scenes[0], { ...opening.scenes[0], sceneId: "S02", lighting: "lantern", characters: ["watcher"], props: ["P01"], flow: opening.scenes[0].flow.slice(6).map((item: Record<string, unknown>) => item.speaker === "keeper" ? { ...item, speaker: "watcher" } : item) }];
  firstScene.flow = firstScene.flow.slice(0, 6);
  opening.scenes = [firstScene, secondScene];
  return { cast, art, script };
}
