import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { ApiError, plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { getDraft, putDraft } from "../src/draft-registry";
import { useAuthoringDraftAutosave } from "../src/features/authoring/useAuthoringDraftAutosave";
import type { AuthoringDraft } from "../src/types";
import type { WorkspaceOperation } from "../src/app/workspace/contracts";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); sessionStorage.clear(); });

async function harness(initiallyAllowed = true) {
  let project = { ...demoProject, id: "a" }, allowed = initiallyAllowed;
  const serverAuthoringDrafts = { current: new Map<string, AuthoringDraft>() };
  const onConflict = vi.fn();
  let autosave!: ReturnType<typeof useAuthoringDraftAutosave>;
  function Harness() {
    autosave = useAuthoringDraftAutosave({ project, writesAllowed: allowed,
      durableDraftsEnabledRef: { current: true }, serverAuthoringDrafts,
      captureWorkspaceOperation: (): WorkspaceOperation => ({ projectId: project.id, epoch: 1, stage: "brief" }),
      isWorkspaceOperationCurrent: operation => operation.projectId === project.id,
      setDurableDraftStatus: vi.fn(), setError: vi.fn(), onConflict });
    return null;
  }
  const root = createRoot(document.createElement("div"));
  const render = () => act(async () => root.render(createElement(Harness)));
  await render();
  return { get autosave() { return autosave; }, get project() { return project; }, onConflict,
    setAllowed: async (value: boolean) => { allowed = value; await render(); },
    replaceProject: async () => { project = { ...project, id: "b" }; await render(); },
    unmount: () => act(async () => root.unmount()) };
}

it("halts timer and explicit flush writes while project authority is unverified", async () => {
  vi.useFakeTimers();
  const state = await harness(false), write = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  const retained = putDraft(state.project, "brief", { title: "exact retained input" });
  try {
    state.autosave.scheduleAuthoringDraftAutosave("brief");
    await vi.advanceTimersByTimeAsync(1000);
    await expect(state.autosave.flushAuthoringDraft("brief")).resolves.toBe(false);
    expect(write).not.toHaveBeenCalled(); expect(getDraft(state.project, "brief")).toEqual(retained);
  } finally { await state.unmount(); }
});

it("a timer armed before loss of authority cannot write after it", async () => {
  vi.useFakeTimers();
  const state = await harness(), write = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  try {
    putDraft(state.project, "brief", { title: "retained" });
    state.autosave.scheduleAuthoringDraftAutosave("brief"); await state.setAllowed(false);
    await vi.advanceTimersByTimeAsync(1000); expect(write).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it("409 stops same-event blur retries until the owning workflow explicitly resolves the conflict", async () => {
  const state = await harness(), write = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockRejectedValueOnce(new ApiError("conflict", 409));
  const retained = putDraft(state.project, "brief", { title: "retained conflict" });
  try {
    await expect(state.autosave.flushAuthoringDraft("brief")).resolves.toBe(false);
    await expect(state.autosave.flushAuthoringDraft("brief")).resolves.toBe(false);
    expect(write).toHaveBeenCalledOnce(); expect(state.onConflict).toHaveBeenCalledExactlyOnceWith("brief", retained, state.project);
    await state.setAllowed(false); await expect(state.autosave.flushAuthoringDraft("brief")).resolves.toBe(false);
    expect(getDraft(state.project, "brief")).toEqual(retained);
    write.mockResolvedValue({ projectId: "a", editorScope: "brief", entityId: "root", baseCanonicalRevision: state.project.revision,
      draftRevision: 1, payload: retained.payload as Record<string, unknown>, updatedAt: "2026-10-08" });
    await state.setAllowed(true); await expect(state.autosave.flushAuthoringDraft("brief")).resolves.toBe(true);
    expect(write).toHaveBeenCalledTimes(2); expect(getDraft(state.project, "brief")).toBeUndefined();
  } finally { await state.unmount(); }
});

it("a stale project callback cannot write after another project owns the session", async () => {
  const state = await harness(), write = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  const staleFlush = state.autosave.flushAuthoringDraft;
  try {
    putDraft(state.project, "brief", { title: "old project input" }); await state.replaceProject();
    await expect(staleFlush("brief")).resolves.toBe(false); expect(write).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it("a held save409 retains newer typing as the conflict rather than the rejected request snapshot", async () => {
  const state = await harness();
  let reject!: (error: Error) => void;
  const write = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockReturnValue(new Promise((_resolve, fail) => { reject = fail; }));
  try {
    putDraft(state.project, "brief", { title: "First submitted text" });
    const pending = state.autosave.flushAuthoringDraft("brief"); expect(write).toHaveBeenCalledOnce();
    const newer = putDraft(state.project, "brief", { title: "Newer retained typing" });
    reject(new ApiError("conflict", 409)); await expect(pending).resolves.toBe(false);
    expect(state.onConflict).toHaveBeenCalledExactlyOnceWith("brief", newer, state.project);
    expect(getDraft(state.project, "brief")).toEqual(newer);
  } finally { await state.unmount(); }
});
