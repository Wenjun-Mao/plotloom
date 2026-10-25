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
  let epoch = 0, routeProjectId = project.id;
  const params: Parameters<typeof useProjectLifecycle>[0] = {
    session: { project, activePage: "brief", capture: () => ({ epoch, projectId: routeProjectId, stage: "brief" }),
      isCurrent: operation => operation.epoch === epoch && operation.projectId === routeProjectId, acceptCanonicalProject: vi.fn() },
    currentDraft: { current: undefined }, commitProject: vi.fn(async () => { params.currentDraft.current = undefined; }),
    commitStage: vi.fn(), discardCurrentAuthoringDraft: vi.fn(async () => true), mediaDraftQuiescence: quiescence,
    reviewDraftStore: createReviewDraftStore(quiescence, sessionStorage),
    directory: { open: vi.fn(async () => {}), close: vi.fn(), refresh: vi.fn(async () => {}), setError: vi.fn() },
    openProject: vi.fn(), startBlank: vi.fn(), explicitProjectClose: true, portableSnapshots: true, reportError: vi.fn(),
  };
  const archive = vi.spyOn(plotloomApi, "archiveProject").mockResolvedValue(target as ProjectResource);
  const restore = vi.spyOn(plotloomApi, "restoreProject").mockResolvedValue(target as ProjectResource);
  const snapshot = vi.spyOn(plotloomApi, "createProjectSnapshot").mockResolvedValue({ projectId: project.id } as Awaited<ReturnType<typeof plotloomApi.createProjectSnapshot>>);
  const close = vi.spyOn(plotloomApi, "freezeProject").mockResolvedValue({ projectId: project.id, state: "closed", revision: 1 });
  let owner!: ReturnType<typeof useProjectLifecycle>;
  function Probe() { owner = useProjectLifecycle(params); return owner.confirmation; }
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  await act(async () => root.render(createElement(Probe)));
  return { get owner() { return owner; }, params, project, target, quiescence, archive, restore, snapshot, close,
    changeEpoch: () => { epoch++; }, changeRoute: (id: string) => { routeProjectId = id; epoch++; }, rerender: () => act(async () => root.render(createElement(Probe))),
    dispose: async () => { await act(async () => root.unmount()); host.remove(); } };
}

it("holds one same-tick command through its request and directory refresh", async () => {
  const h = await harness(), request = deferred(), refresh = deferred(); let command!: Promise<void>;
  h.archive.mockImplementation(async () => { await request.promise; return h.target as ProjectResource; });
  vi.mocked(h.params.directory.refresh).mockImplementationOnce(() => refresh.promise);
  try {
    await act(async () => {
      command = h.owner.mutate(h.target, "archive");
      await h.owner.mutate(h.target, "restore"); await h.owner.createSnapshot(); await h.owner.mutate(h.target, "freeze");
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


it("Freeze drains drafts without Apply, settles reads and retains the current workspace", async () => {
  const h = await harness();
  const flush = vi.fn(async () => true);
  h.quiescence.register(h.project.id, "unfinished", flush);
  try {
    await act(async () => h.owner.mutate(h.target, "freeze"));
    expect(flush).toHaveBeenCalledOnce(); expect(h.close).toHaveBeenCalledOnce();
    expect(h.params.commitProject).not.toHaveBeenCalled(); expect(h.params.commitStage).not.toHaveBeenCalled();
    expect(h.params.startBlank).not.toHaveBeenCalled();
    expect(h.params.session.acceptCanonicalProject).toHaveBeenCalledWith(expect.objectContaining({ operationalState: "closed" }));
    expect(h.quiescence.canWrite(h.project.id)).toBe(false);
  } finally { await h.dispose(); }
});

it("Freeze refusal retains journals and releases client admission without force exit", async () => {
  const h = await harness();
  h.quiescence.register(h.project.id, "unsynced", async () => false, { locallyPreserved: () => true, pending: () => true });
  try {
    await act(async () => h.owner.mutate(h.target, "freeze"));
    expect(h.close).not.toHaveBeenCalled(); expect(h.params.startBlank).not.toHaveBeenCalled();
    expect(h.params.directory.setError).toHaveBeenCalledWith(expect.stringContaining("尚未同步"));
    expect(h.quiescence.isClosing(h.project.id)).toBe(false);
    expect(await h.quiescence.preserve(h.project.id)).toBe(true);
  } finally { await h.dispose(); }
});

it("Archive preserves working input without canonically applying it", async () => {
  const h = await harness(), flush = vi.fn(async () => true);
  h.quiescence.register(h.project.id, "author", flush);
  try {
    await act(async () => h.owner.mutate(h.target, "archive"));
    expect(flush).toHaveBeenCalledOnce(); expect(h.archive).toHaveBeenCalledOnce();
    expect(h.params.commitProject).not.toHaveBeenCalled(); expect(h.params.commitStage).not.toHaveBeenCalled();
    expect("pendingArchive" in h.owner).toBe(false);
  } finally { await h.dispose(); }
});
