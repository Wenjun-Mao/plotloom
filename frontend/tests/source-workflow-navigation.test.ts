import { describe, expect, it } from "vitest";

import { sourceWorkflowHref, sourceWorkflowLabel, sourceWorkflowTarget, sourceWorkflowTargets, viewHref, workspaceHref } from "../src/app/workspace/sourceWorkflowNavigation";

describe("source workflow navigation contract", () => {
  it("only permits the four embedded source owners as fragment targets", () => {
    expect(sourceWorkflowTargets).toEqual(["source", "art", "script", "storyboard-review"]);
    expect(sourceWorkflowTarget("script")).toBe("script");
    expect(sourceWorkflowTarget("storyboard")).toBeUndefined();
    expect(sourceWorkflowTarget("unknown")).toBeUndefined();
  });

  it("names only validated source fragments as the creator's active task", () => {
    expect(sourceWorkflowLabel("source")).toBe("来源与大纲");
    expect(sourceWorkflowLabel("art")).toBe("美术参考");
    expect(sourceWorkflowLabel("script")).toBe("剧本");
    expect(sourceWorkflowLabel("storyboard-review")).toBe("分镜评审");
    expect(sourceWorkflowLabel("storyboard")).toBeUndefined();
  });

  it("keeps embedded source review distinct from the legacy shot and media workspace", () => {
    expect(sourceWorkflowHref("project A", "storyboard-review")).toBe("?project=project+A&stage=source#storyboard-review");
    expect(workspaceHref("project A", "storyboard")).toBe("?project=project+A&stage=storyboard");
  });

  it("uses project-scoped reader and play URLs without adding readiness ownership", () => {
    expect(viewHref("project A", "story-prototype")).toBe("?project=project+A&view=story-prototype");
    expect(viewHref("project A", "play")).toBe("?project=project+A&view=play");
  });
});
