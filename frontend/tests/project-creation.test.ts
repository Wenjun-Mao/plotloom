import { describe, expect, it } from "vitest";
import { demoProject } from "../src/demo";
import { initialStagesThrough, projectCreationBody, projectCreationRequest, workspaceWithStageDraft } from "../src/project-creation";

describe("first-save project creation contract", () => {
  it("keeps a bare brief request free of initial stages", () => {
    expect(projectCreationRequest(demoProject.brief)).toEqual({ brief: demoProject.brief });
  });

  it("constructs the contiguous canonical prefix through the active editor draft", () => {
    const storyboardDraft = {
      ...demoProject.storyboard,
      shots: [...demoProject.storyboard.shots, { ...demoProject.storyboard.shots[0], id: "local-shot" }],
    };
    const workspace = workspaceWithStageDraft(demoProject, "storyboard", storyboardDraft);

    expect(initialStagesThrough(workspace, "storyboard")).toEqual([
      { stage: "story_bible", payload: demoProject.storyBible },
      { stage: "story_graph", payload: demoProject.storyGraph },
      { stage: "scene_beats", payload: demoProject.sceneBeats },
      { stage: "storyboard", payload: storyboardDraft },
    ]);
  });

  it("gives equal canonical requests an equal serialized retry identity", () => {
    const first = projectCreationRequest(demoProject.brief, initialStagesThrough(demoProject, "story_graph"));
    const same = projectCreationRequest(demoProject.brief, initialStagesThrough(demoProject, "story_graph"));
    const changed = projectCreationRequest({ ...demoProject.brief, title: "changed" }, initialStagesThrough(demoProject, "story_graph"));

    expect(projectCreationBody(same)).toBe(projectCreationBody(first));
    expect(projectCreationBody(changed)).not.toBe(projectCreationBody(first));
  });
});
