export interface SamePersonComparison {
  characterId: string;
  judgment: "pass" | "fail" | "unassessable";
  identityNotes: string;
  stateNotes: string;
  productionDecision?: "hold" | "authorize";
  uncertaintyReason?: string;
}

export interface SamePersonReview {
  id: string;
  projectId: string;
  bindingId: string;
  reviewRevision: number;
  referenceBindings: Array<{ characterId: string; referenceDecisionId: string; referenceRevision: number; assetHashes: string[] }>;
  comparisons: Array<SamePersonComparison | {
    characterId: string; judgment: "pass" | "fail" | "unassessable"; comment?: string;
    productionDecision?: "hold" | "authorize"; uncertaintyReason?: string;
    confirmation: { version: "whole-pack-material.v1"; receiptId: string; bundleHash: string; shotId: string };
  }>;
  reviewer: string;
  attribution?: import("./human-review-attribution").HumanReviewAttribution;
  notes: string;
  current: boolean;
  latest: boolean;
  productionEligible: boolean;
  createdAt: string;
}

export interface SamePersonReviewsResponse {
  revision: number;
  reviews: SamePersonReview[];
}

export interface SamePersonComparisonDraft extends Omit<SamePersonComparison, "judgment" | "productionDecision"> {
  judgment: SamePersonComparison["judgment"] | "";
  productionDecision?: SamePersonComparison["productionDecision"] | "";
}
