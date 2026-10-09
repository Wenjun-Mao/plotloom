import { useCallback, useEffect, useState } from "react";
import { plotloomApi, type RuntimeCapabilities } from "../../api";

type CapabilityRead =
  | { state: "loading"; data: null }
  | { state: "failed"; data: null }
  | { state: "ready"; data: RuntimeCapabilities };

/** A failed capability read cannot establish that a feature is unavailable. */
export function useRuntimeCapabilities() {
  const [read, setRead] = useState<CapabilityRead>({ state: "loading", data: null });
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt(value => value + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setRead({ state: "loading", data: null });
    void plotloomApi.getRuntimeCapabilities(controller.signal).then(data => {
      if (!controller.signal.aborted) setRead({ state: "ready", data });
    }).catch(() => {
      if (!controller.signal.aborted) setRead({ state: "failed", data: null });
    });
    return () => controller.abort();
  }, [attempt]);
  return { ...read, retry };
}
