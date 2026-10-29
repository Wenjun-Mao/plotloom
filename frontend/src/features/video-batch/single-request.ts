import type { H3ReviewedDirections, VideoJobPrepareBody } from "../../api";
import type { Batch } from "./contracts";

const requestKeys = ["approvalId", "shotId", "storyboardRevision", "expectedSelectionRevision", "idempotencyKey", "requestedDurationSeconds",
  "playbackIntent", "resolution", "audio", "aspectPolicy", "allowLetterbox", "allowCenterCrop", "seed", "profileId", "automaticRetryLimit"] as const;
function normalized(request: VideoJobPrepareBody) {
  const values = { requestedDurationSeconds: null, playbackIntent: "source_exact", resolution: null, audio: null, aspectPolicy: null,
    allowLetterbox: false, allowCenterCrop: false, seed: null, profileId: null, automaticRetryLimit: 0, ...request };
  return requestKeys.map(key => values[key] ?? null);
}
export function isSingleShotBatch(batch: Batch, shotId: string): boolean {
  return batch.manifest.setup.shotIds?.length === 1 && batch.manifest.setup.shotIds[0] === shotId
    && batch.manifest.scopeShotIds.length === 1 && batch.manifest.scopeShotIds[0] === shotId
    && batch.manifest.setup.singleRequest?.shotId === shotId;
}
/** An existing current batch is reusable only for the exact original manual request. */
export function matchesSingleRequest(batch: Batch, request: VideoJobPrepareBody, sourceHash: string): boolean {
  const saved = batch.manifest.setup.singleRequest;
  return !!saved && !saved.reviewedDirections && !request.reviewedDirections
    && Object.keys(saved).every(key => requestKeys.includes(key as typeof requestKeys[number]) || key === "reviewedDirections")
    && JSON.stringify(normalized(saved)) === JSON.stringify(normalized(request))
    && batch.manifest.setup.shotIds?.length === 1 && batch.manifest.setup.shotIds[0] === request.shotId
    && batch.manifest.scopeShotIds.length === 1 && batch.manifest.scopeShotIds[0] === request.shotId
    && batch.manifest.targets.length === 1 && batch.manifest.targets[0].shotId === request.shotId
    && batch.manifest.targets[0].sourceHash === sourceHash;
}
export function authorizedSingleDirections(batch: Batch, request: VideoJobPrepareBody, sourceHash: string): H3ReviewedDirections | null {
  if (["stale", "cancelled"].includes(batch.state) || !matchesSingleRequest(batch, request, sourceHash) || batch.execution.authorizedManifestHash !== batch.manifestHash
    || batch.execution.intentReviewVersion !== "production-intent.v2") return null;
  const value = batch.authorizedDirections?.[request.shotId], target = batch.manifest.targets[0];
  return value?.reviewBasis?.version === "production-intent.v2" && value.reviewBasis.batchId === batch.id
    && value.reviewBasis.manifestHash === batch.manifestHash && value.reviewBasis.shotId === request.shotId
    && value.sourceHash === sourceHash && value.intentAuthorization?.version === "production-intent.v2"
    && JSON.stringify(value.fields) === JSON.stringify(target.directions?.fields)
    && JSON.stringify(value.fidelityCheck) === JSON.stringify(target.directions?.fidelityCheck)
    && value.intentAuthorization?.briefHash === target.productionBrief?.briefHash
    && value.fidelityCheck?.version === "assistant-fidelity.v1" && value.fidelityCheck.batchId === batch.id
    && /^[a-f0-9]{64}$/.test(value.promptSha256) ? value : null;
}
export const batchIsSettled = (batch: Batch) => ["cancelled", "approved"].includes(batch.state);
