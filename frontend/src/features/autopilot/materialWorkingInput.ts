import type { GalleryDraft } from "./bulkMaterialReview";
import type { ReviewMaterial } from "./contracts";

type FrameText = { shotId: string; identityIntent: string; compositionIntent: string; styleIntent: string; sourceRefs: string[]; comment: string; comparisons: { characterId: string; comment: string; uncertaintyReason: string }[] };
type MaterialText = { notes: string; frames: FrameText[] };

/** Retain authored text; review judgments and production authorization are transient. */
export function materialWorkingInput(material: ReviewMaterial, drafts: GalleryDraft[], notes: string): string {
  const input: MaterialText = { notes, frames: drafts.map((draft, index) => ({
    shotId: material.bundle.frames[index].shotId,
    identityIntent: draft.intent.identityIntent || "", compositionIntent: draft.intent.compositionIntent || "", styleIntent: draft.intent.styleIntent || "",
    sourceRefs: draft.intent.sourceRefs, comment: draft.comment,
    comparisons: draft.comparisons.map(({ characterId, comment, uncertaintyReason }) => ({ characterId, comment: comment || "", uncertaintyReason: uncertaintyReason || "" })),
  })) };
  return JSON.stringify(input);
}
export function resumeMaterialWorkingInput(text: string, material: ReviewMaterial, drafts: GalleryDraft[]): { notes: string; drafts: GalleryDraft[] } {
  const input = JSON.parse(text) as MaterialText;
  if (typeof input.notes !== "string" || !Array.isArray(input.frames) || input.frames.length !== drafts.length) throw new Error("整包审阅文字草稿无法匹配当前素材。");
  return { notes: input.notes, drafts: drafts.map((draft, index) => {
    const frame = input.frames[index];
    if (frame.shotId !== material.bundle.frames[index].shotId || ![frame.identityIntent, frame.compositionIntent, frame.styleIntent, frame.comment].every(value => typeof value === "string") || !Array.isArray(frame.sourceRefs) || !frame.sourceRefs.every(value => typeof value === "string") || !Array.isArray(frame.comparisons)) throw new Error("首帧文字草稿无法匹配当前素材。");
    return { ...draft, intent: { ...draft.intent, identityIntent: frame.identityIntent, compositionIntent: frame.compositionIntent, styleIntent: frame.styleIntent, sourceRefs: frame.sourceRefs, sourceEndorsement: undefined }, comment: frame.comment,
      comparisons: draft.comparisons.map(comparison => {
        const retained = frame.comparisons.find(value => value.characterId === comparison.characterId);
        if (!retained || typeof retained.comment !== "string" || typeof retained.uncertaintyReason !== "string") throw new Error("身份审阅文字草稿无法匹配当前角色。");
        return { ...comparison, comment: retained.comment, uncertaintyReason: retained.uncertaintyReason };
      }),
    };
  }) };
}
