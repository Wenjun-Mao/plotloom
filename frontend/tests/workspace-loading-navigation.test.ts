import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { useWorkspaceNavigation } from "../src/app/workspace/useWorkspaceNavigation";

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
