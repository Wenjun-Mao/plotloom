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
  let project = { ...structuredClone(demoProject), id: "project" };
  const payload = graphDraftFixture();
  const receipt: AuthoringDraft = { projectId: "project", editorScope: "story_graph", entityId: "root", baseCanonicalRevision: project.stageRevisions.story_graph,
    draftRevision: 1, payload: payload as unknown as Record<string, unknown>, updatedAt: "2026-10-09" };
  const serverDrafts = { current: new Map([["project:story_graph:root", receipt]]) }, remember = vi.fn();
  let owner!: GraphWorkbenchController, admitted = false;
  const state = (revision = 1, bindingHash = payload.bindingHash): GraphWorkbenchState => ({ bindingHash, baseCanonicalRevision: project.stageRevisions.story_graph,
    draft: { ...receipt, projectId: project.id, draftRevision: revision, payload: { ...payload, bindingHash } }, initialPayload: null, readOnlyReason: null });
  const read = vi.spyOn(plotloomApi, "getGraphWorkbench").mockImplementation(async () => state());
  const confirmed = { ...source, sectionMapStatus: "current", acceptedSectionMap: { revision: 1, mapping: payload.mapping } } as SourceOutlineReviewState;
  const save = vi.spyOn(plotloomApi, "saveSectionMap").mockResolvedValue(confirmed);
  const installed = { ...confirmed, graphAdmission: { status: "current", graphRevision: 1 } } as SourceOutlineReviewState;
  const install = vi.spyOn(plotloomApi, "installSectionMapGraph").mockResolvedValue(installed);
  const sourceReviewChanged = vi.fn();
  const canonicalChanged = vi.fn(async () => {});
  const root = createRoot(document.createElement("div"));
  function Probe() { owner = useGraphWorkbench(); return null; }
  const render = () => act(async () => root.render(createElement(GraphWorkbenchProvider, { project, enabled: true, readOnly: false, restoredNonce: 0, serverDrafts, remember,
    flush: async () => true, clearDraftWorkflow: vi.fn(), canonicalChanged, revisionConflict: vi.fn(),
    sourceReviewChanged, readAdmission: (_id, allowed) => { admitted = allowed; }, children: createElement(Probe) })));
  await render();
  return { get owner() { return owner; }, get admitted() { return admitted; }, serverDrafts, read, save, install, remember, state, confirmed, installed, sourceReviewChanged, canonicalChanged,
    switchProject: async (id: string) => { project = { ...project, id }; await render(); },
    close: () => act(async () => root.unmount()) };
}

it("held post-confirmation GET revokes read admission; failed GET keeps the successful confirmation outcome", async () => {
  const state = await harness();
  let reject!: (reason: Error) => void, command!: Promise<boolean>;
  state.read.mockImplementationOnce(() => new Promise((_done, fail) => { reject = fail; }));
  try {
    await act(async () => { command = state.owner.confirmMapping(source); });
    expect(state.save).toHaveBeenCalledOnce(); expect(state.owner.readStatus).toBe("loading"); expect(state.admitted).toBe(false);
    expect(state.sourceReviewChanged).toHaveBeenCalledExactlyOnceWith(state.confirmed);
    await act(async () => { state.owner.changeDraft({ ...graphDraftFixture(), fieldBuffers: { blocked: "held input" } }); });
    await act(async () => { reject(new Error("HTTP 503 confirmation graph read")); expect(await command).toBe(true); });
    const retained = structuredClone(state.owner.draft);
    await act(async () => state.owner.changeDraft({ ...graphDraftFixture(), fieldBuffers: { blocked: "failed input" } }));
    expect(state.owner.readStatus).toBe("failed"); expect(state.admitted).toBe(false); expect(state.owner.readError).toContain("HTTP 503");
    expect(state.owner.error).toBe(""); expect(state.remember).not.toHaveBeenCalled(); expect(state.owner.draft).toEqual(retained);
    state.read.mockResolvedValue(state.state(2, "d".repeat(64)));
    await act(async () => state.owner.refresh()); expect(state.owner.readStatus).toBe("ready"); expect(state.admitted).toBe(true);
    expect(state.save).toHaveBeenCalledOnce();
    expect(state.sourceReviewChanged).toHaveBeenCalledExactlyOnceWith(state.confirmed);
  } finally { await state.close(); }
});

it("application publishes its returned admission before canonical refresh, even if the graph read fails", async () => {
  const state = await harness();
  try {
    state.canonicalChanged.mockImplementationOnce(async () => {
      expect(state.sourceReviewChanged).toHaveBeenCalledExactlyOnceWith(state.installed);
    });
    state.read.mockRejectedValueOnce(new Error("HTTP 503 applied graph read"));
    await act(async () => { expect(await state.owner.installMapping(state.confirmed)).toBe(true); });
    expect(state.install).toHaveBeenCalledOnce();
    expect(state.sourceReviewChanged).toHaveBeenCalledExactlyOnceWith(state.installed);
    expect(state.canonicalChanged).toHaveBeenCalledOnce();
    expect(state.owner.readStatus).toBe("failed");
    expect(state.admitted).toBe(false);
    expect(state.owner.readError).toContain("HTTP 503");
    expect(state.owner.error).toBe("");
  } finally { await state.close(); }
});

it("failed application retains its draft and publishes no admission", async () => {
  const state = await harness();
  try {
    const retained = structuredClone(state.owner.draft);
    state.install.mockRejectedValueOnce(new Error("application rejected"));
    state.read.mockClear();
    await act(async () => { expect(await state.owner.installMapping(state.confirmed)).toBe(false); });
    expect(state.sourceReviewChanged).not.toHaveBeenCalled();
    expect(state.canonicalChanged).not.toHaveBeenCalled();
    expect(state.read).not.toHaveBeenCalled();
    expect(state.owner.error).toContain("application rejected");
    expect(state.owner.draft).toEqual(retained);
  } finally { await state.close(); }
});

it("application from a previous project cannot publish or clear the new project's draft", async () => {
  const state = await harness();
  let release!: (value: SourceOutlineReviewState) => void, command!: Promise<boolean>;
  state.install.mockImplementationOnce(() => new Promise(done => { release = done; }));
  try {
    await act(async () => { command = state.owner.installMapping(state.confirmed); });
    expect(state.install).toHaveBeenCalledOnce();
    await state.switchProject("other-project");
    const retained = structuredClone(state.owner.draft);
    state.read.mockClear();
    await act(async () => { release(state.installed); expect(await command).toBe(false); });
    expect(state.sourceReviewChanged).not.toHaveBeenCalled();
    expect(state.canonicalChanged).not.toHaveBeenCalled();
    expect(state.read).not.toHaveBeenCalled();
    expect(state.owner.draft).toEqual(retained);
    expect(state.serverDrafts.current.has("other-project:story_graph:root")).toBe(true);
  } finally { await state.close(); }
});

it("failed confirmation does not publish a review or launch its follow-up graph read", async () => {
  const state = await harness();
  try {
    state.save.mockRejectedValueOnce(new Error("confirmation rejected"));
    state.read.mockClear();
    await act(async () => { expect(await state.owner.confirmMapping(source)).toBe(false); });
    expect(state.sourceReviewChanged).not.toHaveBeenCalled();
    expect(state.read).not.toHaveBeenCalled();
    expect(state.owner.error).toContain("confirmation rejected");
    expect(state.owner.readStatus).toBe("ready");
  } finally { await state.close(); }
});

it("a confirmation response from a previous project cannot replace the shared review", async () => {
  const state = await harness();
  let release!: (value: SourceOutlineReviewState) => void, command!: Promise<boolean>;
  state.save.mockImplementationOnce(() => new Promise(done => { release = done; }));
  try {
    await act(async () => { command = state.owner.confirmMapping(source); });
    expect(state.save).toHaveBeenCalledOnce();
    await state.switchProject("other-project");
    state.read.mockClear();
    await act(async () => { release(state.confirmed); expect(await command).toBe(false); });
    expect(state.sourceReviewChanged).not.toHaveBeenCalled();
    expect(state.read).not.toHaveBeenCalled();
    expect(state.owner.error).toBe("");
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
