import { useCallback, useRef } from "react";
import { plotloomApi } from "../../api";
import { traceEvents } from "../../model";
import { quarantineItemsFromProgress } from "../../workspace-state";
import type { PipelineRun, RunExecutionTrace, RunProgress, TraceEvent, WorkspaceProject } from "../../types";
import type { PageId, WorkspaceOperation } from "./contracts";

type RouteRef = { current: { project: string; stage: PageId; run: string } };
type EpochRef = { current: number };

export function useRunSession({ loadEpoch, visibleRoute, isCurrent, setProject, setRun, setProgress, setTrace, setExecutionTrace, reloadProject, setError, describeError }: {
  loadEpoch: EpochRef;
  visibleRoute: RouteRef;
  isCurrent: (operation: WorkspaceOperation) => boolean;
  setProject: React.Dispatch<React.SetStateAction<WorkspaceProject>>;
  setRun: React.Dispatch<React.SetStateAction<PipelineRun | undefined>>;
  setProgress: React.Dispatch<React.SetStateAction<RunProgress | undefined>>;
  setTrace: React.Dispatch<React.SetStateAction<TraceEvent[]>>;
  setExecutionTrace: React.Dispatch<React.SetStateAction<RunExecutionTrace | undefined>>;
  reloadProject: (projectId: string, epoch?: number) => Promise<void>;
  setError: (message: string) => void;
  describeError: (error: unknown) => string;
}) {
  const pollingEpochs = useRef(new Map<string, number>());
  const traceEpoch = useRef(0);
  const loadedEvidenceFor = useRef<string | undefined>(undefined);
  const loadingEvidenceFor = useRef<string | undefined>(undefined);
  const resetTrace = useCallback(() => { traceEpoch.current += 1; loadedEvidenceFor.current = undefined; loadingEvidenceFor.current = undefined; setTrace([]); setExecutionTrace(undefined); }, [setExecutionTrace, setTrace]);
  const pollRun = useCallback(async (runId: string, projectIdToRefresh = visibleRoute.current.project) => {
    const pollingEpoch = loadEpoch.current;
    if (pollingEpochs.current.get(runId) === pollingEpoch) return;
    const operation: WorkspaceOperation = { epoch: pollingEpoch, projectId: projectIdToRefresh || "", stage: visibleRoute.current.stage };
    pollingEpochs.current.set(runId, pollingEpoch);
    try {
      let keepPolling = true;
      while (keepPolling) {
        const progress = await plotloomApi.getRunProgress(runId);
        if (!isCurrent(operation)) return;
        setProgress(progress);
        setRun((current) => current?.id === runId ? { ...current, status: progress.status, failureCode: progress.failureCode, failedStage: progress.failedStage } : current);
        setProject((current) => ({ ...current, quarantines: quarantineItemsFromProgress(progress) }));
        keepPolling = progress.status === "queued" || progress.status === "running" || progress.status === "cancel_requested";
        if (keepPolling) await new Promise((resolve) => window.setTimeout(resolve, 1400));
      }
      if (projectIdToRefresh && isCurrent(operation)) await reloadProject(projectIdToRefresh, operation.epoch);
    } catch (error) { if (isCurrent(operation)) setError(describeError(error)); }
    finally { if (pollingEpochs.current.get(runId) === pollingEpoch) pollingEpochs.current.delete(runId); }
  }, [describeError, isCurrent, loadEpoch, reloadProject, setError, setProgress, setProject, setRun, visibleRoute]);
  const loadTraceEvidence = useCallback(async (runId: string, projectId: string) => {
    if (loadedEvidenceFor.current === runId || loadingEvidenceFor.current === runId) return;
    loadingEvidenceFor.current = runId;
    const evidenceEpoch = ++traceEpoch.current;
    const workspaceEpoch = loadEpoch.current;
    const routeChanged = () => visibleRoute.current.project !== projectId || visibleRoute.current.stage !== "trace" || (visibleRoute.current.run !== "" && visibleRoute.current.run !== runId);
    try {
      const [runTrace, executionTrace] = await Promise.all([plotloomApi.getTrace(runId), plotloomApi.getRunExecutionTrace(runId).catch(() => undefined)]);
      if (evidenceEpoch !== traceEpoch.current || workspaceEpoch !== loadEpoch.current || routeChanged()) return;
      setTrace(traceEvents(runTrace, executionTrace)); setExecutionTrace(executionTrace); loadedEvidenceFor.current = runId;
    } catch (error) { if (evidenceEpoch === traceEpoch.current && workspaceEpoch === loadEpoch.current && !routeChanged()) setError(`无法加载运行证据：${describeError(error)}`); }
    finally { if (loadingEvidenceFor.current === runId) loadingEvidenceFor.current = undefined; }
  }, [describeError, loadEpoch, setError, setExecutionTrace, setTrace, visibleRoute]);
  return { pollRun, loadTraceEvidence, resetTrace };
}
