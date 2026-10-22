import type { StoryboardReview } from "../../types";

/** A retained approval ID is not current authority for an edited storyboard. */
export function hasCurrentStoryboardApproval(review: StoryboardReview | null | undefined, revision: number | undefined, draftChanged: boolean): boolean {
  return Boolean(!draftChanged && review?.activeApproval && review.head.status === "ready"
    && review.head.revision === revision && review.activeApproval.subjectRevision === revision);
}
