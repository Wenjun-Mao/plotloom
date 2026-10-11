import { act, createElement, useRef } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { getDraft, putDraft } from "../src/draft-registry";
import { GraphWorkbenchProvider } from "../src/features/graph/GraphWorkbenchProvider";
import { useGraphWorkbench, type GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import { useAuthoringDraftAutosave } from "../src/features/authoring/useAuthoringDraftAutosave";
import { graphDraftFixture } from "./graph-workbench-fixture";
import type { GraphWorkbenchState } from "../src/features/graph/contracts";
import type { AuthoringDraft, SourceOutlineReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const project = { ...demoProject, id: "graph-read-test" };
const root = () => createRoot(document.createElement("div"));
let owner: GraphWorkbenchController, autosave: ReturnType<typeof useAuthoringDraftAutosave>;
const state = (): GraphWorkbenchState => ({ bindingHash: "a".repeat(64), baseCanonicalRevision: project.stageRevisions.story_graph,
  draft: null, initialPayload: graphDraftFixture(), readOnlyReason: null });
function Probe() { owner = useGraphWorkbench(); return null; }
function Harness() {
  const authority = useRef(false), serverDrafts = useRef(new Map<string, AuthoringDraft>());
  autosave = useAuthoringDraftAutosave({ project, writesAllowed: true, scopeWritesAllowed: scope => scope !== "story_graph" || authority.current,
    durableDraftsEnabledRef: useRef(true), serverAuthoringDrafts: serverDrafts,
    captureWorkspaceOperation: () => ({ projectId: project.id, epoch: 0, stage: "creator" }), isWorkspaceOperationCurrent: () => true,
    setDurableDraftStatus: vi.fn(), setError: vi.fn(), onConflict: vi.fn() });
  return createElement(GraphWorkbenchProvider, { project, enabled: true, readOnly: false, restoredNonce: 0, serverDrafts,
    readAdmission: (_projectId, allowed) => { authority.current = allowed; },
    remember: payload => { putDraft(project, "story_graph", payload); autosave.scheduleAuthoringDraftAutosave("story_graph"); },
    flush: () => autosave.flushAuthoringDraft("story_graph"), clearDraftWorkflow: vi.fn(), canonicalChanged: vi.fn(async () => {}), sourceReviewChanged: vi.fn(), revisionConflict: vi.fn(),
    children: createElement(Probe) });
}
beforeEach(() => { sessionStorage.clear(); vi.spyOn(plotloomApi, "getGraphWorkbench").mockImplementation(async () => state()); });
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); sessionStorage.clear(); });

it("initial held and failed graph reads admit no local edits or commands, then GET retry restores authority", async () => {
  const mounted = root(), write = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  let reject!: (reason: Error) => void;
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementation(() => new Promise((_done, fail) => { reject = fail; }));
  try {
    await act(async () => mounted.render(createElement(Harness)));
    expect(owner.readStatus).toBe("loading"); expect(owner.state).toBeNull();
    await act(async () => {
      owner.changeDraft(graphDraftFixture()); expect(await owner.saveDraft()).toBe(false);
      expect(await owner.prepareCommand({ operation: "set_start", nodeId: "opening" })).toBe(false);
      expect(await owner.confirmMapping({} as SourceOutlineReviewState)).toBe(false);
      expect(await owner.installMapping({} as SourceOutlineReviewState)).toBe(false);
    });
    await act(async () => reject(new Error("offline")));
    expect(owner.readStatus).toBe("failed"); expect(owner.error).toBe(""); expect(owner.draft).toBeNull();
    expect(getDraft(project, "story_graph")).toBeUndefined(); expect(write).not.toHaveBeenCalled();
    vi.mocked(plotloomApi.getGraphWorkbench).mockImplementation(async () => state());
    await act(async () => owner.refresh()); expect(owner.readStatus).toBe("ready"); expect(owner.draft).not.toBeNull();
  } finally { await act(async () => mounted.unmount()); }
});

it("provider pending and failed reads suspend actual autosave timers and blur while retaining unsent fields", async () => {
  vi.useFakeTimers();
  const mounted = root(), write = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  try {
    await act(async () => mounted.render(createElement(Harness)));
    const edited = { ...graphDraftFixture(), fieldBuffers: { unfinished: "exact unsent content" } };
    await act(async () => owner.changeDraft(edited));
    const retained = getDraft(project, "story_graph");
    let reject!: (reason: Error) => void;
    vi.mocked(plotloomApi.getGraphWorkbench).mockImplementationOnce(() => new Promise((_done, fail) => { reject = fail; }));
    let reading!: Promise<void>;
    await act(async () => { reading = owner.refresh(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    await expect(autosave.flushAuthoringDraft("story_graph")).resolves.toBe(false);
    await act(async () => { reject(new Error("offline")); await reading; });
    await expect(autosave.flushAuthoringDraft("story_graph")).resolves.toBe(false);
    await act(async () => owner.saveDraft());
    expect(write).not.toHaveBeenCalled(); expect(owner.draft).toEqual(edited); expect(getDraft(project, "story_graph")).toEqual(retained);
    await act(async () => owner.refresh()); expect(owner.readStatus).toBe("ready"); expect(owner.draft).toEqual(edited);
  } finally { await act(async () => mounted.unmount()); }
});

it("successful canonical readonly is readable while autosave remains blocked", async () => {
  const mounted = root(), write = vi.spyOn(plotloomApi, "saveAuthoringDraft");
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementation(async () => ({ ...state(), readOnlyReason: "只读规范图" }));
  try {
    await act(async () => mounted.render(createElement(Harness)));
    expect(owner.readStatus).toBe("ready"); expect(owner.readError).toBe("");
    putDraft(project, "story_graph", graphDraftFixture());
    await expect(autosave.flushAuthoringDraft("story_graph")).resolves.toBe(false);
    await act(async () => { owner.changeDraft(graphDraftFixture()); expect(await owner.saveDraft()).toBe(false); });
    expect(write).not.toHaveBeenCalled();
  } finally { await act(async () => mounted.unmount()); }
});

it("stale but ready graph authority admits explicit recovery", async () => {
  const mounted = root(), payload = graphDraftFixture();
  const receipt: AuthoringDraft = { projectId: project.id, editorScope: "story_graph", entityId: "root", draftRevision: 1,
    baseCanonicalRevision: project.stageRevisions.story_graph, payload: payload as unknown as Record<string, unknown>, updatedAt: "2026-10-09" };
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementation(async () => ({ ...state(), bindingHash: "d".repeat(64), draft: receipt, initialPayload: null }));
  const recovery = vi.spyOn(plotloomApi, "recoverGraphDraft").mockImplementation(async () => {
    receipt.payload = { ...payload, bindingHash: "d".repeat(64) }; receipt.draftRevision++; return receipt;
  });
  try {
    await act(async () => mounted.render(createElement(Harness))); expect(owner.stale).toBe(true);
    await act(async () => owner.recover()); expect(recovery).toHaveBeenCalledOnce(); expect(owner.stale).toBe(false);
  } finally { await act(async () => mounted.unmount()); }
});
