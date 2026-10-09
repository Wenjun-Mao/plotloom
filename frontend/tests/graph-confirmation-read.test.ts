import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { GraphWorkbenchProvider } from "../src/features/graph/GraphWorkbenchProvider";
import { useGraphWorkbench, type GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import { graphDraftFixture } from "./graph-workbench-fixture";
import type { GraphWorkbenchState } from "../src/features/graph/contracts";
import type { AuthoringDraft, SourceOutlineReviewState } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); });
const source = { source: { revision: 1 }, acceptedOutline: { revision: 1, contentHash: "e".repeat(64) }, acceptedSectionMap: null } as SourceOutlineReviewState;
async function harness() {
  const project = { ...structuredClone(demoProject), id: "project" }, payload = graphDraftFixture();
  const receipt: AuthoringDraft = { projectId: "project", editorScope: "story_graph", entityId: "root", baseCanonicalRevision: project.stageRevisions.story_graph,
    draftRevision: 1, payload: payload as unknown as Record<string, unknown>, updatedAt: "2026-10-09" };
  const serverDrafts = { current: new Map([["project:story_graph:root", receipt]]) }, remember = vi.fn();
  let owner!: GraphWorkbenchController, admitted = false;
  const state = (revision = 1, bindingHash = payload.bindingHash): GraphWorkbenchState => ({ bindingHash, baseCanonicalRevision: project.stageRevisions.story_graph,
    draft: { ...receipt, draftRevision: revision, payload: { ...payload, bindingHash } }, initialPayload: null, readOnlyReason: null });
  const read = vi.spyOn(plotloomApi, "getGraphWorkbench").mockImplementation(async () => state());
  const save = vi.spyOn(plotloomApi, "saveSectionMap").mockResolvedValue({} as SourceOutlineReviewState);
  const root = createRoot(document.createElement("div"));
  function Probe() { owner = useGraphWorkbench(); return null; }
  await act(async () => root.render(createElement(GraphWorkbenchProvider, { project, enabled: true, readOnly: false, restoredNonce: 0, serverDrafts, remember,
    flush: async () => true, clearDraftWorkflow: vi.fn(), canonicalChanged: async () => {}, revisionConflict: vi.fn(),
    readAdmission: (_id, allowed) => { admitted = allowed; }, children: createElement(Probe) })));
  return { get owner() { return owner; }, get admitted() { return admitted; }, serverDrafts, read, save, remember, state,
    close: () => act(async () => root.unmount()) };
}

it("held post-confirmation GET revokes read admission; failed GET keeps the successful confirmation outcome", async () => {
  const state = await harness();
  let reject!: (reason: Error) => void, command!: Promise<boolean>;
  state.read.mockImplementationOnce(() => new Promise((_done, fail) => { reject = fail; }));
  try {
    await act(async () => { command = state.owner.confirmMapping(source); });
    expect(state.save).toHaveBeenCalledOnce(); expect(state.owner.readStatus).toBe("loading"); expect(state.admitted).toBe(false);
    await act(async () => { state.owner.changeDraft({ ...graphDraftFixture(), fieldBuffers: { blocked: "held input" } }); });
    await act(async () => { reject(new Error("HTTP 503 confirmation graph read")); expect(await command).toBe(true); });
    const retained = structuredClone(state.owner.draft);
    await act(async () => state.owner.changeDraft({ ...graphDraftFixture(), fieldBuffers: { blocked: "failed input" } }));
    expect(state.owner.readStatus).toBe("failed"); expect(state.admitted).toBe(false); expect(state.owner.readError).toContain("HTTP 503");
    expect(state.owner.error).toBe(""); expect(state.remember).not.toHaveBeenCalled(); expect(state.owner.draft).toEqual(retained);
    state.read.mockResolvedValue(state.state(2, "d".repeat(64)));
    await act(async () => state.owner.refresh()); expect(state.owner.readStatus).toBe("ready"); expect(state.admitted).toBe(true);
    expect(state.save).toHaveBeenCalledOnce();
  } finally { await state.close(); }
});

it("a newer graph read supersedes the post-confirmation read and its late result cannot replace authority", async () => {
  const state = await harness();
  let release!: (next: GraphWorkbenchState) => void, command!: Promise<boolean>;
  state.read.mockImplementationOnce(() => new Promise(done => { release = done; }));
  try {
    await act(async () => { command = state.owner.confirmMapping(source); });
    state.read.mockResolvedValue(state.state(2, "d".repeat(64)));
    await act(async () => state.owner.refresh());
    expect(state.owner.state?.bindingHash).toBe("d".repeat(64));
    await act(async () => { release(state.state(2, "f".repeat(64))); expect(await command).toBe(true); });
    expect(state.owner.readStatus).toBe("ready"); expect(state.admitted).toBe(true);
    expect(state.owner.state?.bindingHash).toBe("d".repeat(64)); expect(state.owner.draft?.bindingHash).toBe("d".repeat(64));
    expect(state.save).toHaveBeenCalledOnce();
  } finally { await state.close(); }
});

it("a latest ACK received during post-confirmation reading cannot be downgraded by its result", async () => {
  const state = await harness();
  let release!: (next: GraphWorkbenchState) => void, command!: Promise<boolean>;
  state.read.mockImplementationOnce(() => new Promise(done => { release = done; }));
  try {
    await act(async () => { command = state.owner.confirmMapping(source); });
    const latest = state.state(3, "d".repeat(64)).draft!;
    state.serverDrafts.current.set("project:story_graph:root", latest);
    await act(async () => { release(state.state(2, "d".repeat(64))); expect(await command).toBe(true); });
    expect(state.serverDrafts.current.get("project:story_graph:root")).toEqual(latest);
    expect(state.owner.readStatus).toBe("failed"); expect(state.admitted).toBe(false);
    expect(state.owner.readError).toContain("早于刚保存"); expect(state.owner.error).toBe("");
  } finally { await state.close(); }
});
