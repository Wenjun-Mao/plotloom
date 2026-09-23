import type { ProductionBridgeState } from "./types";

export interface BridgeCut {
  shotId: string;
  sectionId: string;
  episode: number;
  sceneIndex: number;
  seconds: number;
  segmentIndex: number;
  segmentSceneIndex: number;
  sourceCutIndex: number;
}

function positiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0;
}

export function bridgeCut(value: Record<string, unknown>): BridgeCut | undefined {
  const source = value.source;
  if (!source || typeof source !== "object" || Array.isArray(source)) return undefined;
  const coordinates = source as Record<string, unknown>;
  if (
    typeof value.shotId !== "string" || !value.shotId ||
    typeof value.sectionId !== "string" || !value.sectionId ||
    !positiveInteger(value.episode) || !positiveInteger(value.sceneIndex) ||
    !positiveInteger(value.seconds) || !positiveInteger(coordinates.segmentIndex) ||
    !positiveInteger(coordinates.segmentSceneIndex) || !positiveInteger(coordinates.cutIndex)
  ) return undefined;
  return {
    shotId: value.shotId, sectionId: value.sectionId,
    episode: value.episode, sceneIndex: value.sceneIndex, seconds: value.seconds,
    segmentIndex: coordinates.segmentIndex, segmentSceneIndex: coordinates.segmentSceneIndex,
    sourceCutIndex: coordinates.cutIndex,
  };
}

export function currentBridgeCut(
  state: ProductionBridgeState | undefined,
  storyboardRevision: number | undefined,
  shotId: string,
): BridgeCut | undefined {
  if (
    state?.status !== "accepted" || state.staleReasons.length > 0 ||
    !storyboardRevision || state.installedStoryboardCurrent !== true ||
    state.installedStageRevisions?.storyboard !== storyboardRevision
  ) return undefined;
  return state.proposal?.cuts.map(bridgeCut).find((cut) => cut?.shotId === shotId);
}
