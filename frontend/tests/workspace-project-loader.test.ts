import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { ApiError, plotloomApi } from "../src/api";
import { demoProject, demoRun } from "../src/demo";
import { useWorkspaceProjectLoader } from "../src/app/workspace/useWorkspaceProjectLoader";
import type { ProjectResource, RunProgress } from "../src/types";
import type { ProjectLoadResult, WorkspaceOperation } from "../src/app/workspace/contracts";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); window.sessionStorage.clear(); });
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }
const project = { id: "a", revision: 1, brief: demoProject.brief, createdAt: "2026-10-08", updatedAt: "2026-10-08",
  lifecycleRevision: 1, lifecycleStatus: "active", archivedAt: null } satisfies ProjectResource;

async function harness(apiTextPipeline = true) {
  let epoch = 1;
  const cleanups = new Set<() => void>();
  const session = {
    capture: (): WorkspaceOperation => ({ projectId: "a", stage: "brief", epoch }),
    isCurrent: (operation: WorkspaceOperation) => operation.epoch === epoch,
    routeRef: { current: { project: "a", stage: "brief" as const, entity: "", run: "", hash: "" } },
    beginProjectLoad: vi.fn(), acceptProjectLoad: vi.fn(), clearCanonicalRefresh: vi.fn(), rejectProjectLoad: vi.fn(),
    registerCanonicalReloader: vi.fn(() => () => {}),
    registerNavigationCleanup: (cleanup: () => void) => { cleanups.add(cleanup); return () => { cleanups.delete(cleanup); }; },
  };
  vi.spyOn(plotloomApi, "getProject").mockResolvedValue(project);
  vi.spyOn(plotloomApi, "getStages").mockResolvedValue({ stages: [] });
  vi.spyOn(plotloomApi, "getProjectRuns").mockResolvedValue({ runs: [] });
  vi.spyOn(plotloomApi, "getProjectMediaTasks").mockResolvedValue({ tasks: [] });
  const reportMessage = vi.fn();
  const observeRun = vi.fn();
  let loader!: ReturnType<typeof useWorkspaceProjectLoader>;
  function Harness() { loader = useWorkspaceProjectLoader({ session, apiTextPipeline: { current: apiTextPipeline }, durableDrafts: { current: false },
    profiles: { loaded: { current: true }, catalog: { current: { profiles: [] } }, refresh: vi.fn() }, observeRun, reportMessage }); return null; }
  const root = createRoot(document.createElement("div"));
  await act(async () => root.render(createElement(Harness)));
  return { loader, session, reportMessage, observeRun, navigate: () => { epoch++; cleanups.forEach(cleanup => cleanup()); },
    unmount: () => act(async () => root.unmount()) };
}

it.each(["failed", "queued", "running", "cancel_requested"] as const)("loads a retained native %s run summary without absent progress or credential routes", async status => {
  const state = await harness(false);
  const progress = vi.spyOn(plotloomApi, "getRunProgress");
  const profiles = vi.spyOn(plotloomApi, "getTextProviderProfiles");
  const resume = vi.spyOn(plotloomApi, "resumeRun");
  const run = { ...demoRun, projectId: "a", status };
  vi.mocked(plotloomApi.getProjectRuns).mockResolvedValue({ runs: [run] });
  state.session.routeRef.current.run = run.id;
  try {
    await expect(state.loader.loadProject("a")).resolves.toBe("loaded");
    expect(state.session.acceptProjectLoad).toHaveBeenCalledWith(expect.objectContaining({ run, progress: undefined }));
    expect(state.session.rejectProjectLoad).not.toHaveBeenCalled();
    expect(progress).not.toHaveBeenCalled(); expect(profiles).not.toHaveBeenCalled();
    expect(resume).not.toHaveBeenCalled(); expect(state.observeRun).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it("acknowledges only an admitted aggregate and refuses mismatched route requests", async () => {
  const state = await harness();
  try {
    await expect(state.loader.loadProject("b")).resolves.toBe("superseded");
    await expect(state.loader.loadProject("a", 2)).resolves.toBe("superseded");
    expect(plotloomApi.getProject).not.toHaveBeenCalled();
    await expect(state.loader.loadProject("a", 1)).resolves.toBe("loaded");
    expect(state.session.acceptProjectLoad).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ project }));
  } finally { await state.unmount(); }
});

it.each(["resolve", "reject"] as const)("does not publish an older held Resume %s after a same-route replacement read", async outcome => {
  const state = await harness();
  let resolve!: (value: typeof demoRun) => void, reject!: (error: Error) => void;
  const resumed = new Promise<typeof demoRun>((done, fail) => { resolve = done; reject = fail; });
  try {
    vi.mocked(plotloomApi.getProjectRuns).mockResolvedValueOnce({ runs: [{ ...demoRun, projectId: "a", status: "running",
      providerSnapshot: { ...demoRun.providerSnapshot, textAuthMode: "none" } }] });
    vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue({} as RunProgress);
    vi.spyOn(plotloomApi, "resumeRun").mockReturnValueOnce(resumed);
    await expect(state.loader.loadProject("a")).resolves.toBe("loaded");
    expect(plotloomApi.resumeRun).toHaveBeenCalledOnce();
    await expect(state.loader.loadProject("a")).resolves.toBe("loaded");
    await act(async () => { if (outcome === "resolve") resolve(demoRun); else reject(new ApiError("old continuation failed", 503)); });
    expect(state.session.acceptProjectLoad).toHaveBeenCalledTimes(2);
    expect(state.session.rejectProjectLoad).not.toHaveBeenCalled();
    expect(state.observeRun).not.toHaveBeenCalled(); expect(state.reportMessage).toHaveBeenCalledTimes(2);
  } finally { await state.unmount(); }
});

it.each([404, 503])("reports a current HTTP%s read as failed, not loaded", async status => {
  const state = await harness();
  try {
    vi.mocked(plotloomApi.getProject).mockRejectedValue(new ApiError("authority failure", status));
    await expect(state.loader.loadProject("a")).resolves.toBe("failed");
    expect(state.session.acceptProjectLoad).not.toHaveBeenCalled(); expect(state.session.rejectProjectLoad).toHaveBeenCalledOnce();
    expect(state.session.rejectProjectLoad).toHaveBeenCalledWith(undefined, {
      projectId: "a", kind: status === 404 ? "missing" : "unavailable", diagnostic: "authority failure",
    });
  } finally { await state.unmount(); }
});

it("distinguishes a current Resume503 after admitted reads without discarding their snapshot", async () => {
  const state = await harness();
  try {
    vi.mocked(plotloomApi.getProjectRuns).mockResolvedValue({runs: [{...demoRun, projectId: "a", status: "running",
      providerSnapshot: {...demoRun.providerSnapshot, textAuthMode: "none"}}]});
    vi.spyOn(plotloomApi, "getRunProgress").mockResolvedValue({} as RunProgress);
    vi.spyOn(plotloomApi, "resumeRun").mockRejectedValue(new ApiError("resume transport unavailable", 503));
    await act(async () => {await expect(state.loader.loadProject("a")).resolves.toBe("loaded");});
    expect(state.session.acceptProjectLoad).toHaveBeenCalledOnce();
    expect(state.session.rejectProjectLoad).toHaveBeenCalledWith(undefined, {
      projectId: "a", kind: "continuation-failed", diagnostic: "resume transport unavailable",
    });
    expect(state.reportMessage).toHaveBeenLastCalledWith(expect.stringContaining("项目已读入，当前内容仍保留"));
    expect(state.reportMessage.mock.lastCall?.[0]).not.toContain("读取未完成");
    expect(state.observeRun).not.toHaveBeenCalled();
  } finally {await state.unmount();}
});

it.each(["closed", "aggregate-404", "network"])("classifies %s without inventing missing-project authority", async kind => {
  const state = await harness();
  try {
    const error = kind === "closed" ? new ApiError("project is closed", 409, {code: "project_closed"})
      : kind === "aggregate-404" ? new ApiError("stages not found", 404) : new Error("offline");
    if (kind === "aggregate-404") vi.mocked(plotloomApi.getStages).mockRejectedValue(error);
    else vi.mocked(plotloomApi.getProject).mockRejectedValue(error);
    await expect(state.loader.loadProject("a")).resolves.toBe("failed");
    expect(state.session.rejectProjectLoad).toHaveBeenCalledWith(undefined, expect.objectContaining({
      projectId: "a", kind: kind === "closed" ? "closed" : "unavailable",
    }));
    expect(state.session.acceptProjectLoad).not.toHaveBeenCalled();
    expect(state.observeRun).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it("does not publish a late closed rejection after navigation", async () => {
  const state = await harness();
  let reject!: (error: Error) => void;
  try {
    vi.mocked(plotloomApi.getProject).mockReturnValue(new Promise((_, fail) => { reject = fail; }));
    const pending = state.loader.loadProject("a");
    state.navigate();
    reject(new ApiError("project is closed", 409, {code: "project_closed"}));
    await expect(pending).resolves.toBe("superseded");
    expect(state.session.rejectProjectLoad).not.toHaveBeenCalled();
    expect(state.reportMessage).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it.each(["replace", "navigate", "abort"] as const)("supersedes a signal-independent progress read on %s without stale admission/error publication", async action => {
  const state = await harness(), progress = deferred<RunProgress>();
  try {
    vi.mocked(plotloomApi.getProjectRuns).mockResolvedValueOnce({ runs: [{ ...demoRun, projectId: "a", status: "succeeded" }] });
    const readProgress = vi.spyOn(plotloomApi, "getRunProgress").mockReturnValueOnce(progress.promise);
    let pending!: Promise<ProjectLoadResult>;
    await act(async () => { pending = state.loader.loadProject("a"); });
    expect(readProgress).toHaveBeenCalledOnce();
    if (action === "replace") await expect(state.loader.loadProject("a")).resolves.toBe("loaded");
    else if (action === "navigate") state.navigate(); else state.loader.abort();
    progress.resolve({} as RunProgress);
    await expect(pending).resolves.toBe("superseded");
    expect(state.session.acceptProjectLoad).toHaveBeenCalledTimes(action === "replace" ? 1 : 0);
    expect(state.session.rejectProjectLoad).not.toHaveBeenCalled();
    expect(state.reportMessage).toHaveBeenCalledTimes(action === "replace" ? 1 : 0);
  } finally { await state.unmount(); }
});
