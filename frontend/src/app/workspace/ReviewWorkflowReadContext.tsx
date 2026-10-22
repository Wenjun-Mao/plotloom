import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import type { ArtRenderStyle, ArtReviewState, CastReviewState, ScriptReviewState, StoryboardReviewState, ProductionBridgeState } from "../../types";
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
export type StoryboardWorkflowObservation = ReviewObservation & { stage: "storyboard-review"; state?: StoryboardReviewState };
export type BridgeWorkflowObservation = ReviewObservation & { stage: "production-bridge"; state?: ProductionBridgeState; blocked: boolean; canonicalReady: boolean; canOpenShot: boolean };
export type ShotWorkflowObservation = ReviewObservation & { stage: "shot-media"; state?: undefined; shotId?: string; nextText: string; allRoutesReady: boolean };
type Observation = ScriptWorkflowObservation | ArtWorkflowObservation | CastWorkflowObservation | StoryboardWorkflowObservation | BridgeWorkflowObservation | ShotWorkflowObservation;
type ReviewStage = Exclude<Observation["stage"], "production-bridge">;
type Report = (stage: Observation["stage"], observation: Observation | undefined) => void;
const ReviewWorkflowContext = createContext<{ projectId: string; stage?: ReviewStage; report?: Report; read?: Observation; bridgeRead?: BridgeWorkflowObservation } | null>(null);

/** Observe the active review owner, without duplicating its reads or writes. */
export function ReviewWorkflowReadProvider({ projectId, revision, stage, entity, children }: {
  projectId: string; revision: number; stage?: ReviewStage; entity?: string; children: ReactNode;
}) {
  const identity = JSON.stringify([projectId, revision, stage, entity]);
  const owner = useRef({ identity });
  if (owner.current.identity !== identity) owner.current = { identity };
  const token = owner.current;
  const [read, setRead] = useState<{ owner: object; observations: Partial<Record<Observation["stage"], Observation>> }>();
  const report = useCallback<Report>((reportedStage, observation) => {
    const allowed = reportedStage === stage || stage === "storyboard-review" && reportedStage === "production-bridge";
    setRead(current => token === owner.current && stage && allowed ? { owner: token,
      observations: { ...(current?.owner === token ? current.observations : {}), [reportedStage]: observation } } : current);
  }, [identity]);
  const observations = read?.owner === owner.current ? read.observations : undefined;
  return <ReviewWorkflowContext.Provider value={{ projectId, stage, report: stage ? report : undefined,
    read: stage ? observations?.[stage] : undefined, bridgeRead: observations?.["production-bridge"] as BridgeWorkflowObservation | undefined }}>{children}</ReviewWorkflowContext.Provider>;
}

export function useReviewWorkflowRead() { return useContext(ReviewWorkflowContext)?.read; }
export function useBridgeWorkflowRead() { return useContext(ReviewWorkflowContext)?.bridgeRead; }

export function useReportReviewWorkflowRead(projectId: string, active: boolean, observation: Observation) {
  const context = useContext(ReviewWorkflowContext);
  const matchingStage = context?.stage === observation.stage || context?.stage === "storyboard-review" && observation.stage === "production-bridge";
  const report = active && context?.projectId === projectId && matchingStage ? context.report : undefined;
  const { status, state, busy, dirty, error } = observation;
  const renderStyle = observation.stage === "art" || observation.stage === "characters" ? observation.renderStyle : undefined;
  const retainedDraft = observation.stage === "art" || observation.stage === "characters" ? observation.retainedDraft : undefined;
  const designValid = observation.stage === "characters" ? observation.designValid : undefined;
  const blocked = observation.stage === "production-bridge" ? observation.blocked : undefined;
  const canonicalReady = observation.stage === "production-bridge" ? observation.canonicalReady : undefined;
  const canOpenShot = observation.stage === "production-bridge" ? observation.canOpenShot : undefined;
  const shotId = observation.stage === "shot-media" ? observation.shotId : undefined;
  const nextText = observation.stage === "shot-media" ? observation.nextText : undefined;
  const allRoutesReady = observation.stage === "shot-media" ? observation.allRoutesReady : undefined;
  useEffect(() => { report?.(observation.stage, observation); }, [report, status, state, busy, dirty, error, renderStyle, retainedDraft, designValid, blocked, canonicalReady, canOpenShot, shotId, nextText, allRoutesReady]);
  useEffect(() => () => report?.(observation.stage, undefined), [report, observation.stage]);
}
