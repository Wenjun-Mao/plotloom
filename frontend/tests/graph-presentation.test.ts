import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { GraphNodeDetails } from "../src/features/graph/GraphNodeDetails";
import { SourceStructureEditor } from "../src/pages/SourceStructureEditor";
import { CanonicalGraphReader } from "../src/features/graph/CanonicalGraphReader";
import { CanonicalGraphCanvas } from "../src/features/graph/CanonicalGraphCanvas";
import { CreatorCanonicalStoryInspector } from "../src/features/graph/CreatorCanonicalStoryInspector";
import { creatorCanonicalSelectionGeometry } from "../src/features/graph/CreatorCanonicalWorkbench";
import { GraphWorkbenchContext, type GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import { graphControllerFixture, graphDraftFixture } from "./graph-workbench-fixture";
import type { StoryGraph } from "../src/types";
import { creativeWorkflowStepReference } from "../src/creative-workflow-steps";

const flowMock = vi.hoisted(() => vi.fn((_props: Record<string, unknown>) => null));
vi.mock("@xyflow/react", () => ({ ReactFlow: flowMock, Controls: () => null, BaseEdge: () => null, EdgeLabelRenderer: () => null,
  MarkerType: { ArrowClosed: "closed" }, Position: { Bottom: "bottom", Top: "top" } }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root, owner: GraphWorkbenchController;
const kinds = ["start", "scene", "decision", "join", "ending"] as const;
const labels = ["开场", "故事发展", "选择点", "汇合点", "结局"];

beforeEach(() => {
  flowMock.mockClear();
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  const draft = graphDraftFixture();
  draft.mapping.topology.nodes = kinds.map(kind => ({ id: kind, kind }));
  draft.mapping.topology.startNodeId = "start";
  draft.mapping.sections = kinds.map((kind, index) => ({ sectionId: kind, title: labels[index], summary: "剧情", ending: kind === "ending", footageMode: kind === "decision" || kind === "join" ? "route_only" : "footage" }));
  draft.mapping.topology.edges = [{ id: "start-scene", sourceNodeId: "start", targetNodeId: "scene", kind: "continuation", stateEffects: {}, entityStateEffects: [] }];
  owner = graphControllerFixture({ draft, selectedNodeId: "scene" });
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

it("uses Chinese node-type and endpoint labels while retaining exact enum commands", async () => {
  await act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: owner, children: createElement(GraphNodeDetails, { disabled: false }) })));
  const type = [...host.querySelectorAll("select")].find(select => [...select.options].map(option => option.textContent).join("|") === labels.join("|"))!;
  expect([...type.options].map(option => option.value)).toEqual(kinds);
  for (const endpoint of host.querySelectorAll<HTMLSelectElement>(".graph-edge-detail select")) {
    expect([...endpoint.options].slice(1).map(option => option.textContent)).toEqual(labels.map(label => `${label} · ${label}`));
    expect([...endpoint.options].slice(1).map(option => option.value)).toEqual(kinds);
  }
  await act(async () => { type.value = "decision"; type.dispatchEvent(new Event("change", { bubbles: true })); });
  expect(owner.prepareCommand).toHaveBeenCalledWith({ operation: "set_kind", nodeId: "scene", kind: "decision", footageMode: "footage" });
});

it("uses the same labels for accepted read-only nodes and footage modes", async () => {
  const value: StoryGraph = { startNodeId: "start", nodes: owner.draft!.mapping.topology.nodes.map(node => {
    const section = owner.draft!.mapping.sections.find(section => section.sectionId === node.id)!;
    return { ...node, title: section.title, summary: section.summary, footageMode: section.footageMode };
  }), edges: [], joinContracts: [] };
  await act(async () => root.render(createElement(CanonicalGraphReader, { value })));
  expect([...host.querySelectorAll("details section > strong")].map(element => element.textContent)).toEqual(kinds.map((kind, index) => `${kind} · ${labels[index]} · ${kind === "decision" || kind === "join" ? "仅路线控制点" : "包含画面"}`));
});

it("renders canonical choices through shared ranks and reserved lanes without changing the accepted graph", async () => {
  const value: StoryGraph = {
    startNodeId: "start",
    nodes: [
      { id: "join", title: "汇合与重读", kind: "join", summary: "两条路线在此相遇。", footageMode: "route_only" },
      { id: "west", title: "西侧航标", kind: "scene", summary: "沿西侧通道前进。", footageMode: "footage" },
      { id: "start", title: "灯塔的抉择", kind: "decision", summary: "风暴迫近，值守人必须决定。", footageMode: "route_only" },
      { id: "east", title: "东侧航标", kind: "scene", summary: "沿东侧通道前进。", footageMode: "footage" },
    ],
    edges: [
      { id: "direct-skip", sourceNodeId: "start", targetNodeId: "join", kind: "choice", choiceText: "直接启用备用信标，暂时绕过两条侧廊，再回到汇合处。", stateEffects: {}, entityStateEffects: [] },
      { id: "east-join", sourceNodeId: "east", targetNodeId: "join", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      { id: "start-west", sourceNodeId: "start", targetNodeId: "west", kind: "choice", choiceText: "检查西侧航标", stateEffects: {}, entityStateEffects: [] },
      { id: "west-join", sourceNodeId: "west", targetNodeId: "join", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      { id: "start-east", sourceNodeId: "start", targetNodeId: "east", kind: "choice", choiceText: "检查东侧航标", stateEffects: {}, entityStateEffects: [] },
    ],
    joinContracts: [],
  };
  const original = structuredClone(value);
  await act(async () => root.render(createElement(CanonicalGraphReader, { value })));
  const props = flowMock.mock.calls.at(-1)?.[0] as { [key: string]: unknown; nodes: Array<Record<string, any>>; edges: Array<Record<string, any>>; fitViewOptions: unknown; nodesDraggable: boolean; nodesConnectable: boolean; edgesReconnectable: boolean; elementsSelectable: boolean };
  expect(props.nodes.map(node => node.id)).toEqual(value.nodes.map(node => node.id));
  expect(props.nodes.find(node => node.id === "start")).toMatchObject({ position: { y: 32 }, sourcePosition: "bottom", targetPosition: "top", width: 194, height: 112 });
  expect(props.nodes.filter(node => ["west", "east"].includes(node.id)).map(node => node.position.y)).toEqual([288, 288]);
  expect(props.nodes.find(node => node.id === "join")?.position.y).toBe(544);
  expect(props.edges.map(edge => edge.id)).toEqual(value.edges.map(edge => edge.id));
  expect(props.edges.find(edge => edge.id === "direct-skip")?.data).toMatchObject({ label: value.edges[0].choiceText, kind: "choice" });
  expect(props.edges.find(edge => edge.id === "direct-skip")?.data.path).toContain(" L ");
  const joinLanes = props.edges.filter(edge => edge.target === "join").map(edge => edge.data.labelX).sort((a: number, b: number) => a - b);
  expect(joinLanes).toHaveLength(3);
  expect(new Set(joinLanes).size).toBe(3);
  expect(props).toMatchObject({ nodesDraggable: false, nodesConnectable: false, edgesReconnectable: false, elementsSelectable: false,
    fitViewOptions: { padding: .12 } });
  expect(props).toMatchObject({ zoomOnScroll: false, zoomOnPinch: true, zoomOnDoubleClick: false,
    panOnScroll: false, panOnDrag: true, preventScrolling: false, zoomActivationKeyCode: null });
  expect(props.nodesFocusable).toBeUndefined();
  expect(value).toEqual(original);
});

it("aligns the Creator inspector and horizontal reveal to fitView-transformed node bounds", () => {
  const selection = creatorCanonicalSelectionGeometry(
    new DOMRect(0, 100, 900, 800),
    new DOMRect(200, 200, 502, 400),
    1,
    500,
    40,
    new DOMRect(640, 456, 194, 112),
  );
  expect(selection).toEqual({ selectedY: 412, needsHorizontalReveal: true, scrollLeft: 326 });
});

it("selects canonical Creator nodes by pointer and keyboard while keeping chart navigation passive", async () => {
  const value: StoryGraph = { startNodeId: "start", nodes: [
    { id: "start", title: "开场", kind: "start", summary: "开始。", footageMode: "footage" },
    { id: "ending", title: "结局", kind: "ending", summary: "结束。", footageMode: "footage" },
  ], edges: [], joinContracts: [] };
  const select = vi.fn();
  await act(async () => root.render(createElement(CanonicalGraphCanvas, { value, selectedNodeId: "start", onNodeSelect: select })));
  const props = flowMock.mock.calls.at(-1)?.[0] as Record<string, any>;
  expect(props).toMatchObject({ nodesDraggable: false, nodesConnectable: false, edgesReconnectable: false, elementsSelectable: false,
    zoomOnScroll: false, zoomOnPinch: false, zoomOnDoubleClick: false, panOnScroll: false, panOnDrag: false, preventScrolling: false });
  expect(props.nodes.find((node: Record<string, any>) => node.id === "start")).toMatchObject({ focusable: true, selectable: true, selected: true });
  props.onNodeClick({}, props.nodes[1]);
  expect(select).toHaveBeenLastCalledWith("ending");

  const canvas = host.querySelector<HTMLElement>(".canonical-graph-canvas")!;
  const node = document.createElement("div"); node.className = "canonical-flow-node"; node.dataset.id = "start"; canvas.append(node);
  node.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
  expect(select).toHaveBeenLastCalledWith("start");
});

it("projects canonical node, route effects, and join details into the Creator inspector", async () => {
  const value: StoryGraph = {
    startNodeId: "start",
    nodes: [
      { id: "start", title: "开场", kind: "start", summary: "先行检查。", footageMode: "footage" },
      { id: "choice", title: "选择航标", kind: "decision", summary: "海雾接近。", footageMode: "route_only" },
      { id: "join", title: "回到值守台", kind: "join", summary: "两线归并。", footageMode: "route_only" },
      { id: "ending", title: "信标恢复", kind: "ending", summary: "港湾重见信标。", footageMode: "footage" },
    ],
    edges: [
      { id: "start-choice", sourceNodeId: "start", targetNodeId: "choice", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
      { id: "choice-join", sourceNodeId: "choice", targetNodeId: "join", kind: "choice", choiceText: "启用备用信标", stateEffects: { harbor_signal: "visible" }, entityStateEffects: [{ entityType: "location", entityId: "loc_control", state: "active" }] },
      { id: "join-ending", sourceNodeId: "join", targetNodeId: "ending", kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] },
    ],
    joinContracts: [{ id: "join-contract", joinNodeId: "join", incomingNodeIds: ["choice"], requiredStateKeys: ["harbor_signal"], allowedDifferences: ["weather"], reconciliation: "各路线回到值守台后继续。", notes: "路线选择保留在连接效果中。" }],
  };
  await act(async () => root.render(createElement(CreatorCanonicalStoryInspector, { graph: value, nodeId: "join" })));
  const fields = [...host.querySelectorAll<HTMLElement>(".field")].map(field => ({
    label: field.querySelector("label")?.textContent?.trim(),
    control: field.querySelector<HTMLInputElement | HTMLTextAreaElement>("input, textarea"),
  }));
  const read = (label: string) => fields.filter(field => field.label === label).map(field => field.control?.value);
  expect(read("章节标题")).toEqual(["回到值守台"]);
  expect(read("节点类型")).toEqual(["汇合点"]);
  expect(read("画面模式")).toEqual(["仅路线控制点"]);
  expect(read("剧情摘要")).toEqual(["两线归并。"]);
  expect(read("选项文字")).toEqual(["启用备用信标"]);
  expect(read("状态效果")).toContain("harbor_signal：visible\nlocation · loc_control：active");
  expect(read("输入节点")).toEqual(["选择航标"]);
  expect(read("必需状态")).toEqual(["harbor_signal"]);
  expect(read("允许差异")).toEqual(["weather"]);
  expect(read("汇合衔接")).toEqual(["各路线回到值守台后继续。"]);
  expect(read("合同备注")).toEqual(["路线选择保留在连接效果中。"]);
  expect(fields.every(field => field.control?.readOnly)).toBe(true);
  expect(host.querySelectorAll("button")).toHaveLength(0);
});

it.each(["decision", "join"])("explains %s footage production and playback without changing draft-only toggle semantics", async (kind) => {
  owner.selectedNodeId = kind;
  const render = async () => act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: owner, children: createElement(GraphNodeDetails, { disabled: false }) })));
  await render();
  const checkbox = host.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
  expect(checkbox.closest("label")?.textContent).toBe("此节点需要拍摄");
  expect(checkbox.checked).toBe(false);
  const description = document.getElementById(checkbox.getAttribute("aria-describedby")!)!;
  expect(description.className).toBe("graph-node-footage-help");
  expect(checkbox.closest("label")?.contains(description)).toBe(false);
  expect(description.textContent).toContain("需制作剧本场景、分镜和影片，时长计入完整路线");
  expect(description.textContent).toContain(kind === "decision" ? "先播放本节点影片，再显示问题与选项" : "播放本节点影片后，再继续后续路线");
  expect(description.textContent).toContain("不勾选则仅控制路线，无需拍摄");
  expect(description.textContent).toContain("确认并应用后才影响故事路线，不会自动生成影片");
  expect(description.textContent).toContain(`影响${creativeWorkflowStepReference("production")}`);
  expect(description.textContent).toContain("可能需要重新分配路线时长，并修订或重新审阅已有剧本、分镜和制作内容");
  expect(description.textContent).toContain("目标时长不会自动增加");
  expect(description.textContent).toContain(`完成后在${creativeWorkflowStepReference("play")}核对受影响路线`);
  expect(description.querySelectorAll("p")).toHaveLength(2);
  const original = owner.draft!.mapping;
  await act(async () => checkbox.click());
  const footage = { ...original, topologyOrigin: "author", sections: original.sections.map(section => section.sectionId === kind ? { ...section, footageMode: "footage" } : section) };
  expect(owner.changeMapping).toHaveBeenLastCalledWith(footage);
  owner.draft = { ...owner.draft!, mapping: { ...original, topologyOrigin: "author", sections: original.sections.map(section => section.sectionId === kind ? { ...section, footageMode: "footage" } : section) } };
  await render();
  expect(checkbox.checked).toBe(true);
  await act(async () => checkbox.click());
  expect(owner.changeMapping).toHaveBeenLastCalledWith({ ...original, topologyOrigin: "author" });
  expect(owner.saveDraft).not.toHaveBeenCalled();
  expect(owner.confirmMapping).not.toHaveBeenCalled();
  expect(owner.installMapping).not.toHaveBeenCalled();
});

it.each(["decision", "join"])("shares %s shooting help with Source and retains each owner's exact draft mutation", async (kind) => {
  owner.selectedNodeId = kind;
  const mapping = owner.draft!.mapping;
  const sourceChange = vi.fn();
  await act(async () => root.render(createElement(SourceStructureEditor, { mapping, disabled: false, onChange: sourceChange })));
  const sourceFieldset = [...host.querySelectorAll("fieldset")].find(fieldset => fieldset.querySelector("legend")?.textContent?.includes(kind === "decision" ? "选择节点" : "分支汇合"))!;
  const sourceCheckbox = sourceFieldset.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
  const sourceLabel = sourceCheckbox.closest("label")!;
  const sourceHelp = document.getElementById(sourceCheckbox.getAttribute("aria-describedby")!)!;
  expect(sourceLabel.textContent).toBe("此节点需要拍摄");
  expect(sourceHelp.textContent).toContain(kind === "decision" ? "先播放本节点影片，再显示问题与选项" : "播放本节点影片后，再继续后续路线");
  expect(sourceHelp.textContent).toContain(`影响${creativeWorkflowStepReference("production")}`);
  expect(sourceHelp.textContent).toContain(`完成后在${creativeWorkflowStepReference("play")}核对受影响路线`);
  await act(async () => sourceCheckbox.click());
  const sectionIndex = mapping.sections.findIndex(section => section.sectionId === kind);
  const expectedSource = { ...mapping, topologyOrigin: "author", sections: mapping.sections.map((item, index) => index === sectionIndex ? { ...item, footageMode: "footage" } : item) };
  expect(sourceChange).toHaveBeenCalledWith(expectedSource);

  await act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: owner, children: createElement(GraphNodeDetails, { disabled: false }) })));
  const graphCheckbox = host.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
  const graphLabel = graphCheckbox.closest("label")!;
  const graphHelp = document.getElementById(graphCheckbox.getAttribute("aria-describedby")!)!;
  expect(graphLabel.textContent).toBe(sourceLabel.textContent);
  expect(graphHelp.textContent).toBe(sourceHelp.textContent);
  const expectedGraph = { ...mapping, topologyOrigin: "author", sections: mapping.sections.map(item => item.sectionId === kind ? { ...item, footageMode: "footage" } : item) };
  await act(async () => graphCheckbox.click());
  expect(owner.changeMapping).toHaveBeenLastCalledWith(expectedGraph);
  expect(owner.saveDraft).not.toHaveBeenCalled();
  expect(owner.confirmMapping).not.toHaveBeenCalled();
  expect(owner.installMapping).not.toHaveBeenCalled();
});

it.each(["decision", "join"])("keeps Source %s shooting explanation visible when editing is disabled", async kind => {
  owner.selectedNodeId = kind;
  const sourceChange = vi.fn();
  await act(async () => root.render(createElement(SourceStructureEditor, { mapping: owner.draft!.mapping, disabled: true, onChange: sourceChange })));
  const fieldset = [...host.querySelectorAll("fieldset")].find(item => item.querySelector("legend")?.textContent?.includes(kind === "decision" ? "选择节点" : "分支汇合"))!;
  const checkbox = fieldset.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
  expect(checkbox.disabled).toBe(true);
  expect(checkbox.closest("label")?.textContent).toBe("此节点需要拍摄");
  expect(document.getElementById(checkbox.getAttribute("aria-describedby")!)?.textContent).toContain("不会自动生成影片");
  await act(async () => checkbox.click());
  expect(sourceChange).not.toHaveBeenCalled();
});

it.each(["decision", "join"])("keeps %s footage help readable when editing is disabled", async (kind) => {
  owner.selectedNodeId = kind;
  await act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: owner, children: createElement(GraphNodeDetails, { disabled: true }) })));
  const checkbox = host.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
  expect(checkbox.disabled).toBe(true);
  expect(document.getElementById(checkbox.getAttribute("aria-describedby")!)?.textContent).toContain("不会自动生成影片");
  await act(async () => checkbox.click());
  expect(owner.changeMapping).not.toHaveBeenCalled();
});

it.each(["start", "scene", "ending"])("does not offer optional filming for %s nodes", async (kind) => {
  owner.selectedNodeId = kind;
  await act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: owner, children: createElement(GraphNodeDetails, { disabled: false }) })));
  expect(host.querySelector('input[type="checkbox"]')).toBeNull();
  expect(host.querySelector(".graph-node-footage-help")).toBeNull();
});
