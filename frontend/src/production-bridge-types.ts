/** Current proposal review is separate from immutable installed-story authority. */
export interface CanonicalReplacementHead {
  revision: number;
  entityRevisionId: string | null;
  contentHash: string | null;
  status: string;
}

export interface ProductionBridgeReplacementTarget {
  installedAdmissionId: string | null;
  bible: CanonicalReplacementHead;
  graph: CanonicalReplacementHead;
  sceneBeats: CanonicalReplacementHead;
  storyboard: CanonicalReplacementHead;
}

export interface ProductionBridgePrepareRequest {
  expectedProposalRevision: number;
  expectedProposalContentHash: string | null;
  expectedSourceInputsHash: string;
  replacementTarget: ProductionBridgeReplacementTarget;
}

export interface ProductionBridgeConflict { code: string; message: string; sectionId: string | null; episode: number | null; sceneIndex: number | null; }
export interface ProductionBridgeIntentEntry { id: string; targetKind: "scene_objective" | "beat_purpose"; targetId: string; sourceCoordinates: Record<string, unknown>; sourceContentHash: string; sourceExcerpt: string; suggestedText: string | null; text: string; }
export interface ProductionBridgeIntentPackage { suggestionOrigin: "none" | "model_inference.v1"; reviewState: "pending" | "model_suggested" | "author_saved"; entries: ProductionBridgeIntentEntry[]; provenance?: Record<string, unknown> | null; }
export interface PresentationSpan { start: number; end: number; role: "unassigned" | "physical" | "visible_text" | "runtime_choice" | "review_only" | "dialogue"; rendering: string; reason: string; }
export interface PresentationSource { id: string; kind: "action" | "composition" | "dialogue"; targetId: string; coordinates: Record<string, unknown>; sourceHash: string; sourceText: string; spans: PresentationSpan[]; }
export interface RuntimeChoice { choiceId: string; sectionId: string; prompt: string; outcomes: Array<{ outcomeId: string; label: string; endingSectionId: string; consequence: string }>; }
export type RuntimeChoices = { choices: RuntimeChoice[] };
export interface ProductionPresentation { version: 1; reviewed: boolean; sourceHash: string; sources: PresentationSource[]; runtimeChoice: RuntimeChoices; frozenEvidence: Record<string, unknown>; }

export interface ProductionSceneMapping {
  inputs: Record<string, unknown>;
  scenes: Array<Record<string, unknown>>;
  cuts: Array<Record<string, unknown>>;
}

export interface ProductionBridgeProposal extends ProductionSceneMapping {
  presentation: ProductionPresentation;
  revision: number;
  contentHash: string;
  replacementTarget: ProductionBridgeReplacementTarget;
  intentPackage: ProductionBridgeIntentPackage;
  conflicts: ProductionBridgeConflict[];
  advisories: ProductionBridgeConflict[];
  installable: boolean;
  preparedAt: string;
}

export interface InstalledProduction extends ProductionSceneMapping {
  admissionId: string;
  proposalRevision: number;
  proposalContentHash: string;
  installedStageRevisions: Record<string, number>;
  status: "current" | "outdated";
  staleReasons: string[];
  runtimeChoice: RuntimeChoices | null;
}

export interface ProductionBridgeIntentJob { id: string; status: "queued" | "dispatched" | "ready" | "stale" | "failed" | "cancelled" | "outcome_unknown"; proposalRevision: number; proposalContentHash: string; profileId: string; profileVersion: number; promptVersion: string; createdAt: string; updatedAt: string; errorCode: string | null; errorMessage: string | null; resultProposalRevision: number | null; providerRequestId: string | null; responseHash: string | null; }

export interface ProductionBridgeState {
  intentGeneration: { status: "available" } | { status: "unavailable"; reason: "not_configured" };
  proposal: ProductionBridgeProposal | null;
  status: "missing" | "ready" | "accepted" | "stale";
  staleReasons: string[];
  installation: InstalledProduction | null;
  preparation: { status: "available"; request: ProductionBridgePrepareRequest } | { status: "unavailable"; reason: string };
  intentJob?: ProductionBridgeIntentJob | null;
  simulationLabel?: string | null;
}
