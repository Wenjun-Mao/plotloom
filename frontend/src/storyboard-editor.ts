import type {
  AudioEvent,
  Beat,
  DialogueCue,
  SceneBeatPlan,
  Shot,
  ShotBeatLink,
  Storyboard,
  ValidationIssue,
} from "./types";

export type StoryboardEntity =
  | { kind: "shot"; shotId: string }
  | { kind: "link"; shotId: string; beatId: string };

export interface StoryboardIssueTarget {
  entity: StoryboardEntity;
  field: string;
}

export interface ShotRemovalImpact {
  shotId: string;
  linkBeatIds: string[];
  unscheduledCueIds: string[];
}

export interface BeatCoverage {
  beatId: string;
  primaryShotIds: string[];
  supportingShotIds: string[];
}

/**
 * A scene migration changes only Shot.sceneId. Cue scheduling and coverage are
 * retained for deliberate follow-up edits, never silently removed or moved.
 */
export interface ShotSceneMigrationImpact {
  shotId: string;
  fromSceneId: string;
  toSceneId: string;
  crossSceneCueIds: string[];
  crossSceneLinkKeys: string[];
  normalizedSceneIds: string[];
}

export function encodeStoryboardEntity(entity: StoryboardEntity): string {
  return entity.kind === "shot"
    ? `shot:${entity.shotId}`
    : `link:${entity.shotId}:${entity.beatId}`;
}

export function parseStoryboardEntity(value: string): StoryboardEntity | undefined {
  if (value.startsWith("shot:")) {
    const shotId = value.slice(5);
    return shotId ? { kind: "shot", shotId } : undefined;
  }
  if (value.startsWith("link:")) {
    const [shotId, beatId, ...rest] = value.slice(5).split(":");
    return shotId && beatId && rest.length === 0
      ? { kind: "link", shotId, beatId }
      : undefined;
  }
  // M1-B0 wrote bare shot IDs into the URL. Keep those bookmarks readable.
  return value ? { kind: "shot", shotId: value } : undefined;
}

export function storyboardFocusKey(target: StoryboardIssueTarget): string {
  return target.entity.kind === "shot"
    ? `storyboard:shot:${target.entity.shotId}:${target.field}`
    : `storyboard:link:${target.entity.shotId}:${target.entity.beatId}:${target.field}`;
}

export function createShot(
  id: string,
  sceneId: string,
  order: number,
  defaults: Pick<Shot, "characterIds" | "locationId" | "entryState" | "exitState">,
): Shot {
  return {
    id,
    sceneId,
    order,
    title: "新镜头",
    shotSize: "medium",
    durationUnits: 1000,
    cameraAngle: "平视",
    cameraMovement: "固定",
    composition: "",
    visualIntent: "",
    motionIntent: "",
    action: "",
    transition: "硬切",
    characterIds: [...defaults.characterIds],
    locationId: defaults.locationId,
    propIds: [],
    cueIds: [],
    audioPlan: { events: [] },
    requiredEntityStates: [],
    entryState: structuredClone(defaults.entryState),
    exitState: structuredClone(defaults.exitState),
  };
}

export function addShot(storyboard: Storyboard, shot: Shot): Storyboard {
  if (storyboard.shots.some((candidate) => candidate.id === shot.id)) {
    throw new Error(`duplicate shot id: ${shot.id}`);
  }
  return { ...storyboard, shots: [...storyboard.shots, shot] };
}

export function patchShot(
  storyboard: Storyboard,
  shotId: string,
  patch: Partial<Omit<Shot, "id" | "sceneId" | "order">>,
): Storyboard {
  const protectedFields = patch as Partial<Shot>;
  const current = storyboard.shots.find((shot) => shot.id === shotId);
  if (protectedFields.id !== undefined && protectedFields.id !== shotId) {
    throw new Error("shot identity is immutable");
  }
  if (protectedFields.sceneId !== undefined && protectedFields.sceneId !== current?.sceneId) {
    throw new Error("use migrateShotToScene to change a shot scene");
  }
  if (protectedFields.order !== undefined && protectedFields.order !== current?.order) {
    throw new Error("use moveShot to change a shot order");
  }
  const { id: _id, sceneId: _sceneId, order: _order, ...editable } = protectedFields;
  return {
    ...storyboard,
    shots: storyboard.shots.map((shot) =>
      shot.id === shotId ? { ...shot, ...editable, id: shot.id, sceneId: shot.sceneId, order: shot.order } : shot,
    ),
  };
}

export function shotSceneMigrationImpact(
  storyboard: Storyboard,
  plan: Pick<SceneBeatPlan, "scenes" | "beats" | "dialogueCues">,
  shotId: string,
  targetSceneId: string,
): ShotSceneMigrationImpact {
  const shot = storyboard.shots.find((candidate) => candidate.id === shotId);
  if (!shot) throw new Error(`unknown shot: ${shotId}`);
  if (!plan.scenes.some((scene) => scene.id === targetSceneId)) {
    throw new Error(`unknown target scene: ${targetSceneId}`);
  }
  const beatSceneById = new Map(plan.beats.map((beat) => [beat.id, beat.sceneId]));
  const cueSceneById = new Map(plan.dialogueCues.map((cue) => [cue.id, beatSceneById.get(cue.beatId)]));
  return {
    shotId,
    fromSceneId: shot.sceneId,
    toSceneId: targetSceneId,
    crossSceneCueIds: shot.cueIds.filter((cueId) => cueSceneById.get(cueId) !== targetSceneId).sort(),
    crossSceneLinkKeys: storyboard.shotBeatLinks
      .filter((link) => link.shotId === shotId && beatSceneById.get(link.beatId) !== targetSceneId)
      .map((link) => `${link.shotId}:${link.beatId}`)
      .sort(),
    normalizedSceneIds: [...new Set([shot.sceneId, targetSceneId])].sort(),
  };
}

export function migrateShotToScene(
  storyboard: Storyboard,
  shotId: string,
  targetSceneId: string,
): Storyboard {
  const shot = storyboard.shots.find((candidate) => candidate.id === shotId);
  if (!shot) throw new Error(`unknown shot: ${shotId}`);
  if (!targetSceneId) throw new Error("target scene ID must not be blank");
  if (shot.sceneId === targetSceneId) return normalizeShotOrders(storyboard);
  const nextOrder = storyboard.shots.filter((candidate) => candidate.sceneId === targetSceneId).length + 1;
  return normalizeShotOrders({
    ...storyboard,
    shots: storyboard.shots.map((candidate) => candidate.id === shotId
      ? { ...candidate, id: candidate.id, sceneId: targetSceneId, order: nextOrder }
      : candidate),
  });
}

export function moveShot(
  storyboard: Storyboard,
  shotId: string,
  direction: -1 | 1,
): Storyboard {
  const selected = storyboard.shots.find((shot) => shot.id === shotId);
  if (!selected) return storyboard;
  const ordered = storyboard.shots
    .filter((shot) => shot.sceneId === selected.sceneId)
    .sort((left, right) => left.order - right.order || left.id.localeCompare(right.id));
  const index = ordered.findIndex((shot) => shot.id === shotId);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= ordered.length) return storyboard;
  [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
  const orderById = new Map(ordered.map((shot, position) => [shot.id, position + 1]));
  return {
    ...storyboard,
    shots: storyboard.shots.map((shot) =>
      shot.sceneId === selected.sceneId
        ? { ...shot, order: orderById.get(shot.id)! }
        : shot,
    ),
  };
}

export function normalizeShotOrders(storyboard: Storyboard): Storyboard {
  const byId = new Map<string, Shot>();
  [...new Set(storyboard.shots.map((shot) => shot.sceneId))].forEach((sceneId) => {
    storyboard.shots
      .filter((shot) => shot.sceneId === sceneId)
      .slice()
      .sort((left, right) => left.order - right.order || left.id.localeCompare(right.id))
      .forEach((shot, index) => byId.set(shot.id, { ...shot, order: index + 1 }));
  });
  return { ...storyboard, shots: storyboard.shots.map((shot) => byId.get(shot.id) || shot) };
}

export function shotRemovalImpact(
  storyboard: Storyboard,
  shotId: string,
): ShotRemovalImpact {
  const shot = storyboard.shots.find((candidate) => candidate.id === shotId);
  return {
    shotId,
    linkBeatIds: storyboard.shotBeatLinks
      .filter((link) => link.shotId === shotId)
      .map((link) => link.beatId),
    unscheduledCueIds: shot ? [...shot.cueIds] : [],
  };
}

export function removeShot(storyboard: Storyboard, shotId: string): Storyboard {
  const selected = storyboard.shots.find((shot) => shot.id === shotId);
  if (!selected) return storyboard;
  const remaining = storyboard.shots.filter((shot) => shot.id !== shotId);
  const ordered = remaining
    .filter((shot) => shot.sceneId === selected.sceneId)
    .sort((left, right) => left.order - right.order || left.id.localeCompare(right.id));
  const orderById = new Map(ordered.map((shot, index) => [shot.id, index + 1]));
  return {
    shots: remaining.map((shot) =>
      shot.sceneId === selected.sceneId
        ? { ...shot, order: orderById.get(shot.id)! }
        : shot,
    ),
    // This is the only cascade, and the caller must show it from
    // shotRemovalImpact before applying the mutation.
    shotBeatLinks: storyboard.shotBeatLinks.filter((link) => link.shotId !== shotId),
  };
}

export function cueSchedule(storyboard: Storyboard): Map<string, string[]> {
  const schedule = new Map<string, string[]>();
  for (const shot of storyboard.shots) {
    for (const cueId of shot.cueIds) {
      schedule.set(cueId, [...(schedule.get(cueId) ?? []), shot.id]);
    }
  }
  return schedule;
}

export function assignCue(
  storyboard: Storyboard,
  shotId: string,
  cueId: string,
): Storyboard {
  const scheduledBy = cueSchedule(storyboard).get(cueId) ?? [];
  if (scheduledBy.some((candidate) => candidate !== shotId)) {
    throw new Error(`cue ${cueId} is already scheduled by ${scheduledBy.join(", ")}`);
  }
  const shot = storyboard.shots.find((candidate) => candidate.id === shotId);
  if (!shot || shot.cueIds.includes(cueId)) return storyboard;
  return patchShot(storyboard, shotId, { cueIds: [...shot.cueIds, cueId] });
}

export function unassignCue(
  storyboard: Storyboard,
  shotId: string,
  cueId: string,
): Storyboard {
  const shot = storyboard.shots.find((candidate) => candidate.id === shotId);
  if (!shot) return storyboard;
  return patchShot(storyboard, shotId, {
    cueIds: shot.cueIds.filter((candidate) => candidate !== cueId),
  });
}

export function addShotBeatLink(
  storyboard: Storyboard,
  link: ShotBeatLink,
): Storyboard {
  if (
    storyboard.shotBeatLinks.some(
      (candidate) =>
        candidate.shotId === link.shotId && candidate.beatId === link.beatId,
    )
  ) {
    throw new Error("this shot-to-beat relationship already exists");
  }
  if (
    link.role === "primary" &&
    storyboard.shotBeatLinks.some(
      (candidate) => candidate.beatId === link.beatId && candidate.role === "primary",
    )
  ) {
    throw new Error(`beat ${link.beatId} already has a PRIMARY shot`);
  }
  return {
    ...storyboard,
    shotBeatLinks: [...storyboard.shotBeatLinks, link],
  };
}

export function patchShotBeatLink(
  storyboard: Storyboard,
  shotId: string,
  beatId: string,
  patch: Pick<Partial<ShotBeatLink>, "role" | "coverageWeight">,
): Storyboard {
  if (
    patch.role === "primary" &&
    storyboard.shotBeatLinks.some(
      (candidate) =>
        candidate.beatId === beatId &&
        candidate.role === "primary" &&
        candidate.shotId !== shotId,
    )
  ) {
    throw new Error(`beat ${beatId} already has a PRIMARY shot`);
  }
  return {
    ...storyboard,
    shotBeatLinks: storyboard.shotBeatLinks.map((link) =>
      link.shotId === shotId && link.beatId === beatId
        ? { ...link, ...patch, shotId, beatId }
        : link,
    ),
  };
}

export function removeShotBeatLink(
  storyboard: Storyboard,
  shotId: string,
  beatId: string,
): Storyboard {
  return {
    ...storyboard,
    shotBeatLinks: storyboard.shotBeatLinks.filter(
      (link) => link.shotId !== shotId || link.beatId !== beatId,
    ),
  };
}

export function beatCoverage(
  storyboard: Storyboard,
  beats: Beat[],
): BeatCoverage[] {
  return beats.map((beat) => {
    const links = storyboard.shotBeatLinks.filter((link) => link.beatId === beat.id);
    return {
      beatId: beat.id,
      primaryShotIds: links.filter((link) => link.role === "primary").map((link) => link.shotId),
      supportingShotIds: links.filter((link) => link.role === "supporting").map((link) => link.shotId),
    };
  });
}

export function addAudioEvent(shot: Shot, event: AudioEvent): Shot {
  if (shot.audioPlan.events.some((candidate) => candidate.id === event.id)) {
    throw new Error(`duplicate audio event id: ${event.id}`);
  }
  return {
    ...shot,
    audioPlan: { events: [...shot.audioPlan.events, event] },
  };
}

export function patchAudioEvent(
  shot: Shot,
  eventId: string,
  patch: Partial<AudioEvent>,
): Shot {
  if (patch.id !== undefined && patch.id !== eventId) {
    throw new Error("audio event identity is immutable");
  }
  return {
    ...shot,
    audioPlan: {
      events: shot.audioPlan.events.map((event) =>
        event.id === eventId ? { ...event, ...patch, id: event.id } : event,
      ),
    },
  };
}

export function removeAudioEvent(shot: Shot, eventId: string): Shot {
  return {
    ...shot,
    audioPlan: {
      events: shot.audioPlan.events.filter((event) => event.id !== eventId),
    },
  };
}

export function storyboardIssueTarget(
  storyboard: Storyboard,
  issue: ValidationIssue,
): StoryboardIssueTarget | undefined {
  const parts = issue.path.replace(/^storyboard\./, "").split(".");
  if (parts[0] === "shots" && parts[1]) {
    const byId = storyboard.shots.find((shot) => shot.id === parts[1]);
    const byIndex = /^\d+$/.test(parts[1])
      ? storyboard.shots[Number(parts[1])]
      : undefined;
    const shot = byId ?? byIndex;
    if (!shot) return undefined;
    let field = parts[2] || "entity";
    if (field === "audioPlan" && parts[3] === "events" && parts[4]) {
      const event = /^\d+$/.test(parts[4])
        ? shot.audioPlan.events[Number(parts[4])]
        : shot.audioPlan.events.find((candidate) => candidate.id === parts[4]);
      field = event ? `audioPlan.events.${event.id}.${parts[5] || "entity"}` : "audioPlan";
    } else if ((field === "entryState" || field === "exitState") && parts[3]) {
      const nested = parts.slice(3);
      if (nested[0] === "entityStates" && nested[1]) {
        field = `${field}.entityStates.${nested[1]}.${nested[2] || "entityId"}`;
      } else if (nested[0] === "facts") {
        field = `${field}.facts${nested.length > 1 ? `.${nested.slice(1).join(".")}` : ""}`;
      } else {
        field = `${field}.${nested[0]}`;
      }
    } else if (field === "requiredEntityStates" && parts[3]) {
      field = `${field}.${parts[3]}.${parts[4] || "entityId"}`;
    }
    return { entity: { kind: "shot", shotId: shot.id }, field };
  }
  if (parts[0] === "shotBeatLinks" && parts[1]) {
    const index = Number(parts[1]);
    const link = Number.isInteger(index)
      ? storyboard.shotBeatLinks[index]
      : undefined;
    if (link) return { entity: { kind: "link", shotId: link.shotId, beatId: link.beatId }, field: parts[2] || "entity" };
    const beatLinks = storyboard.shotBeatLinks.filter((candidate) => candidate.beatId === parts[1]);
    if (beatLinks.length === 1) {
      return { entity: { kind: "link", shotId: beatLinks[0].shotId, beatId: beatLinks[0].beatId }, field: parts[2] || "entity" };
    }
  }
  return undefined;
}

export function storyboardIssueEntity(
  storyboard: Storyboard,
  issue: ValidationIssue,
): StoryboardEntity | undefined {
  return storyboardIssueTarget(storyboard, issue)?.entity;
}

export function cueLabel(cue: DialogueCue): string {
  const speaker = cue.speakerId ?? cue.voiceOver ?? "旁白";
  return `${speaker} · ${cue.text} · ${cue.estimatedDurationUnits}ms`;
}
