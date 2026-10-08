import type { InstalledProduction, ProductionBridgePrepareRequest, ProductionBridgeReplacementTarget, ProductionBridgeState } from "../src/types";

export function replacementTarget(): ProductionBridgeReplacementTarget {
  const head = () => ({ revision: 0, entityRevisionId: null, contentHash: null, status: "missing" });
  return { installedAdmissionId: null, bible: head(), graph: head(), sceneBeats: head(), storyboard: head() };
}

export function prepareRequest(overrides: Partial<ProductionBridgePrepareRequest> = {}): ProductionBridgePrepareRequest {
  return { expectedProposalRevision: 0, expectedProposalContentHash: null, expectedSourceInputsHash: "b".repeat(64), replacementTarget: replacementTarget(), ...overrides };
}

export function installedProduction(overrides: Partial<InstalledProduction> = {}): InstalledProduction {
  return {
    admissionId: "installed-admission", proposalRevision: 1, proposalContentHash: "a".repeat(64),
    installedStageRevisions: { story_bible: 1, story_graph: 1, scene_beats: 1, storyboard: 1 },
    status: "current", staleReasons: [], inputs: {}, scenes: [], cuts: [], runtimeChoice: { choices: [] }, ...overrides,
  };
}

export function bridgeState(overrides: Partial<ProductionBridgeState> = {}): ProductionBridgeState {
  return {
    intentGeneration: { status: "available" }, proposal: null, status: "missing", staleReasons: [],
    installation: null, preparation: { status: "available", request: prepareRequest() }, ...overrides,
  };
}
