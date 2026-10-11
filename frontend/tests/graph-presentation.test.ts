import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { GraphNodeDetails } from "../src/features/graph/GraphNodeDetails";
import { CanonicalGraphReader } from "../src/features/graph/CanonicalGraphReader";
import { GraphWorkbenchContext, type GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import { graphControllerFixture, graphDraftFixture } from "./graph-workbench-fixture";
import type { StoryGraph } from "../src/types";
import { creativeWorkflowStepReference } from "../src/creative-workflow-steps";

vi.mock("@xyflow/react", () => ({ ReactFlow: () => null, MarkerType: { ArrowClosed: "closed" } }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root, owner: GraphWorkbenchController;
const kinds = ["start", "scene", "decision", "join", "ending"] as const;
const labels = ["开场", "故事发展", "选择点", "汇合点", "结局"];

beforeEach(() => {
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
