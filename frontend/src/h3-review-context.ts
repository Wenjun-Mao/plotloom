import { useState } from "react";
import type { ManagedAsset, ReviewedKeyframe } from "./types";

/** Availability cannot manufacture a change to the last authoritative source. */
export function useH3MediaIdentity({ projectId, shotId, ready, binding, keyframe, samePersonReviewId }: {
  projectId?: string;
  shotId?: string;
  ready: boolean;
  binding?: ReviewedKeyframe;
  keyframe?: ManagedAsset;
  samePersonReviewId?: string;
}) {
  const scope = JSON.stringify([projectId, shotId]);
  const identity = JSON.stringify([
    binding?.id, binding?.selectionRevision, binding?.visualIntentId,
    binding?.visualIntentRevision, keyframe?.id, keyframe?.originalHash, samePersonReviewId,
  ]);
  const [observed, setObserved] = useState({ scope, identity: ready ? identity : "unknown" });
  if (observed.scope !== scope || (ready && observed.identity !== identity)) {
    const next = { scope, identity: ready ? identity : "unknown" };
    setObserved(next);
    return next.identity;
  }
  return observed.identity;
}
