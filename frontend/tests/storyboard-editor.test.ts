import { describe, expect, it } from "vitest";
import { demoProject } from "../src/demo";
import {
  addAudioEvent,
  addShotBeatLink,
  assignCue,
  encodeStoryboardEntity,
  moveShot,
  migrateShotToScene,
  parseStoryboardEntity,
  patchAudioEvent,
  removeShot,
  shotRemovalImpact,
  shotSceneMigrationImpact,
  storyboardFocusKey,
  storyboardIssueEntity,
  storyboardIssueTarget,
} from "../src/storyboard-editor";

describe("storyboard editor contract", () => {
  it("reorders shots within one scene without rewriting stable identities", () => {
    const original = structuredClone(demoProject.storyboard);
    const first = original.shots[0];
    const second = original.shots[1];
    expect(first.sceneId).toBe(second.sceneId);

    const moved = moveShot(original, second.id, -1);

    expect(moved.shots.find((shot) => shot.id === first.id)?.order).toBe(2);
    expect(moved.shots.find((shot) => shot.id === second.id)?.order).toBe(1);
    expect(original).toEqual(demoProject.storyboard);
    expect(new Set(moved.shots.map((shot) => shot.id))).toEqual(new Set(original.shots.map((shot) => shot.id)));
  });

  it("reports every relationship before the only explicit shot-delete cascade", () => {
    const shot = { ...demoProject.storyboard.shots[0], audioPlan: { events: [] } };
    const impact = shotRemovalImpact(demoProject.storyboard, shot.id);
    expect(impact.linkBeatIds).toEqual(["b1"]);
    expect(impact.unscheduledCueIds).toEqual(["cue_b1"]);

    const removed = removeShot(demoProject.storyboard, shot.id);
    expect(removed.shots.some((candidate) => candidate.id === shot.id)).toBe(false);
    expect(removed.shotBeatLinks.some((link) => link.shotId === shot.id)).toBe(false);
    expect(demoProject.storyboard.shots.some((candidate) => candidate.id === shot.id)).toBe(true);
  });

  it("keeps dialogue authoritative and refuses hidden reassignment or duplicate PRIMARY coverage", () => {
    const first = demoProject.storyboard.shots[0];
    const second = demoProject.storyboard.shots[1];
    expect(() => assignCue(demoProject.storyboard, second.id, first.cueIds[0])).toThrow(/already scheduled/);

    expect(() => addShotBeatLink(demoProject.storyboard, {
      shotId: second.id,
      beatId: "b1",
      role: "primary",
      coverageWeight: 1,
    })).toThrow(/already has a PRIMARY/);
  });

  it("migrates a stable shot without silently rewriting cue schedules or coverage", () => {
    const shot = demoProject.storyboard.shots[0];
    const impact = shotSceneMigrationImpact(demoProject.storyboard, demoProject.sceneBeats, shot.id, "scene_diagnose");
    expect(impact.crossSceneCueIds).toEqual(["cue_b1"]);
    expect(impact.crossSceneLinkKeys).toEqual([`${shot.id}:b1`]);
    const migrated = migrateShotToScene(demoProject.storyboard, shot.id, "scene_diagnose");
    expect(migrated.shots.find((candidate) => candidate.id === shot.id)).toMatchObject({ id: shot.id, sceneId: "scene_diagnose", order: expect.any(Number) });
    expect(migrated.shotBeatLinks).toEqual(demoProject.storyboard.shotBeatLinks);
    expect(migrated.shots.find((candidate) => candidate.id === shot.id)?.cueIds).toEqual(shot.cueIds);
  });

  it("edits typed audio immutably and maps stable URL and issue identities", () => {
    const shot = { ...demoProject.storyboard.shots[0], audioPlan: { events: [] } };
    const withAudio = addAudioEvent(shot, {
      id: "audio_test",
      kind: "ambience",
      description: "air",
      startOffsetUnits: 0,
      durationUnits: 100,
    });
    const patched = patchAudioEvent(withAudio, "audio_test", { kind: "score" });
    expect(patched.audioPlan.events[0].kind).toBe("score");
    expect(shot.audioPlan.events).toHaveLength(0);

    const encoded = encodeStoryboardEntity({ kind: "shot", shotId: shot.id });
    expect(parseStoryboardEntity(encoded)).toEqual({ kind: "shot", shotId: shot.id });
    expect(parseStoryboardEntity(shot.id)).toEqual({ kind: "shot", shotId: shot.id });
    expect(storyboardIssueEntity(demoProject.storyboard, {
      code: "bad_shot",
      path: `shots.${shot.id}.durationUnits`,
      message: "bad",
    })).toEqual({ kind: "shot", shotId: shot.id });
    expect(storyboardIssueEntity(demoProject.storyboard, {
      code: "bad_link",
      path: "shotBeatLinks.0",
      message: "bad",
    })).toEqual({ kind: "link", shotId: shot.id, beatId: "b1" });
    expect(storyboardIssueTarget(demoProject.storyboard, {
      code: "bad_title",
      path: "shots.0.title",
      message: "required",
    })).toEqual({ entity: { kind: "shot", shotId: shot.id }, field: "title" });
    const audioStoryboard = {
      ...demoProject.storyboard,
      shots: demoProject.storyboard.shots.map((candidate, index) => index === 0
        ? { ...candidate, audioPlan: { events: [{ id: "audio-air", kind: "ambience" as const, description: "air", startOffsetUnits: 0, durationUnits: 100 }] } }
        : candidate),
    };
    const audioTarget = storyboardIssueTarget(audioStoryboard, {
      code: "bad_audio",
      path: "shots.0.audioPlan.events.0.description",
      message: "required",
    });
    expect(audioTarget).toEqual({ entity: { kind: "shot", shotId: shot.id }, field: "audioPlan.events.audio-air.description" });
    expect(storyboardFocusKey(audioTarget!)).toBe(`storyboard:shot:${shot.id}:audioPlan.events.audio-air.description`);
    expect(storyboardIssueTarget(audioStoryboard, {
      code: "bad_fact",
      path: "shots.0.entryState.facts.route",
      message: "invalid",
    })).toEqual({ entity: { kind: "shot", shotId: shot.id }, field: "entryState.facts.route" });
    expect(storyboardIssueTarget(audioStoryboard, {
      code: "bad_fact",
      path: `shots.${shot.id}.exitState.facts.route`,
      message: "invalid",
    })).toEqual({ entity: { kind: "shot", shotId: shot.id }, field: "exitState.facts.route" });
  });
});
