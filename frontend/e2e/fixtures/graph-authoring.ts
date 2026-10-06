import type { APIRequestContext } from "@playwright/test";
import type { SectionMap } from "../../src/types";
import type { GraphAuthoringDraft, GraphWorkbenchState } from "../../src/features/graph/contracts";
import { expect } from "../fixture";

async function json(pending: ReturnType<APIRequestContext["get"]>): Promise<any> {
  const response = await pending; expect(response.ok(), await response.text()).toBeTruthy(); return response.json();
}
export async function currentFixtureMapping(request: APIRequestContext, projectUrl: string, content: Omit<SectionMap, "seedTopology">): Promise<SectionMap> {
  const state: GraphWorkbenchState = await json(request.get(`${projectUrl}/graph-workbench`));
  const draft = state.draft?.payload as unknown as GraphAuthoringDraft | undefined;
  const seed = draft ? draft.mapping.seedTopology : state.initialPayload!.mapping.seedTopology;
  return { ...content, seedTopology: seed };
}
export async function acknowledgeGraphMapping(request: APIRequestContext, projectUrl: string, mapping: SectionMap): Promise<number> {
  let state: GraphWorkbenchState = await json(request.get(`${projectUrl}/graph-workbench`));
  if (state.draft && state.draft.payload.bindingHash !== state.bindingHash) {
    await json(request.post(`${projectUrl}/graph-workbench/recover`, { data: { expectedDraftRevision: state.draft.draftRevision, expectedBindingHash: state.bindingHash, payload: null } }));
    state = await json(request.get(`${projectUrl}/graph-workbench`));
  }
  const payload: GraphAuthoringDraft = { bindingHash: state.bindingHash, mapping, rowHints: {}, selectedNodeId: mapping.topology.startNodeId, detachedEndpoints: {}, fieldBuffers: {} };
  const saved = await json(request.put(`${projectUrl}/authoring-drafts`, { data: { editorScope: "story_graph", entityId: "root", baseCanonicalRevision: state.baseCanonicalRevision, expectedDraftRevision: state.draft?.draftRevision ?? 0, payload } }));
  return saved.draftRevision;
}
export async function graphDraftRevision(request: APIRequestContext, projectUrl: string): Promise<number> {
  const state: GraphWorkbenchState = await json(request.get(`${projectUrl}/graph-workbench`));
  expect(state.draft).not.toBeNull(); return state.draft!.draftRevision;
}
export function beaconMap(): Omit<SectionMap, "seedTopology"> {
  return { topologyOrigin: "author", topology: { startNodeId: "opening", nodes: [{ id: "opening", kind: "start" }, { id: "power-choice", kind: "decision" }, { id: "beacon", kind: "ending" }, { id: "dock", kind: "ending" }],
    edges: [{ id: "opening-choice", sourceNodeId: "opening", targetNodeId: "power-choice", kind: "continuation", stateEffects: {}, entityStateEffects: [] },
      ...["beacon", "dock"].map(id => ({ id: `${id}-path`, sourceNodeId: "power-choice", targetNodeId: id, kind: "choice" as const, stateEffects: {}, entityStateEffects: [] }))], joins: [] },
    sections: [{ sectionId: "opening", title: "Storm warning", summary: "The keeper has one cable and two destinations.", ending: false, footageMode: "footage" },
      { sectionId: "power-choice", title: "Power choice", summary: "Choose where to send the cable.", ending: false, footageMode: "route_only" },
      { sectionId: "beacon", title: "Beacon lit", summary: "The beacon guides sailors through the storm.", ending: true, footageMode: "footage" },
      { sectionId: "dock", title: "Dock lit", summary: "The dock welcomes boats while the beacon goes dark.", ending: true, footageMode: "footage" }],
    choices: [{ choiceId: "power-choice", sectionId: "power-choice", prompt: "Where should the keeper send the cable?", outcomes: [
      { outcomeId: "beacon-path", label: "Light the beacon", consequence: "The dock loses power.", endingSectionId: "beacon" },
      { outcomeId: "dock-path", label: "Light the dock", consequence: "The beacon goes dark.", endingSectionId: "dock" }] }], joinReconciliations: {} };
}
