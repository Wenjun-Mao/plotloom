import type { SceneBeatPlan, Shot, Storyboard, StoryGraph } from "./types";

/** Display-only labels never change frozen source or production authority. */
export function shotLabel(shot: Partial<Pick<Shot, "id" | "title" | "action">>, fallback = "当前镜头"): string {
  const title = shot.title?.trim();
  const value = title && Array.from(title).length <= 64
    ? title : shot.action?.trim() || shot.id || fallback;
  const characters = Array.from(value);
  return characters.length > 52 ? `${characters.slice(0, 51).join("")}…` : value;
}

/** Recovery links identify the owning story position, even when shots share prose. */
export function storyShotLabel(shotId: string, storyboard: Storyboard, plan: SceneBeatPlan, graph: StoryGraph): string {
  const shot = storyboard.shots.find(item => item.id === shotId);
  const scene = plan.scenes.find(item => item.id === shot?.sceneId);
  const node = graph.nodes.find(item => item.id === scene?.storyNodeId);
  if (!shot || !scene || !node) return shot ? `${shotLabel(shot)} · ${shot.id}` : shotId;
  const scenes = plan.scenes.filter(item => item.storyNodeId === node.id).sort((a, b) => a.order - b.order);
  const shots = storyboard.shots.filter(item => item.sceneId === scene.id).sort((a, b) => a.order - b.order);
  const nodeName = shotLabel({ id: node.id, title: node.title });
  const context = `节点 ${graph.nodes.findIndex(item => item.id === node.id) + 1}：${nodeName}`;
  return `${context} · 场次 ${scenes.findIndex(item => item.id === scene.id) + 1} · 镜头 ${shots.findIndex(item => item.id === shot.id) + 1}：${shotLabel(shot)}`;
}
