import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { putDraft } from "../src/draft-registry";
import { useProjectLifecycle } from "../src/app/workspace/useProjectLifecycle";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import { createReviewDraftStore } from "../src/features/authoring/reviewDraftStore";
import type { ProjectListItem, ProjectResource } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); });
const deferred = () => {
  let resolve!: () => void;
  const promise = new Promise<void>(done => { resolve = done; });
  return { promise, resolve };
};

async function harness() {
  const project = { ...structuredClone(demoProject), id: "command-owner", revision: 1, lifecycleRevision: 1, lifecycleStatus: "active" as const };
  const target: ProjectListItem = { ...project, archivedAt: null, createdAt: "2026-10-09", updatedAt: "2026-10-09", operationalState: "open",
    stageStatuses: { story_bible: "ready", story_graph: "ready", scene_beats: "ready", storyboard: "ready" }, latestRun: null };
  const quiescence = createProjectDraftQuiescence();
  let epoch = 0;
  const params: Parameters<typeof useProjectLifecycle>[0] = {
    session: { project, activePage: "brief", capture: () => ({ epoch, projectId: project.id, stage: "brief" }),
      isCurrent: operation => operation.epoch === epoch, acceptCanonicalProject: vi.fn() },
    currentDraft: { current: undefined }, commitProject: vi.fn(async () => { params.currentDraft.current = undefined; }),
    commitStage: vi.fn(), discardCurrentAuthoringDraft: vi.fn(async () => true), mediaDraftQuiescence: quiescence,
    reviewDraftStore: createReviewDraftStore(quiescence, sessionStorage),
    directory: { open: vi.fn(async () => {}), close: vi.fn(), refresh: vi.fn(async () => {}), setError: vi.fn() },
    openProject: vi.fn(), startBlank: vi.fn(), explicitProjectClose: true, portableSnapshots: true, reportError: vi.fn(),
  };
  const archive = vi.spyOn(plotloomApi, "archiveProject").mockResolvedValue(target as ProjectResource);
  const restore = vi.spyOn(plotloomApi, "restoreProject").mockResolvedValue(target as ProjectResource);
  const snapshot = vi.spyOn(plotloomApi, "createProjectSnapshot").mockResolvedValue({ projectId: project.id } as Awaited<ReturnType<typeof plotloomApi.createProjectSnapshot>>);
  const close = vi.spyOn(plotloomApi, "closeProject").mockResolvedValue({ projectId: project.id, state: "closed", revision: 1 });
  let owner!: ReturnType<typeof useProjectLifecycle>;
  function Probe() { owner = useProjectLifecycle(params); return owner.confirmation; }
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  await act(async () => root.render(createElement(Probe)));
  return { get owner() { return owner; }, params, project, target, quiescence, archive, restore, snapshot, close,
    changeEpoch: () => { epoch++; }, rerender: () => act(async () => root.render(createElement(Probe))),
    dispose: async () => { await act(async () => root.unmount()); host.remove(); } };
}

it("holds one same-tick command through its request and directory refresh", async () => {
  const h = await harness(), request = deferred(), refresh = deferred(); let command!: Promise<void>;
  h.archive.mockImplementation(async () => { await request.promise; return h.target as ProjectResource; });
  vi.mocked(h.params.directory.refresh).mockImplementationOnce(() => refresh.promise);
  try {
    await act(async () => {
      command = h.owner.mutate(h.target, "archive");
      await h.owner.mutate(h.target, "restore"); await h.owner.createSnapshot(); await h.owner.saveAndCloseCurrent();
    });
    expect(h.owner.commandMessage).toContain(`正在归档「${h.project.brief.title}」`);
    expect(h.archive).toHaveBeenCalledOnce(); expect(h.restore).not.toHaveBeenCalled(); expect(h.snapshot).not.toHaveBeenCalled(); expect(h.close).not.toHaveBeenCalled();
    await act(async () => request.resolve());
    expect(h.owner.commandMessage).toContain("正在归档");
    await act(async () => { await h.owner.mutate(h.target, "restore"); refresh.resolve(); await command; });
    expect(h.restore).not.toHaveBeenCalled(); expect(h.owner.commandMessage).toBe("");
    await act(async () => h.owner.mutate(h.target, "restore")); expect(h.restore).toHaveBeenCalledOnce();
  } finally { request.resolve(); refresh.resolve(); await h.dispose(); }
});

it("snapshot owns the same synchronous admission and releases it after setup refusal", async () => {
  const h = await harness(), held = deferred(); let command!: Promise<void>;
  h.snapshot.mockImplementationOnce(async () => { await held.promise; return { projectId: h.project.id } as Awaited<ReturnType<typeof plotloomApi.createProjectSnapshot>>; });
  try {
    await act(async () => { command = h.owner.createSnapshot(); await h.owner.mutate(h.target, "archive"); await h.owner.createSnapshot(); });
    expect(h.snapshot).toHaveBeenCalledOnce(); expect(h.archive).not.toHaveBeenCalled();
    await act(async () => { held.resolve(); await command; });
    vi.spyOn(h.quiescence, "beginClose").mockImplementationOnce(() => { throw new Error("controlled setup refusal"); });
    await act(async () => h.owner.createSnapshot());
    expect(h.params.reportError).toHaveBeenCalledWith("controlled setup refusal");
    expect(h.owner.commandMessage).toBe(""); expect(h.owner.snapshottingProjectId).toBeUndefined();
    await act(async () => h.owner.mutate(h.target, "archive")); expect(h.archive).toHaveBeenCalledOnce();
  } finally { held.resolve(); await h.dispose(); }
});

it.each([false, true])("save-before-archive is owned once and preserves buffers when epoch changes: %s", async changed => {
  const h = await harness(), held = deferred(); let command!: Promise<void>;
  const authored = { ...h.project.brief, title: "Unsent original title" };
  h.params.currentDraft.current = { scope: "brief", payload: authored }; putDraft(h.project, "brief", authored);
  vi.mocked(h.params.commitProject).mockImplementationOnce(async () => { await held.promise; if (!changed) h.params.currentDraft.current = undefined; });
  try {
    await act(async () => h.owner.mutate(h.target, "archive")); expect(h.owner.pendingArchive).toBeDefined();
    await act(async () => { command = h.owner.resolvePendingArchive("save"); await h.owner.resolvePendingArchive("save"); await h.owner.resolvePendingArchive("discard"); await h.owner.createSnapshot(); });
    expect(h.params.commitProject).toHaveBeenCalledOnce(); expect(h.archive).not.toHaveBeenCalled(); expect(h.snapshot).not.toHaveBeenCalled();
    const newer = { scope: "brief" as const, payload: { ...authored, title: "New session input" } };
    if (changed) { h.changeEpoch(); h.params.currentDraft.current = newer; }
    await act(async () => { held.resolve(); await command; });
    expect(h.owner.commandMessage).toBe("");
    if (changed) {
      h.params.session.project = { ...h.project, id: "new-workspace-project" };
      await h.rerender();
      await act(async () => h.owner.resolvePendingArchive("discard"));
      expect(h.archive).not.toHaveBeenCalled(); expect(h.params.currentDraft.current).toBe(newer);
      expect(h.owner.pendingArchive).toBeUndefined();
      expect(h.params.directory.setError).toHaveBeenCalledTimes(1);
    }
    else { expect(h.archive).toHaveBeenCalledOnce(); expect(h.owner.pendingArchive).toBeUndefined(); }
  } finally { held.resolve(); await h.dispose(); }
});

it("failed save keeps the decision and buffer; cancelled/capability no-ops do not take ownership", async () => {
  const h = await harness();
  const authored = { ...h.project.brief, title: "Retained after failed save" };
  h.params.currentDraft.current = { scope: "brief", payload: authored }; putDraft(h.project, "brief", authored);
  vi.mocked(h.params.commitProject).mockImplementationOnce(async () => {});
  try {
    await act(async () => h.owner.mutate(h.target, "archive"));
    await act(async () => h.owner.resolvePendingArchive("save"));
    expect(h.owner.pendingArchive).toBeDefined(); expect(h.params.currentDraft.current?.payload).toEqual(authored); expect(h.archive).not.toHaveBeenCalled();
    await act(async () => h.owner.resolvePendingArchive("cancel")); expect(h.owner.commandMessage).toBe("");
    h.params.explicitProjectClose = false;
    await h.rerender();
    await act(async () => h.owner.mutate(h.target, "open"));
    expect(h.params.directory.setError).toHaveBeenCalledTimes(1); expect(h.close).not.toHaveBeenCalled();
  } finally { await h.dispose(); }
});

it("late archive settlement releases ownership without publishing stale UI", async () => {
  const h = await harness(), held = deferred(); let command!: Promise<void>;
  h.archive.mockImplementationOnce(async () => { await held.promise; return h.target as ProjectResource; });
  try {
    await act(async () => { command = h.owner.mutate(h.target, "archive"); });
    h.changeEpoch();
    await act(async () => { held.resolve(); await command; });
    expect(h.params.session.acceptCanonicalProject).not.toHaveBeenCalled(); expect(h.params.directory.refresh).not.toHaveBeenCalled(); expect(h.owner.commandMessage).toBe("");
    await act(async () => h.owner.mutate(h.target, "restore")); expect(h.restore).toHaveBeenCalledOnce();
  } finally { held.resolve(); await h.dispose(); }
});
