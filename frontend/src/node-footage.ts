import type { SceneBeatPlan, StoryNode, Storyboard } from "./types";

export function nodeFootageGaps(node: StoryNode, plan: SceneBeatPlan, board: Storyboard): string[] {
  const scenes = plan.scenes.filter(scene => scene.storyNodeId === node.id);
  if (node.footageMode === "route_only") {
    return scenes.length ? [`${node.title}（路线控制节点不应包含画面）`] : [];
  }
  if (node.footageMode !== "footage") return [`${node.title}（画面契约无效）`];
  return !scenes.length || scenes.some(scene => !board.shots.some(shot => shot.sceneId === scene.id))
    ? [`${node.title}（缺少已编排场景或镜头）`] : [];
}
