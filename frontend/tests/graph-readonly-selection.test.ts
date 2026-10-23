import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { GraphWorkbenchProvider } from "../src/features/graph/GraphWorkbenchProvider";
import { useGraphWorkbench, type GraphWorkbenchController } from "../src/features/graph/GraphWorkbenchContext";
import { readGraphSelection, storeGraphSelection } from "../src/features/graph/graphSelection";
import type { WorkspaceProject, StoryGraph } from "../src/types";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root, owner: GraphWorkbenchController, project: WorkspaceProject;
const serverDrafts = { current: new Map() };
const graph = (prefix: string): StoryGraph => ({
  startNodeId: `${prefix}-start`,
  nodes: [
    { id: `${prefix}-start`, title: `${prefix} 开场`, kind: "start", summary: "共同开场。", footageMode: "footage" },
    { id: `${prefix}-ending`, title: `${prefix} 结局`, kind: "ending", summary: "路线结束。", footageMode: "footage" },
  ],
  edges: [{ id: `${prefix}-edge`, sourceNodeId: `${prefix}-start`, targetNodeId: `${prefix}-ending`, kind: "continuation", choiceText: null, stateEffects: {}, entityStateEffects: [] }],
  joinContracts: [],
});

function Probe() { owner = useGraphWorkbench(); return null; }
function Harness() {
  return createElement(GraphWorkbenchProvider, {
    project, enabled: true, readOnly: false, restoredNonce: 0, serverDrafts,
    remember: () => undefined, flush: async () => true, clearDraftWorkflow: () => undefined,
    canonicalChanged: async () => undefined, sourceReviewChanged: () => undefined, revisionConflict: () => undefined,
    children: createElement(Probe),
  });
}
async function show() { await act(async () => root.render(createElement(Harness))); }

beforeEach(() => {
  vi.restoreAllMocks(); localStorage.clear(); sessionStorage.clear();
  project = { ...structuredClone(demoProject), id: "project-a", storyGraph: graph("a"), revision: 1,
    stageRevisions: { story_bible: 0, story_graph: 0, scene_beats: 0, storyboard: 0 } };
  root = createRoot(document.createElement("div"));
  vi.spyOn(plotloomApi, "getGraphWorkbench").mockImplementation(async () => ({ bindingHash: "a".repeat(64),
    baseCanonicalRevision: project.stageRevisions.story_graph, draft: null, initialPayload: null,
    readOnlyReason: "已接受规范图只读。" }));
  vi.spyOn(plotloomApi, "saveAuthoringDraft");
  vi.spyOn(plotloomApi, "previewGraphCommand");
  vi.spyOn(plotloomApi, "applyGraphCommand");
});

afterEach(async () => { await act(async () => root.unmount()); localStorage.clear(); sessionStorage.clear(); vi.restoreAllMocks(); });

it("keeps canonical selection per project and falls back to the current canonical opening", async () => {
  storeGraphSelection("project-a", "removed-node");
  storeGraphSelection("project-b", "b-ending");
  await show();
  expect(owner.readStatus).toBe("ready");
  expect(owner.state?.readOnlyReason).toBeTruthy();
  expect(owner.draft).toBeNull();
  expect(owner.selectedNodeId).toBe("a-start");
  expect(readGraphSelection("project-a")).toBe("a-start");

  await act(async () => owner.selectNode("a-ending"));
  expect(readGraphSelection("project-a")).toBe("a-ending");
  const projectA = project;
  project = { ...structuredClone(projectA), id: "project-b", storyGraph: graph("b") };
  await show();
  expect(owner.selectedNodeId).toBe("b-ending");

  project = projectA;
  await show();
  expect(owner.selectedNodeId).toBe("a-ending");

  project = { ...structuredClone(projectA), storyGraph: { ...graph("a"), nodes: [graph("a").nodes[0]], edges: [] } };
  storeGraphSelection("project-a", "a-ending");
  await show();
  await act(async () => owner.refresh());
  expect(owner.selectedNodeId).toBe("a-start");
  expect(readGraphSelection("project-a")).toBe("a-start");
  expect(plotloomApi.saveAuthoringDraft).not.toHaveBeenCalled();
  expect(plotloomApi.previewGraphCommand).not.toHaveBeenCalled();
  expect(plotloomApi.applyGraphCommand).not.toHaveBeenCalled();
});
