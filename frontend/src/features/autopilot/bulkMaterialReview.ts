import type { BulkComparison, GalleryFrame, MaterialSelectionHandoff, ReviewMaterial } from "./contracts";

export type GalleryDraft = { intent: GalleryFrame["intentContext"]["intent"]; compatibility: "pass" | "fail" | "hold"; comment: string; comparisons: BulkComparison[]; observedCompatibility?: boolean; observedCharacters?: string[] };

export function galleryDraft(frame: GalleryFrame): GalleryDraft {
  return { intent: structuredClone(frame.intentContext.intent), compatibility: "hold", comment: "",
    comparisons: frame.characterIds.map(characterId => ({ characterId, judgment: "unassessable", productionDecision: "hold" })) };
}

export function hasGalleryObservations(draft: GalleryDraft) {
  return Boolean(draft.observedCompatibility || draft.comment.trim() || draft.comparisons.some(item =>
    draft.observedCharacters?.includes(item.characterId) || item.comment?.trim() || item.uncertaintyReason?.trim()));
}

export function materialSelectionHandoff(material: ReviewMaterial, drafts?: GalleryDraft[], notes = ""): MaterialSelectionHandoff {
  return { expectedRunRevision: material.runRevision, bundleHash: material.bundleHash,
    ...(notes.trim() ? { notes } : {}),
    frames: material.bundle.frames.map((frame, index) => {
      const draft = drafts?.[index];
      const observations = draft?.comparisons.filter(item => draft.observedCharacters?.includes(item.characterId) || item.comment?.trim() || item.uncertaintyReason?.trim()) || [];
      return { shotId: frame.shotId, assetId: frame.assetId, intentContext: frame.intentContext, intent: draft?.intent || frame.intentContext.intent,
        ...(draft && hasGalleryObservations(draft) ? { qualityObservation: {
          ...(draft.observedCompatibility ? { compatibility: draft.compatibility } : {}),
          ...(draft.comment ? { comment: draft.comment } : {}),
          comparisons: observations.map(item => ({ characterId: item.characterId,
            ...(draft.observedCharacters?.includes(item.characterId) ? { judgment: item.judgment } : {}),
            ...(item.comment ? { comment: item.comment } : {}), ...(item.uncertaintyReason ? { uncertaintyReason: item.uncertaintyReason } : {}) })),
        } } : {}) };
    }) };
}
