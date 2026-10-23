import type { SourceOutlineReviewState } from "../../types";

/** Retained accepted content is not necessarily accepted for the current source. */
export function acceptedOutlineIsCurrent(review: SourceOutlineReviewState | null): boolean {
  return Boolean(review?.source && review.outlineStatus === "accepted" && review.acceptedOutline
    && review.acceptedOutline.sourceRevision === review.source.revision);
}
