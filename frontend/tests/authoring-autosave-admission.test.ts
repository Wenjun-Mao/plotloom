import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { ApiError, plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { getDraft, putDraft } from "../src/draft-registry";
import { useAuthoringDraftAutosave } from "../src/features/authoring/useAuthoringDraftAutosave";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import type { AuthoringDraft } from "../src/types";
import type { WorkspaceOperation } from "../src/app/workspace/contracts";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); sessionStorage.clear(); localStorage.clear(); });

async function harness(initiallyAllowed = true) {
  let project = { ...demoProject, id: "a" }, allowed = initiallyAllowed, graphAllowed = true;
  let epoch = 1;
  const serverAuthoringDrafts = { current: new Map<string, AuthoringDraft>() };
  const onConflict = vi.fn();
  const onMutationAcknowledged = vi.fn();
  let autosave!: ReturnType<typeof useAuthoringDraftAutosave>;
  function Harness() {
    autosave = useAuthoringDraftAutosave({ project, writesAllowed: allowed,
      scopeWritesAllowed: scope => scope !== "story_graph" || graphAllowed,
      durableDraftsEnabledRef: { current: true }, serverAuthoringDrafts,
      captureWorkspaceOperation: (): WorkspaceOperation => ({ projectId: project.id, epoch, stage: "brief" }),
      isWorkspaceOperationCurrent: operation => operation.projectId === project.id && operation.epoch === epoch,
      setDurableDraftStatus: vi.fn(), setError: vi.fn(), onConflict, onMutationAcknowledged });
    return null;
  }
  const root = createRoot(document.createElement("div"));
  const render = () => act(async () => root.render(createElement(Harness)));
  await render();
  return { get autosave() { return autosave; }, get project() { return project; }, onConflict, onMutationAcknowledged,
    setAllowed: async (value: boolean) => { allowed = value; await render(); },
    setGraphAllowed: (value: boolean) => { graphAllowed = value; },
    replaceProject: async () => { project = { ...project, id: "b" }; await render(); },
    replaceOperation: async () => { epoch++; await render(); },
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

it("observes a successful current draft PUT only after its owned receipt arrives", async () => {
  const state = await harness();
  let resolve!: (value: AuthoringDraft) => void;
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockReturnValue(new Promise(done => { resolve = done; }));
  const local = putDraft(state.project, "brief", { ...state.project.brief });
  const pending = state.autosave.flushAuthoringDraft("brief");
  try {
    expect(state.onMutationAcknowledged).not.toHaveBeenCalled();
    resolve({ projectId: "a", editorScope: "brief", entityId: "root", baseCanonicalRevision: local.baseRevision,
      draftRevision: 1, payload: local.payload as Record<string, unknown>, updatedAt: "2026-10-12" });
    await expect(pending).resolves.toBe(true);
    expect(state.onMutationAcknowledged).toHaveBeenCalledExactlyOnceWith({ projectId: "a", epoch: 1, stage: "brief" });
  } finally { await state.unmount(); }
});

it.each(["project", "operation"])("retains an admitted late PUT receipt without publishing it into a newer %s", async kind => {
  const state = await harness();
  let resolve!: (value: AuthoringDraft) => void;
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockReturnValue(new Promise(done => { resolve = done; }));
  const local = putDraft(state.project, "brief", { title: "old admitted input" });
  const pending = state.autosave.flushAuthoringDraft("brief");
  try {
    if (kind === "project") await state.replaceProject(); else await state.replaceOperation();
    resolve({ projectId: "a", editorScope: "brief", entityId: "root", baseCanonicalRevision: local.baseRevision,
      draftRevision: 1, payload: local.payload as Record<string, unknown>, updatedAt: "2026-10-12" });
    await pending;
    expect(state.onMutationAcknowledged).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it("graph read loss blocks queued timers and blur without freezing unrelated scopes", async () => {
  vi.useFakeTimers();
  const state = await harness(), write = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  const retained = putDraft(state.project, "story_graph", { exact: "unsent fields" });
  try {
    state.autosave.scheduleAuthoringDraftAutosave("story_graph");
    state.setGraphAllowed(false);
    await vi.advanceTimersByTimeAsync(1000);
    await expect(state.autosave.flushAuthoringDraft("story_graph")).resolves.toBe(false);
    expect(write).not.toHaveBeenCalled(); expect(getDraft(state.project, "story_graph")).toEqual(retained);
    const brief = putDraft(state.project, "brief", { title: "other scope" });
    write.mockResolvedValue({ projectId: "a", editorScope: "brief", entityId: "root", baseCanonicalRevision: brief.baseRevision,
      draftRevision: 1, payload: brief.payload as Record<string, unknown>, updatedAt: "2026-10-09" });
    await expect(state.autosave.flushAuthoringDraft("brief")).resolves.toBe(true);
    expect(write).toHaveBeenCalledOnce(); expect(getDraft(state.project, "story_graph")).toEqual(retained);
  } finally { await state.unmount(); }
});

it("Close and snapshot can drain an empty graph queue without mounting its editor", async () => {
  const state = await harness(), write = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  const quiescence = createProjectDraftQuiescence();
  quiescence.register("a", "authoring", () => state.autosave.flushAuthoringDraft("story_graph"));
  state.setGraphAllowed(false);
  try {
    for (const operation of ["close", "snapshot"]) {
      const attempt = quiescence.beginClose("a");
      try {
        expect(await attempt.drain(), operation).toBe(true);
        expect(attempt.canCommit(), operation).toBe(true);
      } finally { attempt.finish(); }
    }
    expect(write).not.toHaveBeenCalled();
  } finally { await state.unmount(); }
});

it("lifecycle drain joins an admitted graph flight after read loss without starting another write", async () => {
  const state = await harness();
  let resolve!: (value: AuthoringDraft) => void;
  const write = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockReturnValue(new Promise(done => { resolve = done; }));
  const first = putDraft(state.project, "story_graph", { exact: "already admitted" });
  const pending = state.autosave.flushAuthoringDraft("story_graph");
  state.setGraphAllowed(false);
  const quiescence = createProjectDraftQuiescence();
  quiescence.register("a", "authoring", () => state.autosave.flushAuthoringDraft("story_graph"));
  const attempt = quiescence.beginClose("a");
  let drained = false;
  const draining = attempt.drain().then(result => { drained = true; return result; });
  try {
    await act(async () => undefined);
    expect(drained).toBe(false);
    resolve({ projectId: "a", editorScope: "story_graph", entityId: "root", baseCanonicalRevision: first.baseRevision,
      draftRevision: 1, payload: first.payload as Record<string, unknown>, updatedAt: "2026-10-09" });
    await expect(pending).resolves.toBe(true);
    await expect(draining).resolves.toBe(true);
    expect(attempt.canCommit()).toBe(true); expect(write).toHaveBeenCalledOnce();
    expect(getDraft(state.project, "story_graph")).toBeUndefined();
  } finally {
    resolve({ projectId: "a", editorScope: "story_graph", entityId: "root", baseCanonicalRevision: first.baseRevision,
      draftRevision: 1, payload: first.payload as Record<string, unknown>, updatedAt: "2026-10-09" });
    await Promise.all([pending, draining]); attempt.finish(); await state.unmount();
  }
});

it("lifecycle drain refuses a dirty graph queue while its read is unavailable", async () => {
  const state = await harness(), write = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  const retained = putDraft(state.project, "story_graph", { exact: "must await current read" });
  state.setGraphAllowed(false);
  const quiescence = createProjectDraftQuiescence();
  quiescence.register("a", "authoring", () => state.autosave.flushAuthoringDraft("story_graph"));
  const attempt = quiescence.beginClose("a");
  try {
    await expect(attempt.drain()).resolves.toBe(false);
    expect(attempt.canCommit()).toBe(false); expect(write).not.toHaveBeenCalled();
    expect(getDraft(state.project, "story_graph")).toEqual(retained);
  } finally { attempt.finish(); await state.unmount(); }
});

it("graph in-flight ACK remains valid after read loss but cannot drain newer input", async () => {
  const state = await harness();
  let resolve!: (value: AuthoringDraft) => void;
  const write = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockReturnValue(new Promise(done => { resolve = done; }));
  try {
    const first = putDraft(state.project, "story_graph", { exact: "first" });
    const pending = state.autosave.flushAuthoringDraft("story_graph");
    const newer = putDraft(state.project, "story_graph", { exact: "newer" });
    state.setGraphAllowed(false);
    resolve({ projectId: "a", editorScope: "story_graph", entityId: "root", baseCanonicalRevision: first.baseRevision,
      draftRevision: 1, payload: first.payload as Record<string, unknown>, updatedAt: "2026-10-09" });
    await expect(pending).resolves.toBe(false);
    expect(write).toHaveBeenCalledOnce(); expect(getDraft(state.project, "story_graph")?.payload).toEqual(newer.payload);
    expect(getDraft(state.project, "story_graph")?.serverDraftRevision).toBe(1);
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

it("a retained project callback writes only its original owner after navigation", async () => {
  const state = await harness(); const original = state.project;
  const write = vi.spyOn(plotloomApi, "saveAuthoringDraft").mockResolvedValue({ projectId: "a", editorScope: "brief", entityId: "root", baseCanonicalRevision: original.revision,
    draftRevision: 1, payload: { title: "old project input" }, updatedAt: "2026-10-24" });
  const retainedFlush = state.autosave.flushAuthoringDraft;
  try {
    putDraft(original, "brief", { title: "old project input" }); await state.replaceProject();
    await expect(retainedFlush("brief")).resolves.toBe(true);
    expect(write).toHaveBeenCalledExactlyOnceWith("a", expect.objectContaining({ payload: { title: "old project input" } }));
    expect(getDraft(state.project, "brief")).toBeUndefined(); expect(state.onMutationAcknowledged).not.toHaveBeenCalled();
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
