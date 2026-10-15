import type { AutopilotRun } from "./contracts";

type MaterialSubject = { owner: string; id: string; subjectType?: string | null };

function isMaterialSubject(value: unknown): value is MaterialSubject {
  if (!value || typeof value !== "object") return false;
  const subject = value as Record<string, unknown>;
  return typeof subject.owner === "string" && typeof subject.id === "string";
}

function operationKey(subject: MaterialSubject): string {
  return `${subject.owner}:${subject.subjectType ? `${subject.subjectType}:` : ""}${subject.id}`;
}

function inventorySubjects(run: AutopilotRun): MaterialSubject[] | null {
  const bundled = run.bundle?.inventory.subjects;
  if (Array.isArray(bundled)) return bundled.filter(isMaterialSubject);
  const checkpoint = run.checkpoints.find(item => item.operationKey === "material.inventory");
  const result = checkpoint?.evidence.result.inventory;
  if (!result || typeof result !== "object") return null;
  const subjects = (result as Record<string, unknown>).subjects;
  return Array.isArray(subjects) ? subjects.filter(isMaterialSubject) : null;
}

/** One definition for the detailed and sticky run summaries. */
export function projectAutopilotProgress(run: AutopilotRun) {
  const textStages = ["outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation"];
  const textAdopted = run.checkpoints.filter(item => textStages.includes(item.operationKey) && item.state === "adopted").length;
  const subjects = inventorySubjects(run);
  const references = new Set((subjects ?? [])
    .filter(item => item.owner !== "image")
    .map(operationKey));
  const shots = new Set((subjects ?? [])
    .filter(item => item.owner === "image")
    .map(item => item.id));
  const adoptedReferences = new Set(run.checkpoints
    .filter(item => item.state === "adopted" && ["character-reference", "art-reference"].includes(item.evidence.owner))
    .map(item => item.operationKey)
    .filter(key => references.has(key)));
  const materialStale = run.materialCurrent === false || run.state === "stale" || run.blocker?.code === "material_changed";
  const provisionalFrames = materialStale ? new Set<string>() : new Set((run.frames ?? [])
    .map(item => item.shotId)
    .filter(shotId => shots.has(shotId)));
  const retainedCandidates = new Set(run.checkpoints
    .filter(item => ["image", "character-reference", "art-reference"].includes(item.evidence.owner))
    .flatMap(item => Array.isArray(item.evidence.result.candidateAssetIds)
      ? item.evidence.result.candidateAssetIds.filter((id): id is string => typeof id === "string") : []));
  const activities = (run.activities ?? []).filter(item =>
    ["waiting", "queued", "generating", "validating", "unknown", "cancelling"].includes(item.state));
  return {
    textAdopted,
    textRequired: textStages.length,
    imagesSelected: materialStale ? 0 : adoptedReferences.size + provisionalFrames.size,
    imagesRequired: subjects?.length ?? null,
    imagesRetained: retainedCandidates.size,
    activities,
    generating: activities.filter(item => item.state === "generating").length,
    validating: activities.filter(item => item.state === "validating").length,
    queued: activities.filter(item => item.state === "queued").length,
  };
}
