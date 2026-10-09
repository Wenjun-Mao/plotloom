import type { SamePersonComparison, SamePersonComparisonDraft, SamePersonReview } from "../../../same-person-review-types";

/** Review evidence belongs to the reviewer, never to a prefilled assertion. */
export function newSamePersonComparisons(
  identities: readonly { characterId: string }[],
): SamePersonComparisonDraft[] {
  return identities.map(({ characterId }) => ({
    characterId,
    judgment: "",
    identityNotes: "",
    stateNotes: "",
  }));
}

export function completeSamePersonComparisons(drafts: SamePersonComparisonDraft[]): SamePersonComparison[] | null {
  if (!drafts.length || drafts.some(item => !item.judgment || !item.identityNotes.trim() || !item.stateNotes.trim()
    || (item.judgment === "unassessable" && (!item.productionDecision || !item.uncertaintyReason?.trim())))) return null;
  return drafts.map(item => ({
    characterId: item.characterId, judgment: item.judgment as SamePersonComparison["judgment"],
    identityNotes: item.identityNotes.trim(), stateNotes: item.stateNotes.trim(),
    ...(item.judgment === "unassessable" ? {
      productionDecision: item.productionDecision as "hold" | "authorize",
      uncertaintyReason: item.uncertaintyReason!.trim(),
    } : {}),
  }));
}

export function latestCurrentReviewsByBinding(reviews: SamePersonReview[]): Map<string, SamePersonReview> {
  return new Map(reviews.filter(item => item.current && item.latest).map(item => [item.bindingId, item]));
}

export function samePersonReviewSummary(review: SamePersonReview): string {
  return review.comparisons.map(item => `${item.characterId}：${item.judgment === "pass" ? "通过" : item.judgment === "fail" ? "不通过" : `无法判断 · ${item.productionDecision === "authorize" ? "已明确授权投产（接受身份不确定性）" : "暂缓投产"}`}`).join("；");
}
