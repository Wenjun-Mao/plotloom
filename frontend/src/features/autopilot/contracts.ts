import type { GeometryPreparation } from "./geometryContracts";
import type { ArtRenderStyle, VisualIntent, ScriptBinding } from "../../types";
import type { SamePersonComparison } from "../../same-person-review-types";

export type AutopilotActivity = {
  operationKey: string; owner: string; subjectId: string; jobId: string;
  domain: "text" | "image";
  state: "waiting" | "queued" | "generating" | "validating" | "unknown" | "cancelling" | "delivered" | "adopted" | "failed";
};
export type AutopilotRun = {
  timing?: import("../../components/WorkflowTiming").TimingFacts | null;
  handoffAttribution?: import("../../human-review-attribution").HumanReviewAttribution | null;
  id: string; projectId: string; revision: number;
  state: "running" | "waiting" | "paused" | "blocked" | "cancelled" | "stale" | "taken_over" | "awaiting_review" | "handed_off";
  frames?: Array<{ shotId: string; geometryPreparation?: GeometryPreparation }>;
  phase: string; blocker: { code: string; message: string } | null;
  materialCurrent?: boolean; activities?: AutopilotActivity[];
  policy: { version?: string; geometryPreparation?: { recipeVersion: string }; styleAuthority?: "preset" | "brief"; renderStyle?: ArtRenderStyle | null; artRenderStyle?: ArtRenderStyle | null; maxImages: number | null; maxJobs: number | null;
    automaticRetryLimit?: number | null; textCorrectionLimit?: number; executorBinding?: { backend: "codex_exec"; model: string; reasoningEffort: string; maxProcesses: number; maxTextProcesses?: number; maxImageProcesses?: number } };
  checkpoints: Array<{ operationKey: string; state: string; retry?: import("../generation-retry/contracts").GenerationRetryStatus; evidence: { owner: string; jobId?: string; result: Record<string, unknown> } }>;
  bundle: { inventory: { subjects: Array<{ owner: string; id: string; subjectType?: "scene" | "prop" | null }> }; frames: unknown[]; references: unknown[] } | null;
  handoff: { receiptId: string } | null;
};
export type Launch = { expectedBriefRevision: number; styleAuthority: "brief" | "preset"; renderStyle?: ArtRenderStyle; artRenderStyle?: ArtRenderStyle; maxImages: number | null; maxJobs: number | null; textCorrectionLimit?: number; automaticRetryLimit?: number };
export type TextFailure = { runId: string; runRevision: number; stage: string; stageLabel: string; failedAttemptId: string | null; rejectionHash: string | null;
  terminalContentFailure: boolean; resolved?: boolean; canRetry: boolean; reason: string; automaticUsed: number; automaticLimit: number;
  issues: Array<{ code: string; field: string; item: string; rule: string; excerpt: string | null }>; diagnostics: string[];
  history: Array<{ ordinal: number; mode: "original" | "automatic" | "manual"; state: string; outcome: string | null; comparison: "unknown" | "changed" | "repeated" }> };
export type TextRetry = { commandId: string; expectedRunId: string; expectedRevision: number; failedAttemptId: string; rejectionHash: string; directions: string };
export type ReviewFrame = { targetUse?: VisualIntent["intent"]["targetUse"]; geometryPreparation?: GeometryPreparation; shotId: string; sceneId: string; title: string; sceneName: string; direction: string; assetId: string; originalHash: string; description: string; characterIds: string[]; origin: string };
export type IntentContext = { kind: "storyboard" | "reviewed_intent"; sourceId: string; revision: number; contentHash: string; shotId: string; intent: Omit<VisualIntent["intent"], "targetUse"> };
export type GalleryFrame = ReviewFrame & { intentContext: IntentContext };
export type ReviewReference = { owner: string; subjectId: string; name: string; decisionId: string; assetId: string;
  assets: Array<{ assetId: string; originalHash: string; width: number; height: number }> };
export type ReviewMaterial = { runRevision: number; bundleHash: string; bundle: {
  inventory: { routeCount: number }; references: ReviewReference[]; frames: GalleryFrame[];
  story: { characters: Record<string, string>; graph: { nodes: Array<{ id: string; title: string; summary: string }> }; routes?: string[][]; script: Record<string, unknown>; scriptBinding: ScriptBinding; reports?: Array<{ name: string; url: string }> };
} };
export type Handoff = { expectedRunRevision: number; bundleHash: string; notes?: string; endorsedReferenceIds: string[];
  frames: Array<{ shotId: string; assetId: string; intent: Omit<VisualIntent["intent"], "targetUse">; compatibilityNote: string; comparisons: SamePersonComparison[] }> };
export type MaterialSelectionHandoff = { attribution?: { kind: "codex_task"; taskId: string } | import("../../components/ProjectQaContext").QaActor; expectedRunRevision: number; bundleHash: string;
  notes?: string;
  frames: Array<{ shotId: string; assetId: string; intentContext: IntentContext; intent: IntentContext["intent"];
    qualityObservation?: { compatibility?: "pass" | "fail" | "hold"; comment?: string; comparisons: Array<{ characterId: string; judgment?: BulkComparison["judgment"]; comment?: string; uncertaintyReason?: string }> } }> };

export type BulkComparison = { characterId: string; judgment: "pass" | "fail" | "unassessable"; comment?: string; productionDecision?: "hold" | "authorize"; uncertaintyReason?: string };
export type BulkHandoff = { attribution?: import("../../components/ProjectQaContext").QaActor; basis: "whole-pack-material.v1"; expectedRunRevision: number; bundleHash: string; notes?: string; endorsedReferenceIds: string[];
  frames: Array<{ shotId: string; assetId: string; intentContext: IntentContext; intent: IntentContext["intent"]; compatibility: "pass" | "fail" | "hold"; comment?: string; comparisons: BulkComparison[] }> };
