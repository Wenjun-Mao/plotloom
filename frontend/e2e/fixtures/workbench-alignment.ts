import type { APIRequestContext, Page, TestInfo } from "@playwright/test";
import { expect, type Workbench } from "../fixture";
import { createScriptProject, json } from "../f5a-fixture";
import { demoProject } from "../../src/demo";
import { canonicalFourNodeSplit } from "./canonical-workbench";

type Journey = { page: Page; request: APIRequestContext; workbench: Workbench };
export async function actionReadUncertainty({ page, request, workbench }: Journey) {
  const id = await createScriptProject(request, workbench.apiOrigin, "shared-action-uncertainty", {}, []);
  const base = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  const save = page.getByRole("button", { name: "保存图草稿", exact: true }); await save.click(); await expect(save).toBeEnabled();
  const before = await json(request.get(`${base}/graph-workbench`));
  const switcher = page.getByRole("group", { name: "同一剧情图的两种视图" });
  for (const [endpoint, status] of [["source-outline", "来源与大纲尚未核实，请先重新读取。"], ["production-bridge", "投产状态尚未核对，暂不能应用路线。"]]) {
    const pattern = `**/api/v2/projects/${id}/${endpoint}`;
    await page.route(pattern, route => route.fulfill({ status: 503, json: { detail: "owned read failure" } }));
    await page.reload();
    for (const mode of ["创作工作台", "专业工作台"]) {
      await switcher.getByRole("button", { name: mode, exact: true }).click();
      const bar = page.getByRole("region", { name: "整张剧情图 · 保存与应用", exact: true });
      await expect(bar.locator(".graph-workflow-status")).toHaveText(status);
      await expect(bar.getByRole("button", { name: "确认图内容", exact: true })).toBeDisabled();
      await expect(bar.getByRole("button", { name: "应用到故事路线", exact: true })).toBeDisabled();
    }
    expect(await json(request.get(`${base}/graph-workbench`))).toEqual(before);
    await page.unroute(pattern); await page.reload();
    await expect(page.locator(".graph-workflow-status")).toHaveText("当前图内容已应用到故事路线。");
  }
}
export async function canonicalBriefPreview({ page, request, workbench }: Journey, info: TestInfo) {
  const graph = canonicalFourNodeSplit();
  const created = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: {
    brief: { ...demoProject.brief, title: "Canonical target preview", decisionPointsPerPath: 1, endingCount: 2, desiredJoinCount: 0 },
    initialStages: [{ stage: "story_bible", payload: demoProject.storyBible }, { stage: "story_graph", payload: graph }],
  } }));
  const base = `${workbench.apiOrigin}/api/v2/projects/${created.id}`;
  const stages = await json(request.get(`${base}/stages`)), initial = await json(request.get(`${base}/graph-workbench`));
  expect(initial.draft).toBeNull(); expect(initial.readOnlyReason).toBeTruthy();
  await page.setViewportSize({ width: 1280, height: 768 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${created.id}&stage=creator`);
  await expect(page.locator(".canonical-flow-node")).toHaveCount(4);
  await page.getByRole("button", { name: /^项目简报与创作设置/ }).click();
  await page.getByLabel("剧情节点数量上限", { exact: true }).fill("40");
  const preview = page.getByRole("dialog", { name: "确认结构目标调整" });
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  await expect(preview).toContainText("预览依据：当前已接受规范图");
  await expect(preview).toContainText("当前实际图：4 节点 · 2 结局 · 0 汇合 · 2 条完整路线");
  await page.screenshot({ path: info.outputPath("canonical-brief-preview.png") });
  await preview.getByRole("button", { name: "取消调整", exact: true }).click();
  expect((await json(request.get(base))).brief.nodeBudget).toBe(demoProject.brief.nodeBudget);
  expect(await json(request.get(`${base}/stages`))).toEqual(stages);
  expect(await json(request.get(`${base}/graph-workbench`))).toEqual(initial);
  await page.route(`**/api/v2/projects/${created.id}/graph-workbench`, route => route.fulfill({ status: 503, json: { detail: "owned graph read failure" } }));
  const failedRead = page.waitForResponse(response => response.url().endsWith(`/projects/${created.id}/graph-workbench`) && response.status() === 503);
  await page.reload(); await failedRead;
  const recover = page.getByRole("button", { name: "恢复草稿", exact: true });
  // The cancelled preview still has the ordinary Brief form draft. Wait for
  // hydration's explicit recovery surface rather than racing its publication.
  await expect(recover).toBeVisible(); await recover.click();
  await expect(page.getByRole("dialog", { name: "发现可恢复草稿" })).toHaveCount(0);
  await page.getByLabel("剧情节点数量上限", { exact: true }).fill("41");
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  await expect(preview).toContainText("预览依据：当前图尚未核实");
  await expect(preview.locator("tbody tr").first()).toHaveText(`节点上限${demoProject.brief.nodeBudget}41`);
  await expect(preview).not.toContainText("当前实际图：");
  await preview.getByRole("button", { name: "取消调整", exact: true }).click();
  expect((await json(request.get(base))).brief.nodeBudget).toBe(demoProject.brief.nodeBudget);
  await page.unroute(`**/api/v2/projects/${created.id}/graph-workbench`); await page.reload();
  await expect(recover).toBeVisible(); await recover.click();
  await expect(page.getByRole("dialog", { name: "发现可恢复草稿" })).toHaveCount(0);
  await page.getByLabel("剧情节点数量上限", { exact: true }).fill("42");
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  await expect(preview).toContainText("预览依据：当前已接受规范图");
  await preview.getByRole("button", { name: "取消调整", exact: true }).click();
  expect(await json(request.get(`${base}/stages`))).toEqual(stages);
}
export async function canonicalProNavigation(page: Page, editable = false) {
  const canvas = page.locator(editable ? ".graph-canvas" : ".canonical-graph-canvas"), transform = page.locator(".react-flow__viewport");
  for (const target of [canvas, page.locator(".react-flow__node").nth(1), page.locator(".react-flow__edge-interaction").first()]) {
    await target.scrollIntoViewIfNeeded();
    const point = await target.evaluate(element => {
      const r = element.getBoundingClientRect(), chrome = Math.max(0, ...[...document.querySelectorAll(".topbar, .recommended-workflow-guide")].map(e => e.getBoundingClientRect().bottom));
      if (element instanceof SVGGeometryElement) {
        const p = element.getPointAtLength(element.getTotalLength() / 2), screen = new DOMPoint(p.x, p.y).matrixTransform(element.getScreenCTM()!);
        return { x: screen.x, y: screen.y };
      }
      return { x: r.x + Math.min(30, r.width / 2), y: Math.max(r.top, chrome) + Math.min(30, (Math.min(r.bottom, innerHeight) - Math.max(r.top, chrome)) / 2) };
    });
    const before = await transform.getAttribute("style"), y = await page.evaluate(() => scrollY);
    await page.mouse.move(point.x, point.y); await page.mouse.wheel(0, 80);
    await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(y);
    await expect(transform).toHaveAttribute("style", before!);
  }
  const beforeControls = await transform.getAttribute("style");
  await page.getByRole("button", { name: "Zoom In", exact: true }).click();
  await expect(transform).not.toHaveAttribute("style", beforeControls!);
  await page.getByRole("button", { name: "Fit View", exact: true }).click();
  if (editable) return;
  const node = page.locator(".canonical-flow-node").first(), position = await node.getAttribute("style");
  await node.scrollIntoViewIfNeeded(); const r = (await node.boundingBox())!;
  await page.mouse.move(r.x + r.width / 2, r.y + r.height / 2); await page.mouse.down();
  await page.mouse.move(r.x + r.width / 2 + 45, r.y + r.height / 2 + 30, { steps: 4 }); await page.mouse.up();
  await expect(node).toHaveAttribute("style", position!);
  const retained = await transform.getAttribute("style");
  const switcher = page.getByRole("group", { name: "同一剧情图的两种视图" });
  await switcher.getByRole("button", { name: "创作工作台", exact: true }).click();
  await switcher.getByRole("button", { name: "专业工作台", exact: true }).click();
  await expect(transform).toHaveAttribute("style", retained!);
}

export async function longEditableLabel({ page, request, workbench }: Journey, info: TestInfo) {
  const id = await createScriptProject(request, workbench.apiOrigin, "long-editable-choice", {}, []);
  const base = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const initial = await json(request.get(`${base}/graph-workbench`));
  const mapping = initial.initialPayload.mapping;
  const choice = mapping.choices[0], section = mapping.sections.find((s: { sectionId: string }) => s.sectionId === choice.sectionId);
  const edgeId = choice.outcomes[0].outcomeId, text = "风暴逼近仍须逐字保留完整选择内容".repeat(20).slice(0, 300);
  expect(text.length).toBe(300);
  await page.setViewportSize({ width: 1700, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await page.getByRole("button", { name: `选择节点 ${section.title}`, exact: true }).click();
  await page.getByRole("textbox", { name: "选项文字", exact: true }).first().fill(text);
  await page.getByRole("button", { name: "保存图草稿", exact: true }).click();
  await expect.poll(async () => (await json(request.get(`${base}/graph-workbench`))).draft?.payload.mapping.choices[0].outcomes[0].label).toBe(text);
  const saved = await json(request.get(`${base}/graph-workbench`));
  expect(saved.draft.payload.mapping.topology).toEqual(mapping.topology);
  for (const size of [{ width: 1280, height: 460 }, { width: 1280, height: 768 }, { width: 1700, height: 900 }]) {
    await page.setViewportSize(size);
    const label = page.locator(`[data-edge-label="${edgeId}"]`);
    await expect(label).toHaveText(text); await expect(label).toHaveAccessibleName(new RegExp(text));
    const collisions = await page.locator(".creator-chart").evaluate(element => {
      const bounds = (selector: string) => [...element.querySelectorAll(selector)].map(e => e.getBoundingClientRect());
      const labels = bounds(".creator-edge-label"), nodes = bounds(".creator-node");
      const overlaps = (a: DOMRect, b: DOMRect) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
      return labels.some((label, index) => nodes.some(node => overlaps(label, node)) || labels.slice(index + 1).some(other => overlaps(label, other)));
    });
    expect(collisions).toBe(false);
    await label.focus(); for (let i = 0; i < 4; i++) await page.keyboard.press("ArrowDown");
    await expect.poll(() => label.evaluate(element => element.scrollTop)).toBeGreaterThan(0);
    await page.screenshot({ path: info.outputPath(`editable-long-label-${size.width}x${size.height}.png`) });
    await page.keyboard.press("Enter");
    await expect(page.getByLabel("精确选项或后续", { exact: true })).toHaveValue(edgeId);
    await page.getByRole("dialog", { name: "编辑精确连接" }).getByRole("button", { name: "取消", exact: true }).click();
  }
  await info.attach("editable-label-readback", { body: JSON.stringify({ id, text, mapping: saved.draft.payload.mapping }), contentType: "application/json" });
}

export async function professionalLifecycle({ page, request, workbench }: Journey, info: TestInfo) {
  const id = await createScriptProject(request, workbench.apiOrigin, "pro-lifecycle-a", {}, []);
  const other = await createScriptProject(request, workbench.apiOrigin, "pro-lifecycle-b", {}, []);
  await page.setViewportSize({ width: 1700, height: 900 });
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=graph`);
  const save = page.getByRole("button", { name: "保存图草稿", exact: true }); await save.click(); await expect(save).toBeEnabled();
  const base = `${workbench.apiOrigin}/api/v2/projects/${id}`;
  const before = await json(request.get(`${base}/graph-workbench`)), stages = await json(request.get(`${base}/stages`));
  const writes: string[] = [];
  page.on("request", r => { if (new URL(r.url()).pathname.startsWith(`/api/v2/projects/${id}`) && !["GET", "HEAD", "OPTIONS"].includes(r.method())) writes.push(`${r.method()} ${new URL(r.url()).pathname}`); });
  const transform = page.locator(".react-flow__viewport");
  await expect(page.locator(".react-flow__node")).toHaveCount(4);
  const first = page.locator(".react-flow__node").first();
  const initialPosition = await first.getAttribute("style");
  await first.scrollIntoViewIfNeeded(); const box = (await first.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2); await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 60, box.y + box.height / 2 + 45, { steps: 5 }); await page.mouse.up();
  await expect(first).not.toHaveAttribute("style", initialPosition!);
  const position = await first.getAttribute("style");
  await page.getByRole("button", { name: "Zoom In", exact: true }).click();
  const visual = await transform.getAttribute("style");
  const switcher = page.getByRole("group", { name: "同一剧情图的两种视图" });
  await switcher.getByRole("button", { name: "创作工作台", exact: true }).click();
  await switcher.getByRole("button", { name: "专业工作台", exact: true }).click();
  await expect(first).toHaveAttribute("style", position!); await expect(transform).toHaveAttribute("style", visual!);
  expect(await json(request.get(`${base}/graph-workbench`))).toEqual(before); expect(await json(request.get(`${base}/stages`))).toEqual(stages); expect(writes).toEqual([]);
  await page.screenshot({ path: info.outputPath("pro-node-position-retained.png") });
  await info.attach("pro-position-readback", { body: JSON.stringify({ id, other, initialPosition, position, visual, before, stages, writes }), contentType: "application/json" });
  const open = async (project: string) => {
    await page.getByRole("button", { name: /^当前项目 · 切换/ }).click();
    await page.locator(`[data-project-id="${project}"] .directory-open`).click();
    await switcher.getByRole("button", { name: "专业工作台", exact: true }).click();
    await expect(page.locator(".react-flow__node")).toHaveCount(4);
  };
  await open(other); await open(id);
  await expect(first).toHaveAttribute("style", initialPosition!); await expect(transform).not.toHaveAttribute("style", visual!);
  await page.getByRole("button", { name: "Zoom In", exact: true }).click();
  const zoomed = await transform.getAttribute("style"); await page.reload();
  await expect(first).toHaveAttribute("style", initialPosition!); await expect(transform).not.toHaveAttribute("style", zoomed!);
  await page.getByRole("button", { name: "Zoom In", exact: true }).click();
  const beforeClose = await transform.getAttribute("style");
  await page.getByRole("button", { name: /^当前项目 · 切换/ }).click();
  const row = page.locator(`[data-project-id="${id}"]`);
  await row.getByRole("button", { name: "保存并关闭项目", exact: true }).click();
  await row.getByRole("button", { name: "重新打开", exact: true }).click();
  await switcher.getByRole("button", { name: "专业工作台", exact: true }).click();
  await expect(first).toHaveAttribute("style", initialPosition!);
  await expect(transform).not.toHaveAttribute("style", beforeClose!);
}
