import { useEffect, useState } from "react";
import { autopilotApi } from "./api";
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
    void autopilotApi.deliveryEvidence(projectId, abort.signal).then(value => {
        if (!abort.signal.aborted) setState({ key, status: "ready", value });
      }).catch(failure => { if (!abort.signal.aborted) setState({ key, status: "failed", message: failure instanceof Error ? failure.message : String(failure) }); });
    return () => abort.abort();
  }, [projectId, bundleHash, key, attempt]);
  return { state: state?.key === key ? state : undefined, retry: () => { setState(undefined); setAttempt(value => value + 1); } };
}
