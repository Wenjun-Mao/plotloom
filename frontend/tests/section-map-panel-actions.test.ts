import { act, createElement, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SectionMapPanel } from "../src/pages/SectionMapPanel";
import { SourceStructureEditor } from "../src/pages/SourceStructureEditor";
import { GraphWorkbenchContext } from "../src/features/graph/GraphWorkbenchContext";
import { graphControllerFixture } from "./graph-workbench-fixture";
import type { SectionMap, SourceTopology } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root;
let host: HTMLDivElement;
const seedTopology: SourceTopology = {
  plannerVersion: "story_graph_topology.v3", projectId: "project", topologyHash: "a".repeat(64), structuralParameters: {}, startNodeId: "opening",
  nodes: [{ id: "opening", kind: "start", footageMode: "footage" }, { id: "choose", kind: "decision", footageMode: "route_only" },
    { id: "ending-a", kind: "ending", footageMode: "footage" }, { id: "ending-b", kind: "ending", footageMode: "footage" }],
  edges: [{ id: "opening-choice", sourceNodeId: "opening", targetNodeId: "choose", kind: "continuation" },
    { id: "path-a", sourceNodeId: "choose", targetNodeId: "ending-a", kind: "choice" },
    { id: "path-b", sourceNodeId: "choose", targetNodeId: "ending-b", kind: "choice" }], joins: [],
};
const mapping: SectionMap = {
  seedTopology, topologyOrigin: "planner",
  topology: { startNodeId: seedTopology.startNodeId, nodes: seedTopology.nodes.map(({ id, kind }) => ({ id, kind })),
    edges: seedTopology.edges.map(edge => ({ ...edge, stateEffects: {}, entityStateEffects: [] })), joins: [] },
  sections: [
    { sectionId: "opening", title: "开场", summary: "选择开始。", ending: false, footageMode: "footage" },
    { sectionId: "choose", title: "选择", summary: "选择行动。", ending: false, footageMode: "route_only" },
    { sectionId: "ending-a", title: "结局 A", summary: "路线 A。", ending: true, footageMode: "footage" },
    { sectionId: "ending-b", title: "结局 B", summary: "路线 B。", ending: true, footageMode: "footage" },
  ],
  choices: [{ choiceId: "choose", sectionId: "choose", prompt: "选择？", outcomes: [
    { outcomeId: "path-a", label: "前往 A", consequence: "发生 A。", endingSectionId: "ending-a" },
    { outcomeId: "path-b", label: "前往 B", consequence: "发生 B。", endingSectionId: "ending-b" },
  ] }], joinReconciliations: {},
};
const accepted = { revision: 3, sourceRevision: 1, outlineRevision: 2, outlineContentHash: "outline", contentHash: "map-hash", mapping, acceptedAt: "2026-09-26" } as any;
const outline = { revision: 2, sourceRevision: 1, contentHash: "outline" } as any;
const admission = { status: "current", sectionMapRevision: 3, sectionMapContentHash: "map-hash", graphRevision: 4, graphContentHash: "graph-hash", staleReasons: [] } as any;

function SharedOwner({ children, stale = false }: { children: import("react").ReactNode; stale?: boolean }) {
  const [currentMapping, changeMapping] = useState(mapping);
  const draft = { bindingHash: "a".repeat(64), mapping: currentMapping, rowHints: {}, selectedNodeId: "opening", detachedEndpoints: {}, fieldBuffers: {} };
  return createElement(GraphWorkbenchContext.Provider, { value: graphControllerFixture({ draft, stale, changeMapping: next => changeMapping(next as SectionMap) }), children });
}
function render({ status = "current", graphReady = false, sourceDirty = false, admissionMismatch, busy = false, readOnly = false, outlineCurrent = true, staleReasons = [] }: { status?: "current" | "stale"; graphReady?: boolean; sourceDirty?: boolean; admissionMismatch?: "hash" | "revision"; busy?: boolean; readOnly?: boolean; outlineCurrent?: boolean; staleReasons?: string[] } = {}) {
  const effectiveAdmission = admissionMismatch === "hash" ? { ...admission, sectionMapContentHash: "other-map" } : admissionMismatch === "revision" ? { ...admission, sectionMapRevision: 4 } : admission;
  return act(async () => root.render(createElement(SharedOwner, { children: createElement(SectionMapPanel, {
    outline, outlineCurrent, accepted, status, staleReasons, graphAdmission: effectiveAdmission, graphReady, sourceDirty, routes: [], readOnly, busy,
    onSave: () => undefined, onInstall: () => undefined, onContinue: () => undefined,
  }) })));
}
function button(label: string) { return Array.from(host.querySelectorAll("button")).find((item) => item.textContent === label)!; }

beforeEach(() => { host = document.createElement("div"); document.body.append(host); root = createRoot(host); });
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

it("records footage changes as author edits while preserving the seed", async () => {
  const change = vi.fn();
  await act(async () => root.render(createElement(SourceStructureEditor, { mapping, disabled: false, onChange: change })));
  await act(async () => host.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click());
  const edited = change.mock.calls[0][0] as SectionMap;
  expect(edited.topologyOrigin).toBe("author");
  expect(edited.seedTopology).toEqual(mapping.seedTopology);
  expect(edited.sections.find(section => section.sectionId === "choose")?.footageMode).toBe("footage");
});

it("requires a saved clean map before applying and enables save after an edit", async () => {
  await render();
  const required = host.querySelectorAll("[aria-required='true']");
  expect(required).toHaveLength(13);
  for (const control of required) {
    expect(control.closest("label")?.querySelector(".required-mark")?.getAttribute("aria-hidden")).toBe("true");
    expect(control.hasAttribute("required")).toBe(false);
  }
  expect(button("保存修改").disabled).toBe(true);
  expect(button("应用到故事路线").disabled).toBe(false);
  const title = host.querySelector<HTMLInputElement>("input[value='开场']")!;
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(title, "新的开场");
  await act(async () => title.dispatchEvent(new Event("input", { bubbles: true })));
  expect(button("保存修改").disabled).toBe(false);
  expect(button("应用到故事路线").disabled).toBe(true);
  expect(host.textContent).toContain("请先保存修改");
});

it("allows stale maps to be explicitly reconfirmed and only continues after the matching admitted graph loads", async () => {
  await render({ status: "stale", graphReady: true });
  expect(button("保存修改").disabled).toBe(false);
  expect(button("应用到故事路线").disabled).toBe(true);
  await render({ graphReady: true });
  expect(button("应用到故事路线").disabled).toBe(true);
  expect(button("继续：角色设定").disabled).toBe(false);
  expect(host.textContent).toContain("故事路线已就绪");
});

it("explains stale branches without promising an unavailable outline return and retains technical evidence", async () => {
  await render({ status: "stale", outlineCurrent: false, staleReasons: ["accepted source revision changed to r2"] });
  expect(host.textContent).toContain("请先确认当前大纲，再检查并保存分支；旧内容仍保留");
  expect(host.textContent).toContain("请先在上方确认当前大纲，再继续");
  expect(host.textContent).not.toContain("返回保留的有效版本");
  const details = [...host.querySelectorAll("details")].find(item => item.querySelector("summary")?.textContent === "技术详情：分支过期原因")!;
  expect(details.open).toBe(false);
  expect(details.textContent).toContain("accepted source revision changed to r2");
  expect(button("保存修改").disabled).toBe(true);
  expect(button("应用到故事路线").disabled).toBe(true);
});

it("keeps continuation unavailable for a mismatched admission, source edits, busy, or read-only state", async () => {
  await render({ graphReady: true, admissionMismatch: "hash" });
  expect(Array.from(host.querySelectorAll("button")).find((item) => item.textContent === "继续：角色设定")).toBeUndefined();
  await render({ graphReady: true, admissionMismatch: "revision" });
  expect(Array.from(host.querySelectorAll("button")).find((item) => item.textContent === "继续：角色设定")).toBeUndefined();
  await render({ graphReady: true, sourceDirty: true });
  expect(button("继续：角色设定").disabled).toBe(true);
  expect(host.textContent).toContain("请先保存故事内容");
  await render({ graphReady: true, busy: true });
  expect(button("继续：角色设定").disabled).toBe(true);
  await render({ graphReady: true, readOnly: true });
  expect(button("继续：角色设定").disabled).toBe(true);
});

it("never confirms a retained root draft under changed current context", async () => {
  const save = vi.fn().mockResolvedValue(true);
  await act(async () => root.render(createElement(SharedOwner, { stale: true, children: createElement(SectionMapPanel, {
    outline, accepted, status: "current", staleReasons: [], graphAdmission: admission, graphReady: true, sourceDirty: false,
    routes: [], readOnly: false, busy: false, onSave: save, onInstall: () => undefined, onContinue: () => undefined,
  }) })));
  expect(host.textContent).toContain("当前图草稿仍保留");
  expect(button("保存修改").disabled).toBe(true);
  expect(button("应用到故事路线").disabled).toBe(true);
  expect(button("继续：角色设定").disabled).toBe(true);
  await act(async () => button("保存修改").click());
  expect(save).not.toHaveBeenCalled();
});
