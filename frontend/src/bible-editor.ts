import type {
  CharacterCard,
  LocationCard,
  PropCard,
  RequiredEntityState,
  SceneBeatPlan,
  StoryBible,
  Storyboard,
  ValidationIssue,
} from "./types";

export type BibleEntityType = "character" | "location" | "prop";
export type BibleEntity = CharacterCard | LocationCard | PropCard;

export interface BibleEntitySelection {
  type: BibleEntityType;
  id: string;
}

export interface BibleReferenceContext {
  sceneBeats?: SceneBeatPlan;
  storyboard?: Storyboard;
}

export interface BibleReferenceImpact {
  kind: "scene" | "shot" | "state" | "cue";
  id: string;
  path: string;
  message: string;
}

export interface BibleIssueTarget {
  field: string;
  entity?: BibleEntitySelection;
}

export interface DeleteBibleEntityResult {
  deleted: boolean;
  bible: StoryBible;
  impacts: BibleReferenceImpact[];
}

const entityCollections: Record<BibleEntityType, keyof Pick<StoryBible, "characters" | "locations" | "props">> = {
  character: "characters",
  location: "locations",
  prop: "props",
};

const entityPrefixes: Record<BibleEntityType, string> = {
  character: "character",
  location: "location",
  prop: "prop",
};

export function entityUrlIdentity(type: BibleEntityType, id: string): string {
  return `bible:${type}:${id}`;
}

export function entityForIdentity(bible: StoryBible, identity?: string): BibleEntitySelection | undefined {
  if (!identity) return undefined;
  const namespaced = /^bible:(character|location|prop):(.+)$/.exec(identity);
  if (namespaced) {
    const type = namespaced[1] as BibleEntityType;
    const id = namespaced[2];
    return bible[entityCollections[type]].some((entity) => entity.id === id) ? { type, id } : undefined;
  }

  // Older links only stored an entity ID. Preserve them until they are replaced
  // by a type-qualified identity, preferring the canonical collection order.
  for (const type of ["character", "location", "prop"] as const) {
    if (bible[entityCollections[type]].some((entity) => entity.id === identity)) return { type, id: identity };
  }
  return undefined;
}

export function entityBySelection(bible: StoryBible, selection?: BibleEntitySelection): BibleEntity | undefined {
  if (!selection) return undefined;
  return bible[entityCollections[selection.type]].find((entity) => entity.id === selection.id);
}

export function addBibleEntity(
  bible: StoryBible,
  type: BibleEntityType,
  id: string,
): StoryBible {
  const base = { id, name: "未命名实体", description: "", visualAnchors: [], soundAnchors: [], allowedStates: [], continuityRules: [] };
  const entity: BibleEntity = type === "character"
    ? { ...base, role: null, goal: "", traits: [], voiceAnchors: [] }
    : base;
  const collection = entityCollections[type];
  return { ...bible, [collection]: [...bible[collection], entity] } as StoryBible;
}

export function updateBibleEntity(
  bible: StoryBible,
  selection: BibleEntitySelection,
  patch: Partial<BibleEntity>,
): StoryBible {
  const collection = entityCollections[selection.type];
  return {
    ...bible,
    [collection]: bible[collection].map((entity) => entity.id === selection.id ? { ...entity, ...patch } : entity),
  } as StoryBible;
}

function stateImpacts(
  states: RequiredEntityState[] | undefined,
  selection: BibleEntitySelection,
  owner: "scene" | "beat" | "shot",
  ownerId: string,
  statePath: string,
): BibleReferenceImpact[] {
  return (states ?? [])
    .filter((state) => state.entityType === selection.type && state.entityId === selection.id)
    .map((state, index) => ({
      kind: "state" as const,
      id: ownerId,
      path: `${statePath}.entityStates.${index}`,
      message: `${owner} ${ownerId} requires ${entityPrefixes[selection.type]} state “${state.state}”`,
    }));
}

/** Return every known authored reference; callers must resolve them before deletion. */
export function bibleEntityImpacts(
  selection: BibleEntitySelection,
  context: BibleReferenceContext = {},
): BibleReferenceImpact[] {
  const impacts: BibleReferenceImpact[] = [];
  const { sceneBeats, storyboard } = context;

  for (const scene of sceneBeats?.scenes ?? []) {
    if (selection.type === "character" && scene.characterIds.includes(selection.id)) {
      impacts.push({ kind: "scene", id: scene.id, path: `scenes.${scene.id}.characterIds`, message: `scene ${scene.id} casts this character` });
    }
    if (selection.type === "location" && scene.locationId === selection.id) {
      impacts.push({ kind: "scene", id: scene.id, path: `scenes.${scene.id}.locationId`, message: `scene ${scene.id} takes place at this location` });
    }
    impacts.push(...stateImpacts(scene.entryState?.entityStates, selection, "scene", scene.id, `scenes.${scene.id}.entryState`));
    impacts.push(...stateImpacts(scene.exitState?.entityStates, selection, "scene", scene.id, `scenes.${scene.id}.exitState`));
  }
  for (const beat of sceneBeats?.beats ?? []) {
    impacts.push(...stateImpacts(beat.entryState?.entityStates, selection, "beat", beat.id, `beats.${beat.id}.entryState`));
    impacts.push(...stateImpacts(beat.exitState?.entityStates, selection, "beat", beat.id, `beats.${beat.id}.exitState`));
  }
  if (selection.type === "character") {
    for (const cue of sceneBeats?.dialogueCues ?? []) {
      if (cue.speakerId === selection.id) {
        impacts.push({ kind: "cue", id: cue.id, path: `dialogueCues.${cue.id}.speakerId`, message: `cue ${cue.id} names this character as speaker` });
      }
    }
  }
  for (const shot of storyboard?.shots ?? []) {
    const directReference = selection.type === "character"
      ? shot.characterIds.includes(selection.id)
      : selection.type === "location"
        ? shot.locationId === selection.id
        : shot.propIds.includes(selection.id);
    if (directReference) {
      const field = selection.type === "character" ? "characterIds" : selection.type === "location" ? "locationId" : "propIds";
      impacts.push({ kind: "shot", id: shot.id, path: `shots.${shot.id}.${field}`, message: `shot ${shot.id} references this ${selection.type}` });
    }
    impacts.push(...stateImpacts(shot.requiredEntityStates, selection, "shot", shot.id, `shots.${shot.id}.requiredEntityStates`));
    impacts.push(...stateImpacts(shot.entryState?.entityStates, selection, "shot", shot.id, `shots.${shot.id}.entryState`));
    impacts.push(...stateImpacts(shot.exitState?.entityStates, selection, "shot", shot.id, `shots.${shot.id}.exitState`));
  }
  return impacts;
}

export function deleteBibleEntity(
  bible: StoryBible,
  selection: BibleEntitySelection,
  context?: BibleReferenceContext,
): DeleteBibleEntityResult {
  const impacts = bibleEntityImpacts(selection, context);
  if (impacts.length) return { deleted: false, bible, impacts };
  const collection = entityCollections[selection.type];
  return {
    deleted: true,
    bible: { ...bible, [collection]: bible[collection].filter((entity) => entity.id !== selection.id) } as StoryBible,
    impacts,
  };
}

export function issueTargetForPath(bible: StoryBible, path: ValidationIssue["path"]): BibleIssueTarget | undefined {
  const normalized = path.replace(/^storyBible\./, "");
  const match = /^(characters|locations|props)\.([^.]+)(?:\.(.*))?$/.exec(normalized);
  if (!match) return normalized ? { field: normalized.split(".")[0] } : undefined;
  const type = match[1] === "characters" ? "character" : match[1] === "locations" ? "location" : "prop";
  const collection = bible[entityCollections[type]];
  const token = match[2];
  const entity = /^\d+$/.test(token) ? collection[Number(token)] : collection.find((candidate) => candidate.id === token);
  return entity ? { entity: { type, id: entity.id }, field: (match[3] ?? "entity").split(".")[0] } : { field: normalized.split(".")[0] };
}
