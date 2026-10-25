import { expect, test } from "./fixture";
import { createScriptProject, fixture, json, writeDelivery } from "./f5a-fixture";

test.use({ actionTimeout: 10_000 });

test("node Story retains every scene and losslessly saves the original dirty section across selection and modes", async ({ page, request, workbench }, info) => {
  test.setTimeout(90_000);
  const script = await fixture("script.json");
  const first = script.episodes[0].scenes[0];
  script.episodes[0].scenes = [{ ...first, flow: first.flow.slice(0, 10) }, { ...first, flow: first.flow.slice(10) }];
  const id = await createScriptProject(request, workbench.apiOrigin, "creator-story", { script });
  const url = `${workbench.apiOrigin}/api/v2/projects/${id}/script`;
  const retained = (await json(request.get(url))).acceptedScript;
  const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
  await page.setViewportSize({ width: 1700, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await page.getByText("场景、动作与对白", { exact: true }).click();
  const panel = page.getByTestId("script-review");
  const selectedNodeReader = panel.getByRole("region", { name: "当前已确认剧本 r1 · 节点 opening", exact: true });
  const wholeScriptReader = panel.getByRole("region", { name: "当前已确认剧本 r1", exact: true });
  await expect(selectedNodeReader).toBeVisible();
  await expect(wholeScriptReader).toBeVisible();
  const scenes = selectedNodeReader.locator("[data-script-occurrence]");
  await expect(scenes).toHaveCount(2);
  const wholeScriptScenes = wholeScriptReader.locator("[data-script-occurrence]");
  await expect(wholeScriptScenes).toHaveCount(retained.script.episodes.reduce((total: number, episode: { scenes: unknown[] }) => total + episode.scenes.length, 0));
  const expectedFlowByScene = retained.script.episodes[0].scenes.map((scene: { flow: Array<{ action?: string; speaker?: string; line?: string; delivery?: string }> }) =>
    scene.flow.map((item: { action?: string; speaker?: string; line?: string; delivery?: string }) => {
      if (typeof item.action === "string") return item.action;
      return `${item.speaker}：${item.line}${typeof item.delivery === "string" ? ` · ${item.delivery}` : ""}`;
    })
  );
  for (const [sceneIndex, expectedFlow] of expectedFlowByScene.entries()) {
    await expect(scenes.nth(sceneIndex).locator("[data-flow-order]")).toHaveText(expectedFlow);
  }
  await expect(scenes.nth(0).locator("[data-flow-order]").nth(2)).toContainText("One cable. Two places need it.");
  await expect(scenes.nth(1).locator("[data-flow-order]").nth(9)).toContainText("The unconnected cable rests across the desk between both switches.");
  await page.screenshot({ path: info.outputPath("all-scene-occurrences.png"), fullPage: true });
  await panel.getByRole("button", { name: "重新打开剧本", exact: true }).click();
  const editor = panel.getByLabel("opening 章节剧本 JSON", { exact: true });
  await expect(editor).toBeVisible();
  const episode = JSON.parse(await editor.inputValue());
  expect(episode).toEqual(retained.script.episodes[0]);
  episode.scenes[0].flow[0].action += " She protects the original route evidence.";
  const text = JSON.stringify(episode, null, 2);
  await editor.fill(text);
  await page.locator('[data-creator-node="beacon"] .creator-node-select').click();
  await expect(panel).toContainText("正在保留 opening 的未保存章节");
  await expect(editor).toHaveValue(text);
  await page.getByRole("tab", { name: "制作", exact: true }).click();
  await page.getByRole("tab", { name: "故事", exact: true }).click();
  await expect(editor).toHaveValue(text);
  await page.getByRole("button", { name: "专业工作台", exact: true }).click();
  await expect(page).toHaveURL(/stage=graph/);
  await page.getByRole("button", { name: "创作工作台", exact: true }).click();
  await page.getByText("场景、动作与对白", { exact: true }).click();
  await panel.getByRole("combobox").selectOption({ label: "opening · episode 1" });
  await expect(editor).toHaveValue(text);
  await page.reload();
  await page.getByText("场景、动作与对白", { exact: true }).click();
  await panel.getByRole("combobox").selectOption({ label: "opening · episode 1" });
  await expect(panel.getByRole("button", { name: "恢复编辑草稿", exact: true })).toHaveCount(0);
  await expect(editor).toHaveValue(text);
  expect((await json(request.get(url))).acceptedScript).toEqual(retained);
  await panel.getByRole("button", { name: "保存此章节，不覆盖其他章节", exact: true }).click();
  await expect(panel).toContainText("已确认 r2");
  const accepted = (await json(request.get(url))).acceptedScript;
  expect(accepted.script.episodes).toEqual([episode, ...retained.script.episodes.slice(1)]);
  expect(accepted.script.sectionBindings).toEqual(retained.script.sectionBindings);
  await panel.getByText("阅读原始剧本报告（只读）", { exact: true }).click();
  await expect(page.frameLocator('iframe[title="原始剧本交付报告（只读）"]').locator("body")).toContainText("does not describe the current accepted revision");
  await page.locator('[data-creator-node="power-choice"] .creator-node-select').click();
  const routeOnlyReader = panel.getByRole("region", { name: "当前已确认剧本 r2 · 节点 power-choice", exact: true });
  await expect(routeOnlyReader).toContainText("路线控制点，没有自己的画面场次");
  await expect(routeOnlyReader.locator("[data-script-occurrence]")).toHaveCount(0);
  const updatedWholeScriptReader = panel.getByRole("region", { name: "当前已确认剧本 r2", exact: true });
  await expect(updatedWholeScriptReader.locator("[data-script-occurrence]")).toHaveCount(accepted.script.episodes.reduce((total: number, episode: { scenes: unknown[] }) => total + episode.scenes.length, 0));
  expect(errors).toEqual([]);
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/runs`))).runs).toEqual([]);
});

test("creator Story retries reads and reuses explicit whole-package prepare, check, report, accept and cancel", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "creator-script-task", {}, ["cast", "art"]);
  const url = `${workbench.apiOrigin}/api/v2/projects/${id}/script`;
  let failed = true;
  await page.route(`**/api/v2/projects/${id}/script`, route => failed ? route.fulfill({ status: 503, json: { detail: "read fixture unavailable" } }) : route.continue());
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await page.getByText("场景、动作与对白", { exact: true }).click();
  const panel = page.getByTestId("script-review");
  await expect(panel).toContainText("无法加载");
  failed = false;
  await panel.getByRole("button", { name: "重试加载剧本", exact: true }).click();
  await expect(panel).toContainText("影响整份剧本");
  await panel.getByRole("button", { name: "准备剧本任务", exact: true }).click();
  await expect(panel.getByRole("button", { name: "取消此任务", exact: true })).toBeEnabled();
  const cancelled = (await json(request.get(url))).candidate;
  await panel.getByRole("button", { name: "取消此任务", exact: true }).click();
  await expect(panel.getByRole("button", { name: "准备剧本任务", exact: true })).toBeEnabled();
  await panel.getByRole("button", { name: "准备剧本任务", exact: true }).click();
  await expect(panel.getByRole("button", { name: "取消此任务", exact: true })).toBeEnabled();
  const candidate = (await json(request.get(url))).candidate;
  expect(candidate.jobId).not.toBe(cancelled.jobId);
  const prepared = await json(request.get(`${url}/candidates/${candidate.jobId}/handoff`));
  await writeDelivery(prepared, "script", await fixture("script.json"));
  await panel.getByRole("button", { name: "立即检查", exact: true }).click();
  await expect(panel.getByRole("button", { name: "确认使用此剧本", exact: true })).toBeEnabled();
  await panel.getByText("阅读原始剧本报告（只读）", { exact: true }).click();
  await expect(page.frameLocator('iframe[title="原始剧本交付报告（只读）"]').locator("body")).toContainText("Deterministic upstream-context fixture report");
  await panel.getByRole("button", { name: "确认使用此剧本", exact: true }).click();
  await expect(panel).toContainText("已确认 r1");
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/runs`))).runs).toEqual([]);
});

test("creator observes automatic result checking without another send or automatic acceptance", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "creator-auto-check", {}, ["cast", "art"]);
  const url = `${workbench.apiOrigin}/api/v2/projects/${id}/script`;
  const prepared = await json(request.post(`${url}/candidates`));
  const taskUrl = `**/api/v2/projects/${id}/specialist-tasks/script/${prepared.jobId}`;
  // Transport-only queued receipt; all delivery checks and review state use the
  // real disposable API. No assistant or provider receives a dispatch.
  await page.route(taskUrl, async route => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...await response.json(), state: "queued", configured: true } });
  });
  let sends = 0, checks = 0;
  page.on("request", request => { if (request.url().endsWith("/send")) sends++; if (request.url().endsWith("/check")) checks++; });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await page.getByText("场景、动作与对白", { exact: true }).click();
  const panel = page.getByTestId("script-review");
  await expect(panel).toContainText("自动检查交付中");
  await writeDelivery(prepared, "script", await fixture("script.json"));
  await expect(panel.getByRole("button", { name: "确认使用此剧本", exact: true })).toBeEnabled();
  const state = await json(request.get(url));
  expect(state.candidate.status).toBe("ready");
  expect(state.acceptedScript).toBeNull();
  expect(checks).toBeGreaterThanOrEqual(1); expect(sends).toBe(0);
});
