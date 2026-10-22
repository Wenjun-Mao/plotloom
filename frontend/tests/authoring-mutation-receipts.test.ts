import { act, createElement, useRef } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { useAuthoringDraftRecovery } from "../src/app/workspace/useAuthoringDraftRecovery";
import { useProjectAuthoringPersistence } from "../src/app/workspace/useProjectAuthoringPersistence";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import type { AuthoringDraft } from "../src/types";
import type { WorkspaceOperation } from "../src/app/workspace/contracts";
import { routeFromLocation } from "../src/app/workspace/contracts";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); });

async function harness(recoveryMode: boolean) {
  let project = { ...demoProject, id: "a" }, epoch = 1;
  const draft: AuthoringDraft = { projectId: "a", editorScope: "brief", entityId: "root", draftRevision: 2,
    baseCanonicalRevision: project.revision, payload: { ...project.brief }, updatedAt: "2026-10-12" };
  const serverDrafts = { current: new Map([["a:brief:root", draft]]) };
  const errors = vi.fn(), observed = vi.fn();
  let authoring!: ReturnType<typeof useProjectAuthoringPersistence>;
  let recovery!: ReturnType<typeof useAuthoringDraftRecovery>;
  const capture = (): WorkspaceOperation => ({ projectId: project.id, epoch, stage: "brief" });
  const isCurrent = (operation: WorkspaceOperation) => operation.projectId === project.id && operation.epoch === epoch;
  const excluded = (): never => { throw new Error("Canonical commands are outside this draft-receipt harness"); };
  function Harness() {
    const durable = useRef(true);
    const session = { project, connection: "connected" as const, activePage: "brief" as const,
      route: { ...routeFromLocation(), project: project.id, stage: "brief" as const }, serverDrafts, capture, isCurrent,
      registerNavigationCleanup: () => () => undefined, unsafeDraft: undefined,
      markCanonicalRefreshRequired: excluded, refreshCurrentRoute: excluded, reloadCanonicalProject: excluded,
      acceptCreatedProject: excluded, acceptCanonicalProject: excluded, acceptCanonicalStage: excluded,
      acceptStoryboardReview: excluded, showValidationIssues: excluded, clearValidationIssues: excluded,
      applyDemoSave: excluded, rejectProjectLoad: excluded, setUnsafeDraft: excluded };
    authoring = useProjectAuthoringPersistence({
      session,
      durableDraftsEnabled: durable, feedback: { setBusy: vi.fn(), setError: errors },
      draftQuiescence: createProjectDraftQuiescence(),
    });
    recovery = useAuthoringDraftRecovery({
      session, durableEnabled: recoveryMode,
      currentDraft: authoring.currentDraft, restoredDraft: authoring.restoredDraft, setRestoredDraft: authoring.setRestoredDraft,
      draftConflict: authoring.draftConflict, setDraftConflict: authoring.setDraftConflict,
      scheduleAutosave: authoring.scheduleAuthoringDraftAutosave, setError: errors,
      reloadDraftConflict: authoring.reloadDraftConflict, copyDraftConflict: authoring.copyDraftConflict,
      discardDraftConflict: authoring.discardDraftConflict,
      onMutationAcknowledged: operation => { observed(operation); authoring.observeAuthoringMutation(operation); },
    });
    return null;
  }
  const root = createRoot(document.createElement("div"));
  const render = () => act(async () => root.render(createElement(Harness)));
  await render();
  return { get authoring() { return authoring; }, get recovery() { return recovery; }, serverDrafts, errors, observed,
    replaceProject: async () => { project = { ...project, id: "b" }; epoch++; await render(); },
    unmount: () => act(async () => root.unmount()) };
}

it.each(["exact", "mismatch", "failure", "superseded"])("recovery discard publishes only an owned exact receipt (%s)", async kind => {
  const state = await harness(true);
  let resolve!: (receipt: number | undefined) => void, reject!: (error: Error) => void;
  const discard = vi.spyOn(plotloomApi, "discardAuthoringDraft").mockReturnValue(new Promise((done, fail) => { resolve = done; reject = fail; }));
  try {
    expect(state.recovery.recovery?.source).toBe("server");
    await act(async () => state.recovery.discard());
    expect(discard).toHaveBeenCalledExactlyOnceWith("a", { editorScope: "brief", entityId: "root", expectedDraftRevision: 2 });
    expect(state.observed).not.toHaveBeenCalled(); expect(state.authoring.admissionVersion).toBe(0);
    if (kind === "superseded") await state.replaceProject();
    await act(async () => { if (kind === "failure") reject(new Error("storage unavailable")); else resolve(kind === "mismatch" ? 3 : 2); });
    expect(state.authoring.admissionVersion).toBe(kind === "exact" ? 1 : 0);
    expect(state.observed).toHaveBeenCalledTimes(kind === "exact" ? 1 : 0);
    expect(state.serverDrafts.current.has("a:brief:root")).toBe(kind !== "exact");
    expect(state.errors).toHaveBeenCalledTimes(["mismatch", "failure"].includes(kind) ? 1 : 0);
  } finally { await state.unmount(); }
});

it.each([2, 3])("close-time authoring discard advances observation only for exact receipt %s", async receipt => {
  const state = await harness(false);
  vi.spyOn(plotloomApi, "discardAuthoringDraft").mockResolvedValue(receipt);
  try {
    state.authoring.currentDraft.current = { scope: "brief", payload: demoProject.brief };
    let result = false;
    await act(async () => { result = await state.authoring.discardCurrentAuthoringDraft("brief"); });
    expect(result).toBe(receipt === 2);
    expect(state.authoring.admissionVersion).toBe(receipt === 2 ? 1 : 0);
    expect(state.serverDrafts.current.has("a:brief:root")).toBe(receipt !== 2);
    expect(state.authoring.currentDraft.current === undefined).toBe(receipt === 2);
  } finally { await state.unmount(); }
});
