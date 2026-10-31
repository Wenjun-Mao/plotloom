import { describe, expect, it } from "vitest";
import { lastChoicePath, validateSave, type Story } from "../src/player/state";

const story: Story = {
  format: 1, gameId: "test", storyRevision: "story-r1", assetVersion: "media-v1", title: "Test", intro: "", start: "opening",
  nodes: [
    { id: "opening", title: "Opening", clips: [{ slot: "one", src: "media/a.mp4", durationUnits: 3000, dialogue: [], visibleText: [] }], question: "", edges: [{ id: "enter", to: "choice", label: null }], ending: null },
    { id: "choice", title: "Choice", clips: [], question: "?", edges: [{ id: "a", to: "a", label: "A" }, { id: "b", to: "b", label: "B" }], ending: null },
    ...["a", "b"].map(id => ({ id, title: id, clips: [], question: "", edges: [], ending: { title: id, text: "" } })),
  ],
};
const save = { revision: story.storyRevision, path: ["opening", "choice", "a"], clip: 0, time: 0, finished: true };
describe("standalone route persistence", () => {
  it("validates Continue and truncates abandoned branches before replay", () => {
    expect(validateSave(story, save)).toEqual(save);
    const path = lastChoicePath(story, save.path)!;
    expect(path).toEqual(["opening", "choice"]);
    expect(validateSave(story, { ...save, path: [...path, "b"] })?.path).toEqual(["opening", "choice", "b"]);
    expect(lastChoicePath(story, ["opening", "choice"])).toBeNull();
  });
  it.each([
    { ...save, revision: "old-story" }, { ...save, path: ["opening", "b"] },
    { ...save, path: ["choice", "a"] }, { ...save, clip: 1 }, { ...save, time: -1 },
    { ...save, time: Infinity }, { ...save, path: ["opening", "choice", "missing"] },
  ])("refuses stale or invalid saved route %#", value => expect(validateSave(story, value)).toBeNull());
  it("allows asset replacement without inventing a different authored story", () => {
    expect(validateSave({ ...story, assetVersion: "media-v2" }, save)).toEqual(save);
  });
});
