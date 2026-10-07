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
  await prototype.getByRole("button", { name: /播放路线 .*Light the dock/ }).click();
  await expect(prototype.getByTestId("route-reader")).toContainText("Dock first.");
  await prototype.getByRole("button", { name: "分镜" }).click();
  const storyboard = prototype.getByTestId("storyboard-reader");
  await expect(storyboard).toContainText("按路径查看章节、段落与镜头");
  await expect(storyboard).toContainText("上游画面提示（原样）");
  await expect(storyboard).not.toContainText("画面 / 动作");
  await expect(storyboard).toContainText("The dock stays on.");
  await expect(storyboard).not.toContainText("Sailors can see the channel now.");
  await expect(prototype.getByTestId("route-reader")).toHaveCount(0);
  await prototype.getByText("打开上游分镜报告（静态阅读）", { exact: true }).click();
  await expect(prototype).toContainText("原始归档与已确认评审内容保持独立");
  const report = prototype.locator('iframe[title="static upstream storyboard report"]');
  await expect(report).toHaveAttribute("sandbox", "");
  await expect(report).toHaveAttribute("referrerpolicy", "no-referrer");
  await expect(report).toHaveAttribute("src", /presentation=static/);
  await prototype.getByText("打开上游分镜报告（静态阅读）", { exact: true }).click();
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

test("shows pending storyboard reads distinctly and retries fatal reader errors without writes", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "story-prototype-read-recovery");
  let rejectScriptRead = true;
  await page.route(`**/api/v2/projects/${id}/script`, async route => {
    if (rejectScriptRead) { await route.fulfill({ status: 503, json: { detail: "暂时无法读取剧本" } }); }
    else await route.continue();
  });
  let finishStoryboard!: () => void;
  const held = new Promise<void>(resolve => { finishStoryboard = resolve; });
  await page.route(`**/api/v2/projects/${id}/storyboard-source-review`, async route => { await held; await route.continue(); });
  const writes: string[] = [];
  page.on("request", request => { if (request.url().includes("/api/v2/") && request.method() !== "GET") writes.push(request.method()); });
  try {
    await page.goto(`${workbench.frontendOrigin}/v2/?view=story-prototype&project=${id}`);
    await expect(page.getByRole("heading", { name: "暂时无法阅读故事" })).toBeVisible();
    await expect(page.getByRole("link", { name: "返回创作流程", exact: true })).toBeVisible();
    rejectScriptRead = false;
    await page.getByRole("button", { name: "重新读取故事" }).click();
    await expect(page.getByTestId("story-prototype")).toBeVisible();
    await expect(page.getByRole("button", { name: "分镜 · 正在检查" })).toBeVisible();
    await expect(page.getByRole("button", { name: "分镜 · 当前不可读" })).toHaveCount(0);
    finishStoryboard();
    await expect(page.getByRole("button", { name: "分镜 · 当前不可读" })).toBeVisible();
    expect(writes).toEqual([]);
  } finally { finishStoryboard(); }
});

async function multiSceneCandidates() {
  const [cast, art, script] = await Promise.all([fixture("cast.json"), fixture("art.json"), fixture("script.json")]);
  cast.characters.push({ id: "watcher", name: "Ilan", reviewNotes: { sourceNotes: "Appearance is proposed", performanceGuidance: "" }, persona: { personality: ["Careful"],  appearance: "Oilskin coat and a harbor lantern", arc: "Keeps the dock visible", motivation: "Bring boats in safely" }, voice: { timbre: "Low and careful" } });
  art.scenes.push({ id: "S02", name: "Dock platform", primary: false, summary: "The harbor watcher protects the landing.", anchors: [{ name: "wet planks", desc: "rain-slick wood" }, { name: "mooring post", desc: "black iron" }, { name: "rope coil", desc: "salt-stiff hemp" }], lighting: [{ state: "lantern", prompt: "amber lantern glow across wet planks" }], image: { prompt: "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth, empty harbor dock platform", negativePrompt: "people, human figures", sheet: "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth", tags: [] } });
  art.props.push({ id: "P01", name: "Signal lamp", summary: "Marks the safe dock approach.", anchors: [{ name: "brass hood", desc: "dented brass" }, { name: "green lens", desc: "ribbed glass" }, { name: "wire handle", desc: "looped steel" }], states: [{ state: "lit", prompt: "green lens glowing" }], scale: "手持级", relatedScenes: ["S02"], usage: { episodes: [1], beats: [] }, image: { prompt: "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth, a brass signal lamp at handheld scale on a pure white background", negativePrompt: "people, human hands, fingers", sheet: "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth, handheld scale, pure white background", tags: [] } });
  art.sectionUsage[0] = { sectionId: "opening", sceneIds: ["S01", "S02"], propIds: ["P01"] };
  const opening = script.episodes[0];
  const [firstScene, secondScene] = [opening.scenes[0], { ...opening.scenes[0], sceneId: "S02", lighting: "lantern", characters: ["watcher"], props: ["P01"], flow: opening.scenes[0].flow.slice(6).map((item: Record<string, unknown>) => item.speaker === "keeper" ? { ...item, speaker: "watcher" } : item) }];
  firstScene.flow = firstScene.flow.slice(0, 6);
  opening.scenes = [firstScene, secondScene];
  return { cast, art, script };
}

test("keeps all nine explicit routes through shared joins and endings in both readers", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "shared-ending-reader");
  await acceptStoryboardReview(request, workbench.apiOrigin, id);
  const root = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const stages = await json(request.get(`${root}/stages`));
  const scriptState = await json(request.get(`${root}/script`));
  const reviewState = await json(request.get(`${root}/storyboard-source-review`));
  const graphStage = stages.stages.find((stage: any) => stage.head.stage === "story_graph");
  const nodes = ["opening", "first-choice", "branch-1", "branch-2", "branch-3", "join", "second-choice", "ending-1", "ending-2", "ending-3"];
  const footage = nodes.filter(node => !node.endsWith("choice"));
  const edge = (sourceNodeId: string, targetNodeId: string, choiceText = "") => ({ id: `${sourceNodeId}-${targetNodeId}`, sourceNodeId, targetNodeId, kind: choiceText ? "choice" : "continuation", choiceText, stateEffects: {}, entityStateEffects: [] });
  graphStage.payload = { ...graphStage.payload, startNodeId: "opening", nodes: nodes.map(node => ({ id: node, title: node, kind: node === "opening" ? "start" : node.endsWith("choice") ? "decision" : node === "join" ? "join" : node.startsWith("ending") ? "ending" : "scene", footageMode: footage.includes(node) ? "footage" : "route_only" })), edges: [edge("opening", "first-choice"), ...[1, 2, 3].flatMap(n => [edge("first-choice", `branch-${n}`, `inspect-${n}`), edge(`branch-${n}`, "join")]), edge("join", "second-choice"), ...[1, 2, 3].map(n => edge("second-choice", `ending-${n}`, `mode-${n}`))] };
  const bindings = footage.map((sectionId, index) => ({ sectionId, episode: index + 1 }));
  const accepted = scriptState.acceptedScript;
  accepted.binding.sectionBindings = bindings;
  accepted.script = { ...accepted.script, sectionBindings: bindings, episodes: bindings.map(({ sectionId, episode }) => ({ ep: episode, scenes: [{ sceneId: "S01", flow: [{ action: `SCRIPT ${sectionId}` }] }] })) };
  reviewState.acceptedReview.binding.sectionBindings = bindings;
  reviewState.acceptedReview.storyboard = { episodes: bindings.map(({ sectionId, episode }) => ({ ep: episode, segments: [{ sceneIndex: 1, cuts: [{ frame: `FRAME ${sectionId}`, seconds: 5 }] }] })) };
  // Read-only transport fixture: exercise the production reader's exact current bindings.
  await page.route(`**/api/v2/projects/${id}/stages`, route => route.fulfill({ json: stages }));
  await page.route(`**/api/v2/projects/${id}/script`, route => route.fulfill({ json: scriptState }));
  await page.route(`**/api/v2/projects/${id}/storyboard-source-review`, route => route.fulfill({ json: reviewState }));
  const writes: string[] = [];
  page.on("request", request => { if (request.url().includes("/api/v2/") && request.method() !== "GET") writes.push(request.method()); });
  await page.setViewportSize({ width: 1700, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?view=story-prototype&project=${id}`);
  const prototype = page.getByTestId("story-prototype");
  await expect(prototype.locator(".branch-choice")).toHaveCount(9);
  for (let branch = 1; branch <= 3; branch++) for (let ending = 1; ending <= 3; ending++) {
    const route = prototype.getByRole("button", { name: new RegExp(`^播放路线 ${(branch - 1) * 3 + ending}：`) });
    await route.click();
    await expect(route).toHaveAttribute("aria-pressed", "true");
    const expectedSections = ["opening", `branch-${branch}`, "join", `ending-${ending}`];
    await prototype.getByRole("button", { name: "剧本", exact: true }).click();
    const screenplay = prototype.getByTestId("route-reader");
    await expect(screenplay.locator(".screenplay-section")).toHaveCount(4);
    await expect(screenplay.locator(`[data-section-id="ending-${ending}"]`)).toHaveClass(/focused/);
    expect(await screenplay.locator("[data-section-id]").evaluateAll(elements => elements.map(element => element.getAttribute("data-section-id")))).toEqual(expectedSections);
    await expect(screenplay).toContainText(`SCRIPT branch-${branch}`);
    await expect(screenplay).toContainText(`SCRIPT ending-${ending}`);
    await prototype.getByRole("button", { name: "分镜", exact: true }).click();
    const storyboard = prototype.getByTestId("storyboard-reader");
    await expect(storyboard.locator(".storyboard-episode")).toHaveCount(4);
    expect(await storyboard.locator("[data-storyboard-section]").evaluateAll(elements => elements.map(element => element.getAttribute("data-storyboard-section")))).toEqual(expectedSections);
    await expect(storyboard).toContainText(`FRAME branch-${branch}`);
    await expect(storyboard).toContainText(`FRAME ending-${ending}`);
    await prototype.getByRole("button", { name: /^开场/ }).click();
    await expect(route).toHaveAttribute("aria-pressed", "true");
    await storyboard.getByRole("button", { name: /join/ }).click();
    await expect(route).toHaveAttribute("aria-pressed", "true");
  }
  expect(writes).toEqual([]);
});
