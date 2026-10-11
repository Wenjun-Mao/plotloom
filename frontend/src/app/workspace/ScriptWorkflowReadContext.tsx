import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { ScriptReviewState } from "../../types";

export interface ScriptWorkflowObservation {
  status: "loading" | "failed" | "ready";
  state?: ScriptReviewState;
  busy: boolean;
  dirty: boolean;
}
type Report = (observation: ScriptWorkflowObservation | undefined) => void;
const ScriptWorkflowContext = createContext<{ projectId: string; report?: Report; read?: ScriptWorkflowObservation } | null>(null);

/** Observe the active review owner, without duplicating its reads or writes. */
export function ScriptWorkflowReadProvider({ projectId, revision, active, children }: {
  projectId: string; revision: number; active: boolean; children: ReactNode;
}) {
  const identity = JSON.stringify([projectId, revision, active]);
  const owner = useRef({ identity });
  if (owner.current.identity !== identity) owner.current = { identity };
  const token = owner.current;
  const [read, setRead] = useState<{ owner: object; observation: ScriptWorkflowObservation | undefined }>();
  const report = useCallback<Report>((observation) => {
    setRead(current => token === owner.current && active ? { owner: token, observation } : current);
  }, [identity]);
  return <ScriptWorkflowContext.Provider value={{ projectId, report: active ? report : undefined,
    read: read?.owner === owner.current ? read.observation : undefined }}>{children}</ScriptWorkflowContext.Provider>;
}

export function useScriptWorkflowRead() { return useContext(ScriptWorkflowContext)?.read; }

export function useReportScriptWorkflowRead(projectId: string, active: boolean, observation: ScriptWorkflowObservation) {
  const context = useContext(ScriptWorkflowContext);
  const report = active && context?.projectId === projectId ? context.report : undefined;
  const { status, state, busy, dirty } = observation;
  useEffect(() => { report?.({ status, state, busy, dirty }); }, [report, status, state, busy, dirty]);
  useEffect(() => () => report?.(undefined), [report]);
}
