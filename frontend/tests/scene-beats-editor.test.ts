import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SceneBeatPlan } from "../src/types";
import { SceneBeatsPage } from "../src/pages/SceneBeatsPage";
import {
  addBeat,
  addCue,
  addScene,
  applyDeleteImpact,
  beatDeleteImpact,
  beatMigrationImpact,
  cueDeleteImpact,
  emptyBeat,
  emptyScene,
  cueMigrationImpact,
  migrateBeatToScene,
  migrateCueToBeat,
  normalizeSceneBeatReferences,
  parseContinuityObject,
  reorderBeat,
  reorderCue,
  reorderScene,
  sceneDeleteImpact,
  sceneBeatsEntityIdentity,
  sceneBeatsFocusKey,
  sceneBeatsIssueTarget,
  sceneIdFromIdentity,
  parseSceneBeatsEntityIdentity,
  sceneUrlIdentity,
  type StoryboardDeletionContext,
} from "../src/scene-beats-editor";

const ids = (...values: string[]) => () => values.shift() || "next";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function plan(): SceneBeatPlan {
  const first = emptyScene("scene-a", "node-a", 1);
  const second = emptyScene("scene-b", "node-a", 2);
  const beatA = emptyBeat("beat-a", "scene-a", 1);
  const beatB = emptyBeat("beat-b", "scene-a", 2);
  return normalizeSceneBeatReferences({
    scenes: [first, second], beats: [beatA, beatB],
    dialogueCues: [
      { id: "cue-a", beatId: "beat-a", order: 1, speakerId: "hero", voiceOver: null, text: "Go", language: "en", delivery: "natural", performanceNotes: "", estimatedDurationUnits: 100 },
      { id: "cue-b", beatId: "beat-a", order: 2, speakerId: null, voiceOver: "Narrator", text: "Now", language: "en", delivery: "brisk", performanceNotes: "", estimatedDurationUnits: 100 },
    ],
  });
}

function storyboardReferences(): StoryboardDeletionContext {
  return {
    shots: [
      { id: "shot-a", sceneId: "scene-a", cueIds: ["cue-a"] },
      { id: "shot-b", sceneId: "scene-b", cueIds: ["cue-b"] },
    ],
    shotBeatLinks: [
      { shotId: "shot-a", beatId: "beat-a" },
      { shotId: "shot-b", beatId: "beat-b" },
    ],
  };
}

describe("scene-beats editor helpers", () => {
  it("exports the editor page without requiring global workspace state", () => {
    expect(typeof SceneBeatsPage).toBe("function");
  });

  it("uses storyboard-compatible namespaced identities while accepting legacy scene routes", () => {
    expect(sceneUrlIdentity("scene/a")).toBe("scene:scene%2Fa");
    expect(sceneIdFromIdentity("scene:scene%2Fa")).toBe("scene/a");
    expect(sceneIdFromIdentity("scene/scene%2Fa")).toBe("scene/a");
    expect(sceneIdFromIdentity("scene-a")).toBe("scene-a");
    expect(sceneBeatsEntityIdentity({ kind: "beat", id: "beat/a" })).toBe("beat:beat%2Fa");
    expect(parseSceneBeatsEntityIdentity("cue:cue%2Fa")).toEqual({ kind: "cue", id: "cue/a" });
    expect(parseSceneBeatsEntityIdentity("scene-a")).toEqual({ kind: "scene", id: "scene-a" });
    expect(sceneBeatsFocusKey({ kind: "cue", id: "cue-a" }, "text")).toBe("scene-beats:cue:cue-a:text");
  });

  it("maps ID and array-index issue paths to the exact entity, parent scene, and field", () => {
    const source = plan();
    expect(sceneBeatsIssueTarget(source, { code: "scene", path: "scenes.scene-a.durationBudgetUnits", message: "too short" })).toMatchObject({ entity: { kind: "scene", id: "scene-a" }, sceneId: "scene-a", field: "durationBudgetUnits" });
    expect(sceneBeatsIssueTarget(source, { code: "beat", path: "beats.1.description", message: "required" })).toMatchObject({ entity: { kind: "beat", id: "beat-b" }, sceneId: "scene-a", field: "description" });
    expect(sceneBeatsIssueTarget(source, { code: "cue", path: "dialogueCues.1.estimatedDurationUnits", message: "too short" })).toMatchObject({ entity: { kind: "cue", id: "cue-b" }, sceneId: "scene-a", field: "estimatedDurationUnits" });
    expect(sceneBeatsIssueTarget(source, { code: "fact", path: "scenes.0.entryState.facts.route", message: "invalid" })).toMatchObject({ entity: { kind: "scene", id: "scene-a" }, field: "entryState.facts.route" });
    expect(sceneBeatsIssueTarget(source, { code: "fact", path: "scenes.scene-a.exitState.facts.route", message: "invalid" })).toMatchObject({ entity: { kind: "scene", id: "scene-a" }, field: "exitState.facts.route" });
    expect(sceneBeatsIssueTarget(source, { code: "delta", path: "beats.0.continuityDelta.route", message: "invalid" })).toMatchObject({ entity: { kind: "beat", id: "beat-a" }, field: "continuityDelta.route" });
    expect(sceneBeatsIssueTarget(source, { code: "delta", path: "beats.beat-a.continuityDelta.route", message: "invalid" })).toMatchObject({ entity: { kind: "beat", id: "beat-a" }, field: "continuityDelta.route" });
  });

  it("creates stable records and keeps declared beat IDs derived from ordered beats", () => {
    const withScene = addScene(plan(), ids("scene-c"), "node-b");
    expect(withScene.scenes.at(-1)).toMatchObject({ id: "scene-c", storyNodeId: "node-b", order: 1 });
    const withBeat = addBeat(plan(), "scene-a", ids("beat-c"));
    expect(withBeat.scenes.find((scene) => scene.id === "scene-a")?.beatIds).toEqual(["beat-a", "beat-b", "beat-c"]);
    const withCue = addCue(withBeat, "beat-c", ids("cue-c"));
    expect(withCue.dialogueCues.at(-1)).toMatchObject({ id: "cue-c", beatId: "beat-c", speakerId: null, voiceOver: "旁白" });
  });

  it("reorders scene, beat, and cue orders without changing stable IDs", () => {
    const movedScene = reorderScene(plan(), "scene-b", -1);
    expect(movedScene.scenes.map((scene) => [scene.id, scene.order])).toEqual([["scene-a", 2], ["scene-b", 1]]);
    const movedBeat = reorderBeat(plan(), "beat-b", -1);
    expect(movedBeat.scenes.find((scene) => scene.id === "scene-a")?.beatIds).toEqual(["beat-b", "beat-a"]);
    const movedCue = reorderCue(plan(), "cue-b", -1);
    expect(movedCue.dialogueCues.map((cue) => [cue.id, cue.order])).toEqual([["cue-a", 2], ["cue-b", 1]]);
  });

  it("migrates beat and cue parent references with stable IDs and canonical orders", () => {
    const movedBeat = migrateBeatToScene(plan(), "beat-a", "scene-b");
    expect(beatMigrationImpact(plan(), "beat-a", "scene-b").affectedCueIds).toEqual(["cue-a", "cue-b"]);
    expect(movedBeat.beats.find((beat) => beat.id === "beat-a")).toMatchObject({ id: "beat-a", sceneId: "scene-b", order: 1 });
    expect(movedBeat.beats.find((beat) => beat.id === "beat-b")?.order).toBe(1);
    expect(movedBeat.scenes.find((scene) => scene.id === "scene-a")?.beatIds).toEqual(["beat-b"]);
    expect(movedBeat.scenes.find((scene) => scene.id === "scene-b")?.beatIds).toEqual(["beat-a"]);

    const movedCue = migrateCueToBeat(plan(), "cue-b", "beat-b");
    expect(cueMigrationImpact(plan(), "cue-b", "beat-b")).toMatchObject({ targetId: "cue-b", fromParentId: "beat-a", toParentId: "beat-b" });
    expect(movedCue.dialogueCues.find((cue) => cue.id === "cue-b")).toMatchObject({ id: "cue-b", beatId: "beat-b", order: 1 });
    expect(movedCue.dialogueCues.find((cue) => cue.id === "cue-a")?.order).toBe(1);
  });

  it("reports exact delete cascades and removes all dependent beats and cues", () => {
    const original = plan();
    const storyboard = storyboardReferences();
    const beforeStoryboard = structuredClone(storyboard);
    const impact = sceneDeleteImpact(original, "scene-a", storyboard);
    expect(impact).toMatchObject({ sceneIds: ["scene-a"], beatIds: ["beat-a", "beat-b"], cueIds: ["cue-a", "cue-b"] });
    const deleted = applyDeleteImpact(original, impact);
    expect(deleted.scenes.map((scene) => scene.id)).toEqual(["scene-b"]);
    expect(deleted.beats).toEqual([]);
    expect(deleted.dialogueCues).toEqual([]);
    expect(storyboard).toEqual(beforeStoryboard);
    expect(impact.retainedStoryboardReferences).toEqual([
      { kind: "shot_beat_link", id: "shot-a:beat-a", path: "storyboard.shotBeatLinks.shot-a:beat-a" },
      { kind: "shot_beat_link", id: "shot-b:beat-b", path: "storyboard.shotBeatLinks.shot-b:beat-b" },
      { kind: "shot_cue_schedule", id: "shot-a", path: "storyboard.shots.shot-a.cueIds.cue-a" },
      { kind: "shot_scene", id: "shot-a", path: "storyboard.shots.shot-a.sceneId" },
      { kind: "shot_cue_schedule", id: "shot-b", path: "storyboard.shots.shot-b.cueIds.cue-b" },
    ]);
    expect(beatDeleteImpact(original, "beat-a", storyboard)).toMatchObject({
      sceneIds: [], beatIds: ["beat-a"], cueIds: ["cue-a", "cue-b"], retainedSceneIds: ["scene-a"],
    });
  });

  it("discloses downstream links and schedules without modifying the storyboard projection", () => {
    const original = plan();
    const storyboard = storyboardReferences();
    const beforeStoryboard = structuredClone(storyboard);

    expect(beatDeleteImpact(original, "beat-a", storyboard).retainedStoryboardReferences).toEqual([
      { kind: "shot_beat_link", id: "shot-a:beat-a", path: "storyboard.shotBeatLinks.shot-a:beat-a" },
      { kind: "shot_cue_schedule", id: "shot-a", path: "storyboard.shots.shot-a.cueIds.cue-a" },
      { kind: "shot_cue_schedule", id: "shot-b", path: "storyboard.shots.shot-b.cueIds.cue-b" },
    ]);
    expect(cueDeleteImpact(original, "cue-a", storyboard).retainedStoryboardReferences).toEqual([
      { kind: "shot_cue_schedule", id: "shot-a", path: "storyboard.shots.shot-a.cueIds.cue-a" },
    ]);
    expect(storyboard).toEqual(beforeStoryboard);
  });

  it("parses only object-shaped continuity facts", () => {
    expect(parseContinuityObject('{"route":"left"}')).toEqual({ value: { route: "left" }, error: null });
    expect(parseContinuityObject("[]").error).toBe("必须是 JSON 对象");
    expect(parseContinuityObject("{").error).toBe("不是有效 JSON 对象");
  });
});

describe("scene-beats structural deletion confirmation", () => {
  let root: Root;

  beforeEach(() => {
    document.body.innerHTML = '<div id="test-root"></div>';
    root = createRoot(document.getElementById("test-root")!);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
  });

  it("uses a top-level confirmation dialog and shows the exact scene cascade before changing the draft", async () => {
    const source = plan();
    const onDraftChange = vi.fn();
    const onEntitySelect = vi.fn();
    await act(async () => root.render(createElement(SceneBeatsPage, {
      value: source,
      stale: false,
      saving: false,
      onSave: async () => undefined,
      onDraftChange,
      onEntitySelect,
    })));

    const deleteScene = [...document.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent === "删除场景");
    expect(deleteScene).toBeDefined();
    await act(async () => deleteScene!.focus());
    expect(onEntitySelect).not.toHaveBeenCalled();
    await act(async () => deleteScene!.click());

    const dialog = document.querySelector<HTMLElement>('[data-testid="delete-impact"]');
    expect(dialog).not.toBeNull();
    expect(dialog?.getAttribute("role")).toBe("alertdialog");
    expect(dialog?.classList.contains("modal")).toBe(true);
    expect(dialog?.textContent).toContain("scene-a");
    expect(dialog?.textContent).toContain("beat-a");
    expect(dialog?.textContent).toContain("cue-a");
    expect(onDraftChange).not.toHaveBeenCalled();

    const cancel = [...dialog!.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent === "取消");
    await act(async () => cancel!.click());
    expect(document.querySelector('[data-testid="delete-impact"]')).toBeNull();
    expect(onDraftChange).not.toHaveBeenCalled();
  });

  it("applies only the confirmed beat cascade and leaves sibling scene data intact", async () => {
    const source = plan();
    const onDraftChange = vi.fn();
    await act(async () => root.render(createElement(SceneBeatsPage, {
      value: source,
      stale: false,
      saving: false,
      onSave: async () => undefined,
      onDraftChange,
    })));

    const deleteBeat = [...document.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent === "删除节拍");
    expect(deleteBeat).toBeDefined();
    await act(async () => deleteBeat!.click());
    const dialog = document.querySelector<HTMLElement>('[data-testid="delete-impact"]');
    expect(dialog?.textContent).toContain("beat-a");
    expect(dialog?.textContent).toContain("cue-a");
    expect(dialog?.textContent).toContain("cue-b");
    expect(dialog?.textContent).toContain("删除场景：无");

    const confirm = dialog!.querySelector<HTMLButtonElement>('[data-testid="confirm-delete"]');
    await act(async () => confirm!.click());
    expect(onDraftChange).toHaveBeenCalledTimes(1);
    const changed = onDraftChange.mock.calls[0][0] as SceneBeatPlan;
    expect(changed.scenes.map((scene) => scene.id)).toEqual(["scene-a", "scene-b"]);
    expect(changed.beats.map((beat) => beat.id)).toEqual(["beat-b"]);
    expect(changed.dialogueCues).toEqual([]);
    expect(document.querySelector('[data-testid="delete-impact"]')).toBeNull();
  });
});
