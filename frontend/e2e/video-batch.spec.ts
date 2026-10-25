import { batchVideoTest as test, expect } from "./fixture";

test("known QA context unavailable after copy or stale material never falls back to creator Start", async ({ page, workbench }) => {
  const project = (await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects`)).json()).projects[0].id;
  let starts = 0;
  await page.route("**/qa-context", route => route.fulfill({ json: { required: true, eligible: false, attribution: null,
    reason: "原始运行时授权或当前素材尚未核实；不能改为创作者确认。" } }));
  await page.route("**/video-batch/start", async route => { starts++; await route.continue(); });
  await page.goto(`${workbench.frontendOrigin}/v2/e2e/video-batch-runtime.html?project=${project}`);
  await page.getByRole("button", { name: "用助手准备全部英文方向", exact: true }).click();
  await expect(page.getByRole("button", { name: "开始批量制作", exact: true })).toBeDisabled();
  await expect(page.getByText(/不能改为创作者确认/)).toBeVisible();
  expect(starts).toBe(0);
  expect((await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects/${project}/video-jobs`)).json()).jobs).toHaveLength(0);
});

for (const boundary of ["cancel-failed", "cancel-response-lost", "successor-response-lost"] as const) {
  test(`selective replacement recovers ${boundary} without replaying history or cancelling its successor`, async ({ page, workbench }, info) => {
    test.setTimeout(90000);
    const project = (await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects`)).json()).projects[0].id;
    const api = `${workbench.apiOrigin}/api/v2/projects/${project}/video-batch`;
    await page.goto(`${workbench.frontendOrigin}/v2/e2e/video-batch-runtime.html?project=${project}`);
    await page.getByRole("button", { name: "用助手准备全部英文方向", exact: true }).click();
    await page.getByRole("button", { name: "开始批量制作", exact: true }).click();
    await page.getByRole("button", { name: "审阅全部视频", exact: true }).click({ timeout: 30000 });
    const before = await (await page.request.get(api)).json();
    const original = await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects/${project}/video-jobs`)).json();
    const dialog = page.getByRole("dialog", { name: "审阅全部视频", exact: true });
    await dialog.getByRole("button", { name: /重新制作这个镜头…/ }).first().click();
    await dialog.getByLabel("重做原因或期望变化").fill("QA creative variation: retain tighter camera framing; no invented provider failure.");
    await dialog.getByRole("button", { name: "保存拒绝与修改原因", exact: true }).click();
    await expect(dialog.getByText(/已拒绝：/)).toBeVisible();
    let cancellations = 0, replacements = 0, rejections = 0;
    await page.route("**/video-jobs/*/review", async route => { rejections++; await route.continue(); });
    await page.route("**/video-batch/control", async route => {
      cancellations++;
      if (boundary === "cancel-failed" && cancellations === 1) { await route.abort("failed"); return; }
      if (boundary === "cancel-response-lost" && cancellations === 1) { await route.fetch(); await route.abort("failed"); return; }
      await route.continue();
    });
    await page.route("**/video-batch/replace-rejected", async route => {
      replacements++;
      if (boundary === "successor-response-lost" && replacements === 1) { await route.fetch(); await route.abort("failed"); return; }
      await route.continue();
    });
    await dialog.getByRole("button", { name: "仅重做这些镜头", exact: true }).click();
    if (boundary !== "successor-response-lost") {
      await expect(dialog.getByText(/已核实：/)).toBeVisible();
      await dialog.getByRole("button", { name: "关闭审阅", exact: true }).click();
      await page.reload();
      const current = await (await page.request.get(api)).json();
      expect(current.id).toBe(before.id);
      await page.getByRole("button", { name: boundary === "cancel-failed" ? "审阅全部视频" : "审阅已完成视频与重做镜头", exact: true }).click();
      await dialog.getByRole("button", { name: "仅重做这些镜头", exact: true }).click();
    }
    await expect(dialog).not.toBeVisible();
    const successor = await (await page.request.get(api)).json();
    expect(successor.id).not.toBe(before.id); expect(successor.state).toBe("setup");
    expect(successor.manifest.replacement.batchId).toBe(before.id);
    expect(successor.manifest.newJobs).toBe(1);
    expect(successor.manifest.targets.filter((item: { mode: string }) => item.mode === "reuse")).toHaveLength(5);
    expect(cancellations).toBe(boundary === "cancel-failed" ? 2 : 1); expect(replacements).toBe(1); expect(rejections).toBe(0);
    const after = await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects/${project}/video-jobs`)).json();
    expect(after.jobs).toHaveLength(original.jobs.length);
    await page.reload();
    expect((await (await page.request.get(api)).json()).id).toBe(successor.id);
    await expect(page.getByRole("button", { name: "用助手准备全部英文方向", exact: true })).toBeVisible();
    await page.screenshot({ path: info.outputPath(`selective-${boundary}-1280.png`) });
  });
}

test("native batch survives reload and awaits one atomic audiovisual decision", async ({ page, workbench }, info) => {
  const projects = await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects`)).json();
  const projectId = projects.projects[0].id as string;
  await page.setViewportSize({width:1280,height:768});
  await page.goto(`${workbench.frontendOrigin}/v2/e2e/video-batch-runtime.html?project=${projectId}`);
  await page.getByRole("button",{name:"用助手准备全部英文方向"}).click();
  const start=page.getByRole("button",{name:"开始批量制作",exact:true});
  await expect(start).toBeVisible({timeout:20000});
  const jobsBefore=await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`)).json();
  expect(jobsBefore.jobs).toHaveLength(0);
  await page.getByText("审阅全部英文方向、源时长与编译提示词",{exact:true}).click();
  await expect(page.locator("pre").first()).toContainText("integrated_multimodal_description");
  await start.click();
  await page.reload();
  await expect(page.getByRole("button",{name:"审阅全部视频",exact:true})).toBeVisible({timeout:30000});
  const generated=await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`)).json();
  expect(generated.jobs).toHaveLength(6); expect(generated.jobs.every((job:{selected:boolean})=>!job.selected)).toBe(true);
  await page.getByRole("button",{name:"审阅全部视频",exact:true}).click();
  const dialog=page.getByRole("dialog",{name:"审阅全部视频",exact:true});
  await expect(dialog.locator("video")).toHaveCount(6);
  for(const video of await dialog.locator("video").all()) await expect(video).toHaveAttribute("preload","none");
  await dialog.getByRole("button",{name:"关闭审阅"}).click();
  expect((await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`)).json()).jobs.every((job:{selected:boolean})=>!job.selected)).toBe(true);
  await page.getByRole("button",{name:"审阅全部视频",exact:true}).click();
  let release!:()=>void, acknowledged!:()=>void;
  const held=new Promise<void>(resolve=>{release=resolve;});
  const committed=new Promise<void>(resolve=>{acknowledged=resolve;});
  await page.route("**/video-batch/confirm",async route=>{const response=await route.fetch(); acknowledged(); await held; await route.fulfill({response});});
  await dialog.getByRole("button",{name:"确认全部视频并用于故事",exact:true}).click();
  await committed;
  await page.evaluate(()=>{
    Object.defineProperty(document,"visibilityState",{configurable:true,get:()=>"hidden"}); document.dispatchEvent(new Event("visibilitychange"));
    Object.defineProperty(document,"visibilityState",{configurable:true,get:()=>"visible"}); document.dispatchEvent(new Event("visibilitychange"));
  });
  release();
  await expect(dialog).not.toBeVisible();
  await expect(page.locator("#video-batch-next-action")).not.toBeFocused();
  const selected=await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`)).json();
  expect(selected.jobs.every((job:{selected:boolean})=>job.selected)).toBe(true);
  await expect(page.getByRole("button",{name:"已保存 · 查看故事播放"})).toBeVisible();
  await page.getByRole("button",{name:"查看结果",exact:true}).click();
  await page.screenshot({path:info.outputPath("batch-saved-1280x768.png")});
  for(const size of [{width:1280,height:460},{width:1700,height:900}]) {
    await page.setViewportSize(size); await page.getByRole("button",{name:"查看结果",exact:true}).click();
    const bounds=await page.locator("#video-batch-next-action").boundingBox();
    const guide=await page.locator(".recommended-workflow-guide").boundingBox();
    expect(bounds!.y).toBeGreaterThanOrEqual(guide!.y+guide!.height);
    await page.screenshot({path:info.outputPath(`batch-saved-${size.width}x${size.height}.png`)});
  }
});


test("storyboard batch refreshes the existing player after whole-pack approval", async ({page,workbench})=>{
  const projectId=(await(await page.request.get(`${workbench.apiOrigin}/api/v2/projects`)).json()).projects[0].id;
  await page.goto(`${workbench.frontendOrigin}/v2/e2e/video-batch-runtime.html?project=${projectId}&page=storyboard`);
  await page.getByRole("button",{name:"用助手准备全部英文方向",exact:true}).click();
  await page.getByRole("button",{name:"开始批量制作",exact:true}).click();
  await expect(page.getByRole("button",{name:"审阅全部视频",exact:true})).toBeVisible({timeout:30000});
  await page.getByRole("button",{name:"审阅全部视频",exact:true}).click();
  await page.getByRole("button",{name:"确认全部视频并用于故事",exact:true}).click();
  await page.getByRole("button",{name:"已保存 · 查看故事播放",exact:true}).click();
  await page.locator("#shot-story-preview").getByRole("button",{name:"播放当前",exact:true}).click();
  await expect(page.locator("#shot-story-preview video").first()).toBeAttached();
  const frozen = await page.request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/freeze`);
  expect(frozen.ok(), await frozen.text()).toBeTruthy();
  const writes: string[] = [];
  page.on("request", request => { if (!["GET", "HEAD"].includes(request.method()) && request.url().includes(`/projects/${projectId}/`)) writes.push(request.url()); });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=storyboard#shot-story-preview`);
  await expect(page.getByRole("banner").getByText("冻结只读", { exact: true })).toBeVisible();
  await page.locator("#shot-story-preview").getByRole("button", { name: "播放当前", exact: true }).click();
  const frozenVideo = page.locator("#shot-story-preview video").first();
  await expect.poll(async () => frozenVideo.evaluate(element => (element as HTMLVideoElement).currentTime)).toBeGreaterThan(0.15);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&view=play`);
  await expect(page.getByTestId("play-view")).toBeVisible();
  await page.getByRole("button", { name: "播放当前", exact: true }).click();
  await expect.poll(async () => page.locator("video").first().evaluate(element => (element as HTMLVideoElement).currentTime)).toBeGreaterThan(0.15);
  expect(writes).toEqual([]);
  expect((await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}`)).json()).operationalState).toBe("closed");

});


test("pause survives process restart and resumed completion preserves an unrelated edit",async({page,workbench})=>{
  const projectId=(await(await page.request.get(`${workbench.apiOrigin}/api/v2/projects`)).json()).projects[0].id;
  await page.goto(`${workbench.frontendOrigin}/v2/e2e/video-batch-runtime.html?project=${projectId}`);
  await page.getByRole("button",{name:"用助手准备全部英文方向",exact:true}).click();
  await page.getByRole("button",{name:"开始批量制作",exact:true}).click();
  await page.getByRole("button",{name:"暂停新派发",exact:true}).click();
  await expect(page.getByRole("button",{name:"继续原批次",exact:true})).toBeVisible();
  await workbench.restartBackend();
  await page.reload();
  await expect(page.getByRole("button",{name:"继续原批次",exact:true})).toBeVisible();
  await page.getByRole("button",{name:"继续原批次",exact:true}).click();
  const edit=page.getByRole("textbox",{name:"与后台完成无关的编辑",exact:true});
  await edit.fill("Keep this unrelated foreground edit.");
  const position=await page.evaluate(()=>window.scrollY);
  await expect(page.getByRole("button",{name:"审阅全部视频",exact:true})).toBeAttached({timeout:30000});
  await expect(edit).toBeFocused(); await expect(edit).toHaveValue("Keep this unrelated foreground edit.");
  expect(Math.abs(await page.evaluate(()=>window.scrollY)-position)).toBeLessThan(2);
});

test("aggregate budgets roundtrip through the local UI API and persistence without dispatch", async ({ page, workbench }, info) => {
  const projectId = (await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects`)).json()).projects[0].id;
  const api = `${workbench.apiOrigin}/api/v2/projects/${projectId}/video-batch`;
  let view = await (await page.request.get(api)).json();
  expect(view.manifest.setup).toMatchObject({ maxJobs: null, maxRequestedSeconds: null });
  const cancel = async () => {
    const response = await page.request.post(`${api}/control`, { data: {
      batchId: view.id, expectedControlRevision: view.controlRevision, action: "cancel",
    } });
    expect(response.ok()).toBe(true);
  };
  await cancel();
  await page.setViewportSize({ width: 1280, height: 768 });
  await page.goto(`${workbench.frontendOrigin}/v2/e2e/video-batch-runtime.html?project=${projectId}`);
  await page.getByRole("button", { name: "准备新的缺失视频清单", exact: true }).click();
  await expect(page.getByLabel("最多新视频任务预算")).toHaveValue("unlimited");
  await expect(page.getByLabel("最多请求源秒数预算")).toHaveValue("unlimited");
  const setup = page.getByRole("button", { name: "批量生成缺失视频", exact: true });
  await page.screenshot({ path: info.outputPath("unlimited-budgets-1280x768.png") });
  await setup.click();
  await expect(page.getByText("任务上限 不限 / 源秒上限 不限", { exact: false })).toBeVisible();
  view = await (await page.request.get(api)).json();
  expect(view.manifest.setup).toMatchObject({ maxJobs: null, maxRequestedSeconds: null });
  const unlimitedHash = view.manifestHash;
  await page.reload();
  await expect(page.getByText("任务上限 不限 / 源秒上限 不限", { exact: false })).toBeVisible();
  expect((await (await page.request.get(api)).json()).manifestHash).toBe(unlimitedHash);
  await cancel(); await page.reload();
  await page.getByRole("button", { name: "准备新的缺失视频清单", exact: true }).click();
  await page.getByLabel("最多新视频任务预算").selectOption("finite");
  await expect(setup).toBeDisabled();
  await page.getByLabel("最多新视频任务", { exact: true }).fill("0");
  await expect(setup).toBeDisabled();
  await page.getByLabel("最多新视频任务", { exact: true }).fill("1");
  await page.getByLabel("最多请求源秒数预算").selectOption("finite");
  await expect(setup).toBeDisabled();
  await page.getByLabel("最多请求源秒数", { exact: true }).fill("5");
  await setup.click();
  await expect(page.getByText("任务上限 1 项 / 源秒上限 5 秒", { exact: false })).toBeVisible();
  view = await (await page.request.get(api)).json();
  expect(view.manifest.setup).toMatchObject({ maxJobs: 1, maxRequestedSeconds: 5 });
  expect(view.manifest.blockers.length).toBeGreaterThan(0);
  await expect(page.getByRole("button", { name: "用助手准备全部英文方向", exact: true })).toBeDisabled();
  const finiteHash = view.manifestHash;
  await page.reload();
  await expect(page.getByText("任务上限 1 项 / 源秒上限 5 秒", { exact: false })).toBeVisible();
  expect((await (await page.request.get(api)).json()).manifestHash).toBe(finiteHash);
  expect((await (await page.request.get(`${workbench.apiOrigin}/api/v2/projects/${projectId}/video-jobs`)).json()).jobs).toHaveLength(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: info.outputPath("finite-budgets-1280x768.png") });
});
