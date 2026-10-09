import type { StoryNode } from "../../types";

export const storyNodeKinds = ["start", "scene", "decision", "join", "ending"] as const;
export const storyNodeKindLabels: Record<StoryNode["kind"], string> = {
  start: "开场", scene: "故事发展", decision: "选择点", join: "汇合点", ending: "结局",
};
export const footageModeLabels: Record<StoryNode["footageMode"], string> = {
  footage: "包含画面", route_only: "仅路线控制点",
};
