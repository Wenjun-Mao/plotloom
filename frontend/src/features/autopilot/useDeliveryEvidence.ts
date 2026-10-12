import { useEffect, useState } from "react";
import { plotloomApi } from "../../api";
import type { EvidenceReads } from "./deliveryEvidence";

type ReadState = { key: string; status: "ready"; value: EvidenceReads } | { key: string; status: "failed"; message: string };

/** One cancellable read owner per exact review bundle; authored form state stays separate. */
export function useDeliveryEvidence(projectId: string, bundleHash?: string) {
  const [state, setState] = useState<ReadState>();
  const [attempt, setAttempt] = useState(0);
  const key = `${projectId}:${bundleHash || ""}:${attempt}`;
  useEffect(() => {
    if (!bundleHash) return;
    const abort = new AbortController();
    void Promise.all([plotloomApi.getManagedAssets(projectId, abort.signal), plotloomApi.getCharacterReferenceProposals(projectId, abort.signal),
      plotloomApi.getArtReferenceProposals(projectId, abort.signal), plotloomApi.getImageJobs(projectId, abort.signal)])
      .then(([assets, characters, art, images]) => {
        if (!abort.signal.aborted) setState({ key, status: "ready", value: { assets: assets.assets, characters: characters.proposals, art: art.proposals, images: images.jobs } });
      }).catch(failure => { if (!abort.signal.aborted) setState({ key, status: "failed", message: failure instanceof Error ? failure.message : String(failure) }); });
    return () => abort.abort();
  }, [projectId, bundleHash, key, attempt]);
  return { state: state?.key === key ? state : undefined, retry: () => { setState(undefined); setAttempt(value => value + 1); } };
}
