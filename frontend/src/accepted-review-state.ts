import type { ReviewContextDiagnostic } from "./review-context-types";

/** Independent accepted-content authority; candidate status never grants it. */
export interface AcceptedReviewState {
  status: "missing" | "current" | "reopened" | "retained";
  staleReasons: ReviewContextDiagnostic[];
}
