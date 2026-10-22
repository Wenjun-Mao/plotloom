import type { BulkComparison, BulkHandoff, GalleryFrame, ReviewMaterial } from "./contracts";

export type GalleryDraft = { intent: GalleryFrame["intentContext"]["intent"]; compatibility: "pass" | "fail" | "hold"; comment: string; comparisons: BulkComparison[] };

export function galleryDraft(frame: GalleryFrame): GalleryDraft {
  return { intent: structuredClone(frame.intentContext.intent), compatibility: "pass", comment: "",
    comparisons: frame.characterIds.map(characterId => ({ characterId, judgment: "pass" })) };
}

export function galleryFrameReady(draft: GalleryDraft) {
  const authoredBounds = draft.intent.sourceEndorsement ||
    [draft.intent.identityIntent, draft.intent.compositionIntent, draft.intent.styleIntent].every(value => !value || value.length <= 2000);
  return Boolean(authoredBounds) && draft.compatibility === "pass" && Boolean(draft.intent.sourceRefs.length &&
    [draft.intent.identityIntent, draft.intent.compositionIntent, draft.intent.styleIntent].some(value => value?.trim())) &&
    draft.comparisons.every(item => item.judgment === "pass" || item.judgment === "unassessable" &&
      item.productionDecision === "authorize" && Boolean(item.uncertaintyReason?.trim()));
}

export function bulkHandoff(material: ReviewMaterial, drafts: GalleryDraft[], notes: string): BulkHandoff {
  return { basis: "whole-pack-material.v1", expectedRunRevision: material.runRevision, bundleHash: material.bundleHash,
    ...(notes.trim() ? { notes } : {}), endorsedReferenceIds: material.bundle.references.map(item => item.decisionId),
    frames: material.bundle.frames.map((frame, index) => ({ shotId: frame.shotId, assetId: frame.assetId,
      intentContext: frame.intentContext, intent: drafts[index].intent, compatibility: drafts[index].compatibility,
      ...(drafts[index].comment.trim() ? { comment: drafts[index].comment } : {}), comparisons: drafts[index].comparisons })) };
}
