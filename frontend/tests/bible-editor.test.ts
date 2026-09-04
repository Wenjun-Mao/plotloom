import { describe, expect, it } from "vitest";
import {
  addBibleEntity,
  bibleEntityImpacts,
  deleteBibleEntity,
  entityForIdentity,
  entityUrlIdentity,
  issueTargetForPath,
  updateBibleEntity,
} from "../src/bible-editor";
import type { SceneBeatPlan, StoryBible, Storyboard } from "../src/types";

const bible: StoryBible = {
  logline: "logline", premise: "premise", genre: "genre", tone: "tone", audience: "audience", narrativePromise: "promise", visualLanguage: "visual",
  themes: ["theme"], worldRules: ["rule"], knownFacts: ["fact"], openQuestions: ["question"], sourceNotes: ["note"],
  characters: [{ id: "char-a", name: "A", role: "lead", description: "desc", goal: "goal", traits: ["brave"], visualAnchors: ["coat"], soundAnchors: ["steps"], voiceAnchors: ["warm"], allowedStates: ["ready"], continuityRules: ["coat stays"], }],
  locations: [{ id: "loc-a", name: "A place", description: "desc", visualAnchors: ["fog"], soundAnchors: ["rain"], allowedStates: ["open"], continuityRules: ["night"], }],
  props: [{ id: "prop-a", name: "A prop", description: "desc", visualAnchors: ["brass"], soundAnchors: ["click"], allowedStates: ["closed"], continuityRules: ["left hand"], }],
};

describe("Story Bible immutable helpers", () => {
  it("serializes all V2 entity anchors and keeps stable IDs through immutable edits", () => {
    const withLocation = addBibleEntity(bible, "location", "loc-new");
    const edited = updateBibleEntity(withLocation, { type: "character", id: "char-a" }, { voiceAnchors: ["quiet"], traits: ["careful"] });

    expect(bible.locations).toHaveLength(1);
    expect(edited.locations.at(-1)?.id).toBe("loc-new");
    expect(edited.characters[0]).toMatchObject({ id: "char-a", visualAnchors: ["coat"], soundAnchors: ["steps"], voiceAnchors: ["quiet"], traits: ["careful"] });
    expect(JSON.parse(JSON.stringify(edited))).toEqual(edited);
  });

  it("supports namespaced identities while preserving bare entity URLs", () => {
    expect(entityUrlIdentity("character", "char-a")).toBe("bible:character:char-a");
    expect(entityForIdentity(bible, "bible:location:loc-a")).toEqual({ type: "location", id: "loc-a" });
    expect(entityForIdentity(bible, "prop-a")).toEqual({ type: "prop", id: "prop-a" });
    expect(entityForIdentity(bible, "bible:character:missing")).toBeUndefined();
  });

  it("enumerates scene, shot, state, and cue references and refuses hidden cascades", () => {
    const sceneBeats = {
      scenes: [{ id: "scene-1", characterIds: ["char-a"], locationId: "loc-a", entryState: { entityStates: [{ entityType: "character", entityId: "char-a", state: "ready" }] }, exitState: { entityStates: [] } }],
      beats: [{ id: "beat-1", entryState: { entityStates: [] }, exitState: { entityStates: [{ entityType: "prop", entityId: "prop-a", state: "closed" }] } }],
      dialogueCues: [{ id: "cue-1", speakerId: "char-a" }],
    } as unknown as SceneBeatPlan;
    const storyboard = {
      shots: [{ id: "shot-1", characterIds: ["char-a"], locationId: "loc-a", propIds: ["prop-a"], requiredEntityStates: [{ entityType: "character", entityId: "char-a", state: "ready" }], entryState: { entityStates: [] }, exitState: { entityStates: [{ entityType: "location", entityId: "loc-a", state: "open" }] } }],
      shotBeatLinks: [],
    } as unknown as Storyboard;
    const context = { sceneBeats, storyboard };
    const characterImpacts = bibleEntityImpacts({ type: "character", id: "char-a" }, context);
    const kinds = characterImpacts.map((impact) => impact.kind);

    expect(kinds).toEqual(expect.arrayContaining(["scene", "shot", "state", "cue"]));
    expect(characterImpacts.map((impact) => impact.path)).toContain("dialogueCues.cue-1.speakerId");
    const refused = deleteBibleEntity(bible, { type: "character", id: "char-a" }, context);
    expect(refused.deleted).toBe(false);
    expect(refused.bible).toBe(bible);
    expect(refused.impacts).toHaveLength(characterImpacts.length);
    expect(bibleEntityImpacts({ type: "location", id: "loc-a" }, context).map((impact) => impact.kind)).toEqual(expect.arrayContaining(["scene", "shot", "state"]));
    expect(bibleEntityImpacts({ type: "prop", id: "prop-a" }, context).map((impact) => impact.kind)).toEqual(expect.arrayContaining(["shot", "state"]));
    expect(deleteBibleEntity(bible, { type: "prop", id: "prop-a" }).deleted).toBe(true);
  });

  it("maps issue paths to scalar fields and stable entity rails", () => {
    expect(issueTargetForPath(bible, "storyBible.characters.char-a.voiceAnchors")).toEqual({ entity: { type: "character", id: "char-a" }, field: "voiceAnchors" });
    expect(issueTargetForPath(bible, "locations.0.allowedStates")).toEqual({ entity: { type: "location", id: "loc-a" }, field: "allowedStates" });
    expect(issueTargetForPath(bible, "characters.0.allowedStates.0")).toEqual({ entity: { type: "character", id: "char-a" }, field: "allowedStates" });
    expect(issueTargetForPath(bible, "worldRules.0")).toEqual({ field: "worldRules" });
    expect(issueTargetForPath(bible, "worldRules")).toEqual({ field: "worldRules" });
  });
});
