import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { useDraftConflictReload } from "../src/app/workspace/useDraftConflictReload";
import type { DraftConflictState } from "../src/app/workspace/useProjectAuthoringPersistence";
import type { ProjectLoadResult, WorkspaceOperation } from "../src/app/workspace/contracts";
import { demoProject } from "../src/demo";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const makeConflict = (title = "retained author input"): DraftConflictState => ({
  scope: "brief", serverReloaded: false, workspace: { ...demoProject, id: "a" },
  record: { key: "a:brief:1", projectId: "a", scope: "brief", baseRevision: 1,
    serverDraftRevision: 0, localRevision: 1, payload: { ...demoProject.brief, title }, updatedAt: "2026-10-08" },
});
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }

async function harness() {
  let epoch = 0, conflict: DraftConflictState | undefined = makeConflict();
  const cleanups = new Set<() => void>();
  const reloadCanonicalProject = vi.fn<(id: string, epoch?: number) => Promise<ProjectLoadResult>>();
  const onLoaded = vi.fn();
  const session = {
    project: { ...demoProject, id: "a" }, capture: (): WorkspaceOperation => ({ projectId: "a", stage: "brief", epoch }),
    isCurrent: (operation: WorkspaceOperation) => operation.epoch === epoch,
    refreshCurrentRoute: () => { epoch++; cleanups.forEach(cleanup => cleanup()); return epoch; },
    reloadCanonicalProject,
    registerNavigationCleanup: (cleanup: () => void) => { cleanups.add(cleanup); return () => { cleanups.delete(cleanup); }; },
  };
  let controller!: ReturnType<typeof useDraftConflictReload>;
  function Harness() { controller = useDraftConflictReload({ conflict, session, onLoaded }); return null; }
  const root = createRoot(document.createElement("div"));
  const render = () => act(async () => root.render(createElement(Harness)));
  await render();
  return { get controller() { return controller; }, get conflict() { return conflict; }, session, reloadCanonicalProject, onLoaded,
    replace: async () => { conflict = makeConflict("newer conflict"); await render(); },
    unmount: () => act(async () => root.unmount()) };
}

it.each(["failed", "superseded"] as const)("preserves the exact conflict after %s and permits an explicit owned retry", async result => {
  const state = await harness(), read = deferred<ProjectLoadResult>();
  try {
    state.reloadCanonicalProject.mockReturnValueOnce(read.promise).mockResolvedValueOnce("loaded");
    let pending!: Promise<boolean>;
    await act(async () => { pending = state.controller.reload(); });
    expect(state.controller.reloading).toBe(true); expect(state.controller.isPending()).toBe(true);
    expect(state.onLoaded).not.toHaveBeenCalled();
    await expect(state.controller.reload()).resolves.toBe(false);
    expect(state.reloadCanonicalProject).toHaveBeenCalledOnce();
    await act(async () => { read.resolve(result); expect(await pending).toBe(false); });
    expect(state.onLoaded).not.toHaveBeenCalled(); expect(state.controller.reloading).toBe(false);
    expect(state.conflict?.record.payload).toMatchObject({ title: "retained author input" });
    await act(async () => { expect(await state.controller.reload()).toBe(true); });
    expect(state.onLoaded).toHaveBeenCalledExactlyOnceWith(state.conflict);
  } finally { await state.unmount(); }
});

it.each(["navigate", "replace"] as const)("does not acknowledge a late loaded result after %s", async action => {
  const state = await harness(), read = deferred<ProjectLoadResult>();
  try {
    state.reloadCanonicalProject.mockReturnValueOnce(read.promise);
    let pending!: Promise<boolean>;
    await act(async () => { pending = state.controller.reload(); });
    if (action === "navigate") await act(async () => { state.session.refreshCurrentRoute(); });
    else await state.replace();
    await act(async () => { read.resolve("loaded"); expect(await pending).toBe(false); });
    expect(state.onLoaded).not.toHaveBeenCalled(); expect(state.controller.reloading).toBe(false);
  } finally { await state.unmount(); }
});

it("a superseded completion cannot clear the pending owner of a newer conflict", async () => {
  const state = await harness(), older = deferred<ProjectLoadResult>(), newer = deferred<ProjectLoadResult>();
  try {
    state.reloadCanonicalProject.mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    let first!: Promise<boolean>, second!: Promise<boolean>;
    await act(async () => { first = state.controller.reload(); }); await state.replace();
    await act(async () => { second = state.controller.reload(); });
    await act(async () => { older.resolve("loaded"); expect(await first).toBe(false); });
    expect(state.controller.reloading).toBe(true); expect(state.onLoaded).not.toHaveBeenCalled();
    await act(async () => { newer.resolve("loaded"); expect(await second).toBe(true); });
    expect(state.onLoaded).toHaveBeenCalledExactlyOnceWith(state.conflict);
  } finally { await state.unmount(); }
});
