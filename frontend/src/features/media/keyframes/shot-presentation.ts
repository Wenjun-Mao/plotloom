import type { ImageJob, Shot } from "../../../types";

export type PhysicalPresentation = Pick<Shot, "action" | "composition" | "visualIntent" | "motionIntent" | "cameraMovement">;
export type LiteralSource = { shotId: string; index: number };
export type MessagePresentation = "source" | "popped_out_draft" | "popped_out_send";
export interface ShotPresentationReview {
  expectedRevision: number; sourceHash: string; approvalId: string; storyboardRevision: number;
  physical: PhysicalPresentation; literalSources: LiteralSource[];
  messagePresentation: MessagePresentation; reason: string; reviewed: true;
}
export interface ShotPresentationState {
  revision: number; current: boolean;
  source: { shot: Shot; resolvedContext: Record<string, unknown>; predecessor: Shot | null;
    sourceHash: string; literalOptions: Array<LiteralSource & { text: string; sourceCoordinates: Record<string, unknown>; sourceContentHash: string }> };
  decision: { id: string; revision: number; sourceHash: string; effectiveShot: Shot; review: ShotPresentationReview } | null;
}

export function physicalFields(shot: Shot): PhysicalPresentation {
  return { action: shot.action, composition: shot.composition, visualIntent: shot.visualIntent,
    motionIntent: shot.motionIntent, cameraMovement: shot.cameraMovement };
}

/** Unbound current deliveries need review; absence of a binding cannot prove staleness. */
export function generatedCandidateState(assetId: string, jobs: ImageJob[]): "current" | "history" | "imported" {
  const job = jobs.find(job => job.deliveries.some(delivery => delivery.candidates.some(candidate => candidate.assetId === assetId)));
  return job ? job.current ? "current" : "history" : "imported";
}
