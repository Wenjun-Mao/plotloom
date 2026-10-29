import { createHash } from "node:crypto";
import type { InstalledProduction, RuntimeChoice, SceneBeatPlan, VideoJob } from "../src/types";
import { frozenVideoSnapshot } from "../src/features/media/frozen-video-snapshot";
import { installedProduction } from "./production-bridge-fixture";

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value !== null && typeof value === "object") return Object.fromEntries(Object.entries(value).sort(([left],[right])=>left < right ? -1 : left > right ? 1 : 0).map(([key,item])=>[key,canonical(item)]));
  return value;
}
const digest = (value: unknown) => createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex");

/** Full F5 read identity, not a kind-only shortcut past the choice hook. */
export function bindBridgePlayback(jobs: VideoJob[], scenes: SceneBeatPlan["scenes"], choices: RuntimeChoice[], revision = 1) {
  const admissionId = `installed-${jobs[0]?.projectId}-${revision}`;
  const proposalContentHash = revision === 1 ? "a".repeat(64) : "b".repeat(64);
  const installedStageRevisions = { story_bible: revision, story_graph: revision, scene_beats: revision, storyboard: revision };
  const mappings = scenes.map((scene, index) => ({ sectionId: scene.storyNodeId, episode: index + 1, sceneIndex: 1,
    sceneId: scene.id, title: scene.title, cutCount: jobs.filter(job => (frozenVideoSnapshot(job)?.shot as { sceneId?: string })?.sceneId === scene.id).length }));
  const cuts = jobs.map((job, index) => {
    const shot = frozenVideoSnapshot(job)?.shot as { id: string; sceneId: string };
    const scene = mappings.find(item => item.sceneId === shot.sceneId)!;
    return { sectionId: scene.sectionId, episode: scene.episode, sceneIndex: scene.sceneIndex, cutIndex: 1,
      shotId: shot.id, seconds: 6, beats: [1, 1], composition: "The character holds still.",
      frame: "A cinematic still.", h3Prompt: "The character holds still.",
      source: { segmentIndex: 1, segmentSceneIndex: 1, cutIndex: index + 1 } };
  });
  const installation: InstalledProduction = installedProduction({ admissionId, proposalRevision: revision,
    proposalContentHash, installedStageRevisions, cuts, scenes: mappings, runtimeChoice: { choices } });
  const selected = jobs.map((job, index) => ({ ...job, selectionRevision: 1,
    playbackSegment: { ...job.playbackSegment!, videoJobId: job.id, shotId: cuts[index].shotId,
      derivativeHash: "c".repeat(64), selectedRevision: 1 },
    snapshot: { ...frozenVideoSnapshot(job), shot: { ...frozenVideoSnapshot(job)?.shot as object, durationUnits: 6000 },
      sourceTiming: { kind: "f5_bridge", admissionId, proposalRevision: revision, proposalContentHash,
        installedStageRevisions, cut: cuts[index], cutHash: digest(cuts[index]), durationUnits: 6000 } } }));
  return { jobs: selected, installation };
}
