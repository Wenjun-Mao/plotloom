import type {
  Beat,
  ContinuityState,
  DialogueCue,
  DramaticScene,
  EntityType,
  RequiredEntityState,
  SceneBeatPlan,
  Shot,
  ShotBeatLink,
  ValidationIssue,
} from "./types";

export type StableIdFactory = () => string;

export interface DeleteImpact {
  kind: "scene" | "beat" | "cue";
  targetId: string;
  /** IDs that will be removed after the author explicitly confirms. */
  sceneIds: string[];
  beatIds: string[];
  cueIds: string[];
  /** Parents that remain canonical but whose derived ordering changes. */
  retainedSceneIds: string[];
  retainedBeatIds: string[];
  /** Read-only later-stage relations that will become stale, never cascaded. */
  retainedStoryboardReferences: StoryboardDeletionReference[];
}

/** The Scene Beats editor intentionally receives only the storyboard fields
 * needed to disclose deletion consequences; it cannot mutate this projection. */
export interface StoryboardDeletionContext {
  shots: ReadonlyArray<Pick<Shot, "id" | "sceneId" | "cueIds">>;
  shotBeatLinks: ReadonlyArray<Pick<ShotBeatLink, "shotId" | "beatId">>;
}

export interface StoryboardDeletionReference {
  kind: "shot_scene" | "shot_beat_link" | "shot_cue_schedule";
  id: string;
  path: string;
}

/**
 * A direct parent-reference migration. It deliberately does not rewrite any
 * storyboard scheduling or coverage owned by a later stage.
 */
export interface SceneBeatsMigrationImpact {
  kind: "beat" | "cue";
  targetId: string;
  fromParentId: string;
  toParentId: string;
  affectedCueIds: string[];
  normalizedSceneIds: string[];
  normalizedBeatIds: string[];
}

export interface ContinuityJsonResult {
  value: Record<string, unknown>;
  error: string | null;
}

export type SceneBeatsEntityKind = "scene" | "beat" | "cue";

export interface SceneBeatsEntity {
  kind: SceneBeatsEntityKind;
  id: string;
}

export interface SceneBeatsIssueTarget {
  entity: SceneBeatsEntity;
  sceneId: string;
  field: string;
}

/** Shared with storyboard gate navigation: `scene:`, `beat:`, and `cue:`. */
export function sceneBeatsEntityIdentity(entity: SceneBeatsEntity): string {
  return `${entity.kind}:${encodeURIComponent(entity.id)}`;
}

export const sceneUrlIdentity = (sceneId: string) => sceneBeatsEntityIdentity({ kind: "scene", id: sceneId });

/** Accept prior bare scene routes while emitting unambiguous scene routes. */
export function sceneIdFromIdentity(identity?: string): string | undefined {
  if (!identity) return undefined;
  if (identity.startsWith("scene:")) return decodeIdentity(identity.slice("scene:".length));
  if (identity.startsWith("scene/")) return decodeURIComponent(identity.slice("scene/".length));
  return identity;
}

/** Parses all authored identities; a bare value remains a legacy scene route. */
export function parseSceneBeatsEntityIdentity(identity?: string): SceneBeatsEntity | undefined {
  if (!identity) return undefined;
  const match = /^(scene|beat|cue):(.+)$/.exec(identity);
  if (match) return { kind: match[1] as SceneBeatsEntityKind, id: decodeIdentity(match[2]) };
  if (identity.startsWith("scene/")) return { kind: "scene", id: decodeIdentity(identity.slice("scene/".length)) };
  return { kind: "scene", id: identity };
}

export function sceneBeatsFocusKey(entity: SceneBeatsEntity, field = "entity"): string {
  return `scene-beats:${entity.kind}:${encodeURIComponent(entity.id)}:${field}`;
}

/** Resolve API paths that may use canonical IDs or Pydantic array indexes. */
export function sceneBeatsIssueTarget(plan: SceneBeatPlan, issue: ValidationIssue): SceneBeatsIssueTarget | undefined {
  const [root, rawIdentity, ...rest] = issue.path.split(".");
  const field = bestIssueField(root, rest);
  if (root === "scenes") {
    const scene = resolveIssueEntity(plan.scenes, rawIdentity);
    return scene ? { entity: { kind: "scene", id: scene.id }, sceneId: scene.id, field } : undefined;
  }
  if (root === "beats") {
    const beat = resolveIssueEntity(plan.beats, rawIdentity);
    if (!beat) return undefined;
    return { entity: { kind: "beat", id: beat.id }, sceneId: beat.sceneId, field };
  }
  if (root === "dialogueCues") {
    const cue = resolveIssueEntity(plan.dialogueCues, rawIdentity);
    if (!cue) return undefined;
    const beat = plan.beats.find((item) => item.id === cue.beatId);
    return beat ? { entity: { kind: "cue", id: cue.id }, sceneId: beat.sceneId, field } : undefined;
  }
  return undefined;
}

function decodeIdentity(value: string): string {
  try { return decodeURIComponent(value); } catch { return value; }
}

function resolveIssueEntity<T extends { id: string }>(items: T[], rawIdentity: string | undefined): T | undefined {
  if (rawIdentity === undefined) return undefined;
  const byId = items.find((item) => item.id === rawIdentity);
  if (byId) return byId;
  return /^\d+$/.test(rawIdentity) ? items[Number(rawIdentity)] : undefined;
}

function bestIssueField(root: string, parts: string[]): string {
  const field = parts[0] || "entity";
  if (["entryState", "exitState"].includes(field) && parts[1]) {
    if (parts[1] === "entityStates" && parts[2]) {
      return `${field}.entityStates.${parts[2]}.${parts[3] || "entityId"}`;
    }
    if (parts[1] === "facts") return `${field}.facts${parts.length > 2 ? `.${parts.slice(2).join(".")}` : ""}`;
    return `${field}.${parts[1]}`;
  }
  if (root === "beats" && field === "continuityDelta" && parts[1]) {
    return `continuityDelta.${parts.slice(1).join(".")}`;
  }
  if (root === "dialogueCues" && ["speakerId", "voiceOver"].includes(field)) return field;
  return field;
}

export const emptyContinuityState = (note = ""): ContinuityState => ({
  facts: {}, entityStates: [], screenDirection: null, lighting: null, sound: null,
  notes: note ? [note] : [],
});

export const emptyScene = (id: string, storyNodeId = "", order = 1): DramaticScene => ({
  id, storyNodeId, order, title: "新场景", objective: "", locationId: null,
  characterIds: [], beatIds: [], durationBudgetUnits: 1000,
  entryState: emptyContinuityState(), exitState: emptyContinuityState(),
});

export const emptyBeat = (id: string, sceneId: string, order: number): Beat => ({
  id, sceneId, order, description: "", purpose: "", visibleEvent: "", immediateResult: "",
  dramaticChange: "", entryState: emptyContinuityState(), exitState: emptyContinuityState(),
  continuityAnchors: [], continuityDelta: {},
});

export const emptyCue = (id: string, beatId: string, order: number): DialogueCue => ({
  id, beatId, order, speakerId: null, voiceOver: "旁白", text: "", language: "zh-CN",
  delivery: "natural", performanceNotes: "", estimatedDurationUnits: 1000,
});

export function parseContinuityObject(raw: string): ContinuityJsonResult {
  if (!raw.trim()) return { value: {}, error: null };
  try {
    const value: unknown = JSON.parse(raw);
    if (!value || Array.isArray(value) || typeof value !== "object") {
      return { value: {}, error: "必须是 JSON 对象" };
    }
    return { value: value as Record<string, unknown>, error: null };
  } catch {
    return { value: {}, error: "不是有效 JSON 对象" };
  }
}

export function updateContinuityState(
  state: ContinuityState,
  patch: Partial<ContinuityState>,
): ContinuityState {
  return { ...state, ...patch };
}

export function updateContinuityNotes(state: ContinuityState, raw: string): ContinuityState {
  return { ...state, notes: raw.split("\n").map((item) => item.trim()).filter(Boolean) };
}

export function updateContinuityEntityStates(
  state: ContinuityState,
  entityStates: RequiredEntityState[],
): ContinuityState {
  return { ...state, entityStates: entityStates.map((item) => ({ ...item })) };
}

export function newEntityState(type: EntityType = "character"): RequiredEntityState {
  return { entityType: type, entityId: "", state: "" };
}

export function normalizeSceneBeatReferences(plan: SceneBeatPlan): SceneBeatPlan {
  const scenes = normalizeOrdersByParent(plan.scenes, (scene) => scene.storyNodeId);
  const beats = normalizeOrdersByParent(plan.beats, (beat) => beat.sceneId);
  const dialogueCues = normalizeOrdersByParent(plan.dialogueCues, (cue) => cue.beatId);
  const beatsByScene = new Map<string, Beat[]>();
  beats.forEach((beat) => beatsByScene.set(beat.sceneId, [...(beatsByScene.get(beat.sceneId) || []), beat]));
  const withReferences = scenes.map((scene) => {
    const ordered = (beatsByScene.get(scene.id) || []).slice().sort((left, right) => left.order - right.order);
    return { ...scene, beatIds: ordered.map((beat) => beat.id) };
  });
  return { ...plan, scenes: withReferences, beats, dialogueCues };
}

function orderedIds<T extends { id: string; order: number }>(items: T[]): T[] {
  return items.slice().sort((left, right) => left.order - right.order || left.id.localeCompare(right.id));
}

function replaceOrders<T extends { id: string; order: number }>(items: T[]): T[] {
  return orderedIds(items).map((item, index) => ({ ...item, order: index + 1 }));
}

function normalizeOrdersByParent<T extends { id: string; order: number }>(
  items: T[],
  parentId: (item: T) => string,
): T[] {
  const normalizedById = new Map<string, T>();
  [...new Set(items.map(parentId))].forEach((parent) => {
    replaceOrders(items.filter((item) => parentId(item) === parent)).forEach((item) => normalizedById.set(item.id, item));
  });
  return items.map((item) => normalizedById.get(item.id) || item);
}

function moveWithin<T extends { id: string; order: number }>(items: T[], id: string, direction: -1 | 1): T[] {
  const ordered = orderedIds(items);
  const index = ordered.findIndex((item) => item.id === id);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= ordered.length) return replaceOrders(ordered);
  [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
  return ordered.map((item, order) => ({ ...item, order: order + 1 }));
}

export function addScene(plan: SceneBeatPlan, factory: StableIdFactory, storyNodeId = ""): SceneBeatPlan {
  const siblingScenes = plan.scenes.filter((scene) => scene.storyNodeId === storyNodeId);
  return { ...plan, scenes: [...plan.scenes, emptyScene(factory(), storyNodeId, siblingScenes.length + 1)] };
}

export function patchScene(plan: SceneBeatPlan, sceneId: string, patch: Partial<Omit<DramaticScene, "id" | "beatIds">>): SceneBeatPlan {
  const before = plan.scenes.find((scene) => scene.id === sceneId);
  const protectedFields = patch as Partial<DramaticScene>;
  if (protectedFields.id !== undefined && protectedFields.id !== sceneId) throw new Error("scene identity is immutable");
  const scenes = plan.scenes.map((scene) => scene.id === sceneId
    ? { ...scene, ...protectedFields, id: scene.id, beatIds: scene.beatIds }
    : scene);
  if (!before || patch.storyNodeId === undefined || patch.storyNodeId === before.storyNodeId) return normalizeSceneBeatReferences({ ...plan, scenes });
  const normalized = scenes.map((scene) => ({ ...scene }));
  const affectedNodes = new Set([before.storyNodeId, patch.storyNodeId]);
  affectedNodes.forEach((nodeId) => {
    const reordered = replaceOrders(normalized.filter((scene) => scene.storyNodeId === nodeId));
    reordered.forEach((scene) => {
      const index = normalized.findIndex((item) => item.id === scene.id);
      normalized[index] = scene;
    });
  });
  return normalizeSceneBeatReferences({ ...plan, scenes: normalized });
}

export function reorderScene(plan: SceneBeatPlan, sceneId: string, direction: -1 | 1): SceneBeatPlan {
  const selected = plan.scenes.find((scene) => scene.id === sceneId);
  if (!selected) return plan;
  const reordered = moveWithin(plan.scenes.filter((scene) => scene.storyNodeId === selected.storyNodeId), sceneId, direction);
  const byId = new Map(reordered.map((scene) => [scene.id, scene]));
  return { ...plan, scenes: plan.scenes.map((scene) => byId.get(scene.id) || scene) };
}

export function addBeat(plan: SceneBeatPlan, sceneId: string, factory: StableIdFactory): SceneBeatPlan {
  const order = plan.beats.filter((beat) => beat.sceneId === sceneId).length + 1;
  return normalizeSceneBeatReferences({ ...plan, beats: [...plan.beats, emptyBeat(factory(), sceneId, order)] });
}

export function patchBeat(plan: SceneBeatPlan, beatId: string, patch: Partial<Omit<Beat, "id" | "sceneId">>): SceneBeatPlan {
  return normalizeSceneBeatReferences({
    ...plan, beats: plan.beats.map((beat) => beat.id === beatId ? { ...beat, ...patch, id: beat.id, sceneId: beat.sceneId } : beat),
  });
}

export function beatMigrationImpact(plan: SceneBeatPlan, beatId: string, targetSceneId: string): SceneBeatsMigrationImpact {
  const beat = plan.beats.find((item) => item.id === beatId);
  if (!beat) throw new Error(`unknown beat: ${beatId}`);
  if (!plan.scenes.some((scene) => scene.id === targetSceneId)) throw new Error(`unknown target scene: ${targetSceneId}`);
  return {
    kind: "beat", targetId: beatId, fromParentId: beat.sceneId, toParentId: targetSceneId,
    // Their stable beatId remains unchanged, so these cues follow the beat's
    // context without a hidden DialogueCue reassignment.
    affectedCueIds: plan.dialogueCues.filter((cue) => cue.beatId === beatId).map((cue) => cue.id).sort(),
    normalizedSceneIds: [...new Set([beat.sceneId, targetSceneId])].sort(),
    normalizedBeatIds: [beatId],
  };
}

export function migrateBeatToScene(plan: SceneBeatPlan, beatId: string, targetSceneId: string): SceneBeatPlan {
  const impact = beatMigrationImpact(plan, beatId, targetSceneId);
  if (impact.fromParentId === impact.toParentId) return normalizeSceneBeatReferences(plan);
  const nextOrder = plan.beats.filter((beat) => beat.sceneId === targetSceneId).length + 1;
  return normalizeSceneBeatReferences({
    ...plan,
    beats: plan.beats.map((beat) => beat.id === beatId
      ? { ...beat, id: beat.id, sceneId: targetSceneId, order: nextOrder }
      : beat),
  });
}

export function reorderBeat(plan: SceneBeatPlan, beatId: string, direction: -1 | 1): SceneBeatPlan {
  const selected = plan.beats.find((beat) => beat.id === beatId);
  if (!selected) return plan;
  const reordered = moveWithin(plan.beats.filter((beat) => beat.sceneId === selected.sceneId), beatId, direction);
  const byId = new Map(reordered.map((beat) => [beat.id, beat]));
  return normalizeSceneBeatReferences({ ...plan, beats: plan.beats.map((beat) => byId.get(beat.id) || beat) });
}

export function addCue(plan: SceneBeatPlan, beatId: string, factory: StableIdFactory): SceneBeatPlan {
  const order = plan.dialogueCues.filter((cue) => cue.beatId === beatId).length + 1;
  return { ...plan, dialogueCues: [...plan.dialogueCues, emptyCue(factory(), beatId, order)] };
}

export function patchCue(plan: SceneBeatPlan, cueId: string, patch: Partial<Omit<DialogueCue, "id" | "beatId">>): SceneBeatPlan {
  const protectedFields = patch as Partial<DialogueCue>;
  if (protectedFields.id !== undefined && protectedFields.id !== cueId) throw new Error("dialogue cue identity is immutable");
  if (protectedFields.beatId !== undefined && protectedFields.beatId !== plan.dialogueCues.find((cue) => cue.id === cueId)?.beatId) {
    throw new Error("use migrateCueToBeat to change a cue beat");
  }
  const next = plan.dialogueCues.map((cue) => cue.id === cueId
    ? { ...cue, ...protectedFields, id: cue.id, beatId: cue.beatId }
    : cue);
  return normalizeSceneBeatReferences({ ...plan, dialogueCues: next });
}

export function cueMigrationImpact(plan: SceneBeatPlan, cueId: string, targetBeatId: string): SceneBeatsMigrationImpact {
  const cue = plan.dialogueCues.find((item) => item.id === cueId);
  if (!cue) throw new Error(`unknown dialogue cue: ${cueId}`);
  if (!plan.beats.some((beat) => beat.id === targetBeatId)) throw new Error(`unknown target beat: ${targetBeatId}`);
  const targetSceneId = plan.beats.find((beat) => beat.id === targetBeatId)!.sceneId;
  return {
    kind: "cue", targetId: cueId, fromParentId: cue.beatId, toParentId: targetBeatId,
    affectedCueIds: [cueId], normalizedSceneIds: [targetSceneId],
    normalizedBeatIds: [...new Set([cue.beatId, targetBeatId])].sort(),
  };
}

export function migrateCueToBeat(plan: SceneBeatPlan, cueId: string, targetBeatId: string): SceneBeatPlan {
  const impact = cueMigrationImpact(plan, cueId, targetBeatId);
  if (impact.fromParentId === impact.toParentId) return normalizeSceneBeatReferences(plan);
  const nextOrder = plan.dialogueCues.filter((cue) => cue.beatId === targetBeatId).length + 1;
  return normalizeSceneBeatReferences({
    ...plan,
    dialogueCues: plan.dialogueCues.map((cue) => cue.id === cueId
      ? { ...cue, id: cue.id, beatId: targetBeatId, order: nextOrder }
      : cue),
  });
}

export function reorderCue(plan: SceneBeatPlan, cueId: string, direction: -1 | 1): SceneBeatPlan {
  const selected = plan.dialogueCues.find((cue) => cue.id === cueId);
  if (!selected) return plan;
  const reordered = moveWithin(plan.dialogueCues.filter((cue) => cue.beatId === selected.beatId), cueId, direction);
  const byId = new Map(reordered.map((cue) => [cue.id, cue]));
  return { ...plan, dialogueCues: plan.dialogueCues.map((cue) => byId.get(cue.id) || cue) };
}

function retainedStoryboardReferences(
  storyboard: StoryboardDeletionContext | undefined,
  removed: Pick<DeleteImpact, "sceneIds" | "beatIds" | "cueIds">,
): StoryboardDeletionReference[] {
  if (!storyboard) return [];
  const removedScenes = new Set(removed.sceneIds);
  const removedBeats = new Set(removed.beatIds);
  const removedCues = new Set(removed.cueIds);
  const references: StoryboardDeletionReference[] = [];
  storyboard.shots.forEach((shot) => {
    if (removedScenes.has(shot.sceneId)) {
      references.push({ kind: "shot_scene", id: shot.id, path: `storyboard.shots.${shot.id}.sceneId` });
    }
    shot.cueIds.filter((cueId) => removedCues.has(cueId)).forEach((cueId) => {
      references.push({ kind: "shot_cue_schedule", id: shot.id, path: `storyboard.shots.${shot.id}.cueIds.${cueId}` });
    });
  });
  storyboard.shotBeatLinks.filter((link) => removedBeats.has(link.beatId)).forEach((link) => {
    const id = `${link.shotId}:${link.beatId}`;
    references.push({ kind: "shot_beat_link", id, path: `storyboard.shotBeatLinks.${id}` });
  });
  return references.sort((left, right) => left.path.localeCompare(right.path));
}

export function sceneDeleteImpact(
  plan: SceneBeatPlan,
  sceneId: string,
  storyboard?: StoryboardDeletionContext,
): DeleteImpact {
  const beatIds = plan.beats.filter((beat) => beat.sceneId === sceneId).map((beat) => beat.id);
  const impact = {
    kind: "scene", targetId: sceneId, sceneIds: [sceneId], beatIds,
    cueIds: plan.dialogueCues.filter((cue) => beatIds.includes(cue.beatId)).map((cue) => cue.id),
    retainedSceneIds: [], retainedBeatIds: [], retainedStoryboardReferences: [],
  } satisfies DeleteImpact;
  return { ...impact, retainedStoryboardReferences: retainedStoryboardReferences(storyboard, impact) };
}

export function beatDeleteImpact(
  plan: SceneBeatPlan,
  beatId: string,
  storyboard?: StoryboardDeletionContext,
): DeleteImpact {
  const beat = plan.beats.find((item) => item.id === beatId);
  const impact = {
    kind: "beat", targetId: beatId, sceneIds: [], beatIds: beat ? [beatId] : [],
    cueIds: plan.dialogueCues.filter((cue) => cue.beatId === beatId).map((cue) => cue.id),
    retainedSceneIds: beat ? [beat.sceneId] : [], retainedBeatIds: [], retainedStoryboardReferences: [],
  } satisfies DeleteImpact;
  return { ...impact, retainedStoryboardReferences: retainedStoryboardReferences(storyboard, impact) };
}

export function cueDeleteImpact(
  plan: SceneBeatPlan,
  cueId: string,
  storyboard?: StoryboardDeletionContext,
): DeleteImpact {
  const cue = plan.dialogueCues.find((item) => item.id === cueId);
  const beat = cue ? plan.beats.find((item) => item.id === cue.beatId) : undefined;
  const impact = {
    kind: "cue", targetId: cueId, sceneIds: [], beatIds: [], cueIds: cue ? [cueId] : [],
    retainedSceneIds: beat ? [beat.sceneId] : [], retainedBeatIds: cue ? [cue.beatId] : [], retainedStoryboardReferences: [],
  } satisfies DeleteImpact;
  return { ...impact, retainedStoryboardReferences: retainedStoryboardReferences(storyboard, impact) };
}

export function applyDeleteImpact(plan: SceneBeatPlan, impact: DeleteImpact): SceneBeatPlan {
  const beatIds = new Set(impact.beatIds);
  const cueIds = new Set(impact.cueIds);
  const scenes = plan.scenes.filter((scene) => !impact.sceneIds.includes(scene.id));
  const beats = plan.beats.filter((beat) => !beatIds.has(beat.id));
  const dialogueCues = plan.dialogueCues.filter((cue) => !cueIds.has(cue.id));
  const reindexedScenes = scenes.map((scene) => scene);
  [...new Set(reindexedScenes.map((scene) => scene.storyNodeId))].forEach((nodeId) => {
    const reordered = replaceOrders(reindexedScenes.filter((scene) => scene.storyNodeId === nodeId));
    reordered.forEach((scene) => {
      const index = reindexedScenes.findIndex((item) => item.id === scene.id);
      reindexedScenes[index] = scene;
    });
  });
  const reindexedBeats = beats.map((beat) => beat);
  [...new Set(reindexedBeats.map((beat) => beat.sceneId))].forEach((sceneId) => {
    const reordered = replaceOrders(reindexedBeats.filter((beat) => beat.sceneId === sceneId));
    reordered.forEach((beat) => {
      const index = reindexedBeats.findIndex((item) => item.id === beat.id);
      reindexedBeats[index] = beat;
    });
  });
  const reindexedCues = dialogueCues.map((cue) => cue);
  [...new Set(reindexedCues.map((cue) => cue.beatId))].forEach((beatId) => {
    const reordered = replaceOrders(reindexedCues.filter((cue) => cue.beatId === beatId));
    reordered.forEach((cue) => {
      const index = reindexedCues.findIndex((item) => item.id === cue.id);
      reindexedCues[index] = cue;
    });
  });
  return normalizeSceneBeatReferences({ ...plan, scenes: reindexedScenes, beats: reindexedBeats, dialogueCues: reindexedCues });
}
