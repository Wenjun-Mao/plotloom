import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import type { GraphAuthoringDraft, GraphCommandPreview } from "../src/features/graph/contracts";
import { GraphCommandDialog } from "../src/features/graph/GraphCommandDialog";
import { graphDraftFixture } from "./graph-workbench-fixture";

const { useGraphWorkbench } = vi.hoisted(() => ({ useGraphWorkbench: vi.fn() }));
vi.mock("../src/features/graph/GraphWorkbenchContext", () => ({ useGraphWorkbench }));

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root, container: HTMLDivElement, owner: GraphWorkbenchController;

function draftWithJoin(): GraphAuthoringDraft {
  const draft = graphDraftFixture();
  draft.mapping.topology.nodes.push({ id: "merge", kind: "join" });
  draft.mapping.sections.push({ sectionId: "merge", title: "汇合点", summary: "", ending: false, footageMode: "route_only" });
  draft.mapping.topology.edges = [
    { id: "opening-merge", sourceNodeId: "opening", targetNodeId: "merge", kind: "continuation", stateEffects: {}, entityStateEffects: [] },
    { id: "merge-ending", sourceNodeId: "merge", targetNodeId: "ending", kind: "continuation", stateEffects: {}, entityStateEffects: [] },
  ];
  return draft;
}

function contractDraft(): GraphAuthoringDraft {
  const draft = draftWithJoin();
  draft.mapping.topology.joins = [{ id: "join-1", joinNodeId: "merge", incomingNodeIds: ["opening"],
    requiredStateKeys: ["arrival"], allowedDifferences: ["arrival"], notes: "Authored contract note." }];
  draft.mapping.joinReconciliations = { "join-1": "Preserve the arrival state." };
  return draft;
}

function preview(before: GraphAuthoringDraft, after: GraphAuthoringDraft,
  impact: GraphCommandPreview["impact"]): GraphCommandPreview {
  return { draftRevision: 1, bindingHash: before.bindingHash, command: { operation: "remove_join", joinId: "join-1" },
    result: after, impact, previewHash: "c".repeat(64) };
}

function impact(changes: Partial<GraphCommandPreview["impact"]> = {}): GraphCommandPreview["impact"] {
  return { addedNodeIds: [], removedNodeIds: [], addedEdgeIds: [], removedEdgeIds: [], changedEdgeIds: [],
    affectedJoinIds: [], retainedNodeIds: [], pendingEdgeIds: [], messages: [], ...changes };
}

async function renderDialog() {
  await act(async () => root.render(createElement(GraphCommandDialog)));
  return container.querySelector("dialog")!;
}

beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true, value(this: HTMLDialogElement) { this.setAttribute("open", ""); },
  });
  container = document.createElement("div"); root = createRoot(container);
  const draft = draftWithJoin();
  owner = { state: null, readStatus: "ready", readError: "", draft, selectedNodeId: "opening", busy: false, error: "", stale: false, preview: null,
    previewConflict: false, canUndo: false, refresh: vi.fn().mockResolvedValue(undefined), selectNode: vi.fn(),
    changeMapping: vi.fn(), changeDraft: vi.fn(), adoptMapping: vi.fn(), saveDraft: vi.fn().mockResolvedValue(true),
    confirmMapping: vi.fn().mockResolvedValue(true), installMapping: vi.fn().mockResolvedValue(true),
    prepareCommand: vi.fn().mockResolvedValue(true), cancelPreview: vi.fn(), applyPreview: vi.fn().mockResolvedValue(undefined),
    undo: vi.fn().mockResolvedValue(undefined), recover: vi.fn().mockResolvedValue(undefined), discard: vi.fn().mockResolvedValue(true) };
  useGraphWorkbench.mockReturnValue(owner);
});

afterEach(async () => {
  await act(async () => root.unmount());
  vi.clearAllMocks();
});

it("discloses nonblank contract deletion while showing that its node and graph connections remain", async () => {
  const before = contractDraft();
  before.mapping.sections.find(section => section.sectionId === "opening")!.title = "第一条路径";
  const after = structuredClone(before);
  after.mapping.topology.joins = [];
  after.mapping.joinReconciliations = {};
  owner.draft = before;
  owner.preview = preview(before, after, impact({ affectedJoinIds: ["join-1"], retainedNodeIds: ["opening", "merge", "ending"],
    messages: ["移除汇合合同及其必需状态键、允许差异、协调说明、备注和未提交字段输入。汇合节点与图连接保留。"] }));

  const dialog = await renderDialog();

  expect(dialog.textContent).toContain("移除汇合合同：汇合点（直接输入：第一条路径）");
  expect(dialog.textContent).toContain("必需状态键、允许差异、协调说明、备注和未提交字段输入");
  expect(dialog.textContent).toContain("汇合节点与图连接保留");
  expect(dialog.textContent).not.toContain("保留原有事实");
  expect(after.mapping.topology.nodes).toEqual(before.mapping.topology.nodes);
  expect(after.mapping.topology.edges).toEqual(before.mapping.topology.edges);
});

it("classifies a newly added join contract from before and result membership", async () => {
  const before = draftWithJoin(), after = contractDraft();
  before.mapping.sections.find(section => section.sectionId === "opening")!.title = "第一条路径";
  after.mapping.sections.find(section => section.sectionId === "opening")!.title = "第一条路径";
  owner.draft = before;
  owner.preview = preview(before, after, impact({ affectedJoinIds: ["join-1"], retainedNodeIds: ["opening", "merge", "ending"],
    messages: ["新增汇合合同；合同字段目前为空，请填写并审阅其直接输入节点。"] }));

  const dialog = await renderDialog();

  expect(dialog.textContent).toContain("新增汇合合同：汇合点（直接输入：第一条路径）");
  expect(dialog.textContent).not.toContain("需审阅汇合");
  expect(dialog.textContent).toContain("合同字段目前为空");
});

it("states when added and removed contracts have no direct input nodes", async () => {
  const before = contractDraft();
  before.mapping.topology.joins[0].incomingNodeIds = [];
  const after = structuredClone(before);
  before.mapping.topology.joins[0].notes = "Removed contract";
  before.mapping.joinReconciliations["join-1"] = "Removed reconciliation";
  after.mapping.topology.joins = [{ ...before.mapping.topology.joins[0], id: "join-2",
    requiredStateKeys: [], allowedDifferences: [], notes: "" }];
  after.mapping.joinReconciliations = { "join-2": "" };
  owner.draft = before;
  owner.preview = preview(before, after, impact({ affectedJoinIds: ["join-1", "join-2"],
    retainedNodeIds: ["opening", "merge", "ending"], messages: ["合同输入为空。"] }));

  const dialog = await renderDialog();

  expect(dialog.textContent).toContain("移除汇合合同：汇合点（直接输入：无直接输入）");
  expect(dialog.textContent).toContain("新增汇合合同：汇合点（直接输入：无直接输入）");
});

it("shows exact before and after input-node memberships for a retained contract", async () => {
  const before = contractDraft();
  before.mapping.sections.find(section => section.sectionId === "opening")!.title = "第一条路径";
  const after = structuredClone(before);
  after.mapping.topology.nodes.push({ id: "new-route", kind: "scene" });
  after.mapping.sections.push({ sectionId: "new-route", title: "新增路线", summary: "", ending: false, footageMode: "footage" });
  after.mapping.topology.joins[0].incomingNodeIds = ["opening", "new-route"];
  owner.draft = before;
  owner.preview = preview(before, after, impact({ affectedJoinIds: ["join-1"], retainedNodeIds: ["opening", "merge", "ending"] }));

  const dialog = await renderDialog();

  expect(dialog.textContent).toContain("汇合输入节点变化，需重新审阅：汇合点：第一条路径 → 第一条路径、新增路线");
  expect(dialog.textContent).toContain("汇合输入节点变化，需重新审阅");
});

it("shows retained node kind and footage-mode changes", async () => {
  const before = draftWithJoin(), after = structuredClone(before);
  before.mapping.sections.find(section => section.sectionId === "merge")!.title = "最后一条能源总线";
  after.mapping.sections.find(section => section.sectionId === "merge")!.title = "最后一条能源总线";
  after.mapping.topology.nodes.find(node => node.id === "merge")!.kind = "scene";
  after.mapping.sections.find(section => section.sectionId === "merge")!.footageMode = "footage";
  owner.draft = before;
  owner.preview = preview(before, after, impact({ retainedNodeIds: ["opening", "merge", "ending"] }));

  const dialog = await renderDialog();

  expect(dialog.textContent).toContain("节点类型与画面变化：最后一条能源总线：类型 汇合点 → 故事发展；画面 仅路线控制点 → 包含画面");
  expect(dialog.textContent).toContain("修改节点类型或画面");
});
