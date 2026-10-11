import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import type { SourceOutlineReviewState } from "../../types";

export type WorkspaceSourceReviewStatus = "idle" | "loading" | "ready" | "failed";
export type WorkspaceSourceReviewResult =
  | { status: "ready"; value: SourceOutlineReviewState }
  | { status: "failed"; error: string };

interface ReadSnapshot {
  key: string;
  status: WorkspaceSourceReviewStatus;
  value: SourceOutlineReviewState | null;
  error: string;
}

/** One project-scoped read owner shared by the process guide and graph/source views. */
export function useWorkspaceSourceReview(projectId: string | undefined, projectRevision: number, enabled = true) {
  const key = projectId ? `${projectId}:${projectRevision}` : "";
  const [snapshot, setSnapshot] = useState<ReadSnapshot>({ key: "", status: "idle", value: null, error: "" });
  const epoch = useRef(0);
  const inFlight = useRef<{ key: string; promise: Promise<WorkspaceSourceReviewResult | null> } | null>(null);

  const refresh = useCallback(async (): Promise<WorkspaceSourceReviewResult | null> => {
    if (inFlight.current?.key === key) return inFlight.current.promise;
    const request = ++epoch.current;
    if (!projectId) {
      setSnapshot({ key, status: "idle", value: null, error: "" });
      return null;
    }
    setSnapshot({ key, status: "loading", value: null, error: "" });
    let promise!: Promise<WorkspaceSourceReviewResult | null>;
    promise = (async () => {
      try {
        const value = await plotloomApi.getSourceOutline(projectId);
        if (request !== epoch.current) return null;
        setSnapshot({ key, status: "ready", value, error: "" });
        return { status: "ready", value };
      } catch (reason) {
        const error = reason instanceof Error ? reason.message : String(reason);
        if (request !== epoch.current) return null;
        setSnapshot({ key, status: "failed", value: null, error });
        return { status: "failed", error };
      } finally {
        if (inFlight.current?.promise === promise) inFlight.current = null;
      }
    })();
    inFlight.current = { key, promise };
    return promise;
  }, [key, projectId]);

  useEffect(() => {
    if (!enabled) return;
    void refresh();
    return () => { epoch.current++; };
  }, [enabled, refresh]);

  const replace = useCallback((value: SourceOutlineReviewState) => {
    epoch.current++;
    inFlight.current = null;
    setSnapshot({ key, status: "ready", value, error: "" });
  }, [key]);

  const current = snapshot.key === key
    ? snapshot
    : { key, status: projectId ? "loading" as const : "idle" as const, value: null, error: "" };
  return { ...current, refresh, replace };
}

export type WorkspaceSourceReviewRead = ReturnType<typeof useWorkspaceSourceReview>;
