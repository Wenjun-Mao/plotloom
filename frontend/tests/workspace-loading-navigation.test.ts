import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { useWorkspaceNavigation } from "../src/app/workspace/useWorkspaceNavigation";
import type { RunStatus } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("replaces a cancelled project load when returning to the still-displayed project", async () => {
  const loadProject = vi.fn().mockResolvedValue(undefined);
  const session = {
    project: { id: "a" }, connection: "loading", activePage: "source",
    routeRef: { current: { project: "b", stage: "source", entity: "", run: "", hash: "" } },
    navigateToProject: vi.fn(() => 3), needsCanonicalRefresh: () => false,
    cancelRunSelection: vi.fn(), setUnsafeDraft: vi.fn(),
  };
  const drafts = { current: { current: undefined }, clearRecovery: vi.fn(), clearConflict: vi.fn() };
  let navigation!: ReturnType<typeof useWorkspaceNavigation>;
  function Harness() {
    navigation = useWorkspaceNavigation({ session, drafts, loadProject, pollRun: vi.fn(), isProjectClosing: () => false } as never);
    return null;
  }
  const root = createRoot(document.createElement("div"));
  try {
    await act(async () => root.render(createElement(Harness)));
    await act(async () => navigation.requestNavigation({ project: "a", stage: "source" }));
    expect(session.navigateToProject).toHaveBeenCalledTimes(1);
    expect(loadProject).toHaveBeenCalledWith("a", 3);
  } finally { await act(async () => root.unmount()); }
});

async function activeRunNavigation({
  status = "running", runProject = "a", pending = false, refresh = false,
}: { status?: RunStatus; runProject?: string; pending?: boolean; refresh?: boolean } = {}) {
  const loadProject = vi.fn().mockResolvedValue(undefined);
  const pollRun = vi.fn().mockResolvedValue(undefined);
  const session = {
    project: { id: "a" }, connection: "connected", activePage: "trace",
    run: { id: "run-a", projectId: runProject, status }, runSelectionPending: pending,
    routeRef: { current: { project: "a", stage: "trace", entity: "", run: "run-a", hash: "" } },
    navigateToProject: vi.fn((route) => { session.routeRef.current = route; return 4; }),
    needsCanonicalRefresh: () => refresh, beginRunSelection: vi.fn(),
    cancelRunSelection: vi.fn(), setUnsafeDraft: vi.fn(),
  };
  const drafts = { current: { current: undefined }, clearRecovery: vi.fn(), clearConflict: vi.fn() };
  let navigation!: ReturnType<typeof useWorkspaceNavigation>;
  function Harness() {
    navigation = useWorkspaceNavigation({ session, drafts, loadProject, pollRun, isProjectClosing: () => false } as never);
    return null;
  }
  const root = createRoot(document.createElement("div"));
  await act(async () => root.render(createElement(Harness)));
  return { navigation, session, loadProject, pollRun, unmount: async () => act(async () => root.unmount()) };
}

it.each(["queued", "running", "cancel_requested"] as const)(
  "continues observing a same-project %s run under the new navigation epoch",
  async (status) => {
    const state = await activeRunNavigation({ status });
    try {
      await act(async () => state.navigation.requestNavigation({ project: "a", stage: "quarantine" }));
      expect(state.session.routeRef.current.stage).toBe("quarantine");
      expect(state.pollRun).toHaveBeenCalledExactlyOnceWith("run-a", "a");
      expect(state.session.navigateToProject.mock.invocationCallOrder[0]).toBeLessThan(state.pollRun.mock.invocationCallOrder[0]);
      expect(state.loadProject).not.toHaveBeenCalled();
    } finally { await state.unmount(); }
  },
);

it.each(["succeeded", "quarantined", "cancelled", "failed"] as const)(
  "does not restart observation for a %s run while navigating",
  async (status) => {
    const state = await activeRunNavigation({ status });
    try {
      await act(async () => state.navigation.requestNavigation({ project: "a", stage: "quarantine" }));
      expect(state.pollRun).not.toHaveBeenCalled();
      expect(state.loadProject).not.toHaveBeenCalled();
    } finally { await state.unmount(); }
  },
);

it("does not observe a retained run belonging to another project", async () => {
  const state = await activeRunNavigation({ runProject: "b" });
  try {
    await act(async () => state.navigation.requestNavigation({ project: "a", stage: "quarantine" }));
    expect(state.pollRun).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it.each([{ refresh: true }, { pending: true }])("leaves canonical refresh and cancelled trace selection with their existing owners: %j", async (options) => {
  const state = await activeRunNavigation(options);
  try {
    await act(async () => state.navigation.requestNavigation({ project: "a", stage: "quarantine" }));
    expect(state.pollRun).not.toHaveBeenCalled();
    if (options.refresh) expect(state.loadProject).toHaveBeenCalledExactlyOnceWith("a", 4);
    else expect(state.session.cancelRunSelection).toHaveBeenCalledOnce();
  } finally { await state.unmount(); }
});

it("loads the destination project instead of transferring the previous project's observer", async () => {
  const state = await activeRunNavigation();
  try {
    await act(async () => state.navigation.requestNavigation({ project: "b", stage: "quarantine" }));
    expect(state.pollRun).not.toHaveBeenCalled();
    expect(state.loadProject).toHaveBeenCalledExactlyOnceWith("b", 4);
  } finally { await state.unmount(); }
});
