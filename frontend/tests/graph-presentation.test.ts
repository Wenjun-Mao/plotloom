import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { GraphNodeDetails } from "../src/features/graph/GraphNodeDetails";
import { CanonicalGraphReader } from "../src/features/graph/CanonicalGraphReader";
import { GraphWorkbenchContext, type GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import { graphControllerFixture, graphDraftFixture } from "./graph-workbench-fixture";
import type { StoryGraph } from "../src/types";

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
