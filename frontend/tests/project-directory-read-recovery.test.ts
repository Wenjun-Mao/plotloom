import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { useProjectDirectory } from "../src/app/workspace/useProjectDirectory";
import { ProjectDirectoryDialog } from "../src/app/workspace/ProjectDirectoryDialog";
import { useWorkspaceSourceReview } from "../src/app/workspace/useWorkspaceSourceReview";
import type { ProjectListItem, SourceOutlineReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());
async function directoryHarness() {
  let owner!: ReturnType<typeof useProjectDirectory>;
  const root = createRoot(document.createElement("div"));
  function Probe() { owner = useProjectDirectory(String); return null; }
  await act(async () => root.render(createElement(Probe)));
  return { get owner() { return owner; }, close: () => act(async () => root.unmount()) };
}
const row = (id: string) => ({ id } as ProjectListItem);
it("retained directory failure disables only row operations and explains the available new-workspace actions", async () => {
  const host = document.createElement("div"), root = createRoot(host);
  const onBlank = vi.fn(), onSample = vi.fn(), onOpen = vi.fn(), onAction = vi.fn(async () => undefined);
  try {
    await act(async () => root.render(createElement(ProjectDirectoryDialog, {
      projects: [{ id: "a", brief: { title: "Retained project" }, revision: 1, updatedAt: "2026-10-09T10:00:00Z" } as ProjectListItem],
      currentProjectId: "a", showArchived: false, error: "", readError: "directory offline", loading: false,
      hasMore: false, explicitProjectClose: true, onBlank, onSample, onOpen, onAction,
      onRetry: vi.fn(), onLoadMore: vi.fn(), onArchived: vi.fn(), onClose: vi.fn(),
    })));
    expect(host.textContent).toContain("列表中的项目操作暂不可用");
    expect(host.textContent).toContain("仍可新建空白项目或打开示例项目");
    const rowButtons = [...host.querySelectorAll<HTMLButtonElement>(".directory-item button")];
    expect(rowButtons.length).toBeGreaterThan(0); expect(rowButtons.every(button => button.disabled)).toBe(true);
    for (const label of ["新建空白项目", "打开示例项目"]) {
      const button = [...host.querySelectorAll<HTMLButtonElement>(".directory-onboarding button")].find(item => item.textContent === label)!;
      expect(button.disabled).toBe(false); await act(async () => button.click());
    }
    expect(onBlank).toHaveBeenCalledOnce(); expect(onSample).toHaveBeenCalledOnce();
    expect(onOpen).not.toHaveBeenCalled(); expect(onAction).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});
it("directory initial failure retries the exact GET and keeps action errors independent", async () => {
  const read = vi.spyOn(plotloomApi, "listProjects").mockRejectedValueOnce(new Error("offline"));
  const state = await directoryHarness();
  try {
    await act(async () => state.owner.openDirectory());
    expect(state.owner.readError).toContain("offline"); expect(state.owner.error).toBe("");
    read.mockResolvedValue({ projects: [row("a")], nextCursor: null });
    await act(async () => { state.owner.setError("action failed"); await state.owner.retry(); });
    expect(state.owner.projects).toEqual([row("a")]); expect(state.owner.readError).toBe("");
    expect(state.owner.error).toBe("action failed"); expect(read).toHaveBeenNthCalledWith(2, false, 50, undefined);
  } finally { await state.close(); }
});
it("directory failed append preserves rows and cursor, and filter failure cannot mislabel rows", async () => {
  const read = vi.spyOn(plotloomApi, "listProjects").mockResolvedValueOnce({ projects: [row("a")], nextCursor: "page2" });
  const state = await directoryHarness();
  try {
    await act(async () => state.owner.openDirectory());
    read.mockRejectedValueOnce(new Error("append offline"));
    await act(async () => state.owner.refresh(false, "page2", true));
    expect(state.owner.projects).toEqual([row("a")]); expect(state.owner.nextCursor).toBe("page2");
    read.mockResolvedValueOnce({ projects: [row("b")], nextCursor: null });
    await act(async () => state.owner.retry());
    expect(read).toHaveBeenNthCalledWith(3, false, 50, "page2"); expect(state.owner.projects).toEqual([row("a"), row("b")]);
    read.mockRejectedValueOnce(new Error("filter offline"));
    await act(async () => { state.owner.setShowArchived(true); await state.owner.refresh(true); });
    expect(state.owner.projects).toEqual([]); expect(state.owner.readError).toContain("filter offline");
  } finally { await state.close(); }
});
it("directory close and newer filter invalidate held replies", async () => {
  let resolve!: (value: { projects: ProjectListItem[]; nextCursor: null }) => void;
  const read = vi.spyOn(plotloomApi, "listProjects").mockImplementationOnce(() => new Promise(done => { resolve = done; }));
  const state = await directoryHarness();
  try {
    let pending!: Promise<unknown>;
    await act(async () => { pending = state.owner.openDirectory(); });
    await act(async () => state.owner.closeDirectory());
    await act(async () => { resolve({ projects: [row("late")], nextCursor: null }); await pending; });
    expect(state.owner.projects).toEqual([]); expect(state.owner.open).toBe(false);
    read.mockResolvedValue({ projects: [row("current")], nextCursor: null });
    await act(async () => state.owner.openDirectory()); expect(state.owner.projects).toEqual([row("current")]);
  } finally { await state.close(); }
});
it("shared source read catches failure, retries GET and excludes late project results", async () => {
  let owner!: ReturnType<typeof useWorkspaceSourceReview>, project = "a";
  const read = vi.spyOn(plotloomApi, "getSourceOutline").mockRejectedValueOnce(new Error("source offline"));
  const root = createRoot(document.createElement("div"));
  function Probe() { owner = useWorkspaceSourceReview(project, 1); return null; }
  try {
    await act(async () => root.render(createElement(Probe))); expect(owner.status).toBe("failed");
    let resolve!: (value: SourceOutlineReviewState) => void;
    read.mockImplementationOnce(() => new Promise(done => { resolve = done; }));
    let pending!: Promise<unknown>;
    await act(async () => { pending = owner.refresh(); }); expect(owner.status).toBe("loading"); expect(owner.value).toBeNull();
    const source = (marker: string): SourceOutlineReviewState => ({ source: null, candidate: null, acceptedOutline: null, outlineStatus: "missing", acceptedSectionMap: null, sectionMapStatus: "missing", sectionMapStaleReasons: [marker], graphAdmission: null });
    project = "b"; read.mockResolvedValue(source("b"));
    await act(async () => root.render(createElement(Probe)));
    await act(async () => { resolve(source("a")); await pending; });
    expect(owner.value?.sectionMapStaleReasons).toEqual(["b"]); expect(owner.status).toBe("ready");
    expect(read.mock.calls.map(call => call[0])).toEqual(["a", "a", "b"]);
  } finally { await act(async () => root.unmount()); }
});

it("coalesces source reads and prevents a held read from replacing a mutation result", async () => {
  const source = (revision: number): SourceOutlineReviewState => ({
    source: { revision } as never, candidate: null, acceptedOutline: null, outlineStatus: "missing",
    acceptedSectionMap: null, sectionMapStatus: "missing", sectionMapStaleReasons: [], graphAdmission: null,
  });
  let resolve!: (value: SourceOutlineReviewState) => void;
  const read = vi.spyOn(plotloomApi, "getSourceOutline").mockImplementation(() => new Promise(done => { resolve = done; }));
  let owner!: ReturnType<typeof useWorkspaceSourceReview>;
  const root = createRoot(document.createElement("div"));
  function Probe() { owner = useWorkspaceSourceReview("project", 1); return null; }
  try {
    await act(async () => root.render(createElement(Probe)));
    expect(read).toHaveBeenCalledOnce();
    let refresh!: Promise<unknown>;
    await act(async () => { refresh = owner.refresh(); });
    expect(read).toHaveBeenCalledOnce();
    await act(async () => {
      owner.replace(source(2));
      resolve(source(1));
      await refresh;
    });
    expect(owner.status).toBe("ready");
    expect(owner.value?.source?.revision).toBe(2);
  } finally { await act(async () => root.unmount()); }
});
