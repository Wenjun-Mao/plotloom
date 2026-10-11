import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { ArtRenderStyle, ArtReviewState, CastReviewState, ScriptReviewState } from "../../types";
import type { ReviewContextFailure } from "../../pages/ReviewContextNotice";

interface ReviewObservation {
  status: "loading" | "failed" | "ready";
  busy: boolean;
  dirty: boolean;
  error?: ReviewContextFailure;
}
export type ScriptWorkflowObservation = ReviewObservation & { stage: "script"; state?: ScriptReviewState };
export type ArtWorkflowObservation = ReviewObservation & { stage: "art"; state?: ArtReviewState; renderStyle: ArtRenderStyle | ""; retainedDraft: boolean };
export type CastWorkflowObservation = ReviewObservation & { stage: "characters"; state?: CastReviewState; renderStyle: ArtRenderStyle | ""; retainedDraft: boolean; designValid: boolean };
type Observation = ScriptWorkflowObservation | ArtWorkflowObservation | CastWorkflowObservation;
type ReviewStage = Observation["stage"];
type Report = (observation: Observation | undefined) => void;
const ReviewWorkflowContext = createContext<{ projectId: string; stage?: ReviewStage; report?: Report; read?: Observation } | null>(null);

/** Observe the active review owner, without duplicating its reads or writes. */
export function ReviewWorkflowReadProvider({ projectId, revision, stage, children }: {
  projectId: string; revision: number; stage?: ReviewStage; children: ReactNode;
}) {
  const identity = JSON.stringify([projectId, revision, stage]);
  const owner = useRef({ identity });
  if (owner.current.identity !== identity) owner.current = { identity };
  const token = owner.current;
  const [read, setRead] = useState<{ owner: object; observation: Observation | undefined }>();
  const report = useCallback<Report>((observation) => {
    setRead(current => token === owner.current && stage && (!observation || observation.stage === stage) ? { owner: token, observation } : current);
  }, [identity]);
  return <ReviewWorkflowContext.Provider value={{ projectId, stage, report: stage ? report : undefined,
    read: read?.owner === owner.current ? read.observation : undefined }}>{children}</ReviewWorkflowContext.Provider>;
}

export function useReviewWorkflowRead() { return useContext(ReviewWorkflowContext)?.read; }

export function useReportReviewWorkflowRead(projectId: string, active: boolean, observation: Observation) {
  const context = useContext(ReviewWorkflowContext);
  const report = active && context?.projectId === projectId && context.stage === observation.stage ? context.report : undefined;
  const { status, state, busy, dirty, error } = observation;
  const renderStyle = observation.stage !== "script" ? observation.renderStyle : undefined;
  const retainedDraft = observation.stage !== "script" ? observation.retainedDraft : undefined;
  const designValid = observation.stage === "characters" ? observation.designValid : undefined;
  useEffect(() => { report?.(observation); }, [report, status, state, busy, dirty, error, renderStyle, retainedDraft, designValid]);
  useEffect(() => () => report?.(undefined), [report]);
}
