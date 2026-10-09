import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { ApiError, plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { acknowledgeDraft, getDraft, putDraft } from "../src/draft-registry";
import { GraphWorkbenchProvider } from "../src/features/graph/GraphWorkbenchProvider";
import { useGraphWorkbench, type GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import { graphDraftKey } from "../src/features/graph/contracts";
import type { GraphAuthoringDraft, GraphCommandPreview, GraphWorkbenchState } from "../src/features/graph/contracts";
import type { AuthoringDraft, WorkspaceProject } from "../src/types";
import type { SourceOutlineReviewState } from "../src/types";
import { graphDraftFixture } from "./graph-workbench-fixture";
import { storeGraphSelection } from "../src/features/graph/graphSelection";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root, owner: GraphWorkbenchController, server: AuthoringDraft | null, preview: GraphCommandPreview;
let project: WorkspaceProject, serverDrafts: { current: Map<string, AuthoringDraft> };
let flushGate: Promise<void> | undefined;
const revisionConflict = vi.fn();
const receipt = (payload: GraphAuthoringDraft, revision: number, base = 0): AuthoringDraft => ({ projectId: "project", editorScope: "story_graph", entityId: "root", baseCanonicalRevision: base,
  draftRevision: revision, payload: structuredClone(payload) as unknown as Record<string, unknown>, updatedAt: "2026-10-06T00:00:00Z" });
function state(): GraphWorkbenchState { return { bindingHash: "a".repeat(64), baseCanonicalRevision: project.stageRevisions.story_graph, draft: server ? structuredClone(server) : null,
  initialPayload: server ? null : graphDraftFixture(), readOnlyReason: null }; }
function Probe({ mode }: { mode: string }) { owner = useGraphWorkbench(); return createElement("span", null, mode); }
function Harness({ mode = "story", enabled = true, restoredPayload, restoredNonce = 0 }: { mode?: string; enabled?: boolean; restoredPayload?: GraphAuthoringDraft; restoredNonce?: number }) {
  const source = project;
  return createElement(GraphWorkbenchProvider, { project: source, enabled, readOnly: false, restoredPayload, restoredNonce, serverDrafts,
    remember: payload => putDraft(source, "story_graph", payload, serverDrafts.current.get(graphDraftKey(source.id!))?.draftRevision ?? 0),
    flush: async () => {
      await flushGate;
      const local = getDraft(source, "story_graph");
      if (!local) return true;
      const saved = await plotloomApi.saveAuthoringDraft(source.id!, { editorScope: "story_graph", entityId: "root", baseCanonicalRevision: local.baseRevision,
        expectedDraftRevision: local.serverDraftRevision, payload: local.payload as Record<string, unknown> });
      serverDrafts.current.set(graphDraftKey(source.id!), saved);
      acknowledgeDraft(source, "story_graph", local.localRevision, saved.draftRevision);
      return true;
    }, clearDraftWorkflow: vi.fn(), canonicalChanged: vi.fn().mockResolvedValue(undefined), revisionConflict,
    children: createElement(Probe, { mode }) });
}
async function show(mode?: string) { await act(async () => root.render(createElement(Harness, { mode }))); }

it("preserves graph refusal facts and leaves the acknowledged draft untouched", async () => {
  server = receipt(graphDraftFixture(), 1); await show();
  const before = structuredClone(server);
  const details = { code: "graph_edit_unsafe", diagnostics: [{ code: "out_degree", identity: "out_degree:opening",
    severity: 1, previousSeverity: 0, facts: { nodeId: "opening", nodeKind: "decision", actual: 7, limit: 6 } }] };
  vi.mocked(plotloomApi.previewGraphCommand).mockRejectedValueOnce(new ApiError("raw refusal", 409, details));
  await act(async () => { expect(await owner.prepareCommand({ operation: "add_edge", edgeId: "seventh", sourceNodeId: "opening", targetNodeId: null })).toBe(false); });
  expect(owner.errorDetails).toEqual(details);
  expect(owner.preview).toBeNull(); expect(owner.previewConflict).toBe(false);
  expect(server).toEqual(before); expect(plotloomApi.saveAuthoringDraft).not.toHaveBeenCalled();
  expect(plotloomApi.applyGraphCommand).not.toHaveBeenCalled();
  await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  expect(owner.errorDetails).toBeUndefined();
});
beforeEach(() => {
  sessionStorage.clear(); vi.restoreAllMocks(); revisionConflict.mockClear(); server = null;
  flushGate = undefined;
  project = { ...structuredClone(demoProject), id: "project", revision: 1, stageRevisions: { story_bible: 0, story_graph: 0, scene_beats: 0, storyboard: 0 } };
  serverDrafts = { current: new Map() }; root = createRoot(document.createElement("div"));
  vi.spyOn(plotloomApi, "getGraphWorkbench").mockImplementation(async () => state());
  vi.spyOn(plotloomApi, "saveAuthoringDraft").mockImplementation(async (_, body) => {
    if (body.expectedDraftRevision !== (server?.draftRevision ?? 0)) throw new Error("stale mock receipt");
    server = receipt(body.payload as unknown as GraphAuthoringDraft, (server?.draftRevision ?? 0) + 1, body.baseCanonicalRevision);
    return structuredClone(server);
  });
  vi.spyOn(plotloomApi, "previewGraphCommand").mockImplementation(async (_, body) => {
    const draft = structuredClone(server!.payload) as unknown as GraphAuthoringDraft;
    draft.mapping.sections[0].title = "Confirmed structural edit";
    preview = { draftRevision: body.expectedDraftRevision, bindingHash: draft.bindingHash, command: body.command, result: draft,
      impact: { addedNodeIds: [], removedNodeIds: [], addedEdgeIds: [], removedEdgeIds: [], changedEdgeIds: [], affectedJoinIds: [], retainedNodeIds: [], pendingEdgeIds: [], messages: [] }, previewHash: "c".repeat(64) };
    return preview;
  });
  vi.spyOn(plotloomApi, "applyGraphCommand").mockImplementation(async (_, body) => {
    if (body.expectedDraftRevision !== server!.draftRevision) throw new Error("stale mock preview");
    server = receipt(preview.result, server!.draftRevision + 1);
    return structuredClone(server);
  });
});
afterEach(async () => { await act(async () => root.unmount()); sessionStorage.clear(); vi.restoreAllMocks(); });

it("retained failed reads freeze all new edits and prepared preview writes without discarding input", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  const retainedPreview = owner.preview, retained = structuredClone(owner.draft);
  vi.mocked(plotloomApi.getGraphWorkbench).mockRejectedValueOnce(new Error("offline"));
  await act(async () => owner.refresh());
  vi.mocked(plotloomApi.saveAuthoringDraft).mockClear(); vi.mocked(plotloomApi.previewGraphCommand).mockClear();
  await act(async () => {
    owner.changeDraft({ ...graphDraftFixture(), fieldBuffers: { kept: "new forbidden edit" } });
    await owner.applyPreview(); await owner.undo(); await owner.discard(); await owner.recover();
    await owner.saveDraft(); await owner.prepareCommand({ operation: "set_start", nodeId: "ending" });
  });
  expect(owner.draft).toEqual(retained); expect(owner.preview).toEqual(retainedPreview);
  expect(plotloomApi.saveAuthoringDraft).not.toHaveBeenCalled(); expect(plotloomApi.applyGraphCommand).not.toHaveBeenCalled();
  expect(plotloomApi.previewGraphCommand).not.toHaveBeenCalled();
});

it("a read begun during command acknowledgement prevents the late command dispatch", async () => {
  await show(); let release!: () => void;
  flushGate = new Promise(done => { release = done; });
  let command!: Promise<boolean>;
  await act(async () => { command = owner.prepareCommand({ operation: "set_start", nodeId: "opening" }); });
  let resolve!: (value: GraphWorkbenchState) => void;
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementationOnce(() => new Promise(done => { resolve = done; }));
  let reading!: Promise<void>;
  await act(async () => { reading = owner.refresh(); });
  await act(async () => { release(); expect(await command).toBe(false); });
  expect(plotloomApi.previewGraphCommand).not.toHaveBeenCalled();
  await act(async () => { resolve(state()); await reading; });
  expect(owner.readStatus).toBe("ready");
});

it("preserves one draft through mode changes and saves without approval or dispatch", async () => {
  await show();
  const edited = structuredClone(owner.draft!); edited.mapping.sections[0].summary = "Unsent author prose";
  await act(async () => owner.changeMapping(edited.mapping));
  await show("production");
  expect(owner.draft!.mapping.sections[0].summary).toBe("Unsent author prose");
  await act(async () => { expect(await owner.saveDraft()).toBe(true); });
  expect(server!.payload.mapping).toEqual(edited.mapping);
  expect(getDraft(project, "story_graph")).toBeUndefined();
  expect(plotloomApi.applyGraphCommand).not.toHaveBeenCalled();
});

it("re-reads trusted context after conflict recovery without a canonical revision change", async () => {
  await show();
  const restored = graphDraftFixture(); restored.bindingHash = "d".repeat(64);
  restored.mapping.sections[0].summary = "Recovered author prose";
  server = receipt(restored, 3); serverDrafts.current.set(graphDraftKey("project"), server);
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementation(async () => ({ ...state(), bindingHash: restored.bindingHash }));
  await act(async () => root.render(createElement(Harness, { restoredPayload: restored, restoredNonce: 1 })));
  expect(owner.stale).toBe(false);
  expect(owner.state!.draft!.draftRevision).toBe(3);
  expect(owner.state!.bindingHash).toBe(restored.bindingHash);
  const edited = structuredClone(owner.draft!); edited.mapping.sections[0].summary += " continued";
  await act(async () => owner.changeMapping(edited.mapping));
  await act(async () => { expect(await owner.saveDraft()).toBe(true); });
  expect(server!.payload.mapping).toEqual(edited.mapping);
  expect(server!.draftRevision).toBe(4);
});

it("pauses edits but preserves selection during a recovery authority read", async () => {
  await show();
  const restored = graphDraftFixture(); restored.mapping.sections[0].summary = "Recovered";
  server = receipt(restored, 2); serverDrafts.current.set(graphDraftKey("project"), server);
  let release!: (value: GraphWorkbenchState) => void;
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementationOnce(() => new Promise(done => { release = done; }));
  await act(async () => root.render(createElement(Harness, { restoredPayload: restored, restoredNonce: 1 })));
  const edited = structuredClone(owner.draft!); edited.mapping.sections[0].summary = "Typed after recovery";
  await act(async () => { owner.changeMapping(edited.mapping); owner.selectNode("ending"); });
  await act(async () => release(state()));
  expect(owner.draft!.mapping.sections[0].summary).toBe("Recovered");
  expect(owner.selectedNodeId).toBe("ending");
  expect(getDraft(project, "story_graph")).toBeUndefined();
});

it("rejects a delayed recovery authority read after switching projects", async () => {
  await show();
  const restored = graphDraftFixture(); restored.bindingHash = "d".repeat(64);
  server = receipt(restored, 2); serverDrafts.current.set(graphDraftKey("project"), server);
  const oldState = { ...state(), bindingHash: restored.bindingHash };
  let release!: (value: GraphWorkbenchState) => void;
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementationOnce(() => new Promise(done => { release = done; }));
  await act(async () => root.render(createElement(Harness, { restoredPayload: restored, restoredNonce: 1 })));
  project = { ...project, id: "other-project" }; server = null; await show();
  await act(async () => release(oldState));
  expect(owner.state!.bindingHash).toBe("a".repeat(64));
  expect(owner.draft!.mapping.sections[0].summary).toBe("opening story");
  expect(owner.stale).toBe(false);
});

it("reports a current preview only after saving and validation succeed", async () => {
  await show();
  const command = { operation: "set_start" as const, nodeId: "opening" };
  vi.mocked(plotloomApi.previewGraphCommand).mockRejectedValueOnce(new Error("cycle refused"));
  await act(async () => { expect(await owner.prepareCommand(command)).toBe(false); });
  expect(owner.preview).toBeNull();
  expect(owner.error).toBe("cycle refused");
  await act(async () => { expect(await owner.prepareCommand(command)).toBe(true); });
  expect(owner.preview).not.toBeNull();
  expect(owner.error).toBe("");
  expect(plotloomApi.applyGraphCommand).not.toHaveBeenCalled();
});

it("does not send an old command to a new project after a delayed flush", async () => {
  await show();
  let release!: () => void, preparing!: Promise<boolean>;
  flushGate = new Promise(done => { release = done; });
  await act(async () => { preparing = owner.prepareCommand({ operation: "set_start", nodeId: "opening" }); });
  project = { ...project, id: "other-project" };
  await show();
  await act(async () => { release(); expect(await preparing).toBe(false); });
  expect(plotloomApi.previewGraphCommand).not.toHaveBeenCalled();
  expect(owner.preview).toBeNull();
  expect(owner.error).toBe("");
  expect(owner.busy).toBe(false);
});

it("does not publish an old preview after the project changes during its request", async () => {
  await show();
  const implementation = vi.mocked(plotloomApi.previewGraphCommand).getMockImplementation()!;
  let release!: () => void, preparing!: Promise<boolean>;
  const held = new Promise<void>(done => { release = done; });
  vi.mocked(plotloomApi.previewGraphCommand).mockImplementationOnce(async (...args) => { await held; return implementation(...args); });
  await act(async () => { preparing = owner.prepareCommand({ operation: "set_start", nodeId: "opening" }); });
  project = { ...project, id: "other-project" }; await show();
  await act(async () => { release(); expect(await preparing).toBe(false); });
  expect(plotloomApi.previewGraphCommand).toHaveBeenCalledWith("project", expect.anything());
  expect(owner.preview).toBeNull();
  expect(owner.busy).toBe(false);
});

it("stops a held command when its provider is unmounted", async () => {
  await show();
  let release!: () => void, preparing!: Promise<boolean>;
  flushGate = new Promise(done => { release = done; });
  await act(async () => { preparing = owner.prepareCommand({ operation: "set_start", nodeId: "opening" }); });
  await act(async () => root.render(null));
  await act(async () => { release(); expect(await preparing).toBe(false); });
  expect(plotloomApi.previewGraphCommand).not.toHaveBeenCalled();
});

it("keeps the new session busy when an old session's operation finishes", async () => {
  await show();
  const implementation = vi.mocked(plotloomApi.previewGraphCommand).getMockImplementation()!;
  let releaseOld!: () => void, releaseNew!: () => void, oldOperation!: Promise<boolean>, newOperation!: Promise<boolean>;
  const oldHeld = new Promise<void>(done => { releaseOld = done; });
  const newHeld = new Promise<void>(done => { releaseNew = done; });
  vi.mocked(plotloomApi.previewGraphCommand)
    .mockImplementationOnce(async (...args) => { await oldHeld; return implementation(...args); })
    .mockImplementationOnce(async (...args) => { await newHeld; return implementation(...args); });
  await act(async () => { oldOperation = owner.prepareCommand({ operation: "set_start", nodeId: "opening" }); });
  await act(async () => root.render(createElement(Harness, { enabled: false })));
  await show();
  await act(async () => { newOperation = owner.prepareCommand({ operation: "set_start", nodeId: "opening" }); });
  await act(async () => { releaseOld(); expect(await oldOperation).toBe(false); });
  expect(owner.busy).toBe(true);
  expect(owner.preview).toBeNull();
  await act(async () => { releaseNew(); expect(await newOperation).toBe(true); });
  expect(owner.busy).toBe(false);
  expect(owner.preview).not.toBeNull();
});

it("keeps the currently selected node after a command with no selection intent", async () => {
  await show();
  await act(async () => owner.selectNode("ending"));
  await act(async () => owner.prepareCommand({ operation: "add_join", nodeId: "ending", joinId: "new-join" }));
  // The acknowledged draft still carries its earlier opening selection.
  expect(preview.result.selectedNodeId).toBe("opening");
  await act(async () => owner.applyPreview());
  expect(owner.selectedNodeId).toBe("ending");
});

it("cancel changes nothing and Undo preserves later unfinished field input", async () => {
  await show();
  const command = { operation: "set_start" as const, nodeId: "opening" };
  await act(async () => owner.prepareCommand(command));
  await act(async () => owner.cancelPreview());
  expect(plotloomApi.applyGraphCommand).not.toHaveBeenCalled();
  expect(owner.draft!.mapping.sections[0].title).toBe("opening");
  await act(async () => owner.prepareCommand(command));
  await act(async () => owner.applyPreview());
  expect(owner.canUndo).toBe(true);
  const pending = structuredClone(owner.draft!); pending.fieldBuffers["edge:opening-ending:stateEffects"] = '{"unfinished":';
  await act(async () => owner.changeDraft(pending));
  const savedCalls = vi.mocked(plotloomApi.saveAuthoringDraft).mock.calls.length;
  await act(async () => owner.undo());
  expect(owner.error).toContain("已有内容修改");
  expect(owner.draft!.fieldBuffers).toEqual(pending.fieldBuffers);
  expect(vi.mocked(plotloomApi.saveAuthoringDraft).mock.calls).toHaveLength(savedCalls);
});

it("surfaces a previous-base session buffer after canonical reload", async () => {
  const oldProject = structuredClone(project), oldDraft = graphDraftFixture(); oldDraft.mapping.sections[0].summary = "Previous-base unsent prose";
  putDraft(oldProject, "story_graph", oldDraft, 0);
  project = { ...project, stageRevisions: { ...project.stageRevisions, story_graph: 1 } };
  await show();
  expect(revisionConflict).toHaveBeenCalled();
  expect(revisionConflict.mock.calls[0][0].payload.mapping.sections[0].summary).toBe("Previous-base unsent prose");
  expect(sessionStorage.getItem("plotloom:workbench-drafts:v1")).toContain("Previous-base unsent prose");
});

it("rejects a delayed refresh that predates a newer autosave acknowledgement", async () => {
  server = receipt(graphDraftFixture(), 1); await show();
  const old = state(); let resolve!: (value: GraphWorkbenchState) => void;
  const edited = structuredClone(owner.draft!); edited.mapping.sections[0].summary = "Newer acknowledged prose";
  await act(async () => owner.changeMapping(edited.mapping));
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementationOnce(() => new Promise(done => { resolve = done; }));
  let reading!: Promise<void>;
  await act(async () => { reading = owner.refresh(); });
  // A save already dispatched before the read may still acknowledge afterward.
  server = receipt(edited, 2); serverDrafts.current.set(graphDraftKey("project"), server);
  const local = getDraft(project, "story_graph")!;
  acknowledgeDraft(project, "story_graph", local.localRevision, 2);
  expect(serverDrafts.current.get(graphDraftKey("project"))!.draftRevision).toBe(2);
  await act(async () => { resolve(old); await reading; });
  expect(owner.readStatus).toBe("failed");
  expect(owner.draft!.mapping.sections[0].summary).toBe("Newer acknowledged prose");
  expect(serverDrafts.current.get(graphDraftKey("project"))!.draftRevision).toBe(2);
});

it("refuses a preview after newer local edits instead of overwriting them", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  const edited = structuredClone(owner.draft!); edited.mapping.sections[0].summary = "Typed after preview";
  await act(async () => owner.changeMapping(edited.mapping));
  expect(owner.preview).toBeNull();
  await act(async () => owner.applyPreview());
  expect(owner.draft!.mapping.sections[0].summary).toBe("Typed after preview");
  expect(plotloomApi.applyGraphCommand).not.toHaveBeenCalled();
});

it("retires a remote revision-conflicted preview before any repeated confirmation, then explicitly rereads and prepares anew", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  const confirm = owner.applyPreview;
  const remote = structuredClone(server!.payload) as unknown as GraphAuthoringDraft;
  remote.mapping.sections[0].summary = "Remote newer prose";
  server = receipt(remote, 2);
  vi.mocked(plotloomApi.applyGraphCommand).mockRejectedValueOnce(new ApiError("arbitrary server wording", 409, { code: "revision_conflict" }));
  await act(async () => confirm());
  expect(owner.preview).toBeNull(); expect(owner.previewConflict).toBe(true);
  expect(owner.error).toContain("重新读取");
  await act(async () => { await confirm(); expect(await owner.prepareCommand({ operation: "set_start", nodeId: "opening" })).toBe(false); });
  expect(plotloomApi.applyGraphCommand).toHaveBeenCalledTimes(1);
  await act(async () => owner.refresh());
  expect(owner.previewConflict).toBe(false);
  expect(owner.draft!.mapping.sections[0].summary).toBe("Remote newer prose");
  await act(async () => { expect(await owner.prepareCommand({ operation: "set_start", nodeId: "opening" })).toBe(true); });
  expect(owner.preview!.draftRevision).toBe(2);
});

it("preserves unsent buffers, selection and the original CAS basis during explicit conflict reads and subsequent typing", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  const apply = owner.applyPreview;
  let reject!: (reason: unknown) => void, applying!: Promise<void>;
  vi.mocked(plotloomApi.applyGraphCommand).mockImplementationOnce(() => new Promise((_, fail) => { reject = fail; }));
  await act(async () => { applying = apply(); });
  const edited = structuredClone(owner.draft!); edited.fieldBuffers["edge:opening-ending:stateEffects"] = '{"unfinished":';
  // A delayed response must not consume input that arrived after dispatch.
  await act(async () => owner.selectNode("ending"));
  server = receipt(graphDraftFixture(), 2);
  await act(async () => { reject(new ApiError("CAS", 409, { code: "revision_conflict" })); await applying; });
  await act(async () => owner.changeDraft(edited));
  await act(async () => owner.refresh());
  expect(owner.previewConflict).toBe(true); expect(owner.selectedNodeId).toBe("ending");
  expect(getDraft(project, "story_graph")!.serverDraftRevision).toBe(1);
  expect(revisionConflict).toHaveBeenCalledWith(expect.objectContaining({ serverDraftRevision: 1, payload: edited }));
  // The refresh retained the local draft; restoring it uses the existing recovery
  // boundary, not a silent CAS update from a read.
  expect(serverDrafts.current.get(graphDraftKey("project"))!.draftRevision).toBe(1);
  const next = structuredClone(owner.draft!); next.fieldBuffers = edited.fieldBuffers;
  await act(async () => owner.changeDraft(next));
  expect(getDraft(project, "story_graph")!.serverDraftRevision).toBe(1);
  expect((getDraft(project, "story_graph")!.payload as GraphAuthoringDraft).fieldBuffers).toEqual(edited.fieldBuffers);
});

it("retains the invalidated preview boundary and local content when explicit rereading fails", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  vi.mocked(plotloomApi.applyGraphCommand).mockRejectedValueOnce(new ApiError("CAS", 409, { code: "revision_conflict" }));
  await act(async () => owner.applyPreview());
  const retained = structuredClone(owner.draft);
  vi.mocked(plotloomApi.getGraphWorkbench).mockRejectedValueOnce(new Error("offline"));
  await act(async () => owner.refresh());
  expect(owner.previewConflict).toBe(true); expect(owner.preview).toBeNull(); expect(owner.draft).toEqual(retained);
  expect(owner.readError).toContain("offline"); expect(owner.readStatus).toBe("failed");
  await act(async () => owner.applyPreview());
  expect(plotloomApi.applyGraphCommand).toHaveBeenCalledTimes(1);
});

it("does not classify unrelated 409 responses as a draft revision conflict", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  vi.mocked(plotloomApi.applyGraphCommand).mockRejectedValueOnce(new ApiError("domain refusal", 409, { code: "graph_invalid" }));
  await act(async () => owner.applyPreview());
  expect(owner.previewConflict).toBe(false); expect(owner.preview).not.toBeNull(); expect(owner.error).toBe("domain refusal");
});

it("ignores an old project's delayed revision conflict response", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  let reject!: (reason: unknown) => void, applying!: Promise<void>;
  vi.mocked(plotloomApi.applyGraphCommand).mockImplementationOnce(() => new Promise((_, fail) => { reject = fail; }));
  await act(async () => { applying = owner.applyPreview(); });
  project = { ...project, id: "other-project" }; server = null; await show();
  await act(async () => { reject(new ApiError("old CAS", 409, { code: "revision_conflict" })); await applying; });
  expect(owner.previewConflict).toBe(false); expect(owner.error).toBe(""); expect(owner.preview).toBeNull();
});

it("ignores a reread failure older than a successful authority read", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  vi.mocked(plotloomApi.applyGraphCommand).mockRejectedValueOnce(new ApiError("CAS", 409, { code: "revision_conflict" }));
  await act(async () => owner.applyPreview());
  let reject!: (reason: unknown) => void, oldRead!: Promise<void>;
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementationOnce(() => new Promise((_, fail) => { reject = fail; }));
  await act(async () => { oldRead = owner.refresh(); });
  const remote = graphDraftFixture(); remote.mapping.sections[0].summary = "Latest successful authority";
  server = receipt(remote, 2);
  await act(async () => owner.refresh());
  const latest = { draft: structuredClone(owner.draft), receipt: structuredClone(serverDrafts.current.get(graphDraftKey("project"))), conflict: owner.previewConflict, error: owner.error };
  await act(async () => { reject(new Error("obsolete failure")); await oldRead; });
  expect({ draft: owner.draft, receipt: serverDrafts.current.get(graphDraftKey("project")), conflict: owner.previewConflict, error: owner.error }).toEqual(latest);
});

it("preserves this tab's surviving live selection over another tab's stored preference on reread", async () => {
  server = receipt(graphDraftFixture(), 1); await show();
  await act(async () => owner.selectNode("ending"));
  storeGraphSelection("project", "opening");
  expect(getDraft(project, "story_graph")).toBeUndefined();
  await act(async () => owner.refresh());
  expect(owner.selectedNodeId).toBe("ending");
  project = { ...project, id: "other-project" }; server = null;
  storeGraphSelection("other-project", "opening"); await show();
  expect(owner.selectedNodeId).toBe("opening");
});

it("uses the server's valid selection with an explanation if the live node was remotely removed", async () => {
  server = receipt(graphDraftFixture(), 1); await show();
  await act(async () => owner.selectNode("ending"));
  const next = graphDraftFixture(); next.mapping.topology.nodes = next.mapping.topology.nodes.filter(node => node.id !== "ending");
  next.mapping.sections = next.mapping.sections.filter(section => section.sectionId !== "ending");
  next.mapping.topology.edges[0].targetNodeId = null;
  server = receipt(next, 2);
  await act(async () => owner.refresh());
  expect(owner.selectedNodeId).toBe("opening"); expect(owner.error).toContain("原选中节点已不在");
});

it("keeps draft content when discard fails, then clears only on its exact receipt", async () => {
  await show();
  const edited = structuredClone(owner.draft!); edited.mapping.sections[0].summary = "Preserved until discard acknowledgement";
  await act(async () => owner.changeMapping(edited.mapping));
  const discard = vi.spyOn(plotloomApi, "discardAuthoringDraft").mockRejectedValueOnce(new Error("CAS refused"));
  await act(async () => { expect(await owner.discard()).toBe(false); });
  expect(owner.draft!.mapping.sections[0].summary).toBe(edited.mapping.sections[0].summary);
  expect(serverDrafts.current.get(graphDraftKey("project"))).toBeDefined();
  discard.mockImplementationOnce(async (_, body) => { const revision = server!.draftRevision; expect(body.expectedDraftRevision).toBe(revision); server = null; return revision; });
  await act(async () => { expect(await owner.discard()).toBe(true); });
  expect(owner.draft!.mapping.sections[0].summary).toBe("opening story");
  expect(serverDrafts.current.size).toBe(0);
});

it("preserves draft Undo through own content confirmation on the same canonical base", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  await act(async () => owner.applyPreview());
  vi.spyOn(plotloomApi, "saveSectionMap").mockImplementationOnce(async () => {
    const payload = structuredClone(server!.payload) as unknown as GraphAuthoringDraft;
    payload.bindingHash = "d".repeat(64); server = receipt(payload, server!.draftRevision + 1);
    return {} as SourceOutlineReviewState;
  });
  vi.mocked(plotloomApi.getGraphWorkbench).mockImplementation(async () => ({ ...state(), bindingHash: "d".repeat(64) }));
  const source = { source: { revision: 1 }, acceptedOutline: { revision: 1, contentHash: "e".repeat(64) }, acceptedSectionMap: null } as SourceOutlineReviewState;
  vi.mocked(plotloomApi.getGraphWorkbench).mockRejectedValueOnce(new Error("post-confirm read failure"));
  await act(async () => { expect(await owner.confirmMapping(source)).toBe(true); });
  expect(owner.readStatus).toBe("failed"); expect(owner.error).toBe("");
  await act(async () => owner.refresh());
  expect(owner.canUndo).toBe(true);
  await act(async () => owner.undo());
  expect(owner.draft!.bindingHash).toBe("d".repeat(64));
  expect(owner.draft!.mapping.sections[0].title).toBe("opening");
});

it("retains a later author selection when an asynchronous Undo receipt arrives", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "set_start", nodeId: "opening" }));
  await act(async () => owner.applyPreview());
  const save = vi.mocked(plotloomApi.saveAuthoringDraft).getMockImplementation()!;
  let release!: () => void, undo!: Promise<void>;
  const held = new Promise<void>(done => { release = done; });
  vi.mocked(plotloomApi.saveAuthoringDraft).mockImplementationOnce(async (...args) => { await held; return save(...args); });
  await act(async () => { undo = owner.undo(); });
  await act(async () => owner.selectNode("ending"));
  await act(async () => { release(); await undo; });
  expect(owner.selectedNodeId).toBe("ending");
  expect(owner.draft!.mapping.sections[0].title).toBe("opening");
  expect(owner.canUndo).toBe(false);
});

it("uses command selection if a later selected node is removed by its receipt", async () => {
  await show(); await act(async () => owner.prepareCommand({ operation: "delete", nodeId: "ending", method: "only_delete" }));
  preview.result.mapping.topology.nodes = preview.result.mapping.topology.nodes.filter(node => node.id !== "ending");
  preview.result.mapping.sections = preview.result.mapping.sections.filter(section => section.sectionId !== "ending");
  preview.result.mapping.topology.edges[0].targetNodeId = null;
  const apply = vi.mocked(plotloomApi.applyGraphCommand).getMockImplementation()!;
  let release!: () => void, applying!: Promise<void>;
  const held = new Promise<void>(done => { release = done; });
  vi.mocked(plotloomApi.applyGraphCommand).mockImplementationOnce(async (...args) => { await held; return apply(...args); });
  await act(async () => { applying = owner.applyPreview(); });
  await act(async () => owner.selectNode("ending"));
  await act(async () => { release(); await applying; });
  expect(owner.selectedNodeId).toBe("opening");
  expect(owner.draft!.mapping.sections[0].title).toBe("Confirmed structural edit");
});
