import type { ArtRenderStyle, VisualIntent, ScriptBinding } from "../../types";
import type { SamePersonComparison, SamePersonComparisonDraft } from "../../same-person-review-types";

export type AutopilotRun = {
  id: string; projectId: string; revision: number;
  state: "running" | "waiting" | "paused" | "blocked" | "cancelled" | "stale" | "taken_over" | "awaiting_review" | "handed_off";
  phase: string; blocker: { code: string; message: string } | null;
  policy: { renderStyle: ArtRenderStyle; artRenderStyle: ArtRenderStyle; maxImages: number; maxJobs: number };
  checkpoints: Array<{ operationKey: string; state: string; evidence: { owner: string; jobId?: string; result: Record<string, unknown> } }>;
  bundle: { inventory: { subjects: Array<{ owner: string }> }; frames: unknown[]; references: unknown[] } | null;
  handoff: { receiptId: string } | null;
};
export type Launch = { expectedBriefRevision: number; renderStyle: ArtRenderStyle; artRenderStyle: ArtRenderStyle; maxImages: number; maxJobs: number };
export type ReviewFrame = { shotId: string; sceneId: string; title: string; sceneName: string; direction: string; assetId: string; originalHash: string; description: string; characterIds: string[]; origin: string };
export type ReviewReference = { owner: string; subjectId: string; name: string; decisionId: string; assetId: string;
  assets: Array<{ assetId: string; originalHash: string; width: number; height: number }> };
export type ReviewMaterial = { runRevision: number; bundleHash: string; bundle: {
  inventory: { routeCount: number }; references: ReviewReference[]; frames: ReviewFrame[];
  story: { characters: Record<string, string>; graph: { nodes: Array<{ id: string; title: string; summary: string }> }; routes?: string[][]; script: Record<string, unknown>; scriptBinding: ScriptBinding; reports?: Array<{ name: string; url: string }> };
} };
export type FrameDraft = { direction: string; sources: string; compatibility: string; comparisons: SamePersonComparisonDraft[] };
export type Handoff = { expectedRunRevision: number; bundleHash: string; reviewer: string; notes: string; endorsedReferenceIds: string[];
  frames: Array<{ shotId: string; assetId: string; intent: Omit<VisualIntent, "id" | "assetId" | "revision">["intent"]; compatibilityNote: string; comparisons: SamePersonComparison[] }> };

export function completeFrame(draft: FrameDraft) {
  return Boolean(draft.direction.trim() && draft.sources.trim() && draft.compatibility.trim() && draft.comparisons.every(item =>
    item.identityNotes.trim() && item.stateNotes.trim() && (item.judgment === "pass" ||
      item.judgment === "unassessable" && item.productionDecision === "authorize" && item.uncertaintyReason?.trim())));
}
