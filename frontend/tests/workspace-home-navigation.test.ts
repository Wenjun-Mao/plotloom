import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { blankWorkspace } from "../src/app/workspace/contracts";
import { useWorkspaceNavigation } from "../src/app/workspace/useWorkspaceNavigation";
import { putDraft } from "../src/draft-registry";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => window.sessionStorage.clear());

async function harness({ persisted = false, durable = false, closing = false } = {}) {
  const project = { ...blankWorkspace("home-test"), ...(persisted ? { id: "project-a", revision: 1 } : {}) };
  const session = {
    project, activePage: "brief", connection: persisted ? "connected" : "blank",
    routeRef: { current: { project: project.id || "", stage: "brief", entity: "", run: "", hash: "" } },
    clearForEmptyRoute: vi.fn(), navigate: vi.fn(), navigateToProject: vi.fn(),
    setUnsafeDraft: vi.fn(), needsCanonicalRefresh: () => false,
    run: { id: "run-a", projectId: "project-a", status: "running" },
  };
  const drafts = {
    current: { current: undefined as { scope: "brief"; payload: unknown } | undefined },
    durableEnabled: { current: durable }, flush: vi.fn().mockResolvedValue(true),
    clearRecovery: vi.fn(), clearConflict: vi.fn(), commitProject: vi.fn(), commitStage: vi.fn(),
  };
  const loadProject = vi.fn(); const pollRun = vi.fn();
  let navigation!: ReturnType<typeof useWorkspaceNavigation>;
  function Harness() {
    navigation = useWorkspaceNavigation({ session, drafts, loadProject, pollRun, isProjectClosing: () => closing } as never);
    return null;
  }
  const root = createRoot(document.createElement("div"));
  await act(async () => root.render(createElement(Harness)));
  return {
    session, drafts, loadProject, pollRun, get navigation() { return navigation; },
    home: () => act(async () => navigation.requestNavigation({ project: "", stage: "brief", home: true })),
    unmount: () => act(async () => root.unmount()),
  };
}

it("admits explicit Home even when a clean local workspace already has the empty brief route", async () => {
  const state = await harness();
  try {
    await state.home();
    expect(state.session.clearForEmptyRoute).toHaveBeenCalledExactlyOnceWith(
      { project: "", stage: "brief", entity: "", run: "", hash: "" }, "push",
    );
    expect(state.loadProject).not.toHaveBeenCalled();
    expect(state.pollRun).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it("keeps ordinary local page navigation distinct from Home", async () => {
  const state = await harness();
  try {
    await act(async () => state.navigation.requestNavigation({ project: "", stage: "bible" }));
    expect(state.session.navigate).toHaveBeenCalledOnce();
    expect(state.session.clearForEmptyRoute).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it("retains unsaved local typing when Home is cancelled", async () => {
  const state = await harness();
  const payload = { ...state.session.project.brief, title: "尚未保存的片名" };
  putDraft(state.session.project, "brief", payload);
  state.drafts.current.current = { scope: "brief", payload };
  try {
    await state.home();
    expect(state.navigation.pendingNavigation).toMatchObject({ home: true });
    expect(state.session.clearForEmptyRoute).not.toHaveBeenCalled();
    await act(async () => state.navigation.resolvePendingNavigation("cancel"));
    expect(state.navigation.pendingNavigation).toBeUndefined();
    expect(state.drafts.current.current?.payload).toEqual(payload);
    expect(state.session.clearForEmptyRoute).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it.each([true, false])("waits for durable draft admission before Home: saved=%s", async (saved) => {
  const state = await harness({ persisted: true, durable: true });
  putDraft(state.session.project, "brief", { ...state.session.project.brief, title: "项目中的草稿" });
  let release!: (value: boolean) => void;
  state.drafts.flush.mockImplementation(() => new Promise<boolean>(resolve => { release = resolve; }));
  try {
    await state.home();
    expect(state.session.clearForEmptyRoute).not.toHaveBeenCalled();
    await act(async () => release(saved));
    expect(state.session.clearForEmptyRoute).toHaveBeenCalledTimes(saved ? 1 : 0);
    expect(Boolean(state.navigation.pendingNavigation)).toBe(!saved);
    expect(state.pollRun).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it("does not detach a project during its admitted Close or Delete", async () => {
  const state = await harness({ persisted: true, closing: true });
  try {
    await state.home();
    expect(state.session.clearForEmptyRoute).not.toHaveBeenCalled();
    expect(state.navigation.pendingNavigation).toBeUndefined();
  } finally { await state.unmount(); }
});
