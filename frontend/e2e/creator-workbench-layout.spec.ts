import { expect, test, checkedStaticTest } from "./fixture";
import { createCreatorGraph } from "./fixtures/creator-graph";
import { json } from "./f5a-fixture";
import { demoProject } from "../src/demo";
import { footageModeLabels, storyNodeKindLabels } from "../src/features/graph/presentation";
import type { StoryGraph } from "../src/types";

function canonicalFourNodeSplit(): StoryGraph {
  return {
    startNodeId: "start",
    nodes: [
      { id: "start", title: "共同开场", kind: "start", summary: "灯塔的值守夜。", footageMode: "footage" },
      { id: "decision", title: "选择照明方向", kind: "decision", summary: "海雾正向港湾推进。", footageMode: "route_only" },
      { id: "sea-ending", title: "继续照向海面", kind: "ending", summary: "航道上的船只看见信标。", footageMode: "footage" },
      { id: "shore-ending", title: "照亮岸边石阶", kind: "ending", summary: "岸边的人们沿石阶撤离。", footageMode: "footage" },
    ],
    edges: [
      { id: "start-decision", sourceNodeId: "start", targetNodeId: "decision", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      { id: "decision-sea", sourceNodeId: "decision", targetNodeId: "sea-ending", kind: "choice", choiceText: "继续照向海面", stateEffects: { harbor_signal: "visible" }, entityStateEffects: [{ entityType: "location", entityId: "loc_control", state: "active" }] },
      { id: "decision-shore", sourceNodeId: "decision", targetNodeId: "shore-ending", kind: "choice", choiceText: "照亮岸边石阶", stateEffects: {}, entityStateEffects: [] },
    ],
    joinContracts: [],
  };
}

function canonicalJoinGraph(longChoice: string): StoryGraph {
  return {
    startNodeId: "start",
    nodes: [
      { id: "start", title: "共同开场", kind: "start", summary: "灯塔的值守夜。", footageMode: "footage" },
      { id: "decision", title: "选择航标路线", kind: "decision", summary: "海雾正向港湾推进。", footageMode: "route_only" },
      { id: "west", title: "检查西侧航标", kind: "scene", summary: "西侧信号仍可读取。", footageMode: "footage" },
      { id: "east", title: "检查东侧航标", kind: "scene", summary: "东侧通道仍可进入。", footageMode: "footage" },
      { id: "join", title: "回到值守台", kind: "join", summary: "两条侧廊在此汇合。", footageMode: "route_only" },
      { id: "ending", title: "信标恢复", kind: "ending", summary: "港湾重新看见信标。", footageMode: "footage" },
    ],
    edges: [
      { id: "start-decision", sourceNodeId: "start", targetNodeId: "decision", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      { id: "decision-west", sourceNodeId: "decision", targetNodeId: "west", kind: "choice", choiceText: "检查西侧航标", stateEffects: {}, entityStateEffects: [] },
      { id: "decision-east", sourceNodeId: "decision", targetNodeId: "east", kind: "choice", choiceText: "检查东侧航标", stateEffects: {}, entityStateEffects: [] },
      { id: "decision-skip", sourceNodeId: "decision", targetNodeId: "join", kind: "choice", choiceText: longChoice, stateEffects: {}, entityStateEffects: [] },
      { id: "west-join", sourceNodeId: "west", targetNodeId: "join", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      { id: "east-join", sourceNodeId: "east", targetNodeId: "join", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      { id: "join-ending", sourceNodeId: "join", targetNodeId: "ending", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
    ],
    joinContracts: [{ id: "join-contract", joinNodeId: "join", incomingNodeIds: ["decision", "west", "east"], requiredStateKeys: [], allowedDifferences: [], reconciliation: "各路线回到值守台后继续。", notes: "路线选择保留在连接效果中。" }],
  };
}

const canonicalViewports = [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }];
const longChoiceText = "风暴逼近时，先检查备用电源和两侧航标，再回到值守台核对海面信号后决定下一步。".repeat(5);
const canonicalScenarios = [
  {
    id: "four-node-split",
    graph: canonicalFourNodeSplit(),
    brief: { decisionPointsPerPath: 1, endingCount: 2, desiredJoinCount: 0, nodeBudget: 4, maxOutDegree: 2 },
    choiceLabels: [{ id: "decision-sea", text: "继续照向海面" }, { id: "decision-shore", text: "照亮岸边石阶" }],
  },
  {
    id: "join-long-skip",
    graph: canonicalJoinGraph(longChoiceText),
    brief: { decisionPointsPerPath: 1, endingCount: 1, desiredJoinCount: 1, nodeBudget: 6, maxOutDegree: 3 },
    choiceLabels: [
      { id: "decision-west", text: "检查西侧航标" },
      { id: "decision-east", text: "检查东侧航标" },
      { id: "decision-skip", text: longChoiceText },
    ],
    longChoiceEdgeId: "decision-skip",
  },
];

for (const scenario of canonicalScenarios) for (const viewport of canonicalViewports) checkedStaticTest(`canonical read-only ${scenario.id} labels ${viewport.width}x${viewport.height}`, async ({ page, request, workbench }, info) => {
  await page.setViewportSize(viewport);
  const graph = scenario.graph;
  const created = await json(request.post(`${workbench.apiOrigin}/api/v2/projects`, { data: {
    brief: { ...demoProject.brief, ...scenario.brief, title: `Canonical ${scenario.id} fixture ${viewport.width}x${viewport.height}` },
    initialStages: [{ stage: "story_bible", payload: demoProject.storyBible }, { stage: "story_graph", payload: graph }],
  } }));
  const id = created.id as string;
  const stagesUrl = `${workbench.apiOrigin}/api/v2/projects/${id}/stages`;
  const graphWorkbenchUrl = `${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`;
  let expectedCreatorSelection = graph.startNodeId;
  const beforeStages = await json(request.get(stagesUrl));
  const beforeWorkbench = await json(request.get(graphWorkbenchUrl));
  expect(beforeWorkbench.readOnlyReason).toBeTruthy();
  const writes: string[] = [];
  page.on("request", browserRequest => {
    const url = new URL(browserRequest.url());
    if (url.pathname.startsWith(`/api/v2/projects/${id}`) && !["GET", "HEAD", "OPTIONS"].includes(browserRequest.method())) writes.push(`${browserRequest.method()} ${url.pathname}`);
  });

  for (const mode of ["creator", "graph"]) {
    const readerUrl = `${workbench.frontendOrigin}/v2/?project=${id}&stage=${mode}`;
    await page.goto(readerUrl);
    for (const reload of [false, true]) {
      if (reload) await page.reload();
      let creatorInspector = page.getByRole("complementary", { name: "当前节点详情" });
      if (mode === "creator") {
        await expect(page.locator(".creator-canonical-workbench")).toBeVisible();
        await expect(page.getByRole("heading", { name: "创作工作台", exact: true })).toBeVisible();
        await expect(page.locator(".canonical-graph-reader")).toHaveCount(0);
        await expect(creatorInspector).toBeVisible();
        const expectedNode = graph.nodes.find(node => node.id === expectedCreatorSelection)!;
        await expect(creatorInspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue(expectedNode.title);
        await expect(creatorInspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveAttribute("readonly", "");
        await expect(creatorInspector.getByRole("textbox", { name: "节点类型", exact: true })).toHaveValue(storyNodeKindLabels[expectedNode.kind]);
        await expect(creatorInspector.getByRole("textbox", { name: "画面模式", exact: true })).toHaveValue(footageModeLabels[expectedNode.footageMode]);
        const panel = (await creatorInspector.boundingBox())!, chart = (await page.locator(".canonical-graph-scroll").boundingBox())!;
        expect(panel.x).toBeGreaterThanOrEqual(chart.x + chart.width);
        expect(panel.width).toBeGreaterThanOrEqual(300); expect(panel.width).toBeLessThanOrEqual(520);
        expect(panel.x + panel.width).toBeLessThanOrEqual(viewport.width + 1);
        const chromeBottom = await page.evaluate(() => Math.max(0, ...[...document.querySelectorAll(".topbar, .recommended-workflow-guide")].map(header => header.getBoundingClientRect().bottom)));
        expect(panel.y).toBeGreaterThanOrEqual(chromeBottom - 1);
        expect(panel.y + panel.height).toBeLessThanOrEqual(viewport.height + 1);
        expect(panel.height).toBeLessThanOrEqual(viewport.height * .85 + 1);
      } else {
        const reader = page.locator(".canonical-graph-reader");
        await expect(reader).toBeVisible();
        await expect(reader).toContainText(`已接受路线 · ${graph.nodes.length} 个节点 · ${graph.edges.length} 条连接`);
      }
      await expect(page.getByRole("button", { name: "保存图草稿", exact: true })).toHaveCount(0);
      const labels = page.locator(".canonical-edge-label");
      await expect(labels).toHaveCount(graph.edges.length);
      for (const choice of scenario.choiceLabels) await expect(page.locator(`[data-edge-label="${choice.id}"]`)).toHaveText(choice.text);
      const geometry = await page.evaluate(() => {
        const canvas = document.querySelector<HTMLElement>(".canonical-graph-canvas")!;
        const scroll = document.querySelector<HTMLElement>(".canonical-graph-scroll")!;
        const canvasRect = canvas.getBoundingClientRect();
        const nodes = [...document.querySelectorAll<HTMLElement>(".canonical-flow-node")].map(element => {
          const rect = element.getBoundingClientRect();
          return { x: rect.x, y: rect.y, right: rect.right, bottom: rect.bottom };
        });
        const labels = [...document.querySelectorAll<HTMLElement>(".canonical-edge-label")].map(element => {
          const rect = element.getBoundingClientRect();
          return { x: rect.x, y: rect.y, right: rect.right, bottom: rect.bottom, visible: getComputedStyle(element).visibility === "visible" };
        });
        const intersects = (left: { x: number; y: number; right: number; bottom: number }, right: { x: number; y: number; right: number; bottom: number }) => left.x < right.right && left.right > right.x && left.y < right.bottom && left.bottom > right.y;
        const labelsWithinGraph = labels.every(label => label.x >= canvasRect.left - 1 && label.right <= canvasRect.right + 1 && label.y >= canvasRect.top - 1 && label.bottom <= canvasRect.bottom + 1);
        const probe = document.createElement("span");
        probe.style.backgroundColor = "var(--xy-edge-label-background-color)";
        probe.style.color = "var(--accent)";
        canvas.append(probe);
        const themeBackground = getComputedStyle(probe).backgroundColor, themeChoice = getComputedStyle(probe).color;
        probe.remove();
        const choiceLabel = document.querySelector<HTMLElement>(".canonical-edge-label.choice")!;
        return { canvasHeight: canvasRect.height, scrollWidth: scroll.scrollWidth, clientWidth: scroll.clientWidth,
          themeBackground, themeChoice, choiceColor: getComputedStyle(choiceLabel).color,
          labelBackgrounds: [...document.querySelectorAll<HTMLElement>(".canonical-edge-label")].map(label => getComputedStyle(label).backgroundColor),
          labels, labelsWithinGraph,
          labelNodeOverlaps: labels.some(label => nodes.some(node => intersects(label, node))),
          labelLabelOverlaps: labels.some((label, index) => labels.slice(index + 1).some(other => intersects(label, other))),
          hasHorizontalOverflow: scroll.scrollWidth > scroll.clientWidth };
      });
      expect(geometry.canvasHeight).toBeGreaterThan(440);
      expect(geometry.scrollWidth).toBeGreaterThanOrEqual(geometry.clientWidth);
      expect(geometry.labelBackgrounds.every(background => background === geometry.themeBackground)).toBe(true);
      expect(geometry.choiceColor).toBe(geometry.themeChoice);
      expect(geometry.labels.every(label => label.visible)).toBe(true);
      expect(geometry.labelsWithinGraph).toBe(true);
      expect(geometry.labelNodeOverlaps).toBe(false);
      expect(geometry.labelLabelOverlaps).toBe(false);
      if (scenario.longChoiceEdgeId) {
        const longLabel = page.locator(`[data-edge-label="${scenario.longChoiceEdgeId}"]`);
        await expect(longLabel).toHaveAttribute("role", "note");
        await expect(longLabel).toHaveAttribute("tabindex", "0");
        await expect(longLabel).toHaveText(longChoiceText);
        const scrollCapacity = await longLabel.evaluate(element => element.scrollHeight - element.clientHeight);
        expect(scrollCapacity).toBeGreaterThan(0);
        await longLabel.focus();
        for (let key = 0; key < 4; key++) await page.keyboard.press("ArrowDown");
        await expect.poll(() => longLabel.evaluate(element => element.scrollTop)).toBeGreaterThan(0);
      }
      await page.screenshot({ path: info.outputPath(`${scenario.id}-${mode}-${viewport.width}x${viewport.height}-${reload ? "reload" : "initial"}.png`) });
      if (geometry.hasHorizontalOverflow) {
        const scroll = page.locator(".canonical-graph-scroll");
        await scroll.evaluate(element => { element.scrollLeft = element.scrollWidth; });
        await expect.poll(() => scroll.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
        await scroll.evaluate(element => { element.scrollLeft = 0; });
      }
      if (scenario.id === "four-node-split" && viewport.width === 1280 && viewport.height === 768 && mode === "creator" && !reload) {
        const title = creatorInspector.getByRole("textbox", { name: "章节标题", exact: true });
        await page.locator('.canonical-flow-node[data-id="sea-ending"]').click();
        await expect(title).toHaveValue("继续照向海面");
        await expect(creatorInspector.getByRole("textbox", { name: "剧情摘要", exact: true })).toHaveValue("航道上的船只看见信标。");
        await expect(creatorInspector.getByRole("textbox", { name: "选项文字", exact: true })).toHaveValue("继续照向海面");
        await expect(creatorInspector.getByRole("textbox", { name: "状态效果", exact: true })).toHaveValue("harbor_signal：visible\nlocation · loc_control：active");
        const keyboardNode = page.locator('.canonical-flow-node[data-id="shore-ending"]');
        await keyboardNode.focus(); await page.keyboard.press("Enter");
        await expect(title).toHaveValue("照亮岸边石阶");
        expectedCreatorSelection = "shore-ending";

        const chartScroll = page.locator(".canonical-graph-scroll");
        await chartScroll.evaluate(element => element.scrollIntoView({ block: "center" }));
        const scrollBeforeWheel = await page.evaluate(() => window.scrollY);
        const viewportBeforeWheel = await page.locator(".canonical-graph-flow .react-flow__viewport").getAttribute("style");
        const wheelRect = (await chartScroll.boundingBox())!;
        await page.mouse.move(wheelRect.x + Math.min(80, wheelRect.width / 2), wheelRect.y + wheelRect.height / 2);
        await page.mouse.wheel(0, 240);
        await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(scrollBeforeWheel);
        expect(await page.locator(".canonical-graph-flow .react-flow__viewport").getAttribute("style")).toBe(viewportBeforeWheel);

        await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=graph`);
        await expect(page.locator(".canonical-graph-reader")).toBeVisible();
        await page.goto(readerUrl);
        creatorInspector = page.getByRole("complementary", { name: "当前节点详情" });
        await expect(creatorInspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("照亮岸边石阶");
        await page.reload();
        creatorInspector = page.getByRole("complementary", { name: "当前节点详情" });
        await expect(creatorInspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("照亮岸边石阶");
        await page.evaluate(projectId => localStorage.setItem(`plotloom:graph-selection:v1:${projectId}`, JSON.stringify("removed-node")), id);
        await page.reload();
        creatorInspector = page.getByRole("complementary", { name: "当前节点详情" });
        await expect(creatorInspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("共同开场");
        expectedCreatorSelection = graph.startNodeId;

        const separator = page.getByRole("separator", { name: "调整节点详情宽度" });
        const initialWidth = (await creatorInspector.boundingBox())!.width;
        await separator.focus(); await page.keyboard.press("ArrowLeft");
        const keyboardWidth = (await creatorInspector.boundingBox())!.width;
        expect(keyboardWidth).toBeGreaterThan(initialWidth);
        const handle = (await separator.boundingBox())!;
        await page.mouse.move(handle.x + handle.width / 2, handle.y + 40); await page.mouse.down();
        await page.mouse.move(handle.x - 35, handle.y + 40, { steps: 4 });
        expect((await creatorInspector.boundingBox())!.width).toBeGreaterThan(keyboardWidth);
        await page.keyboard.press("Escape"); await page.mouse.up();
        expect((await creatorInspector.boundingBox())!.width).toBeCloseTo(keyboardWidth, 0);
        expect(await page.evaluate(projectId => JSON.parse(localStorage.getItem(`plotloom:creator-presentation:v1:${projectId}`)!).width, id)).toBe(keyboardWidth);
      }
      if (scenario.id === "join-long-skip" && viewport.width === 1280 && viewport.height === 768 && mode === "creator" && !reload) {
        await page.locator('.canonical-flow-node[data-id="join"]').click();
        await expect(creatorInspector.getByRole("textbox", { name: "汇合衔接", exact: true })).toHaveValue("各路线回到值守台后继续。");
        await expect(creatorInspector.getByRole("textbox", { name: "合同备注", exact: true })).toHaveValue("路线选择保留在连接效果中。");
        await expect(creatorInspector.getByRole("textbox", { name: "输入节点", exact: true })).toHaveValue("选择航标路线\n检查西侧航标\n检查东侧航标");
        await page.locator('.canonical-flow-node[data-id="decision"]').click();
        await expect(creatorInspector.getByRole("textbox", { name: "选项文字", exact: true }).nth(2)).toHaveValue(longChoiceText);
        const chartScroll = page.locator(".canonical-graph-scroll");
        await chartScroll.evaluate(element => { element.scrollLeft = element.scrollWidth; });
        await expect.poll(() => chartScroll.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
        const savedChartX = await chartScroll.evaluate(element => element.scrollLeft);
        expectedCreatorSelection = "decision";
        await page.reload();
        creatorInspector = page.getByRole("complementary", { name: "当前节点详情" });
        await expect(creatorInspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("选择航标路线");
        await expect(creatorInspector.getByRole("textbox", { name: "节点类型", exact: true })).toHaveValue(storyNodeKindLabels.decision);
        await expect(creatorInspector.getByRole("textbox", { name: "画面模式", exact: true })).toHaveValue(footageModeLabels.route_only);
        await expect(creatorInspector.getByRole("textbox", { name: "选项文字", exact: true }).nth(2)).toHaveValue(longChoiceText);
        await expect.poll(() => page.locator(".canonical-graph-scroll").evaluate(element => element.scrollLeft)).toBe(savedChartX);
      }
      if (scenario.id === "join-long-skip" && viewport.width === 1280 && viewport.height === 768 && mode === "graph" && !reload) {
        const graphCanvas = page.locator(".canonical-graph-canvas");
        // Focusing a lower label scrolls the page; interact with the visible
        // canvas below sticky chrome, not its now-offscreen document origin.
        const interaction = await graphCanvas.evaluate(element => {
          const rect = element.getBoundingClientRect();
          const chromeBottom = Math.max(0, ...[...document.querySelectorAll(".topbar, .recommended-workflow-guide")].map(header => header.getBoundingClientRect().bottom));
          const top = Math.max(rect.top, chromeBottom), bottom = Math.min(rect.bottom, innerHeight);
          const left = Math.max(rect.left, 0), right = Math.min(rect.right, innerWidth);
          return { x: left + 42, y: top + 40, visibleWidth: right - left, visibleHeight: bottom - top };
        });
        expect(interaction.visibleWidth).toBeGreaterThan(120);
        expect(interaction.visibleHeight).toBeGreaterThan(200);
        const readAlignment = () => page.evaluate(() => {
          const viewport = document.querySelector<HTMLElement>(".canonical-graph-flow .react-flow__viewport")!;
          const matrix = new DOMMatrixReadOnly(getComputedStyle(viewport).transform);
          const rect = (selector: string) => document.querySelector<HTMLElement>(selector)!.getBoundingClientRect();
          const node = rect('.canonical-flow-node[data-id="ending"]');
          const label = rect('[data-edge-label="decision-skip"]');
          return {
            scale: matrix.a, translateX: matrix.e, translateY: matrix.f,
            nodeX: node.left + node.width / 2, nodeY: node.top + node.height / 2,
            labelX: label.left + label.width / 2, labelY: label.top + label.height / 2,
          };
        });
        const beforePan = await readAlignment();
        await page.mouse.move(interaction.x, interaction.y);
        await page.mouse.down();
        await page.mouse.move(interaction.x + 42, interaction.y + 28, { steps: 5 });
        await page.mouse.up();
        await expect.poll(async () => (await readAlignment()).translateX).not.toBe(beforePan.translateX);
        const afterPan = await readAlignment();
        expect(afterPan.scale).toBeCloseTo(beforePan.scale, 2);
        expect(Math.abs((afterPan.nodeX - beforePan.nodeX) - (afterPan.translateX - beforePan.translateX))).toBeLessThan(2);
        expect(Math.abs((afterPan.nodeY - beforePan.nodeY) - (afterPan.translateY - beforePan.translateY))).toBeLessThan(2);
        expect(Math.abs((afterPan.labelX - beforePan.labelX) - (afterPan.translateX - beforePan.translateX))).toBeLessThan(2);
        expect(Math.abs((afterPan.labelY - beforePan.labelY) - (afterPan.translateY - beforePan.translateY))).toBeLessThan(2);
        await page.mouse.move(interaction.x + 40, interaction.y + 120);
        await page.mouse.wheel(0, -120);
        await expect.poll(async () => (await readAlignment()).scale).toBeGreaterThan(afterPan.scale);
        const afterZoom = await readAlignment();
        const zoomRatio = afterZoom.scale / afterPan.scale;
        expect(Math.abs((afterZoom.labelX - afterZoom.nodeX) - (afterPan.labelX - afterPan.nodeX) * zoomRatio)).toBeLessThan(3);
        expect(Math.abs((afterZoom.labelY - afterZoom.nodeY) - (afterPan.labelY - afterPan.nodeY) * zoomRatio)).toBeLessThan(3);
        await page.screenshot({ path: info.outputPath(`${scenario.id}-${mode}-${viewport.width}x${viewport.height}-pan-wheel.png`) });
      }
    }
  }

  const afterStages = await json(request.get(stagesUrl));
  const afterWorkbench = await json(request.get(graphWorkbenchUrl));
  expect(afterStages.stages).toEqual(beforeStages.stages);
  expect(afterWorkbench).toEqual(beforeWorkbench);
  expect(afterWorkbench.draft).toEqual(beforeWorkbench.draft);
  expect(afterWorkbench.initialPayload).toEqual(beforeWorkbench.initialPayload);
  expect(writes).toEqual([]);
});

for (const viewport of [{ width: 1280, height: 768 }, { width: 1280, height: 460 }, { width: 1700, height: 900 }]) test(`creator desktop rows and tall inspector ${viewport.width}x${viewport.height}`, async ({ page, request, workbench }, info) => {
  await page.setViewportSize(viewport);
  const failures: string[] = []; page.on("pageerror", error => failures.push(error.message));
  const id = await createCreatorGraph(request, workbench.apiOrigin, `${viewport.width}-${viewport.height}`, 6, 12);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  await expect(page.getByRole("heading", { name: "创作工作台", exact: true })).toBeVisible();
  const chart = page.getByLabel("剧情图横向平移", { exact: true }), inspector = page.getByRole("complementary", { name: "当前节点详情" });
  await expect(page.locator("[data-creator-node]")).toHaveCount(24);
  const rowAdd = page.getByRole("button", { name: "向第 1 行添加节点", exact: true });
  const rowAddPresentation = await rowAdd.evaluate(element => {
    const buttonStyle = getComputedStyle(element), icon = element.querySelector<HTMLElement>(".creator-row-add-icon")!;
    const before = getComputedStyle(icon, "::before"), after = getComputedStyle(icon, "::after");
    return {
      button: { width: element.getBoundingClientRect().width, height: element.getBoundingClientRect().height, padding: buttonStyle.padding, placeItems: buttonStyle.placeItems },
      icon: { hidden: icon.getAttribute("aria-hidden"), width: getComputedStyle(icon).width, height: getComputedStyle(icon).height, placeItems: getComputedStyle(icon).placeItems },
      bars: [[before.width, before.height, before.gridRowStart, before.gridColumnStart], [after.width, after.height, after.gridRowStart, after.gridColumnStart]],
    };
  });
  expect(rowAddPresentation).toEqual({ button: { width: 30, height: 30, padding: "0px", placeItems: "center" }, icon: { hidden: "true", width: "12px", height: "12px", placeItems: "center" }, bars: [["12px", "2px", "1", "1"], ["2px", "12px", "1", "1"]] });
  const metrics = await chart.evaluate(element => ({ scroll: element.scrollWidth > element.clientWidth, height: element.scrollHeight, outer: (element as HTMLElement).offsetHeight, vertical: getComputedStyle(element).overflowY }));
  expect(metrics.scroll).toBe(true); expect(metrics.vertical).toBe("hidden"); expect(metrics.height, JSON.stringify(metrics)).toBeLessThanOrEqual(metrics.outer + 1);
  expect((await page.locator(".creator-row-insert").last().boundingBox())!.y + (await page.locator(".creator-row-insert").last().boundingBox())!.height).toBeLessThanOrEqual((await chart.boundingBox())!.y + (await chart.boundingBox())!.height);
  const parallel = await page.locator('[data-creator-node^="branch-"]').evaluateAll(elements => elements.map(element => element.getBoundingClientRect().top));
  expect(new Set(parallel.map(Math.round)).size).toBe(1);
  const labels = await page.locator('[data-edge-label^="branch-output-"]').evaluateAll(elements => elements.map(element => { const box = element.getBoundingClientRect(); return `${Math.round(box.x)}:${Math.round(box.y)}`; }));
  expect(new Set(labels).size).toBe(6);
  await page.getByRole("button", { name: "选择节点 风暴前的共同开场", exact: true }).click();
  await expect(inspector.getByRole("textbox", { name: "章节标题", exact: true })).toHaveValue("风暴前的共同开场");
  if (viewport.height === 460) {
    const available = await page.locator(".creator-layout").evaluate(element => {
      const rect = element.getBoundingClientRect();
      const chrome = Math.max(0, ...[...document.querySelectorAll(".topbar, .recommended-workflow-guide")].map(header => header.getBoundingClientRect().bottom));
      return Math.min(Math.min(rect.bottom - 8, innerHeight - 8) - Math.max(rect.top + 8, chrome + 8), innerHeight * .85);
    });
    await expect.poll(async () => (await inspector.boundingBox())!.height).toBeCloseTo(available, 0);
  }
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
  const workspaceTop = await page.evaluate(() => Math.max(0, ...[...document.querySelectorAll(".topbar, .recommended-workflow-guide")].map(header => header.getBoundingClientRect().bottom)));
  expect(box.y).toBeGreaterThanOrEqual(workspaceTop); expect(box.y + box.height).toBeLessThanOrEqual(viewport.height + 1);
  await page.screenshot({ path: info.outputPath("bottom.png") });
  const guide = page.getByTestId("recommended-workflow");
  await guide.getByText("查看六步状态", { exact: true }).click();
  await expect.poll(async () => {
    const expanded = (await guide.boundingBox())!, panel = (await inspector.boundingBox())!;
    return panel.y >= expanded.y + expanded.height && panel.y + panel.height <= viewport.height + 1;
  }).toBe(true);
  await page.screenshot({ path: info.outputPath("expanded-guide-inspector.png") });
  await guide.getByText("查看六步状态", { exact: true }).click();
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
