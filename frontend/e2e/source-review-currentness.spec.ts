import { expect, test } from "./fixture";
import { availableSpecialistWithoutSend, changeScript, createScriptProject, endpoint, fixture, json, writeDelivery } from "./f5a-fixture";
import type { APIRequestContext, Page } from "@playwright/test";

async function acceptedReview(request: APIRequestContext, origin: string, id: string) {
  const root = endpoint(origin, id);
  const prepared = await json(request.post(`${root}/candidates`));
  await writeDelivery(prepared);
  await json(request.post(`${root}/candidates/${prepared.jobId}/refresh`));
  await json(request.post(`${root}/accept`, { data: {
    jobId: prepared.jobId, expectedReviewRevision: 0, binding: prepared.binding,
  } }));
  return (await json(request.get(root))).acceptedReview;
}

async function navigate(page: Page, name: string) {
  await page.getByRole("link", { name, exact: true }).click();
}

for (const width of [1280, 1700]) test(`expanded accepted Script JSON remains inside the ${width}px desktop`, async ({ page, request, workbench }) => {
  const longScript = await fixture("script.json");
  longScript.episodes[0].cliff += ` Layout regression source token ${"ContinuousSourceToken".repeat(120)}`;
  const id = await createScriptProject(request, workbench.apiOrigin, `script-json-layout-${width}`, { script: longScript });
  await page.setViewportSize({ width, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#script`);
  const panel = page.getByTestId("script-review");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  await panel.getByText("查看当前已确认剧本", { exact: true }).click();
  const raw = panel.locator(".script-json-disclosure[open] pre");
  await expect(raw).toBeVisible();
  const geometry = await raw.evaluate(element => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
    rawRight: element.getBoundingClientRect().right,
    whiteSpace: getComputedStyle(element).whiteSpace,
  }));
  expect(geometry.documentWidth).toBeLessThanOrEqual(geometry.viewportWidth);
  expect(geometry.rawRight).toBeLessThanOrEqual(width);
  expect(geometry.whiteSpace).toBe("pre-wrap");
  await expect(page.getByRole("link", { name: "美术参考", exact: true })).toBeInViewport();
});

async function changeArt(request: APIRequestContext, origin: string, id: string) {
  const url = `${origin}/api/v2/projects/${id}/art`;
  const { acceptedArt: base } = await json(request.get(url));
  await json(request.post(`${url}/reopen`, { data: { expectedArtRevision: base.revision } }));
  const art = structuredClone(base.art);
  art.scenes[0].summary += " Changed upstream authority.";
  await json(request.post(`${url}/save`, { data: { expectedArtRevision: base.revision, binding: base.binding, art } }));
}

async function changeCast(request: APIRequestContext, origin: string, id: string) {
  const url = `${origin}/api/v2/projects/${id}/cast`;
  const { acceptedCast: base } = await json(request.get(url));
  await json(request.post(`${url}/reopen`, { data: { expectedCastRevision: base.revision } }));
  const cast = structuredClone(base.cast);
  cast.characters[0].name += " revised";
  await json(request.post(`${url}/save`, { data: { expectedCastRevision: base.revision, binding: base.binding, cast, consumerMappings: base.consumerMappings } }));
}

test("opening-only UI save revalidates the retained sibling review without a page reload", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "sibling-ui-save");
  const retained = await acceptedReview(request, workbench.apiOrigin, id);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const storyboard = page.getByTestId("storyboard-review");
  await expect(storyboard).toContainText("已确认评审 r1");
  await navigate(page, "剧本");
  const script = page.getByTestId("script-review");
  await script.getByRole("button", { name: "重新打开剧本" }).click();
  await script.getByRole("combobox").selectOption({ label: "opening · episode 1" });
  const textarea = script.locator("textarea");
  const episode = JSON.parse(await textarea.inputValue());
  episode.cliff = "Deterministic edited route status; choice remains pending.";
  await textarea.fill(JSON.stringify(episode));
  await script.getByRole("button", { name: "保存此章节，不覆盖其他章节" }).click();
  await expect(script).toContainText("已确认 r2");
  await navigate(page, "分镜评审");
  await expect(storyboard).toContainText("上下文已过期");
  await expect(storyboard).toContainText("script revision changed");
  await expect(storyboard.getByRole("button", { name: "准备投产提案" })).toBeDisabled();
  const state = await json(request.get(endpoint(workbench.apiOrigin, id)));
  expect(state.status).toBe("stale");
  expect(state.acceptedReview).toEqual(retained);
});

test("same-project server refresh revalidates source-review panels", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "same-project-refresh");
  await acceptedReview(request, workbench.apiOrigin, id);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const storyboard = page.getByTestId("storyboard-review");
  await expect(storyboard).toContainText("已确认评审 r1");
  await changeScript(request, workbench.apiOrigin, id);
  await page.getByRole("button", { name: "刷新服务器版本", exact: true }).click();
  await navigate(page, "分镜评审");
  await expect(storyboard).toContainText("上下文已过期");
  await expect(storyboard.getByRole("button", { name: "准备投产提案" })).toBeDisabled();
});

test("pending or failed activation reads retain evidence but cannot enable stale actions", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "held-currentness-read");
  await acceptedReview(request, workbench.apiOrigin, id);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const storyboard = page.getByTestId("storyboard-review");
  await expect(storyboard).toContainText("已确认评审 r1");
  await navigate(page, "剧本");
  await expect(page.getByTestId("script-review")).toContainText("已确认 r1");
  await changeScript(request, workbench.apiOrigin, id);
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const url = `**/api/v2/projects/${id}/storyboard-source-review`;
  await page.route(url, async route => {
    await held;
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "held currentness read failed" }) });
  });
  try {
    await navigate(page, "分镜评审");
    await expect(storyboard).toContainText("正在刷新");
    await expect(storyboard.getByRole("button", { name: "准备分镜任务" })).toBeDisabled();
    await expect(storyboard.getByRole("button", { name: "准备投产提案" })).toBeDisabled();
  } finally {
    release();
  }
  await expect(storyboard).toContainText("无法刷新");
  await expect(storyboard.getByRole("button", { name: "准备分镜任务" })).toBeDisabled();
  await page.unroute(url);
  await storyboard.getByRole("button", { name: "重试加载分镜评审" }).click();
  await expect(storyboard).toContainText("上下文已过期");
  await expect(storyboard.getByRole("button", { name: "准备分镜任务" })).toBeEnabled();
});

test("navigation revalidation preserves a same-project unsaved scoped Script draft", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "retained-scoped-draft");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#script`);
  const script = page.getByTestId("script-review");
  await script.getByRole("button", { name: "重新打开剧本" }).click();
  await script.getByRole("combobox").selectOption({ label: "opening · episode 1" });
  const textarea = script.locator("textarea");
  const draft = `${await textarea.inputValue()}\n `;
  await textarea.fill(draft);
  await navigate(page, "美术参考");
  await expect(page.getByTestId("art-review")).toContainText("已确认美术设定 r1");
  await navigate(page, "剧本");
  await expect(script.getByRole("button", { name: "保存此章节，不覆盖其他章节" })).toBeEnabled();
  await expect(textarea).toHaveValue(draft);
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/script`))).acceptedScript.revision).toBe(1);
});

for (const authority of ["head", "status"] as const) test(`dirty Script retains original text after an accepted ${authority} change`, async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, `dirty-script-${authority}`);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#script`);
  const panel = page.getByTestId("script-review");
  await panel.getByRole("button", { name: "重新打开剧本" }).click();
  await panel.getByRole("combobox").selectOption({ label: "opening · episode 1" });
  const draft = `${await panel.locator("textarea").inputValue()}\n `;
  await panel.locator("textarea").fill(draft);
  if (authority === "head") await changeScript(request, workbench.apiOrigin, id);
  else await changeArt(request, workbench.apiOrigin, id);
  await navigate(page, "美术参考");
  await navigate(page, "剧本");
  const retained = panel.getByRole("region", { name: "保留的未保存章节" });
  await expect(retained).toContainText("剧本 r1");
  await expect(retained.getByRole("textbox")).toHaveValue(draft);
  await expect(retained.getByRole("button", { name: "保存此章节，不覆盖其他章节" })).toBeDisabled();
  await retained.getByRole("button", { name: "用当前章节替换草稿" }).click();
  await expect(retained).toHaveCount(0);
  await expect(panel).toContainText(`已确认 r${authority === "head" ? 2 : 1}`);
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/script`))).acceptedScript.revision).toBe(authority === "head" ? 2 : 1);
});

test("dirty Art survives reopened-to-stale status with the same accepted revision", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "dirty-art-stale");
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#art`);
  const panel = page.getByTestId("art-review");
  await panel.getByRole("button", { name: "重新打开美术提案" }).click();
  await expect(panel.getByRole("button", { name: "保存重新打开的美术" })).toBeEnabled();
  await panel.locator("details.art-json-editor").last().locator("summary").click();
  const editor = panel.locator("details.art-json-editor textarea").last();
  const draft = `${await editor.inputValue()}\n `;
  await editor.fill(draft);
  await changeCast(request, workbench.apiOrigin, id);
  await navigate(page, "剧本");
  await navigate(page, "美术参考");
  const retained = panel.getByRole("region", { name: "保留的未保存美术草稿" });
  await expect(retained).toContainText("美术 r1");
  await expect(retained.getByRole("textbox")).toHaveValue(draft);
  await expect(retained.getByRole("button", { name: "保存重新打开的美术" })).toBeDisabled();
  await retained.getByRole("button", { name: "舍弃美术草稿" }).click();
  await expect(retained).toHaveCount(0);
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/art`))).acceptedArt.revision).toBe(1);
});

for (const stage of ["script", "storyboard"] as const) for (const ready of [false, true]) {
  test(`stale ${stage} ${ready ? "ready" : "prepared"} candidate blocks acceptance/dispatch but permits cancellation`, async ({ page, request, workbench }) => {
    const id = await createScriptProject(request, workbench.apiOrigin, `stale-${stage}-${ready}`);
    const url = stage === "script" ? `${workbench.apiOrigin}/api/v2/projects/${id}/script` : endpoint(workbench.apiOrigin, id);
    const prepared = await json(request.post(`${url}/candidates`));
    const sends = await availableSpecialistWithoutSend(page, id, stage, prepared.jobId);
    if (ready) {
      await writeDelivery(prepared, stage, stage === "script" ? await fixture("script.json") : undefined);
      await json(request.post(`${url}/candidates/${prepared.jobId}/refresh`));
    }
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#${stage === "script" ? "script" : "storyboard-review"}`);
    const panel = page.getByTestId(stage === "script" ? "script-review" : "storyboard-review");
    if (!ready) await expect(panel.getByRole("button", { name: "发送给文字创作助手" })).toBeEnabled();
    if (stage === "script") await changeArt(request, workbench.apiOrigin, id);
    else await changeScript(request, workbench.apiOrigin, id);
    await page.reload();
    await expect(panel).toContainText("上下文已过期");
    if (ready) {
      await expect(panel.getByRole("button", { name: stage === "script" ? "确认使用此剧本" : "确认此分镜评审方案" })).toBeDisabled();
      await expect(panel.getByRole("button", { name: stage === "script" ? "拒绝并取消此剧本" : "拒绝并取消此评审" })).toBeEnabled();
    } else {
      await expect(panel.getByRole("button", { name: "发送给文字创作助手" })).toBeDisabled();
      await expect(panel.getByRole("button", { name: "立即检查" })).toBeEnabled();
      await expect(panel.getByRole("button", { name: "取消此任务", exact: true })).toBeEnabled();
    }
    expect(sends()).toBe(0);
  });
}

test("failed post-mutation refresh disables old successful authority until explicit retry", async ({ page, request, workbench }) => {
  const id = await createScriptProject(request, workbench.apiOrigin, "post-mutation-failure");
  const url = endpoint(workbench.apiOrigin, id);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=source#storyboard-review`);
  const panel = page.getByTestId("storyboard-review");
  await expect(panel.getByRole("button", { name: "准备分镜任务" })).toBeEnabled();
  await page.route(`**/api/v2/projects/${id}/storyboard-source-review`, route => route.fulfill({ status: 503, body: JSON.stringify({ detail: "post-mutation read failed" }) }));
  await panel.getByRole("button", { name: "准备分镜任务" }).click();
  await expect(panel).toContainText("无法刷新");
  await expect(panel.getByRole("button", { name: "准备分镜任务" })).toBeDisabled();
  expect((await json(request.get(url))).candidate.status).toBe("prepared");
  await page.unroute(`**/api/v2/projects/${id}/storyboard-source-review`);
  await panel.getByRole("button", { name: "重试加载分镜评审" }).click();
  await expect(panel.getByRole("button", { name: "取消此任务", exact: true })).toBeEnabled();
});
