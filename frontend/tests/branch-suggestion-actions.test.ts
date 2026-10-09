import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { SectionMapPanel } from "../src/pages/SectionMapPanel";
import { GraphWorkbenchContext } from "../src/features/graph/GraphWorkbenchContext";
import { graphControllerFixture, graphDraftFixture } from "./graph-workbench-fixture";
import type { AcceptedOutlineRevision, BranchTaskState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
const candidate = { jobId: "branch-task", status: "ready", reportAvailable: false, suggestion: {
  nodes: [], choices: [], joins: [], clarifications: [],
} };
const task: BranchTaskState = { candidate, plannedTopology: null, infeasibleReason: null, staleReasons: [] };
const outline = { revision: 1, sourceRevision: 1, contentHash: "outline" } as AcceptedOutlineRevision;
const draft = graphDraftFixture();
let owner: ReturnType<typeof graphControllerFixture>;

beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  owner = graphControllerFixture({ draft });
  vi.spyOn(plotloomApi, "getBranchSuggestions").mockResolvedValue(task);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });
function button(label: string) { return [...host.querySelectorAll("button")].find(item => item.textContent === label)!; }
async function render(changes: Partial<Parameters<typeof SectionMapPanel>[0]> = {}) {
  await act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: owner }, createElement(SectionMapPanel, {
    projectId: "project", outline, outlineCurrent: true, accepted: null, status: "missing", staleReasons: [],
    graphAdmission: null, graphReady: false, sourceDirty: false, routes: [], readOnly: false, busy: false,
    onSave: vi.fn(), onInstall: vi.fn(), onContinue: vi.fn(), ...changes,
  }))));
}

it("cancels an obsolete task without adopting or changing the dirty graph/source", async () => {
  owner.stale = true;
  const cancel = vi.spyOn(plotloomApi, "cancelBranchSuggestions").mockResolvedValue({ ...task, candidate: { ...candidate, status: "cancelled" } });
  await render({ outlineCurrent: false, sourceDirty: true });
  expect(button("带入可编辑草稿").disabled).toBe(true);
  expect(button("放弃此建议任务").disabled).toBe(false);
  await act(async () => button("放弃此建议任务").click());
  expect(cancel).toHaveBeenCalledExactlyOnceWith("project", "branch-task");
  expect(button("准备剧情分支建议").disabled).toBe(true);
  expect(owner.adoptMapping).not.toHaveBeenCalled();
  expect(owner.changeMapping).not.toHaveBeenCalled();
  expect(owner.draft).toBe(draft);
});

it.each(["readOnly", "busy", "graphBusy"] as const)("still blocks cancellation for %s", async reason => {
  const cancel = vi.spyOn(plotloomApi, "cancelBranchSuggestions");
  owner.busy = reason === "graphBusy";
  await render({ readOnly: reason === "readOnly", busy: reason === "busy" });
  expect(button("放弃此建议任务").disabled).toBe(true);
  await act(async () => button("放弃此建议任务").click());
  expect(cancel).not.toHaveBeenCalled();
});

it("rereads the candidate when the retained outline becomes non-current", async () => {
  const read = vi.mocked(plotloomApi.getBranchSuggestions);
  await render();
  read.mockResolvedValue({ ...task, staleReasons: ["请先确认当前大纲。"] });
  await render({ outlineCurrent: false });
  expect(read).toHaveBeenCalledTimes(2);
  expect(host.textContent).toContain("请先确认当前大纲。");
});

it("shows readable failed-read feedback and retries without mutations", async () => {
  const failure = new Error("服务请求失败（HTTP 503）"); failure.name = "ApiError";
  vi.mocked(plotloomApi.getBranchSuggestions).mockRejectedValueOnce(failure);
  await render();
  expect(host.querySelector('[role="alert"]')?.textContent).toContain(failure.message);
  expect(host.textContent).not.toContain("ApiError:");
  expect(button("放弃此建议任务")).toBeUndefined();
  await act(async () => button("重试读取建议").click());
  expect(button("放弃此建议任务").disabled).toBe(false);
  expect(owner.adoptMapping).not.toHaveBeenCalled();
});

it("retains the task on cancellation failure without retrying automatically", async () => {
  let reject!: (error: Error) => void;
  const cancel = vi.spyOn(plotloomApi, "cancelBranchSuggestions").mockReturnValue(new Promise((_, fail) => { reject = fail; }));
  await render({ sourceDirty: true });
  await act(async () => button("放弃此建议任务").click());
  expect(button("放弃此建议任务").disabled).toBe(true);
  await act(async () => button("放弃此建议任务").click());
  const failure = new Error("取消未完成，请稍后重试。"); failure.name = "ApiError";
  await act(async () => reject(failure));
  expect(cancel).toHaveBeenCalledTimes(1);
  expect(button("放弃此建议任务").disabled).toBe(false);
  expect(host.textContent).toContain(failure.message);
  expect(host.textContent).not.toContain("ApiError:");
  expect(owner.adoptMapping).not.toHaveBeenCalled();
});

it("keeps cancellation owned through a basis change and rereads after it commits", async () => {
  let finish!: (state: BranchTaskState) => void;
  const cancelled = { ...task, candidate: { ...candidate, status: "cancelled" } };
  const cancel = vi.spyOn(plotloomApi, "cancelBranchSuggestions").mockReturnValue(new Promise(resolve => { finish = resolve; }));
  await render();
  await act(async () => button("放弃此建议任务").click());
  await render({ outlineCurrent: false });
  expect(button("放弃此建议任务").disabled).toBe(true);
  vi.mocked(plotloomApi.getBranchSuggestions).mockResolvedValue(cancelled);
  await act(async () => finish(cancelled));
  expect(cancel).toHaveBeenCalledTimes(1);
  expect(button("放弃此建议任务")).toBeUndefined();
  expect(button("准备剧情分支建议").disabled).toBe(true);
  expect(plotloomApi.getBranchSuggestions).toHaveBeenCalledTimes(3);
});

it("does not apply a departed project's cancellation response to the new project", async () => {
  let finish!: (state: BranchTaskState) => void;
  vi.spyOn(plotloomApi, "cancelBranchSuggestions").mockReturnValue(new Promise(resolve => { finish = resolve; }));
  await render();
  await act(async () => button("放弃此建议任务").click());
  vi.mocked(plotloomApi.getBranchSuggestions).mockResolvedValue({ ...task, candidate: { ...candidate, jobId: "other-task" } });
  await render({ projectId: "other-project" });
  expect(button("放弃此建议任务").disabled).toBe(false);
  await act(async () => finish({ ...task, candidate: { ...candidate, status: "cancelled" } }));
  expect(button("放弃此建议任务").disabled).toBe(false);
  expect(button("准备剧情分支建议")).toBeUndefined();
  expect(plotloomApi.getBranchSuggestions).toHaveBeenCalledTimes(2);
});
