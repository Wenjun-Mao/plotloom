import type { InstalledProduction, VideoJob } from "../../types";
import { frozenVideoSnapshot } from "./frozen-video-snapshot";
import { isCurrentVideoSelection } from "./video-next-action";

const record = (value: unknown): Record<string, unknown> | null =>
  value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
const positive = (value: unknown): value is number => typeof value === "number" && Number.isInteger(value) && value > 0;
const hash = (value: unknown) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
function ordered(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(ordered);
  const object = record(value);
  return object ? Object.fromEntries(Object.keys(object).sort().map(key => [key, ordered(object[key])])) : value;
}
const equal = (left: unknown, right: unknown) => JSON.stringify(ordered(left)) === JSON.stringify(ordered(right));

/** Exact passive read identity; generation-policy currentness grants no playback authority. */
export function bridgePlaybackProof(job: VideoJob) {
  const snapshot = frozenVideoSnapshot(job), shot = record(snapshot?.shot), segment = job.playbackSegment;
  return { id: job.id, projectId: job.projectId, selectionRevision: job.selectionRevision,
    shot: { id: shot?.id, sceneId: shot?.sceneId, durationUnits: shot?.durationUnits },
    sourceTiming: snapshot?.sourceTiming,
    segment: segment && { id: segment.id, videoJobId: segment.videoJobId, shotId: segment.shotId,
      selectedRevision: segment.selectedRevision, derivativeHash: segment.derivativeHash,
      authoredDurationUnits: segment.authoredDurationUnits } };
}

/**
 * The fresh media read reuses the backend's selected-playback source, installation,
 * approval and segment guards. Recorded installation metadata supplies choices only
 * after every displayed clip is rebound to that exact complete installed cut set.
 * An outdated generation installation alone never grants this passive admission.
 */
export function selectedBridgeChoicesEligible(
  projectId: string, installation: InstalledProduction | null | undefined,
  displayed: readonly VideoJob[], fresh: readonly VideoJob[],
): boolean {
  if (!installation || !displayed.length || !installation.runtimeChoice
    || !installation.admissionId || !positive(installation.proposalRevision) || !hash(installation.proposalContentHash)
    || (installation.status === "current" ? installation.staleReasons.length !== 0
      : installation.status !== "outdated" || installation.staleReasons.length === 0)) return false;
  const stages = installation.installedStageRevisions;
  if (!equal(Object.keys(stages).sort(), ["scene_beats", "story_bible", "story_graph", "storyboard"])
    || !Object.values(stages).every(positive)) return false;
  const wanted = new Set(displayed.map(job => job.id));
  const selected = fresh.filter(job => wanted.has(job.id));
  if (wanted.size !== displayed.length || selected.length !== displayed.length
    || new Set(selected.map(job => job.id)).size !== displayed.length) return false;
  const cuts = installation.cuts;
  if (cuts.length !== displayed.length || new Set(cuts.map(cut => cut.shotId)).size !== cuts.length) return false;
  const shots = new Set<unknown>();
  return displayed.every(job => {
    const current = selected.find(item => item.id === job.id);
    if (!current || job.projectId !== projectId || current.projectId !== projectId
      || !isCurrentVideoSelection(job) || !isCurrentVideoSelection(current)
      || !equal(bridgePlaybackProof(job), bridgePlaybackProof(current))) return false;
    const snapshot = frozenVideoSnapshot(current), shot = record(snapshot?.shot), source = record(snapshot?.sourceTiming);
    const cut = record(source?.cut), segment = current.playbackSegment;
    if (!shot || !source || !cut || !segment || typeof shot.id !== "string" || !shot.id || shots.has(shot.id)) return false;
    shots.add(shot.id);
    const installed = cuts.find(item => item.shotId === shot.id);
    const scenes = installation.scenes.filter(item => item.sectionId === cut.sectionId
      && item.episode === cut.episode && item.sceneIndex === cut.sceneIndex);
    return source.kind === "f5_bridge" && source.admissionId === installation.admissionId
      && source.proposalRevision === installation.proposalRevision && source.proposalContentHash === installation.proposalContentHash
      && equal(source.installedStageRevisions, stages) && hash(source.cutHash) && equal(cut, installed)
      && scenes.length === 1 && scenes[0].sceneId === shot.sceneId
      && positive(shot.durationUnits) && source.durationUnits === shot.durationUnits
      && segment.authoredDurationUnits === shot.durationUnits && segment.videoJobId === current.id && segment.shotId === shot.id
      && hash(segment.derivativeHash) && positive(current.selectionRevision) && segment.selectedRevision === current.selectionRevision;
  });
}
