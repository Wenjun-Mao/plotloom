import { batchVideoTest as test, expect } from "./fixture";

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
