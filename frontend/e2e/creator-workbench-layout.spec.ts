import { expect, test } from "./fixture";
import { createCreatorGraph } from "./fixtures/creator-graph";
import { json } from "./f5a-fixture";

for (const viewport of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) test(`creator desktop rows and tall inspector ${viewport.width}x${viewport.height}`, async ({ page, request, workbench }, info) => {
  await page.setViewportSize(viewport);
  const failures: string[] = []; page.on("pageerror", error => failures.push(error.message));
  const id = await createCreatorGraph(request, workbench.apiOrigin, `${viewport.width}-${viewport.height}`, 6, 12);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await expect(page.getByRole("heading", { name: "创作工作台", exact: true })).toBeVisible();
  const chart = page.getByLabel("剧情图横向平移", { exact: true }), inspector = page.getByRole("complementary", { name: "当前节点详情" });
  await expect(page.locator("[data-creator-node]")).toHaveCount(24);
  const metrics = await chart.evaluate(element => ({ scroll: element.scrollWidth > element.clientWidth, height: element.scrollHeight, outer: (element as HTMLElement).offsetHeight, vertical: getComputedStyle(element).overflowY }));
  expect(metrics.scroll).toBe(true); expect(metrics.vertical).toBe("hidden"); expect(metrics.height, JSON.stringify(metrics)).toBeLessThanOrEqual(metrics.outer + 1);
  expect((await page.locator(".creator-row-insert").last().boundingBox())!.y + (await page.locator(".creator-row-insert").last().boundingBox())!.height).toBeLessThanOrEqual((await chart.boundingBox())!.y + (await chart.boundingBox())!.height);
  const parallel = await page.locator('[data-creator-node^="branch-"]').evaluateAll(elements => elements.map(element => element.getBoundingClientRect().top));
  expect(new Set(parallel.map(Math.round)).size).toBe(1);
  const labels = await page.locator('[data-edge-label^="branch-output-"]').evaluateAll(elements => elements.map(element => { const box = element.getBoundingClientRect(); return `${Math.round(box.x)}:${Math.round(box.y)}`; }));
  expect(new Set(labels).size).toBe(6);
  await page.getByRole("button", { name: "选择节点 风暴前的共同开场", exact: true }).click();
  await expect(inspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("风暴前的共同开场");
  if (viewport.height === 460) await expect.poll(async () => (await inspector.boundingBox())!.height).toBeGreaterThan(300);
  await page.screenshot({ path: info.outputPath("top.png") });
  for (const index of [1, 3, 6]) {
    await page.getByRole("button", { name: `选择节点 并行发展 ${index}：穿过长长的灯塔走廊`, exact: true }).click();
    await expect(inspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue(`并行发展 ${index}：穿过长长的灯塔走廊`);
    await page.screenshot({ path: info.outputPath(`parallel-${index}-viewport.png`) });
  }
  await page.mouse.move((await chart.boundingBox())!.x + 80, (await chart.boundingBox())!.y + 100);
  await page.mouse.wheel(0, 1550);
  await page.getByRole("button", { name: "选择节点 step-6", exact: true }).click();
  await expect(inspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("step-6");
  await page.screenshot({ path: info.outputPath("middle.png") });
  await page.locator('[data-edge-label="branch-output-1"]').click();
  await expect(page.getByLabel("精确选项或后续", { exact: true })).toHaveValue("branch-output-1");
  await page.getByRole("dialog", { name: "编辑精确连接" }).getByRole("button", { name: "取消", exact: true }).click();
  await page.getByRole("button", { name: "选择节点 结局 B", exact: true }).click();
  await expect(inspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("结局 B");
  const box = (await inspector.boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(50); expect(box.y + box.height).toBeLessThanOrEqual(viewport.height + 1);
  await page.screenshot({ path: info.outputPath("bottom.png") });
  await chart.hover(); await page.mouse.wheel(500, 0);
  await expect.poll(() => chart.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  const separator = page.getByRole("separator", { name: "调整节点详情宽度" });
  const before = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`));
  const textarea = inspector.getByRole("textbox", { name: "剧情摘要", exact: true }); await textarea.fill("保留未发送的节点正文与光标。");
  const body = inspector.locator(".creator-inspector-body"); await body.hover(); await page.mouse.wheel(0, 350);
  const handle = (await separator.boundingBox())!, startWidth = (await inspector.boundingBox())!.width;
  expect(startWidth).toBe(viewport.width === 1700 ? 380 : 300);
  await page.mouse.move(handle.x + handle.width / 2, handle.y + 40); await page.mouse.down(); await page.mouse.move(handle.x - 90, handle.y + 40, { steps: 8 }); await page.mouse.up();
  expect((await inspector.boundingBox())!.width).toBeGreaterThan(startWidth);
  await expect(textarea).toHaveValue("保留未发送的节点正文与光标。");
  await separator.focus(); await page.keyboard.press("Home"); expect((await inspector.boundingBox())!.width).toBeCloseTo(300, 0);
  await page.keyboard.press("Shift+ArrowLeft"); expect((await inspector.boundingBox())!.width).toBeCloseTo(350, 0);
  for (const key of ["Tab", "Escape"]) {
    await separator.focus();
    const resized = (await separator.boundingBox())!;
    await page.mouse.move(resized.x + 9, resized.y + 40); await page.mouse.down(); await page.mouse.move(resized.x - 80, resized.y + 40);
    expect((await inspector.boundingBox())!.width).toBeGreaterThan(350);
    await page.keyboard.press(key); await page.mouse.up();
    expect((await inspector.boundingBox())!.width).toBeCloseTo(350, 0);
    expect(await page.evaluate(id => JSON.parse(localStorage.getItem(`plotloom:creator-presentation:v1:${id}`)!).width, id)).toBe(350);
  }
  if (viewport.width === 1700) {
    await separator.focus(); await page.keyboard.press("End");
    expect((await inspector.boundingBox())!.width).toBeCloseTo(520, 0);
    await page.setViewportSize({ width: 1280, height: 768 });
    await expect.poll(async () => (await inspector.boundingBox())!.width).toBeLessThan(520);
    await page.setViewportSize(viewport);
    await expect.poll(async () => (await inspector.boundingBox())!.width).toBeCloseTo(520, 0);
    await separator.dblclick();
    expect((await inspector.boundingBox())!.width).toBeCloseTo(380, 0);
    await separator.focus(); await page.keyboard.press("Home"); await page.keyboard.press("Shift+ArrowLeft");
  }
  await page.getByRole("button", { name: "保存图草稿", exact: true }).click();
  const saved = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`));
  expect(saved.draft.payload.mapping.topology).toEqual(before.draft.payload.mapping.topology);
  await page.reload(); await expect(inspector).toBeVisible(); expect((await inspector.boundingBox())!.width).toBeCloseTo(350, 0);
  await expect(inspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("结局 B");
  await page.screenshot({ path: info.outputPath("resized-reopened.png") });
  await page.getByRole("button", { name: "选择节点 step-6", exact: true }).click();
  const selectedOnly = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`));
  await page.reload(); await expect(inspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("step-6");
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`))).draft.draftRevision).toBe(selectedOnly.draft.draftRevision);
  expect(failures).toEqual([]);
});
