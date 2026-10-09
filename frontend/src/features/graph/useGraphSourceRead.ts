import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import type { SourceOutlineReviewState } from "../../types";

/** Source commands require a read belonging to the displayed project/binding. */
export function useGraphSourceRead(projectId: string | undefined, bindingHash: string | undefined) {
  const [value, setValue] = useState<SourceOutlineReviewState | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "failed">("loading");
  const [error, setError] = useState("");
  const key = `${projectId}:${bindingHash}`;
  const [loadedKey, setLoadedKey] = useState(key);
  const epoch = useRef(0);
  const refresh = useCallback(async () => {
    const request = ++epoch.current;
    setLoadedKey(key);
    setValue(null); setStatus("loading"); setError("");
    if (!projectId) return;
    try {
      const next = await plotloomApi.getSourceOutline(projectId);
      if (request !== epoch.current) return;
      setValue(next); setStatus("ready");
    } catch (reason) {
      if (request !== epoch.current) return;
      setStatus("failed"); setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [projectId, bindingHash]);
  useEffect(() => { void refresh(); return () => { epoch.current++; }; }, [refresh]);
  return { value: loadedKey === key ? value : null, status: loadedKey === key ? status : "loading", error: loadedKey === key ? error : "", refresh };
}
