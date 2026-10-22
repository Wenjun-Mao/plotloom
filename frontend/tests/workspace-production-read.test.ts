import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { GraphWorkbenchContext } from "../src/features/graph/GraphWorkbenchContext";
import { WorkspaceProductionProvider, useWorkspaceProduction } from "../src/features/graph/WorkspaceProductionContext";
import type { ScriptReviewState, SourceOutlineReviewState, StoryboardReview } from "../src/types";
import { graphControllerFixture, graphDraftFixture } from "./graph-workbench-fixture";
import { workflowProductionFixture } from "./workflow-production-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
afterEach(() => vi.restoreAllMocks());

async function harness() {
  const data = workflowProductionFixture({ graphAdmission: {} } as SourceOutlineReviewState);
  const calls = {
    bridge: vi.spyOn(plotloomApi, "getProductionBridge").mockResolvedValue(data.bridge!),
    script: vi.spyOn(plotloomApi, "getScript").mockResolvedValue(data.script!),
    source: vi.spyOn(plotloomApi, "getStoryboardSourceReview").mockResolvedValue(data.storyboardSource!),
    canonical: vi.spyOn(plotloomApi, "getStoryboardReview").mockResolvedValue({ head: { revision: 1, status: "ready" } } as StoryboardReview),
  };
  const draft = graphDraftFixture();
  const graph = graphControllerFixture({ state: { bindingHash: draft.bindingHash, baseCanonicalRevision: 1,
    draft: null, initialPayload: draft, readOnlyReason: null } });
  let project = { ...demoProject, id: "one", revision: 1 }, active = true;
  let guide!: ReturnType<typeof useWorkspaceProduction>, inspector!: ReturnType<typeof useWorkspaceProduction>;
  function Guide() { guide = useWorkspaceProduction(); return null; }
  function Inspector() { inspector = useWorkspaceProduction(); return null; }
  const root = createRoot(document.createElement("div"));
  const render = () => act(async () => root.render(createElement(GraphWorkbenchContext.Provider, { value: graph },
    createElement(WorkspaceProductionProvider, { project, active, children: [createElement(Guide, { key: "guide" }), createElement(Inspector, { key: "inspector" })] }))));
  await render();
  return { calls, get guide() { return guide; }, get inspector() { return inspector; }, render,
    activate: async (value: boolean) => { active = value; await render(); },
    project: async (id: string) => { project = { ...project, id }; await render(); },
    revision: async () => { project = { ...project, revision: project.revision + 1 }; await render(); },
    close: () => act(async () => root.unmount()) };
}

it("shares one settled read across guide/inspector and view-only rerenders", async () => {
  const state = await harness();
  try {
    expect(state.guide.data).toBe(state.inspector.data);
    expect(state.guide.data?.script?.acceptedReviewState.status).toBe("current");
    await state.render();
    for (const call of Object.values(state.calls)) expect(call).toHaveBeenCalledOnce();
    await state.revision();
    for (const call of Object.values(state.calls)) expect(call).toHaveBeenCalledTimes(2);
  } finally { await state.close(); }
});

it("invalidates advice on return from review pages, even without a project revision change", async () => {
  const state = await harness();
  let release!: (value: ScriptReviewState) => void;
  const missing: ScriptReviewState = { status: "missing", acceptedReviewState: { status: "missing", staleReasons: [] }, acceptedScript: null, candidate: null, staleReasons: [] };
  try {
    await state.activate(false);
    expect(state.guide.data).toBeUndefined();
    state.calls.script.mockImplementationOnce(() => new Promise(done => { release = done; }));
    await state.activate(true);
    expect(state.guide.data).toBeUndefined();
    expect(state.inspector.data).toBeUndefined();
    await act(async () => release(missing));
    expect(state.guide.data?.script).toEqual(missing);
    expect(state.guide.data).toBe(state.inspector.data);
    for (const call of Object.values(state.calls)) expect(call).toHaveBeenCalledTimes(2);
  } finally { await state.close(); }
});

it("reports failed reads and gives both consumers the same retry result", async () => {
  const state = await harness();
  try {
    state.calls.script.mockRejectedValueOnce(new Error("HTTP 503"));
    await act(async () => state.guide.retry());
    expect(state.guide.data?.errors).toEqual(["剧本暂不可读取"]);
    expect(state.inspector.data?.script).toBeUndefined();
    await act(async () => state.inspector.retry());
    expect(state.guide.data?.errors).toEqual([]);
    expect(state.guide.data).toBe(state.inspector.data);
    state.calls.source.mockRejectedValueOnce(new Error("source review unavailable"));
    await act(async () => state.guide.retry());
    expect(state.guide.data?.storyboardSource).toBeUndefined();
    // The additional advisory read does not change existing inspector admission.
    expect(state.guide.data?.errors).toEqual([]);
  } finally { await state.close(); }
});

it("suppresses late reads across project one → two → one", async () => {
  const state = await harness();
  let late!: (value: ScriptReviewState) => void, current!: (value: ScriptReviewState) => void;
  try {
    state.calls.script.mockImplementationOnce(() => new Promise(done => { late = done; }));
    await state.project("two");
    expect(state.guide.data).toBeUndefined();
    state.calls.script.mockImplementationOnce(() => new Promise(done => { current = done; }));
    await state.project("one");
    expect(state.guide.data).toBeUndefined();
    const missing: ScriptReviewState = { status: "missing", acceptedReviewState: { status: "missing", staleReasons: [] }, acceptedScript: null, candidate: null, staleReasons: [] };
    await act(async () => late(missing));
    expect(state.guide.data).toBeUndefined();
    await act(async () => current(missing));
    expect(state.guide.data?.script).toEqual(missing);
    expect(state.guide.data).toBe(state.inspector.data);
  } finally { await state.close(); }
});
