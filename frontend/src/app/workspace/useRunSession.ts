import { useCallback, useEffect, useRef } from "react";
import { plotloomApi } from "../../api";
import { traceEvents } from "../../model";
import type { WorkspaceSession } from "./useWorkspaceSession";

type RunProjectionSession = Pick<WorkspaceSession,
  "route" | "routeRef" | "capture" | "isCurrent" | "clearTrace" | "registerNavigationCleanup"
  | "acceptRunProgress" | "reloadCanonicalProject" | "acceptTraceEvidence"
>;

/** Submits route-current progress and trace evidence to the workspace session. */
export function useRunSession({ session, setError, describeError }: {
  session: RunProjectionSession;
  setError: (message: string) => void;
  describeError: (error: unknown) => string;
}) {
  const pollingEpochs = useRef(new Map<string, number>());
  const traceEpoch = useRef(0);
  const loadedEvidenceFor = useRef<string | undefined>(undefined);
  const loadingEvidenceFor = useRef<string | undefined>(undefined);
  const disposed = useRef(false);
  const invalidateTraceRequests = useCallback(() => {
    traceEpoch.current += 1;
    loadedEvidenceFor.current = undefined;
    loadingEvidenceFor.current = undefined;
  }, []);
  const resetTrace = useCallback(() => {
    invalidateTraceRequests();
    session.clearTrace();
  }, [invalidateTraceRequests, session]);

  useEffect(() => session.registerNavigationCleanup(invalidateTraceRequests), [invalidateTraceRequests, session.registerNavigationCleanup]);
  useEffect(() => () => {
    disposed.current = true;
    invalidateTraceRequests();
    pollingEpochs.current.clear();
  }, [invalidateTraceRequests]);

  const pollRun = useCallback(async (runId: string, projectId = session.route.project) => {
    const operation = session.capture();
    if (!projectId || operation.projectId !== projectId || pollingEpochs.current.get(runId) === operation.epoch) return;
    pollingEpochs.current.set(runId, operation.epoch);
    try {
      let keepPolling = true;
      while (keepPolling && !disposed.current) {
        const progress = await plotloomApi.getRunProgress(runId);
        if (!session.isCurrent(operation)) return;
        session.acceptRunProgress(runId, progress);
        keepPolling = progress.status === "queued" || progress.status === "running" || progress.status === "cancel_requested";
        if (keepPolling) await new Promise((resolve) => window.setTimeout(resolve, 1400));
      }
      if (projectId && session.isCurrent(operation)) await session.reloadCanonicalProject(projectId, operation.epoch);
    } catch (error) {
      if (session.isCurrent(operation)) setError(describeError(error));
    } finally {
      if (pollingEpochs.current.get(runId) === operation.epoch) pollingEpochs.current.delete(runId);
    }
  }, [describeError, session, setError]);

  const loadTraceEvidence = useCallback(async (runId: string, projectId: string) => {
    if (loadedEvidenceFor.current === runId || loadingEvidenceFor.current === runId) return;
    const operation = session.capture();
    if (operation.projectId !== projectId || operation.stage !== "trace") return;
    loadingEvidenceFor.current = runId;
    const evidenceEpoch = ++traceEpoch.current;
    try {
      const [runTrace, executionTrace] = await Promise.all([
        plotloomApi.getTrace(runId),
        plotloomApi.getRunExecutionTrace(runId).catch(() => undefined),
      ]);
      const route = session.routeRef.current;
      if (
        disposed.current
        || evidenceEpoch !== traceEpoch.current
        || !session.isCurrent(operation)
        || route.project !== projectId
        || route.stage !== "trace"
        || (route.run !== "" && route.run !== runId)
      ) return;
      session.acceptTraceEvidence(traceEvents(runTrace, executionTrace), executionTrace);
      loadedEvidenceFor.current = runId;
    } catch (error) {
      if (evidenceEpoch === traceEpoch.current && session.isCurrent(operation)) {
        setError(`无法加载运行证据：${describeError(error)}`);
      }
    } finally {
      if (loadingEvidenceFor.current === runId) loadingEvidenceFor.current = undefined;
    }
  }, [describeError, session, setError]);

  return { pollRun, loadTraceEvidence, resetTrace };
}
